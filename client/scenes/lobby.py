# Host sees:
#     - Current options (read-only summary; could be made editable via
#       SET_OPTIONS later)
#     - If spiritualist_mode == "manual": a row of player buttons to
#       tap to assign who the spiritualist is
#     - "Start Game" button -- greyed out (disabled) until can_start is
#       True (i.e. enough players have joined), then becomes active
#       ("red"/primary-styled per the sketch's intent of "available")
#     - "End Game" button -- always available, returns everyone to
#       mainMenu.py

#   Non-host sees:
#     - The same player list / options, read-only
#     - "Exit" button -- leaves the lobby and returns to mainMenu.py
#       (per the brief: "join a different game", so we land them back
#       on the main menu where Join Game is one click away)

# Everyone transitions to maze.py once GAME_STARTING arrives.


import pygame

from shared import protocol
from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from client.scenes.base import Scene
from client.widgets import (
    Button,
    ChatPanel,
    COLOR_BG,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_BORDER
)

class LobbyScene(Scene):
    def on_enter(self, **kwargs):
        font_small = self.app.fonts["small"]

        self.start_button = Button((0, 0, 160, 44), "Start Game", self.app.fonts["normal"], variant="primary")
        self.end_button = Button((0, 0, 140, 40), "End Game", font_small, variant="danger")
        self.exit_button = Button((0, 0, 140, 40), "Exit", font_small, variant="danger")

        self.spiritualist_buttons = []  # list of (player_id, Button), manual mode only
        self.status_message = ""
        self.chat_open = False
        self.chat_button = Button(
            (WINDOW_WIDTH - 120, 20, 100, 40),
            "Chat",
            self.app.fonts["small"]
        )

        self.chat_panel = ChatPanel(
            (
                WINDOW_WIDTH // 2,
                0,
                WINDOW_WIDTH // 2,
                WINDOW_HEIGHT
            ),
            self.app.fonts["chat"],
            self.app.session.chat_messages
        )

        self._layout_dirty = True

    def _is_host(self):
        return self.app.session.is_host()

    def _lobby(self):
        return self.app.session.lobby_state

    def handle_event(self, event):
        lobby = self._lobby()

        if self.chat_button.handle_event(event):
            self.chat_open = not self.chat_open

        if self.chat_open:
            action, payload = self.chat_panel.handle_event(event)
            if action == "close":
                self.chat_open = False
            if action == "send":
                self.app.network.send(
                    protocol.CHAT_MESSAGE,
                    {
                        "text": payload
                    }
                )

        if not lobby:
            return

        if self._is_host():
            can_start = lobby.get("can_start", False)
            self.start_button.enabled = can_start
            if self.start_button.handle_event(event):
                self.app.network.send(protocol.START_GAME)

            if self.end_button.handle_event(event):
                self.app.network.send(protocol.END_GAME)

            if lobby.get("options", {}).get("spiritualist_mode") == "manual":
                for player_id, button in self.spiritualist_buttons:
                    if button.handle_event(event):
                        self.app.network.send(protocol.SET_SPIRITUALIST, {"player_id": player_id})
        else:
            if self.exit_button.handle_event(event):
                self.app.network.send(protocol.EXIT_LOBBY)
                self.app.session.reset_lobby()
                self.app.session.chat_messages.clear() # clear chat history
                self.app.set_scene("main_menu")

    def handle_message(self, msg_type, data):
        if msg_type == protocol.CHAT_MESSAGE:
            msg = f"{data['sender']}: {data['text']}"
            self.app.session.chat_messages.append(msg)
        
        elif msg_type == protocol.CHAT_HISTORY:
            self.app.session.chat_messages.clear()
            for msg in data.get("messages", []):

                self.app.session.chat_messages.append(
                    f"{msg['sender']}: {msg['text']}"
                )

        elif msg_type == protocol.LOBBY_STATE:
            self._layout_dirty = True
        elif msg_type == protocol.GAME_STARTING:
            # Transition is handled centrally in app.py's message pump;
            # nothing for the lobby scene to do here.
            pass
        elif msg_type == protocol.ERROR:
            self.status_message = data.get("message", "Something went wrong.")

    def _rebuild_layout(self):
        lobby = self._lobby()
        if not lobby:
            return

        font_small = self.app.fonts["small"]
        is_host = self._is_host()

        bottom_y = WINDOW_HEIGHT - 70
        if is_host:
            # self.start_button.rect.update(WINDOW_WIDTH // 2 - 170, bottom_y, 160, 44)
            # self.end_button.rect.update(WINDOW_WIDTH // 2 + 20, bottom_y + 2, 140, 40)
            self.start_button.rect.update(
                WINDOW_WIDTH // 2 - 260,
                bottom_y,
                160,
                44
            )
            self.end_button.rect.update(
                WINDOW_WIDTH // 2 - 80,
                bottom_y + 2,
                140,
                40
            )
        else:
            # self.exit_button.rect.update(WINDOW_WIDTH // 2 - 70, bottom_y, 140, 40)
            self.exit_button.rect.update(
                WINDOW_WIDTH // 2 - 260,
                bottom_y,
                160,
                44
            )

        self.spiritualist_buttons = []
        if is_host and lobby.get("options", {}).get("spiritualist_mode") == "manual":
            players = lobby.get("players", [])
            x = WINDOW_WIDTH // 2 - (len(players) * 90) // 2
            y = WINDOW_HEIGHT // 2 + 70
            for p in players:
                btn = Button((x, y, 80, 32), p["name"][:10], font_small)
                self.spiritualist_buttons.append((p["player_id"], btn))
                x += 90

        self._layout_dirty = False

    def update(self, dt):
        if self._layout_dirty:
            self._rebuild_layout()

    def draw(self, surface):
        surface.fill(COLOR_BG)
        lobby = self._lobby()
        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]

        if not lobby:
            empty_surf = font_small.render("Loading lobby...", True, COLOR_MUTED)
            surface.blit(empty_surf, (WINDOW_WIDTH // 2 - empty_surf.get_width() // 2, WINDOW_HEIGHT // 2))
            return

        title = f"{lobby['host_name']}'s Lobby"
        title_surf = font_large.render(title, True, COLOR_TEXT)
        surface.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 30))

        options = lobby.get("options", {})
        joined_text = f"Joined: {len(lobby.get('players', []))} / {options.get('num_players', '?')} players"
        joined_surf = font_small.render(joined_text, True, COLOR_MUTED)
        surface.blit(joined_surf, (WINDOW_WIDTH // 2 - joined_surf.get_width() // 2, 80))

        # Player list panel
        panel_rect = pygame.Rect(WINDOW_WIDTH // 2 - 200, 110, 400, 160)
        pygame.draw.rect(surface, COLOR_PANEL, panel_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, panel_rect, width=1, border_radius=6)

        spiritualist_id = lobby.get("spiritualist_id")
        for i, p in enumerate(lobby.get("players", [])):
            tag = ""
            if p["player_id"] == lobby.get("host_id"):
                tag += " (Host)"
            if p["player_id"] == spiritualist_id:
                tag += " [Spiritualist]"
            line = f"{p['name']}{tag}"
            line_surf = font_small.render(line, True, COLOR_TEXT)
            surface.blit(line_surf, (panel_rect.x + 16, panel_rect.y + 12 + i * 22))

        options_text = (
            f"Players: {options.get('num_players')}  |  "
            f"Spiritualist: {options.get('spiritualist_mode')}  |  "
            f"Ghosts: {options.get('num_ghosts')}"
        )
        options_surf = font_small.render(options_text, True, COLOR_MUTED)
        surface.blit(options_surf, (WINDOW_WIDTH // 2 - options_surf.get_width() // 2, panel_rect.bottom + 14))

        if self._is_host():
            self.start_button.draw(surface)
            self.end_button.draw(surface)

            if options.get("spiritualist_mode") == "manual":
                pick_label = font_small.render("Tap a player to assign as Spiritualist:", True, COLOR_MUTED)
                if self.spiritualist_buttons:
                    label_y = self.spiritualist_buttons[0][1].rect.y - 24
                    surface.blit(pick_label, (WINDOW_WIDTH // 2 - pick_label.get_width() // 2, label_y))
                for player_id, button in self.spiritualist_buttons:
                    button.variant = "primary" if player_id == spiritualist_id else "default"
                    button.draw(surface)

            if not lobby.get("can_start", False):
                hint_surf = font_small.render("Waiting for more players to join...", True, COLOR_MUTED)
                surface.blit(
                    hint_surf,
                    (WINDOW_WIDTH // 2 - hint_surf.get_width() // 2, self.start_button.rect.bottom + 10),
                )
        else:
            self.exit_button.draw(surface)
            waiting_surf = font_small.render("Waiting for host to start game...", True, COLOR_MUTED)
            surface.blit(
                waiting_surf,
                (WINDOW_WIDTH // 2 - waiting_surf.get_width() // 2, self.exit_button.rect.y - 30),
            )

        if self.status_message:
            status_surf = font_small.render(self.status_message, True, COLOR_MUTED)
            surface.blit(status_surf, (WINDOW_WIDTH // 2 - status_surf.get_width() // 2, panel_rect.bottom + 40))

        # for the chat panel
        self.chat_button.draw(surface)

        if self.chat_open:
            self.chat_panel.draw(surface)
        
