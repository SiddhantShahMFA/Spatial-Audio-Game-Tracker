"""HTML renderer bridge for Streamlit."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit.components.v1 as components


HTML_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "frontend" / "renderer.html"


def render_audio_scene(payload: dict, *, height: int = 760) -> None:
    html_template = HTML_TEMPLATE_PATH.read_text(encoding="utf-8")
    html = html_template.replace("__REPLAY_PAYLOAD__", json.dumps(payload))
    components.html(html, height=height, scrolling=False)
