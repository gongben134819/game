import random
from dataclasses import dataclass


RUN_UPGRADES = {
    "damage": {"title": "伤害提升", "max_level": 8},
    "fire_rate": {"title": "施法加速", "max_level": 8},
    "missile_count": {"title": "飞弹分裂", "max_level": 4},
    "move_speed": {"title": "轻盈步伐", "max_level": 5},
    "max_health": {"title": "生命上限", "max_level": 4},
    "pickup_range": {"title": "收集范围", "max_level": 6},
}

WEAPON_UPGRADES = {
    "missile": {"title": "魔法飞弹", "max_level": 8},
    "blade": {"title": "旋转刀刃", "max_level": 6},
    "pulse": {"title": "雷霆脉冲", "max_level": 5},
    "flame": {"title": "火焰法球", "max_level": 6},
    "frost": {"title": "冰霜碎片", "max_level": 6},
    "drone": {"title": "金币无人机", "max_level": 6},
}

EVOLUTION_REQUIREMENTS = {
    "missile": {"stat": "missile_count", "level": 2, "title": "星雨飞弹", "description": "飞弹可穿透并分裂追击"},
    "blade": {"stat": "damage", "level": 4, "title": "幻影刀阵", "description": "刀刃留下残影伤害"},
    "pulse": {"stat": "fire_rate", "level": 4, "title": "天罚雷环", "description": "脉冲额外召唤雷击"},
    "flame": {"stat": "damage", "level": 3, "title": "炼狱火场", "description": "火场范围扩大并持续灼烧"},
    "frost": {"stat": "pickup_range", "level": 3, "title": "极寒冰瀑", "description": "冰霜扇形扩大并强化减速"},
    "drone": {"stat": "fire_rate", "level": 3, "title": "黄金齐射", "description": "无人机周期性齐射"},
}


@dataclass(frozen=True)
class UpgradeOption:
    id: str
    title: str
    description: str


def _stat_level(player, upgrade_id):
    return player.run_upgrade_levels.get(upgrade_id, 0)


def _weapon_level(player, weapon_id):
    return player.weapons.get(weapon_id, 0)


def _can_evolve(player, weapon_id):
    requirement = EVOLUTION_REQUIREMENTS[weapon_id]
    if weapon_id in getattr(player, "weapon_evolutions", set()):
        return False
    if _weapon_level(player, weapon_id) < WEAPON_UPGRADES[weapon_id]["max_level"]:
        return False
    return _stat_level(player, requirement["stat"]) >= requirement["level"]


def build_upgrade_pool(player):
    pool = []

    for upgrade_id, definition in RUN_UPGRADES.items():
        current_level = _stat_level(player, upgrade_id)
        if current_level >= definition["max_level"]:
            continue

        next_level = current_level + 1
        descriptions = {
            "damage": f"所有武器伤害 +15%（等级 {next_level}）",
            "fire_rate": f"武器冷却缩短 8%（等级 {next_level}）",
            "missile_count": f"魔法飞弹额外发射数 +1（等级 {next_level}）",
            "move_speed": f"移动速度 +18（等级 {next_level}）",
            "max_health": f"最大生命 +1 并回复 1 点（等级 {next_level}）",
            "pickup_range": f"拾取范围 +20（等级 {next_level}）",
        }
        pool.append(UpgradeOption(upgrade_id, definition["title"], descriptions[upgrade_id]))

    for weapon_id, definition in WEAPON_UPGRADES.items():
        current_level = _weapon_level(player, weapon_id)
        if current_level < definition["max_level"]:
            if current_level == 0:
                description = "解锁新武器"
            else:
                description = f"强化武器效果（等级 {current_level + 1}）"
            pool.append(UpgradeOption(f"weapon:{weapon_id}", definition["title"], description))
            continue

        if _can_evolve(player, weapon_id):
            evolution = EVOLUTION_REQUIREMENTS[weapon_id]
            pool.append(UpgradeOption(f"evolve:{weapon_id}", evolution["title"], evolution["description"]))

    return pool


def choose_upgrade_options(player, count=3, rng=None):
    rng = rng or random
    pool = build_upgrade_pool(player)
    rng.shuffle(pool)
    return pool[:count]


def apply_upgrade(player, upgrade_id):
    if upgrade_id.startswith("weapon:"):
        player.upgrade_weapon(upgrade_id.split(":", 1)[1])
        return

    if upgrade_id.startswith("evolve:"):
        player.evolve_weapon(upgrade_id.split(":", 1)[1])
        return

    player.run_upgrade_levels[upgrade_id] = player.run_upgrade_levels.get(upgrade_id, 0) + 1

    if upgrade_id == "damage":
        player.damage_multiplier += 0.15
    elif upgrade_id == "fire_rate":
        player.cooldown_multiplier = max(0.45, player.cooldown_multiplier * 0.92)
    elif upgrade_id == "missile_count":
        player.extra_missiles += 1
    elif upgrade_id == "move_speed":
        player.speed += 18
    elif upgrade_id == "max_health":
        player.max_health += 1
        player.heal(1)
    elif upgrade_id == "pickup_range":
        player.pickup_range += 20
