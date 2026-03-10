from spatial_audio_tracker.models import MatchEvent
from spatial_audio_tracker.narration import NarrationService


def test_fallback_narration_mentions_side_for_shot():
    service = NarrationService(api_key=None)
    event = MatchEvent(
        event_id="event-1",
        frame_id=1,
        timestamp_s=1.2,
        team="Home",
        event_type="SHOT",
        subtype=None,
        player_from="Home_9",
        player_to=None,
        x=30.0,
        z=0.0,
        raw_x=0.8,
        raw_y=0.5,
        important=True,
        narration_priority=90,
    )
    text = service._fallback_text(event, {"ball_x": 30.0})
    assert "shot" in text.lower()
    assert "right" in text.lower()
