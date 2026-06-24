import pygame

from client.scenes.base import Scene
from shared.constants import WINDOW_WIDTH, WINDOW_HEIGHT


class TutorialScene(Scene):

    def on_enter(self, **kwargs):
        self.maze_data = kwargs["maze_data"]
        self.your_role = kwargs["your_role"]

    def handle_event(self, event):
        if (
            event.type == pygame.KEYDOWN
            or event.type == pygame.MOUSEBUTTONDOWN
        ):

            self.app.set_scene(
                "maze",
                maze_data=self.maze_data,
                your_role=self.your_role
            )

    def handle_message(self, msg_type, data):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((20, 20, 20))

        font_title = self.app.fonts["large"]
        font_body = self.app.fonts["normal"]

        y = 80

        title = font_title.render(
            "TUTORIAL",
            True,
            (255,255,255)
        )

        surface.blit(
            title,
            (WINDOW_WIDTH//2 - title.get_width()//2, y)
        )

        y += 80

        if self.your_role == "spiritualist":

            lines = [
                "YOUR ROLE: SPIRITUALIST",
                "",
                "You can see ghosts.",
                "You cannot see maze walls.",
                "Guide explorers safely through the maze.",
                "Avoid ghosts and reach the exit.",
            ]

        else:

            lines = [
                "YOUR ROLE: EXPLORER",
                "",
                "You can see maze walls.",
                "You cannot see ghosts.",
                "Follow the Spiritualist's guidance.",
                "Avoid getting trapped and reach the exit.",
            ]

        for line in lines:
            text = font_body.render(
                line,
                True,
                (255,255,255)
            )

            surface.blit(
                text,
                (WINDOW_WIDTH//2 - text.get_width()//2, y)
            )

            y += 40

        y += 40

        continue_text = font_body.render(
            "Press any key or click to continue",
            True,
            (200,200,200)
        )

        surface.blit(
            continue_text,
            (
                WINDOW_WIDTH//2 - continue_text.get_width()//2,
                y
            )
        )