import copy
import json
import os

from game.config.settings import DATA_DIR, SAVE_FILE
from game.systems.characters import CHARACTERS, DEFAULT_CHARACTER_ID
from game.systems.chapters import CHAPTER_ORDER
from game.systems.unlocks import BLUEPRINT_TYPES, DEFAULT_UNLOCKED_CHARACTERS, DEFAULT_UNLOCKED_WEAPONS, ITEM_DEFS
from game.systems.upgrades import WEAPON_UPGRADES


SAVE_VERSION = 2


PERMANENT_UPGRADES = {
    "max_health": {
        "name": "生命强化",
        "description": "每级增加 1 点初始生命。",
        "base_cost": 80,
        "cost_step": 70,
        "max_level": 1000,
    },
    "move_speed": {
        "name": "疾行训练",
        "description": "每级增加 18 点移动速度。",
        "base_cost": 70,
        "cost_step": 65,
        "max_level": 5,
    },
    "base_damage": {
        "name": "奥术锋刃",
        "description": "每级增加 10% 基础伤害。",
        "base_cost": 90,
        "cost_step": 85,
        "max_level": 1000,
    },
    "gold_bonus": {
        "name": "淘金本能",
        "description": "每级增加 15% 金币收益。",
        "base_cost": 75,
        "cost_step": 75,
        "max_level": 5,
    },
}


DEFAULT_SAVE_DATA = {
    "version": SAVE_VERSION,
    "total_gold": 0,
    "high_score": 0,
    "longest_time": 0,
    "completed_chapters": [],
    "endless_highest_floor": 0,
    "permanent_upgrades": {upgrade_id: 0 for upgrade_id in PERMANENT_UPGRADES},
    "unlocked_characters": list(DEFAULT_UNLOCKED_CHARACTERS),
    "unlocked_weapons": list(DEFAULT_UNLOCKED_WEAPONS),
    "unlocked_items": [],
    "item_levels": {item_id: 0 for item_id in ITEM_DEFS},
    "blueprints": {blueprint_type: 0 for blueprint_type in BLUEPRINT_TYPES},
    "selected_character": DEFAULT_CHARACTER_ID,
}


def normalize_save_data(data):
    """按 v2 schema 规范化存档；旧结构或损坏结构直接重置。"""
    normalized = copy.deepcopy(DEFAULT_SAVE_DATA)
    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return normalized

    for key in ("total_gold", "high_score", "longest_time", "endless_highest_floor"):
        value = data.get(key, normalized[key])
        if isinstance(value, (int, float)):
            normalized[key] = max(0, int(value))

    completed = data.get("completed_chapters", [])
    if isinstance(completed, list):
        normalized["completed_chapters"] = [chapter for chapter in CHAPTER_ORDER if chapter in completed]

    upgrades = data.get("permanent_upgrades", {})
    if isinstance(upgrades, dict):
        for upgrade_id, definition in PERMANENT_UPGRADES.items():
            value = upgrades.get(upgrade_id, 0)
            if isinstance(value, (int, float)):
                normalized["permanent_upgrades"][upgrade_id] = max(0, min(definition["max_level"], int(value)))

    unlocked_characters = data.get("unlocked_characters", [])
    if isinstance(unlocked_characters, list):
        normalized["unlocked_characters"] = sorted(
            {character_id for character_id in unlocked_characters if character_id in CHARACTERS}
            | set(DEFAULT_UNLOCKED_CHARACTERS)
        )

    unlocked_weapons = data.get("unlocked_weapons", [])
    if isinstance(unlocked_weapons, list):
        normalized["unlocked_weapons"] = sorted(
            {weapon_id for weapon_id in unlocked_weapons if weapon_id in WEAPON_UPGRADES}
            | set(DEFAULT_UNLOCKED_WEAPONS)
        )

    unlocked_items = data.get("unlocked_items", [])
    if isinstance(unlocked_items, list):
        normalized["unlocked_items"] = sorted({item_id for item_id in unlocked_items if item_id in ITEM_DEFS})

    item_levels = data.get("item_levels", {})
    if isinstance(item_levels, dict):
        for item_id, definition in ITEM_DEFS.items():
            value = item_levels.get(item_id, 0)
            if isinstance(value, (int, float)):
                level = max(0, min(definition["max_level"], int(value)))
                normalized["item_levels"][item_id] = level
                if level > 0 and item_id not in normalized["unlocked_items"]:
                    normalized["unlocked_items"].append(item_id)

    blueprints = data.get("blueprints", {})
    if isinstance(blueprints, dict):
        for blueprint_type in BLUEPRINT_TYPES:
            value = blueprints.get(blueprint_type, 0)
            if isinstance(value, (int, float)):
                normalized["blueprints"][blueprint_type] = max(0, int(value))

    selected = data.get("selected_character", DEFAULT_CHARACTER_ID)
    if selected in normalized["unlocked_characters"]:
        normalized["selected_character"] = selected

    return normalized


def load_save(path=SAVE_FILE):
    if not os.path.exists(path):
        return save_game(DEFAULT_SAVE_DATA, path)

    try:
        with open(path, "r", encoding="utf-8") as file:
            return normalize_save_data(json.load(file))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_SAVE_DATA)


def save_game(data, path=SAVE_FILE):
    normalized = normalize_save_data(data)
    os.makedirs(os.path.dirname(path) or DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
    return normalized


def get_permanent_upgrade_cost(upgrade_id, current_level):
    definition = PERMANENT_UPGRADES[upgrade_id]
    if current_level >= definition["max_level"]:
        return None
    return definition["base_cost"] + definition["cost_step"] * current_level + 15 * current_level * current_level


def purchase_upgrade(data, upgrade_id):
    normalized = normalize_save_data(data)
    if upgrade_id not in PERMANENT_UPGRADES:
        return normalized, False, "未知升级"

    current_level = normalized["permanent_upgrades"][upgrade_id]
    cost = get_permanent_upgrade_cost(upgrade_id, current_level)
    if cost is None:
        return normalized, False, "该升级已满级"

    if normalized["total_gold"] < cost:
        return normalized, False, "金币不足"

    normalized["total_gold"] -= cost
    normalized["permanent_upgrades"][upgrade_id] = current_level + 1
    return normalized, True, "购买成功"


def record_run(
    data,
    score,
    elapsed_time,
    gold_earned,
    victory=False,
    mode="chapter",
    chapter_id=None,
    endless_floor=0,
    blueprints=None,
):
    normalized = normalize_save_data(data)
    normalized["total_gold"] += max(0, int(gold_earned))
    normalized["high_score"] = max(normalized["high_score"], int(score))
    normalized["longest_time"] = max(normalized["longest_time"], int(elapsed_time))

    if mode == "chapter" and victory and chapter_id in CHAPTER_ORDER:
        if chapter_id not in normalized["completed_chapters"]:
            normalized["completed_chapters"].append(chapter_id)
            normalized["completed_chapters"].sort(key=CHAPTER_ORDER.index)
    if mode == "endless":
        normalized["endless_highest_floor"] = max(normalized["endless_highest_floor"], int(endless_floor))
    if isinstance(blueprints, dict):
        for blueprint_type in BLUEPRINT_TYPES:
            normalized["blueprints"][blueprint_type] += max(0, int(blueprints.get(blueprint_type, 0)))

    return normalized
