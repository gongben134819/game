import random

import pygame

from game.config.settings import *
from game.entities.drop import Drop
from game.entities.enemy import ENEMY_TYPES, Enemy
from game.entities.player import Player
from game.systems.effects import FloatingText, ScreenShake, burst_particles, trim_group
from game.systems.resources import ResourceManager
from game.systems.save_data import PERMANENT_UPGRADES, load_save, purchase_upgrade, record_run, save_game
from game.systems.upgrades import apply_upgrade, choose_upgrade_options
from game.systems.weapons import WeaponController
from game.ui.ui import UI


DROP_EFFECT_COLORS = {
    "exp": CYAN,
    "gold": YELLOW,
    "heart": GREEN,
    "magnet": PURPLE,
}


class Level:
    MENU = "menu"
    PLAYING = "playing"
    LEVEL_UP = "level_up"
    SHOP = "shop"
    VICTORY = "victory"
    GAME_OVER = "game_over"

    def __init__(self):
        # 获取显示表面
        self.display_surface = pygame.display.get_surface()
        self.ui = UI(self.display_surface)
        self.resources = ResourceManager()
        self.save_data = load_save()
        self.state = self.MENU
        self.shop_message = ""
        self.result_saved = False
        self.setup_run()

    def setup_run(self):
        # 创建精灵组
        self.all_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.attack_sprites = pygame.sprite.Group()
        self.enemy_projectile_sprites = pygame.sprite.Group()
        self.drop_sprites = pygame.sprite.Group()
        self.particle_sprites = pygame.sprite.Group()
        self.floating_text_sprites = pygame.sprite.Group()

        permanent_upgrades = self.save_data["permanent_upgrades"]
        self.player = Player(
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),
            self.resources,
            permanent_upgrades,
            self.all_sprites,
        )
        self.weapon_controller = WeaponController(self.player, self.resources)

        self.score = 0
        self.elapsed_time = 0
        self.enemy_timer = 0
        self.elite_timer = 0
        self.boss_spawned = False
        self.boss = None
        self.pending_level_ups = 0
        self.level_up_options = []
        self.shake = ScreenShake()
        self.hit_stop_timer = 0
        self.flash_timer = 0
        self.result_saved = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_mouse_click(event.pos)
            return

        if event.type != pygame.KEYDOWN:
            return

        if self.state == self.MENU:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.start_game()
            elif event.key == pygame.K_s:
                self.shop_message = ""
                self.state = self.SHOP

        elif self.state == self.SHOP:
            if event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.state = self.MENU
            elif pygame.K_1 <= event.key <= pygame.K_4:
                self.buy_shop_upgrade(event.key - pygame.K_1)

        elif self.state == self.LEVEL_UP:
            if pygame.K_1 <= event.key <= pygame.K_3:
                self.choose_level_upgrade(event.key - pygame.K_1)

        elif self.state in (self.GAME_OVER, self.VICTORY):
            if event.key == pygame.K_r:
                self.start_game()
            elif event.key == pygame.K_m:
                self.state = self.MENU

    def handle_mouse_click(self, pos):
        if self.state == self.MENU:
            action = self.ui.hit_menu(pos)
            if action == "start":
                self.resources.play("select")
                self.start_game()
            elif action == "shop":
                self.resources.play("select")
                self.shop_message = ""
                self.state = self.SHOP

        elif self.state == self.SHOP:
            button = self.ui.hit_shop(pos)
            if not button:
                return

            self.resources.play("select")
            if button["action"] == "back":
                self.state = self.MENU
            elif button["action"] == "upgrade":
                self.buy_shop_upgrade(button["index"])

        elif self.state == self.LEVEL_UP:
            index = self.ui.hit_level_up(pos)
            if index is not None:
                self.choose_level_upgrade(index)

        elif self.state in (self.GAME_OVER, self.VICTORY):
            action = self.ui.hit_result(pos)
            if action == "restart":
                self.resources.play("select")
                self.start_game()
            elif action == "menu":
                self.resources.play("select")
                self.state = self.MENU

    def start_game(self):
        self.setup_run()
        self.state = self.PLAYING

    def buy_shop_upgrade(self, index):
        upgrade_ids = list(PERMANENT_UPGRADES)
        if index < 0 or index >= len(upgrade_ids):
            return False

        self.save_data, success, self.shop_message = purchase_upgrade(self.save_data, upgrade_ids[index])
        if success:
            self.resources.play("upgrade")
            self.save_data = save_game(self.save_data)
        return success

    def choose_level_upgrade(self, index):
        if index < 0 or index >= len(self.level_up_options):
            return

        apply_upgrade(self.player, self.level_up_options[index].id)
        self.resources.play("select")
        self.resources.play("upgrade", cooldown=0.04)
        self.add_floating_text(self.player.rect.midtop, "升级", CYAN)
        self.add_particles(self.player.rect.center, CYAN, 18, 190, 5)
        if self.pending_level_ups > 0:
            self.open_level_up()
        else:
            self.level_up_options = []
            self.state = self.PLAYING

    def open_level_up(self):
        self.pending_level_ups -= 1
        self.level_up_options = choose_upgrade_options(self.player)
        if not self.level_up_options:
            self.state = self.PLAYING
            return
        self.state = self.LEVEL_UP

    def random_edge_position(self, margin=60):
        side = random.choice(("top", "right", "bottom", "left"))
        if side == "top":
            return random.randint(0, SCREEN_WIDTH), -margin
        if side == "right":
            return SCREEN_WIDTH + margin, random.randint(0, SCREEN_HEIGHT)
        if side == "bottom":
            return random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + margin
        return -margin, random.randint(0, SCREEN_HEIGHT)

    def choose_enemy_kind(self):
        elapsed = self.elapsed_time
        choices = [("grunt", 60)]
        if elapsed >= 35:
            choices.append(("fast", 25))
        if elapsed >= 80:
            choices.append(("tank", 18))
        if elapsed >= 120:
            choices.append(("ranger", 18))
        if elapsed >= ELITE_START_TIME:
            choices.append(("elite", 6))

        total = sum(weight for _, weight in choices)
        roll = random.uniform(0, total)
        current = 0
        for kind, weight in choices:
            current += weight
            if roll <= current:
                return kind
        return "grunt"

    def spawn_enemy(self, kind=None):
        kind = kind or self.choose_enemy_kind()
        size = ENEMY_TYPES[kind]["size"]
        pos = self.random_edge_position(size)
        difficulty = 1.0 + min(1.15, self.elapsed_time / 300)
        enemy = Enemy(
            pos,
            self.player,
            kind,
            self.resources,
            (self.all_sprites, self.enemy_projectile_sprites),
            difficulty,
            self.all_sprites,
            self.enemy_sprites,
        )
        if kind == "boss":
            self.boss = enemy
        return enemy

    def spawn_boss(self):
        if self.boss_spawned:
            return
        self.boss_spawned = True
        boss = self.spawn_enemy("boss")
        self.shake.add(16)
        self.flash_timer = max(self.flash_timer, 0.18)
        self.resources.play("boss")
        self.add_floating_text((SCREEN_WIDTH // 2, 150), "金币领主出现", YELLOW)
        self.add_particles(boss.rect.center, YELLOW, 42, 240, 6)

    def update_spawns(self, dt):
        if self.elapsed_time >= BOSS_SPAWN_TIME:
            self.spawn_boss()

        self.enemy_timer += dt
        enemy_interval = max(0.34, ENEMY_SPAWN_TIME - self.elapsed_time * 0.0022)
        if self.enemy_timer >= enemy_interval:
            self.enemy_timer = 0
            spawn_count = 1
            if self.elapsed_time >= 150:
                spawn_count += 1
            if self.elapsed_time >= 285:
                spawn_count += 1
            for _ in range(spawn_count):
                self.spawn_enemy()

        if self.elapsed_time >= ELITE_START_TIME:
            self.elite_timer += dt
            if self.elite_timer >= 32:
                self.elite_timer = 0
                self.spawn_enemy("elite")

    def spawn_drops(self, enemy):
        if enemy.exp_value > 0:
            Drop(
                enemy.rect.center,
                "exp",
                enemy.exp_value,
                self.player,
                self.resources,
                self.all_sprites,
                self.drop_sprites,
                effect_groups=(self.all_sprites, self.particle_sprites),
            )

        gold_chance = 0.38
        if enemy.is_elite:
            gold_chance = 0.85
        if enemy.is_boss:
            gold_chance = 1.0
        if random.random() <= gold_chance:
            amount = GOLD_DROP_VALUE
            if enemy.is_elite:
                amount = 12
            elif enemy.is_boss:
                amount = 80
            Drop(
                enemy.rect.center,
                "gold",
                amount,
                self.player,
                self.resources,
                self.all_sprites,
                self.drop_sprites,
                effect_groups=(self.all_sprites, self.particle_sprites),
            )

        if not enemy.is_boss and random.random() <= 0.045:
            Drop(
                enemy.rect.center,
                "heart",
                HEART_HEAL_VALUE,
                self.player,
                self.resources,
                self.all_sprites,
                self.drop_sprites,
                effect_groups=(self.all_sprites, self.particle_sprites),
            )

        if not enemy.is_boss and random.random() <= 0.035:
            Drop(
                enemy.rect.center,
                "magnet",
                1,
                self.player,
                self.resources,
                self.all_sprites,
                self.drop_sprites,
                effect_groups=(self.all_sprites, self.particle_sprites),
            )

    def kill_enemy(self, enemy):
        if not enemy.alive():
            return

        self.score += enemy.score_value
        color = enemy.definition["color"]
        self.add_particles(enemy.rect.center, color, 12 if not enemy.is_boss else 60, 180 if not enemy.is_boss else 300, 5)
        if enemy.is_elite:
            self.shake.add(6)
        if enemy.is_boss:
            self.shake.add(18)
        self.resources.play("kill", cooldown=0.04)
        self.spawn_drops(enemy)
        is_boss = enemy.is_boss
        enemy.kill()

        if is_boss:
            self.score += 500
            self.finish_run(True)

    def handle_attack_collisions(self):
        collisions = pygame.sprite.groupcollide(self.attack_sprites, self.enemy_sprites, False, False)
        for attack, enemies in collisions.items():
            for enemy in enemies:
                if not attack.alive():
                    break
                if hasattr(attack, "can_hit") and not attack.can_hit(enemy):
                    continue

                killed = enemy.take_damage(attack.damage)
                self.add_hit_feedback(enemy, attack.damage, killed)
                if killed:
                    self.kill_enemy(enemy)
                if hasattr(attack, "register_hit"):
                    attack.register_hit(enemy)

    def add_hit_feedback(self, enemy, damage, killed=False):
        color = enemy.definition["color"]
        self.add_particles(enemy.rect.center, color, 5 if not killed else 12, 120, 4)
        self.add_floating_text(enemy.rect.midtop, str(int(damage)), YELLOW if killed else WHITE)
        self.hit_stop_timer = max(self.hit_stop_timer, HIT_STOP_TIME)
        self.shake.add(2.5 if not enemy.is_boss else 5)
        self.resources.play("hit", cooldown=0.035)

    def add_particles(self, pos, color, count=10, speed=160, size=4):
        burst_particles(pos, color, self.all_sprites, self.particle_sprites, count, speed, size)

    def add_floating_text(self, pos, text, color):
        FloatingText(pos, text, self.ui.tiny_font, color, self.all_sprites, self.floating_text_sprites)
        trim_group(self.floating_text_sprites, MAX_FLOATING_TEXTS)

    def collect_drop(self, drop):
        if drop.kind == "exp":
            level_ups = self.player.add_exp(drop.amount)
            self.pending_level_ups += level_ups
            self.add_floating_text(drop.rect.center, f"+{drop.amount}经验", CYAN)
        elif drop.kind == "gold":
            gained = self.player.add_gold(drop.amount)
            self.score += gained
            self.add_floating_text(drop.rect.center, f"+{gained}", YELLOW)
        elif drop.kind == "heart":
            self.player.heal(drop.amount)
            self.add_floating_text(drop.rect.center, "+生命", GREEN)
        elif drop.kind == "magnet":
            self.player.activate_magnet()
            self.add_floating_text(drop.rect.center, "吸附", PURPLE)

        self.add_particles(drop.rect.center, DROP_EFFECT_COLORS.get(drop.kind, CYAN), 6, 120, 3)
        self.resources.play("pickup", cooldown=0.025)

    def handle_player_collisions(self):
        enemy_hits = pygame.sprite.spritecollide(self.player, self.enemy_sprites, False)
        if enemy_hits:
            damage = max(enemy.damage for enemy in enemy_hits)
            if self.player.take_damage(damage):
                self.on_player_hurt(damage)

        projectile_hits = pygame.sprite.spritecollide(self.player, self.enemy_projectile_sprites, True)
        for projectile in projectile_hits:
            if self.player.take_damage(projectile.damage):
                self.on_player_hurt(projectile.damage)

        drops = pygame.sprite.spritecollide(self.player, self.drop_sprites, True)
        for drop in drops:
            self.collect_drop(drop)

        if self.player.health <= 0:
            self.finish_run(False)
            return

        if self.pending_level_ups > 0 and self.state == self.PLAYING:
            self.open_level_up()

    def on_player_hurt(self, damage):
        self.shake.add(11)
        self.flash_timer = max(self.flash_timer, 0.22)
        self.add_particles(self.player.rect.center, RED, 20, 220, 5)
        self.add_floating_text(self.player.rect.midtop, f"-{damage}", RED)
        self.resources.play("hurt")

    def finish_run(self, victory):
        if self.result_saved:
            return

        if victory:
            self.player.add_gold(VICTORY_BONUS_GOLD)

        self.save_data = record_run(self.save_data, self.score, self.elapsed_time, self.player.run_gold)
        self.save_data = save_game(self.save_data)
        self.result_saved = True
        self.resources.play("victory" if victory else "defeat")
        self.state = self.VICTORY if victory else self.GAME_OVER

    def draw_world(self):
        self.ui.update_cursor(False)
        self.ui.draw_background()
        offset = (round(self.shake.offset.x), round(self.shake.offset.y))
        for sprite in self.all_sprites:
            self.display_surface.blit(sprite.image, sprite.rect.move(offset))
        self.ui.draw_hud(
            self.player,
            self.score,
            self.elapsed_time,
            RUN_DURATION,
            len(self.enemy_sprites),
            self.boss,
        )
        self.draw_flash()

    def draw_flash(self):
        if self.flash_timer <= 0:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(FLASH_ALPHA * min(1, self.flash_timer / 0.22))
        overlay.fill((255, 48, 48, alpha))
        self.display_surface.blit(overlay, (0, 0))

    def run_playing(self, dt):
        self.shake.update(dt)
        self.flash_timer = max(0, self.flash_timer - dt)
        if self.hit_stop_timer > 0:
            self.hit_stop_timer = max(0, self.hit_stop_timer - dt)
            self.draw_world()
            return

        self.elapsed_time += dt
        self.update_spawns(dt)
        self.weapon_controller.update(dt, self)
        self.all_sprites.update(dt)
        self.handle_attack_collisions()
        self.handle_player_collisions()
        self.draw_world()

    def run_level_up(self):
        self.draw_world()
        self.ui.draw_level_up(self.level_up_options)

    def run_result(self, title):
        self.draw_world()
        self.ui.draw_result(title, self.player, self.score, self.elapsed_time, self.save_data)

    def run(self, dt):
        if self.state == self.MENU:
            self.ui.draw_menu(self.save_data)
        elif self.state == self.SHOP:
            self.ui.draw_shop(self.save_data, self.shop_message)
        elif self.state == self.PLAYING:
            self.run_playing(dt)
        elif self.state == self.LEVEL_UP:
            self.run_level_up()
        elif self.state == self.VICTORY:
            self.run_result("胜利")
        elif self.state == self.GAME_OVER:
            self.run_result("游戏结束")
