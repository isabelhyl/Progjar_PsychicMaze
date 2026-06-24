import random
import pygame
from sys import exit as sys_exit

from shared.constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MAZE_TILE_WIDTH,
    MAZE_TILE_HEIGHT,
    FPS,
)

COLOR_BG = (20, 20, 28)
COLOR_WALL = (235, 235, 245)
COLOR_PATH = (40, 40, 55)
COLOR_EXIT = (90, 220, 130)

# how much breathing room to leave around the maze so the exit marker isn't flush against the window edge
EXIT_MARGIN = 24

MAZE_AREA_SIZE = min(WINDOW_WIDTH, WINDOW_HEIGHT) - EXIT_MARGIN
TILE_SIZE = MAZE_AREA_SIZE // max(MAZE_TILE_WIDTH, MAZE_TILE_HEIGHT)

MAZE_PIXEL_WIDTH = TILE_SIZE * MAZE_TILE_WIDTH
MAZE_PIXEL_HEIGHT = TILE_SIZE * MAZE_TILE_HEIGHT


def generate_maze(cols=MAZE_TILE_WIDTH, rows=MAZE_TILE_HEIGHT):
    """
    Recursive-backtracker maze generator.
    Returns (grid, start_cell, exit_cell):
      - grid: rows x cols list of cells, each a dict of open walls
        {"N": bool, "S": bool, "E": bool, "W": bool}; True = passage open.
      - start_cell: (col, row) tuple, top-left by convention.
      - exit_cell: (col, row) tuple, bottom-right by convention.
    Grid size defaults to the tile counts from constants.py.
    """
    grid = [
        [{"N": False, "S": False, "E": False, "W": False} for _ in range(cols)]
        for _ in range(rows)
    ]
    visited = [[False] * cols for _ in range(rows)]

    def neighbors(cx, cy):
        candidates = [
            ("N", cx, cy - 1, "S"),
            ("S", cx, cy + 1, "N"),
            ("E", cx + 1, cy, "W"),
            ("W", cx - 1, cy, "E"),
        ]
        result = []
        for direction, nx, ny, opposite in candidates:
            if 0 <= nx < cols and 0 <= ny < rows and not visited[ny][nx]:
                result.append((direction, nx, ny, opposite))
        return result

    stack = [(0, 0)]
    visited[0][0] = True

    while stack:
        cx, cy = stack[-1]
        options = neighbors(cx, cy)
        if not options:
            stack.pop()
            continue

        direction, nx, ny, opposite = random.choice(options)
        grid[cy][cx][direction] = True
        grid[ny][nx][opposite] = True
        visited[ny][nx] = True
        stack.append((nx, ny))

    start_cell = (0, 0)
    exit_cell = (cols - 1, rows - 1)
    return grid, start_cell, exit_cell


def carve_exit(grid, exit_cell, side="E"):
    ex, ey = exit_cell
    grid[ey][ex][side] = True


def draw_maze(surface, grid, exit_cell, tile_size, offset=(0, 0), exit_side="E"):
    # draws the maze grid onto the given surface, and a small exit marker poking out into the margin space reserved around the maze
    ox, oy = offset
    wall_thickness = 2
    cols = len(grid[0])
    rows = len(grid)

    surface.fill(COLOR_PATH, (ox, oy, cols * tile_size, rows * tile_size))

    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            px = ox + x * tile_size
            py = oy + y * tile_size

            if not cell["N"]:
                pygame.draw.line(surface, COLOR_WALL, (px, py), (px + tile_size, py), wall_thickness)
            if not cell["S"]:
                pygame.draw.line(surface, COLOR_WALL, (px, py + tile_size), (px + tile_size, py + tile_size), wall_thickness)
            if not cell["W"]:
                pygame.draw.line(surface, COLOR_WALL, (px, py), (px, py + tile_size), wall_thickness)
            if not cell["E"]:
                pygame.draw.line(surface, COLOR_WALL, (px + tile_size, py), (px + tile_size, py + tile_size), wall_thickness)

    # exit marker: a small green tab in the margin, just outside the exit
    # cell's open wall, so the way out is visually obvious
    ex_col, ex_row = exit_cell
    epx = ox + ex_col * tile_size
    epy = oy + ex_row * tile_size
    marker_thickness = max(4, tile_size // 4)
    marker_length = tile_size // 2
    pad = (tile_size - marker_length) // 2

    if exit_side == "E":
        rect = (epx + tile_size, epy + pad, marker_thickness, marker_length)
    elif exit_side == "W":
        rect = (epx - marker_thickness, epy + pad, marker_thickness, marker_length)
    elif exit_side == "S":
        rect = (epx + pad, epy + tile_size, marker_length, marker_thickness)
    else:  # "N"
        rect = (epx + pad, epy - marker_thickness, marker_length, marker_thickness)

    pygame.draw.rect(surface, COLOR_EXIT, rect)


def main():
    pygame.init()
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Psychic Maze")
    clock = pygame.time.Clock()

    # center the maze in whatever space it doesn't fill, turning the EXIT_MARGIN reserved above into breathing room on every side.
    offset_x = (WINDOW_WIDTH - MAZE_PIXEL_WIDTH) // 2
    offset_y = (WINDOW_HEIGHT - MAZE_PIXEL_HEIGHT) // 2

    exit_side = "E"
    maze_grid, start_cell, exit_cell = generate_maze()
    carve_exit(maze_grid, exit_cell, side=exit_side)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys_exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                maze_grid, start_cell, exit_cell = generate_maze()  # press R to regenerate
                carve_exit(maze_grid, exit_cell, side=exit_side)

        window.fill(COLOR_BG)
        draw_maze(window, maze_grid, exit_cell, TILE_SIZE, offset=(offset_x, offset_y), exit_side=exit_side)
        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
