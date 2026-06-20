# Maze window is a square (16 tiles wide x 16 tiles high)
# Chat window is a rectangle (8 tiles wide x 16 tiles high)
# Each tile is 32px x 32px
# Soooo uhhhh, that's 24 tiles wide x 16 tiles high, meaning
# 768 pixels wide and 512 pixels high

# https://www.youtube.com/watch?v=vY_9LKxQL_0
# don't forget pip install pygame
# and uh, run the code in Powershell (actually idk how Isabel does it directly from VSCode)

import pygame
from sys import exit

WINDOW_WIDTH = 768
WINDOW_HEIGHT = 512
TILE_SIZE = 32

CHAT_TILE_WIDTH = 8
CHAT_TILE_HEIGHT = 16
MAZE_TILE_WIDTH = 16
MAZE_TILE_HEIGHT = 16

window = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
pygame.display.set_caption("Psychic Maze")
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
    pygame.display.update()
    clock.tick(60) # 60FPS