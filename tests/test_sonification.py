from pathlib import Path

from spatial_audio_tracker.metrica import MetricaReplaySource
from spatial_audio_tracker.sonification import build_renderer_payload


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_metrica"


def test_renderer_payload_contains_core_audio_entities():
    bundle = MetricaReplaySource().load(
        str(DATA_DIR / "sample_tracking.csv"),
        str(DATA_DIR / "sample_events.csv"),
        source_name="Sample",
    )
    payload = build_renderer_payload(bundle, "Broadcast", narration_enabled=True)
    assert payload["camera"]["name"] == "Broadcast"
    assert payload["frames"][0]["ball"]["x"] is not None
    assert payload["frames"][0]["nearest_attacker"] is not None
    assert payload["frames"][0]["nearest_defender"] is not None
    assert any(event["event_type"] == "SHOT" for event in payload["events"])
