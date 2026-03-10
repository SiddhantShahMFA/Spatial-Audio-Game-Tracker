"""Prepare frontend-friendly replay payloads and derived event flags."""

from __future__ import annotations

from dataclasses import asdict

from .constants import CAMERA_PRESETS
from .models import MatchEvent, ReplayBundle


def build_event_label(event: MatchEvent) -> str:
    parts = [event.event_type.replace("_", " ").title()]
    if event.team:
        parts.append(f"for {event.team}")
    if event.player_from:
        parts.append(f"by {event.player_from}")
    return " ".join(parts)


def build_renderer_payload(bundle: ReplayBundle, selected_camera: str, *, narration_enabled: bool) -> dict:
    camera_name = selected_camera if selected_camera in CAMERA_PRESETS else "Broadcast"
    frames = []
    for frame in bundle.frames:
        player_index = {player.player_id: asdict(player) for player in frame.players}
        frames.append(
            {
                "frame_id": frame.frame_id,
                "period": frame.period,
                "timestamp_s": frame.timestamp_s,
                "ball": {"x": frame.ball_x, "y": frame.ball_y, "z": frame.ball_z, "speed_mps": frame.ball_speed_mps},
                "possessing_team": frame.possessing_team,
                "nearest_attacker": player_index.get(frame.nearest_attacker_id) if frame.nearest_attacker_id else None,
                "nearest_defender": player_index.get(frame.nearest_defender_id) if frame.nearest_defender_id else None,
                "event_ids": list(frame.event_ids),
                "players": list(player_index.values()),
            }
        )
    events = [
        {
            "event_id": event.event_id,
            "frame_id": event.frame_id,
            "timestamp_s": event.timestamp_s,
            "team": event.team,
            "event_type": event.event_type,
            "important": event.important,
            "priority": event.narration_priority,
            "label": build_event_label(event),
            "x": event.x,
            "z": event.z,
        }
        for event in sorted(bundle.events, key=lambda item: (item.timestamp_s, -item.narration_priority))
    ]
    return {
        "source_name": bundle.source_name,
        "fps": bundle.fps,
        "duration_s": bundle.duration_s,
        "camera": {"name": camera_name, "preset": CAMERA_PRESETS[camera_name]},
        "frames": frames,
        "events": events,
        "settings": {"narration_enabled": narration_enabled},
    }
