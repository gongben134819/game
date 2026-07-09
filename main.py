import sys

import pygame

from game.config.settings import *
from game.core.level import Level


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("金币冲刺")
        self.set_icon()
        self.clock = pygame.time.Clock()
        self.level = Level()

    def set_icon(self):
        try:
            pygame.display.set_icon(pygame.image.load(LOGO_FILE))
        except (FileNotFoundError, pygame.error):
            pass

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.level.handle_event(event)

            dt = self.clock.tick(FPS) / 1000
            self.level.run(dt)
            pygame.display.update()


if __name__ == "__main__":
    game = Game()
    game.run()
