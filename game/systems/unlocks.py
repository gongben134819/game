from dataclasses import dataclass

from game.systems.characters import CHARACTERS, DEFAULT_CHARACTER_ID


DEFAULT_UNLOCKED_WEAPONS = ("missile", "blade", "pulse")
DEFAULT_UNLOCKED_CHARACTERS = (DEFAULT_CHARACTER_ID,)
BLUEPRINT_TYPES = ("character", "weapon", "item")


@dataclass(frozen=True)
class UnlockDefinition:
    id: str
    name: str
    category: str
    description: str
    gold_cost: int
    blueprint_type: str
    blueprint_cost: int
    requirement: tuple


ITEM_DEFS = {
    "revive_charm": {
        "name": "复活护符",
        "description": "每局首次死亡时回复部分生命，等级提高回复量。",
        "base_cost": 180,
        "cost_step": 140,
        "max_level": 3,
        "blueprint_cost": 1,
        "requirement": ("chapter", "mine"),
    },
    "starter_magnet": {
        "name": "开局磁铁",
        "description": "开局获得短时磁铁效果，等级提高持续时间。",
        "base_cost": 130,
        "cost_step": 105,
        "max_level": 4,
        "blueprint_cost": 1,
        "requirement": ("gold", 150),
    },
    "exp_charm": {
        "name": "经验护符",
        "description": "提升经验获取效率，更快触发局内升级。",
        "base_cost": 210,
        "cost_step": 160,
        "max_level": 5,
        "blueprint_cost": 2,
        "requirement": ("chapter", "lava"),
    },
    "gold_dice": {
        "name": "金币骰子",
        "description": "提高金币掉落收益，适合刷商城资源。",
        "base_cost": 190,
        "cost_step": 135,
        "max_level": 5,
        "blueprint_cost": 1,
        "requirement": ("chapter", "mine"),
    },
    "boss_hunter": {
        "name": "Boss 猎手",
        "description": "对 Boss 造成更高伤害，章节推进更稳定。",
        "base_cost": 260,
        "cost_step": 190,
        "max_level": 4,
        "blueprint_cost": 2,
        "requirement": ("chapter", "frost"),
    },
    "blueprint_radar": {
        "name": "蓝图雷达",
        "description": "提高蓝图掉落与结算奖励数量。",
        "base_cost": 240,
        "cost_step": 180,
        "max_level": 4,
        "blueprint_cost": 2,
        "requirement": ("endless_floor", 2),
    },
}


CHARACTER_UNLOCKS = {
    "knight": UnlockDefinition("knight", CHARACTERS["knight"].name, "character", "通关金币矿洞后可解锁，生命更高。", 260, "character", 1, ("chapter", "mine")),
    "rogue": UnlockDefinition("rogue", CHARACTERS["rogue"].name, "character", "累计金币达到 200 后可解锁，高速高收益。", 240, "character", 1, ("gold", 200)),
    "alchemist": UnlockDefinition("alchemist", CHARACTERS["alchemist"].name, "character", "通关熔火遗迹后可解锁，擅长燃烧。", 360, "character", 2, ("chapter", "lava")),
    "witch": UnlockDefinition("witch", CHARACTERS["witch"].name, "character", "通关冰封宝库后可解锁，擅长控场。", 420, "character", 2, ("chapter", "frost")),
    "engineer": UnlockDefinition("engineer", CHARACTERS["engineer"].name, "character", "无尽达到第 3 层后可解锁，强化无人机流派。", 520, "character", 3, ("endless_floor", 3)),
}


WEAPON_UNLOCKS = {
    "flame": UnlockDefinition("flame", "火焰法球", "weapon", "通关金币矿洞后可解锁，制造燃烧区域。", 220, "weapon", 1, ("chapter", "mine")),
    "frost": UnlockDefinition("frost", "冰霜碎片", "weapon", "通关熔火遗迹后可解锁，扇形发射并减速。", 280, "weapon", 1, ("chapter", "lava")),
    "drone": UnlockDefinition("drone", "金币无人机", "weapon", "通关机关工坊后可解锁，环绕并自动射击。", 420, "weapon", 2, ("chapter", "factory")),
}


def requirement_met(save_data, requirement):
    kind, value = requirement
    if kind == "chapter":
        return value in save_data.get("completed_chapters", [])
    if kind == "endless_floor":
        return save_data.get("endless_highest_floor", 0) >= value
    if kind == "gold":
        return save_data.get("total_gold", 0) >= value
    return False


def requirement_text(requirement):
    kind, value = requirement
    if kind == "chapter":
        names = {
            "mine": "通关金币矿洞",
            "lava": "通关熔火遗迹",
            "frost": "通关冰封宝库",
            "factory": "通关机关工坊",
            "throne": "通关王座金库",
        }
        return names.get(value, "完成章节")
    if kind == "endless_floor":
        return f"无尽达到第 {value} 层"
    if kind == "gold":
        return f"累计金币达到 {value}"
    return "满足条件"


def item_upgrade_cost(item_id, level):
    definition = ITEM_DEFS[item_id]
    if level >= definition["max_level"]:
        return None
    return definition["base_cost"] + definition["cost_step"] * level + 20 * level * level


def purchase_character_unlock(save_data, character_id):
    definition = CHARACTER_UNLOCKS.get(character_id)
    if not definition:
        return save_data, False, "该角色已默认解锁或不存在"
    if character_id in save_data.get("unlocked_characters", []):
        return save_data, False, "角色已解锁"
    return _purchase_unlock(save_data, definition, "unlocked_characters")


def purchase_weapon_unlock(save_data, weapon_id):
    definition = WEAPON_UNLOCKS.get(weapon_id)
    if not definition:
        return save_data, False, "该武器已默认解锁或不存在"
    if weapon_id in save_data.get("unlocked_weapons", []):
        return save_data, False, "武器已解锁"
    return _purchase_unlock(save_data, definition, "unlocked_weapons")


def purchase_item(save_data, item_id):
    if item_id not in ITEM_DEFS:
        return save_data, False, "未知道具"

    definition = ITEM_DEFS[item_id]
    current_level = save_data.get("item_levels", {}).get(item_id, 0)
    if current_level >= definition["max_level"]:
        return save_data, False, "道具已满级"
    if not requirement_met(save_data, definition["requirement"]):
        return save_data, False, f"需要{requirement_text(definition['requirement'])}"

    cost = item_upgrade_cost(item_id, current_level)
    blueprint_cost = definition["blueprint_cost"] if current_level == 0 else 0
    if save_data.get("total_gold", 0) < cost:
        return save_data, False, "金币不足"
    if save_data.get("blueprints", {}).get("item", 0) < blueprint_cost:
        return save_data, False, "道具蓝图不足"

    save_data["total_gold"] -= cost
    if blueprint_cost:
        save_data["blueprints"]["item"] -= blueprint_cost
    if item_id not in save_data["unlocked_items"]:
        save_data["unlocked_items"].append(item_id)
    save_data["item_levels"][item_id] = current_level + 1
    return save_data, True, "购买成功"


def _purchase_unlock(save_data, definition, unlock_key):
    if not requirement_met(save_data, definition.requirement):
        return save_data, False, f"需要{requirement_text(definition.requirement)}"
    if save_data.get("total_gold", 0) < definition.gold_cost:
        return save_data, False, "金币不足"
    if save_data.get("blueprints", {}).get(definition.blueprint_type, 0) < definition.blueprint_cost:
        return save_data, False, "蓝图不足"

    save_data["total_gold"] -= definition.gold_cost
    save_data["blueprints"][definition.blueprint_type] -= definition.blueprint_cost
    save_data[unlock_key].append(definition.id)
    return save_data, True, "解锁成功"
