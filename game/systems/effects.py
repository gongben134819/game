import math
import random

import pygame

from game.config.settings import *


EFFECT_COLORS = {
    "default": WHITE,
    "missile": CYAN,
    "blade": (220, 248, 255),
    "pulse": BLUE,
    "flame": (255, 128, 48),
    "frost": (170, 238, 255),
    "drone": YELLOW,
    "burn": (255, 112, 42),
    "slow": (142, 226, 255),
    "gold": YELLOW,
}

runtime_settings = {}


def set_runtime_settings(settings_data):
    global runtime_settings
    runtime_settings = settings_data or {}


def effect_preset():
    quality = runtime_settings.get("effect_quality", EFFECT_QUALITY)
    return EFFECT_QUALITY_PRESETS.get(quality, EFFECT_QUALITY_PRESETS["medium"])


def scaled_count(count):
    return max(1, int(round(count * effect_preset()["particle_multiplier"])))


def trail_interval(base_interval):
    return base_interval * effect_preset()["trail_interval_scale"]


def particle_budget():
    return effect_preset()["max_particles"]


class ScreenShake:
    def __init__(self):
        self.amount = 0
        self.offset = pygame.math.Vector2()

    def add(self, amount):
        self.amount = min(18, max(self.amount, amount))

    def update(self, dt):
        if self.amount <= 0:
            self.amount = 0
            self.offset.update(0, 0)
            return

        self.amount = max(0, self.amount - SHAKE_DECAY * dt)
        self.offset.update(
            random.uniform(-self.amount, self.amount),
            random.uniform(-self.amount, self.amount),
        )


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, velocity, color, lifetime, size, *groups, shape="circle", stretch=1.0):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(velocity)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.shape = shape
        self.stretch = max(1.0, stretch)
        width = int(size * 2 * self.stretch + 4)
        height = int(size * 2 + 4)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        ratio = max(0, self.lifetime / self.max_lifetime)
        alpha = int(230 * ratio)
        radius = max(1, int(self.size * ratio))
        color = (*self.color[:3], alpha)
        rect = self.image.get_rect()
        if self.shape == "spark":
            pygame.draw.line(self.image, color, (rect.centerx - radius * self.stretch, rect.centery), (rect.centerx + radius * self.stretch, rect.centery), max(1, radius))
            pygame.draw.circle(self.image, (*WHITE, alpha // 2), rect.center, max(1, radius // 2))
        elif self.shape == "diamond":
            cx, cy = rect.center
            pygame.draw.polygon(self.image, color, [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)])
        else:
            pygame.draw.circle(self.image, color, rect.center, radius)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return

        self.velocity *= 0.92
        self.pos += self.velocity * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.redraw()


class Shockwave(pygame.sprite.Sprite):
    def __init__(self, pos, radius, color, lifetime=0.32, width=3, *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.radius = radius
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.width = width
        size = radius * 2 + 8
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        progress = 1 - self.lifetime / self.max_lifetime
        alpha = int(effect_preset()["shockwave_alpha"] * (1 - progress))
        radius = max(2, int(self.radius * (0.2 + 0.8 * progress)))
        center = self.image.get_rect().center
        pygame.draw.circle(self.image, (*self.color[:3], alpha), center, radius, self.width)
        pygame.draw.circle(self.image, (*WHITE, alpha // 3), center, max(1, radius // 2), 1)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.redraw()


class SlashArc(pygame.sprite.Sprite):
    def __init__(self, pos, radius, angle, color, *groups):
        super().__init__(*groups)
        self.lifetime = 0.18
        self.max_lifetime = self.lifetime
        self.radius = radius
        self.angle = angle
        self.color = color
        size = radius * 2 + 10
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        alpha = int(190 * self.lifetime / self.max_lifetime)
        rect = pygame.Rect(5, 5, self.radius * 2, self.radius * 2)
        start = self.angle - 0.75
        end = self.angle + 0.75
        pygame.draw.arc(self.image, (*self.color[:3], alpha), rect, start, end, 5)
        pygame.draw.arc(self.image, (*WHITE, alpha // 2), rect.inflate(-8, -8), start + 0.1, end - 0.1, 2)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.redraw()


class FlashSprite(pygame.sprite.Sprite):
    def __init__(self, pos, radius, color, *groups):
        super().__init__(*groups)
        self.lifetime = 0.12
        self.max_lifetime = self.lifetime
        self.radius = radius
        self.color = color
        size = radius * 2 + 4
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        alpha = int(180 * self.lifetime / self.max_lifetime)
        center = self.image.get_rect().center
        pygame.draw.circle(self.image, (*self.color[:3], alpha), center, self.radius)
        pygame.draw.circle(self.image, (*WHITE, alpha), center, max(2, self.radius // 3))

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.redraw()


class FloatingText(pygame.sprite.Sprite):
    def __init__(self, pos, text, font, color, *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(random.uniform(-12, 12), -54)
        self.lifetime = 0.78
        self.max_lifetime = self.lifetime
        self.font = font
        self.text = text
        self.color = color
        self.image = self.font.render(self.text, True, self.color)
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return

        self.velocity.y += 28 * dt
        self.pos += self.velocity * dt
        ratio = max(0, self.lifetime / self.max_lifetime)
        self.image = self.font.render(self.text, True, self.color)
        self.image.set_alpha(int(255 * ratio))
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))


def trim_group(group, max_count):
    while len(group) > max_count:
        group.sprites()[0].kill()


def random_direction():
    direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
    if direction.magnitude() == 0:
        direction.update(1, 0)
    return direction.normalize()


def burst_particles(pos, color, all_group, particle_group, count=10, speed=160, size=4, shape="circle"):
    for _ in range(scaled_count(count)):
        direction = random_direction()
        velocity = direction * random.uniform(speed * 0.35, speed)
        Particle(
            pos,
            velocity,
            color,
            random.uniform(0.22, 0.52),
            random.randint(2, size),
            all_group,
            particle_group,
            shape=shape,
            stretch=1.7 if shape == "spark" else 1.0,
        )
    trim_group(particle_group, particle_budget())


def trail_particle(pos, velocity, color, all_group, particle_group, size=3, lifetime=0.18, shape="spark"):
    Particle(pos, velocity, color, lifetime, size, all_group, particle_group, shape=shape, stretch=2.2)
    trim_group(particle_group, particle_budget())


def impact_effect(pos, kind, all_group, particle_group, killed=False):
    color = EFFECT_COLORS.get(kind, EFFECT_COLORS["default"])
    count = 14 if killed else 7
    speed = 210 if killed else 145
    shape = "diamond" if kind == "frost" else "spark" if kind in ("missile", "blade", "pulse", "drone") else "circle"
    burst_particles(pos, color, all_group, particle_group, count, speed, 5 if killed else 4, shape)
    if kind == "blade":
        SlashArc(pos, 24 if not killed else 32, random.uniform(0, math.tau), color, all_group, particle_group)
    elif kind in ("pulse", "flame", "frost") or killed:
        Shockwave(pos, 34 if killed else 24, color, 0.25, 2, all_group, particle_group)
    else:
        FlashSprite(pos, 12 if killed else 8, color, all_group, particle_group)
    trim_group(particle_group, particle_budget())


def death_effect(pos, color, all_group, particle_group, boss=False):
    burst_particles(pos, color, all_group, particle_group, 46 if boss else 18, 320 if boss else 210, 7 if boss else 5, "spark")
    Shockwave(pos, 86 if boss else 42, color, 0.42 if boss else 0.28, 4 if boss else 3, all_group, particle_group)
    FlashSprite(pos, 34 if boss else 18, WHITE, all_group, particle_group)
    trim_group(particle_group, particle_budget())


def status_aura(pos, kind, all_group, particle_group):
    color = EFFECT_COLORS.get(kind, EFFECT_COLORS["default"])
    velocity = pygame.math.Vector2(random.uniform(-18, 18), random.uniform(-46, -16))
    Particle(pos, velocity, color, 0.32, 3, all_group, particle_group, shape="diamond" if kind == "slow" else "circle")
    trim_group(particle_group, particle_budget())
