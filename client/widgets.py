"""
client/widgets.py

Small, dependency-free pygame UI building blocks shared across every
scene. Nothing here knows about the network or game state -- widgets
just draw themselves and report interaction (click, text changes) back
to whoever owns them.
"""

import pygame


COLOR_BG = (20, 20, 28)
COLOR_PANEL = (32, 32, 44)
COLOR_TEXT = (235, 235, 245)
COLOR_MUTED = (150, 150, 165)
COLOR_BORDER = (90, 90, 110)

COLOR_BUTTON = (60, 60, 85)
COLOR_BUTTON_HOVER = (85, 85, 120)
COLOR_BUTTON_DISABLED = (50, 50, 55)
COLOR_BUTTON_DANGER = (180, 60, 70)
COLOR_BUTTON_DANGER_HOVER = (210, 80, 90)
COLOR_BUTTON_PRIMARY = (90, 180, 130)
COLOR_BUTTON_PRIMARY_HOVER = (110, 210, 150)


class Button:
    """A clickable rectangle with a label. `variant` controls color
    scheme: "default", "primary" (greenish, used for start/join/confirm),
    or "danger" (reddish, used for end game/exit)."""

    def __init__(self, rect, label, font, variant="default", enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.variant = variant
        self.enabled = enabled
        self._hovered = False

    def handle_event(self, event):
        """Returns True if this click event activates the button."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def _colors(self):
        if not self.enabled:
            return COLOR_BUTTON_DISABLED, COLOR_MUTED
        if self.variant == "danger":
            return (COLOR_BUTTON_DANGER_HOVER if self._hovered else COLOR_BUTTON_DANGER), COLOR_TEXT
        if self.variant == "primary":
            return (COLOR_BUTTON_PRIMARY_HOVER if self._hovered else COLOR_BUTTON_PRIMARY), (20, 20, 28)
        return (COLOR_BUTTON_HOVER if self._hovered else COLOR_BUTTON), COLOR_TEXT

    def draw(self, surface):
        bg, fg = self._colors()
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, width=1, border_radius=6)
        text_surf = self.font.render(self.label, True, fg)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class TextInput:
    """A single-line editable text field. Call handle_event for every
    pygame event, and check .text for the current contents."""

    def __init__(self, rect, font, placeholder="", max_length=20):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.placeholder = placeholder
        self.max_length = max_length
        self.text = ""
        self.active = False
        self._cursor_visible = True
        self._cursor_timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                pass  # caller checks for Enter separately via pygame.K_RETURN if needed
            elif len(self.text) < self.max_length and event.unicode.isprintable():
                self.text += event.unicode

    def update(self, dt):
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_PANEL, self.rect, border_radius=4)
        border_color = COLOR_BUTTON_PRIMARY if self.active else COLOR_BORDER
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=4)

        if self.text:
            text_surf = self.font.render(self.text, True, COLOR_TEXT)
        else:
            text_surf = self.font.render(self.placeholder, True, COLOR_MUTED)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.centery - text_surf.get_height() // 2))

        if self.active and self._cursor_visible:
            cursor_x = self.rect.x + 10 + self.font.size(self.text)[0] + 2
            pygame.draw.line(
                surface, COLOR_TEXT,
                (cursor_x, self.rect.y + 8), (cursor_x, self.rect.bottom - 8), 2
            )


class Stepper:
    """A '<  value  >' control for adjusting an integer within [min_value, max_value]."""

    def __init__(self, rect, font, value, min_value, max_value, step=1, label=""):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.label = label

        btn_w = 32
        self.left_button = Button((self.rect.x, self.rect.y, btn_w, self.rect.height), "<", font)
        self.right_button = Button(
            (self.rect.right - btn_w, self.rect.y, btn_w, self.rect.height), ">", font
        )

    def handle_event(self, event):
        """Returns True if the value changed."""
        if self.left_button.handle_event(event):
            new_val = max(self.min_value, self.value - self.step)
            if new_val != self.value:
                self.value = new_val
                return True
        if self.right_button.handle_event(event):
            new_val = min(self.max_value, self.value + self.step)
            if new_val != self.value:
                self.value = new_val
                return True
        return False

    def draw(self, surface):
        self.left_button.draw(surface)
        self.right_button.draw(surface)

        value_rect = pygame.Rect(
            self.left_button.rect.right, self.rect.y,
            self.right_button.rect.x - self.left_button.rect.right, self.rect.height
        )
        pygame.draw.rect(surface, COLOR_PANEL, value_rect)
        pygame.draw.rect(surface, COLOR_BORDER, value_rect, width=1)

        text_surf = self.font.render(str(self.value), True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=value_rect.center)
        surface.blit(text_surf, text_rect)


class ToggleGroup:
    """A row of mutually-exclusive option buttons (e.g. "random" / "manual")."""

    def __init__(self, rect, font, options, selected, gap=10):
        self.font = font
        self.options = options  # list of (value, label)
        self.selected = selected
        self.buttons = []

        x = rect[0]
        btn_w = (rect[2] - gap * (len(options) - 1)) // len(options)
        for value, label in options:
            self.buttons.append((value, Button((x, rect[1], btn_w, rect[3]), label, font, variant="default")))
            x += btn_w + gap

    def handle_event(self, event):
        """Returns True if the selection changed."""
        for value, button in self.buttons:
            if button.handle_event(event):
                if value != self.selected:
                    self.selected = value
                    return True
        return False

    def draw(self, surface):
        for value, button in self.buttons:
            # Highlight the currently-selected option using the primary variant.
            button.variant = "primary" if value == self.selected else "default"
            button.draw(surface)
