import copy
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game.config.settings import (
    CYAN,
    EFFECT_QUALITY_PRESETS,
    ENEMY_FRAME_COUNT,
    PLAYER_BASE_EXP,
    PLAYER_FRAME_COUNT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WEAPON_FRAME_COUNT,
)
from game.entities.enemy import Enemy
from game.systems.effects import (
    FlashSprite,
    Particle,
    ScreenShake,
    Shockwave,
    SlashArc,
    impact_effect,
    particle_budget,
    set_runtime_settings,
    status_aura,
)
from game.systems.resources import ResourceManager
from game.systems.save_data import (
    DEFAULT_SAVE_DATA,
    PERMANENT_UPGRADES,
    get_permanent_upgrade_cost,
    load_save,
    purchase_upgrade,
    save_game,
)
from game.systems.settings_data import (
    DEFAULT_SETTINGS_DATA,
    load_settings,
    normalize_settings_data,
    save_settings,
)
from game.systems.upgrades import (
    EVOLUTION_REQUIREMENTS,
    RUN_UPGRADES,
    WEAPON_UPGRADES,
    UpgradeOption,
    build_upgrade_pool,
    choose_upgrade_options,
)
from game.ui.ui import UI


class FakePlayer:
    def __init__(self):
        self.run_upgrade_levels = {upgrade_id: 0 for upgrade_id in RUN_UPGRADES}
        self.weapons = {weapon_id: 0 for weapon_id in WEAPON_UPGRADES}
        self.weapons["missile"] = 1
        self.weapon_evolutions = set()
        self.run_gold = 0


class SaveDataTests(unittest.TestCase):
    def test_save_round_trip_normalizes_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "save_data.json")
            data = copy.deepcopy(DEFAULT_SAVE_DATA)
            data["total_gold"] = 300
            data["high_score"] = 1200
            data["longest_time"] = 188
            data["permanent_upgrades"]["max_health"] = 2

            saved = save_game(data, path)
            loaded = load_save(path)

        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["total_gold"], 300)
        self.assertEqual(loaded["permanent_upgrades"]["max_health"], 2)

    def test_purchase_upgrade_uses_price_and_caps_level(self):
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        first_cost = get_permanent_upgrade_cost("max_health", 0)
        data["total_gold"] = first_cost

        data, success, message = purchase_upgrade(data, "max_health")

        self.assertTrue(success, message)
        self.assertEqual(data["total_gold"], 0)
        self.assertEqual(data["permanent_upgrades"]["max_health"], 1)
        max_level = PERMANENT_UPGRADES["max_health"]["max_level"]
        self.assertIsNone(get_permanent_upgrade_cost("max_health", max_level))


class SettingsDataTests(unittest.TestCase):
    def test_missing_and_broken_settings_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = os.path.join(temp_dir, "settings_data.json")
            broken_path = os.path.join(temp_dir, "broken_settings.json")
            with open(broken_path, "w", encoding="utf-8") as file:
                file.write("{broken")

            self.assertEqual(load_settings(missing_path), DEFAULT_SETTINGS_DATA)
            self.assertEqual(load_settings(broken_path), DEFAULT_SETTINGS_DATA)

    def test_settings_normalize_invalid_values(self):
        normalized = normalize_settings_data(
            {
                "master_volume": 180,
                "muted": "yes",
                "effect_quality": "ultra",
                "screen_shake": False,
                "damage_numbers": False,
                "background_detail": "medium",
                "fullscreen": True,
            }
        )

        self.assertEqual(normalized["master_volume"], 100)
        self.assertFalse(normalized["muted"])
        self.assertEqual(normalized["effect_quality"], "high")
        self.assertFalse(normalized["screen_shake"])
        self.assertFalse(normalized["damage_numbers"])
        self.assertEqual(normalized["background_detail"], "medium")
        self.assertTrue(normalized["fullscreen"])

    def test_settings_round_trip_does_not_touch_save_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = os.path.join(temp_dir, "settings_data.json")
            save_path = os.path.join(temp_dir, "save_data.json")
            save_game(copy.deepcopy(DEFAULT_SAVE_DATA), save_path)
            before = load_save(save_path)

            data = copy.deepcopy(DEFAULT_SETTINGS_DATA)
            data["master_volume"] = 35
            data["muted"] = True
            saved = save_settings(data, settings_path)
            loaded = load_settings(settings_path)
            after = load_save(save_path)

        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["master_volume"], 35)
        self.assertTrue(loaded["muted"])
        self.assertEqual(before, after)


class UpgradeTests(unittest.TestCase):
    def test_upgrade_choices_do_not_repeat(self):
        player = FakePlayer()
        options = choose_upgrade_options(player, count=3, rng=random.Random(7))
        ids = [option.id for option in options]

        self.assertEqual(len(options), 3)
        self.assertEqual(len(ids), len(set(ids)))

    def test_new_weapons_are_in_upgrade_pool(self):
        player = FakePlayer()
        pool_ids = {option.id for option in build_upgrade_pool(player)}

        self.assertIn("weapon:flame", pool_ids)
        self.assertIn("weapon:frost", pool_ids)
        self.assertIn("weapon:drone", pool_ids)

    def test_evolution_requires_max_weapon_and_stat_level(self):
        player = FakePlayer()
        player.weapons["flame"] = WEAPON_UPGRADES["flame"]["max_level"]
        self.assertNotIn("evolve:flame", {option.id for option in build_upgrade_pool(player)})

        requirement = EVOLUTION_REQUIREMENTS["flame"]
        player.run_upgrade_levels[requirement["stat"]] = requirement["level"]
        self.assertIn("evolve:flame", {option.id for option in build_upgrade_pool(player)})

        player.weapon_evolutions.add("flame")
        self.assertNotIn("evolve:flame", {option.id for option in build_upgrade_pool(player)})


class ResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_missing_image_and_sound_fall_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            surface = manager.load_image(
                "missing",
                (17, 19),
                lambda size: pygame.Surface(size, pygame.SRCALPHA),
            )
            sound = manager.load_sound("missing")

        self.assertEqual(surface.get_size(), (17, 19))
        self.assertIsNone(sound.play())

    def test_missing_frames_fall_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            frames = manager.load_frames(
                "missing",
                (12, 13),
                lambda size, index=0: pygame.Surface(size, pygame.SRCALPHA),
                frame_count=3,
            )

        self.assertEqual(len(frames), 3)
        self.assertTrue(all(frame.get_size() == (12, 13) for frame in frames))

    def test_high_frame_count_fallbacks_are_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            player_frames = manager.load_frames(
                "missing_player",
                (48, 48),
                lambda size, index=0: pygame.Surface(size, pygame.SRCALPHA),
                frame_count=PLAYER_FRAME_COUNT,
            )
            enemy_frames = manager.load_frames(
                "missing_enemy",
                (40, 40),
                lambda size, index=0: pygame.Surface(size, pygame.SRCALPHA),
                frame_count=ENEMY_FRAME_COUNT,
            )
            weapon_frames = manager.load_frames(
                "missing_weapon",
                (20, 20),
                lambda size, index=0: pygame.Surface(size, pygame.SRCALPHA),
                frame_count=WEAPON_FRAME_COUNT,
            )

        self.assertEqual(len(player_frames), PLAYER_FRAME_COUNT)
        self.assertEqual(len(enemy_frames), ENEMY_FRAME_COUNT)
        self.assertEqual(len(weapon_frames), WEAPON_FRAME_COUNT)

    def test_missing_effect_image_falls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            image = manager.load_image(
                "slash_arc",
                (48, 48),
                lambda size: pygame.Surface(size, pygame.SRCALPHA),
            )

        self.assertEqual(image.get_size(), (48, 48))

    def test_missing_sound_play_respects_cooldown_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            self.assertIsNone(manager.play("missing", cooldown=1))
            self.assertIsNone(manager.play("missing", cooldown=1))
            self.assertIn("missing", manager.last_sound_times)

    def test_sound_volume_and_muted_control_play_path(self):
        class FakeSound:
            def __init__(self):
                self.play_count = 0
                self.volume = None

            def set_volume(self, volume):
                self.volume = volume

            def play(self):
                self.play_count += 1
                return "channel"

        fake = FakeSound()
        manager = ResourceManager(image_dir="", sound_dir="", settings_data={"master_volume": 35, "muted": False})
        manager.load_sound = lambda name: fake

        self.assertEqual(manager.play("select"), "channel")
        self.assertAlmostEqual(fake.volume, 0.35)
        self.assertEqual(fake.play_count, 1)

        manager.set_settings({"master_volume": 35, "muted": True})
        self.assertIsNone(manager.play("select"))
        self.assertEqual(fake.play_count, 1)

        manager.set_settings({"master_volume": 0, "muted": False})
        self.assertIsNone(manager.play("select"))
        self.assertEqual(fake.play_count, 1)


class EffectTests(unittest.TestCase):
    def test_effect_quality_presets_scale_particle_budget(self):
        self.assertLess(
            EFFECT_QUALITY_PRESETS["low"]["max_particles"],
            EFFECT_QUALITY_PRESETS["medium"]["max_particles"],
        )
        self.assertLess(
            EFFECT_QUALITY_PRESETS["medium"]["max_particles"],
            EFFECT_QUALITY_PRESETS["high"]["max_particles"],
        )
        self.assertIn(particle_budget(), {preset["max_particles"] for preset in EFFECT_QUALITY_PRESETS.values()})

    def test_runtime_effect_quality_changes_particle_budget(self):
        try:
            set_runtime_settings({"effect_quality": "low"})
            low = particle_budget()
            set_runtime_settings({"effect_quality": "medium"})
            medium = particle_budget()
            set_runtime_settings({"effect_quality": "high"})
            high = particle_budget()
        finally:
            set_runtime_settings(DEFAULT_SETTINGS_DATA)

        self.assertLess(low, medium)
        self.assertLess(medium, high)

    def test_particle_expires(self):
        group = pygame.sprite.Group()
        Particle((10, 10), (0, 0), (255, 255, 255), 0.05, 3, group)

        group.update(0.1)

        self.assertEqual(len(group), 0)

    def test_screen_shake_decays(self):
        shake = ScreenShake()
        shake.add(10)
        shake.update(0.1)

        self.assertLess(shake.amount, 10)
        self.assertGreater(shake.amount, 0)

        shake.update(1.0)
        self.assertEqual(shake.amount, 0)

    def test_flash_slash_and_shockwave_expire(self):
        group = pygame.sprite.Group()
        FlashSprite((20, 20), 8, (255, 255, 255), group)
        SlashArc((20, 20), 14, 0, (91, 217, 235), group)
        Shockwave((20, 20), 20, (91, 217, 235), 0.15, 2, group)

        group.update(1.0)

        self.assertEqual(len(group), 0)

    def test_impact_feedback_accepts_all_effect_kinds(self):
        all_group = pygame.sprite.Group()
        particle_group = pygame.sprite.Group()

        for kind in ("default", "missile", "blade", "pulse", "flame", "frost", "drone", "gold"):
            impact_effect((30, 30), kind, all_group, particle_group)

        self.assertGreater(len(all_group), 0)
        self.assertGreater(len(particle_group), 0)

    def test_status_aura_creates_temporary_sprite(self):
        all_group = pygame.sprite.Group()
        particle_group = pygame.sprite.Group()

        status_aura((30, 30), "burn", all_group, particle_group)
        status_aura((30, 30), "slow", all_group, particle_group)

        self.assertEqual(len(all_group), 2)
        all_group.update(1.0)
        self.assertEqual(len(all_group), 0)


class EnemyStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1280, 720))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_burn_ticks_damage_and_slow_reduces_movement(self):
        resources = ResourceManager(image_dir="", sound_dir="")
        player = FakePlayer()
        player.pos = pygame.math.Vector2(100, 100)
        enemy = Enemy((200, 100), player, "grunt", resources, difficulty=1.0)

        enemy.apply_burn(5, 1.2)
        events = enemy.update_statuses(0.6)
        self.assertTrue(events)
        self.assertLess(enemy.health, enemy.max_health)

        normal_pos = pygame.math.Vector2(enemy.pos)
        enemy.update(0.2)
        normal_distance = normal_pos.distance_to(enemy.pos)

        slowed = Enemy((200, 100), player, "grunt", resources, difficulty=1.0)
        slowed.apply_slow(0.5, 1.0)
        slow_pos = pygame.math.Vector2(slowed.pos)
        slowed.update(0.2)
        slow_distance = slow_pos.distance_to(slowed.pos)

        self.assertLess(slow_distance, normal_distance)


class PlayerProgressionConstantTests(unittest.TestCase):
    def test_base_exp_is_positive(self):
        self.assertGreater(PLAYER_BASE_EXP, 0)


class UIInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_ui_hit_regions_are_recorded_after_draw(self):
        ui = UI(self.surface)
        save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        options = [
            UpgradeOption("damage", "伤害提升", "所有武器伤害 +15%"),
            UpgradeOption("weapon:blade", "旋转刀刃", "解锁新武器"),
            UpgradeOption("pickup_range", "收集范围", "拾取范围 +20"),
        ]

        ui.draw_menu(save_data)
        self.assertEqual(ui.hit_menu(ui.menu_buttons["start"].center), "start")
        self.assertEqual(ui.hit_menu(ui.menu_buttons["shop"].center), "shop")
        self.assertEqual(ui.hit_menu(ui.menu_buttons["settings"].center), "settings")

        ui.draw_shop(save_data)
        first_shop_button = ui.shop_buttons[0]
        back_button = ui.shop_buttons[-1]
        self.assertEqual(ui.hit_shop(first_shop_button["rect"].center)["index"], 0)
        self.assertEqual(ui.hit_shop(back_button["rect"].center)["action"], "back")

        ui.draw_level_up(options)
        self.assertEqual(ui.hit_level_up(ui.level_up_cards[0][1].center), 0)
        self.assertEqual(ui.hit_level_up(ui.level_up_cards[1][1].center), 1)

        ui.draw_result("游戏结束", FakePlayer(), 100, 32, save_data)
        self.assertEqual(ui.hit_result(ui.result_buttons["restart"].center), "restart")
        self.assertEqual(ui.hit_result(ui.result_buttons["menu"].center), "menu")

    def test_level_up_long_text_stays_inside_cards(self):
        ui = UI(self.surface)
        options = [
            UpgradeOption("weapon:flame", "火焰法球超级强化形态", "解锁新武器并在命中敌群时留下更大范围的燃烧区域，持续造成伤害"),
            UpgradeOption("max_health", "生命上限", "最大生命 +1 并回复 1 点（等级 1），这个描述故意很长用于测试换行"),
            UpgradeOption("weapon:frost", "冰霜碎片", "解锁新武器，向最近敌人方向扇形发射并造成减速效果"),
        ]

        ui.draw_background()
        ui.draw_level_up(options)

        cards = [rect for _, rect in ui.level_up_cards]
        self.assertTrue(ui.last_text_rects["level_up"])
        for text_rect in ui.last_text_rects["level_up"]:
            self.assertTrue(any(card.contains(text_rect) for card in cards), text_rect)

    def test_settings_hit_regions_are_recorded_after_draw(self):
        ui = UI(self.surface)

        ui.draw_settings(copy.deepcopy(DEFAULT_SETTINGS_DATA))

        settings_actions = {button["action"] for button in ui.settings_buttons}
        self.assertIn("volume_down", settings_actions)
        self.assertIn("volume_up", settings_actions)
        self.assertIn("muted", settings_actions)
        self.assertIn("effect_quality:low", settings_actions)
        self.assertIn("effect_quality:medium", settings_actions)
        self.assertIn("effect_quality:high", settings_actions)
        self.assertIn("screen_shake", settings_actions)
        self.assertIn("damage_numbers", settings_actions)
        self.assertIn("background_detail:high", settings_actions)
        self.assertIn("fullscreen", settings_actions)
        self.assertIn("back", settings_actions)

        back_button = next(button for button in ui.settings_buttons if button["action"] == "back")
        self.assertEqual(ui.hit_settings(back_button["rect"].center), "back")

    def test_settings_buttons_do_not_overlap(self):
        ui = UI(self.surface)

        ui.draw_settings(copy.deepcopy(DEFAULT_SETTINGS_DATA))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 360, 36, 720, 648)
        buttons = ui.settings_buttons
        for button in buttons:
            self.assertTrue(panel.contains(button["rect"]), button)

        for index, first in enumerate(buttons):
            for second in buttons[index + 1 :]:
                self.assertFalse(first["rect"].colliderect(second["rect"]), (first, second))

        button_by_action = {button["action"]: button for button in buttons}
        self.assertEqual(ui.hit_settings(button_by_action["volume_down"]["rect"].center), "volume_down")
        self.assertEqual(ui.hit_settings(button_by_action["fullscreen"]["rect"].center), "fullscreen")
        self.assertEqual(ui.hit_settings(button_by_action["back"]["rect"].center), "back")
        self.assertGreaterEqual(
            button_by_action["back"]["rect"].top - button_by_action["fullscreen"]["rect"].bottom,
            70,
        )

    def test_shop_and_button_long_text_stays_inside_bounds(self):
        import game.ui.ui as ui_module

        ui = UI(self.surface)
        original_upgrades = ui_module.PERMANENT_UPGRADES
        patched_upgrades = copy.deepcopy(original_upgrades)
        first_key = next(iter(patched_upgrades))
        patched_upgrades[first_key]["description"] = "永久提升初始生命并提供更稳定的前期容错，这是一段很长的商店描述用于测试换行和边界限制"
        ui_module.PERMANENT_UPGRADES = patched_upgrades
        try:
            ui.draw_shop(copy.deepcopy(DEFAULT_SAVE_DATA))
        finally:
            ui_module.PERMANENT_UPGRADES = original_upgrades

        shop_rows = [button["rect"] for button in ui.shop_buttons if button["action"] == "upgrade"]
        self.assertTrue(ui.last_text_rects["shop"])
        for text_rect in ui.last_text_rects["shop"]:
            self.assertTrue(any(row.contains(text_rect) for row in shop_rows), text_rect)

        button_rect = pygame.Rect(100, 100, 300, 42)
        ui.last_text_rects = {}
        ui.draw_button_row("Enter / Space", "这是一个非常长的按钮标签", button_rect, CYAN)
        for text_rect in ui.last_text_rects["button"]:
            self.assertTrue(button_rect.contains(text_rect), text_rect)

    def test_background_detail_counts_scale_by_quality(self):
        ui = UI(self.surface)
        low = ui.background_item_count("low")
        medium = ui.background_item_count("medium")
        high = ui.background_item_count("high")

        self.assertLessEqual(low["gold"], medium["gold"])
        self.assertLess(medium["gold"], high["gold"])
        self.assertLessEqual(low["stones"], medium["stones"])
        self.assertLess(medium["stones"], high["stones"])

        ui.draw_background("low")
        ui.draw_background("medium")
        ui.draw_background("high")

    def test_background_decor_is_stable_and_inside_screen(self):
        first = UI(self.surface)
        second = UI(self.surface)

        self.assertEqual(first.background_decor, second.background_decor)
        screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.assertTrue(first.background_decor["stones"])
        for rect, _ in first.background_decor["stones"]:
            self.assertTrue(screen_rect.contains(rect), rect)
        for group_name in ("cracks", "veins"):
            for points in first.background_decor[group_name]:
                for x, y in points:
                    self.assertGreaterEqual(x, 0)
                    self.assertLessEqual(x, SCREEN_WIDTH)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(y, SCREEN_HEIGHT)
        for x, y, _ in first.background_decor["gold"]:
            self.assertTrue(screen_rect.collidepoint(x, y))

        first.draw_background()
        self.assertNotEqual(self.surface.get_at((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))[:3], (16, 20, 28))


class MouseEventSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1280, 720))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        import game.core.level as level_module

        self.level_module = level_module
        self.original_save_game = level_module.save_game
        self.original_save_settings = level_module.save_settings
        level_module.save_game = lambda data: data
        level_module.save_settings = lambda data: normalize_settings_data(data)

    def tearDown(self):
        self.level_module.save_game = self.original_save_game
        self.level_module.save_settings = self.original_save_settings

    def click(self, level, pos):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
        level.handle_event(event)

    def test_mouse_clicks_drive_menu_shop_upgrade_and_result_states(self):
        level = self.level_module.Level()
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)

        level.run(1 / 60)
        self.click(level, level.ui.menu_buttons["shop"].center)
        self.assertEqual(level.state, level.SHOP)

        level.run(1 / 60)
        self.click(level, level.ui.shop_buttons[0]["rect"].center)
        self.assertEqual(level.shop_message, "金币不足")

        self.click(level, level.ui.shop_buttons[-1]["rect"].center)
        self.assertEqual(level.state, level.MENU)

        level.run(1 / 60)
        self.click(level, level.ui.menu_buttons["start"].center)
        self.assertEqual(level.state, level.PLAYING)

        level.pending_level_ups = 1
        level.open_level_up()
        level.run(1 / 60)
        self.click(level, level.ui.level_up_cards[0][1].center)
        self.assertEqual(level.state, level.PLAYING)

        level.finish_run(False)
        level.run(1 / 60)
        self.click(level, level.ui.result_buttons["restart"].center)
        self.assertEqual(level.state, level.PLAYING)

        level.finish_run(False)
        level.run(1 / 60)
        self.click(level, level.ui.result_buttons["menu"].center)
        self.assertEqual(level.state, level.MENU)

    def test_settings_menu_and_pause_paths(self):
        display_changes = []
        level = self.level_module.Level(
            copy.deepcopy(DEFAULT_SETTINGS_DATA),
            lambda data: display_changes.append(copy.deepcopy(data)),
        )
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)

        level.run(1 / 60)
        self.click(level, level.ui.menu_buttons["settings"].center)
        self.assertEqual(level.state, level.SETTINGS)
        self.assertEqual(level.settings_return_state, level.MENU)

        level.run(1 / 60)
        volume_down = next(button for button in level.ui.settings_buttons if button["action"] == "volume_down")
        self.click(level, volume_down["rect"].center)
        self.assertEqual(level.settings_data["master_volume"], 90)

        effect_low = next(button for button in level.ui.settings_buttons if button["action"] == "effect_quality:low")
        self.click(level, effect_low["rect"].center)
        self.assertEqual(level.settings_data["effect_quality"], "low")

        fullscreen = next(button for button in level.ui.settings_buttons if button["action"] == "fullscreen")
        self.click(level, fullscreen["rect"].center)
        self.assertTrue(level.settings_data["fullscreen"])
        self.assertEqual(len(display_changes), 1)

        level.run(1 / 60)
        back = next(button for button in level.ui.settings_buttons if button["action"] == "back")
        self.click(level, back["rect"].center)
        self.assertEqual(level.state, level.MENU)

        level.start_game()
        level.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
        self.assertEqual(level.state, level.SETTINGS)
        self.assertEqual(level.settings_return_state, level.PLAYING)
        level.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
        self.assertEqual(level.state, level.PLAYING)

    def test_feedback_toggles_disable_shake_and_damage_numbers(self):
        level = self.level_module.Level(copy.deepcopy(DEFAULT_SETTINGS_DATA))
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        level.start_game()
        enemy = level.spawn_enemy("grunt")

        level.settings_data["screen_shake"] = False
        level.settings_data["damage_numbers"] = False
        level.add_hit_feedback(enemy, 3, False, "missile")

        self.assertEqual(level.shake.amount, 0)
        self.assertEqual(len(level.floating_text_sprites), 0)

    def test_new_weapons_unlock_and_update_without_crashing(self):
        level = self.level_module.Level()
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        level.start_game()
        for weapon_id in ("missile", "blade", "pulse", "flame", "frost", "drone"):
            level.player.weapons[weapon_id] = WEAPON_UPGRADES[weapon_id]["max_level"]
        level.player.weapon_evolutions.update(("missile", "blade", "pulse", "flame", "frost", "drone"))
        level.spawn_enemy("grunt")

        for _ in range(150):
            level.run_playing(1 / 60)

        self.assertTrue(level.state in (level.PLAYING, level.LEVEL_UP, level.GAME_OVER, level.VICTORY))

    def test_visual_effect_paths_run_with_statuses_and_boss(self):
        level = self.level_module.Level()
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        level.start_game()
        for weapon_id in ("missile", "blade", "pulse", "flame", "frost", "drone"):
            level.player.weapons[weapon_id] = WEAPON_UPGRADES[weapon_id]["max_level"]
        level.player.weapon_evolutions.update(("missile", "blade", "pulse", "flame", "frost", "drone"))

        burning = level.spawn_enemy("grunt")
        slowed = level.spawn_enemy("fast")
        burning.apply_burn(3, 1.0)
        slowed.apply_slow(0.5, 1.0)
        level.spawn_enemy("elite")
        level.spawn_boss()

        for _ in range(180):
            level.run_playing(1 / 60)

        self.assertTrue(level.state in (level.PLAYING, level.LEVEL_UP, level.GAME_OVER, level.VICTORY))


if __name__ == "__main__":
    unittest.main()
