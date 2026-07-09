import sys

import pygame

from game.config.settings import *
from game.core.level import Level
from game.systems.settings_data import load_settings


class Game:
    def __init__(self):
        pygame.init()
        self.settings_data = load_settings()
        self.screen = self.create_screen()
        pygame.display.set_caption("金币冲刺")
        self.set_icon()
        self.clock = pygame.time.Clock()
        self.level = Level(self.settings_data, self.apply_display_settings)

    def create_screen(self):
        flags = pygame.FULLSCREEN if self.settings_data.get("fullscreen", False) else 0
        return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    def apply_display_settings(self, settings_data):
        self.settings_data = settings_data
        self.screen = self.create_screen()
        self.level.display_surface = self.screen
        self.level.ui.surface = self.screen

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
