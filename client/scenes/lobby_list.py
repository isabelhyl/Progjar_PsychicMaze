# each row shows a lobby (host's name + player count) with a "Join" button. 
# Requests the list on entry and re-requests periodically so it doesn't go stale while the player is browsing
# (a lobby could fill up or close while they're here).


import pygame

from shared import protocol
from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from client.scenes.base import Scene
from client.widgets import Button, COLOR_BG, COLOR_TEXT, COLOR_MUTED, COLOR_PANEL, COLOR_BORDER

REFRESH_INTERVAL = 2.0  # seconds between automatic LIST_LOBBIES re-requests
ROW_HEIGHT = 48
ROW_GAP = 8
LIST_TOP = 90
LIST_WIDTH = 480


class LobbyListScene(Scene):
    def on_enter(self, **kwargs):
        self._refresh_timer = 0.0
        self.status_message = ""
        self.row_buttons = []  # list of (lobby_id, Button)

        self.back_button = Button(
            (WINDOW_WIDTH // 2 - 70, WINDOW_HEIGHT - 60, 140, 40),
            "Back", self.app.fonts["small"],
        )

        self._request_list()
        self._rebuild_rows()

    def _request_list(self):
        self.app.network.send(protocol.LIST_LOBBIES)

    def _rebuild_rows(self):
        font = self.app.fonts["small"]
        self.row_buttons = []
        x = WINDOW_WIDTH // 2 - LIST_WIDTH // 2

        for i, lobby in enumerate(self.app.session.lobby_list):
            y = LIST_TOP + i * (ROW_HEIGHT + ROW_GAP)
            join_btn = Button((x + LIST_WIDTH - 90, y + 6, 70, ROW_HEIGHT - 12), "Join", font, variant="primary")
            self.row_buttons.append((lobby["lobby_id"], join_btn))

    def handle_event(self, event):
        for lobby_id, button in self.row_buttons:
            if button.handle_event(event):
                self.app.network.send(protocol.JOIN_GAME, {"lobby_id": lobby_id})
                self.status_message = "Joining..."

        if self.back_button.handle_event(event):
            self.app.set_scene("main_menu")

    def handle_message(self, msg_type, data):
        if msg_type == protocol.LOBBY_LIST:
            self._rebuild_rows()
        elif msg_type == protocol.LOBBY_STATE:
            self.app.session.lobby_state = data
            self.app.set_scene("lobby")
        elif msg_type == protocol.ERROR:
            self.status_message = data.get("message", "Could not join lobby.")

    def update(self, dt):
        self._refresh_timer += dt
        if self._refresh_timer >= REFRESH_INTERVAL:
            self._refresh_timer = 0.0
            self._request_list()

    def draw(self, surface):
        surface.fill(COLOR_BG)
        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]

        title_surf = font_large.render("List of Lobbies", True, COLOR_TEXT)
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 30))

        x = WINDOW_WIDTH // 2 - LIST_WIDTH // 2
        lobbies = self.app.session.lobby_list

        if not lobbies:
            empty_surf = font_small.render("No lobbies available yet.", True, COLOR_MUTED)
            surface.blit(empty_surf, (WINDOW_WIDTH // 2 - empty_surf.get_width() // 2, LIST_TOP + 10))

        for i, lobby in enumerate(lobbies):
            y = LIST_TOP + i * (ROW_HEIGHT + ROW_GAP)
            row_rect = pygame.Rect(x, y, LIST_WIDTH, ROW_HEIGHT)
            pygame.draw.rect(surface, COLOR_PANEL, row_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_BORDER, row_rect, width=1, border_radius=6)

            label = f"{lobby['host_name']}'s Lobby"
            count = f"{lobby['num_players']} / {lobby['max_players']} players"
            label_surf = font_small.render(label, True, COLOR_TEXT)
            count_surf = font_small.render(count, True, COLOR_MUTED)
            surface.blit(label_surf, (row_rect.x + 16, row_rect.y + 8))
            surface.blit(count_surf, (row_rect.x + 16, row_rect.y + 26))

            _, join_btn = self.row_buttons[i]
            join_btn.draw(surface)

        self.back_button.draw(surface)

        if self.status_message:
            status_surf = font_small.render(self.status_message, True, COLOR_MUTED)
            surface.blit(
                status_surf,
                (WINDOW_WIDTH // 2 - status_surf.get_width() // 2, self.back_button.rect.y - 30),
            )
