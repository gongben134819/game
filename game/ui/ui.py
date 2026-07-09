import random

import pygame

from game.config.settings import *
from game.systems.save_data import PERMANENT_UPGRADES, get_permanent_upgrade_cost


class UI:
    def __init__(self, surface, resources=None):
        self.surface = surface
        self.resources = resources
        self.font_sizes = {}
        self.font = self.get_font(30)
        self.big_font = self.get_font(68)
        self.mid_font = self.get_font(42)
        self.small_font = self.get_font(24)
        self.tiny_font = self.get_font(20)
        self.menu_buttons = {}
        self.shop_buttons = []
        self.level_up_cards = []
        self.result_buttons = {}
        self.settings_buttons = []
        self.last_text_rects = {}
        self.background_decor = self.build_background_decor()

    def get_font(self, size):
        # 优先使用常见中文字体，避免中文显示成方块
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
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(**{anchor: pos})
        self.surface.blit(text_surface, rect)
        return rect

    def remember_text_rect(self, key, rect):
        if key is None:
            return
        self.last_text_rects.setdefault(key, []).append(rect.copy())

    def draw_fit_text(self, text, font, color, rect, anchor="center", min_size=16, key=None):
        rect = pygame.Rect(rect)
        text = str(text)
        selected_font = font
        text_surface = selected_font.render(text, True, color)

        if text_surface.get_width() > rect.width or text_surface.get_height() > rect.height:
            start_size = self.font_sizes.get(id(font), max(min_size, font.get_height() - 4))
            for size in range(start_size, min_size - 1, -1):
                candidate = self.get_font(size)
                candidate_surface = candidate.render(text, True, color)
                if candidate_surface.get_width() <= rect.width and candidate_surface.get_height() <= rect.height:
                    selected_font = candidate
                    text_surface = candidate_surface
                    break

        if text_surface.get_width() > rect.width:
            ellipsis = "…"
            clipped = text
            fitted = False
            while clipped:
                candidate = clipped[:-1] + ellipsis
                text_surface = selected_font.render(candidate, True, color)
                if text_surface.get_width() <= rect.width:
                    text = candidate
                    fitted = True
                    break
                clipped = clipped[:-1]
            if not fitted:
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

    def draw_wrapped_text(
        self,
        text,
        font,
        color,
        rect,
        align="center",
        max_lines=3,
        line_gap=4,
        min_size=16,
        key=None,
    ):
        rect = pygame.Rect(rect)
        selected_font = font
        lines = self.wrap_text(text, selected_font, rect.width)

        start_size = self.font_sizes.get(id(font), max(min_size, font.get_height() - 4))
        found_size = False
        for size in range(start_size, min_size - 1, -1):
            candidate_font = self.get_font(size)
            candidate_lines = self.wrap_text(text, candidate_font, rect.width)
            line_height = candidate_font.get_linesize()
            visible_lines = min(len(candidate_lines), max_lines)
            total_height = visible_lines * line_height + max(0, visible_lines - 1) * line_gap
            if total_height <= rect.height:
                selected_font = candidate_font
                lines = candidate_lines
                found_size = True
                break
        if not found_size:
            selected_font = self.get_font(min_size)
            lines = self.wrap_text(text, selected_font, rect.width)

        overflow = len(lines) > max_lines
        lines = lines[:max_lines]
        if overflow and lines:
            ellipsis = "…"
            clipped = lines[-1]
            while clipped and selected_font.size(clipped + ellipsis)[0] > rect.width:
                clipped = clipped[:-1]
            lines[-1] = clipped + ellipsis

        line_height = selected_font.get_linesize()
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
        y = rect.centery - total_height // 2
        rendered_rects = []
        for line in lines:
            text_surface = selected_font.render(line, True, color)
            line_rect = text_surface.get_rect()
            if align == "left":
                line_rect.midleft = (rect.left, y + line_height // 2)
            elif align == "right":
                line_rect.midright = (rect.right, y + line_height // 2)
            else:
                line_rect.center = (rect.centerx, y + line_height // 2)
            self.surface.blit(text_surface, line_rect)
            rendered_rects.append(line_rect.copy())
            self.remember_text_rect(key, line_rect)
            y += line_height + line_gap
        return rendered_rects

    def build_background_decor(self):
        rng = random.Random(20260709)
        decor = {"stones": [], "cracks": [], "veins": [], "gold": []}
        for _ in range(44):
            width = rng.randrange(28, 92)
            height = rng.randrange(12, 38)
            rect = pygame.Rect(rng.randrange(0, SCREEN_WIDTH - width), rng.randrange(0, SCREEN_HEIGHT - height), width, height)
            color = rng.choice(((18, 24, 31), (20, 28, 37), (24, 31, 39), (15, 20, 27)))
            decor["stones"].append((rect, color))
        for _ in range(24):
            start = (rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT))
            points = [start]
            for _ in range(rng.randrange(2, 5)):
                last_x, last_y = points[-1]
                points.append((max(0, min(SCREEN_WIDTH, last_x + rng.randrange(-34, 35))), max(0, min(SCREEN_HEIGHT, last_y + rng.randrange(-22, 23)))))
            decor["cracks"].append(points)
        for _ in range(10):
            start = (rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT))
            points = [start]
            for _ in range(rng.randrange(3, 7)):
                last_x, last_y = points[-1]
                points.append((max(0, min(SCREEN_WIDTH, last_x + rng.randrange(-60, 61))), max(0, min(SCREEN_HEIGHT, last_y + rng.randrange(-30, 31)))))
            decor["veins"].append(points)
        for _ in range(120):
            decor["gold"].append((rng.randrange(0, SCREEN_WIDTH), rng.randrange(0, SCREEN_HEIGHT), rng.randrange(1, 3)))
        return decor

    def background_item_count(self, detail="high"):
        if detail == "low":
            return {
                "stones": 0,
                "cracks": 0,
                "veins": 0,
                "gold": 0,
            }
        if detail == "medium":
            return {
                "stones": len(self.background_decor["stones"]) // 2,
                "cracks": len(self.background_decor["cracks"]) // 2,
                "veins": len(self.background_decor["veins"]) // 2,
                "gold": len(self.background_decor["gold"]) // 2,
            }
        return {
            "stones": len(self.background_decor["stones"]),
            "cracks": len(self.background_decor["cracks"]),
            "veins": len(self.background_decor["veins"]),
            "gold": len(self.background_decor["gold"]),
        }

    def draw_background(self, detail="high"):
        counts = self.background_item_count(detail)
        self.surface.fill((9, 12, 16))
        for rect, color in self.background_decor["stones"][: counts["stones"]]:
            pygame.draw.rect(self.surface, color, rect, border_radius=3)
            pygame.draw.rect(self.surface, (12, 16, 22), rect, 1, border_radius=3)
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.surface, (18, 25, 33), (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.surface, (18, 25, 33), (0, y), (SCREEN_WIDTH, y), 1)
        for points in self.background_decor["veins"][: counts["veins"]]:
            pygame.draw.lines(self.surface, (72, 60, 30), False, points, 2)
            pygame.draw.lines(self.surface, (126, 94, 38), False, points, 1)
        for points in self.background_decor["cracks"][: counts["cracks"]]:
            pygame.draw.lines(self.surface, (5, 8, 12), False, points, 2)
            pygame.draw.lines(self.surface, (32, 39, 46), False, points, 1)
        for x, y, radius in self.background_decor["gold"][: counts["gold"]]:
            pygame.draw.circle(self.surface, (92, 72, 28), (x, y), radius)
            if radius > 1:
                pygame.draw.circle(self.surface, (152, 114, 38), (x, y), 1)
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
            cursor = pygame.SYSTEM_CURSOR_HAND if hovering else pygame.SYSTEM_CURSOR_ARROW
            pygame.mouse.set_cursor(cursor)
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
        for action, rect in self.menu_buttons.items():
            if rect.collidepoint(pos):
                return action
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

    def draw_hud(self, player, score, elapsed_time, duration, enemy_count, boss=None):
        self.draw_panel(pygame.Rect(18, 16, 500, 82))
        self.draw_fit_text(f"得分 {score}", self.small_font, WHITE, pygame.Rect(34, 26, 122, 30), "midleft", 16)
        self.draw_fit_text(f"金币 {player.run_gold}", self.small_font, YELLOW, pygame.Rect(170, 26, 120, 30), "midleft", 16)
        self.draw_fit_text(f"时间 {self.format_time(elapsed_time)} / {self.format_time(duration)}", self.small_font, WHITE, pygame.Rect(304, 26, 198, 30), "midleft", 16)

        health_ratio = player.health / max(1, player.max_health)
        self.draw_text("生命", self.tiny_font, TEXT_MUTED, (34, 64))
        self.draw_bar(pygame.Rect(84, 66, 128, 14), health_ratio, RED)
        self.draw_text(f"{player.health}/{player.max_health}", self.tiny_font, WHITE, (222, 60))

        exp_ratio = player.exp / max(1, player.next_exp)
        self.draw_text(f"等级 {player.level}", self.tiny_font, TEXT_MUTED, (304, 64))
        self.draw_bar(pygame.Rect(374, 66, 120, 14), exp_ratio, CYAN)

        self.draw_panel(pygame.Rect(SCREEN_WIDTH - 206, 16, 188, 50))
        self.draw_fit_text(f"敌人 {enemy_count}", self.small_font, WHITE, pygame.Rect(SCREEN_WIDTH - 186, 24, 148, 32), "midleft", 16)
        self.draw_weapon_slots(player)

        if boss and boss.alive():
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, SCREEN_HEIGHT - 42, 520, 20)
            self.draw_bar(rect, boss.health / max(1, boss.max_health), YELLOW)
            self.draw_text("金币领主", self.small_font, WHITE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62), "center")

    def draw_menu_legacy(self, save_data):
        mouse_pos = pygame.mouse.get_pos()
        self.last_text_rects = {}
        self.menu_buttons = {
            "start": pygame.Rect(SCREEN_WIDTH // 2 - 205, 358, 410, 44),
            "shop": pygame.Rect(SCREEN_WIDTH // 2 - 205, 414, 410, 44),
            "settings": pygame.Rect(SCREEN_WIDTH // 2 - 205, 470, 410, 44),
        }

        self.draw_background()
        self.draw_text("金币冲刺", self.big_font, WHITE, (SCREEN_WIDTH // 2, 112), "center")
        self.draw_text("幸存者式肉鸽", self.mid_font, CYAN, (SCREEN_WIDTH // 2, 184), "center")

        self.draw_preview_strip()

        self.draw_panel(pygame.Rect(SCREEN_WIDTH // 2 - 260, 342, 520, 222), PANEL_DARK, CYAN)
        self.draw_button_row(
            "Enter / Space",
            "开始新游戏",
            self.menu_buttons["start"],
            CYAN,
            self.menu_buttons["start"].collidepoint(mouse_pos),
        )
        self.draw_button_row(
            "S",
            "永久升级商店",
            self.menu_buttons["shop"],
            YELLOW,
            self.menu_buttons["shop"].collidepoint(mouse_pos),
        )

        record_text = f"最高分 {save_data['high_score']}    最长生存 {self.format_time(save_data['longest_time'])}    总金币 {save_data['total_gold']}"
        self.draw_fit_text(record_text, self.tiny_font, TEXT_MUTED, pygame.Rect(SCREEN_WIDTH // 2 - 245, 482, 490, 28), "center", 14)
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.menu_buttons.values()))

    def draw_menu(self, save_data):
        mouse_pos = pygame.mouse.get_pos()
        self.last_text_rects = {}
        self.menu_buttons = {
            "start": pygame.Rect(SCREEN_WIDTH // 2 - 205, 352, 410, 44),
            "shop": pygame.Rect(SCREEN_WIDTH // 2 - 205, 408, 410, 44),
            "settings": pygame.Rect(SCREEN_WIDTH // 2 - 205, 464, 410, 44),
        }

        self.draw_background()
        self.draw_text("金币冲刺", self.big_font, WHITE, (SCREEN_WIDTH // 2, 112), "center")
        self.draw_text("幸存者式肉鸽", self.mid_font, CYAN, (SCREEN_WIDTH // 2, 184), "center")
        self.draw_preview_strip()

        self.draw_panel(pygame.Rect(SCREEN_WIDTH // 2 - 260, 336, 520, 228), PANEL_DARK, CYAN)
        self.draw_button_row(
            "Enter / Space",
            "开始新游戏",
            self.menu_buttons["start"],
            CYAN,
            self.menu_buttons["start"].collidepoint(mouse_pos),
        )
        self.draw_button_row(
            "S",
            "永久升级商店",
            self.menu_buttons["shop"],
            YELLOW,
            self.menu_buttons["shop"].collidepoint(mouse_pos),
        )
        self.draw_button_row(
            "O",
            "设置",
            self.menu_buttons["settings"],
            PURPLE,
            self.menu_buttons["settings"].collidepoint(mouse_pos),
        )

        record_text = f"最高分 {save_data['high_score']}    最长生存 {self.format_time(save_data['longest_time'])}    总金币 {save_data['total_gold']}"
        self.draw_fit_text(record_text, self.tiny_font, TEXT_MUTED, pygame.Rect(SCREEN_WIDTH // 2 - 245, 522, 490, 28), "center", 14)
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.menu_buttons.values()))

    def settings_label(self, value):
        return {
            "low": "低",
            "medium": "中",
            "high": "高",
        }.get(value, "高")

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
        rect.height = min(rect.height, 52)
        self.draw_fit_text(title, self.small_font, WHITE, pygame.Rect(rect.x, rect.y, rect.width, 28), "midleft", 16, "settings")
        self.draw_wrapped_text(description, self.tiny_font, TEXT_MUTED, pygame.Rect(rect.x, rect.y + 28, rect.width, 30), "left", 2, 1, 13, "settings")

    def draw_settings(self, settings_data, from_playing=False):
        mouse_pos = pygame.mouse.get_pos()
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
        self.draw_fit_text(
            "Esc 返回，设置会立即保存",
            self.tiny_font,
            TEXT_MUTED,
            pygame.Rect(panel.x + 60, panel.y + 82, panel.width - 120, 28),
            "center",
            14,
            "settings",
        )

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
            self.draw_settings_button(
                f"{name}:{value}",
                self.settings_label(value),
                rect,
                colors[value],
                mouse_pos,
                current == value,
            )

    def draw_button_row(self, key_text, label, rect, color, hovered=False):
        self.draw_click_rect(rect, PANEL_DARK, color, hovered)
        key_width = 150 if rect.width >= 320 else 70
        key_rect = pygame.Rect(rect.x + 18, rect.y + 4, key_width, 36)
        pygame.draw.rect(self.surface, self.lighten(color, 10) if hovered else color, key_rect, border_radius=6)
        self.draw_fit_text(key_text, self.tiny_font, BLACK, key_rect.inflate(-8, -4), "center", 13, "button")
        label_rect = pygame.Rect(key_rect.right + 18, rect.y + 4, rect.right - key_rect.right - 32, rect.height - 8)
        self.draw_fit_text(label, self.small_font, WHITE, label_rect, "midleft", 16, "button")

    def draw_preview_strip(self):
        y = 278
        pygame.draw.line(self.surface, (56, 76, 102), (392, y), (888, y), 2)
        self.draw_preview_sprite((514, y), PLAYER_COLOR, PLAYER_OUTLINE, 34, "player")
        self.draw_preview_sprite((628, y), ENEMY_COLOR, ENEMY_CORE, 30, "diamond")
        self.draw_preview_sprite((740, y), (150, 100, 240), (66, 38, 124), 30, "diamond")
        self.draw_preview_sprite((852, y), YELLOW, (145, 77, 34), 38, "boss")

    def draw_preview_sprite(self, center, color, core, size, kind):
        x, y = center
        if kind == "player":
            pygame.draw.circle(self.surface, color, center, size // 2)
            pygame.draw.circle(self.surface, core, center, size // 2, 3)
            pygame.draw.circle(self.surface, WHITE, (x + 7, y - 6), 4)
        elif kind == "boss":
            rect = pygame.Rect(0, 0, size, size)
            rect.center = center
            pygame.draw.rect(self.surface, color, rect, border_radius=6)
            pygame.draw.circle(self.surface, core, center, size // 4)
            pygame.draw.rect(self.surface, WHITE, (x - 10, y - 18, 20, 5), border_radius=2)
        else:
            half = size // 2
            pygame.draw.polygon(self.surface, color, [(x, y - half), (x + half, y), (x, y + half), (x - half, y)])
            pygame.draw.circle(self.surface, core, center, max(5, size // 5))

    def draw_shop(self, save_data, message=""):
        mouse_pos = pygame.mouse.get_pos()
        self.last_text_rects = {}
        self.shop_buttons = []

        self.draw_background()
        self.draw_text("永久升级商店", self.mid_font, WHITE, (SCREEN_WIDTH // 2, 64), "center")
        self.draw_text(f"总金币：{save_data['total_gold']}", self.font, YELLOW, (SCREEN_WIDTH // 2, 118), "center")

        y = 178
        for index, (upgrade_id, definition) in enumerate(PERMANENT_UPGRADES.items(), start=1):
            level = save_data["permanent_upgrades"][upgrade_id]
            cost = get_permanent_upgrade_cost(upgrade_id, level)
            rect = pygame.Rect(220, y, 840, 82)
            can_buy = cost is not None and save_data["total_gold"] >= cost
            border_color = GREEN if cost is None else YELLOW if can_buy else (92, 104, 126)
            hovered = rect.collidepoint(mouse_pos)
            self.shop_buttons.append({"action": "upgrade", "index": index - 1, "rect": rect.copy()})
            self.draw_click_rect(rect, PANEL_DARK, border_color, hovered, disabled=cost is not None and not can_buy)
            self.draw_fit_text(
                f"{index}. {definition['name']}  Lv.{level}/{definition['max_level']}",
                self.font,
                WHITE,
                pygame.Rect(244, y + 10, 580, 34),
                "midleft",
                18,
                "shop",
            )
            self.draw_wrapped_text(
                definition["description"],
                self.small_font,
                TEXT_MUTED,
                pygame.Rect(244, y + 43, 610, 32),
                "left",
                2,
                2,
                14,
                "shop",
            )
            cost_text = "已满级" if cost is None else f"{cost} 金币"
            color = GREEN if cost is None else YELLOW if can_buy else TEXT_MUTED
            self.draw_fit_text(cost_text, self.font, color, pygame.Rect(858, y + 18, 180, 40), "midright", 18, "shop")
            y += 96

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, 596, 360, 42)
        self.shop_buttons.append({"action": "back", "rect": back_rect.copy()})
        self.draw_button_row("Esc / M", "返回主菜单", back_rect, CYAN, back_rect.collidepoint(mouse_pos))
        self.draw_fit_text("按 1-4 或点击升级项购买", self.small_font, WHITE, pygame.Rect(SCREEN_WIDTH // 2 - 220, 546, 440, 30), "center", 16)
        if message:
            self.draw_fit_text(message, self.small_font, CYAN, pygame.Rect(SCREEN_WIDTH // 2 - 250, 632, 500, 30), "center", 16)
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.shop_buttons))

    def draw_level_up(self, options):
        mouse_pos = pygame.mouse.get_pos()
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
        if upgrade_id in ("max_health",):
            return GREEN
        return CYAN

    def draw_upgrade_icon(self, center, color, upgrade_id):
        weapon_id = self.extract_weapon_id(upgrade_id)
        if weapon_id:
            icon = self.load_weapon_icon(weapon_id, (46, 46))
            if icon:
                rect = icon.get_rect(center=center)
                pygame.draw.circle(self.surface, color, center, 26)
                pygame.draw.circle(self.surface, WHITE, center, 26, 2)
                self.surface.blit(icon, rect)
                if upgrade_id.startswith("evolve:"):
                    pygame.draw.circle(self.surface, YELLOW, center, 29, 3)
                return

        pygame.draw.circle(self.surface, color, center, 22)
        pygame.draw.circle(self.surface, WHITE, center, 22, 2)
        x, y = center
        if upgrade_id.startswith(("weapon:", "evolve:")):
            pygame.draw.polygon(self.surface, BLACK, [(x, y - 13), (x + 13, y), (x, y + 13), (x - 13, y)])
        elif upgrade_id == "max_health":
            pygame.draw.circle(self.surface, BLACK, (x - 6, y - 4), 6)
            pygame.draw.circle(self.surface, BLACK, (x + 6, y - 4), 6)
            pygame.draw.polygon(self.surface, BLACK, [(x - 12, y), (x + 12, y), (x, y + 13)])
        else:
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

    def draw_result(self, title, player, score, elapsed_time, save_data):
        mouse_pos = pygame.mouse.get_pos()
        self.last_text_rects = {}
        self.result_buttons = {
            "restart": pygame.Rect(SCREEN_WIDTH // 2 - 235, 526, 220, 44),
            "menu": pygame.Rect(SCREEN_WIDTH // 2 + 15, 526, 220, 44),
        }

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.surface.blit(overlay, (0, 0))

        self.draw_text(title, self.big_font, WHITE, (SCREEN_WIDTH // 2, 148), "center")
        self.draw_panel(pygame.Rect(SCREEN_WIDTH // 2 - 235, 250, 470, 220), PANEL_DARK)
        lines = [
            f"本局得分：{score}",
            f"本局金币：{player.run_gold}",
            f"生存时间：{self.format_time(elapsed_time)}",
            f"最高分：{save_data['high_score']}",
            f"总金币：{save_data['total_gold']}",
        ]
        for index, line in enumerate(lines):
            self.draw_fit_text(
                line,
                self.font,
                WHITE if index < 3 else TEXT_MUTED,
                pygame.Rect(SCREEN_WIDTH // 2 - 200, 264 + index * 36, 400, 34),
                "center",
                18,
                "result",
            )

        self.draw_button_row("R", "重新开始", self.result_buttons["restart"], CYAN, self.result_buttons["restart"].collidepoint(mouse_pos))
        self.draw_button_row("M", "返回主菜单", self.result_buttons["menu"], YELLOW, self.result_buttons["menu"].collidepoint(mouse_pos))
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.result_buttons.values()))
