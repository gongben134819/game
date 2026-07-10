import math
import os
import random
import struct
import sys
import wave

import pygame

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from game.config.settings import (
    DROP_FRAME_COUNT,
    ENEMY_FRAME_COUNT,
    IMAGE_DIR,
    PLAYER_FRAME_COUNT,
    SOUND_DIR,
    WEAPON_FRAME_COUNT,
)


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


def brighten(color, amount):
    return tuple(min(255, channel + amount) for channel in color)


def darken(color, amount):
    return tuple(max(0, channel - amount) for channel in color)


def draw_player(index=0):
    surface = pixel_surface((48, 48))
    bob = [0, -1, -2, -1, 0, 1, 2, 1][index % PLAYER_FRAME_COUNT]
    step = 2 if index % 4 in (1, 2) else -2
    cloth = 1 if index % 4 in (2, 3) else -1

    pygame.draw.ellipse(surface, (8, 12, 22, 150), (7, 39, 35, 6))
    pygame.draw.polygon(surface, (14, 30, 60), [(9, 17 + bob), (38, 17 + bob), (42, 42 + cloth), (31, 38), (24, 44), (16, 38), (6, 42 - cloth)])
    pygame.draw.polygon(surface, (28, 72, 138), [(14, 17 + bob), (35, 17 + bob), (36, 39), (27, 36 + cloth), (22, 41), (14, 37)])
    pygame.draw.line(surface, (86, 184, 255), (16, 20 + bob), (13, 38), 2)
    pygame.draw.line(surface, (104, 205, 255), (33, 20 + bob), (35, 37), 2)
    pygame.draw.rect(surface, (84, 172, 246), (15, 14 + bob, 18, 25), border_radius=4)
    pygame.draw.rect(surface, (34, 105, 185), (15, 30 + bob, 18, 8), border_radius=2)
    pygame.draw.rect(surface, (255, 226, 118), (20, 30 + bob, 8, 4), border_radius=1)
    pygame.draw.circle(surface, (226, 236, 248), (24, 10 + bob), 7)
    pygame.draw.rect(surface, (54, 38, 72), (17, 3 + bob, 15, 8), border_radius=3)
    pygame.draw.rect(surface, (68, 48, 92), (13, 9 + bob, 22, 4), border_radius=2)
    pygame.draw.rect(surface, (96, 72, 132), (18, 4 + bob, 12, 3), border_radius=1)
    pygame.draw.rect(surface, (68, 42, 24), (17, 10 + bob, 4, 7), border_radius=1)
    pygame.draw.rect(surface, (255, 255, 255), (27, 9 + bob, 4, 3), border_radius=1)
    pygame.draw.rect(surface, (121, 221, 255), (10, 22 + bob, 6, 12), border_radius=2)
    pygame.draw.rect(surface, (245, 250, 255), (33, 21 + bob, 8, 4), border_radius=2)
    pygame.draw.rect(surface, (74, 44, 22), (37, 14 + bob, 3, 24), border_radius=1)
    pygame.draw.circle(surface, (255, 221, 88), (38, 12 + bob), 4)
    pygame.draw.circle(surface, (255, 255, 255), (37, 11 + bob), 1)
    pygame.draw.rect(surface, (19, 35, 58), (14, 38 + step, 7, 5), border_radius=2)
    pygame.draw.rect(surface, (19, 35, 58), (28, 38 - step, 7, 5), border_radius=2)
    pygame.draw.rect(surface, (126, 218, 255), (15, 39 + step, 5, 2))
    pygame.draw.rect(surface, (126, 218, 255), (29, 39 - step, 5, 2))
    return surface


def draw_diamond(size, color, core, index=0, kind="grunt"):
    surface = pixel_surface((size, size))
    center = size // 2
    bob = [0, 1, 1, 0, -1, -1][index % ENEMY_FRAME_COUNT]
    glow = index % 3
    pygame.draw.polygon(surface, (40, 20, 24, 120), [(center, size - 7), (size - 5, center + 5), (center, size - 1), (5, center + 5)])
    if kind == "elite":
        pygame.draw.circle(surface, (*brighten(color, 30), 90), (center, center + bob), center - 1, 2)
    if kind == "fast":
        for offset in (0, 5, 10):
            pygame.draw.line(surface, (255, 220, 160, 120), (3, center - 8 + offset), (10, center - 12 + offset + bob), 2)
    pygame.draw.polygon(surface, color, [(center, 2 + bob), (size - 2, center), (center, size - 2 - bob), (2, center)])
    pygame.draw.polygon(surface, brighten(color, 36), [(center, 5 + bob), (size - 8, center), (center, center + 4)])
    if kind in ("grunt", "elite"):
        spike = max(3, size // 8)
        pygame.draw.polygon(surface, darken(color, 42), [(center, 0 + bob), (center - spike, 7 + bob), (center + spike, 7 + bob)])
        pygame.draw.polygon(surface, darken(color, 42), [(0, center), (7, center - spike), (7, center + spike)])
        pygame.draw.polygon(surface, darken(color, 42), [(size - 1, center), (size - 8, center - spike), (size - 8, center + spike)])
    if kind == "ranger":
        pygame.draw.rect(surface, (64, 38, 102), (size - 9, 7 + bob, 4, size - 13), border_radius=1)
        pygame.draw.circle(surface, (200, 150, 255), (size - 7, 8 + bob), 3)
    pygame.draw.rect(surface, core, (center - 7, center - 6 + bob, 14, 12 + glow // 2), border_radius=2)
    pygame.draw.rect(surface, (255, 255, 255), (center - 5, center - 12 + bob, 4, 4))
    pygame.draw.rect(surface, (255, 255, 255), (center + 2, center - 12 + bob, 4, 4))
    if kind == "elite":
        pygame.draw.circle(surface, (255, 226, 190), (center, center + bob), 4, 1)
    return surface


def draw_tank(index=0):
    surface = pixel_surface((52, 52))
    bob = [0, 0, 1, 0, -1, 0][index % ENEMY_FRAME_COUNT]
    pygame.draw.rect(surface, (30, 36, 46, 140), (8, 40, 36, 5))
    pygame.draw.rect(surface, (92, 106, 124), (4, 16 + bob, 44, 24), border_radius=4)
    pygame.draw.rect(surface, (132, 162, 188), (6, 10 + bob, 40, 32), border_radius=4)
    pygame.draw.rect(surface, (188, 212, 228), (8, 12 + bob, 36, 5), border_radius=2)
    pygame.draw.rect(surface, (88, 112, 138), (8, 28 + bob, 36, 10), border_radius=2)
    pygame.draw.rect(surface, (62, 78, 94), (14, 18 + bob, 24, 16), border_radius=2)
    pygame.draw.rect(surface, (220, 234, 244), (18, 8 + bob, 16, 6), border_radius=2)
    pygame.draw.rect(surface, (180, 206, 226), (5, 20 + bob, 5, 12), border_radius=2)
    pygame.draw.rect(surface, (180, 206, 226), (42, 20 + bob, 5, 12), border_radius=2)
    for x in (12, 22, 32):
        pygame.draw.circle(surface, (44, 56, 70), (x, 35 + bob), 2)
    pygame.draw.rect(surface, (235, 244, 250), (20, 21 + bob, 5, 4))
    pygame.draw.rect(surface, (235, 244, 250), (28, 21 + bob, 5, 4))
    return surface


def draw_boss(index=0):
    surface = pixel_surface((104, 104))
    bob = [0, -1, -1, 0, 1, 1][index % ENEMY_FRAME_COUNT]
    pygame.draw.rect(surface, (50, 34, 22, 145), (19, 84, 66, 8), border_radius=2)
    pygame.draw.rect(surface, (124, 66, 34), (10, 34 + bob, 84, 48), border_radius=8)
    pygame.draw.rect(surface, (255, 198, 82), (14, 24 + bob, 76, 60), border_radius=8)
    pygame.draw.rect(surface, (255, 222, 112), (18, 27 + bob, 68, 9), border_radius=3)
    pygame.draw.rect(surface, (205, 124, 48), (14, 63 + bob, 76, 21), border_radius=4)
    pygame.draw.circle(surface, (255, 230, 114), (52, 53 + bob), 21)
    pygame.draw.circle(surface, (145, 77, 34), (52, 53 + bob), 15)
    pygame.draw.circle(surface, (255, 245, 180), (47, 48 + bob), 5)
    pygame.draw.polygon(surface, (255, 244, 186), [(30, 24 + bob), (39, 9 + bob), (48, 23 + bob), (52, 7 + bob), (58, 23 + bob), (68, 9 + bob), (76, 24 + bob)])
    pygame.draw.rect(surface, (255, 244, 186), (29, 21 + bob, 48, 9), border_radius=2)
    pygame.draw.circle(surface, (255, 86, 126), (52, 19 + bob), 3)
    pygame.draw.rect(surface, (255, 255, 255), (33, 44 + bob, 9, 8), border_radius=1)
    pygame.draw.rect(surface, (255, 255, 255), (63, 44 + bob, 9, 8), border_radius=1)
    pygame.draw.rect(surface, (82, 38, 18), (42, 67 + bob, 22, 6), border_radius=2)
    pygame.draw.rect(surface, (255, 226, 110), (4, 43 + bob, 14, 29), border_radius=4)
    pygame.draw.rect(surface, (255, 226, 110), (86, 43 + bob, 14, 29), border_radius=4)
    pygame.draw.rect(surface, (160, 86, 34), (7, 48 + bob, 8, 18), border_radius=2)
    pygame.draw.rect(surface, (160, 86, 34), (89, 48 + bob, 8, 18), border_radius=2)
    for x in (26, 78):
        pygame.draw.circle(surface, (255, 244, 186), (x, 74 + bob), 4)
    return surface


def draw_drop(kind, index=0):
    surface = pixel_surface((24, 24))
    pulse = [0, 1, 2, 1, 0, 1][index % DROP_FRAME_COUNT]
    if kind == "gold":
        pygame.draw.rect(surface, (255, 236, 145), (4, 4, 16, 16), border_radius=2)
        pygame.draw.rect(surface, (244, 190, 62), (6, 6, 12, 12 + pulse // 2), border_radius=2)
        pygame.draw.rect(surface, (255, 255, 255), (8, 6, 4, 4))
    elif kind == "exp":
        pygame.draw.polygon(surface, (91, 217, 235), [(12, 2 - pulse // 2), (21, 12), (12, 22 + pulse // 2), (3, 12)])
        pygame.draw.rect(surface, (255, 255, 255), (10, 7, 4, 4))
    elif kind == "heart":
        pygame.draw.rect(surface, (232, 76, 76), (6, 7, 12, 10 + pulse // 2), border_radius=2)
        pygame.draw.rect(surface, (232, 76, 76), (8, 5, 4, 4))
        pygame.draw.rect(surface, (232, 76, 76), (14, 5, 4, 4))
        pygame.draw.rect(surface, (255, 255, 255), (8, 7, 3, 3))
    elif kind == "magnet":
        pygame.draw.rect(surface, (168, 116, 255), (5, 4, 5, 15), border_radius=2)
        pygame.draw.rect(surface, (168, 116, 255), (14, 4, 5, 15), border_radius=2)
        pygame.draw.rect(surface, (168, 116, 255), (8, 14, 8, 5), border_radius=2)
        pygame.draw.rect(surface, (255, 255, 255), (5, 4, 5, 4))
        pygame.draw.rect(surface, (255, 255, 255), (14, 4, 5, 4))
    return surface


def draw_blueprint(kind, index=0):
    surface = pixel_surface((24, 24))
    colors = {
        "character": (72, 142, 255),
        "weapon": (168, 116, 255),
        "item": (82, 196, 120),
    }
    color = colors.get(kind, (91, 217, 235))
    pulse = [0, 1, 2, 1, 0, 1][index % DROP_FRAME_COUNT]
    pygame.draw.rect(surface, (235, 244, 250), (4, 3, 16, 18), border_radius=3)
    pygame.draw.rect(surface, color, (6, 5 + pulse // 2, 12, 14), border_radius=2)
    pygame.draw.line(surface, (255, 255, 255), (8, 10), (16, 10), 2)
    pygame.draw.line(surface, (255, 255, 255), (8, 14), (15, 14), 1)
    if kind == "character":
        pygame.draw.circle(surface, (255, 255, 255), (12, 8), 3)
    elif kind == "weapon":
        pygame.draw.polygon(surface, (255, 255, 255), [(12, 7), (16, 12), (12, 17), (8, 12)])
    else:
        pygame.draw.rect(surface, (255, 255, 255), (9, 8, 6, 8), border_radius=1)
    return surface


def draw_item_icon(kind):
    surface = pixel_surface((36, 36))
    center = 18
    colors = {
        "revive_charm": (82, 196, 120),
        "starter_magnet": (168, 116, 255),
        "exp_charm": (91, 217, 235),
        "gold_dice": (244, 190, 62),
        "boss_hunter": (232, 76, 76),
        "blueprint_radar": (72, 142, 255),
    }
    color = colors.get(kind, (91, 217, 235))
    pygame.draw.circle(surface, (22, 27, 38), (center, center), 17)
    pygame.draw.circle(surface, color, (center, center), 14)
    pygame.draw.circle(surface, (255, 255, 255), (center, center), 14, 2)
    if kind == "revive_charm":
        pygame.draw.circle(surface, (255, 255, 255), (center - 5, center - 3), 4)
        pygame.draw.circle(surface, (255, 255, 255), (center + 5, center - 3), 4)
        pygame.draw.polygon(surface, (255, 255, 255), [(center - 9, center), (center + 9, center), (center, center + 10)])
    elif kind == "starter_magnet":
        pygame.draw.arc(surface, (255, 255, 255), (9, 8, 18, 20), math.pi, math.tau, 4)
        pygame.draw.rect(surface, (255, 255, 255), (8, 17, 5, 8))
        pygame.draw.rect(surface, (255, 255, 255), (23, 17, 5, 8))
    elif kind == "exp_charm":
        pygame.draw.polygon(surface, (255, 255, 255), [(center, 6), (27, center), (center, 30), (9, center)])
    elif kind == "gold_dice":
        pygame.draw.rect(surface, (255, 255, 255), (9, 9, 18, 18), border_radius=3)
        for point in ((14, 14), (22, 14), (18, 18), (14, 22), (22, 22)):
            pygame.draw.circle(surface, color, point, 2)
    elif kind == "boss_hunter":
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 10, 3)
        pygame.draw.line(surface, (255, 255, 255), (center, 6), (center, 30), 2)
        pygame.draw.line(surface, (255, 255, 255), (6, center), (30, center), 2)
    elif kind == "blueprint_radar":
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 10, 2)
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 4)
        pygame.draw.line(surface, (255, 255, 255), (center, center), (27, 11), 2)
    return surface


def draw_character_icon(kind, color):
    surface = pixel_surface((48, 48))
    pygame.draw.ellipse(surface, (8, 12, 22, 150), (8, 38, 32, 6))
    pygame.draw.polygon(surface, darken(color, 60), [(12, 18), (36, 18), (40, 40), (24, 44), (8, 40)])
    pygame.draw.rect(surface, color, (15, 16, 18, 22), border_radius=4)
    pygame.draw.circle(surface, (226, 236, 248), (24, 10), 7)
    pygame.draw.circle(surface, (255, 255, 255), (28, 9), 2)
    if kind == "knight":
        pygame.draw.rect(surface, (210, 224, 236), (14, 5, 20, 9), border_radius=3)
        pygame.draw.rect(surface, (130, 154, 176), (11, 20, 8, 16), border_radius=2)
    elif kind == "rogue":
        pygame.draw.polygon(surface, (30, 42, 34), [(12, 8), (35, 4), (32, 15), (15, 15)])
        pygame.draw.line(surface, (255, 244, 186), (32, 22), (41, 17), 2)
    elif kind == "alchemist":
        pygame.draw.circle(surface, (255, 178, 64), (38, 22), 5)
        pygame.draw.line(surface, (255, 255, 255), (36, 20), (40, 24), 1)
    elif kind == "witch":
        pygame.draw.polygon(surface, (38, 58, 96), [(13, 10), (24, 0), (36, 10)])
        pygame.draw.rect(surface, (160, 226, 255), (9, 23, 8, 3), border_radius=1)
    elif kind == "engineer":
        pygame.draw.circle(surface, (244, 190, 62), (38, 18), 6)
        pygame.draw.rect(surface, (92, 64, 28), (34, 16, 8, 4), border_radius=1)
    else:
        pygame.draw.rect(surface, (68, 48, 92), (14, 7, 20, 5), border_radius=2)
    return surface


def draw_skill_icon(kind, color):
    surface = pixel_surface((36, 36))
    center = 18
    pygame.draw.circle(surface, (22, 27, 38), (center, center), 17)
    pygame.draw.circle(surface, color, (center, center), 14)
    pygame.draw.circle(surface, (255, 255, 255), (center, center), 14, 2)
    if kind == "mage":
        for angle in range(0, 360, 60):
            direction = pygame.math.Vector2(1, 0).rotate(angle)
            pygame.draw.line(surface, (255, 255, 255), (center, center), pygame.math.Vector2(center, center) + direction * 11, 2)
    elif kind == "knight":
        pygame.draw.polygon(surface, (255, 255, 255), [(center, 7), (27, 12), (25, 25), (center, 30), (11, 25), (9, 12)])
    elif kind == "rogue":
        pygame.draw.polygon(surface, (255, 255, 255), [(8, 22), (25, 8), (21, 18), (29, 18), (12, 30), (16, 21)])
    elif kind == "alchemist":
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 8)
        pygame.draw.rect(surface, color, (14, 9, 8, 9), border_radius=2)
    elif kind == "witch":
        pygame.draw.polygon(surface, (255, 255, 255), [(center, 6), (28, center), (center, 30), (8, center)])
        pygame.draw.circle(surface, color, (center, center), 4)
    elif kind == "engineer":
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 9, 3)
        pygame.draw.rect(surface, (255, 255, 255), (center - 2, 6, 4, 8))
        pygame.draw.rect(surface, (255, 255, 255), (center - 2, 22, 4, 8))
    return surface


def draw_chapter_icon(kind):
    surface = pixel_surface((64, 64))
    palettes = {
        "mine": ((20, 28, 37), (244, 190, 62)),
        "lava": ((48, 18, 18), (255, 100, 34)),
        "frost": ((18, 36, 48), (160, 226, 255)),
        "factory": ((30, 34, 42), (132, 162, 188)),
        "throne": ((34, 25, 42), (255, 222, 112)),
    }
    base, accent = palettes[kind]
    surface.fill((0, 0, 0, 0))
    pygame.draw.rect(surface, base, (4, 4, 56, 56), border_radius=8)
    pygame.draw.rect(surface, accent, (4, 4, 56, 56), 3, border_radius=8)
    if kind == "mine":
        pygame.draw.line(surface, accent, (10, 44), (54, 28), 4)
        pygame.draw.circle(surface, accent, (24, 24), 8)
    elif kind == "lava":
        pygame.draw.polygon(surface, accent, [(12, 52), (24, 20), (34, 50), (45, 18), (56, 52)])
    elif kind == "frost":
        pygame.draw.polygon(surface, accent, [(32, 8), (44, 32), (32, 56), (20, 32)])
        pygame.draw.line(surface, (255, 255, 255), (32, 12), (32, 52), 2)
    elif kind == "factory":
        pygame.draw.circle(surface, accent, (32, 32), 18, 4)
        pygame.draw.circle(surface, accent, (32, 32), 6)
    elif kind == "throne":
        pygame.draw.polygon(surface, accent, [(16, 48), (22, 20), (32, 36), (42, 20), (48, 48)])
        pygame.draw.rect(surface, accent, (18, 46, 28, 6), border_radius=2)
    return surface


def draw_projectile(kind, index=0):
    surface = pixel_surface((30, 30))
    center = 15
    if kind == "magic_missile":
        flame = 3 + index % 3
        pygame.draw.polygon(surface, (38, 90, 230), [(center, 24), (center - 5, 18), (center + 5, 18)])
        pygame.draw.polygon(surface, (104, 204, 255), [(center, 28), (center - flame, 20), (center + flame, 20)])
        pygame.draw.circle(surface, (28, 88, 235), (center, center + 1), 10)
        pygame.draw.circle(surface, (91, 217, 235), (center, center), 8 + index % 2)
        pygame.draw.circle(surface, (255, 255, 255), (center - 3, center - 4), 3)
        pygame.draw.rect(surface, (180, 240, 255), (center + 2, center - 7, 3, 9), border_radius=1)
    elif kind == "blade":
        inset = 2 + index % 3
        pygame.draw.polygon(surface, (160, 238, 255, 130), [(center, 1), (29, center), (center, 29), (1, center)])
        pygame.draw.polygon(surface, (255, 255, 255), [(center, inset), (30 - inset, center), (center, 30 - inset), (inset, center)])
        pygame.draw.polygon(surface, (91, 217, 235), [(center, 7), (23, center), (center, 23), (7, center)])
        pygame.draw.line(surface, (32, 100, 150), (8, center + 2), (center, 23), 2)
        pygame.draw.circle(surface, (255, 255, 255), (center, center), 3)
    elif kind == "flame_orb":
        pulse = index % 3
        pygame.draw.circle(surface, (100, 34, 20), (center, center + 2), 12)
        pygame.draw.polygon(surface, (255, 88, 34), [(center, 2 + pulse), (24, 13), (21, 25), (center, 28 - pulse), (8, 23), (5, 12)])
        pygame.draw.circle(surface, (255, 124, 42), (center, center - 1), 9 + pulse)
        pygame.draw.circle(surface, (255, 236, 130), (center - 3, center - 4), 4)
        pygame.draw.circle(surface, (255, 255, 235), (center - 5, center - 6), 2)
    elif kind == "frost_shard":
        pygame.draw.polygon(surface, (210, 248, 255), [(center, 1), (28, center), (center, 29), (2, center)])
        pygame.draw.polygon(surface, (91, 217, 235), [(center, 6), (23, center), (center, 24), (7, center)])
        pygame.draw.line(surface, (255, 255, 255), (center, 5), (center, 24), 2)
        pygame.draw.line(surface, (190, 246, 255), (8, center), (22, center), 1)
        pygame.draw.line(surface, (160, 226, 255), (center, center), (10 + index % 4, 9), 1)
        pygame.draw.line(surface, (160, 226, 255), (center, center), (21 - index % 4, 22), 1)
    elif kind == "drone":
        prop = 1 + index % 2
        pygame.draw.rect(surface, (78, 62, 38), (center - 13, center - 2 - prop, 26, 4 + prop), border_radius=2)
        pygame.draw.rect(surface, (78, 62, 38), (center - 2 - prop, center - 13, 4 + prop, 26), border_radius=2)
        pygame.draw.circle(surface, (86, 64, 34), (center, center), 12)
        pygame.draw.circle(surface, (244, 190, 62), (center, center), 9)
        pygame.draw.circle(surface, (255, 226, 110), (center, center), 5)
        pygame.draw.rect(surface, (255, 255, 255), (center - 4, 5 + index % 2, 8, 4), border_radius=1)
        pygame.draw.rect(surface, (92, 64, 28), (center - 9, center - 2, 18, 5), border_radius=2)
    elif kind == "drone_shot":
        pygame.draw.circle(surface, (244, 190, 62), (center, center), 7)
        pygame.draw.circle(surface, (255, 255, 255), (center - 2, center - 2), 2)
    elif kind == "pulse_icon":
        pygame.draw.circle(surface, (72, 142, 255), (center, center), 12, 3)
        pygame.draw.circle(surface, (91, 217, 235), (center, center), 7, 2)
        pygame.draw.line(surface, (255, 255, 255), (center, 4), (center, 26), 2)
    elif kind == "enemy_projectile":
        pygame.draw.rect(surface, (232, 76, 76), (9, 9, 12, 12), border_radius=2)
        pygame.draw.rect(surface, (255, 255, 255), (11, 10, 4, 4))
    return surface


def draw_effect(kind):
    surface = pixel_surface((48, 48))
    center = 24
    if kind == "slash_arc":
        rect = pygame.Rect(5, 5, 38, 38)
        pygame.draw.arc(surface, (91, 217, 235, 210), rect, -0.7, 1.3, 6)
        pygame.draw.arc(surface, (255, 255, 255, 180), rect.inflate(-8, -8), -0.55, 1.05, 3)
        pygame.draw.circle(surface, (255, 255, 255, 160), (37, 15), 3)
    elif kind == "shock_ring":
        pygame.draw.circle(surface, (91, 217, 235, 160), (center, center), 20, 4)
        pygame.draw.circle(surface, (255, 255, 255, 95), (center, center), 12, 2)
        for angle in range(0, 360, 45):
            direction = pygame.math.Vector2(1, 0).rotate(angle)
            start = pygame.math.Vector2(center, center) + direction * 14
            end = pygame.math.Vector2(center, center) + direction * 22
            pygame.draw.line(surface, (255, 255, 255, 115), start, end, 2)
    elif kind == "spark":
        for angle in range(0, 360, 45):
            direction = pygame.math.Vector2(1, 0).rotate(angle)
            end = pygame.math.Vector2(center, center) + direction * (11 if angle % 90 == 0 else 7)
            pygame.draw.line(surface, (255, 255, 255, 230), (center, center), end, 3)
        pygame.draw.circle(surface, (255, 236, 130, 220), (center, center), 5)
    elif kind == "burn_flame":
        pygame.draw.polygon(surface, (255, 80, 34, 190), [(24, 5), (36, 20), (31, 40), (17, 42), (10, 22)])
        pygame.draw.polygon(surface, (255, 178, 64, 220), [(23, 12), (31, 23), (27, 37), (18, 35), (15, 24)])
        pygame.draw.polygon(surface, (255, 244, 156, 230), [(23, 18), (27, 27), (23, 34), (19, 27)])
    elif kind == "frost_spark":
        pygame.draw.polygon(surface, (190, 246, 255, 210), [(center, 4), (30, 18), (44, center), (30, 30), (center, 44), (18, 30), (4, center), (18, 18)])
        pygame.draw.line(surface, (255, 255, 255, 220), (center, 7), (center, 41), 2)
        pygame.draw.line(surface, (255, 255, 255, 180), (7, center), (41, center), 2)
        pygame.draw.circle(surface, (91, 217, 235, 170), (center, center), 6)
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
    random.seed(7)
    pygame.init()

    save_frames("player", [draw_player(index) for index in range(PLAYER_FRAME_COUNT)])
    save_frames("enemy_grunt", [draw_diamond(40, (225, 72, 72), (100, 22, 28), index, "grunt") for index in range(ENEMY_FRAME_COUNT)])
    save_frames("enemy_fast", [draw_diamond(34, (245, 130, 80), (120, 42, 26), index, "fast") for index in range(ENEMY_FRAME_COUNT)])
    save_frames("enemy_tank", [draw_tank(index) for index in range(ENEMY_FRAME_COUNT)])
    save_frames("enemy_ranger", [draw_diamond(38, (150, 100, 240), (66, 38, 124), index, "ranger") for index in range(ENEMY_FRAME_COUNT)])
    save_frames("enemy_elite", [draw_diamond(58, (255, 86, 126), (128, 24, 54), index, "elite") for index in range(ENEMY_FRAME_COUNT)])
    save_frames("enemy_boss", [draw_boss(index) for index in range(ENEMY_FRAME_COUNT)])
    save_frames("gold", [draw_drop("gold", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("exp", [draw_drop("exp", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("heart", [draw_drop("heart", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("magnet", [draw_drop("magnet", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("blueprint_character", [draw_blueprint("character", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("blueprint_weapon", [draw_blueprint("weapon", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("blueprint_item", [draw_blueprint("item", index) for index in range(DROP_FRAME_COUNT)])
    save_frames("magic_missile", [draw_projectile("magic_missile", index) for index in range(WEAPON_FRAME_COUNT)])
    save_frames("blade", [draw_projectile("blade", index) for index in range(WEAPON_FRAME_COUNT)])
    save_frames("flame_orb", [draw_projectile("flame_orb", index) for index in range(WEAPON_FRAME_COUNT)])
    save_frames("frost_shard", [draw_projectile("frost_shard", index) for index in range(WEAPON_FRAME_COUNT)])
    save_frames("drone", [draw_projectile("drone", index) for index in range(WEAPON_FRAME_COUNT)])
    save_surface("drone_shot", draw_projectile("drone_shot"))
    save_surface("pulse_icon", draw_projectile("pulse_icon"))
    save_surface("enemy_projectile", draw_projectile("enemy_projectile"))
    save_surface("slash_arc", draw_effect("slash_arc"))
    save_surface("shock_ring", draw_effect("shock_ring"))
    save_surface("spark", draw_effect("spark"))
    save_surface("burn_flame", draw_effect("burn_flame"))
    save_surface("frost_spark", draw_effect("frost_spark"))

    character_colors = {
        "mage": (91, 217, 235),
        "knight": (82, 196, 120),
        "rogue": (244, 190, 62),
        "alchemist": (232, 76, 76),
        "witch": (72, 142, 255),
        "engineer": (168, 116, 255),
    }
    for character_id, color in character_colors.items():
        save_surface(f"character_{character_id}", draw_character_icon(character_id, color))
        save_surface(f"skill_{character_id}", draw_skill_icon(character_id, color))

    for item_id in ("revive_charm", "starter_magnet", "exp_charm", "gold_dice", "boss_hunter", "blueprint_radar"):
        save_surface(f"item_{item_id}", draw_item_icon(item_id))

    for chapter_id in ("mine", "lava", "frost", "factory", "throne"):
        save_surface(f"chapter_{chapter_id}", draw_chapter_icon(chapter_id))

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
