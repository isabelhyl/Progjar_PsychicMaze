# Runs the actual maze gameplay for one lobby once the host hits "Start Game"
# One GameSession is created per started lobby and owns:

# - The maze layout (reused from maze.py's generator (see imports below; maze.py is at the project root, so this relies on running everything from there, same convention as windowCode.py)
# - Every player's position, role (spiritualist/explorer), and alive/dead state
# - Every ghost's position and basic chase-the-nearest-explorer AI
# - A fixed-rate simulation tick (GAME_TICK_RATE) that:
#   1. Applies the latest movement input each player last sent
#   2. Moves ghosts toward their nearest living explorer
#   3. Checks ghost-vs-explorer collisions (catches)
#   4. Checks explorer-vs-exit collisions (escapes)
#   5. Evaluates win/lose conditions
#   6. Broadcasts the resulting state to every player in the lobby

# COLLISION MODEL
# Movement is free pixel-by-pixel, so wall collision is done as: 
# build one list of wall line segments from the maze grid once at session start, then each tick, try moving each circular entity (player/ghost) along requested dx/dy and reject the move if the resulting circle would cross any wall segment


import math
import random
import threading
import time

from shared.constants import (
    MAZE_TILE_WIDTH,
    MAZE_TILE_HEIGHT,
    PLAYER_SPEED,
    GHOST_SPEED,
    PLAYER_RADIUS,
    GHOST_RADIUS,
    CATCH_DISTANCE,
    GAME_TICK_RATE,
)
from shared import protocol
from maze import generate_maze, carve_exit, TILE_SIZE as MAZE_TILE_SIZE, MAZE_PIXEL_WIDTH, MAZE_PIXEL_HEIGHT


def _build_wall_segments(grid, tile_size):
    """
    Converts the maze grid (cells with open/closed wall flags) into a
    flat list of ((x1, y1), (x2, y2)) line segments for every CLOSED
    wall. These are in maze-local pixel coordinates (origin at the
    maze's top-left corner, before any centering offset is applied).
    """
    segments = []
    rows = len(grid)
    cols = len(grid[0])

    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            px = x * tile_size
            py = y * tile_size

            if not cell["N"]:
                segments.append(((px, py), (px + tile_size, py)))
            if not cell["S"]:
                segments.append(((px, py + tile_size), (px + tile_size, py + tile_size)))
            if not cell["W"]:
                segments.append(((px, py), (px, py + tile_size)))
            if not cell["E"]:
                segments.append(((px + tile_size, py), (px + tile_size, py + tile_size)))

    return segments


def _point_segment_distance(px, py, x1, y1, x2, y2):
    """Shortest distance from point (px,py) to segment (x1,y1)-(x2,y2)."""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - x1, py - y1)

    t = ((px - x1) * dx + (py - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    return math.hypot(px - closest_x, py - closest_y)


class Entity:
    """Shared position/movement state for both players and ghosts."""

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius


class PlayerEntity(Entity):
    def __init__(self, player_id, role, x, y, radius):
        super().__init__(x, y, radius)
        self.player_id = player_id
        self.role = role  # spiritualist/explorer
        self.alive = True
        self.escaped = False
        self.input_dx = 0.0
        self.input_dy = 0.0
        self.last_input_time = time.time()


class GhostEntity(Entity):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)


class GameSession:
    """
    One running maze game for one lobby. Created by the server when
    the host starts the game; destroyed (or reset) when the round
    ends and the lobby returns to its waiting-room state.
    """

    def __init__(self, lobby, broadcast_fn):
        """
        lobby: the server.state.Lobby this session belongs to (used for
               player list, options, and spiritualist_id).
        broadcast_fn: callable(lobby_id, msg_type, data) -> None, used
               to push messages out to every connected player in this
               lobby without GameSession needing to know about sockets.
        """
        self.lobby = lobby
        self.broadcast = broadcast_fn
        self.lock = threading.RLock()
        self.running = False
        self._thread = None
        self._finished = False

        self.grid, self.start_cell, self.exit_cell = generate_maze(MAZE_TILE_WIDTH, MAZE_TILE_HEIGHT)
        
        
        sx, sy = self.start_cell
        self.grid[sy][sx]["W"] = True

        self.exit_side = "E"
        carve_exit(self.grid, self.exit_cell, side=self.exit_side)
        self.tile_size = MAZE_TILE_SIZE

        # spawn area
        self.spawn_cols = 3
        self.spawn_rows = 3

        self.spawn_x1 = 0
        self.spawn_y1 = 0

        self.spawn_x2 = self.spawn_cols * self.tile_size
        self.spawn_y2 = self.spawn_rows * self.tile_size

        self.wall_segments = _build_wall_segments(self.grid, self.tile_size)

        # Exit "goal" zone: a small area just past the carved exit wall,
        # in maze-local pixel coordinates. Reaching it counts as escaping.
        ex_col, ex_row = self.exit_cell
        self.exit_zone_center = (
            ex_col * self.tile_size + self.tile_size + 6,
            ex_row * self.tile_size + self.tile_size / 2,
        )
        self.exit_zone_radius = self.tile_size * 0.6

        self.players = {}  # player_id -> PlayerEntity
        self.ghosts = []    # list of GhostEntity

        self._spawn_players()
        self._spawn_ghosts()

    def in_spawn_area(self, x, y):
        return (
            self.spawn_x1 <= x <= self.spawn_x2 and
            self.spawn_y1 <= y <= self.spawn_y2
        )


    def _spawn_players(self):
        start_col, start_row = self.start_cell

        # create purple spawn area
        for y in range(3):
            for x in range(3):
                self.grid[y][x]["N"] = True
                self.grid[y][x]["S"] = True
                self.grid[y][x]["E"] = True
                self.grid[y][x]["W"] = True
        # rebuild collision geometry
        self.wall_segments = _build_wall_segments(
            self.grid,
            self.tile_size
        )
        # base_x = start_col * self.tile_size + self.tile_size / 2
        # base_y = start_row * self.tile_size + self.tile_size / 2

        base_x = self.tile_size * 1.5
        base_y = self.tile_size * 1.5
        
        # base_x = -self.tile_size * 0.75
        # base_y = start_row * self.tile_size + self.tile_size / 2

        spiritualist_id = self.lobby.spiritualist_id
        for i, (player_id, player) in enumerate(self.lobby.players.items()):
            role = "spiritualist" if player_id == spiritualist_id else "explorer"
            offset_angle = (2 * math.pi / max(1, len(self.lobby.players))) * i
            jitter = self.tile_size * 0.25
            x = base_x + math.cos(offset_angle) * jitter
            y = base_y + math.sin(offset_angle) * jitter
            self.players[player_id] = PlayerEntity(player_id, role, x, y, PLAYER_RADIUS)

    def _spawn_ghosts(self):
        cols, rows = MAZE_TILE_WIDTH, MAZE_TILE_HEIGHT
        num_ghosts = self.lobby.options.num_ghosts
        for i in range(num_ghosts):
            gx_tile = random.randint(cols // 2, cols - 1)
            gy_tile = random.randint(rows // 2, rows - 1)
            x = gx_tile * self.tile_size + self.tile_size / 2
            y = gy_tile * self.tile_size + self.tile_size / 2
            self.ghosts.append(GhostEntity(x, y, GHOST_RADIUS))

    def mark_player_disconnected(self, player_id):
        """Kill the player entity so a mid-game disconnect doesn't
        freeze win/lose detection waiting for input from a gone client."""
        with self.lock:
            player = self.players.get(player_id)
            if player:
                player.alive = False
                player.input_dx = 0.0
                player.input_dy = 0.0

    def set_player_input(self, player_id, dx, dy):
        with self.lock:
            player = self.players.get(player_id)
            if not player or not player.alive:
                return
            magnitude = math.hypot(dx, dy)
            if magnitude > 1.0:
                dx, dy = dx / magnitude, dy / magnitude
            player.input_dx = dx
            player.input_dy = dy
            player.last_input_time = time.time()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        tick_dt = 1.0 / GAME_TICK_RATE
        last_time = time.time()

        while self.running:
            now = time.time()
            dt = now - last_time
            last_time = now

            with self.lock:
                self._tick(dt)
                state_payload = self._build_state_payload()

            self.broadcast(self.lobby.lobby_id, protocol.GAME_STATE, state_payload)

            elapsed = time.time() - now
            time.sleep(max(0.0, tick_dt - elapsed))

    def _tick(self, dt):
        if self._finished:
            return

        self._move_players(dt)
        self._move_ghosts(dt)
        self._check_catches()
        self._check_escapes()
        self._check_win_lose()

    def _move_players(self, dt):
        for player in self.players.values():
            if not player.alive or player.escaped:
                continue
            self._try_move(player, player.input_dx * PLAYER_SPEED * dt, player.input_dy * PLAYER_SPEED * dt)

    def _move_ghosts(self, dt):
        # living_explorers = [
        #     p for p in self.players.values()
        #     if p.alive and not p.escaped and p.role == "explorer"
        # ]
        living_players = [
            p for p in self.players.values()
            if p.alive and not p.escaped
        ]
        for ghost in self.ghosts:
            if not living_players:
                continue
            target = min(living_players, key=lambda p: math.hypot(p.x - ghost.x, p.y - ghost.y))
            dx, dy = target.x - ghost.x, target.y - ghost.y
            distance = math.hypot(dx, dy)
            if distance < 1e-6:
                continue
            dx, dy = dx / distance, dy / distance
            self._try_move(ghost, dx * GHOST_SPEED * dt, dy * GHOST_SPEED * dt)

    def _try_move(self, entity, move_x, move_y):
        """Attempts to move entity by (move_x, move_y), axis-separated so
        sliding along a wall feels natural instead of fully stopping on
        any contact (classic platformer-style collision resolution)."""
        if move_x != 0:
            new_x = entity.x + move_x
            if not self._collides(new_x, entity.y, entity.radius):
                entity.x = new_x
        if move_y != 0:
            new_y = entity.y + move_y
            if not self._collides(entity.x, new_y, entity.radius):
                entity.y = new_y

    def _collides(self, x, y, radius):
        if self.in_spawn_area(x, y):
            return False
        
        if not (0 <= x <= MAZE_PIXEL_WIDTH and 0 <= y <= MAZE_PIXEL_HEIGHT):
            if math.hypot(x - self.exit_zone_center[0], y - self.exit_zone_center[1]) <= self.exit_zone_radius:
                return False
            return True

        for (x1, y1), (x2, y2) in self.wall_segments:
            if _point_segment_distance(x, y, x1, y1, x2, y2) < radius:
                return True
        return False

    def _respawn_ghost(self, ghost):
        cols, rows = MAZE_TILE_WIDTH, MAZE_TILE_HEIGHT

        while True:
            gx_tile = random.randint(cols // 2, cols - 1)
            gy_tile = random.randint(rows // 2, rows - 1)

            x = gx_tile * self.tile_size + self.tile_size / 2
            y = gy_tile * self.tile_size + self.tile_size / 2

            if not self._collides(x, y, ghost.radius):
                ghost.x = x
                ghost.y = y
                return

    def _check_catches(self):
        for player in self.players.values():
            if not player.alive or player.escaped:
                continue
            for ghost in self.ghosts:
                distance = math.hypot(player.x - ghost.x, player.y - ghost.y)
                if distance <= CATCH_DISTANCE:
                    player.alive = False
                    self.broadcast(self.lobby.lobby_id, protocol.PLAYER_DIED, {"player_id": player.player_id})
                    self._respawn_ghost(ghost) # experiment ke sekian
                    break

    def _check_escapes(self):
        for player in self.players.values():
            if not player.alive or player.escaped:
                continue
            distance = math.hypot(
                player.x - self.exit_zone_center[0], player.y - self.exit_zone_center[1]
            )
            if distance <= self.exit_zone_radius:
                player.escaped = True
                # experiment ke sekian 2
                self.broadcast(
                    self.lobby.lobby_id,
                    protocol.PLAYER_ESCAPED,
                    {
                        "player_id": player.player_id
                    }
                )


    # def _check_win_lose(self):
    #     active_players = [
    #         p for p in self.players.values()
    #         if p.alive and not p.escaped
    #     ]

    #     # Someone is still playing
    #     if active_players:
    #         return

    #     escaped_players = [
    #         p for p in self.players.values()
    #         if p.escaped
    #     ]

    #     # No active players remain.
    #     # If at least one escaped, the last active player escaped.
    #     if escaped_players:
    #         self._end_game("win")
    #     else:
    #         self._end_game("lose")

    def _check_win_lose(self):
        active_players = [
            p for p in self.players.values()
            if p.alive and not p.escaped
        ]

        if active_players:
            return

        escaped_players = [
            p for p in self.players.values()
            if p.escaped
        ]

        # If at least one escaped, the last active player escaped
        if escaped_players:
            self._end_game("win")
        else:
            self._end_game("lose")

    # def _end_game(self, result):
    #     self._finished = True
    #     self.broadcast(self.lobby.lobby_id, protocol.GAME_OVER, {"result": result})
    #     self.stop()

    def _end_game(self, result):
        self._finished = True

        total_players = len(self.players)

        escaped_players = sum(
            1 for p in self.players.values()
            if p.escaped
        )

        failed_players = total_players - escaped_players

        self.broadcast(
            self.lobby.lobby_id,
            protocol.GAME_OVER,
            {
                "result": result,
                "escaped_players": escaped_players,
                "failed_players": failed_players,
                "total_players": total_players,
            }
        )
        self.stop()

    def _build_state_payload(self):
        return {
            "players": [
                {
                    "player_id": p.player_id,
                    "x": p.x,
                    "y": p.y,
                    "alive": p.alive,
                    "escaped": p.escaped,
                    "role": p.role,
                }
                for p in self.players.values()
            ],
            "ghosts": [{"x": g.x, "y": g.y} for g in self.ghosts],
        }

    def build_starting_payload(self, player_id):
        """Per-recipient GAME_STARTING payload: includes the maze layout
        (same for everyone) and that recipient's own role."""
        player = self.players.get(player_id)
        return {
            "lobby_id": self.lobby.lobby_id,
            "maze": {
                "grid": self.grid,
                "tile_size": self.tile_size,
                "cols": MAZE_TILE_WIDTH,
                "rows": MAZE_TILE_HEIGHT,
                "exit_cell": list(self.exit_cell),
                "exit_side": self.exit_side,
            },
            "your_role": player.role if player else "explorer",
        }
