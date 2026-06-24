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

# test

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
from server.chat import NetworkChat  # NEW: Import your chat blueprint

pygame.init()
pygame.font.init() # NEW: Initialize the font system

window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Psychic Maze")

clock = pygame.time.Clock()

# --- CHAT SYSTEM SETUP ---
CHAT_WIDTH = 256
chat_font = pygame.font.SysFont(None, 24)
chat_messages = []  # List to store history of strings
current_input = ""  # The string currently being typed

# Initialize the network connection
# IMPORTANT: Change this to the Host's LAN IP when testing across devices!
chat_client = NetworkChat('127.0.0.1', 5555) 
chat_client.connect()
# -------------------------

# --- ASSET LOADING ---
green_explorer = pygame.image.load("assets/sprites/explorer/green_explorer/idle_1.png").convert_alpha()
red_explorer = pygame.image.load("assets/sprites/explorer/red_explorer/idle_1.png").convert_alpha()
orange_explorer = pygame.image.load("assets/sprites/explorer/orange_explorer/idle_1.png").convert_alpha()
blue_explorer = pygame.image.load("assets/sprites/explorer/blue_explorer/idle_1.png").convert_alpha()
spiritualist = pygame.image.load("assets/sprites/spiritualist/idle_1.png")
ghost = pygame.image.load("assets/sprites/ghost/idle_1.png")
exitTile = pygame.image.load("assets/tiles/exit.png")
floor = pygame.image.load("assets/tiles/black_floor.png")
wall = pygame.image.load("assets/tiles/purple_wall.png")
# ---------------------

while True:
    # 1. NETWORK CHECK: Pull messages silently in the background
    incoming = chat_client.get_new_messages()
    for msg in incoming:
        chat_messages.append(msg)
        # Keep only the last 15 messages so it doesn't flow off the screen
        if len(chat_messages) > 15:
            chat_messages.pop(0)

    # 2. EVENT HANDLING
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            chat_client.running = False # Tell the background thread to stop
            pygame.quit()
            exit()
            
        # Handle Typing
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if current_input.strip() != "":
                    # Send message and clear input box
                    chat_client.send_message(current_input)
                    current_input = ""
            elif event.key == pygame.K_BACKSPACE:
                # Delete last character
                current_input = current_input[:-1]
            else:
                # Add typed character to input string (if it's a standard key)
                current_input += event.unicode
    
    # 3. DRAWING
    window.fill((0,0,0))
    
    # --- DRAW CHAT ZONE (First 256 pixels) ---
    # Draw a dark gray background for the chat to separate it from the maze
    pygame.draw.rect(window, (30, 30, 30), (0, 0, CHAT_WIDTH, GAME_HEIGHT))
    
    # Draw Chat History (rendering from bottom to top)
    y_offset = GAME_HEIGHT - 60
    for msg in reversed(chat_messages):
        text_surface = chat_font.render(msg, True, (255, 255, 255))
        window.blit(text_surface, (10, y_offset))
        y_offset -= 25 # Move up for the next line
        if y_offset < 10: 
            break # Stop drawing if we reach the top of the window
            
    # Draw Input Box Background
    pygame.draw.rect(window, (10, 10, 10), (5, GAME_HEIGHT - 40, CHAT_WIDTH - 10, 30))
    
    # Draw Current Typing Text
    input_surface = chat_font.render(current_input, True, (255, 255, 0)) # Yellow text for typing
    window.blit(input_surface, (10, GAME_HEIGHT - 35))
    # ----------------------------------------

    # --- DRAW MAZE ASSETS ---
    # Since your assets are currently hardcoded starting at x=256, 
    # they naturally sit right next to the new chat zone!
    window.blit(green_explorer, (256,160))
    window.blit(red_explorer, (288,160))
    window.blit(orange_explorer, (320,160))
    window.blit(blue_explorer, (352,160))
    window.blit(spiritualist, (384,160))
    window.blit(ghost, (416,160))
    window.blit(exitTile, (448,160))
    window.blit(floor, (480, 160))
    window.blit(wall, (512,160))

    pygame.display.flip()
    clock.tick(FPS)