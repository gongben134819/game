import random
from dataclasses import dataclass

import pygame

from game.config.settings import BLUE, CYAN, GREEN, RED, SCREEN_HEIGHT, SCREEN_WIDTH, YELLOW
from game.entities.enemy import EnemyProjectile


CHAPTER_ORDER = ("mine", "lava", "frost", "factory", "throne")


@dataclass(frozen=True)
class ChapterDefinition:
    id: str
    name: str
    subtitle: str
    description: str
    mechanic_name: str
    mechanic_description: str
    boss_name: str
    theme: str
    difficulty: float
    reward_blueprint: str


CHAPTERS = {
    "mine": ChapterDefinition(
        "mine",
        "金币矿洞",
        "旧矿脉入口",
        "矿车轨道会定时预警并横向冲撞。",
        "矿车轨道",
        "看到轨道红光后尽快离开横向区域。",
        "矿洞工头",
        "mine",
        1.0,
        "weapon",
    ),
    "lava": ChapterDefinition(
        "lava",
        "熔火遗迹",
        "沉入岩浆的金库",
        "熔岩裂隙会先预警，随后燃烧地面。",
        "熔岩裂隙",
        "裂隙伤害玩家，并会点燃站在其中的敌人。",
        "熔火祭司",
        "lava",
        1.18,
        "item",
    ),
    "frost": ChapterDefinition(
        "frost",
        "冰封宝库",
        "冻结的地下钱库",
        "冰面区域会降低摩擦，让移动更滑。",
        "冰面滑移",
        "经过冰面时提前减速，避免冲进敌群。",
        "冰冠守卫",
        "frost",
        1.34,
        "character",
    ),
    "factory": ChapterDefinition(
        "factory",
        "机关工坊",
        "自动机关守护区",
        "炮台会定时瞄准玩家射击。",
        "机关炮台",
        "炮台弹道清晰但伤害稳定，需要保持移动。",
        "齿轮巨像",
        "factory",
        1.52,
        "weapon",
    ),
    "throne": ChapterDefinition(
        "throne",
        "王座金库",
        "金币领主的宫殿",
        "诅咒区提高金币收益，但会周期性造成压力伤害。",
        "金币诅咒",
        "站在金色法阵中金币更多，但不能贪留太久。",
        "金币领主",
        "throne",
        1.78,
        "item",
    ),
}


def get_chapter(chapter_id):
    return CHAPTERS.get(chapter_id, CHAPTERS["mine"])


def next_chapter_id(chapter_id):
    try:
        index = CHAPTER_ORDER.index(chapter_id)
    except ValueError:
        return None
    if index + 1 >= len(CHAPTER_ORDER):
        return None
    return CHAPTER_ORDER[index + 1]


def chapter_unlocked(save_data, chapter_id):
    if chapter_id == CHAPTER_ORDER[0]:
        return True
    completed = set(save_data.get("completed_chapters", []))
    try:
        index = CHAPTER_ORDER.index(chapter_id)
    except ValueError:
        return False
    return CHAPTER_ORDER[index - 1] in completed


class MapMechanicController:
    def __init__(self, chapter_id):
        self.chapter_id = chapter_id
        seed_offset = CHAPTER_ORDER.index(chapter_id) if chapter_id in CHAPTER_ORDER else 0
        self.rng = random.Random(9301 + seed_offset)
        self.events = []
        self.timer = 0
        self.damage_cooldown = 0
        self.turrets = [
            pygame.Vector2(120, 120),
            pygame.Vector2(SCREEN_WIDTH - 120, 120),
            pygame.Vector2(120, SCREEN_HEIGHT - 120),
            pygame.Vector2(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 120),
        ]
        self.ice_zones = [
            pygame.Rect(170, 150, 260, 110),
            pygame.Rect(800, 135, 280, 120),
            pygame.Rect(500, 455, 330, 120),
        ]
        self.curse_zones = [
            pygame.Rect(220, 170, 270, 140),
            pygame.Rect(780, 390, 290, 150),
        ]

    def reset_frame_effects(self, level):
        level.player.terrain_friction_multiplier = 1.0
        level.player.gold_bonus_multiplier = 1.0

    def update(self, level, dt):
        self.reset_frame_effects(level)
        self.damage_cooldown = max(0, self.damage_cooldown - dt)
        self.timer += dt

        if self.chapter_id == "mine":
            self.update_mine(level)
        elif self.chapter_id == "lava":
            self.update_lava(level)
        elif self.chapter_id == "frost":
            self.update_frost(level)
        elif self.chapter_id == "factory":
            self.update_factory(level)
        elif self.chapter_id == "throne":
            self.update_throne(level)

        for event in list(self.events):
            event["time"] -= dt
            if event["time"] <= 0:
                self.events.remove(event)

    def update_mine(self, level):
        if self.timer >= 7.2:
            self.timer = 0
            y = self.rng.randrange(120, SCREEN_HEIGHT - 110)
            self.events.append({"kind": "minecart", "phase": "warning", "time": 0.9, "y": y})
        for event in list(self.events):
            if event["kind"] == "minecart" and event["phase"] == "warning" and event["time"] <= 0.15:
                event["phase"] = "active"
                event["time"] = 0.55
            if event["kind"] == "minecart" and event["phase"] == "active":
                rect = pygame.Rect(0, event["y"] - 18, SCREEN_WIDTH, 36)
                self.hit_player(level, rect, 1)
                self.damage_enemies(level, rect, 32, "blade")

    def update_lava(self, level):
        if self.timer >= 6.0:
            self.timer = 0
            rect = pygame.Rect(
                self.rng.randrange(140, 900),
                self.rng.randrange(130, 520),
                self.rng.randrange(190, 320),
                54,
            )
            self.events.append({"kind": "lava", "phase": "warning", "time": 0.95, "rect": rect})
        for event in list(self.events):
            if event["kind"] == "lava" and event["phase"] == "warning" and event["time"] <= 0.15:
                event["phase"] = "active"
                event["time"] = 2.0
            if event["kind"] == "lava" and event["phase"] == "active":
                rect = event["rect"]
                self.hit_player(level, rect, 1)
                for enemy in list(level.enemy_sprites):
                    if rect.colliderect(enemy.rect):
                        enemy.apply_burn(5 + int(level.current_difficulty()), 1.5)

    def update_frost(self, level):
        if any(zone.colliderect(level.player.rect) for zone in self.ice_zones):
            level.player.terrain_friction_multiplier = 0.32

    def update_factory(self, level):
        if self.timer < 3.0:
            return
        self.timer = 0
        turrets = self.turrets[::2] if self.rng.random() < 0.5 else self.turrets[1::2]
        for turret in turrets:
            direction = level.player.pos - turret
            EnemyProjectile(turret, direction, 1, level.resources, level.all_sprites, level.enemy_projectile_sprites)
            level.add_particles(turret, CYAN, 6, 120, 3)

    def update_throne(self, level):
        inside = any(zone.colliderect(level.player.rect) for zone in self.curse_zones)
        if not inside:
            return
        level.player.gold_bonus_multiplier = 1.45
        if self.damage_cooldown <= 0:
            self.damage_cooldown = 1.45
            if level.player.take_damage(1):
                level.on_player_hurt(1)

    def hit_player(self, level, rect, damage):
        if rect.colliderect(level.player.rect) and self.damage_cooldown <= 0:
            self.damage_cooldown = 0.65
            if level.player.take_damage(damage):
                level.on_player_hurt(damage)

    def damage_enemies(self, level, rect, damage, effect_kind):
        for enemy in list(level.enemy_sprites):
            if not rect.colliderect(enemy.rect):
                continue
            killed = enemy.take_damage(damage)
            level.add_hit_feedback(enemy, damage, killed, effect_kind)
            if killed:
                level.kill_enemy(enemy)

    def draw(self, surface):
        if self.chapter_id == "frost":
            for zone in self.ice_zones:
                self.draw_zone(surface, zone, BLUE, 34)
        elif self.chapter_id == "factory":
            for turret in self.turrets:
                pygame.draw.circle(surface, (62, 78, 94), turret, 22)
                pygame.draw.circle(surface, CYAN, turret, 8)
        elif self.chapter_id == "throne":
            for zone in self.curse_zones:
                self.draw_zone(surface, zone, YELLOW, 42)

        for event in self.events:
            if event["kind"] == "minecart":
                rect = pygame.Rect(0, event["y"] - 18, SCREEN_WIDTH, 36)
                color = RED if event["phase"] == "active" else YELLOW
                alpha = 92 if event["phase"] == "active" else 54
                self.draw_zone(surface, rect, color, alpha)
                if event["phase"] == "active":
                    cart = pygame.Rect(0, event["y"] - 16, 86, 32)
                    cart.x = int((1 - event["time"] / 0.55) * (SCREEN_WIDTH + 120)) - 100
                    pygame.draw.rect(surface, (88, 70, 46), cart, border_radius=5)
                    pygame.draw.rect(surface, YELLOW, cart, 2, border_radius=5)
            elif event["kind"] == "lava":
                color = RED if event["phase"] == "active" else YELLOW
                self.draw_zone(surface, event["rect"], color, 78 if event["phase"] == "active" else 46)

    def draw_zone(self, surface, rect, color, alpha):
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((*color[:3], alpha))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, color, rect, 2, border_radius=8)
