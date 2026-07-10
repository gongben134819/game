import pygame

from game.config.settings import *
from game.systems.characters import DEFAULT_CHARACTER_ID, get_character
from game.systems.upgrades import RUN_UPGRADES, WEAPON_UPGRADES


class Player(pygame.sprite.Sprite):
    """玩家精灵，负责移动、成长属性、拾取范围和受击状态。"""

    def __init__(
        self,
        pos,
        resources,
        permanent_upgrades=None,
        input_manager=None,
        *groups,
        character_id=DEFAULT_CHARACTER_ID,
        unlocked_weapons=None,
        item_levels=None,
    ):
        super().__init__(*groups)
        self.resources = resources
        self.input_manager = input_manager
        permanent_upgrades = permanent_upgrades or {}
        self.character_id = character_id
        self.character = get_character(character_id)
        self.unlocked_weapons = set(unlocked_weapons or WEAPON_UPGRADES)
        self.item_levels = item_levels or {}

        self.frames = resources.load_frames("player", (PLAYER_SIZE, PLAYER_SIZE), self.draw_fallback, PLAYER_FRAME_COUNT)
        self.frame_index = 0
        self.animation_timer = 0
        self.facing_left = False
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

        self.direction = pygame.math.Vector2()
        self.velocity = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = (PLAYER_SPEED + permanent_upgrades.get("move_speed", 0) * 18) * self.character.speed_multiplier
        self.terrain_friction_multiplier = 1.0

        base_health = PLAYER_MAX_HEALTH + permanent_upgrades.get("max_health", 0)
        self.max_health = max(1, int(round(base_health * self.character.health_multiplier)))
        self.health = self.max_health
        self.invincible_timer = 0
        self.flash_timer = 0

        self.damage_multiplier = (1.0 + permanent_upgrades.get("base_damage", 0) * 0.1) * self.character.damage_multiplier
        self.cooldown_multiplier = 1.0
        if self.character_id == "witch":
            self.cooldown_multiplier *= 0.94
        elif self.character_id == "engineer":
            self.cooldown_multiplier *= 0.92
        self.temporary_cooldown_factor = 1.0
        self.gold_multiplier = (
            (1.0 + permanent_upgrades.get("gold_bonus", 0) * 0.15)
            * self.character.gold_multiplier
            * (1.0 + self.item_levels.get("gold_dice", 0) * 0.06)
        )
        self.gold_bonus_multiplier = 1.0
        self.exp_multiplier = 1.0 + self.item_levels.get("exp_charm", 0) * 0.08
        self.boss_damage_multiplier = 1.0 + self.item_levels.get("boss_hunter", 0) * 0.12
        self.blueprint_bonus = self.item_levels.get("blueprint_radar", 0)
        self.extra_missiles = 0
        self.pickup_range = PLAYER_PICKUP_RANGE * self.character.pickup_multiplier
        self.magnet_timer = 0
        if self.item_levels.get("starter_magnet", 0) > 0:
            self.magnet_timer = 2.0 + self.item_levels["starter_magnet"] * 1.5

        self.level = 1
        self.exp = 0
        self.next_exp = PLAYER_BASE_EXP
        self.run_gold = 0

        self.run_upgrade_levels = {upgrade_id: 0 for upgrade_id in RUN_UPGRADES}
        self.weapons = {weapon_id: 0 for weapon_id in WEAPON_UPGRADES}
        initial_weapon = self.character.initial_weapon if self.character.initial_weapon in self.unlocked_weapons else "missile"
        self.weapons[initial_weapon] = 1
        self.weapon_evolutions = set()

        self.active_cooldown = self.character.active_cooldown
        self.active_timer = 0
        self.active_buff_timer = 0
        self.revive_charges = 1 if self.item_levels.get("revive_charm", 0) > 0 else 0
        self.revive_ratio = min(0.8, 0.35 + self.item_levels.get("revive_charm", 0) * 0.15)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        bob = [0, -1, -2, -1, 0, 1, 2, 1][index % PLAYER_FRAME_COUNT]
        step = 2 if index % 4 in (1, 2) else -1
        color = self.character.color
        pygame.draw.ellipse(surface, (18, 28, 48, 150), (9, 38, 30, 6))
        pygame.draw.polygon(surface, (28, 62, 112), [(12, 18 + bob), (36, 18 + bob), (39, 39), (9, 39)])
        pygame.draw.rect(surface, color, (15, 14 + bob, 18, 24), border_radius=4)
        pygame.draw.rect(surface, (32, 112, 196), (15, 30 + bob, 18, 8), border_radius=2)
        pygame.draw.circle(surface, PLAYER_OUTLINE, (24, 9 + bob), 8)
        pygame.draw.rect(surface, WHITE, (27, 8 + bob, 5, 4), border_radius=1)
        pygame.draw.rect(surface, (95, 210, 255), (10, 22 + bob, 6, 12), border_radius=2)
        pygame.draw.rect(surface, (236, 248, 255), (33, 21 + bob, 8, 4), border_radius=2)
        pygame.draw.rect(surface, (20, 42, 70), (14, 38 + step, 7, 5), border_radius=2)
        pygame.draw.rect(surface, (20, 42, 70), (28, 38 - step, 7, 5), border_radius=2)
        return surface

    def input(self):
        if self.input_manager:
            self.direction = self.input_manager.movement_vector()
            return

        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.direction.y = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])

    def move(self, dt):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
            self.velocity += self.direction * PLAYER_ACCELERATION * dt
            if self.velocity.magnitude() > self.speed:
                self.velocity.scale_to_length(self.speed)
        elif self.velocity.magnitude() > 0:
            friction = PLAYER_FRICTION * self.terrain_friction_multiplier
            speed = max(0, self.velocity.magnitude() - friction * dt)
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

    def cooldown_scale(self):
        return self.cooldown_multiplier * self.temporary_cooldown_factor

    def add_exp(self, amount):
        self.exp += max(1, int(round(amount * self.exp_multiplier)))
        level_ups = 0
        while self.exp >= self.next_exp:
            self.exp -= self.next_exp
            self.level += 1
            level_ups += 1
            self.next_exp = int(PLAYER_BASE_EXP + self.level * 9 + self.level * self.level * 1.4)
        return level_ups

    def add_gold(self, amount):
        gained = max(0, int(round(amount * self.gold_multiplier * self.gold_bonus_multiplier)))
        self.run_gold += gained
        return gained

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def activate_magnet(self):
        self.magnet_timer = MAGNET_DURATION

    def upgrade_weapon(self, weapon_id):
        max_level = WEAPON_UPGRADES[weapon_id]["max_level"]
        self.weapons[weapon_id] = min(max_level, self.weapons.get(weapon_id, 0) + 1)

    def evolve_weapon(self, weapon_id):
        if weapon_id in WEAPON_UPGRADES:
            self.weapon_evolutions.add(weapon_id)

    def skill_ready(self):
        return self.active_timer <= 0

    def trigger_active_cooldown(self):
        self.active_timer = self.active_cooldown

    def active_cooldown_ratio(self):
        if self.active_cooldown <= 0:
            return 0
        return max(0, min(1, self.active_timer / self.active_cooldown))

    def try_revive(self):
        if self.health > 0 or self.revive_charges <= 0:
            return False
        self.revive_charges -= 1
        self.health = max(1, int(round(self.max_health * self.revive_ratio)))
        self.invincible_timer = max(self.invincible_timer, 2.0)
        self.flash_timer = 0.2
        return True

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

    def update_active_skill(self, dt):
        if self.active_timer > 0:
            self.active_timer = max(0, self.active_timer - dt)
        if self.active_buff_timer > 0:
            self.active_buff_timer = max(0, self.active_buff_timer - dt)
            self.temporary_cooldown_factor = 0.55
        else:
            self.temporary_cooldown_factor = 1.0

    def update(self, dt):
        self.input()
        self.move(dt)
        self.update_animation(dt)
        self.update_magnet(dt)
        self.update_active_skill(dt)
        self.update_invincible(dt)
