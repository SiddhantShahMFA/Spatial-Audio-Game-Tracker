"""Metrica-style replay parsing and feature derivation."""

from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from typing import BinaryIO, Iterable, TextIO

from .constants import IMPORTANT_EVENT_TYPES, PITCH_LENGTH_METERS, PITCH_WIDTH_METERS, TRACKING_FPS_FALLBACK
from .models import Frame, MatchEvent, PlayerState, ReplayBundle
from .replay import ReplaySource


def normalized_to_pitch(x_norm: float | None, y_norm: float | None) -> tuple[float | None, float | None]:
    if x_norm is None or y_norm is None:
        return None, None
    return x_norm * PITCH_LENGTH_METERS - (PITCH_LENGTH_METERS / 2), y_norm * PITCH_WIDTH_METERS - (
        PITCH_WIDTH_METERS / 2
    )


def _open_text(file_or_path: str | BinaryIO) -> TextIO:
    if isinstance(file_or_path, str):
        return open(file_or_path, "r", encoding="utf-8-sig", newline="")
    raw = file_or_path.read()
    if isinstance(raw, bytes):
        return io.StringIO(raw.decode("utf-8-sig"))
    return io.StringIO(str(raw))


def _parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _normalize_event_type(event_type: str, subtype: str | None) -> str:
    upper = event_type.strip().upper()
    subtype_upper = (subtype or "").strip().upper()
    if upper == "BALL LOST":
        return "TURNOVER"
    if upper == "PASS" and "INTERCEPTION" in subtype_upper:
        return "TURNOVER"
    if upper == "RECOVERY":
        return "POSSESSION_CHANGE"
    if upper == "SET PIECE" and "CORNER" in subtype_upper:
        return "CORNER"
    return upper


def _narration_priority(event_type: str) -> int:
    priorities = {
        "GOAL": 100,
        "SHOT": 90,
        "TURNOVER": 70,
        "POSSESSION_CHANGE": 60,
        "CORNER": 55,
        "FOUL": 50,
    }
    return priorities.get(event_type, 10)


class MetricaReplaySource(ReplaySource):
    """Parse a Metrica-style tracking/events pair into normalized frames."""

    def load(
        self,
        tracking_file: str | BinaryIO,
        events_file: str | BinaryIO,
        *,
        source_name: str,
    ) -> ReplayBundle:
        tracking_rows = self._read_csv_rows(tracking_file)
        event_rows = self._read_csv_rows(events_file)
        frames, fps = self._build_frames(tracking_rows)
        events = self._build_events(event_rows)
        self._attach_events(frames, events)
        self._derive_possession(frames, events)
        self._derive_speed(frames, fps)
        self._derive_context_players(frames)
        return ReplayBundle(source_name=source_name, fps=fps, frames=frames, events=events)

    def _read_csv_rows(self, file_or_path: str | BinaryIO) -> list[dict[str, str]]:
        handle = _open_text(file_or_path)
        try:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV file is missing headers.")
            return [dict(row) for row in reader]
        finally:
            handle.close()

    def _build_frames(self, rows: Iterable[dict[str, str]]) -> tuple[list[Frame], float]:
        rows = list(rows)
        if not rows:
            raise ValueError("Tracking file is empty.")
        required = {"Frame", "Time [s]", "Period", "ball_x", "ball_y"}
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError(f"Tracking file missing required columns: {', '.join(sorted(missing))}")

        frames: list[Frame] = []
        previous_time: float | None = None
        observed_deltas: list[float] = []

        for row in rows:
            frame_id = int(row["Frame"])
            timestamp_s = float(row["Time [s]"])
            period = int(row["Period"])
            ball_x_norm = _parse_float(row.get("ball_x"))
            ball_y_norm = _parse_float(row.get("ball_y"))
            if ball_x_norm is None or ball_y_norm is None:
                raise ValueError(f"Tracking row {frame_id} is missing ball coordinates.")
            ball_x, ball_z = normalized_to_pitch(ball_x_norm, ball_y_norm)
            players = self._extract_players(row, ball_x, ball_z)
            frames.append(
                Frame(
                    frame_id=frame_id,
                    period=period,
                    timestamp_s=timestamp_s,
                    ball_x=ball_x or 0.0,
                    ball_z=ball_z or 0.0,
                    players=players,
                )
            )
            if previous_time is not None:
                delta = timestamp_s - previous_time
                if delta > 0:
                    observed_deltas.append(delta)
            previous_time = timestamp_s

        fps = TRACKING_FPS_FALLBACK
        if observed_deltas:
            avg_delta = sum(observed_deltas) / len(observed_deltas)
            if avg_delta > 0:
                fps = 1.0 / avg_delta
        return frames, fps

    def _extract_players(self, row: dict[str, str], ball_x: float | None, ball_z: float | None) -> list[PlayerState]:
        players: list[PlayerState] = []
        handled: set[str] = set()

        for key in row:
            if not key.endswith("_x") or key == "ball_x":
                continue
            base = key[:-2]
            y_key = f"{base}_y"
            if y_key not in row or base in handled:
                continue
            x_norm = _parse_float(row.get(key))
            y_norm = _parse_float(row.get(y_key))
            if x_norm is None or y_norm is None:
                continue
            x, z = normalized_to_pitch(x_norm, y_norm)
            team = "Home" if base.startswith("Home_") else "Away" if base.startswith("Away_") else "Unknown"
            distance = None
            if ball_x is not None and ball_z is not None and x is not None and z is not None:
                distance = math.dist((x, z), (ball_x, ball_z))
            players.append(
                PlayerState(
                    player_id=base,
                    team=team,
                    x=x or 0.0,
                    z=z or 0.0,
                    distance_to_ball=distance,
                )
            )
            handled.add(base)

        if not players:
            raise ValueError("Tracking file does not include any player coordinate columns.")
        return players

    def _build_events(self, rows: Iterable[dict[str, str]]) -> list[MatchEvent]:
        rows = list(rows)
        if not rows:
            raise ValueError("Events file is empty.")
        required = {"Start Frame", "Start Time [s]", "Team", "Type"}
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError(f"Events file missing required columns: {', '.join(sorted(missing))}")

        events: list[MatchEvent] = []
        for index, row in enumerate(rows, start=1):
            frame_id = int(float(row["Start Frame"]))
            timestamp_s = float(row["Start Time [s]"])
            subtype = row.get("Subtype") or None
            event_type = _normalize_event_type(row["Type"], subtype)
            raw_x = _parse_float(row.get("Start X"))
            raw_y = _parse_float(row.get("Start Y"))
            x, z = normalized_to_pitch(raw_x, raw_y)
            important = event_type in IMPORTANT_EVENT_TYPES
            events.append(
                MatchEvent(
                    event_id=f"event-{index}",
                    frame_id=frame_id,
                    timestamp_s=timestamp_s,
                    team=(row.get("Team") or "Unknown").strip() or "Unknown",
                    event_type=event_type,
                    subtype=subtype,
                    player_from=(row.get("From") or None),
                    player_to=(row.get("To") or None),
                    x=x,
                    z=z,
                    raw_x=raw_x,
                    raw_y=raw_y,
                    important=important,
                    narration_priority=_narration_priority(event_type),
                    metadata={"end_frame": row.get("End Frame"), "raw_type": row.get("Type")},
                )
            )
        return events

    def _attach_events(self, frames: list[Frame], events: list[MatchEvent]) -> None:
        by_frame = {frame.frame_id: frame for frame in frames}
        for event in events:
            frame = by_frame.get(event.frame_id)
            if frame:
                frame.event_ids.append(event.event_id)

    def _derive_possession(self, frames: list[Frame], events: list[MatchEvent]) -> None:
        event_groups: dict[int, list[MatchEvent]] = defaultdict(list)
        for event in events:
            event_groups[event.frame_id].append(event)

        current_team: str | None = None
        for frame in frames:
            for event in sorted(event_groups.get(frame.frame_id, []), key=lambda item: item.narration_priority, reverse=True):
                if event.team in {"Home", "Away"}:
                    if current_team and current_team != event.team:
                        turnover = MatchEvent(
                            event_id=f"{event.event_id}-turnover",
                            frame_id=frame.frame_id,
                            timestamp_s=frame.timestamp_s,
                            team=event.team,
                            event_type="POSSESSION_CHANGE",
                            subtype=None,
                            player_from=event.player_from,
                            player_to=event.player_to,
                            x=frame.ball_x,
                            z=frame.ball_z,
                            raw_x=None,
                            raw_y=None,
                            important=True,
                            narration_priority=_narration_priority("POSSESSION_CHANGE"),
                            metadata={"derived_from": event.event_id},
                        )
                        events.append(turnover)
                        frame.event_ids.append(turnover.event_id)
                    current_team = event.team
                    break
            frame.possessing_team = current_team

    def _derive_speed(self, frames: list[Frame], fps: float) -> None:
        if len(frames) < 2:
            return
        for previous, current in zip(frames, frames[1:]):
            delta_t = current.timestamp_s - previous.timestamp_s
            if delta_t <= 0:
                delta_t = 1.0 / fps
            distance = math.dist((previous.ball_x, previous.ball_z), (current.ball_x, current.ball_z))
            current.ball_speed_mps = distance / delta_t
        frames[0].ball_speed_mps = frames[1].ball_speed_mps

    def _derive_context_players(self, frames: list[Frame]) -> None:
        for frame in frames:
            if not frame.players:
                continue
            home_players = sorted(
                (player for player in frame.players if player.team == "Home" and player.distance_to_ball is not None),
                key=lambda player: player.distance_to_ball or math.inf,
            )
            away_players = sorted(
                (player for player in frame.players if player.team == "Away" and player.distance_to_ball is not None),
                key=lambda player: player.distance_to_ball or math.inf,
            )
            if frame.possessing_team == "Away":
                attacker_pool, defender_pool = away_players, home_players
            else:
                attacker_pool, defender_pool = home_players, away_players
            if attacker_pool:
                frame.nearest_attacker_id = attacker_pool[0].player_id
            if defender_pool:
                frame.nearest_defender_id = defender_pool[0].player_id
