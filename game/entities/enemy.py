import random

import pygame

from game.config.settings import *


ENEMY_TYPES = {
    "grunt": {
        "name": "追踪怪",
        "image": "enemy_grunt",
        "size": 40,
        "health": 32,
        "speed": 92,
        "damage": 1,
        "score": 12,
        "exp": 7,
        "color": ENEMY_COLOR,
        "core": ENEMY_CORE,
    },
    "fast": {
        "name": "迅捷怪",
        "image": "enemy_fast",
        "size": 34,
        "health": 24,
        "speed": 150,
        "damage": 1,
        "score": 16,
        "exp": 8,
        "color": (245, 130, 80),
        "core": (120, 42, 26),
    },
    "tank": {
        "name": "重甲怪",
        "image": "enemy_tank",
        "size": 52,
        "health": 95,
        "speed": 62,
        "damage": 2,
        "score": 35,
        "exp": 14,
        "color": (138, 166, 190),
        "core": (62, 78, 94),
    },
    "ranger": {
        "name": "远程怪",
        "image": "enemy_ranger",
        "size": 38,
        "health": 36,
        "speed": 82,
        "damage": 1,
        "score": 24,
        "exp": 11,
        "color": (150, 100, 240),
        "core": (66, 38, 124),
        "ranged": True,
        "shoot_interval": 2.3,
        "preferred_range": 300,
    },
    "elite": {
        "name": "精英怪",
        "image": "enemy_elite",
        "size": 58,
        "health": 260,
        "speed": 78,
        "damage": 2,
        "score": 110,
        "exp": 32,
        "color": (255, 86, 126),
        "core": (128, 24, 54),
        "elite": True,
    },
    "boss": {
        "name": "金币领主",
        "image": "enemy_boss",
        "size": 104,
        "health": 2300,
        "speed": 58,
        "damage": 2,
        "score": 850,
        "exp": 0,
        "color": (255, 198, 82),
        "core": (145, 77, 34),
        "boss": True,
        "ranged": True,
        "shoot_interval": 1.35,
        "preferred_range": 230,
    },
}


class EnemyProjectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, resources, *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.speed = 245
        self.image = resources.load_image("enemy_projectile", (ENEMY_PROJECTILE_SIZE, ENEMY_PROJECTILE_SIZE), self.draw_fallback)
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pygame.draw.circle(surface, RED, (center, center), center - 1)
        pygame.draw.circle(surface, WHITE, (center - 3, center - 3), 2)
        return surface

    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        if not pygame.Rect(-60, -60, SCREEN_WIDTH + 120, SCREEN_HEIGHT + 120).collidepoint(self.rect.center):
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(
        self,
        pos,
        target,
        kind,
        resources,
        projectile_groups=None,
        difficulty=1.0,
        *groups,
    ):
        super().__init__(*groups)

        self.target = target
        self.kind = kind
        self.resources = resources
        self.definition = ENEMY_TYPES[kind]
        self.projectile_groups = projectile_groups or ()
        self.pos = pygame.math.Vector2(pos)
        self.size = self.definition["size"]

        health_scale = difficulty
        if self.definition.get("boss"):
            health_scale = 1.0
        self.max_health = max(1, int(self.definition["health"] * health_scale))
        self.health = self.max_health
        self.speed = self.definition["speed"] * (0.92 + random.random() * 0.16)
        self.damage = self.definition["damage"]
        self.score_value = self.definition["score"]
        self.exp_value = self.definition["exp"]
        self.is_boss = self.definition.get("boss", False)
        self.is_elite = self.definition.get("elite", False)
        self.shoot_timer = random.random() * self.definition.get("shoot_interval", 1.0)
        self.frame_index = 0
        self.flash_timer = 0

        self.frames = resources.load_frames(self.definition["image"], (self.size, self.size), self.draw_fallback, 4)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        color = self.definition["color"]
        core = self.definition["core"]
        bob = 1 if index in (1, 2) else 0

        if self.kind == "tank":
            pygame.draw.rect(surface, color, (3, 6 + bob, size[0] - 6, size[1] - 12), border_radius=6)
            pygame.draw.rect(surface, core, (12, 14 + bob, size[0] - 24, size[1] - 28), border_radius=4)
        elif self.kind == "boss":
            pygame.draw.rect(surface, color, (8, 14 + bob, size[0] - 16, size[1] - 22), border_radius=10)
            pygame.draw.circle(surface, core, (center, center + bob), center // 2)
            pygame.draw.rect(surface, WHITE, (center - 18, 8 + bob, 36, 8), border_radius=3)
        else:
            points = [(center, 0 + bob), (size[0], center), (center, size[1] - bob), (0, center)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.circle(surface, core, (center, center + bob), max(5, center // 2))

        return surface

    def take_damage(self, amount):
        self.health -= amount
        self.flash_timer = 0.08
        return self.health <= 0

    def update_animation(self, dt):
        self.frame_index = (self.frame_index + (5 if self.is_boss else 7) * dt) % len(self.frames)
        image = self.frames[int(self.frame_index)].copy()
        if self.flash_timer > 0:
            self.flash_timer = max(0, self.flash_timer - dt)
            image.fill((170, 170, 170, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.image = image

    def update_ranged(self, dt):
        if not self.definition.get("ranged"):
            return

        self.shoot_timer += dt
        if self.shoot_timer < self.definition["shoot_interval"]:
            return

        self.shoot_timer = 0
        direction = self.target.pos - self.pos
        if direction.magnitude() == 0:
            return

        EnemyProjectile(
            self.pos,
            direction,
            self.damage,
            self.resources,
            *self.projectile_groups,
        )

    def update(self, dt):
        to_player = self.target.pos - self.pos
        distance = to_player.magnitude()
        direction = pygame.math.Vector2()

        if distance != 0:
            direction = to_player.normalize()

        if self.definition.get("ranged"):
            preferred_range = self.definition.get("preferred_range", 280)
            if distance < preferred_range * 0.62:
                direction *= -1
            elif distance <= preferred_range:
                direction *= 0

        self.pos += direction * self.speed * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.update_ranged(dt)
        self.update_animation(dt)
