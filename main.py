import sys

import pygame

from game.config.settings import *
from game.core.level import Level
from game.systems.display import DisplayManager
from game.systems.input import InputManager
from game.systems.settings_data import load_settings


class Game:
    def __init__(self):
        pygame.init()
        self.settings_data = load_settings()
        self.display = DisplayManager(self.settings_data)
        self.screen = self.display.create_window()
        pygame.display.set_caption("金币冲刺")
        self.set_icon()
        self.clock = pygame.time.Clock()
        self.input_manager = InputManager(self.display, self.settings_data)
        self.level = Level(self.settings_data, self.apply_display_settings, self.input_manager)
        self.level.display_surface = self.display.logical_surface
        self.level.ui.surface = self.display.logical_surface

    def apply_display_settings(self, settings_data):
        self.settings_data = settings_data
        self.screen = self.display.apply_settings(settings_data)
        self.input_manager.refresh_settings(settings_data)
        self.level.display_surface = self.display.logical_surface
        self.level.ui.surface = self.display.logical_surface

    def set_icon(self):
        try:
            pygame.display.set_icon(pygame.image.load(LOGO_FILE))
        except (FileNotFoundError, pygame.error):
            pass

    def run(self):
        while True:
            self.input_manager.begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    self.display.handle_resize(event.size)
                    continue
                normalized_event = self.input_manager.normalize_event(event)
                if normalized_event is not None:
                    self.level.handle_event(normalized_event)

            dt = self.clock.tick(FPS) / 1000
            self.level.run(dt)
            self.display.present()
            pygame.display.update()


if __name__ == "__main__":
    game = Game()
    game.run()
