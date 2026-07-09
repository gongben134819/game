import math

import pygame

from game.config.settings import *
from game.systems.effects import Particle


def nearest_enemy(origin, enemies, max_distance=None):
    closest = None
    closest_distance = max_distance
    for enemy in enemies:
        if not enemy.alive():
            continue
        distance = origin.distance_to(enemy.pos)
        if closest_distance is None or distance < closest_distance:
            closest = enemy
            closest_distance = distance
    return closest


class MagicMissile(pygame.sprite.Sprite):
    def __init__(self, pos, target, direction, damage, resources, effect_groups=None, *groups):
        super().__init__(*groups)
        self.target = target
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.piercing = False
        self.lifetime = 2.8
        self.trail_timer = 0
        self.effect_groups = effect_groups or ()
        self.pos = pygame.math.Vector2(pos)
        self.image = resources.load_image("magic_missile", (MISSILE_SIZE, MISSILE_SIZE), self.draw_fallback)
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(surface, CYAN, (size[0] // 2, size[1] // 2), size[0] // 2 - 2)
        pygame.draw.circle(surface, WHITE, (size[0] // 2 - 3, size[1] // 2 - 3), 3)
        return surface

    def can_hit(self, enemy):
        return True

    def register_hit(self, enemy):
        self.kill()

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return

        if self.target and self.target.alive():
            target_direction = self.target.pos - self.pos
            if target_direction.magnitude() != 0:
                self.direction = self.direction.lerp(target_direction.normalize(), 0.12)
                self.direction = self.direction.normalize()

        self.pos += self.direction * MISSILE_SPEED * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.trail_timer += dt
        if self.effect_groups and self.trail_timer >= 0.025:
            self.trail_timer = 0
            Particle(
                self.rect.center,
                -self.direction * 70,
                CYAN,
                0.18,
                3,
                *self.effect_groups,
            )

        if not pygame.Rect(-80, -80, SCREEN_WIDTH + 160, SCREEN_HEIGHT + 160).collidepoint(self.rect.center):
            self.kill()


class BladeSprite(pygame.sprite.Sprite):
    def __init__(self, player, slot_index, total_slots, resources, *groups):
        super().__init__(*groups)
        self.player = player
        self.slot_index = slot_index
        self.total_slots = total_slots
        self.angle = math.tau * slot_index / max(1, total_slots)
        self.hit_timers = {}
        self.damage = 0
        self.piercing = True
        self.base_image = resources.load_image("blade", (BLADE_SIZE, BLADE_SIZE), self.draw_fallback)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=player.rect.center)

    def draw_fallback(self, size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        points = [(size[0] // 2, 0), (size[0] - 4, size[1] // 2), (size[0] // 2, size[1] - 4), (4, size[1] // 2)]
        pygame.draw.polygon(surface, WHITE, points)
        pygame.draw.polygon(surface, CYAN, [(size[0] // 2, 5), (size[0] - 9, size[1] // 2), (size[0] // 2, size[1] - 9), (9, size[1] // 2)])
        return surface

    def can_hit(self, enemy):
        return self.hit_timers.get(id(enemy), 0) <= 0

    def register_hit(self, enemy):
        self.hit_timers[id(enemy)] = 0.34

    def update(self, dt):
        for enemy_id in list(self.hit_timers):
            self.hit_timers[enemy_id] -= dt
            if self.hit_timers[enemy_id] <= 0:
                del self.hit_timers[enemy_id]

        level = self.player.weapons.get("blade", 0)
        self.damage = self.player.get_damage(10 + level * 4)
        radius = 66 + level * 7
        self.angle += (3.4 + level * 0.3) * dt
        offset = pygame.math.Vector2(math.cos(self.angle), math.sin(self.angle)) * radius
        center = round(self.player.pos.x + offset.x), round(self.player.pos.y + offset.y)
        self.image = pygame.transform.rotate(self.base_image, -math.degrees(self.angle))
        self.rect = self.image.get_rect(center=center)


class PulseEffect(pygame.sprite.Sprite):
    def __init__(self, pos, radius, *groups):
        super().__init__(*groups)
        self.radius = radius
        self.duration = 0.28
        self.timer = self.duration
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        alpha = int(120 * (self.timer / self.duration))
        ratio = 1 - self.timer / self.duration
        pygame.draw.circle(self.image, (120, 190, 255, alpha), (self.radius, self.radius), int(self.radius * (0.65 + 0.35 * ratio)), 3)
        pygame.draw.circle(self.image, (255, 255, 255, alpha // 2), (self.radius, self.radius), int(self.radius * (0.3 + 0.3 * ratio)), 2)

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return
        self.redraw()


class MagicMissileWeapon:
    def __init__(self, player, resources):
        self.player = player
        self.resources = resources
        self.timer = 0

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("missile", 0)
        if weapon_level <= 0:
            return

        self.timer += dt
        interval = max(0.16, (0.74 - weapon_level * 0.035) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        target = nearest_enemy(self.player.pos, level.enemy_sprites)
        if target is None:
            return

        self.timer = 0
        missile_count = 1 + self.player.extra_missiles + max(0, (weapon_level - 1) // 3)
        base_direction = target.pos - self.player.pos
        if base_direction.magnitude() == 0:
            base_direction = pygame.math.Vector2(1, 0)

        for index in range(missile_count):
            angle_offset = (index - (missile_count - 1) / 2) * 0.15
            direction = base_direction.rotate_rad(angle_offset)
            damage = self.player.get_damage(12 + weapon_level * 3)
            MagicMissile(
                self.player.pos,
                target,
                direction,
                damage,
                self.resources,
                (level.all_sprites, level.particle_sprites),
                level.all_sprites,
                level.attack_sprites,
            )
        level.resources.play("shoot", cooldown=0.06)


class BladeWeapon:
    def __init__(self, player, resources):
        self.player = player
        self.resources = resources
        self.blades = pygame.sprite.Group()

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("blade", 0)
        desired_count = 0 if weapon_level <= 0 else 1 + (weapon_level - 1) // 2

        while len(self.blades) < desired_count:
            BladeSprite(
                self.player,
                len(self.blades),
                desired_count,
                self.resources,
                self.blades,
                level.all_sprites,
                level.attack_sprites,
            )

        while len(self.blades) > desired_count:
            self.blades.sprites()[-1].kill()

        for blade in self.blades:
            blade.total_slots = max(1, desired_count)


class PulseWeapon:
    def __init__(self, player):
        self.player = player
        self.timer = 0

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("pulse", 0)
        if weapon_level <= 0:
            return

        self.timer += dt
        interval = max(1.05, (3.2 - weapon_level * 0.28) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        self.timer = 0
        radius = 130 + weapon_level * 22
        damage = self.player.get_damage(24 + weapon_level * 11)
        PulseEffect(self.player.rect.center, radius, level.all_sprites)

        for enemy in list(level.enemy_sprites):
            if self.player.pos.distance_to(enemy.pos) <= radius and enemy.take_damage(damage):
                level.kill_enemy(enemy)


class WeaponController:
    def __init__(self, player, resources):
        self.weapons = [
            MagicMissileWeapon(player, resources),
            BladeWeapon(player, resources),
            PulseWeapon(player),
        ]

    def update(self, dt, level):
        for weapon in self.weapons:
            weapon.update(dt, level)
