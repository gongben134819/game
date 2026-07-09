import math

import pygame

from game.config.settings import *
from game.systems.effects import FlashSprite, Shockwave, SlashArc, trail_interval, trail_particle


def nearest_enemy(origin, enemies, max_distance=None, ignore_ids=None):
    closest = None
    closest_distance = max_distance
    ignore_ids = ignore_ids or set()
    for enemy in enemies:
        if not enemy.alive() or id(enemy) in ignore_ids:
            continue
        distance = origin.distance_to(enemy.pos)
        if closest_distance is None or distance < closest_distance:
            closest = enemy
            closest_distance = distance
    return closest


def weapon_evolved(player, weapon_id):
    return weapon_id in getattr(player, "weapon_evolutions", set())


class MagicMissile(pygame.sprite.Sprite):
    def __init__(
        self,
        pos,
        target,
        direction,
        damage,
        resources,
        effect_groups=None,
        enemy_group=None,
        evolved=False,
        hits_remaining=1,
        spawn_groups=(),
        *groups,
    ):
        super().__init__(*groups)
        self.target = target
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.resources = resources
        self.effect_groups = effect_groups or ()
        self.enemy_group = enemy_group
        self.evolved = evolved
        self.hits_remaining = hits_remaining
        self.spawn_groups = spawn_groups
        self.hit_ids = set()
        self.split_done = False
        self.effect_kind = "missile"
        self.lifetime = 3.0 if evolved else 2.8
        self.trail_timer = 0
        self.frame_index = 0
        self.pos = pygame.math.Vector2(pos)
        self.frames = resources.load_frames("magic_missile", (MISSILE_SIZE, MISSILE_SIZE), self.draw_fallback, WEAPON_FRAME_COUNT)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pulse = index % 3
        pygame.draw.circle(surface, (40, 102, 255), (center, center + 2), center - 3)
        pygame.draw.circle(surface, CYAN, (center, center), center - 4 + pulse // 2)
        pygame.draw.circle(surface, WHITE, (center - 3, center - 4), 3)
        pygame.draw.rect(surface, (80, 150, 255), (center - 3, size[1] - 6, 6, 5), border_radius=2)
        return surface

    def can_hit(self, enemy):
        return id(enemy) not in self.hit_ids

    def register_hit(self, enemy):
        self.hit_ids.add(id(enemy))
        if not self.evolved:
            self.kill()
            return

        self.hits_remaining -= 1
        if not self.split_done and self.enemy_group and self.spawn_groups:
            self.split_done = True
            for angle in (-0.42, 0.42):
                target = nearest_enemy(self.pos, self.enemy_group, ignore_ids=self.hit_ids)
                MagicMissile(
                    self.pos,
                    target,
                    self.direction.rotate_rad(angle),
                    max(1, int(self.damage * 0.55)),
                    self.resources,
                    self.effect_groups,
                    self.enemy_group,
                    False,
                    1,
                    (),
                    *self.spawn_groups,
                )

        if self.hits_remaining <= 0:
            self.kill()
            return

        self.target = nearest_enemy(self.pos, self.enemy_group, ignore_ids=self.hit_ids) if self.enemy_group else None

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return

        if (not self.target or not self.target.alive()) and self.enemy_group:
            self.target = nearest_enemy(self.pos, self.enemy_group, ignore_ids=self.hit_ids)

        if self.target and self.target.alive():
            target_direction = self.target.pos - self.pos
            if target_direction.magnitude() != 0:
                turn_rate = 0.16 if self.evolved else 0.12
                self.direction = self.direction.lerp(target_direction.normalize(), turn_rate).normalize()

        self.pos += self.direction * MISSILE_SPEED * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.frame_index = (self.frame_index + 14 * dt) % len(self.frames)
        self.image = self.frames[int(self.frame_index)].copy()

        self.trail_timer += dt
        if self.effect_groups and self.trail_timer >= trail_interval(0.025):
            self.trail_timer = 0
            trail_particle(self.rect.center, -self.direction * 88, CYAN, *self.effect_groups, size=3, lifetime=0.2)

        if not pygame.Rect(-80, -80, SCREEN_WIDTH + 160, SCREEN_HEIGHT + 160).collidepoint(self.rect.center):
            self.kill()


class BladeEcho(pygame.sprite.Sprite):
    def __init__(self, center, damage, image, *groups):
        super().__init__(*groups)
        self.damage = damage
        self.hit_ids = set()
        self.effect_kind = "blade"
        self.lifetime = 0.18
        self.max_lifetime = self.lifetime
        self.base_image = image.copy()
        self.image = image.copy()
        self.image.set_alpha(105)
        self.rect = self.image.get_rect(center=center)

    def can_hit(self, enemy):
        return id(enemy) not in self.hit_ids

    def register_hit(self, enemy):
        self.hit_ids.add(id(enemy))

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.image = self.base_image.copy()
        self.image.set_alpha(int(105 * self.lifetime / self.max_lifetime))


class BladeSprite(pygame.sprite.Sprite):
    def __init__(self, player, slot_index, total_slots, resources, echo_groups=(), visual_groups=(), *groups):
        super().__init__(*groups)
        self.player = player
        self.slot_index = slot_index
        self.total_slots = total_slots
        self.angle = math.tau * slot_index / max(1, total_slots)
        self.hit_timers = {}
        self.damage = 0
        self.effect_kind = "blade"
        self.echo_groups = echo_groups
        self.visual_groups = visual_groups
        self.echo_timer = 0
        self.arc_timer = 0
        self.frame_index = 0
        self.frames = resources.load_frames("blade", (BLADE_SIZE, BLADE_SIZE), self.draw_fallback, WEAPON_FRAME_COUNT)
        self.base_image = self.frames[0].copy()
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=player.rect.center)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        inset = 1 + index % 3
        pygame.draw.polygon(surface, (230, 248, 255), [(center, inset), (size[0] - inset, center), (center, size[1] - inset), (inset, center)])
        pygame.draw.polygon(surface, CYAN, [(center, 6), (size[0] - 9, center), (center, size[1] - 9), (9, center)])
        pygame.draw.circle(surface, WHITE, (center, center), 3)
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
        evolved = weapon_evolved(self.player, "blade")
        self.damage = self.player.get_damage(12 + level * 4 + (8 if evolved else 0))
        radius = 66 + level * 7 + (14 if evolved else 0)
        self.angle += (3.4 + level * 0.3 + (0.6 if evolved else 0)) * dt
        offset = pygame.math.Vector2(math.cos(self.angle), math.sin(self.angle)) * radius
        center = round(self.player.pos.x + offset.x), round(self.player.pos.y + offset.y)
        self.frame_index = (self.frame_index + 12 * dt) % len(self.frames)
        self.base_image = self.frames[int(self.frame_index)]
        self.image = pygame.transform.rotate(self.base_image, -math.degrees(self.angle))
        self.rect = self.image.get_rect(center=center)

        if evolved and self.echo_groups:
            self.echo_timer += dt
            if self.echo_timer >= 0.12:
                self.echo_timer = 0
                BladeEcho(center, max(1, int(self.damage * 0.45)), self.image, *self.echo_groups)

        if self.visual_groups:
            self.arc_timer += dt
            interval = trail_interval(0.15 if evolved else 0.24)
            if self.arc_timer >= interval:
                self.arc_timer = 0
                SlashArc(center, 24 + level * 2, self.angle, CYAN, *self.visual_groups)


class PulseEffect(pygame.sprite.Sprite):
    def __init__(self, pos, radius, color=BLUE, *groups):
        super().__init__(*groups)
        self.radius = radius
        self.color = color
        self.duration = 0.3
        self.timer = self.duration
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        alpha = int(130 * (self.timer / self.duration))
        ratio = 1 - self.timer / self.duration
        pygame.draw.circle(self.image, (*self.color[:3], alpha), (self.radius, self.radius), int(self.radius * (0.65 + 0.35 * ratio)), 3)
        pygame.draw.circle(self.image, (255, 255, 255, alpha // 2), (self.radius, self.radius), int(self.radius * (0.3 + 0.3 * ratio)), 2)

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return
        self.redraw()


class LightningStrike(pygame.sprite.Sprite):
    def __init__(self, enemy, damage, *groups):
        super().__init__(*groups)
        self.target_id = id(enemy)
        self.damage = damage
        self.effect_kind = "pulse"
        self.lifetime = 0.14
        self.image = pygame.Surface((48, 80), pygame.SRCALPHA)
        pygame.draw.line(self.image, WHITE, (26, 0), (16, 36), 4)
        pygame.draw.line(self.image, CYAN, (16, 36), (30, 44), 4)
        pygame.draw.line(self.image, WHITE, (30, 44), (20, 80), 4)
        self.rect = self.image.get_rect(center=enemy.rect.center)

    def can_hit(self, enemy):
        return id(enemy) == self.target_id

    def register_hit(self, enemy):
        self.kill()

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()


class FlameField(pygame.sprite.Sprite):
    def __init__(self, pos, radius, damage, burn_damage, burn_duration, *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.radius = radius
        self.damage = damage
        self.effect_kind = "flame"
        self.burn_damage = burn_damage
        self.burn_duration = burn_duration
        self.hit_timers = {}
        self.lifetime = 1.25
        self.max_lifetime = self.lifetime
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        ratio = max(0, self.lifetime / self.max_lifetime)
        alpha = int(115 * ratio)
        center = (self.radius, self.radius)
        pygame.draw.circle(self.image, (244, 110, 42, alpha), center, self.radius - 2)
        pygame.draw.circle(self.image, (255, 220, 92, alpha), center, max(4, int(self.radius * 0.45)))
        pygame.draw.circle(self.image, (255, 248, 190, alpha), center, self.radius - 4, 2)

    def can_hit(self, enemy):
        return self.hit_timers.get(id(enemy), 0) <= 0

    def register_hit(self, enemy):
        enemy.apply_burn(self.burn_damage, self.burn_duration)
        self.hit_timers[id(enemy)] = 0.45

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        for enemy_id in list(self.hit_timers):
            self.hit_timers[enemy_id] -= dt
            if self.hit_timers[enemy_id] <= 0:
                del self.hit_timers[enemy_id]
        self.redraw()


class FlameOrb(pygame.sprite.Sprite):
    def __init__(self, pos, target, direction, damage, resources, evolved, field_groups=(), effect_groups=(), *groups):
        super().__init__(*groups)
        self.target = target
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.resources = resources
        self.evolved = evolved
        self.field_groups = field_groups
        self.effect_groups = effect_groups
        self.effect_kind = "flame"
        self.lifetime = 2.5
        self.frame_index = 0
        self.trail_timer = 0
        self.pos = pygame.math.Vector2(pos)
        self.frames = resources.load_frames("flame_orb", (FLAME_SIZE, FLAME_SIZE), self.draw_fallback, WEAPON_FRAME_COUNT)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pulse = index % 3
        pygame.draw.circle(surface, (160, 50, 24), (center, center), center - 2)
        pygame.draw.circle(surface, (255, 124, 42), (center, center - 1), center - 5 + pulse)
        pygame.draw.circle(surface, (255, 236, 130), (center - 3, center - 4), 4)
        return surface

    def can_hit(self, enemy):
        return True

    def register_hit(self, enemy):
        self.create_field()
        self.kill()

    def create_field(self):
        radius = 72 if self.evolved else 52
        burn_damage = max(1, int(self.damage * (0.42 if self.evolved else 0.3)))
        burn_duration = 2.6 if self.evolved else 1.8
        FlameField(self.rect.center, radius, max(1, int(self.damage * 0.5)), burn_damage, burn_duration, *self.field_groups)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.create_field()
            self.kill()
            return

        if self.target and self.target.alive():
            target_direction = self.target.pos - self.pos
            if target_direction.magnitude() != 0:
                self.direction = self.direction.lerp(target_direction.normalize(), 0.08).normalize()
        self.pos += self.direction * FLAME_SPEED * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.frame_index = (self.frame_index + 10 * dt) % len(self.frames)
        self.image = self.frames[int(self.frame_index)].copy()

        self.trail_timer += dt
        if self.effect_groups and self.trail_timer >= trail_interval(0.035):
            self.trail_timer = 0
            trail_particle(self.rect.center, -self.direction * 62, (255, 124, 42), *self.effect_groups, size=4, lifetime=0.24, shape="circle")


class FrostShard(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, resources, evolved, effect_groups=(), *groups):
        super().__init__(*groups)
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.evolved = evolved
        self.effect_kind = "frost"
        self.effect_groups = effect_groups
        self.hits_remaining = 3 if evolved else 1
        self.hit_ids = set()
        self.lifetime = 1.8
        self.frame_index = 0
        self.trail_timer = 0
        self.pos = pygame.math.Vector2(pos)
        self.frames = resources.load_frames("frost_shard", (FROST_SIZE, FROST_SIZE), self.draw_fallback, WEAPON_FRAME_COUNT)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pygame.draw.polygon(surface, (210, 248, 255), [(center, 1), (size[0] - 3, center), (center, size[1] - 2), (3, center)])
        pygame.draw.polygon(surface, CYAN, [(center, 5), (size[0] - 7, center), (center, size[1] - 7), (7, center)])
        pygame.draw.rect(surface, WHITE, (center - 2, 4 + index % 3, 4, 5))
        return surface

    def can_hit(self, enemy):
        return id(enemy) not in self.hit_ids

    def register_hit(self, enemy):
        self.hit_ids.add(id(enemy))
        enemy.apply_slow(0.42 if self.evolved else 0.62, 2.5 if self.evolved else 1.6)
        self.hits_remaining -= 1
        if self.hits_remaining <= 0:
            self.kill()

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.pos += self.direction * FROST_SPEED * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.frame_index = (self.frame_index + 13 * dt) % len(self.frames)
        self.image = self.frames[int(self.frame_index)].copy()
        self.trail_timer += dt
        if self.effect_groups and self.trail_timer >= trail_interval(0.045):
            self.trail_timer = 0
            trail_particle(self.rect.center, -self.direction * 48, (170, 238, 255), *self.effect_groups, size=2, lifetime=0.16, shape="diamond")
        if not pygame.Rect(-80, -80, SCREEN_WIDTH + 160, SCREEN_HEIGHT + 160).collidepoint(self.rect.center):
            self.kill()


class DroneSprite(pygame.sprite.Sprite):
    def __init__(self, player, slot_index, total_slots, resources, *groups):
        super().__init__(*groups)
        self.player = player
        self.slot_index = slot_index
        self.total_slots = total_slots
        self.angle = math.tau * slot_index / max(1, total_slots)
        self.frame_index = 0
        self.frames = resources.load_frames("drone", (DRONE_SIZE, DRONE_SIZE), self.draw_fallback, WEAPON_FRAME_COUNT)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=player.rect.center)
        self.pos = pygame.math.Vector2(self.rect.center)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pygame.draw.circle(surface, (86, 64, 34), (center, center), center - 3)
        pygame.draw.circle(surface, YELLOW, (center, center), center - 6)
        pygame.draw.rect(surface, WHITE, (center - 4, 5 + index % 2, 8, 4), border_radius=1)
        pygame.draw.rect(surface, (92, 64, 28), (center - 9, center - 2, 18, 5), border_radius=2)
        return surface

    def update(self, dt):
        self.angle += (2.4 + self.player.weapons.get("drone", 0) * 0.14) * dt
        radius = 82 + self.player.weapons.get("drone", 0) * 4
        slot_offset = math.tau * self.slot_index / max(1, self.total_slots)
        offset = pygame.math.Vector2(math.cos(self.angle + slot_offset), math.sin(self.angle + slot_offset)) * radius
        self.pos.update(self.player.pos.x + offset.x, self.player.pos.y + offset.y)
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.frame_index = (self.frame_index + 9 * dt) % len(self.frames)
        self.image = self.frames[int(self.frame_index)].copy()


class DroneShot(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, resources, effect_groups=(), *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() == 0:
            self.direction = pygame.math.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.effect_kind = "drone"
        self.effect_groups = effect_groups
        self.lifetime = 1.4
        self.trail_timer = 0
        self.image = resources.load_image("drone_shot", (DRONE_PROJECTILE_SIZE, DRONE_PROJECTILE_SIZE), self.draw_fallback)
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = size[0] // 2
        pygame.draw.circle(surface, YELLOW, (center, center), center - 1)
        pygame.draw.circle(surface, WHITE, (center - 2, center - 2), 2)
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
        self.pos += self.direction * DRONE_PROJECTILE_SPEED * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.trail_timer += dt
        if self.effect_groups and self.trail_timer >= trail_interval(0.04):
            self.trail_timer = 0
            trail_particle(self.rect.center, -self.direction * 52, YELLOW, *self.effect_groups, size=2, lifetime=0.14)
        if not pygame.Rect(-80, -80, SCREEN_WIDTH + 160, SCREEN_HEIGHT + 160).collidepoint(self.rect.center):
            self.kill()


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
        evolved = weapon_evolved(self.player, "missile")
        interval = max(0.13 if evolved else 0.16, (0.74 - weapon_level * 0.035) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        target = nearest_enemy(self.player.pos, level.enemy_sprites)
        if target is None:
            return

        self.timer = 0
        missile_count = 1 + self.player.extra_missiles + max(0, (weapon_level - 1) // 3) + (1 if evolved else 0)
        base_direction = target.pos - self.player.pos
        if base_direction.magnitude() == 0:
            base_direction = pygame.math.Vector2(1, 0)

        for index in range(missile_count):
            angle_offset = (index - (missile_count - 1) / 2) * 0.15
            direction = base_direction.rotate_rad(angle_offset)
            damage = self.player.get_damage(12 + weapon_level * 3 + (4 if evolved else 0))
            MagicMissile(
                self.player.pos,
                target,
                direction,
                damage,
                self.resources,
                (level.all_sprites, level.particle_sprites),
                level.enemy_sprites,
                evolved,
                3 if evolved else 1,
                (level.all_sprites, level.attack_sprites),
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
        evolved = weapon_evolved(self.player, "blade")
        desired_count = 0 if weapon_level <= 0 else 1 + (weapon_level - 1) // 2 + (1 if evolved else 0)

        while len(self.blades) < desired_count:
            BladeSprite(
                self.player,
                len(self.blades),
                desired_count,
                self.resources,
                (level.all_sprites, level.attack_sprites),
                (level.all_sprites, level.particle_sprites),
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
        evolved = weapon_evolved(self.player, "pulse")
        interval = max(0.9 if evolved else 1.05, (3.2 - weapon_level * 0.28) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        self.timer = 0
        radius = 130 + weapon_level * 22 + (34 if evolved else 0)
        damage = self.player.get_damage(24 + weapon_level * 11 + (14 if evolved else 0))
        PulseEffect(self.player.rect.center, radius, CYAN if evolved else BLUE, level.all_sprites)
        Shockwave(self.player.rect.center, radius, CYAN if evolved else BLUE, 0.3, 3, level.all_sprites, level.particle_sprites)

        struck = []
        for enemy in list(level.enemy_sprites):
            if self.player.pos.distance_to(enemy.pos) <= radius:
                killed = enemy.take_damage(damage)
                level.add_hit_feedback(enemy, damage, killed, "pulse")
                struck.append(enemy)
                if killed:
                    level.kill_enemy(enemy)

        if evolved:
            for enemy in struck[:5]:
                if enemy.alive():
                    LightningStrike(enemy, self.player.get_damage(18 + weapon_level * 5), level.all_sprites, level.attack_sprites)


class FlameWeapon:
    def __init__(self, player, resources):
        self.player = player
        self.resources = resources
        self.timer = 0

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("flame", 0)
        if weapon_level <= 0:
            return

        self.timer += dt
        evolved = weapon_evolved(self.player, "flame")
        interval = max(0.62, (2.45 - weapon_level * 0.16) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        target = nearest_enemy(self.player.pos, level.enemy_sprites)
        if target is None:
            return

        self.timer = 0
        direction = target.pos - self.player.pos
        damage = self.player.get_damage(24 + weapon_level * 9 + (10 if evolved else 0))
        FlameOrb(
            self.player.pos,
            target,
            direction,
            damage,
            self.resources,
            evolved,
            (level.all_sprites, level.attack_sprites),
            (level.all_sprites, level.particle_sprites),
            level.all_sprites,
            level.attack_sprites,
        )
        level.resources.play("shoot", cooldown=0.08)


class FrostWeapon:
    def __init__(self, player, resources):
        self.player = player
        self.resources = resources
        self.timer = 0

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("frost", 0)
        if weapon_level <= 0:
            return

        self.timer += dt
        evolved = weapon_evolved(self.player, "frost")
        interval = max(0.48, (1.8 - weapon_level * 0.1) * self.player.cooldown_multiplier)
        if self.timer < interval:
            return

        target = nearest_enemy(self.player.pos, level.enemy_sprites)
        if target is None:
            return

        self.timer = 0
        base_direction = target.pos - self.player.pos
        if base_direction.magnitude() == 0:
            base_direction = pygame.math.Vector2(1, 0)
        shard_count = 2 + weapon_level // 2 + (2 if evolved else 0)
        spread = 0.18 if not evolved else 0.24
        for index in range(shard_count):
            offset = (index - (shard_count - 1) / 2) * spread
            damage = self.player.get_damage(10 + weapon_level * 4 + (5 if evolved else 0))
            FrostShard(
                self.player.pos,
                base_direction.rotate_rad(offset),
                damage,
                self.resources,
                evolved,
                (level.all_sprites, level.particle_sprites),
                level.all_sprites,
                level.attack_sprites,
            )
        level.resources.play("shoot", cooldown=0.08)


class DroneWeapon:
    def __init__(self, player, resources):
        self.player = player
        self.resources = resources
        self.drones = pygame.sprite.Group()
        self.timer = 0
        self.volley_timer = 0

    def fire_from(self, pos, target, damage, level):
        direction = target.pos - pygame.math.Vector2(pos)
        if direction.magnitude() == 0:
            direction = pygame.math.Vector2(1, 0)
        DroneShot(pos, direction, damage, self.resources, (level.all_sprites, level.particle_sprites), level.all_sprites, level.attack_sprites)
        FlashSprite(pos, 9, YELLOW, level.all_sprites, level.particle_sprites)

    def update(self, dt, level):
        weapon_level = self.player.weapons.get("drone", 0)
        if weapon_level <= 0:
            while self.drones:
                self.drones.sprites()[-1].kill()
            return

        evolved = weapon_evolved(self.player, "drone")
        desired_count = 1 + (weapon_level - 1) // 2 + (1 if evolved else 0)
        while len(self.drones) < desired_count:
            DroneSprite(self.player, len(self.drones), desired_count, self.resources, self.drones, level.all_sprites)
        while len(self.drones) > desired_count:
            self.drones.sprites()[-1].kill()
        for drone in self.drones:
            drone.total_slots = desired_count

        self.timer += dt
        interval = max(0.24, (0.88 - weapon_level * 0.055) * self.player.cooldown_multiplier)
        if self.timer >= interval:
            self.timer = 0
            for drone in self.drones:
                target = nearest_enemy(drone.pos, level.enemy_sprites, 520)
                if target is not None:
                    damage = self.player.get_damage(8 + weapon_level * 3 + (3 if evolved else 0))
                    self.fire_from(drone.rect.center, target, damage, level)
            level.resources.play("shoot", cooldown=0.08)

        if evolved:
            self.volley_timer += dt
            if self.volley_timer >= 2.2:
                self.volley_timer = 0
                damage = self.player.get_damage(9 + weapon_level * 3)
                for index in range(8):
                    direction = pygame.math.Vector2(1, 0).rotate(index * 45)
                    DroneShot(
                        self.player.rect.center,
                        direction,
                        damage,
                        self.resources,
                        (level.all_sprites, level.particle_sprites),
                        level.all_sprites,
                        level.attack_sprites,
                    )
                Shockwave(self.player.rect.center, 76, YELLOW, 0.24, 2, level.all_sprites, level.particle_sprites)


class WeaponController:
    def __init__(self, player, resources):
        self.weapons = [
            MagicMissileWeapon(player, resources),
            BladeWeapon(player, resources),
            PulseWeapon(player),
            FlameWeapon(player, resources),
            FrostWeapon(player, resources),
            DroneWeapon(player, resources),
        ]

    def update(self, dt, level):
        for weapon in self.weapons:
            weapon.update(dt, level)
