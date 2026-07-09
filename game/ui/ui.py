import pygame

from game.config.settings import *
from game.systems.save_data import PERMANENT_UPGRADES, get_permanent_upgrade_cost


class UI:
    def __init__(self, surface):
        self.surface = surface
        self.font = self.get_font(30)
        self.big_font = self.get_font(68)
        self.mid_font = self.get_font(42)
        self.small_font = self.get_font(24)
        self.tiny_font = self.get_font(20)
        self.menu_buttons = {}
        self.shop_buttons = []
        self.level_up_cards = []
        self.result_buttons = {}

    def get_font(self, size):
        # 优先使用常见中文字体，避免中文显示成方块
        font_names = ["microsoftyahei", "simhei", "simsun", "nsimsun"]
        for font_name in font_names:
            font_path = pygame.font.match_font(font_name)
            if font_path:
                return pygame.font.Font(font_path, size)

        return pygame.font.Font(None, size)

    def draw_text(self, text, font, color, pos, anchor="topleft"):
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(**{anchor: pos})
        self.surface.blit(text_surface, rect)
        return rect

    def draw_background(self):
        self.surface.fill(BG_COLOR)
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.surface, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y), 1)

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
        self.draw_text(f"得分 {score}", self.small_font, WHITE, (34, 28))
        self.draw_text(f"金币 {player.run_gold}", self.small_font, YELLOW, (170, 28))
        self.draw_text(f"时间 {self.format_time(elapsed_time)} / {self.format_time(duration)}", self.small_font, WHITE, (304, 28))

        health_ratio = player.health / max(1, player.max_health)
        self.draw_text("生命", self.tiny_font, TEXT_MUTED, (34, 64))
        self.draw_bar(pygame.Rect(84, 66, 128, 14), health_ratio, RED)
        self.draw_text(f"{player.health}/{player.max_health}", self.tiny_font, WHITE, (222, 60))

        exp_ratio = player.exp / max(1, player.next_exp)
        self.draw_text(f"等级 {player.level}", self.tiny_font, TEXT_MUTED, (304, 64))
        self.draw_bar(pygame.Rect(374, 66, 120, 14), exp_ratio, CYAN)

        self.draw_panel(pygame.Rect(SCREEN_WIDTH - 206, 16, 188, 50))
        self.draw_text(f"敌人 {enemy_count}", self.small_font, WHITE, (SCREEN_WIDTH - 186, 28))

        if boss and boss.alive():
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, SCREEN_HEIGHT - 42, 520, 20)
            self.draw_bar(rect, boss.health / max(1, boss.max_health), YELLOW)
            self.draw_text("金币领主", self.small_font, WHITE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62), "center")

    def draw_menu(self, save_data):
        mouse_pos = pygame.mouse.get_pos()
        self.menu_buttons = {
            "start": pygame.Rect(SCREEN_WIDTH // 2 - 205, 370, 410, 44),
            "shop": pygame.Rect(SCREEN_WIDTH // 2 - 205, 426, 410, 44),
        }

        self.draw_background()
        self.draw_text("金币冲刺", self.big_font, WHITE, (SCREEN_WIDTH // 2, 112), "center")
        self.draw_text("幸存者式肉鸽", self.mid_font, CYAN, (SCREEN_WIDTH // 2, 184), "center")

        self.draw_preview_strip()

        self.draw_panel(pygame.Rect(SCREEN_WIDTH // 2 - 260, 354, 520, 170), PANEL_DARK, CYAN)
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
        self.draw_text(record_text, self.tiny_font, TEXT_MUTED, (SCREEN_WIDTH // 2, 494), "center")
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.menu_buttons.values()))

    def draw_button_row(self, key_text, label, rect, color, hovered=False):
        self.draw_click_rect(rect, PANEL_DARK, color, hovered)
        key_width = 150 if rect.width >= 320 else 70
        key_rect = pygame.Rect(rect.x + 18, rect.y + 4, key_width, 36)
        pygame.draw.rect(self.surface, self.lighten(color, 10) if hovered else color, key_rect, border_radius=6)
        self.draw_text(key_text, self.tiny_font, BLACK, key_rect.center, "center")
        self.draw_text(label, self.small_font, WHITE, (key_rect.right + 18, rect.centery), "midleft")

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
            self.draw_text(f"{index}. {definition['name']}  Lv.{level}/{definition['max_level']}", self.font, WHITE, (244, y + 14))
            self.draw_text(definition["description"], self.small_font, TEXT_MUTED, (244, y + 48))
            cost_text = "已满级" if cost is None else f"{cost} 金币"
            color = GREEN if cost is None else YELLOW if can_buy else TEXT_MUTED
            self.draw_text(cost_text, self.font, color, (1038, y + 28), "midright")
            y += 96

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, 596, 360, 42)
        self.shop_buttons.append({"action": "back", "rect": back_rect.copy()})
        self.draw_button_row("Esc / M", "返回主菜单", back_rect, CYAN, back_rect.collidepoint(mouse_pos))
        self.draw_text("按 1-4 或点击升级项购买", self.small_font, WHITE, (SCREEN_WIDTH // 2, 560), "center")
        if message:
            self.draw_text(message, self.small_font, CYAN, (SCREEN_WIDTH // 2, 646), "center")
        self.update_cursor(any(button["rect"].collidepoint(mouse_pos) for button in self.shop_buttons))

    def draw_level_up(self, options):
        mouse_pos = pygame.mouse.get_pos()
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
            self.draw_text(str(index + 1), self.tiny_font, BLACK, (rect.x + 22, rect.y + 22), "center")
            self.draw_text(option.title, self.font, WHITE, (rect.centerx, rect.y + 92), "center")
            self.draw_text(option.description, self.small_font, TEXT_MUTED, (rect.centerx, rect.y + 142), "center")

        self.draw_text("按数字键 1-3 或点击卡片选择，本局暂停中", self.small_font, WHITE, (SCREEN_WIDTH // 2, 520), "center")
        self.update_cursor(any(rect.collidepoint(mouse_pos) for _, rect in self.level_up_cards))

    def upgrade_color(self, upgrade_id):
        if upgrade_id.startswith("weapon:"):
            return PURPLE
        if upgrade_id in ("damage", "fire_rate", "missile_count"):
            return YELLOW
        if upgrade_id in ("max_health",):
            return GREEN
        return CYAN

    def draw_upgrade_icon(self, center, color, upgrade_id):
        pygame.draw.circle(self.surface, color, center, 22)
        pygame.draw.circle(self.surface, WHITE, center, 22, 2)
        x, y = center
        if upgrade_id.startswith("weapon:"):
            pygame.draw.polygon(self.surface, BLACK, [(x, y - 13), (x + 13, y), (x, y + 13), (x - 13, y)])
        elif upgrade_id == "max_health":
            pygame.draw.circle(self.surface, BLACK, (x - 6, y - 4), 6)
            pygame.draw.circle(self.surface, BLACK, (x + 6, y - 4), 6)
            pygame.draw.polygon(self.surface, BLACK, [(x - 12, y), (x + 12, y), (x, y + 13)])
        else:
            pygame.draw.rect(self.surface, BLACK, (x - 12, y - 4, 24, 8), border_radius=3)
            pygame.draw.rect(self.surface, BLACK, (x - 4, y - 12, 8, 24), border_radius=3)

    def draw_result(self, title, player, score, elapsed_time, save_data):
        mouse_pos = pygame.mouse.get_pos()
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
            self.draw_text(line, self.font, WHITE if index < 3 else TEXT_MUTED, (SCREEN_WIDTH // 2, 278 + index * 36), "center")

        self.draw_button_row("R", "重新开始", self.result_buttons["restart"], CYAN, self.result_buttons["restart"].collidepoint(mouse_pos))
        self.draw_button_row("M", "返回主菜单", self.result_buttons["menu"], YELLOW, self.result_buttons["menu"].collidepoint(mouse_pos))
        self.update_cursor(any(rect.collidepoint(mouse_pos) for rect in self.result_buttons.values()))
