import random

import pygame

from game.config.settings import *
from game.systems.chapters import CHAPTER_ORDER, CHAPTERS, chapter_unlocked
from game.systems.characters import CHARACTERS
from game.systems.save_data import PERMANENT_UPGRADES, get_permanent_upgrade_cost
from game.systems.unlocks import (
    CHARACTER_UNLOCKS,
    ITEM_DEFS,
    WEAPON_UNLOCKS,
    item_upgrade_cost,
    requirement_met,
    requirement_text,
)


class UI:
    def __init__(self, surface, resources=None, input_manager=None):
        self.surface = surface
        self.resources = resources
        self.input_manager = input_manager
        self.font_sizes = {}
        self.font = self.get_font(30)
        self.big_font = self.get_font(68)
        self.mid_font = self.get_font(42)
        self.small_font = self.get_font(24)
        self.tiny_font = self.get_font(20)
        self.menu_buttons = {}
        self.chapter_buttons = []
        self.endless_buttons = {}
        self.character_buttons = []
        self.shop_buttons = []
        self.level_up_cards = []
        self.result_buttons = {}
        self.settings_buttons = []
        self.last_text_rects = {}
        self.background_decor = self.build_background_decor()

    def mouse_pos(self):
        if self.input_manager:
            return self.input_manager.logical_mouse_pos()
        return pygame.mouse.get_pos()

    def get_font(self, size):
        font_names = ["microsoftyahei", "simhei", "simsun", "nsimsun"]
        for font_name in font_names:
            font_path = pygame.font.match_font(font_name)
            if font_path:
                font = pygame.font.Font(font_path, size)
                self.font_sizes[id(font)] = size
                return font
        font = pygame.font.Font(None, size)
        self.font_sizes[id(font)] = size
        return font

    def draw_text(self, text, font, color, pos, anchor="topleft"):
        text_surface = font.render(str(text), True, color)
        rect = text_surface.get_rect(**{anchor: pos})
        self.surface.blit(text_surface, rect)
        return rect

    def remember_text_rect(self, key, rect):
        if key is not None:
            self.last_text_rects.setdefault(key, []).append(rect.copy())

    def draw_fit_text(self, text, font, color, rect, anchor="center", min_size=16, key=None):
        rect = pygame.Rect(rect)
        text = str(text)
        selected_font = font
        text_surface = selected_font.render(text, True, color)
        if text_surface.get_width() > rect.width or text_surface.get_height() > rect.height:
            start_size = self.font_sizes.get(id(font), max(min_size, font.get_height() - 4))
            for size in range(start_size, min_size - 1, -1):
                candidate_font = self.get_font(size)
                candidate_surface = candidate_font.render(text, True, color)
                if candidate_surface.get_width() <= rect.width and candidate_surface.get_height() <= rect.height:
                    selected_font = candidate_font
                    text_surface = candidate_surface
                    break
        if text_surface.get_width() > rect.width:
            ellipsis = "..."
            clipped = text
            while clipped:
                candidate = clipped[:-1] + ellipsis
                text_surface = selected_font.render(candidate, True, color)
                if text_surface.get_width() <= rect.width:
                    text = candidate
                    break
                clipped = clipped[:-1]
            if not clipped:
                text = ""
                text_surface = selected_font.render(text, True, color)
        target = text_surface.get_rect()
        if anchor == "midleft":
            target.midleft = rect.midleft
        elif anchor == "midright":
            target.midright = rect.midright
        elif anchor == "center":
            target.center = rect.center
        else:
            target.topleft = rect.topleft
        self.surface.blit(text_surface, target)
        self.remember_text_rect(key, target)
        return target

    def wrap_text(self, text, font, max_width):
        lines = []
        current = ""
        for char in str(text):
            if char == "\n":
                lines.append(current)
                current = ""
                continue
            candidate = current + char
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current or not lines:
            lines.append(current)
        return lines

    def draw_wrapped_text(self, text, font, color, rect, align="center", max_lines=3, line_gap=4, min_size=16, key=None):
        rect = pygame.Rect(rect)
        selected_font = font
        lines = self.wrap_text(text, selected_font, rect.width)
        start_size = self.font_sizes.get(id(font), max(min_size, font.get_height() - 4))
        for size in range(start_size, min_size - 1, -1):
            candidate_font = self.get_font(size)
            candidate_lines = self.wrap_text(text, candidate_font, rect.width)
            visible_lines = min(len(candidate_lines), max_lines)
            total_height = visible_lines * candidate_font.get_linesize() + max(0, visible_lines - 1) * line_gap
            if total_height <= rect.height:
                selected_font = candidate_font
                lines = candidate_lines
                break
        overflow = len(lines) > max_lines
        lines = lines[:max_lines]
        if overflow and lines:
            clipped = lines[-1]
            while clipped and selected_font.size(clipped + "...")[0] > rect.width:
                clipped = clipped[:-1]
            lines[-1] = clipped + "..."
        line_height = selected_font.get_linesize()
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
        y = rect.centery - total_height // 2
        rendered = []
        for line in lines:
            surface = selected_font.render(line, True, color)
            line_rect = surface.get_rect()
            if align == "left":
                line_rect.midleft = (rect.left, y + line_height // 2)
            elif align == "right":
                line_rect.midright = (rect.right, y + line_height // 2)
            else:
                line_rect.center = (rect.centerx, y + line_height // 2)
            self.surface.blit(surface, line_rect)
            self.remember_text_rect(key, line_rect)
            rendered.append(line_rect.copy())
            y += line_height + line_gap
        return rendered

    def build_background_decor(self):
        rng = random.Random(20260709)
        decor = {"stones": [], "cracks": [], "veins": [], "gold": [], "embers": [], "ice": [], "gears": [], "runes": []}
        for _ in range(48):
            width = rng.randrange(28, 92)
            height = rng.randrange(12, 38)
            rect = pygame.Rect(rng.randrange(0, SCREEN_WIDTH - width), rng.randrange(0, SCREEN_HEIGHT - height), width, height)
            color = rng.choice(((18, 24, 31), (20, 28, 37), (24, 31, 39), (15, 20, 27)))
            decor["stones"].append((rect, color))
        for _ in range(26):
            points = [(rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT))]
            for _ in range(rng.randrange(2, 5)):
                last_x, last_y = points[-1]
                points.append((max(0, min(SCREEN_WIDTH, last_x + rng.randrange(-34, 35))), max(0, min(SCREEN_HEIGHT, last_y + rng.randrange(-22, 23)))))
            decor["cracks"].append(points)
        for _ in range(12):
            points = [(rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT))]
            for _ in range(rng.randrange(3, 7)):
                last_x, last_y = points[-1]
                points.append((max(0, min(SCREEN_WIDTH, last_x + rng.randrange(-60, 61))), max(0, min(SCREEN_HEIGHT, last_y + rng.randrange(-30, 31)))))
            decor["veins"].append(points)
        for _ in range(120):
            decor["gold"].append((rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT), rng.randrange(1, 3)))
        for _ in range(65):
            decor["embers"].append((rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT), rng.randrange(1, 4)))
        for _ in range(34):
            decor["ice"].append(pygame.Rect(rng.randrange(0, SCREEN_WIDTH - 90), rng.randrange(0, SCREEN_HEIGHT - 26), rng.randrange(46, 110), rng.randrange(8, 26)))
        for _ in range(20):
            decor["gears"].append((rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT), rng.randrange(10, 26)))
        for _ in range(28):
            decor["runes"].append((rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT), rng.randrange(12, 34)))
        return decor

    def background_item_count(self, detail="high"):
        scale = {"low": 0.0, "medium": 0.5, "high": 1.0}.get(detail, 1.0)
        return {key: int(len(value) * scale) for key, value in self.background_decor.items()}

    def draw_background(self, detail="high", theme="mine"):
        counts = self.background_item_count(detail)
        palettes = {
            "mine": ((9, 12, 16), (18, 25, 33), (126, 94, 38)),
            "lava": ((17, 10, 10), (38, 19, 18), (196, 76, 32)),
            "frost": ((9, 16, 24), (18, 36, 48), (112, 196, 228)),
            "factory": ((12, 14, 18), (30, 34, 42), (110, 128, 142)),
            "throne": ((15, 11, 18), (34, 25, 42), (198, 154, 62)),
        }
        base, grid, accent = palettes.get(theme, palettes["mine"])
        self.surface.fill(base)
        for rect, color in self.background_decor["stones"][: counts["stones"]]:
            pygame.draw.rect(self.surface, color, rect, border_radius=3)
            pygame.draw.rect(self.surface, grid, rect, 1, border_radius=3)
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.surface, grid, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.surface, grid, (0, y), (SCREEN_WIDTH, y), 1)
        for points in self.background_decor["veins"][: counts["veins"]]:
            pygame.draw.lines(self.surface, (72, 60, 30), False, points, 2)
            pygame.draw.lines(self.surface, accent, False, points, 1)
        for points in self.background_decor["cracks"][: counts["cracks"]]:
            pygame.draw.lines(self.surface, (5, 8, 12), False, points, 2)
            pygame.draw.lines(self.surface, (32, 39, 46), False, points, 1)
        if theme == "lava":
            for x, y, radius in self.background_decor["embers"][: counts["embers"]]:
                pygame.draw.circle(self.surface, (162, 58, 28), (x, y), radius)
        elif theme == "frost":
            for rect in self.background_decor["ice"][: counts["ice"]]:
                pygame.draw.rect(self.surface, (34, 68, 88), rect, border_radius=6)
                pygame.draw.rect(self.surface, (104, 186, 220), rect, 1, border_radius=6)
        elif theme == "factory":
            for x, y, radius in self.background_decor["gears"][: counts["gears"]]:
                pygame.draw.circle(self.surface, (56, 64, 74), (x, y), radius, 2)
                pygame.draw.circle(self.surface, (94, 110, 124), (x, y), max(3, radius // 3), 1)
        elif theme == "throne":
            for x, y, radius in self.background_decor["runes"][: counts["runes"]]:
                pygame.draw.circle(self.surface, (118, 74, 126), (x, y), radius, 1)
                pygame.draw.line(self.surface, accent, (x - radius // 2, y), (x + radius // 2, y), 1)
        for x, y, radius in self.background_decor["gold"][: counts["gold"]]:
            pygame.draw.circle(self.surface, (92, 72, 28), (x, y), radius)
            if radius > 1:
                pygame.draw.circle(self.surface, accent, (x, y), 1)
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 72), vignette.get_rect(), 42)
        pygame.draw.rect(vignette, (0, 0, 0, 0), vignette.get_rect().inflate(-130, -90), border_radius=36)
        self.surface.blit(vignette, (0, 0))

    def draw_panel(self, rect, color=PANEL_COLOR, border_color=(64, 78, 102)):
        pygame.draw.rect(self.surface, color, rect, border_radius=8)
        pygame.draw.rect(self.surface, border_color, rect, 2, border_radius=8)

    def lighten(self, color, amount=24):
        return tuple(min(255, channel + amount) for channel in color)

    def update_cursor(self, hovering):
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hovering else pygame.SYSTEM_CURSOR_ARROW)
        except pygame.error:
            pass

    def draw_click_rect(self, rect, color, border_color, hovered=False, disabled=False):
        fill = color if not hovered else self.lighten(color, 12)
        border = border_color if not hovered else self.lighten(border_color, 55)
        if disabled:
            fill = (28, 32, 42)
            border = (74, 80, 92) if not hovered else TEXT_MUTED
        pygame.draw.rect(self.surface, fill, rect, border_radius=8)
        pygame.draw.rect(self.surface, border, rect, 3 if hovered else 2, border_radius=8)

    def hit_menu(self, pos):
        if "start" in self.menu_buttons and self.menu_buttons["start"].collidepoint(pos):
            return "start"
        for action, rect in self.menu_buttons.items():
            if rect.collidepoint(pos):
                return action
        return None

    def hit_chapter(self, pos):
        for button in self.chapter_buttons:
            if button["rect"].collidepoint(pos):
                return button
        return None

    def hit_endless(self, pos):
        for action, rect in self.endless_buttons.items():
            if rect.collidepoint(pos):
                return action
        return None

    def hit_character(self, pos):
        for button in self.character_buttons:
            if button["rect"].collidepoint(pos):
                return button
        return None

    def hit_shop(self, pos):
        for button in self.shop_buttons:
            if button["rect"].collidepoint(pos):
                return button
        return None

    def hit_level_up(self, pos):
        for index, rect in self.level_up_cards:
            if rect.collidepoint(pos):
                return index
        return None

    def hit_result(self, pos):
        for action, rect in self.result_buttons.items():
            if rect.collidepoint(pos):
                return action
        return None

    def hit_settings(self, pos):
        for button in self.settings_buttons:
            if button["rect"].collidepoint(pos):
                return button["action"]
        return None

    def draw_bar(self, rect, ratio, fill_color, back_color=(58, 64, 78)):
        ratio = max(0, min(1, ratio))
        pygame.draw.rect(self.surface, back_color, rect, border_radius=6)
        if ratio > 0:
            fill_rect = pygame.Rect(rect)
            fill_rect.width = max(4, int(rect.width * ratio))
            pygame.draw.rect(self.surface, fill_color, fill_rect, border_radius=6)
        pygame.draw.rect(self.surface, (92, 104, 126), rect, 2, border_radius=6)

    def format_time(self, seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def draw_button_row(self, key_text, label, rect, color, hovered=False):
        self.draw_click_rect(rect, PANEL_DARK, color, hovered)
        key_width = 150 if rect.width >= 320 else 70
        key_rect = pygame.Rect(rect.x + 18, rect.y + 4, key_width, rect.height - 8)
        pygame.draw.rect(self.surface, self.lighten(color, 10) if hovered else color, key_rect, border_radius=6)
        self.draw_fit_text(key_text, self.tiny_font, BLACK, key_rect.inflate(-8, -4), "center", 13, "button")
        label_rect = pygame.Rect(key_rect.right + 18, rect.y + 4, rect.right - key_rect.right - 32, rect.height - 8)
        self.draw_fit_text(label, self.small_font, WHITE, label_rect, "midleft", 16, "button")

    def draw_menu(self, save_data):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.menu_buttons = {}
        self.draw_background()
        self.draw_text("金币冲刺", self.big_font, WHITE, (SCREEN_WIDTH // 2, 90), "center")
        self.draw_text("章节挑战与无尽爬层", self.mid_font, CYAN, (SCREEN_WIDTH // 2, 156), "center")
        self.draw_preview_strip()

        actions = [
            ("chapter", "Enter", "章节挑战", CYAN),
            ("endless", "E", "无尽爬层", PURPLE),
            ("characters", "C", "角色", GREEN),
            ("shop", "S", "金币商城", YELLOW),
            ("settings", "O", "设置", BLUE),
            ("quit", "Esc", "退出", RED),
        ]
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 270, 302, 540, 356)
        self.draw_panel(panel, PANEL_DARK, CYAN)
        y = panel.y + 24
        for action, key, label, color in actions:
            rect = pygame.Rect(panel.x + 58, y, 424, 42)
            self.menu_buttons[action] = rect
            self.draw_button_row(key, label, rect, color, rect.collidepoint(mouse_pos))
            y += 50
        self.menu_buttons["start"] = pygame.Rect(-240, -240, 12, 12)
        record_text = f"最高分 {save_data['high_score']}   最长 {self.format_time(save_data['longest_time'])}   总金币 {save_data['total_gold']}   无尽最高 {save_data['endless_highest_floor']} 层"
        self.draw_fit_text(record_text, self.tiny_font, TEXT_MUTED, pygame.Rect(panel.x + 24, panel.bottom - 34, panel.width - 48, 26), "center", 13)
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.menu_buttons.values()))

    def draw_preview_strip(self):
        y = 242
        pygame.draw.line(self.surface, (56, 76, 102), (370, y), (910, y), 2)
        for x, color, label in (
            (470, CYAN, "法师"),
            (575, GREEN, "骑士"),
            (680, RED, "炼金"),
            (785, BLUE, "寒霜"),
            (890, PURPLE, "机械"),
        ):
            pygame.draw.circle(self.surface, color, (x, y), 24)
            pygame.draw.circle(self.surface, WHITE, (x, y), 24, 2)
            self.draw_fit_text(label, self.tiny_font, WHITE, pygame.Rect(x - 38, y + 30, 76, 22), "center", 12)

    def draw_chapter_select(self, save_data):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.chapter_buttons = []
        self.draw_background(theme="mine")
        self.draw_text("章节挑战", self.mid_font, WHITE, (SCREEN_WIDTH // 2, 56), "center")
        self.draw_fit_text("每章 6 分钟后 Boss 登场，通关后解锁下一章。", self.small_font, TEXT_MUTED, pygame.Rect(260, 96, 760, 32), "center", 16)

        start_x = 90
        for index, chapter_id in enumerate(CHAPTER_ORDER):
            chapter = CHAPTERS[chapter_id]
            rect = pygame.Rect(start_x + index * 238, 160, 210, 350)
            unlocked = chapter_unlocked(save_data, chapter_id)
            completed = chapter_id in save_data.get("completed_chapters", [])
            color = YELLOW if completed else CYAN if unlocked else (82, 88, 102)
            hovered = rect.collidepoint(mouse_pos)
            self.chapter_buttons.append({"action": "chapter", "chapter_id": chapter_id, "rect": rect.copy(), "disabled": not unlocked})
            self.draw_click_rect(rect, PANEL_DARK, color, hovered, not unlocked)
            pygame.draw.circle(self.surface, color, (rect.centerx, rect.y + 58), 32)
            self.draw_fit_text(str(index + 1), self.font, BLACK if unlocked else WHITE, pygame.Rect(rect.centerx - 18, rect.y + 40, 36, 36), "center", 18)
            self.draw_wrapped_text(chapter.name, self.font, WHITE, pygame.Rect(rect.x + 18, rect.y + 100, rect.width - 36, 52), "center", 2, 2, 18, "chapter")
            self.draw_wrapped_text(chapter.description, self.small_font, TEXT_MUTED, pygame.Rect(rect.x + 18, rect.y + 154, rect.width - 36, 78), "center", 3, 2, 14, "chapter")
            self.draw_wrapped_text(chapter.mechanic_name, self.small_font, color, pygame.Rect(rect.x + 18, rect.y + 250, rect.width - 36, 34), "center", 1, 1, 14, "chapter")
            status = "已通关" if completed else "可挑战" if unlocked else "未解锁"
            self.draw_fit_text(status, self.tiny_font, color, pygame.Rect(rect.x + 18, rect.bottom - 44, rect.width - 36, 28), "center", 14)

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 170, 594, 340, 44)
        self.chapter_buttons.append({"action": "back", "rect": back_rect.copy()})
        self.draw_button_row("Esc / M", "返回主菜单", back_rect, YELLOW, back_rect.collidepoint(mouse_pos))
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.chapter_buttons))

    def draw_endless_select(self, save_data):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.endless_buttons = {
            "start": pygame.Rect(SCREEN_WIDTH // 2 - 210, 440, 420, 46),
            "back": pygame.Rect(SCREEN_WIDTH // 2 - 210, 502, 420, 44),
        }
        self.draw_background(theme="throne")
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 330, 118, 660, 470)
        self.draw_panel(panel, PANEL_DARK, PURPLE)
        self.draw_text("无尽爬层", self.mid_font, WHITE, (panel.centerx, panel.y + 52), "center")
        lines = [
            "每 3 分钟进入下一层，敌人倍率和精英频率递增。",
            "Boss 会轮换出现；击败 Boss 后不会结算，继续爬层。",
            f"历史最高：第 {save_data.get('endless_highest_floor', 0)} 层",
            "死亡后保存金币、蓝图和最高层。",
        ]
        y = panel.y + 116
        for line in lines:
            self.draw_wrapped_text(line, self.small_font, TEXT_MUTED, pygame.Rect(panel.x + 58, y, panel.width - 116, 42), "center", 2, 2, 15)
            y += 58
        self.draw_button_row("Enter", "开始无尽爬层", self.endless_buttons["start"], PURPLE, self.endless_buttons["start"].collidepoint(mouse_pos))
        self.draw_button_row("Esc / M", "返回主菜单", self.endless_buttons["back"], YELLOW, self.endless_buttons["back"].collidepoint(mouse_pos))
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.endless_buttons.values()))

    def draw_character_select(self, save_data, message=""):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.character_buttons = []
        self.draw_background(theme="frost")
        self.draw_text("角色选择", self.mid_font, WHITE, (SCREEN_WIDTH // 2, 54), "center")
        selected = save_data.get("selected_character", "mage")
        unlocked = set(save_data.get("unlocked_characters", []))

        for index, (character_id, character) in enumerate(CHARACTERS.items()):
            col = index % 3
            row = index // 3
            rect = pygame.Rect(150 + col * 330, 125 + row * 220, 300, 184)
            is_unlocked = character_id in unlocked
            is_selected = character_id == selected
            border = YELLOW if is_selected else character.color if is_unlocked else (86, 92, 104)
            hovered = rect.collidepoint(mouse_pos)
            self.character_buttons.append({"action": "select", "character_id": character_id, "rect": rect.copy(), "disabled": not is_unlocked})
            self.draw_click_rect(rect, PANEL_DARK, border, hovered, not is_unlocked)
            pygame.draw.circle(self.surface, character.color, (rect.x + 45, rect.y + 44), 28)
            pygame.draw.circle(self.surface, WHITE, (rect.x + 45, rect.y + 44), 28, 2)
            self.draw_fit_text(character.name, self.font, WHITE, pygame.Rect(rect.x + 86, rect.y + 18, rect.width - 108, 32), "midleft", 18, "character")
            self.draw_fit_text(character.title, self.tiny_font, character.color, pygame.Rect(rect.x + 86, rect.y + 52, rect.width - 108, 26), "midleft", 13, "character")
            self.draw_wrapped_text(character.description, self.tiny_font, TEXT_MUTED, pygame.Rect(rect.x + 24, rect.y + 86, rect.width - 48, 46), "left", 2, 2, 13, "character")
            status = "已选择" if is_selected else "点击选择" if is_unlocked else "未解锁"
            self.draw_fit_text(status, self.tiny_font, border, pygame.Rect(rect.x + 24, rect.bottom - 34, rect.width - 48, 24), "center", 13)

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 170, 598, 340, 44)
        self.character_buttons.append({"action": "back", "rect": back_rect.copy()})
        self.draw_button_row("Esc / M", "返回主菜单", back_rect, YELLOW, back_rect.collidepoint(mouse_pos))
        if message:
            self.draw_fit_text(message, self.small_font, CYAN, pygame.Rect(SCREEN_WIDTH // 2 - 240, 648, 480, 28), "center", 14)
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.character_buttons))

    def draw_shop(self, save_data, message="", active_tab="upgrades", page=0):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.shop_buttons = []
        self.draw_background(theme="factory")
        self.draw_text("金币商城", self.mid_font, WHITE, (SCREEN_WIDTH // 2, 50), "center")
        self.draw_fit_text(
            f"金币 {save_data['total_gold']}   蓝图 角色:{save_data['blueprints']['character']} 武器:{save_data['blueprints']['weapon']} 道具:{save_data['blueprints']['item']}",
            self.small_font,
            YELLOW,
            pygame.Rect(230, 88, 820, 32),
            "center",
            15,
        )

        tabs = [("upgrades", "属性强化"), ("characters", "角色解锁"), ("weapons", "武器解锁"), ("items", "道具解锁")]
        tab_buttons = []
        for index, (tab, label) in enumerate(tabs):
            rect = pygame.Rect(150 + index * 250, 132, 220, 40)
            tab_buttons.append({"action": "tab", "tab": tab, "rect": rect.copy()})
            self.draw_click_rect(rect, PANEL_DARK, CYAN if tab == active_tab else (80, 92, 116), rect.collidepoint(mouse_pos))
            self.draw_fit_text(label, self.small_font, WHITE, rect.inflate(-12, -6), "center", 14)

        entries = self.shop_entries(save_data, active_tab)
        page_size = 4
        max_page = max(0, (len(entries) - 1) // page_size)
        page = max(0, min(page, max_page))
        y = 196
        for local_index, entry in enumerate(entries[page * page_size : page * page_size + page_size]):
            rect = pygame.Rect(170, y, 940, 78)
            disabled = not entry["can_buy"] and not entry.get("complete", False)
            border = GREEN if entry.get("complete") else YELLOW if entry["can_buy"] else (92, 104, 126)
            action = "upgrade" if active_tab == "upgrades" else "buy"
            self.shop_buttons.append(
                {
                    "action": action,
                    "tab": active_tab,
                    "id": entry["id"],
                    "index": page * page_size + local_index,
                    "rect": rect.copy(),
                    "disabled": disabled,
                }
            )
            self.draw_click_rect(rect, PANEL_DARK, border, rect.collidepoint(mouse_pos), disabled)
            self.draw_fit_text(entry["name"], self.font, WHITE, pygame.Rect(rect.x + 24, rect.y + 10, 330, 30), "midleft", 18, "shop")
            self.draw_wrapped_text(entry["description"], self.tiny_font, TEXT_MUTED, pygame.Rect(rect.x + 24, rect.y + 42, 590, 28), "left", 2, 1, 13, "shop")
            self.draw_fit_text(entry["status"], self.tiny_font, border, pygame.Rect(rect.right - 292, rect.y + 12, 268, 26), "midright", 13, "shop")
            self.draw_fit_text(entry["cost"], self.small_font, border, pygame.Rect(rect.right - 292, rect.y + 42, 268, 28), "midright", 14, "shop")
            y += 90

        self.shop_buttons.extend(tab_buttons)

        if max_page > 0:
            prev_rect = pygame.Rect(420, 574, 130, 38)
            next_rect = pygame.Rect(730, 574, 130, 38)
            self.shop_buttons.append({"action": "page", "delta": -1, "rect": prev_rect.copy()})
            self.shop_buttons.append({"action": "page", "delta": 1, "rect": next_rect.copy()})
            self.draw_button_row("<", "上一页", prev_rect, CYAN, prev_rect.collidepoint(mouse_pos))
            self.draw_button_row(">", "下一页", next_rect, CYAN, next_rect.collidepoint(mouse_pos))
            self.draw_fit_text(f"{page + 1}/{max_page + 1}", self.small_font, WHITE, pygame.Rect(560, 574, 160, 38), "center", 14)

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, 628, 360, 42)
        self.shop_buttons.append({"action": "back", "rect": back_rect.copy()})
        self.draw_button_row("Esc / M", "返回主菜单", back_rect, YELLOW, back_rect.collidepoint(mouse_pos))
        if message:
            self.draw_fit_text(message, self.small_font, CYAN, pygame.Rect(SCREEN_WIDTH // 2 - 300, 674, 600, 30), "center", 14)
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.shop_buttons))

    def shop_entries(self, save_data, active_tab):
        entries = []
        if active_tab == "upgrades":
            for upgrade_id, definition in PERMANENT_UPGRADES.items():
                level = save_data["permanent_upgrades"][upgrade_id]
                cost = get_permanent_upgrade_cost(upgrade_id, level)
                complete = cost is None
                entries.append({
                    "id": upgrade_id,
                    "name": f"{definition['name']} Lv.{level}/{definition['max_level']}",
                    "description": definition["description"],
                    "cost": "已满级" if complete else f"{cost} 金币",
                    "status": "已完成" if complete else "可购买" if save_data["total_gold"] >= cost else "金币不足",
                    "can_buy": cost is not None and save_data["total_gold"] >= cost,
                    "complete": complete,
                })
        elif active_tab == "characters":
            for character_id, definition in CHARACTER_UNLOCKS.items():
                complete = character_id in save_data["unlocked_characters"]
                can_buy = (not complete and requirement_met(save_data, definition.requirement) and save_data["total_gold"] >= definition.gold_cost and save_data["blueprints"][definition.blueprint_type] >= definition.blueprint_cost)
                entries.append({
                    "id": character_id,
                    "name": definition.name,
                    "description": definition.description,
                    "cost": f"{definition.gold_cost} 金币 + {definition.blueprint_cost} 角色蓝图",
                    "status": "已解锁" if complete else requirement_text(definition.requirement),
                    "can_buy": can_buy,
                    "complete": complete,
                })
        elif active_tab == "weapons":
            for weapon_id, definition in WEAPON_UNLOCKS.items():
                complete = weapon_id in save_data["unlocked_weapons"]
                can_buy = (not complete and requirement_met(save_data, definition.requirement) and save_data["total_gold"] >= definition.gold_cost and save_data["blueprints"][definition.blueprint_type] >= definition.blueprint_cost)
                entries.append({
                    "id": weapon_id,
                    "name": definition.name,
                    "description": definition.description,
                    "cost": f"{definition.gold_cost} 金币 + {definition.blueprint_cost} 武器蓝图",
                    "status": "已解锁" if complete else requirement_text(definition.requirement),
                    "can_buy": can_buy,
                    "complete": complete,
                })
        elif active_tab == "items":
            for item_id, definition in ITEM_DEFS.items():
                level = save_data["item_levels"].get(item_id, 0)
                cost = item_upgrade_cost(item_id, level)
                complete = cost is None
                blueprint_cost = definition["blueprint_cost"] if level == 0 else 0
                can_buy = (not complete and requirement_met(save_data, definition["requirement"]) and save_data["total_gold"] >= cost and save_data["blueprints"]["item"] >= blueprint_cost)
                entries.append({
                    "id": item_id,
                    "name": f"{definition['name']} Lv.{level}/{definition['max_level']}",
                    "description": definition["description"],
                    "cost": "已满级" if complete else f"{cost} 金币" + (f" + {blueprint_cost} 道具蓝图" if blueprint_cost else ""),
                    "status": "已满级" if complete else requirement_text(definition["requirement"]),
                    "can_buy": can_buy,
                    "complete": complete,
                })
        return entries

    def settings_label(self, value):
        return {"low": "低", "medium": "中", "high": "高"}.get(value, "高")

    def draw_settings_button(self, action, label, rect, color, mouse_pos, active=False, disabled=False):
        hovered = rect.collidepoint(mouse_pos)
        border_color = color if active else (80, 92, 116)
        self.settings_buttons.append({"action": action, "rect": rect.copy()})
        self.draw_click_rect(rect, PANEL_DARK, border_color, hovered, disabled)
        text_color = BLACK if active else WHITE
        if active:
            pygame.draw.rect(self.surface, color, rect.inflate(-6, -6), border_radius=6)
        self.draw_fit_text(label, self.small_font, text_color, rect.inflate(-10, -8), "center", 14, "settings")

    def draw_setting_label(self, title, description, rect):
        rect = pygame.Rect(rect)
        self.draw_fit_text(title, self.small_font, WHITE, pygame.Rect(rect.x, rect.y, rect.width, 28), "midleft", 16, "settings")
        self.draw_wrapped_text(description, self.tiny_font, TEXT_MUTED, pygame.Rect(rect.x, rect.y + 28, rect.width, 30), "left", 2, 1, 13, "settings")

    def draw_settings(self, settings_data, from_playing=False):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.settings_buttons = []
        detail = settings_data.get("background_detail", "high")
        if from_playing:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 176))
            self.surface.blit(overlay, (0, 0))
        else:
            self.draw_background(detail)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 360, 36, 720, 648)
        self.draw_panel(panel, PANEL_DARK, CYAN)
        self.draw_text("设置", self.mid_font, WHITE, (panel.centerx, panel.y + 46), "center")
        self.draw_fit_text("Esc 返回，设置会立即保存", self.tiny_font, TEXT_MUTED, pygame.Rect(panel.x + 60, panel.y + 82, panel.width - 120, 28), "center", 14, "settings")
        label_x = panel.x + 48
        control_x = panel.x + 390
        row_y = panel.y + 118
        row_gap = 62
        self.draw_setting_label("音效", "控制所有音效音量，可一键静音。", pygame.Rect(label_x, row_y, 300, 58))
        minus_rect = pygame.Rect(control_x, row_y + 10, 44, 38)
        volume_rect = pygame.Rect(control_x + 54, row_y + 10, 104, 38)
        plus_rect = pygame.Rect(control_x + 168, row_y + 10, 44, 38)
        mute_rect = pygame.Rect(control_x + 226, row_y + 10, 92, 38)
        self.draw_settings_button("volume_down", "-", minus_rect, CYAN, mouse_pos)
        self.draw_panel(volume_rect, PANEL_COLOR, (80, 92, 116))
        self.draw_fit_text(f"{settings_data.get('master_volume', 100)}%", self.small_font, WHITE, volume_rect, "center", 14, "settings")
        self.draw_settings_button("volume_up", "+", plus_rect, CYAN, mouse_pos)
        muted = settings_data.get("muted", False)
        self.draw_settings_button("muted", "静音" if muted else "有声", mute_rect, RED if muted else GREEN, mouse_pos, muted)
        row_y += row_gap
        self.draw_setting_label("特效档位", "影响粒子预算、拖尾频率和冲击波透明度。", pygame.Rect(label_x, row_y, 300, 58))
        self.draw_segmented_setting("effect_quality", settings_data.get("effect_quality", "high"), control_x, row_y + 10, mouse_pos)
        row_y += row_gap
        self.draw_setting_label("屏幕震动", "关闭后保留命中和受击反馈，但不再晃动画面。", pygame.Rect(label_x, row_y, 300, 58))
        screen_shake = settings_data.get("screen_shake", True)
        self.draw_settings_button("screen_shake", "开启" if screen_shake else "关闭", pygame.Rect(control_x, row_y + 10, 146, 38), GREEN if screen_shake else TEXT_MUTED, mouse_pos, screen_shake)
        row_y += row_gap
        self.draw_setting_label("伤害数字", "关闭后隐藏战斗伤害数字，拾取和升级提示保留。", pygame.Rect(label_x, row_y, 300, 58))
        damage_numbers = settings_data.get("damage_numbers", True)
        self.draw_settings_button("damage_numbers", "显示" if damage_numbers else "隐藏", pygame.Rect(control_x, row_y + 10, 146, 38), GREEN if damage_numbers else TEXT_MUTED, mouse_pos, damage_numbers)
        row_y += row_gap
        self.draw_setting_label("背景细节", "控制矿洞遗迹装饰密度，低档更利于性能。", pygame.Rect(label_x, row_y, 300, 58))
        self.draw_segmented_setting("background_detail", detail, control_x, row_y + 10, mouse_pos)
        row_y += row_gap
        self.draw_setting_label("窗口模式", "全屏只改变显示模式，逻辑分辨率保持 1280x720。", pygame.Rect(label_x, row_y, 300, 58))
        fullscreen = settings_data.get("fullscreen", False)
        self.draw_settings_button("fullscreen", "全屏" if fullscreen else "窗口", pygame.Rect(control_x, row_y + 10, 146, 38), PURPLE if fullscreen else CYAN, mouse_pos, fullscreen)
        back_rect = pygame.Rect(panel.centerx - 150, panel.bottom - 56, 300, 42)
        self.draw_settings_button("back", "返回", back_rect, YELLOW, mouse_pos)
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.settings_buttons))

    def draw_segmented_setting(self, name, current, x, y, mouse_pos):
        values = ("low", "medium", "high")
        colors = {"low": GREEN, "medium": CYAN, "high": YELLOW}
        for index, value in enumerate(values):
            rect = pygame.Rect(x + index * 108, y, 98, 38)
            self.draw_settings_button(f"{name}:{value}", self.settings_label(value), rect, colors[value], mouse_pos, current == value)

    def draw_hud(self, player, score, elapsed_time, duration, enemy_count, boss=None, mode="chapter", chapter=None, endless_floor=1, floor_timer=0, blueprints=None):
        self.draw_panel(pygame.Rect(18, 16, 568, 92))
        self.draw_fit_text(f"得分 {score}", self.small_font, WHITE, pygame.Rect(34, 26, 122, 30), "midleft", 16)
        self.draw_fit_text(f"金币 {player.run_gold}", self.small_font, YELLOW, pygame.Rect(170, 26, 120, 30), "midleft", 16)
        mode_text = chapter.name if mode == "chapter" and chapter else f"无尽 {endless_floor} 层"
        self.draw_fit_text(mode_text, self.small_font, CYAN, pygame.Rect(304, 26, 142, 30), "midleft", 16)
        target = duration if mode == "chapter" else 180
        current = elapsed_time if mode == "chapter" else floor_timer
        self.draw_fit_text(f"{self.format_time(current)} / {self.format_time(target)}", self.tiny_font, WHITE, pygame.Rect(452, 26, 116, 30), "midleft", 13)
        self.draw_text("生命", self.tiny_font, TEXT_MUTED, (34, 66))
        self.draw_bar(pygame.Rect(84, 68, 128, 14), player.health / max(1, player.max_health), RED)
        self.draw_text(f"{player.health}/{player.max_health}", self.tiny_font, WHITE, (222, 62))
        self.draw_text(f"等级 {player.level}", self.tiny_font, TEXT_MUTED, (304, 66))
        self.draw_bar(pygame.Rect(374, 68, 120, 14), player.exp / max(1, player.next_exp), CYAN)
        self.draw_skill_hud(player)
        self.draw_panel(pygame.Rect(SCREEN_WIDTH - 206, 16, 188, 50))
        self.draw_fit_text(f"敌人 {enemy_count}", self.small_font, WHITE, pygame.Rect(SCREEN_WIDTH - 186, 24, 148, 32), "midleft", 16)
        self.draw_weapon_slots(player)
        if blueprints and any(blueprints.values()):
            text = f"蓝图 角{blueprints.get('character', 0)} 武{blueprints.get('weapon', 0)} 道{blueprints.get('item', 0)}"
            self.draw_panel(pygame.Rect(18, 116, 210, 36), PANEL_DARK, PURPLE)
            self.draw_fit_text(text, self.tiny_font, PURPLE, pygame.Rect(30, 122, 186, 24), "midleft", 13)
        if boss and boss.alive():
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, SCREEN_HEIGHT - 42, 520, 20)
            self.draw_bar(rect, boss.health / max(1, boss.max_health), YELLOW)
            self.draw_text(chapter.boss_name if chapter else "Boss", self.small_font, WHITE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62), "center")

    def draw_skill_hud(self, player):
        rect = pygame.Rect(610, 18, 250, 62)
        self.draw_panel(rect, PANEL_DARK, player.character.color)
        self.draw_fit_text(player.character.name, self.tiny_font, TEXT_MUTED, pygame.Rect(rect.x + 16, rect.y + 8, 112, 20), "midleft", 12)
        self.draw_fit_text(player.character.active_name, self.small_font, WHITE, pygame.Rect(rect.x + 16, rect.y + 30, 146, 24), "midleft", 14)
        icon_rect = pygame.Rect(rect.right - 62, rect.y + 10, 42, 42)
        pygame.draw.circle(self.surface, player.character.color, icon_rect.center, 21)
        pygame.draw.circle(self.surface, WHITE, icon_rect.center, 21, 2)
        if not player.skill_ready():
            overlay = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            overlay_height = int(icon_rect.height * player.active_cooldown_ratio())
            self.surface.blit(overlay, icon_rect.topleft)
            self.draw_fit_text(str(int(player.active_timer) + 1), self.tiny_font, WHITE, icon_rect, "center", 12)

    def draw_weapon_slots(self, player):
        active = [(weapon_id, level) for weapon_id, level in player.weapons.items() if level > 0]
        if not active:
            return
        panel_width = min(366, 18 + len(active) * 56)
        panel = pygame.Rect(SCREEN_WIDTH - panel_width - 18, 78, panel_width, 54)
        self.draw_panel(panel, PANEL_DARK, (70, 84, 108))
        x = panel.x + 14
        for weapon_id, level in active[:6]:
            icon = self.load_weapon_icon(weapon_id, (30, 30))
            icon_rect = pygame.Rect(x, panel.y + 8, 30, 30)
            if icon:
                self.surface.blit(icon, icon_rect)
            else:
                pygame.draw.circle(self.surface, PURPLE, icon_rect.center, 14)
            if weapon_id in getattr(player, "weapon_evolutions", set()):
                pygame.draw.circle(self.surface, YELLOW, icon_rect.center, 17, 2)
            self.draw_fit_text(str(level), self.tiny_font, WHITE, pygame.Rect(x + 36, panel.y + 10, 16, 28), "midleft", 12)
            x += 56

    def draw_level_up(self, options):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.level_up_cards = []
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.surface.blit(overlay, (0, 0))
        self.draw_text("选择升级", self.mid_font, WHITE, (SCREEN_WIDTH // 2, 142), "center")
        start_x = SCREEN_WIDTH // 2 - 450
        for index, option in enumerate(options):
            rect = pygame.Rect(start_x + index * 310, 230, 280, 220)
            color = self.upgrade_color(option.id)
            hovered = rect.collidepoint(mouse_pos)
            self.level_up_cards.append((index, rect.copy()))
            self.draw_click_rect(rect, PANEL_DARK, color, hovered)
            self.draw_upgrade_icon((rect.centerx, rect.y + 48), color, option.id)
            self.draw_fit_text(str(index + 1), self.tiny_font, BLACK, pygame.Rect(rect.x + 12, rect.y + 10, 24, 24), "center", 14, "level_up")
            self.draw_wrapped_text(option.title, self.font, WHITE, pygame.Rect(rect.x + 24, rect.y + 78, rect.width - 48, 58), "center", 2, 2, 18, "level_up")
            self.draw_wrapped_text(option.description, self.small_font, TEXT_MUTED, pygame.Rect(rect.x + 24, rect.y + 134, rect.width - 48, 70), "center", 3, 2, 14, "level_up")
        self.draw_fit_text("按数字键 1-3 或点击卡片选择，本局暂停中", self.small_font, WHITE, pygame.Rect(SCREEN_WIDTH // 2 - 320, 506, 640, 34), "center", 16)
        self.update_cursor(any(rect.collidepoint(mouse_pos) for _, rect in self.level_up_cards))

    def upgrade_color(self, upgrade_id):
        if upgrade_id.startswith("evolve:"):
            return YELLOW
        if upgrade_id.startswith("weapon:"):
            return PURPLE
        if upgrade_id in ("damage", "fire_rate", "missile_count"):
            return YELLOW
        if upgrade_id == "max_health":
            return GREEN
        return CYAN

    def draw_upgrade_icon(self, center, color, upgrade_id):
        weapon_id = self.extract_weapon_id(upgrade_id)
        if weapon_id:
            icon = self.load_weapon_icon(weapon_id, (46, 46))
            if icon:
                pygame.draw.circle(self.surface, color, center, 26)
                pygame.draw.circle(self.surface, WHITE, center, 26, 2)
                self.surface.blit(icon, icon.get_rect(center=center))
                if upgrade_id.startswith("evolve:"):
                    pygame.draw.circle(self.surface, YELLOW, center, 29, 3)
                return
        pygame.draw.circle(self.surface, color, center, 22)
        pygame.draw.circle(self.surface, WHITE, center, 22, 2)
        x, y = center
        pygame.draw.rect(self.surface, BLACK, (x - 12, y - 4, 24, 8), border_radius=3)
        pygame.draw.rect(self.surface, BLACK, (x - 4, y - 12, 8, 24), border_radius=3)

    def extract_weapon_id(self, upgrade_id):
        if upgrade_id.startswith(("weapon:", "evolve:")):
            return upgrade_id.split(":", 1)[1]
        return None

    def load_weapon_icon(self, weapon_id, size):
        if not self.resources:
            return None
        image_names = {
            "missile": "magic_missile",
            "blade": "blade",
            "pulse": "pulse_icon",
            "flame": "flame_orb",
            "frost": "frost_shard",
            "drone": "drone",
        }
        name = image_names.get(weapon_id)
        if not name:
            return None
        return self.resources.load_image(name, size, lambda fallback_size: self.draw_weapon_icon_fallback(fallback_size, weapon_id))

    def draw_weapon_icon_fallback(self, size, weapon_id):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        center = (size[0] // 2, size[1] // 2)
        color = {
            "missile": CYAN,
            "blade": WHITE,
            "pulse": BLUE,
            "flame": (255, 124, 42),
            "frost": (170, 238, 255),
            "drone": YELLOW,
        }.get(weapon_id, PURPLE)
        pygame.draw.circle(surface, color, center, min(size) // 2 - 3)
        pygame.draw.circle(surface, WHITE, center, min(size) // 2 - 3, 2)
        return surface

    def draw_result(self, title, player, score, elapsed_time, save_data, blueprints=None, mode="chapter", endless_floor=1):
        mouse_pos = self.mouse_pos()
        self.last_text_rects = {}
        self.result_buttons = {
            "restart": pygame.Rect(SCREEN_WIDTH // 2 - 235, 542, 220, 44),
            "menu": pygame.Rect(SCREEN_WIDTH // 2 + 15, 542, 220, 44),
        }
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.surface.blit(overlay, (0, 0))
        self.draw_text(title, self.big_font, WHITE, (SCREEN_WIDTH // 2, 118), "center")
        self.draw_panel(pygame.Rect(SCREEN_WIDTH // 2 - 260, 214, 520, 288), PANEL_DARK)
        lines = [
            f"本局得分：{score}",
            f"本局金币：{player.run_gold}",
            f"生存时间：{self.format_time(elapsed_time)}",
            f"最高分：{save_data['high_score']}",
            f"总金币：{save_data['total_gold']}",
        ]
        if mode == "endless":
            lines.append(f"无尽层数：第 {endless_floor} 层 / 最高 {save_data.get('endless_highest_floor', 0)} 层")
        if blueprints and any(blueprints.values()):
            lines.append(f"蓝图收益：角色 {blueprints.get('character', 0)}  武器 {blueprints.get('weapon', 0)}  道具 {blueprints.get('item', 0)}")
        for index, line in enumerate(lines[:7]):
            self.draw_fit_text(line, self.font, WHITE if index < 3 else TEXT_MUTED, pygame.Rect(SCREEN_WIDTH // 2 - 220, 232 + index * 36, 440, 34), "center", 18, "result")
        self.draw_button_row("R", "重新开始", self.result_buttons["restart"], CYAN, self.result_buttons["restart"].collidepoint(mouse_pos))
        self.draw_button_row("M", "返回主菜单", self.result_buttons["menu"], YELLOW, self.result_buttons["menu"].collidepoint(mouse_pos))
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.result_buttons.values()))
