# Maze window is a square (16 tiles wide x 16 tiles high)
# Chat window is a rectangle (8 tiles wide x 16 tiles high)
# Each tile is 32px x 32px
# Soooo uhhhh, that's 24 tiles wide x 16 tiles high, meaning
# 768 pixels wide and 512 pixels high

# https://www.youtube.com/watch?v=vY_9LKxQL_0
# don't forget pip install pygame
# and uh, run the code in Powershell (actually idk how Isabel does it directly from VSCode)
# to run any files, make sure you're in the root directory and then
# py server.windowCode (for windowCode.py inside the server directory)
# py client.testing (for testing.py inside the client directory)
# You get the general gist of it, right?
# Also why does vsc still say "import pygame could not be resolved"
# Brah I should visit Isabel's apartment to work on this together

import pygame
from sys import exit
from shared.constants import(
    GAME_WIDTH,
    GAME_HEIGHT,
    TILE_SIZE,
    CHAT_TILE_WIDTH,
    CHAT_TILE_HEIGHT,
    MAZE_TILE_WIDTH,
    MAZE_TILE_HEIGHT,
    FPS
)

# I need to do integer scaling

pygame.init()

display_info = pygame.display.Info()

scale = max(1,min
    (
        display_info.current_w // GAME_WIDTH,
        display_info.current_h // GAME_HEIGHT
    )
)

window_width = GAME_WIDTH * scale
window_height = GAME_HEIGHT * scale

window = pygame.display.set_mode((window_width,window_height))
game_surface = pygame.Surface((GAME_WIDTH,GAME_HEIGHT))

pygame.display.set_caption("Psychic Maze")
clock = pygame.time.Clock()

green_explorer = pygame.image.load(
    "assets/sprites/explorer/green_explorer/idle_1.png"
).convert_alpha()

red_explorer = pygame.image.load(
    "assets/sprites/explorer/red_explorer/idle_1.png"
).convert_alpha()

orange_explorer = pygame.image.load(
    "assets/sprites/explorer/orange_explorer/idle_1.png"
).convert_alpha()

blue_explorer = pygame.image.load(
    "assets/sprites/explorer/blue_explorer/idle_1.png"
).convert_alpha()

spiritualist = pygame.image.load(
    "assets/sprites/spiritualist/idle_1.png"
)

ghost = pygame.image.load(
    "assets/sprites/ghost/idle_1.png"
)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
    game_surface.fill((0,0,0))
    game_surface.blit(green_explorer, (256,160))
    game_surface.blit(red_explorer, (288,160))
    game_surface.blit(orange_explorer, (320,160))
    game_surface.blit(blue_explorer, (352,160))
    game_surface.blit(spiritualist, (384,160))
    game_surface.blit(ghost, (416,160))
    
    scaled_surface = pygame.transform.scale(
        game_surface,
        (window_width,window_height)
    )
    
    window.blit(scaled_surface, (0,0))
    pygame.display.flip()
    
    clock.tick(FPS) # 60FPS