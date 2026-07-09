import math

import pygame

from game.config.settings import *
from game.systems.effects import Particle


DROP_DEFS = {
    "exp": {"image": "exp", "color": CYAN, "outline": WHITE},
    "gold": {"image": "gold", "color": COIN_COLOR, "outline": COIN_OUTLINE},
    "heart": {"image": "heart", "color": RED, "outline": WHITE},
    "magnet": {"image": "magnet", "color": PURPLE, "outline": WHITE},
}


class Drop(pygame.sprite.Sprite):
    def __init__(self, pos, kind, amount, player, resources, *groups, effect_groups=None):
        super().__init__(*groups)
        self.kind = kind
        self.amount = amount
        self.player = player
        self.resources = resources
        self.effect_groups = effect_groups or ()
        self.pos = pygame.math.Vector2(pos)
        self.float_timer = 0
        self.frame_index = 0
        self.trail_timer = 0

        definition = DROP_DEFS[kind]
        self.frames = resources.load_frames(definition["image"], (DROP_SIZE, DROP_SIZE), self.draw_fallback, DROP_FRAME_COUNT)
        self.image = self.frames[0].copy()
        self.rect = self.image.get_rect(center=pos)

    def draw_fallback(self, size, index=0):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        definition = DROP_DEFS[self.kind]
        center = size[0] // 2
        pulse = 1 if index in (1, 2) else 0
        if self.kind == "heart":
            pygame.draw.circle(surface, definition["color"], (center - 5, center - 3), 7 + pulse)
            pygame.draw.circle(surface, definition["color"], (center + 5, center - 3), 7 + pulse)
            pygame.draw.polygon(surface, definition["color"], [(center - 12, center), (center + 12, center), (center, center + 12 + pulse)])
        elif self.kind == "magnet":
            pygame.draw.arc(surface, definition["color"], (4, 4 + pulse, size[0] - 8, size[1] - 8), math.pi, math.tau, 5)
            pygame.draw.rect(surface, definition["outline"], (3, center, 6, 7))
            pygame.draw.rect(surface, definition["outline"], (size[0] - 9, center, 6, 7))
        else:
            pygame.draw.circle(surface, definition["outline"], (center, center), center - 2)
            pygame.draw.circle(surface, definition["color"], (center, center), center - 5 + pulse)
        return surface

    def update(self, dt):
        definition = DROP_DEFS[self.kind]
        distance = self.player.pos.distance_to(self.pos)
        should_attract = self.player.magnet_timer > 0 or distance <= self.player.pickup_range

        if should_attract and distance > 1:
            direction = (self.player.pos - self.pos).normalize()
            speed = 720 if self.player.magnet_timer > 0 else 430
            self.pos += direction * speed * dt
            self.trail_timer += dt
            if self.effect_groups and self.trail_timer >= 0.045:
                self.trail_timer = 0
                Particle(
                    self.rect.center,
                    -direction * 70,
                    definition["color"],
                    0.18,
                    2,
                    *self.effect_groups,
                )
        else:
            self.float_timer += dt
            self.pos.y += math.sin(self.float_timer * 5) * 8 * dt

        self.frame_index = (self.frame_index + 8 * dt) % len(self.frames)
        self.image = self.frames[int(self.frame_index)].copy()
        self.rect.center = round(self.pos.x), round(self.pos.y)
