from dataclasses import dataclass

from game.config.settings import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW


DEFAULT_CHARACTER_ID = "mage"


@dataclass(frozen=True)
class CharacterDefinition:
    id: str
    name: str
    title: str
    description: str
    passive: str
    initial_weapon: str
    health_multiplier: float
    speed_multiplier: float
    damage_multiplier: float
    pickup_multiplier: float
    gold_multiplier: float
    active_name: str
    active_description: str
    active_cooldown: float
    color: tuple


CHARACTERS = {
    "mage": CharacterDefinition(
        "mage",
        "冒险法师",
        "均衡施法者",
        "基础能力均衡，适合熟悉章节和无尽模式。",
        "拾取范围小幅提高。",
        "missile",
        1.0,
        1.0,
        1.0,
        1.12,
        1.0,
        "奥术新星",
        "释放环形奥术冲击，伤害身边敌人。",
        18.0,
        CYAN,
    ),
    "knight": CharacterDefinition(
        "knight",
        "守卫骑士",
        "稳固前排",
        "生命更高但移动较慢，主动技提供短暂无敌。",
        "最大生命提高，受击容错更强。",
        "blade",
        1.55,
        0.88,
        0.95,
        0.95,
        1.0,
        "护盾震荡",
        "获得短暂无敌并震退周围敌人。",
        24.0,
        GREEN,
    ),
    "rogue": CharacterDefinition(
        "rogue",
        "迅捷盗贼",
        "高速游走",
        "速度和金币收益更高，但生命较低。",
        "金币收益提高，移动速度提高。",
        "missile",
        0.82,
        1.22,
        1.0,
        0.9,
        1.18,
        "疾影冲刺",
        "向当前方向快速冲刺并短暂无敌。",
        14.0,
        YELLOW,
    ),
    "alchemist": CharacterDefinition(
        "alchemist",
        "炼金术士",
        "范围燃爆",
        "伤害略高，主动技点燃大范围敌人。",
        "武器伤害提高，拾取范围略低。",
        "flame",
        0.95,
        0.98,
        1.14,
        0.92,
        1.0,
        "燃爆药剂",
        "引爆药剂云，点燃并伤害周围敌人。",
        20.0,
        RED,
    ),
    "witch": CharacterDefinition(
        "witch",
        "寒霜女巫",
        "控场专家",
        "移动较慢，但主动技可冻结大范围敌人。",
        "冷却略短，拾取范围提高。",
        "frost",
        0.9,
        0.92,
        1.04,
        1.18,
        1.0,
        "冰封领域",
        "冻结周围敌人并造成冰霜伤害。",
        22.0,
        BLUE,
    ),
    "engineer": CharacterDefinition(
        "engineer",
        "机械师",
        "无人机专家",
        "擅长无人机武器，主动技临时提高射速。",
        "武器冷却缩短，基础生命正常。",
        "drone",
        1.0,
        0.98,
        0.98,
        1.0,
        1.0,
        "无人机超频",
        "短时间大幅提高所有武器射速。",
        26.0,
        PURPLE,
    ),
}


def get_character(character_id):
    return CHARACTERS.get(character_id, CHARACTERS[DEFAULT_CHARACTER_ID])
