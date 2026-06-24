"""
client/app.py

The application shell: owns the single pygame window, the network
connection, the session, and the currently-active Scene. Run this to
play the game:

    py client.app

(run from the project ROOT directory, i.e. Progjar_PsychicMaze/, same
convention as windowCode.py and server/server.py.)

Per-frame flow
--------------
1. Pump pygame events -> forward each to the active scene.
2. Poll the network client for any messages received since last frame.
   A few message types (ERROR, LOBBY_LIST, LOBBY_STATE, DISCONNECTED)
   are handled here centrally since every scene cares about them the
   same way; everything else is forwarded to the active scene.
3. Call scene.update(dt) then scene.draw(screen).
"""

import sys

import pygame

from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS
from shared import protocol
from client.network import NetworkClient
from client.session import Session

from client.scenes.login import LoginScene
from client.scenes.main_menu import MainMenuScene
from client.scenes.game_options import GameOptionsScene
from client.scenes.lobby_list import LobbyListScene
from client.scenes.lobby import LobbyScene
from client.scenes.maze_scene import MazeScene
from client.scenes.tutorial import TutorialScene

class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Psychic Maze")
        self.clock = pygame.time.Clock()

        self.fonts = {
            "small": pygame.font.SysFont(None, 20),
            "normal": pygame.font.SysFont(None, 26),
            "large": pygame.font.SysFont(None, 38),
        }

        self.network = NetworkClient()
        self.session = Session()

        self.scenes = {
            "login": LoginScene(self),
            "main_menu": MainMenuScene(self),
            "game_options": GameOptionsScene(self),
            "lobby_list": LobbyListScene(self),
            "lobby": LobbyScene(self),
            "tutorial": TutorialScene(self),
            "maze": MazeScene(self),
        }
        self.active_scene_name = None
        self.active_scene = None

        self.running = True

    def set_scene(self, name, **kwargs):
        if self.active_scene:
            self.active_scene.on_exit()
        self.active_scene_name = name
        self.active_scene = self.scenes[name]
        self.active_scene.on_enter(**kwargs)

    def run(self):
        self.set_scene("login")

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.active_scene.handle_event(event)

            self._poll_network()

            self.active_scene.update(dt)
            self.active_scene.draw(self.screen)
            pygame.display.update()

        self.network.close()
        pygame.quit()
        sys.exit()

    def _poll_network(self):
        for msg in self.network.poll():
            msg_type = msg.get("type")
            data = msg.get("data", {})

            if msg_type == "DISCONNECTED":
                self.session.error_message = "Lost connection to server."
                self.active_scene.handle_message(msg_type, data)
                continue

            if msg_type == protocol.ERROR:
                self.session.error_message = data.get("message", "Unknown error")

            elif msg_type == protocol.LOBBY_LIST:
                self.session.lobby_list = data.get("lobbies", [])

            elif msg_type == protocol.LOBBY_STATE:
                self.session.lobby_state = data

            elif msg_type == protocol.RETURN_TO_MENU:
                self.session.reset_lobby()
                self.set_scene("main_menu")
                continue

            elif msg_type == protocol.GAME_STARTING:
                # server sends this individually per player with their role and the full maze layout
                # transition immediately to maze
                self.set_scene("tutorial",
                               maze_data=data.get("maze"),
                               your_role=data.get("your_role", "explorer"))
                continue

            # always forward to the active scene too, so it can react immediately 
            # maze scene handles GAME_STATE, PLAYER_DIED, GAME_OVER
            # lobby scene handles redisplayed LOBBY_STATE etc
            self.active_scene.handle_message(msg_type, data)


if __name__ == "__main__":
    App().run()
