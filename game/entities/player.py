import pygame

from game.config.settings import *
from game.systems.upgrades import RUN_UPGRADES, WEAPON_UPGRADES


# 玩家精灵，负责移动、成长属性、拾取半径和受伤状态
class Player(pygame.sprite.Sprite):
    def __init__(self, pos, resources, permanent_upgrades=None, *groups):
        super().__init__(*groups)
        self.resources = resources
        permanent_upgrades = permanent_upgrades or {}

        self.frames = resources.load_frames("player", (PLAYER_SIZE, PLAYER_SIZE), self.draw_fallback, 4)
        self.frame_index = 0
        self.animation_timer = 0
        self.facing_left = False
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

        # 玩家移动方向和精确位置
        self.direction = pygame.math.Vector2()
        self.velocity = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = PLAYER_SPEED + permanent_upgrades.get("move_speed", 0) * 18

        self.max_health = PLAYER_MAX_HEALTH + permanent_upgrades.get("max_health", 0)
        self.health = self.max_health
        self.invincible_timer = 0
        self.flash_timer = 0

        self.damage_multiplier = 1.0 + permanent_upgrades.get("base_damage", 0) * 0.1
        self.cooldown_multiplier = 1.0
        self.gold_multiplier = 1.0 + permanent_upgrades.get("gold_bonus", 0) * 0.15
        self.extra_missiles = 0
        self.pickup_range = PLAYER_PICKUP_RANGE
        self.magnet_timer = 0

        self.level = 1
        self.exp = 0
        self.next_exp = PLAYER_BASE_EXP
        self.run_gold = 0

        self.run_upgrade_levels = {upgrade_id: 0 for upgrade_id in RUN_UPGRADES}
        self.weapons = {weapon_id: 0 for weapon_id in WEAPON_UPGRADES}
        self.weapons["missile"] = 1

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        bob = 1 if index in (1, 2) else 0
        pygame.draw.circle(surface, PLAYER_COLOR, (center, center), center)
        pygame.draw.circle(surface, PLAYER_OUTLINE, (center, center), center, 3)
        pygame.draw.circle(surface, WHITE, (center + 9, center - 8 - bob), 5)
        pygame.draw.rect(surface, (34, 92, 145), (center - 9, center + 8 + bob, 18, 7), border_radius=2)
        return surface

    def input(self):
        keys = pygame.key.get_pressed()

        # 玩家移动方向
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction.x = 1
        else:
            self.direction.x = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.direction.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.direction.y = 1
        else:
            self.direction.y = 0

    def move(self, dt):
        # 斜向移动时保持目标速度一致
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
            self.velocity += self.direction * PLAYER_ACCELERATION * dt
            if self.velocity.magnitude() > self.speed:
                self.velocity.scale_to_length(self.speed)
        elif self.velocity.magnitude() > 0:
            speed = max(0, self.velocity.magnitude() - PLAYER_FRICTION * dt)
            if speed == 0:
                self.velocity.update(0, 0)
            else:
                self.velocity.scale_to_length(speed)

        self.pos.x += self.velocity.x * dt
        self.pos.x = max(self.rect.width / 2, min(SCREEN_WIDTH - self.rect.width / 2, self.pos.x))
        if self.pos.x in (self.rect.width / 2, SCREEN_WIDTH - self.rect.width / 2):
            self.velocity.x = 0
        self.rect.centerx = round(self.pos.x)

        self.pos.y += self.velocity.y * dt
        self.pos.y = max(self.rect.height / 2, min(SCREEN_HEIGHT - self.rect.height / 2, self.pos.y))
        if self.pos.y in (self.rect.height / 2, SCREEN_HEIGHT - self.rect.height / 2):
            self.velocity.y = 0
        self.rect.centery = round(self.pos.y)

    def update_animation(self, dt):
        if self.velocity.x < -10:
            self.facing_left = True
        elif self.velocity.x > 10:
            self.facing_left = False

        speed_ratio = min(1, self.velocity.magnitude() / max(1, self.speed))
        animation_speed = 4 + speed_ratio * 8
        self.frame_index = (self.frame_index + animation_speed * dt) % len(self.frames)
        image = self.frames[int(self.frame_index)].copy()
        if self.facing_left:
            image = pygame.transform.flip(image, True, False)
        if self.flash_timer > 0:
            self.flash_timer = max(0, self.flash_timer - dt)
            image.fill((180, 180, 180, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.image = image

    def get_damage(self, amount):
        return max(1, int(amount * self.damage_multiplier))

    def add_exp(self, amount):
        self.exp += amount
        level_ups = 0
        while self.exp >= self.next_exp:
            self.exp -= self.next_exp
            self.level += 1
            level_ups += 1
            self.next_exp = int(PLAYER_BASE_EXP + self.level * 9 + self.level * self.level * 1.4)
        return level_ups

    def add_gold(self, amount):
        gained = max(0, int(round(amount * self.gold_multiplier)))
        self.run_gold += gained
        return gained

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def activate_magnet(self):
        self.magnet_timer = MAGNET_DURATION

    def upgrade_weapon(self, weapon_id):
        max_level = WEAPON_UPGRADES[weapon_id]["max_level"]
        self.weapons[weapon_id] = min(max_level, self.weapons.get(weapon_id, 0) + 1)

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return False

        self.health = max(0, self.health - amount)
        self.invincible_timer = PLAYER_INVINCIBLE_TIME
        self.flash_timer = 0.1
        return True

    def update_invincible(self, dt):
        if self.invincible_timer <= 0:
            self.image.set_alpha(255)
            return

        self.invincible_timer = max(0, self.invincible_timer - dt)
        alpha = 120 if int(self.invincible_timer * 14) % 2 == 0 else 255
        self.image.set_alpha(alpha)

    def update_magnet(self, dt):
        if self.magnet_timer > 0:
            self.magnet_timer = max(0, self.magnet_timer - dt)

    def update(self, dt):
        self.input()
        self.move(dt)
        self.update_animation(dt)
        self.update_magnet(dt)
        self.update_invincible(dt)
