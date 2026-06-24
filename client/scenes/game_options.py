# Lets the host configure:
#   - Number of players (stepper)
#   - Spiritualist mode: random/manual (toggle)
#   - Number of ghosts (stepper)


import pygame

from shared import protocol
from shared.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    MIN_PLAYERS, MAX_PLAYERS, DEFAULT_NUM_PLAYERS,
    MIN_GHOSTS, MAX_GHOSTS, DEFAULT_NUM_GHOSTS,
)
from client.scenes.base import Scene
from client.widgets import Button, Stepper, ToggleGroup, COLOR_BG, COLOR_TEXT, COLOR_MUTED


class GameOptionsScene(Scene):
    def on_enter(self, **kwargs):
        font = self.app.fonts["normal"]
        font_small = self.app.fonts["small"]

        panel_x = WINDOW_WIDTH // 2 - 170
        row_w = 340
        row_h = 36
        gap = 20
        y = WINDOW_HEIGHT // 2 - 110

        self.players_stepper = Stepper(
            (panel_x, y, row_w, row_h), font, DEFAULT_NUM_PLAYERS, MIN_PLAYERS, MAX_PLAYERS
        )
        y += row_h + gap

        self.spiritualist_toggle = ToggleGroup(
            (panel_x, y, row_w, row_h), font_small,
            options=[("random", "Random"), ("manual", "Manual")],
            selected="random",
        )
        y += row_h + gap

        self.ghosts_stepper = Stepper(
            (panel_x, y, row_w, row_h), font, DEFAULT_NUM_GHOSTS, MIN_GHOSTS, MAX_GHOSTS
        )
        y += row_h + gap + 10

        self.create_button = Button((WINDOW_WIDTH // 2 - 90, y, 180, 44), "Create Lobby", font, variant="primary")
        self.back_button = Button((WINDOW_WIDTH // 2 - 90, y + 54, 180, 36), "Back", font_small)

        self.status_message = ""
        self.awaiting_create = False

    def handle_event(self, event):
        self.players_stepper.handle_event(event)
        self.spiritualist_toggle.handle_event(event)
        self.ghosts_stepper.handle_event(event)

        if self.back_button.handle_event(event):
            self.app.set_scene("main_menu")

        if self.create_button.handle_event(event) and not self.awaiting_create:
            self.app.network.send(protocol.CREATE_GAME, {
                "num_players": self.players_stepper.value,
                "spiritualist_mode": self.spiritualist_toggle.selected,
                "num_ghosts": self.ghosts_stepper.value,
            })
            self.awaiting_create = True
            self.status_message = "Creating lobby..."

    def handle_message(self, msg_type, data):
        if msg_type == protocol.LOBBY_STATE and self.awaiting_create:
            self.awaiting_create = False
            self.app.session.lobby_state = data
            self.app.set_scene("lobby")
        elif msg_type == protocol.ERROR:
            self.awaiting_create = False
            self.status_message = data.get("message", "Could not create lobby.")

    def draw(self, surface):
        surface.fill(COLOR_BG)
        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]

        title_surf = font_large.render("Game Options", True, COLOR_TEXT)
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, WINDOW_HEIGHT // 2 - 170))

        self._draw_row_label("Number of players", self.players_stepper.rect, font_small, surface)
        self._draw_row_label("Spiritualist", self.spiritualist_toggle.buttons[0][1].rect, font_small, surface, full_row_rect=self._toggle_row_rect())
        self._draw_row_label("Number of ghosts", self.ghosts_stepper.rect, font_small, surface)

        self.players_stepper.draw(surface)
        self.spiritualist_toggle.draw(surface)
        self.ghosts_stepper.draw(surface)

        self.create_button.draw(surface)
        self.back_button.draw(surface)

        if self.status_message:
            status_surf = font_small.render(self.status_message, True, COLOR_MUTED)
            surface.blit(
                status_surf,
                (WINDOW_WIDTH // 2 - status_surf.get_width() // 2, self.back_button.rect.bottom + 14),
            )

    def _toggle_row_rect(self):
        first_rect = self.spiritualist_toggle.buttons[0][1].rect
        last_rect = self.spiritualist_toggle.buttons[-1][1].rect
        width = last_rect.right - first_rect.x
        return pygame.Rect(first_rect.x, first_rect.y, width, first_rect.height)

    def _draw_row_label(self, text, rect, font, surface, full_row_rect=None):
        target_rect = full_row_rect if full_row_rect else rect
        label_surf = font.render(text, True, COLOR_MUTED)
        surface.blit(label_surf, (target_rect.x, target_rect.y - 20))
