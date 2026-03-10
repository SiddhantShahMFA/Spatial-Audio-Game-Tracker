"""Narration service with OpenAI integration and deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import MatchEvent, ReplayBundle

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled in runtime fallback
    OpenAI = None  # type: ignore[assignment]


class SupportsResponseText(Protocol):
    output_text: str


@dataclass(slots=True)
class NarrationConfig:
    enabled: bool = False
    model: str = "gpt-4.1-mini"
    max_events: int = 8


class NarrationService:
    def __init__(self, api_key: str | None, config: NarrationConfig | None = None) -> None:
        self.config = config or NarrationConfig(enabled=bool(api_key))
        self._client = OpenAI(api_key=api_key) if api_key and OpenAI else None

    def build_narrations(self, bundle: ReplayBundle) -> dict[str, str]:
        narrations: dict[str, str] = {}
        important_events = sorted(
            (event for event in bundle.events if event.important),
            key=lambda item: (-item.narration_priority, item.timestamp_s),
        )[: self.config.max_events]
        for event in important_events:
            context = self._build_context(bundle, event)
            narrations[event.event_id] = self._generate_text(event, context)
        return narrations

    def _build_context(self, bundle: ReplayBundle, event: MatchEvent) -> dict[str, object]:
        nearby_frames = [
            frame
            for frame in bundle.frames
            if max(0, event.timestamp_s - 1.2) <= frame.timestamp_s <= event.timestamp_s + 0.6
        ]
        last_frame = nearby_frames[-1] if nearby_frames else None
        return {
            "source_name": bundle.source_name,
            "event_type": event.event_type,
            "team": event.team,
            "player_from": event.player_from,
            "player_to": event.player_to,
            "timestamp_s": round(event.timestamp_s, 2),
            "ball_x": round(last_frame.ball_x, 1) if last_frame else event.x,
            "ball_z": round(last_frame.ball_z, 1) if last_frame else event.z,
            "possession_team": last_frame.possessing_team if last_frame else event.team,
        }

    def _generate_text(self, event: MatchEvent, context: dict[str, object]) -> str:
        if not self.config.enabled or not self._client:
            return self._fallback_text(event, context)
        prompt = (
            "You are writing one short, accessible soccer audio narration line in English. "
            "Keep it under 18 words, factual, and tuned for a blind or low-vision listener. "
            f"Context: {context!r}"
        )
        try:
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(model=self.config.model, input=prompt)
                text = getattr(response, "output_text", "").strip()
                if text:
                    return text
            completion = self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = completion.choices[0].message.content or ""
            return text.strip() or self._fallback_text(event, context)
        except Exception:
            return self._fallback_text(event, context)

    def _fallback_text(self, event: MatchEvent, context: dict[str, object]) -> str:
        location = ""
        if context.get("ball_x") is not None:
            x = float(context["ball_x"])
            if x < -20:
                location = " on the left side"
            elif x > 20:
                location = " on the right side"
            else:
                location = " in midfield"
        team = f"{event.team} " if event.team and event.team != "Unknown" else ""
        if event.event_type == "GOAL":
            return f"{team}goal{location}."
        if event.event_type == "SHOT":
            return f"{team}shot{location}."
        if event.event_type == "CORNER":
            return f"{team}corner won{location}."
        if event.event_type in {"TURNOVER", "POSSESSION_CHANGE"}:
            return f"Possession changes to {event.team}{location}."
        if event.event_type == "FOUL":
            return f"Foul against {team.strip() or 'the attack'}{location}."
        return f"{team}{event.event_type.replace('_', ' ').lower()}{location}."
