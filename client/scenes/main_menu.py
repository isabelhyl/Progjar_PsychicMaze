import pygame

from shared import protocol
from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from client.scenes.base import Scene
from client.widgets import Button, COLOR_BG, COLOR_TEXT, COLOR_MUTED


class MainMenuScene(Scene):
    def on_enter(self, **kwargs):
        font = self.app.fonts["normal"]
        
        # btn_w, btn_h = 180, 50
        # gap = 30
        # total_w = btn_w * 2 + gap
        # start_x = WINDOW_WIDTH // 2 - total_w // 2
        
        btn_w, btn_h = 180, 50
        gap = 30
        total_w = btn_w * 3 + gap * 2
        start_x = WINDOW_WIDTH // 2 - total_w // 2

        y = WINDOW_HEIGHT // 2

        self.create_button = Button((start_x, y, btn_w, btn_h), "Create Game", font, variant="primary")
        self.join_button = Button((start_x + btn_w + gap, y, btn_w, btn_h), "Join Game", font)
        self.quit_button = Button((start_x + (btn_w + gap) * 2, y, btn_w, btn_h), "Quit", font, variant="danger")

        self.status_message = ""

    def handle_event(self, event):
        if self.create_button.handle_event(event):
            # gameOptions.py owns sending CREATE_GAME once options are confirmed, so we just navigate there for now
            self.app.set_scene("game_options")

        if self.join_button.handle_event(event):
            self.app.set_scene("lobby_list")

        if self.quit_button.handle_event(event):
            pygame.quit()
            raise SystemExit

    def handle_message(self, msg_type, data):
        if msg_type == protocol.ERROR:
            self.status_message = data.get("message", "Something went wrong.")

    def draw(self, surface):
        surface.fill(COLOR_BG)
        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]

        title_surf = font_large.render("MAIN MENU", True, COLOR_TEXT)
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, WINDOW_HEIGHT // 2 - 100))

        if self.app.session.player_name:
            greeting = font_small.render(f"Logged in as {self.app.session.player_name}", True, COLOR_MUTED)
            surface.blit(greeting, (WINDOW_WIDTH // 2 - greeting.get_width() // 2, WINDOW_HEIGHT // 2 - 60))

        self.create_button.draw(surface)
        self.join_button.draw(surface)
        self.quit_button.draw(surface)

        if self.status_message:
            status_surf = font_small.render(self.status_message, True, COLOR_MUTED)
            surface.blit(
                status_surf,
                (WINDOW_WIDTH // 2 - status_surf.get_width() // 2, self.create_button.rect.bottom + 20),
            )
