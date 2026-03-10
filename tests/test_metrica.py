from pathlib import Path

import pytest

from spatial_audio_tracker.metrica import MetricaReplaySource, normalized_to_pitch


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_metrica"


def test_normalized_to_pitch_corners_and_center():
    assert normalized_to_pitch(0.0, 0.0) == (-52.5, -34.0)
    assert normalized_to_pitch(0.5, 0.5) == (0.0, 0.0)
    assert normalized_to_pitch(1.0, 1.0) == (52.5, 34.0)


def test_metrica_source_loads_sample_bundle():
    source = MetricaReplaySource()
    bundle = source.load(
        str(DATA_DIR / "sample_tracking.csv"),
        str(DATA_DIR / "sample_events.csv"),
        source_name="Test Match",
    )
    assert bundle.source_name == "Test Match"
    assert bundle.frames
    assert bundle.events
    assert bundle.frames[0].nearest_attacker_id is not None
    assert bundle.frames[0].nearest_defender_id is not None
    assert bundle.frames[1].ball_speed_mps >= 0


def test_missing_required_tracking_columns_raise_error(tmp_path: Path):
    bad_tracking = tmp_path / "tracking.csv"
    bad_events = tmp_path / "events.csv"
    bad_tracking.write_text("Frame,Time [s],Period\n1,0.0,1\n", encoding="utf-8")
    bad_events.write_text("Start Frame,Start Time [s],Team,Type\n1,0.0,Home,Pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Tracking file missing required columns"):
        MetricaReplaySource().load(str(bad_tracking), str(bad_events), source_name="Broken")
