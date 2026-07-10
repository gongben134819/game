import copy
import os
import tempfile
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game.config.settings import SCREEN_HEIGHT, SCREEN_WIDTH
from game.core.level import Level
from game.entities.player import Player
from game.systems.chapters import CHAPTER_ORDER, MapMechanicController, chapter_unlocked
from game.systems.characters import CHARACTERS
from game.systems.resources import ResourceManager
from game.systems.save_data import DEFAULT_SAVE_DATA, load_save, normalize_save_data, record_run, save_game
from game.systems.unlocks import purchase_character_unlock, purchase_item, purchase_weapon_unlock
from game.systems.upgrades import build_upgrade_pool
from game.ui.ui import UI


class ContentSaveTests(unittest.TestCase):
    def test_old_or_broken_save_resets_to_v2_schema(self):
        old_data = {
            "total_gold": 999,
            "high_score": 123,
            "longest_time": 45,
            "permanent_upgrades": {"max_health": 3},
        }
        normalized = normalize_save_data(old_data)

        self.assertEqual(normalized["version"], 2)
        self.assertEqual(normalized["total_gold"], 0)
        self.assertEqual(normalized["unlocked_characters"], ["mage"])
        self.assertEqual(set(normalized["unlocked_weapons"]), {"missile", "blade", "pulse"})
        self.assertIn("blueprints", normalized)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "save_data.json")
            with open(path, "w", encoding="utf-8") as file:
                file.write("{broken")
            self.assertEqual(load_save(path), DEFAULT_SAVE_DATA)

    def test_record_run_unlocks_chapter_and_records_endless_blueprints(self):
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        result = record_run(
            data,
            score=1200,
            elapsed_time=361,
            gold_earned=80,
            victory=True,
            mode="chapter",
            chapter_id="mine",
            blueprints={"weapon": 2},
        )

        self.assertIn("mine", result["completed_chapters"])
        self.assertTrue(chapter_unlocked(result, "lava"))
        self.assertEqual(result["blueprints"]["weapon"], 2)

        endless = record_run(result, 1300, 540, 35, False, "endless", endless_floor=4, blueprints={"item": 3})
        self.assertEqual(endless["endless_highest_floor"], 4)
        self.assertEqual(endless["blueprints"]["item"], 3)

    def test_save_round_trip_keeps_new_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "save_data.json")
            data = copy.deepcopy(DEFAULT_SAVE_DATA)
            data["completed_chapters"] = ["mine", "lava"]
            data["unlocked_characters"].append("knight")
            data["unlocked_weapons"].append("flame")
            data["blueprints"]["character"] = 2
            saved = save_game(data, path)
            loaded = load_save(path)

        self.assertEqual(saved, loaded)
        self.assertIn("knight", loaded["unlocked_characters"])
        self.assertIn("flame", loaded["unlocked_weapons"])


class UnlockSystemTests(unittest.TestCase):
    def test_mixed_unlock_consumes_gold_and_blueprints(self):
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["completed_chapters"] = ["mine"]
        data["total_gold"] = 500
        data["blueprints"]["weapon"] = 2

        data, success, message = purchase_weapon_unlock(data, "flame")

        self.assertTrue(success, message)
        self.assertIn("flame", data["unlocked_weapons"])
        self.assertEqual(data["blueprints"]["weapon"], 1)
        self.assertLess(data["total_gold"], 500)

    def test_character_and_item_unlocks_respect_requirements(self):
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["total_gold"] = 1000
        data["blueprints"]["character"] = 3

        data, success, message = purchase_character_unlock(data, "engineer")
        self.assertFalse(success)
        self.assertIn("无尽", message)

        data["endless_highest_floor"] = 3
        data, success, message = purchase_character_unlock(data, "engineer")
        self.assertTrue(success, message)
        self.assertIn("engineer", data["unlocked_characters"])

        data["completed_chapters"] = ["mine"]
        data["blueprints"]["item"] = 2
        data, success, message = purchase_item(data, "starter_magnet")
        self.assertTrue(success, message)
        self.assertEqual(data["item_levels"]["starter_magnet"], 1)

    def test_locked_weapons_are_filtered_from_upgrade_pool(self):
        class FakePlayer:
            def __init__(self):
                self.run_upgrade_levels = {
                    "damage": 0,
                    "fire_rate": 0,
                    "missile_count": 0,
                    "move_speed": 0,
                    "max_health": 0,
                    "pickup_range": 0,
                }
                self.weapons = {"missile": 1, "blade": 0, "pulse": 0, "flame": 0, "frost": 0, "drone": 0}
                self.weapon_evolutions = set()
                self.unlocked_weapons = {"missile", "blade", "pulse"}

        player = FakePlayer()
        pool_ids = {option.id for option in build_upgrade_pool(player)}
        self.assertNotIn("weapon:flame", pool_ids)

        player.unlocked_weapons.add("flame")
        pool_ids = {option.id for option in build_upgrade_pool(player)}
        self.assertIn("weapon:flame", pool_ids)


class CharacterAndMechanicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_six_characters_initialize_with_distinct_active_skills(self):
        resources = ResourceManager(image_dir="", sound_dir="")
        all_weapons = {"missile", "blade", "pulse", "flame", "frost", "drone"}
        active_names = set()

        for character_id, character in CHARACTERS.items():
            player = Player(
                (100, 100),
                resources,
                {},
                None,
                character_id=character_id,
                unlocked_weapons=all_weapons,
            )
            self.assertEqual(player.character_id, character_id)
            self.assertEqual(player.weapons[character.initial_weapon], 1)
            self.assertGreater(player.active_cooldown, 0)
            active_names.add(player.character.active_name)

        self.assertEqual(len(active_names), 6)

    def test_space_active_skill_only_changes_playing_state(self):
        level = Level()
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        level.start_chapter("mine")
        self.assertTrue(level.player.skill_ready())
        self.assertTrue(level.activate_player_skill())
        self.assertGreater(level.player.active_timer, 0)

        level.state = level.MENU
        before = level.player.active_timer
        self.assertFalse(level.activate_player_skill())
        self.assertEqual(level.player.active_timer, before)

    def test_map_mechanics_update_and_draw_without_crashing(self):
        level = Level()
        level.save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        level.start_chapter("mine")

        for chapter_id in CHAPTER_ORDER:
            controller = MapMechanicController(chapter_id)
            controller.timer = 99
            controller.update(level, 0.1)
            controller.draw(self.surface)


class ContentUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_new_menu_and_selection_pages_record_hit_regions(self):
        ui = UI(self.surface)
        save_data = copy.deepcopy(DEFAULT_SAVE_DATA)

        ui.draw_menu(save_data)
        self.assertEqual(ui.hit_menu(ui.menu_buttons["chapter"].center), "chapter")
        self.assertEqual(ui.hit_menu(ui.menu_buttons["endless"].center), "endless")
        self.assertEqual(ui.hit_menu(ui.menu_buttons["characters"].center), "characters")

        ui.draw_chapter_select(save_data)
        first_chapter = next(button for button in ui.chapter_buttons if button.get("chapter_id") == "mine")
        self.assertEqual(ui.hit_chapter(first_chapter["rect"].center)["chapter_id"], "mine")

        ui.draw_endless_select(save_data)
        self.assertEqual(ui.hit_endless(ui.endless_buttons["start"].center), "start")

        ui.draw_character_select(save_data)
        mage = next(button for button in ui.character_buttons if button.get("character_id") == "mage")
        self.assertEqual(ui.hit_character(mage["rect"].center)["character_id"], "mage")

    def test_shop_tabs_and_unlock_rows_are_clickable(self):
        ui = UI(self.surface)
        save_data = copy.deepcopy(DEFAULT_SAVE_DATA)
        save_data["completed_chapters"] = ["mine"]
        save_data["total_gold"] = 1000
        save_data["blueprints"]["weapon"] = 2

        ui.draw_shop(save_data, active_tab="weapons")
        tabs = [button for button in ui.shop_buttons if button["action"] == "tab"]
        self.assertEqual({button["tab"] for button in tabs}, {"upgrades", "characters", "weapons", "items"})
        flame = next(button for button in ui.shop_buttons if button.get("id") == "flame")
        self.assertEqual(ui.hit_shop(flame["rect"].center)["id"], "flame")


if __name__ == "__main__":
    unittest.main()
