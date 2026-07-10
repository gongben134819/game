import copy
import json
import os

from game.config.settings import DATA_DIR, SETTINGS_FILE


QUALITY_LEVELS = ("low", "medium", "high")
DISPLAY_MODES = ("windowed", "fullscreen")
WINDOW_SIZE_OPTIONS = ((1280, 720), (1600, 900), (1920, 1080))
TOUCH_CONTROL_VALUES = (True, False, "auto")

DEFAULT_SETTINGS_DATA = {
    "master_volume": 100,
    "muted": False,
    "effect_quality": "high",
    "screen_shake": True,
    "damage_numbers": True,
    "background_detail": "high",
    "fullscreen": False,
    "display_mode": "windowed",
    "window_size": [1280, 720],
    "ui_scale": 1.0,
    "touch_controls": "auto",
}


def normalize_settings_data(data):
    """补齐缺失设置，并把非法值恢复到默认值。"""
    normalized = copy.deepcopy(DEFAULT_SETTINGS_DATA)
    if not isinstance(data, dict):
        return normalized

    volume = data.get("master_volume", normalized["master_volume"])
    if isinstance(volume, (int, float)):
        normalized["master_volume"] = max(0, min(100, int(volume)))

    for key in ("muted", "screen_shake", "damage_numbers", "fullscreen"):
        value = data.get(key, normalized[key])
        if isinstance(value, bool):
            normalized[key] = value

    for key in ("effect_quality", "background_detail"):
        value = data.get(key, normalized[key])
        if value in QUALITY_LEVELS:
            normalized[key] = value

    display_mode = data.get("display_mode")
    if display_mode in DISPLAY_MODES:
        normalized["display_mode"] = display_mode
    elif normalized.get("fullscreen"):
        normalized["display_mode"] = "fullscreen"

    window_size = data.get("window_size")
    if isinstance(window_size, (list, tuple)) and len(window_size) == 2:
        width, height = window_size
        if isinstance(width, (int, float)) and isinstance(height, (int, float)):
            size = (int(width), int(height))
            if size in WINDOW_SIZE_OPTIONS:
                normalized["window_size"] = [size[0], size[1]]

    ui_scale = data.get("ui_scale")
    if isinstance(ui_scale, (int, float)):
        normalized["ui_scale"] = round(max(0.85, min(1.25, float(ui_scale))), 2)

    touch_controls = data.get("touch_controls")
    if touch_controls in TOUCH_CONTROL_VALUES:
        normalized["touch_controls"] = touch_controls

    normalized["fullscreen"] = normalized["display_mode"] == "fullscreen"

    return normalized


def load_settings(path=SETTINGS_FILE):
    if not os.path.exists(path):
        return save_settings(DEFAULT_SETTINGS_DATA, path)

    try:
        with open(path, "r", encoding="utf-8") as file:
            return normalize_settings_data(json.load(file))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_SETTINGS_DATA)


def save_settings(data, path=SETTINGS_FILE):
    normalized = normalize_settings_data(data)
    os.makedirs(os.path.dirname(path) or DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
    return normalized
