import pygame

from shared import protocol
from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from client.scenes.base import Scene
from client.widgets import TextInput, Button, COLOR_BG, COLOR_TEXT, COLOR_MUTED


class LoginScene(Scene):
    def on_enter(self, **kwargs):
        font = self.app.fonts["normal"]
        input_w, input_h = 280, 40
        self.name_input = TextInput(
            (WINDOW_WIDTH // 2 - input_w // 2, WINDOW_HEIGHT // 2 - 20, input_w, input_h),
            font,
            placeholder="Enter your name",
            max_length=16,
        )
        self.name_input.active = True

        self.submit_button = Button(
            (WINDOW_WIDTH // 2 - 70, WINDOW_HEIGHT // 2 + 40, 140, 40),
            "Submit", font, variant="primary",
        )

        self.status_message = ""
        self.awaiting_response = False

    def handle_event(self, event):
        self.name_input.handle_event(event)

        submitted = self.submit_button.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            submitted = True

        if submitted and not self.awaiting_response:
            self._try_submit()

    def _try_submit(self):
        name = self.name_input.text.strip()
        if not name:
            self.status_message = "Please enter a name."
            return

        if not self.app.network.connected:
            self.status_message = "Connecting..."
            try:
                self.app.network.connect()
            except OSError:
                self.status_message = "Could not reach server. Is it running?"
                return

        self.app.network.send(protocol.LOGIN, {"name": name})
        self.awaiting_response = True
        self.status_message = "Logging in..."

    def handle_message(self, msg_type, data):
        if msg_type == protocol.LOGIN_OK:
            self.app.session.player_id = data["player_id"]
            self.app.session.player_name = data["name"]
            self.app.set_scene("main_menu")
        elif msg_type == protocol.ERROR:
            self.awaiting_response = False
            self.status_message = data.get("message", "Login failed.")
        elif msg_type == "DISCONNECTED":
            self.awaiting_response = False
            self.status_message = "Could not reach server. Is it running?"

    def update(self, dt):
        self.name_input.update(dt)

    def draw(self, surface):
        surface.fill(COLOR_BG)
        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]

        title_surf = font_large.render("Login", True, COLOR_TEXT)
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, WINDOW_HEIGHT // 2 - 90))

        label_surf = font_small.render("Select a name:", True, COLOR_MUTED)
        surface.blit(label_surf, (self.name_input.rect.x, self.name_input.rect.y - 24))

        self.name_input.draw(surface)
        self.submit_button.draw(surface)

        if self.status_message:
            status_surf = font_small.render(self.status_message, True, COLOR_MUTED)
            surface.blit(
                status_surf,
                (WINDOW_WIDTH // 2 - status_surf.get_width() // 2, self.submit_button.rect.bottom + 16),
            )
