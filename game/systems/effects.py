import random

import pygame

from game.config.settings import *


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
    def __init__(self, pos, velocity, color, lifetime, size, *groups):
        super().__init__(*groups)
        self.pos = pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(velocity)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.image = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.redraw()

    def redraw(self):
        self.image.fill((0, 0, 0, 0))
        ratio = max(0, self.lifetime / self.max_lifetime)
        alpha = int(220 * ratio)
        radius = max(1, int(self.size * ratio))
        color = (*self.color[:3], alpha)
        pygame.draw.circle(self.image, color, self.image.get_rect().center, radius)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return

        self.velocity *= 0.92
        self.pos += self.velocity * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
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


def burst_particles(pos, color, all_group, particle_group, count=10, speed=160, size=4):
    for _ in range(count):
        direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if direction.magnitude() == 0:
            direction.update(1, 0)
        direction = direction.normalize()
        velocity = direction * random.uniform(speed * 0.35, speed)
        Particle(
            pos,
            velocity,
            color,
            random.uniform(0.22, 0.52),
            random.randint(2, size),
            all_group,
            particle_group,
        )
    trim_group(particle_group, MAX_PARTICLES)
