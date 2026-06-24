# Just to prevent declaring numbers in one file and then having to get that number in another file
# Or uh magic numbers as they call it
WINDOW_WIDTH = 768
WINDOW_HEIGHT = 512
TILE_SIZE = 32

CHAT_TILE_WIDTH = 8
CHAT_TILE_HEIGHT = 16
MAZE_TILE_WIDTH = 16
MAZE_TILE_HEIGHT = 16

FPS = 60

# Networking
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5555
RECV_BUFFER_SIZE = 4096

# Lobby / game option defaults & limits
MIN_PLAYERS = 2
MAX_PLAYERS = 8
DEFAULT_NUM_PLAYERS = 4
MIN_GHOSTS = 1
MAX_GHOSTS = 4
DEFAULT_NUM_GHOSTS = 1

# Gameplay (maze.py)
PLAYER_SPEED = 120.0       # pixels per second
GHOST_SPEED = 90.0         # pixels per second (slower than players, so skill matters)
PLAYER_RADIUS = 12         # collision radius in pixels (circle vs. wall lines)
GHOST_RADIUS = 12
CATCH_DISTANCE = 16        # ghost-explorer distance (px) counted as "touched"
SPRITE_SIZE = 32           # sprite images are 32x32

GAME_TICK_RATE = 30        # server simulation ticks per second
ANIMATION_FRAME_SECONDS = 0.25  # how long each idle frame shows while moving
