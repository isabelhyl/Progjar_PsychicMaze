# server/state.py

# In-memory data model for connected players and active lobbies
# The server is the single source of truth: clients never mutate this
# state directly, they only send action messages and receive broadcasts
# of the resulting state (see server/server.py)

# This module has no networking code in it on purpose, so it can be
# tested or reasoned about without spinning up sockets

import itertools
import random
import threading

from shared.constants import (
    DEFAULT_NUM_PLAYERS,
    DEFAULT_NUM_GHOSTS,
    MIN_PLAYERS,
    MAX_PLAYERS,
    MIN_GHOSTS,
    MAX_GHOSTS,
)

_id_counter = itertools.count(1)
_id_lock = threading.Lock()


def _next_id(prefix):
    with _id_lock:
        n = next(_id_counter)
    return f"{prefix}_{n}"


class Player:
    # a connected player 'conn' is set by the server when a socket is associated with this player
    # state.py itself never touches sockets.

    def __init__(self, name):
        self.player_id = _next_id("player")
        self.name = name
        self.lobby_id = None  # set once they join/create a lobby

    def to_public_dict(self):
        return {"player_id": self.player_id, "name": self.name}


class GameOptions:
    # toggleable options chosen on the gameOptions.py lobby screen 

    def __init__(self):
        self.num_players = DEFAULT_NUM_PLAYERS
        self.spiritualist_mode = "random"  
        self.num_ghosts = DEFAULT_NUM_GHOSTS

    def update(self, num_players=None, spiritualist_mode=None, num_ghosts=None):
        if num_players is not None:
            self.num_players = max(MIN_PLAYERS, min(MAX_PLAYERS, int(num_players)))
        if spiritualist_mode is not None and spiritualist_mode in ("random", "manual"):
            self.spiritualist_mode = spiritualist_mode
        if num_ghosts is not None:
            self.num_ghosts = max(MIN_GHOSTS, min(MAX_GHOSTS, int(num_ghosts)))

    def to_dict(self):
        return {
            "num_players": self.num_players,
            "spiritualist_mode": self.spiritualist_mode,
            "num_ghosts": self.num_ghosts,
        }


class Lobby:
    def __init__(self, host_player):
        self.lobby_id = _next_id("lobby")
        self.host_id = host_player.player_id
        self.players = {host_player.player_id: host_player} 
        self.options = GameOptions()
        self.spiritualist_id = None
        self.started = False
        self.chat_messages = []
        host_player.lobby_id = self.lobby_id

    @property
    def host_name(self):
        host = self.players.get(self.host_id)
        return host.name if host else "?"

    def add_player(self, player):
        if len(self.players) >= self.options.num_players:
            raise ValueError("Lobby is full")
        if self.started:
            raise ValueError("Game already started")
        self.players[player.player_id] = player
        player.lobby_id = self.lobby_id

    def remove_player(self, player_id):
        self.players.pop(player_id, None)
        if self.spiritualist_id == player_id:
            self.spiritualist_id = None

        # if the host left (disconnected), promote the longest-standing remaining player so that no one is unable to start/end the game later on
        if player_id == self.host_id and self.players:
            self.host_id = next(iter(self.players))

    def is_host(self, player_id):
        return player_id == self.host_id

    def can_start(self):
        return (not self.started) and len(self.players) >= self.options.num_players

    def assign_spiritualist(self, player_id=None):
        # pick spiritualist according to options.spiritualist_mode
        # manual mode = spiritualist is picked by host
        # random mode = spiritualist is chosen automatically
        if self.options.spiritualist_mode == "manual" and player_id is not None:
            if player_id in self.players:
                self.spiritualist_id = player_id
                return
        # fallback: random choice among current players
        self.spiritualist_id = random.choice(list(self.players.keys()))

    def to_public_dict(self):
        return {
            "lobby_id": self.lobby_id,
            "host_id": self.host_id,
            "host_name": self.host_name,
            "players": [p.to_public_dict() for p in self.players.values()],
            "options": self.options.to_dict(),
            "spiritualist_id": self.spiritualist_id,
            "can_start": self.can_start(),
            "started": self.started,
            "chat_messages": self.chat_messages,
        }

    def to_summary_dict(self):
        # smaller view used for the lobbyList.py screen
        return {
            "lobby_id": self.lobby_id,
            "host_name": self.host_name,
            "num_players": len(self.players),
            "max_players": self.options.num_players,
        }


class GameState:
    # container for everything the server is tracking
    # (one instance of this is created in server.py and shared (with a lock) across all client-handler threads

    def __init__(self):
        self.lock = threading.RLock()
        self.players = {} 
        self.lobbies = {}

    # players
    def add_player(self, name):
        player = Player(name)
        with self.lock:
            self.players[player.player_id] = player
        return player

    def get_player(self, player_id):
        return self.players.get(player_id)

    def remove_player(self, player_id):
        with self.lock:
            player = self.players.pop(player_id, None)
            if player and player.lobby_id:
                lobby = self.lobbies.get(player.lobby_id)
                if lobby:
                    lobby.remove_player(player_id)
                    if not lobby.players:
                        self.lobbies.pop(lobby.lobby_id, None)
        return player

    # lobbies
    def create_lobby(self, host_player):
        with self.lock:
            lobby = Lobby(host_player)
            self.lobbies[lobby.lobby_id] = lobby
        return lobby

    def get_lobby(self, lobby_id):
        return self.lobbies.get(lobby_id)

    def get_lobby_for_player(self, player_id):
        player = self.players.get(player_id)
        if not player or not player.lobby_id:
            return None
        return self.lobbies.get(player.lobby_id)

    def list_lobby_summaries(self):
        with self.lock:
            return [
                lobby.to_summary_dict()
                for lobby in self.lobbies.values()
                if not lobby.started
            ]

    def remove_lobby_if_empty(self, lobby_id):
        with self.lock:
            lobby = self.lobbies.get(lobby_id)
            if lobby and not lobby.players:
                self.lobbies.pop(lobby_id, None)
