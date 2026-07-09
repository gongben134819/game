import os

import pygame

from game.config.settings import IMAGE_DIR, SOUND_DIR


class NullSound:
    def play(self):
        return None


class ResourceManager:
    def __init__(self, image_dir=IMAGE_DIR, sound_dir=SOUND_DIR):
        self.image_dir = image_dir
        self.sound_dir = sound_dir
        self.image_cache = {}
        self.frame_cache = {}
        self.sound_cache = {}
        self.last_sound_times = {}
        self.sound_enabled = self._init_sound()

    def _init_sound(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return True
        except pygame.error:
            return False

    def load_image(self, name, size, fallback_factory):
        key = (name, size)
        if key in self.image_cache:
            return self.image_cache[key].copy()

        path = os.path.join(self.image_dir, f"{name}.png")
        image = None
        if os.path.exists(path):
            try:
                image = pygame.image.load(path).convert_alpha()
                image = pygame.transform.scale(image, size)
            except pygame.error:
                image = None

        if image is None:
            image = fallback_factory(size)

        self.image_cache[key] = image
        return image.copy()

    def load_frames(self, name, size, fallback_factory, frame_count=4):
        key = (name, size, frame_count)
        if key in self.frame_cache:
            return [frame.copy() for frame in self.frame_cache[key]]

        frames = []
        for index in range(frame_count):
            path = os.path.join(self.image_dir, f"{name}_{index}.png")
            image = None
            if os.path.exists(path):
                try:
                    image = pygame.image.load(path).convert_alpha()
                    image = pygame.transform.scale(image, size)
                except pygame.error:
                    image = None

            if image is None:
                image = self._fallback_frame(fallback_factory, size, index)
            frames.append(image)

        self.frame_cache[key] = frames
        return [frame.copy() for frame in frames]

    def _fallback_frame(self, fallback_factory, size, index):
        try:
            return fallback_factory(size, index)
        except TypeError:
            return fallback_factory(size)

    def load_sound(self, name):
        if not self.sound_enabled:
            return NullSound()

        if name in self.sound_cache:
            return self.sound_cache[name]

        path = os.path.join(self.sound_dir, f"{name}.wav")
        if not os.path.exists(path):
            self.sound_cache[name] = NullSound()
            return self.sound_cache[name]

        try:
            self.sound_cache[name] = pygame.mixer.Sound(path)
        except pygame.error:
            self.sound_cache[name] = NullSound()
        return self.sound_cache[name]

    def play(self, name, cooldown=0):
        now = pygame.time.get_ticks() / 1000
        if cooldown > 0 and now - self.last_sound_times.get(name, -999) < cooldown:
            return None

        self.last_sound_times[name] = now
        return self.load_sound(name).play()
