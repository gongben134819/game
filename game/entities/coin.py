import pygame

from game.config.settings import *


class Coin(pygame.sprite.Sprite):
    def __init__(self, pos, *groups):
        super().__init__(*groups)

        self.image = pygame.Surface((COIN_SIZE, COIN_SIZE), pygame.SRCALPHA)
        center = COIN_SIZE // 2
        pygame.draw.circle(self.image, COIN_OUTLINE, (center, center), center)
        pygame.draw.circle(self.image, COIN_COLOR, (center, center), center - 3)
        pygame.draw.circle(self.image, WHITE, (center - 4, center - 4), 3)

        self.rect = self.image.get_rect(center=pos)
        self.value = COIN_VALUE
