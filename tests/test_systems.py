import copy
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game.config.settings import PLAYER_BASE_EXP
from game.systems.effects import Particle, ScreenShake
from game.systems.resources import ResourceManager
from game.systems.save_data import (
    DEFAULT_SAVE_DATA,
    get_permanent_upgrade_cost,
    load_save,
    purchase_upgrade,
    save_game,
)
from game.systems.upgrades import RUN_UPGRADES, UpgradeOption, choose_upgrade_options
from game.ui.ui import UI


class FakePlayer:
    def __init__(self):
        self.run_upgrade_levels = {upgrade_id: 0 for upgrade_id in RUN_UPGRADES}
        self.weapons = {"missile": 1, "blade": 0, "pulse": 0}
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
        self.assertIsNone(get_permanent_upgrade_cost("max_health", 5))


class UpgradeTests(unittest.TestCase):
    def test_upgrade_choices_do_not_repeat(self):
        player = FakePlayer()
        options = choose_upgrade_options(player, count=3, rng=random.Random(7))
        ids = [option.id for option in options]

        self.assertEqual(len(options), 3)
        self.assertEqual(len(ids), len(set(ids)))


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

    def test_missing_sound_play_respects_cooldown_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResourceManager(image_dir=temp_dir, sound_dir=temp_dir)
            self.assertIsNone(manager.play("missing", cooldown=1))
            self.assertIsNone(manager.play("missing", cooldown=1))
            self.assertIn("missing", manager.last_sound_times)


class EffectTests(unittest.TestCase):
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
        level_module.save_game = lambda data: data

    def tearDown(self):
        self.level_module.save_game = self.original_save_game

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


if __name__ == "__main__":
    unittest.main()
