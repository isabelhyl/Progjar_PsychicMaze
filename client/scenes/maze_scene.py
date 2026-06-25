# The main gameplay screen. Entered when the client receives GAME_STARTING.

# features:

# ROLE-BASED RENDERING
#   Explorer: sees maze walls + all explorer positions, NOT ghosts
#   Spiritualist: sees all explorer positions + ghost positions, NOT walls
#   Spectator: sees everything (walls, explorers, ghosts) but cannot move; sprite is removed from the game

# ANIMATION
# Each moving character alternates between idle_1 and idle_2 sprites at
# ANIMATION_FRAME_SECONDS intervals. "Moving" means the entity actually
# changed position this frame (players) or is always considered moving
# (ghosts/AI). Standing still shows idle_1 frozen.

# WASD MOVEMENT
# Each frame the scene reads currently-held WASD keys, computes a unit
# direction vector, and sends a MOVE message to the server. The server
# validates movement against maze walls and broadcasts authoritative
# positions back via GAME_STATE.

# POPUPS FOR WIN/LOSE SCENARIOS
# Player escapes = 'YOU'VE ESCAPED, BUT WILL YOUR FRIENDS?'
# Player gets caught by ghost = 'YOU'VE FALLED INTO MY TRAP. YOUR FRIENDS WILL JOIN ME SOON.'
# All players win = 'HOW DARE YOU ESCAPE ME?'
# Some players win and some lose = '"{failed players} out of {total players} have fallen into my trap. For those who escaped, soon I will hunt you down too.'
# All players lose = ' "As usual, curiosity kills the cat. You've fallen into my trap, and now you're gonna pay for it.'



import os
import math
import pygame

from shared import protocol
from shared.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    MAZE_TILE_WIDTH, MAZE_TILE_HEIGHT,
    SPRITE_SIZE, ANIMATION_FRAME_SECONDS,
)
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

# explorer colour variants assigned in join order
EXPLORER_VARIANTS = ["blue_explorer", "red_explorer", "green_explorer", "orange_explorer"]

COLOR_BG        = (20, 20, 28)
COLOR_WALL      = (235, 235, 245)
COLOR_PATH      = (40, 40, 55)
COLOR_EXIT      = (90, 220, 130)
COLOR_TEXT      = (235, 235, 245)
COLOR_MUTED     = (150, 150, 165)
COLOR_OVERLAY   = (0, 0, 0, 180)   

# popup messages
MSG_YOU_DIED = (
    "YOU'VE FALLEN INTO MY TRAP.\n"
    "YOUR FRIENDS WILL JOIN ME SOON."
)

MSG_YOU_ESCAPED = (
    "YOU'VE ESCAPED,\n"
    "BUT WILL YOUR FRIENDS?"
)

MSG_GAME_LOSE = (
    "As usual, curiosity kills the cat.\n"
    "You've fallen into my trap,\n"
    "and now you're gonna pay for it."
)

MSG_GAME_WIN = (
    "HOW DARE YOU AND YOUR FRIENDS\n"
    "ESCAPE ME."
)

MSG_DISMISS     = "Press any key or click to continue"

SPAWN_ROOM_SIZE = 3  


def _load_frames(path):
    """Load [idle_1, idle_2] from a sprites subdirectory. Returns None
    if the directory or files don't exist (graceful fallback)."""
    try:
        f1 = pygame.image.load(os.path.join(path, "idle_1.png")).convert_alpha()
        f2 = pygame.image.load(os.path.join(path, "idle_2.png")).convert_alpha()
        return [f1, f2]
    except (FileNotFoundError, pygame.error):
        return None


class SpriteSheet:
    """Holds the two animation frames for one character type and tracks
    which frame is currently showing."""

    def __init__(self, frames):
        self.frames = frames  
        self._timer = 0.0
        self._frame_idx = 0
        self.moving = False

    def update(self, dt, is_moving):
        self.moving = is_moving
        if is_moving:
            self._timer += dt
            if self._timer >= ANIMATION_FRAME_SECONDS:
                self._timer = 0.0
                self._frame_idx = 1 - self._frame_idx  # toggle 0 <-> 1
        else:
            self._timer = 0.0
            self._frame_idx = 0

    def current_frame(self):
        if self.frames:
            return self.frames[self._frame_idx]
        return None


class PlayerState:
    """Client-side mirror of one player's server-broadcast state."""

    def __init__(self, player_id, name, role, variant_path):
        self.player_id = player_id
        self.name = name
        self.role = role           # "explorer" or "spiritualist"
        self.x = 0.0
        self.y = 0.0
        self.alive = True
        self.escaped = False
        self.prev_x = 0.0
        self.prev_y = 0.0
        self.sheet = SpriteSheet(_load_frames(variant_path))

    def update_anim(self, dt):
        moved = math.hypot(self.x - self.prev_x, self.y - self.prev_y) > 0.5
        self.sheet.update(dt, moved)
        self.prev_x, self.prev_y = self.x, self.y


class GhostState:
    """Client-side mirror of one ghost."""

    def __init__(self, sheet):
        self.x = 0.0
        self.y = 0.0
        self.prev_x = 0.0
        self.prev_y = 0.0
        self.sheet = sheet

    def update_anim(self, dt):
        moved = math.hypot(self.x - self.prev_x, self.y - self.prev_y) > 0.5
        self.sheet.update(dt, moved)
        self.prev_x, self.prev_y = self.x, self.y


class MazeScene(Scene):

    def __init__(self, game):
        super().__init__(game)
        # self.game = game

        self.exit_sprite = pygame.image.load(
            os.path.join("assets", "tiles", "exit.png")
        ).convert_alpha()

        self.purple_tile = pygame.image.load(
            os.path.join("assets", "tiles", "purple_wall.png")
        ).convert_alpha()

        self.black_tile = pygame.image.load(
            os.path.join("assets", "tiles", "black_floor.png")
        ).convert_alpha()



    def on_enter(self, maze_data=None, your_role="explorer", **kwargs):
        self.your_role = your_role        
        self.is_spectator = False # set true when we die
        self.my_player_id = self.app.session.player_id


        self.grid = maze_data["grid"] if maze_data else []
        self.tile_size = maze_data["tile_size"] if maze_data else 30
        self.exit_cell = tuple(maze_data["exit_cell"]) if maze_data else (15, 15)
        self.exit_side = maze_data.get("exit_side", "E") if maze_data else "E"

      
        pixel_w = self.tile_size * MAZE_TILE_WIDTH
        pixel_h = self.tile_size * MAZE_TILE_HEIGHT
        # self.offset_x = (WINDOW_WIDTH - pixel_w) // 2

        GAME_AREA_WIDTH = WINDOW_WIDTH * 3 // 4
        self.offset_x = (
            GAME_AREA_WIDTH - pixel_w
        ) // 2
        self.offset_y = (WINDOW_HEIGHT - pixel_h) // 2

      
        EXIT_MARGIN = self.tile_size

        self._maze_surf = self._bake_maze_surface(
            pixel_w + EXIT_MARGIN,
            pixel_h
        )

     

        self.players = {}   
        self.ghosts  = []  

        # assign explorer colour variants in the order players appear in the lobby state 
        lobby = self.app.session.lobby_state or {}
        self._player_name_map = {p["player_id"]: p["name"]
                                  for p in lobby.get("players", [])}
        self._explorer_index = 0

        base = os.path.join("assets", "sprites")
        self._ghost_frames = _load_frames(os.path.join(base, "ghost"))
        self._spirit_frames = _load_frames(os.path.join(base, "spiritualist"))

        self._keys_held = {pygame.K_w: False, pygame.K_a: False,
                           pygame.K_s: False, pygame.K_d: False}
        self._move_send_timer = 0.0
        self._MOVE_INTERVAL = 1.0 / 30 

        self.popup = None 

     
        self._obituaries = []  
        self._OBT_DURATION = 3.0

        self._game_over = False

        # chat feature
        self.chat_open = False
        self.chat_button = Button(
            (
                WINDOW_WIDTH - 120,
                20,
                100,
                40
            ),
            "Chat",
            self.app.fonts["small"]
        )

        CHAT_WIDTH = WINDOW_WIDTH // 4
        self.chat_panel = ChatPanel(
            (
                WINDOW_WIDTH - CHAT_WIDTH,
                0,
                CHAT_WIDTH,
                WINDOW_HEIGHT
            ),
            self.app.fonts["chat"],
            self.app.session.chat_messages
        )
  
    def _bake_maze_surface(self, w, h):
        surf = pygame.Surface((w, h))

        black = pygame.transform.scale(
            self.black_tile,
            (self.tile_size, self.tile_size)
        )

        purple = pygame.transform.scale(
            self.purple_tile,
            (self.tile_size, self.tile_size)
        )

        # fill entire maze with black floor texture
        for row in range(MAZE_TILE_HEIGHT):
            for col in range(MAZE_TILE_WIDTH):
                surf.blit(
                    black,
                    (
                        col * self.tile_size,
                        row * self.tile_size
                    )
                )

        # paint spawn room purple
        for row in range(SPAWN_ROOM_SIZE):
            for col in range(SPAWN_ROOM_SIZE):
                surf.blit(
                    purple,
                    (
                        col * self.tile_size,
                        row * self.tile_size
                    )
                )

        wall_w = 2
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                px = x * self.tile_size
                py = y * self.tile_size
                ts = self.tile_size
                if not cell["N"]:
                    pygame.draw.line(surf, COLOR_WALL, (px, py), (px + ts, py), wall_w)
                if not cell["S"]:
                    pygame.draw.line(surf, COLOR_WALL, (px, py + ts), (px + ts, py + ts), wall_w)
                if not cell["W"]:
                    pygame.draw.line(surf, COLOR_WALL, (px, py), (px, py + ts), wall_w)
                if not cell["E"]:
                    pygame.draw.line(surf, COLOR_WALL, (px + ts, py), (px + ts, py + ts), wall_w)
        
        # ex_col, ex_row = self.exit_cell
        # epx = ex_col * self.tile_size
        # epy = ex_row * self.tile_size
        # ts = self.tile_size
        # mk = max(4, ts // 4)
        # pad = (ts - ts // 2) // 2
        # if self.exit_side == "E":
        #     rect = (epx + ts, epy + pad, mk, ts // 2)
        # elif self.exit_side == "W":
        #     rect = (epx - mk, epy + pad, mk, ts // 2)
        # elif self.exit_side == "S":
        #     rect = (epx + pad, epy + ts, ts // 2, mk)
        # else:
        #     rect = (epx + pad, epy - mk, ts // 2, mk)
        # pygame.draw.rect(surf, COLOR_EXIT, rect)

        ex_col, ex_row = self.exit_cell

        epx = ex_col * self.tile_size
        epy = ex_row * self.tile_size
        ts = self.tile_size

        door = pygame.transform.scale(
            self.exit_sprite,
            (ts, ts)
        )

        # surf.blit(
        #     door,
        #     (epx + ts - ts//2, epy)
        # )

        # experiment
        # surf.blit(
        #     door,
        #     (epx + ts//4, epy)
        # )
        surf.blit(
            door,
            (epx + ts - 5, epy)
        )


        return surf


    def handle_event(self, event):
        if self.chat_button.handle_event(event):
            self.chat_open = not self.chat_open

        if self.chat_open:
            action, payload = self.chat_panel.handle_event(event)
            if action == "close":
                self.chat_open = False
            elif action == "send":
                self.app.network.send(
                    protocol.CHAT_MESSAGE,
                    {
                        "text": payload
                    }
                )

        # Popup: any key / click dismisses it
        if self.popup:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                dismiss_fn = self.popup.get("on_dismiss")
                self.popup = None
                if dismiss_fn:
                    dismiss_fn()
            return

        if event.type == pygame.KEYDOWN:
            if event.key in self._keys_held:
                self._keys_held[event.key] = True
        if event.type == pygame.KEYUP:
            if event.key in self._keys_held:
                self._keys_held[event.key] = False

    def handle_message(self, msg_type, data):
        if msg_type == protocol.CHAT_MESSAGE:
            msg = f"{data['sender']}: {data['text']}"
            self.app.session.chat_messages.append(msg)
            self.chat_panel.scroll_to_bottom()
            return
        
        elif msg_type == protocol.CHAT_HISTORY:
            self.app.session.chat_messages.clear()
            for msg in data.get("messages", []):

                self.app.session.chat_messages.append(
                    f"{msg['sender']}: {msg['text']}"
                )
            self.chat_panel.scroll_to_bottom()

        elif msg_type == protocol.GAME_STATE:
            self._apply_game_state(data)

        elif msg_type == protocol.PLAYER_DIED:
            dead_id = data.get("player_id")
            if dead_id == self.my_player_id:
                self._show_popup(
                    MSG_YOU_DIED.split("\n") + ["", MSG_DISMISS],
                    on_dismiss=None
                )
                self.is_spectator = True
                self.your_role = "spectator"
            else:
                name = self._player_name_map.get(dead_id, dead_id)
                self._obituaries.append([f"{name} has been caught!", self._OBT_DURATION])
            p = self.players.get(dead_id)
            if p:
                p.alive = False

        elif msg_type == protocol.PLAYER_ESCAPED:
            escaped_id = data.get("player_id")

            if escaped_id == self.my_player_id:
                self._show_popup(
                    MSG_YOU_ESCAPED.split("\n") + ["", MSG_DISMISS],
                    on_dismiss=None
                )

                self.is_spectator = True
                self.your_role = "spectator"

            else:
                name = self._player_name_map.get(
                    escaped_id,
                    escaped_id
                )

                self._obituaries.append(
                    [f"{name} escaped!", self._OBT_DURATION]
                )


        elif msg_type == protocol.GAME_OVER:
            escaped = data.get("escaped_players", 0)
            failed = data.get("failed_players", 0)
            total = data.get("total_players", 0)

            self._game_over = True

            if escaped == 0:

                lines = MSG_GAME_LOSE.split("\n")

            elif escaped == total:

                lines = MSG_GAME_WIN.split("\n")

            else:

                lines = [
                    f"{failed} out of {total} have fallen into my trap.",
                    "",
                    "For those who escaped,",
                    "soon I will hunt you down too."
                ]

            lines += ["", MSG_DISMISS]

            self._show_popup(
                lines,
                on_dismiss=self._return_to_lobby
            )

        elif msg_type == protocol.LOBBY_STATE:
            # Received after EXIT_GAME_TO_LOBBY completes
            self.app.session.lobby_state = data
            self.app.set_scene("lobby")

    def _show_popup(self, lines, on_dismiss=None):
        self.popup = {"lines": lines, "on_dismiss": on_dismiss}

    def _return_to_lobby(self):
        self.app.network.send(protocol.EXIT_GAME_TO_LOBBY)

    def _apply_game_state(self, data):
        base = os.path.join("assets", "sprites")

        for pd in data.get("players", []):
            pid = pd["player_id"]
            if pid not in self.players:
                role = pd["role"]
                if role == "spiritualist":
                    variant_path = os.path.join(base, "spiritualist")
                else:
                    variant = EXPLORER_VARIANTS[self._explorer_index % len(EXPLORER_VARIANTS)]
                    variant_path = os.path.join(base, "explorer", variant)
                    self._explorer_index += 1
                name = self._player_name_map.get(pid, pid)
                self.players[pid] = PlayerState(pid, name, role, variant_path)

            p = self.players[pid]
            p.x      = pd["x"]
            p.y      = pd["y"]
            p.alive  = pd["alive"]
            p.escaped = pd.get("escaped", False)

        # Sync ghost list length and positions
        ghosts_data = data.get("ghosts", [])
        while len(self.ghosts) < len(ghosts_data):
            self.ghosts.append(GhostState(SpriteSheet(_load_frames(os.path.join(base, "ghost")))))
        for i, gd in enumerate(ghosts_data):
            self.ghosts[i].x = gd["x"]
            self.ghosts[i].y = gd["y"]


    def update(self, dt):
        # Animate entities
        for p in self.players.values():
            p.update_anim(dt)
        for g in self.ghosts:
            g.update_anim(dt)

        self._obituaries = [[txt, t - dt] for txt, t in self._obituaries if t - dt > 0]

        # send movement input
        if not self.is_spectator and not self._game_over and not self.popup:
            self._move_send_timer += dt
            if self._move_send_timer >= self._MOVE_INTERVAL:
                self._move_send_timer = 0.0
                self._send_move()

    def _send_move(self):
        dx = (1 if self._keys_held[pygame.K_d] else 0) - (1 if self._keys_held[pygame.K_a] else 0)
        dy = (1 if self._keys_held[pygame.K_s] else 0) - (1 if self._keys_held[pygame.K_w] else 0)
        if dx != 0 or dy != 0:
            # Normalise diagonal to prevent faster diagonal movement
            length = math.hypot(dx, dy)
            self.app.network.send(protocol.MOVE, {"dx": dx / length, "dy": dy / length})
        else:
            # Send a zero vector so server knows we've stopped
            self.app.network.send(protocol.MOVE, {"dx": 0.0, "dy": 0.0})


    def draw(self, surface):
        surface.fill(COLOR_BG)
        role = self.your_role 

        if role in ("explorer", "spectator"):
            surface.blit(self._maze_surf, (self.offset_x, self.offset_y))

        # players logic
        for p in self.players.values():
            # skip escaped players (they're out of the maze)
            if p.escaped:
                continue
            # skip dead players whose sprites should no longer appear
            if not p.alive and p.player_id != self.my_player_id:
                continue
            # don't draw the local player if they're dead (they spectate now)
            if p.player_id == self.my_player_id and self.is_spectator:
                continue

            self._draw_entity(surface, p.sheet, p.x, p.y)
            self._draw_name_tag(surface, p.name, p.x, p.y)

        # draw chat panel
        self.chat_button.draw(surface)
        if self.chat_open:
            self.chat_panel.draw(surface)

        
        if role in ("spiritualist", "spectator"):
            for g in self.ghosts:
                self._draw_entity(surface, g.sheet, g.x, g.y)

       
        self._draw_obituaries(surface)

     
        self._draw_hud(surface, role)

        # pop up overlay
        if self.popup:
            self._draw_popup(surface)

    def _draw_entity(self, surface, sheet, world_x, world_y):
        frame = sheet.current_frame()
        sx = self.offset_x + world_x - SPRITE_SIZE // 2
        sy = self.offset_y + world_y - SPRITE_SIZE // 2
        if frame:
            surface.blit(frame, (sx, sy))
        else:
            # Fallback: coloured dot if sprite didn't load
            pygame.draw.circle(surface, COLOR_TEXT, (int(self.offset_x + world_x), int(self.offset_y + world_y)), 8)

    def _draw_name_tag(self, surface, name, world_x, world_y):
        font = self.app.fonts["small"]
        tag = font.render(name, True, COLOR_TEXT)
        sx = self.offset_x + world_x - tag.get_width() // 2
        sy = self.offset_y + world_y - SPRITE_SIZE // 2 - 16
        surface.blit(tag, (sx, sy))

    def _draw_hud(self, surface, role):
        font = self.app.fonts["small"]
        if role == "spectator":
            label = "SPECTATING"
            color = COLOR_MUTED
        elif role == "spiritualist":
            label = "SPIRITUALIST – you see ghosts, not walls"
            color = (180, 130, 240)
        else:
            label = "EXPLORER – find the exit!"
            color = (90, 200, 130)
        surf = font.render(label, True, color)
        surface.blit(surf, (8, 8))

    def _draw_obituaries(self, surface):
        font = self.app.fonts["small"]
        y = WINDOW_HEIGHT - 30
        for text, _ in reversed(self._obituaries):
            s = font.render(text, True, (220, 100, 100))
            surface.blit(s, (WINDOW_WIDTH // 2 - s.get_width() // 2, y))
            y -= 22

    def _draw_popup(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        font_large = self.app.fonts["large"]
        font_small = self.app.fonts["small"]
        lines = self.popup["lines"]
        line_h = font_large.get_linesize()
        total_h = line_h * len(lines)
        y = WINDOW_HEIGHT // 2 - total_h // 2

        for line in lines:
            if not line:
                y += line_h // 2
                continue
         
            if line == MSG_DISMISS:
                s = font_small.render(line, True, COLOR_MUTED)
            else:
                s = font_large.render(line, True, COLOR_TEXT)
            surface.blit(s, (WINDOW_WIDTH // 2 - s.get_width() // 2, y))
            y += line_h
