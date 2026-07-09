import math
import os
import random
import struct
import wave

import pygame

from game.config.settings import IMAGE_DIR, SOUND_DIR


def ensure_dirs():
    os.makedirs(IMAGE_DIR, exist_ok=True)
    os.makedirs(SOUND_DIR, exist_ok=True)


def save_surface(name, surface):
    pygame.image.save(surface, os.path.join(IMAGE_DIR, f"{name}.png"))


def save_frames(name, frames):
    for index, frame in enumerate(frames):
        save_surface(f"{name}_{index}", frame)
    save_surface(name, frames[0])


def pixel_surface(size=(32, 32)):
    return pygame.Surface(size, pygame.SRCALPHA)


def draw_player(index=0):
    surface = pixel_surface((48, 48))
    bob = [0, -1, 0, 1][index % 4]
    pygame.draw.rect(surface, (20, 42, 70), (12, 34 + bob, 24, 7))
    pygame.draw.rect(surface, (30, 80, 130), (11, 15 + bob, 26, 24))
    pygame.draw.rect(surface, (88, 178, 255), (14, 9 + bob, 20, 29))
    pygame.draw.rect(surface, (40, 116, 190), (14, 30 + bob, 20, 8))
    pygame.draw.rect(surface, (216, 238, 255), (20, 4 + bob, 8, 8))
    pygame.draw.rect(surface, (255, 255, 255), (28, 14 + bob, 6, 6))
    pygame.draw.rect(surface, (121, 221, 255), (16, 14 + bob, 4, 10))
    pygame.draw.rect(surface, (19, 35, 58), (8, 38 + bob, 32, 5))
    return surface


def draw_diamond(size, color, core, index=0):
    surface = pixel_surface((size, size))
    center = size // 2
    bob = [0, 1, 0, -1][index % 4]
    pygame.draw.polygon(surface, (40, 20, 24, 120), [(center, size - 7), (size - 5, center + 5), (center, size - 1), (5, center + 5)])
    pygame.draw.polygon(surface, color, [(center, 2 + bob), (size - 2, center), (center, size - 2 - bob), (2, center)])
    pygame.draw.polygon(surface, tuple(min(255, c + 35) for c in color), [(center, 5 + bob), (size - 8, center), (center, center + 4)])
    pygame.draw.rect(surface, core, (center - 6, center - 6 + bob, 12, 12))
    pygame.draw.rect(surface, (255, 255, 255), (center - 4, center - 12 + bob, 8, 4))
    return surface


def draw_tank(index=0):
    surface = pixel_surface((52, 52))
    bob = [0, 0, 1, 0][index % 4]
    pygame.draw.rect(surface, (30, 36, 46, 140), (8, 40, 36, 5))
    pygame.draw.rect(surface, (132, 162, 188), (6, 10 + bob, 40, 32))
    pygame.draw.rect(surface, (88, 112, 138), (8, 28 + bob, 36, 10))
    pygame.draw.rect(surface, (62, 78, 94), (14, 18 + bob, 24, 16))
    pygame.draw.rect(surface, (220, 234, 244), (18, 8 + bob, 16, 6))
    return surface


def draw_boss(index=0):
    surface = pixel_surface((96, 96))
    bob = [0, -1, 0, 1][index % 4]
    pygame.draw.rect(surface, (50, 34, 22, 140), (18, 78, 60, 7))
    pygame.draw.rect(surface, (255, 198, 82), (14, 20 + bob, 68, 58))
    pygame.draw.rect(surface, (205, 124, 48), (14, 58 + bob, 68, 20))
    pygame.draw.rect(surface, (145, 77, 34), (28, 34 + bob, 40, 30))
    pygame.draw.rect(surface, (255, 244, 186), (34, 12 + bob, 28, 10))
    pygame.draw.rect(surface, (255, 255, 255), (32, 40 + bob, 8, 8))
    pygame.draw.rect(surface, (255, 255, 255), (56, 40 + bob, 8, 8))
    pygame.draw.rect(surface, (82, 38, 18), (38, 58 + bob, 20, 6))
    return surface


def draw_drop(kind, index=0):
    surface = pixel_surface((24, 24))
    pulse = [0, 1, 2, 1][index % 4]
    if kind == "gold":
        pygame.draw.rect(surface, (255, 236, 145), (4, 4, 16, 16))
        pygame.draw.rect(surface, (244, 190, 62), (6, 6, 12, 12 + pulse // 2))
        pygame.draw.rect(surface, (255, 255, 255), (8, 6, 4, 4))
    elif kind == "exp":
        pygame.draw.polygon(surface, (91, 217, 235), [(12, 2 - pulse // 2), (21, 12), (12, 22 + pulse // 2), (3, 12)])
        pygame.draw.rect(surface, (255, 255, 255), (10, 7, 4, 4))
    elif kind == "heart":
        pygame.draw.rect(surface, (232, 76, 76), (6, 7, 12, 10 + pulse // 2))
        pygame.draw.rect(surface, (232, 76, 76), (8, 5, 4, 4))
        pygame.draw.rect(surface, (232, 76, 76), (14, 5, 4, 4))
        pygame.draw.rect(surface, (255, 255, 255), (8, 7, 3, 3))
    elif kind == "magnet":
        pygame.draw.rect(surface, (168, 116, 255), (5, 4, 5, 15))
        pygame.draw.rect(surface, (168, 116, 255), (14, 4, 5, 15))
        pygame.draw.rect(surface, (168, 116, 255), (8, 14, 8, 5))
        pygame.draw.rect(surface, (255, 255, 255), (5, 4, 5, 4))
        pygame.draw.rect(surface, (255, 255, 255), (14, 4, 5, 4))
    return surface


def draw_projectile(kind):
    surface = pixel_surface((24, 24))
    if kind == "magic_missile":
        pygame.draw.rect(surface, (91, 217, 235), (8, 4, 8, 16))
        pygame.draw.rect(surface, (255, 255, 255), (10, 5, 4, 5))
        pygame.draw.rect(surface, (70, 120, 255), (6, 14, 12, 5))
    elif kind == "blade":
        pygame.draw.polygon(surface, (255, 255, 255), [(12, 1), (23, 12), (12, 23), (1, 12)])
        pygame.draw.polygon(surface, (91, 217, 235), [(12, 5), (19, 12), (12, 19), (5, 12)])
    elif kind == "enemy_projectile":
        pygame.draw.rect(surface, (232, 76, 76), (6, 6, 12, 12))
        pygame.draw.rect(surface, (255, 255, 255), (8, 7, 4, 4))
    return surface


def write_tone(name, frequency, duration=0.13, volume=0.35, slide=0):
    sample_rate = 44100
    frame_count = int(sample_rate * duration)
    path = os.path.join(SOUND_DIR, f"{name}.wav")
    with wave.open(path, "w") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(sample_rate)
        frames = []
        for index in range(frame_count):
            t = index / sample_rate
            current_frequency = frequency + slide * (index / max(1, frame_count - 1))
            progress = index / frame_count
            envelope = (1 - progress) ** 1.8
            harmonic = math.sin(math.tau * current_frequency * 2.01 * t) * 0.28
            noise = random.uniform(-0.12, 0.12) if name in ("hit", "kill", "hurt") else 0
            sample = (math.sin(math.tau * current_frequency * t) + harmonic + noise) * volume * envelope
            frames.append(struct.pack("<h", int(sample * 32767)))
        file.writeframes(b"".join(frames))


def main():
    ensure_dirs()
    pygame.init()

    save_frames("player", [draw_player(index) for index in range(4)])
    save_frames("enemy_grunt", [draw_diamond(40, (225, 72, 72), (100, 22, 28), index) for index in range(4)])
    save_frames("enemy_fast", [draw_diamond(34, (245, 130, 80), (120, 42, 26), index) for index in range(4)])
    save_frames("enemy_tank", [draw_tank(index) for index in range(4)])
    save_frames("enemy_ranger", [draw_diamond(38, (150, 100, 240), (66, 38, 124), index) for index in range(4)])
    save_frames("enemy_elite", [draw_diamond(58, (255, 86, 126), (128, 24, 54), index) for index in range(4)])
    save_frames("enemy_boss", [draw_boss(index) for index in range(4)])
    save_frames("gold", [draw_drop("gold", index) for index in range(4)])
    save_frames("exp", [draw_drop("exp", index) for index in range(4)])
    save_frames("heart", [draw_drop("heart", index) for index in range(4)])
    save_frames("magnet", [draw_drop("magnet", index) for index in range(4)])
    save_surface("magic_missile", draw_projectile("magic_missile"))
    save_surface("blade", draw_projectile("blade"))
    save_surface("enemy_projectile", draw_projectile("enemy_projectile"))

    write_tone("pickup", 980, 0.08, 0.22, 360)
    write_tone("hit", 320, 0.07, 0.32, -80)
    write_tone("kill", 260, 0.12, 0.35, -160)
    write_tone("hurt", 170, 0.18, 0.38, -100)
    write_tone("upgrade", 520, 0.24, 0.32, 420)
    write_tone("select", 760, 0.07, 0.22, 120)
    write_tone("shoot", 720, 0.045, 0.16, -220)
    write_tone("boss", 110, 0.5, 0.42, -40)
    write_tone("victory", 660, 0.42, 0.35, 380)
    write_tone("defeat", 220, 0.38, 0.35, -100)


if __name__ == "__main__":
    main()
