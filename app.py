"""Streamlit entrypoint for the spatial audio soccer tracker MVP."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from spatial_audio_tracker.component import render_audio_scene
from spatial_audio_tracker.constants import CAMERA_PRESETS
from spatial_audio_tracker.metrica import MetricaReplaySource
from spatial_audio_tracker.narration import NarrationConfig, NarrationService
from spatial_audio_tracker.sonification import build_renderer_payload


ROOT = Path(__file__).resolve().parent
SAMPLE_TRACKING = ROOT / "data" / "sample_metrica" / "sample_tracking.csv"
SAMPLE_EVENTS = ROOT / "data" / "sample_metrica" / "sample_events.csv"
ENV_FILE = ROOT / ".env"


def load_bundle(tracking_file, events_file, *, source_name: str):
    replay_source = MetricaReplaySource()
    return replay_source.load(tracking_file, events_file, source_name=source_name)


def ensure_session_state() -> None:
    defaults = {
        "playback_running": False,
        "start_time_s": 0.0,
        "playback_speed": 1.0,
        "camera_preset": "Broadcast",
        "narration_enabled": True,
        "show_all_players": False,
        "audio_ready": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _read_env_value(name: str) -> str | None:
    if not ENV_FILE.exists():
        return None
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        parsed = value.strip().strip("'\"")
        return parsed or None
    return None


def get_openai_key() -> str | None:
    env_key = os.environ.get("OPENAI_API_KEY") or _read_env_value("OPENAI_API_KEY")
    if env_key:
        return env_key
    try:
        return st.secrets.get("OPENAI_API_KEY", None)
    except StreamlitSecretNotFoundError:
        return None


def main() -> None:
    st.set_page_config(page_title="Spatial Audio Soccer Tracker", layout="wide")
    ensure_session_state()
    st.title("Spatial Audio Soccer Tracker")
    st.caption("Replay Metrica-style tracking data with spatial audio, event earcons, and optional narrated context.")

    with st.sidebar:
        st.header("Replay Source")
        use_sample = st.toggle("Use bundled sample match", value=True)
        tracking_upload = None
        events_upload = None
        source_name = "Bundled Demo Match"
        if not use_sample:
            tracking_upload = st.file_uploader("Tracking CSV", type=["csv"], key="tracking_csv")
            events_upload = st.file_uploader("Event CSV", type=["csv"], key="events_csv")
            source_name = "Uploaded Match"

        st.header("Playback")
        col1, col2 = st.columns(2)
        if col1.button("Play", use_container_width=True):
            st.session_state.playback_running = True
        if col2.button("Pause", use_container_width=True):
            st.session_state.playback_running = False
        st.session_state.playback_speed = st.select_slider(
            "Speed",
            options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
            value=st.session_state.playback_speed,
        )
        st.session_state.camera_preset = st.selectbox(
            "Camera preset",
            options=list(CAMERA_PRESETS.keys()),
            index=list(CAMERA_PRESETS.keys()).index(st.session_state.camera_preset),
        )
        st.session_state.narration_enabled = st.toggle("Narration", value=st.session_state.narration_enabled)
        st.session_state.show_all_players = st.toggle("Show all players on mini-map", value=st.session_state.show_all_players)

    try:
        if use_sample:
            bundle = load_bundle(str(SAMPLE_TRACKING), str(SAMPLE_EVENTS), source_name=source_name)
        else:
            if not tracking_upload or not events_upload:
                st.info("Upload both tracking and event CSV files to start a custom replay.")
                return
            tracking_upload.seek(0)
            events_upload.seek(0)
            bundle = load_bundle(tracking_upload, events_upload, source_name=source_name)
    except ValueError as exc:
        st.error(str(exc))
        return

    max_time = max(bundle.duration_s, 0.1)
    st.session_state.start_time_s = st.slider(
        "Start time (seconds)",
        min_value=0.0,
        max_value=float(round(max_time, 2)),
        value=min(st.session_state.start_time_s, float(round(max_time, 2))),
        step=0.1,
    )

    openai_key = get_openai_key()
    narration_service = NarrationService(
        api_key=openai_key,
        config=NarrationConfig(enabled=st.session_state.narration_enabled and bool(openai_key)),
    )
    narrations = narration_service.build_narrations(bundle) if st.session_state.narration_enabled else {}

    payload = build_renderer_payload(bundle, st.session_state.camera_preset, narration_enabled=st.session_state.narration_enabled)
    payload["controls"] = {
        "playing": st.session_state.playback_running,
        "speed": st.session_state.playback_speed,
        "start_time_s": st.session_state.start_time_s,
        "show_all_players": st.session_state.show_all_players,
    }
    payload["narrations"] = narrations

    summary_col, status_col = st.columns([2, 1])
    with summary_col:
        st.subheader(bundle.source_name)
        st.write(
            {
                "frames": len(bundle.frames),
                "events": len(bundle.events),
                "duration_s": round(bundle.duration_s, 2),
                "fps": round(bundle.fps, 2),
                "camera": st.session_state.camera_preset,
            }
        )
    with status_col:
        st.subheader("Preset")
        st.caption(CAMERA_PRESETS[st.session_state.camera_preset]["label"])
        st.metric("Narrated events", len(narrations))
        if st.session_state.narration_enabled and not openai_key:
            st.caption("Using deterministic narration fallback. Add `OPENAI_API_KEY` to `.env` or Streamlit secrets for model-generated lines.")

    render_audio_scene(payload)

    with st.expander("Narration preview", expanded=False):
        if narrations:
            for event_id, text in narrations.items():
                st.write(f"{event_id}: {text}")
        else:
            st.caption("Narration disabled or no eligible events found.")

    with st.expander("Data contract notes", expanded=False):
        st.markdown(
            """
            - Tracking CSV must include `Frame`, `Time [s]`, `Period`, `ball_x`, `ball_y`, and player columns such as `Home_7_x`, `Home_7_y`.
            - Event CSV must include `Start Frame`, `Start Time [s]`, `Team`, `Type`, plus optional `Subtype`, `From`, `To`, `Start X`, and `Start Y`.
            - Coordinates are expected in normalized `0..1` pitch space and are mapped internally to a centered `105m x 68m` pitch.
            """
        )


if __name__ == "__main__":
    main()
