import pygame

from game.config.settings import SCREEN_HEIGHT, SCREEN_WIDTH


LOGICAL_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOW_SIZE_OPTIONS = ((1280, 720), (1600, 900), (1920, 1080))


def normalize_window_size(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        width, height = value
        if isinstance(width, (int, float)) and isinstance(height, (int, float)):
            size = int(width), int(height)
            if size in WINDOW_SIZE_OPTIONS:
                return size
    return WINDOW_SIZE_OPTIONS[0]


class DisplayManager:
    def __init__(self, settings_data):
        self.settings_data = settings_data or {}
        self.logical_surface = pygame.Surface(LOGICAL_SIZE)
        self.window_surface = None
        self.scale = 1.0
        self.offset = pygame.math.Vector2()
        self.viewport = pygame.Rect(0, 0, *LOGICAL_SIZE)

    def create_window(self):
        mode = self.settings_data.get("display_mode", "fullscreen" if self.settings_data.get("fullscreen") else "windowed")
        flags = pygame.FULLSCREEN if mode == "fullscreen" else pygame.RESIZABLE
        size = normalize_window_size(self.settings_data.get("window_size", LOGICAL_SIZE))
        if mode == "fullscreen":
            info = pygame.display.Info()
            size = (max(SCREEN_WIDTH, info.current_w), max(SCREEN_HEIGHT, info.current_h))
        self.window_surface = pygame.display.set_mode(size, flags)
        self.update_viewport()
        return self.window_surface

    def apply_settings(self, settings_data):
        self.settings_data = settings_data or {}
        return self.create_window()

    def handle_resize(self, size):
        if self.window_surface is None:
            return
        mode = self.settings_data.get("display_mode", "windowed")
        if mode == "fullscreen":
            return
        width, height = max(1, int(size[0])), max(1, int(size[1]))
        self.window_surface = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.update_viewport()

    def update_viewport(self):
        if self.window_surface is None:
            return
        width, height = self.window_surface.get_size()
        self.scale = min(width / SCREEN_WIDTH, height / SCREEN_HEIGHT)
        scaled_width = max(1, int(SCREEN_WIDTH * self.scale))
        scaled_height = max(1, int(SCREEN_HEIGHT * self.scale))
        self.offset.update((width - scaled_width) // 2, (height - scaled_height) // 2)
        self.viewport = pygame.Rect(int(self.offset.x), int(self.offset.y), scaled_width, scaled_height)

    def to_logical(self, pos):
        if self.scale <= 0:
            return None
        x, y = pos
        if not self.viewport.collidepoint(x, y):
            return None
        logical_x = (x - self.offset.x) / self.scale
        logical_y = (y - self.offset.y) / self.scale
        return int(logical_x), int(logical_y)

    def to_window(self, pos):
        x, y = pos
        return int(x * self.scale + self.offset.x), int(y * self.scale + self.offset.y)

    def present(self):
        if self.window_surface is None:
            return
        self.window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(self.logical_surface, self.viewport.size)
        self.window_surface.blit(scaled, self.viewport.topleft)
