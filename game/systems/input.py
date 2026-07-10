import pygame

from game.config.settings import SCREEN_HEIGHT, SCREEN_WIDTH


class InputManager:
    def __init__(self, display_manager=None, settings_data=None):
        self.display_manager = display_manager
        self.settings_data = settings_data or {}
        self.touch_controls_enabled = False
        self.active_touch_id = None
        self.skill_touch_id = None
        self.joystick_origin = pygame.math.Vector2(118, SCREEN_HEIGHT - 118)
        self.joystick_vector = pygame.math.Vector2()
        self.skill_rect = pygame.Rect(SCREEN_WIDTH - 162, SCREEN_HEIGHT - 154, 104, 104)
        self.skill_pressed = False
        self.suppress_mouse_frames = 0
        self.refresh_settings(self.settings_data)

    def refresh_settings(self, settings_data):
        self.settings_data = settings_data or {}
        touch_setting = self.settings_data.get("touch_controls", "auto")
        self.touch_controls_enabled = touch_setting is True
        if touch_setting == "auto":
            self.touch_controls_enabled = self.detect_touch_device()

    def detect_touch_device(self):
        try:
            return pygame.display.get_driver().lower() in ("android", "wayland")
        except pygame.error:
            return False

    def begin_frame(self):
        self.skill_pressed = False
        if self.suppress_mouse_frames > 0:
            self.suppress_mouse_frames -= 1

    def logical_mouse_pos(self):
        pos = pygame.mouse.get_pos()
        if self.display_manager:
            logical = self.display_manager.to_logical(pos)
            return logical if logical is not None else (-9999, -9999)
        return pos

    def movement_vector(self):
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction.x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction.y += 1

        if self.joystick_vector.magnitude() > 0:
            direction += self.joystick_vector

        if direction.magnitude() > 1:
            direction = direction.normalize()
        return direction

    def normalize_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.suppress_mouse_frames > 0:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            logical = self.to_logical(event.pos)
            if logical is None:
                return None
            if self.touch_controls_enabled and self.skill_rect.collidepoint(logical):
                self.skill_pressed = True
                return {"type": "skill", "pos": logical}
            return {"type": "mouse_down", "pos": logical}

        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return self.handle_finger_event(event)

        return event

    def to_logical(self, pos):
        if self.display_manager:
            return self.display_manager.to_logical(pos)
        return pos

    def finger_to_window_pos(self, event):
        if self.display_manager and self.display_manager.window_surface:
            width, height = self.display_manager.window_surface.get_size()
        else:
            width, height = SCREEN_WIDTH, SCREEN_HEIGHT
        return event.x * width, event.y * height

    def finger_to_logical_pos(self, event):
        return self.to_logical(self.finger_to_window_pos(event))

    def handle_finger_event(self, event):
        logical = self.finger_to_logical_pos(event)
        self.suppress_mouse_frames = 3
        if logical is None:
            return None

        pos_vector = pygame.math.Vector2(logical)
        if event.type == pygame.FINGERDOWN:
            if self.touch_controls_enabled and self.skill_rect.collidepoint(logical):
                self.skill_touch_id = event.finger_id
                self.skill_pressed = True
                return {"type": "skill", "pos": logical}
            if self.touch_controls_enabled and logical[0] < SCREEN_WIDTH * 0.42 and logical[1] > SCREEN_HEIGHT * 0.48:
                self.active_touch_id = event.finger_id
                self.joystick_origin = pos_vector
                self.update_joystick(pos_vector)
                return None
            return {"type": "mouse_down", "pos": logical}

        if event.type == pygame.FINGERMOTION:
            if event.finger_id == self.active_touch_id:
                self.update_joystick(pos_vector)
            return None

        if event.type == pygame.FINGERUP:
            if event.finger_id == self.active_touch_id:
                self.active_touch_id = None
                self.joystick_vector.update(0, 0)
            if event.finger_id == self.skill_touch_id:
                self.skill_touch_id = None
            return None

        return None

    def update_joystick(self, pos):
        offset = pygame.math.Vector2(pos) - self.joystick_origin
        if offset.magnitude() > 64:
            offset.scale_to_length(64)
        self.joystick_vector = offset / 64

    def consume_skill_pressed(self):
        pressed = self.skill_pressed
        self.skill_pressed = False
        return pressed

    def draw_touch_controls(self, surface, skill_ready=True):
        if not self.touch_controls_enabled:
            return

        base_center = (int(self.joystick_origin.x), int(self.joystick_origin.y))
        knob = pygame.math.Vector2(base_center) + self.joystick_vector * 52
        joystick_surface = pygame.Surface((180, 180), pygame.SRCALPHA)
        pygame.draw.circle(joystick_surface, (91, 217, 235, 46), (90, 90), 68)
        pygame.draw.circle(joystick_surface, (255, 255, 255, 72), (90, 90), 68, 2)
        surface.blit(joystick_surface, (base_center[0] - 90, base_center[1] - 90))
        pygame.draw.circle(surface, (91, 217, 235, 130), (int(knob.x), int(knob.y)), 24)
        pygame.draw.circle(surface, (255, 255, 255, 150), (int(knob.x), int(knob.y)), 24, 2)

        color = (244, 190, 62, 130) if skill_ready else (92, 104, 126, 100)
        button_surface = pygame.Surface(self.skill_rect.size, pygame.SRCALPHA)
        pygame.draw.circle(button_surface, color, (self.skill_rect.width // 2, self.skill_rect.height // 2), 50)
        pygame.draw.circle(button_surface, (255, 255, 255, 150), (self.skill_rect.width // 2, self.skill_rect.height // 2), 50, 3)
        surface.blit(button_surface, self.skill_rect.topleft)
