import copy
import json
import os

from game.config.settings import DATA_DIR, SAVE_FILE


PERMANENT_UPGRADES = {
    "max_health": {
        "name": "生命强化",
        "description": "每级增加 1 点初始生命",
        "base_cost": 80,
        "cost_step": 70,
        "max_level": 5,
    },
    "move_speed": {
        "name": "疾行训练",
        "description": "每级增加 18 点移动速度",
        "base_cost": 70,
        "cost_step": 65,
        "max_level": 5,
    },
    "base_damage": {
        "name": "奥术锋刃",
        "description": "每级增加 10% 基础伤害",
        "base_cost": 90,
        "cost_step": 85,
        "max_level": 5,
    },
    "gold_bonus": {
        "name": "淘金本能",
        "description": "每级增加 15% 金币收益",
        "base_cost": 75,
        "cost_step": 75,
        "max_level": 5,
    },
}

DEFAULT_SAVE_DATA = {
    "total_gold": 0,
    "high_score": 0,
    "longest_time": 0,
    "permanent_upgrades": {upgrade_id: 0 for upgrade_id in PERMANENT_UPGRADES},
}


def normalize_save_data(data):
    """补齐缺失字段，并丢弃不符合类型的存档值。"""
    normalized = copy.deepcopy(DEFAULT_SAVE_DATA)
    if not isinstance(data, dict):
        return normalized

    for key in ("total_gold", "high_score", "longest_time"):
        value = data.get(key, normalized[key])
        if isinstance(value, (int, float)):
            normalized[key] = max(0, int(value))

    upgrades = data.get("permanent_upgrades", {})
    if isinstance(upgrades, dict):
        for upgrade_id, definition in PERMANENT_UPGRADES.items():
            value = upgrades.get(upgrade_id, 0)
            if isinstance(value, (int, float)):
                normalized["permanent_upgrades"][upgrade_id] = max(
                    0, min(definition["max_level"], int(value))
                )

    return normalized


def load_save(path=SAVE_FILE):
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULT_SAVE_DATA)

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


def record_run(data, score, elapsed_time, gold_earned):
    normalized = normalize_save_data(data)
    normalized["total_gold"] += max(0, int(gold_earned))
    normalized["high_score"] = max(normalized["high_score"], int(score))
    normalized["longest_time"] = max(normalized["longest_time"], int(elapsed_time))
    return normalized
