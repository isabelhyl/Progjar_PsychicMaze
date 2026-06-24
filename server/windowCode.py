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
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    TILE_SIZE,
    CHAT_TILE_WIDTH,
    CHAT_TILE_HEIGHT,
    MAZE_TILE_WIDTH,
    MAZE_TILE_HEIGHT,
    FPS
)

window = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
pygame.display.set_caption("Psychic Maze")
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
    pygame.display.update()
    clock.tick(FPS) # 60FPS