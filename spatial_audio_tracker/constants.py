"""Project constants and camera presets."""

PITCH_LENGTH_METERS = 105.0
PITCH_WIDTH_METERS = 68.0
TRACKING_FPS_FALLBACK = 25.0

CAMERA_PRESETS = {
    "Broadcast": {
        "position": {"x": 0.0, "y": 18.0, "z": 80.0},
        "forward": {"x": 0.0, "y": -0.16, "z": -1.0},
        "up": {"x": 0.0, "y": 1.0, "z": 0.0},
        "label": "High sideline view centered on midfield.",
    },
    "Left Goal": {
        "position": {"x": -52.5, "y": 3.2, "z": 12.0},
        "forward": {"x": 0.85, "y": -0.04, "z": -0.52},
        "up": {"x": 0.0, "y": 1.0, "z": 0.0},
        "label": "Behind the left goal facing into the pitch.",
    },
    "Right Goal": {
        "position": {"x": 52.5, "y": 3.2, "z": 12.0},
        "forward": {"x": -0.85, "y": -0.04, "z": -0.52},
        "up": {"x": 0.0, "y": 1.0, "z": 0.0},
        "label": "Behind the right goal facing into the pitch.",
    },
    "Midfield Low": {
        "position": {"x": 0.0, "y": 1.8, "z": 36.0},
        "forward": {"x": 0.0, "y": -0.03, "z": -1.0},
        "up": {"x": 0.0, "y": 1.0, "z": 0.0},
        "label": "Low-angle midfield touchline view.",
    },
}

IMPORTANT_EVENT_TYPES = {"SHOT", "GOAL", "FOUL", "CORNER", "POSSESSION_CHANGE", "TURNOVER"}
