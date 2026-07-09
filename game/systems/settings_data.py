import copy
import json
import os

from game.config.settings import DATA_DIR, SETTINGS_FILE


QUALITY_LEVELS = ("low", "medium", "high")

DEFAULT_SETTINGS_DATA = {
    "master_volume": 100,
    "muted": False,
    "effect_quality": "high",
    "screen_shake": True,
    "damage_numbers": True,
    "background_detail": "high",
    "fullscreen": False,
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

    return normalized


def load_settings(path=SETTINGS_FILE):
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULT_SETTINGS_DATA)

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
