# Spatial Audio Game Tracker

Local-first Streamlit MVP for replaying Metrica-style soccer tracking data with:

- browser-based spatial audio for ball motion plus nearest attacker and defender
- event earcons for shots, fouls, corners, goals, and possession changes
- a debug mini-map with named listener presets
- optional server-side OpenAI narration with browser TTS playback

## Quick start

```bash
uv venv .venv
uv pip install -e '.[dev]'
.venv/bin/streamlit run app.py
```

Run tests with:

```bash
uv run pytest -q
```

## Data format

The MVP expects Metrica-style CSVs with normalized `0..1` coordinates.

Tracking CSV required columns:

- `Frame`
- `Time [s]`
- `Period`
- `ball_x`
- `ball_y`
- player columns like `Home_7_x`, `Home_7_y`, `Away_4_x`, `Away_4_y`

Events CSV required columns:

- `Start Frame`
- `Start Time [s]`
- `Team`
- `Type`

Optional event columns used when present:

- `Subtype`
- `From`
- `To`
- `Start X`
- `Start Y`
- `End Frame`
- `End Time [s]`
- `End X`
- `End Y`

Bundled demo files live under [data/sample_metrica/sample_tracking.csv](/Users/siddhantshah/Desktop/AI/Spatial-Audio-Game-Tracker/data/sample_metrica/sample_tracking.csv) and [data/sample_metrica/sample_events.csv](/Users/siddhantshah/Desktop/AI/Spatial-Audio-Game-Tracker/data/sample_metrica/sample_events.csv).

## Narration

For local development, add this to `.env` in the repo root:

```bash
OPENAI_API_KEY=your-api-key
```

The app checks `OPENAI_API_KEY` in this order:

1. shell environment
2. repo-root `.env`
3. `.streamlit/secrets.toml`

Without a key, the app still works and falls back to deterministic event narration.
