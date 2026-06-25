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

MAX_INPUT_HEIGHT = 120


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

    def __init__(self, rect, font, placeholder="", max_length=500):
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
                # print(repr(event.unicode)) # DEBUG CHAT
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

        # if self.text:
        #     text_surf = self.font.render(self.text, True, COLOR_TEXT)
        # else:
        #     text_surf = self.font.render(self.placeholder, True, COLOR_MUTED)
        # surface.blit(text_surf, (self.rect.x + 10, self.rect.centery - text_surf.get_height() // 2))

        text_area_width = self.rect.width - 20
        lines = self.get_wrapped_lines(text_area_width)
        # y = self.rect.y + 8
        # for line in lines:

        line_height = 24
        visible_lines = max(
            1,
            (self.rect.height - 10) // line_height
        )
        lines_to_draw = lines[-visible_lines:]
        y = self.rect.bottom - 8 - len(lines_to_draw) * line_height

        for line in lines_to_draw:
            text_surf = self.font.render(
                line,
                True,
                COLOR_TEXT
            )
            surface.blit(
                text_surf,
                (
                    self.rect.x + 10,
                    y
                )
            )
            y += 24

        if self.active and self._cursor_visible:
            # cursor_x = self.rect.x + 10 + self.font.size(self.text)[0] + 2
            wrapped_lines = self.get_wrapped_lines(
                self.rect.width - 20
            )

            last_line = wrapped_lines[-1] if wrapped_lines else ""

            cursor_x = (
                self.rect.x
                + 10
                + self.font.size(last_line)[0]
            )

            cursor_y = (
                self.rect.bottom
                - 8
                - 24
            )

            # pygame.draw.line(
            #     surface,
            #     COLOR_TEXT,
            #     (cursor_x, cursor_y),
            #     (cursor_x, cursor_y + 20),
            #     2
            # )
            pygame.draw.line(
                surface, COLOR_TEXT,
                (cursor_x, self.rect.y + 8), (cursor_x, self.rect.bottom - 8), 2
            )

    def get_wrapped_lines(self, max_width):
        lines = []
        current = ""

        for char in self.text:
            test = current + char

            if self.font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = char

        if current:
            lines.append(current)

        return lines


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


class ChatPanel:

    def __init__(self, rect, font, messages):
        self.rect = pygame.Rect(rect)
        self.font = font

        # self.messages = []
        self.messages = messages

        self.scroll_offset = 0

        # self.input_box = TextInput(
        #     (
        #         self.rect.x + 10,
        #         self.rect.bottom - 50,
        #         self.rect.width - 20,
        #         40
        #     ),
        #     font,
        #     placeholder="Type a message..."
        # )

        # self.send_button = Button(
        #     (
        #         self.rect.right - 90,
        #         self.rect.bottom - 50,
        #         80,
        #         40
        #     ),
        #     "Send",
        #     font
        # )

        SEND_W = 60
        GAP = 10

        self.send_button = Button(
            (
                self.rect.right - SEND_W - 10,
                self.rect.bottom - 50,
                SEND_W,
                40
            ),
            "Send",
            font
        )

        self.input_box = TextInput(
            (
                self.rect.x + 10,
                self.rect.bottom - 50,

                # stop before Send button
                self.rect.width - SEND_W - GAP - 30,

                40
            ),
            font,
            placeholder="Type a message..."
        )

        self.close_button = Button(
            (
                self.rect.right - 40,
                self.rect.y + 10,
                30,
                30
            ),
            "X",
            font
        )

    def _message_width(self):
        """The width available for rendering one line of chat text.

        This MUST be the single source of truth for message wrapping --
        draw() uses it to lay out text, and the scroll-position
        calculations (add_message / scroll_to_bottom / MOUSEWHEEL
        handling) use it to predict how tall that same text will be.

        Previously, draw() narrowed this to leave room for the close
        button (self.close_button.rect.left - self.rect.x - 20), while
        add_message()/scroll_to_bottom() used a wider self.rect.width -
        20 that ignored the close button entirely. That mismatch meant
        the scroll math always under-estimated how many lines a message
        would actually wrap to once drawn, so scrolling "to the bottom"
        landed a bit short of the real bottom -- the most recent 1-2
        messages would end up rendered just past the visible/clipped
        area, underneath the input box. Computing it once here and
        reusing it everywhere keeps the two calculations from ever
        drifting apart again.
        """
        return self.close_button.rect.left - self.rect.x - 20

    def add_message(self, text):
        self.messages.append(text)
        # total_height = len(self.messages) * 24

        total_height = 0
        message_width = self._message_width()
        for msg in self.messages:
            wrapped_lines = self.wrap_text(
                msg,
                message_width
            )
            total_height += len(wrapped_lines) * 24 + 5

        # visible_height = self.rect.height - 70
        visible_height = self.input_box.rect.top - self.rect.y - 10
        max_scroll = max(0, total_height - visible_height)
        self.scroll_offset = -max_scroll

    def handle_event(self, event):
        if self.close_button.handle_event(event):
            return ("close", None)

        if self.send_button.handle_event(event):

            text = self.input_box.text.strip()

            if text:
                self.input_box.text = ""
                return ("send", text)

        self.input_box.handle_event(event)

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_RETURN:

                text = self.input_box.text.strip()

                if text:
                    self.input_box.text = ""
                    return ("send", text)

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset += event.y * 20
            # total_height = len(self.messages) * 24

            total_height = 0
            message_width = self._message_width()
            for msg in self.messages:
                wrapped_lines = self.wrap_text(
                    msg,
                    message_width
                )
                total_height += len(wrapped_lines) * 24 + 5

            visible_height = self.input_box.rect.top - self.rect.y - 10
            max_scroll = max(0, total_height - visible_height)
            self.scroll_offset = max(
                -max_scroll,
                min(0, self.scroll_offset)
            )

        return (None, None)

    def update(self, dt):
        self.input_box.update(dt)
        wrapped = self.input_box.get_wrapped_lines(
            self.input_box.rect.width - 20
        )

        self.send_button.rect.height = self.input_box.rect.height
        self.send_button.rect.y = self.input_box.rect.y

        num_lines = max(1, len(wrapped))
        self.input_box.rect.height = min(
            MAX_INPUT_HEIGHT,
            max(
                40,
                num_lines * 24 + 10
            )
        )
        # self.input_box.rect.y = (
        #     self.rect.bottom
        #     - self.input_box.rect.height
        #     - 10
        # )
        bottom_margin = 10
        self.input_box.rect.height = min(
            MAX_INPUT_HEIGHT,
            max(
                40,
                num_lines * 24 + 10
            )
        )

        self.input_box.rect.bottom = (
            self.rect.bottom - bottom_margin
        )
        self.send_button.rect.y = self.input_box.rect.y

    def draw(self, surface):

        pygame.draw.rect(
            surface,
            COLOR_PANEL,
            self.rect
        )

        pygame.draw.rect(
            surface,
            COLOR_BORDER,
            self.rect,
            width=2
        )

        y = self.rect.y + 10 + self.scroll_offset

        # surface.set_clip(self.rect)
        message_area_bottom = self.input_box.rect.top - 10
        message_clip = pygame.Rect(
            self.rect.x,
            self.rect.y,
            self.rect.width,
            message_area_bottom - self.rect.y
        )

        surface.set_clip(message_clip)
                
        message_width = self._message_width()

        # for msg in self.messages:
        #     wrapped_lines = self.wrap_text(
        #         msg,
        #         message_width
        #     )
        #     for line in wrapped_lines:
        #         txt = self.font.render(
        #             line,
        #             True,
        #             COLOR_TEXT
        #         )
        #         surface.blit(
        #             txt,
        #             (self.rect.x + 10, y)
        #         )
        #         y += 24
        #     y += 5

        USERNAME_COLOR = COLOR_BUTTON_PRIMARY

        for msg in self.messages:

            if ": " in msg:
                username, text = msg.split(": ", 1)
            else:
                username = ""
                text = msg

            full_text = f"{username}: {text}" if username else text

            wrapped_lines = self.wrap_text(
                full_text,
                message_width
            )

            first_line = True

            for line in wrapped_lines:

                if first_line and username:

                    prefix = f"{username}: "

                    if line.startswith(prefix):

                        name_surface = self.font.render(
                            prefix,
                            True,
                            USERNAME_COLOR
                        )

                        msg_surface = self.font.render(
                            line[len(prefix):],
                            True,
                            COLOR_TEXT
                        )

                        surface.blit(
                            name_surface,
                            (self.rect.x + 10, y)
                        )

                        surface.blit(
                            msg_surface,
                            (
                                self.rect.x + 10 + name_surface.get_width(),
                                y
                            )
                        )

                    else:
                        txt = self.font.render(
                            line,
                            True,
                            COLOR_TEXT
                        )

                        surface.blit(
                            txt,
                            (self.rect.x + 10, y)
                        )

                    first_line = False

                else:

                    txt = self.font.render(
                        line,
                        True,
                        COLOR_TEXT
                    )

                    surface.blit(
                        txt,
                        (self.rect.x + 10, y)
                    )

                y += 24

            y += 5

        surface.set_clip(None)

        self.input_box.draw(surface)
        self.close_button.draw(surface)
        self.send_button.draw(surface)

    def wrap_text(self, text, max_width):
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    def scroll_to_bottom(self):
        total_height = 0
        message_width = self._message_width()

        for msg in self.messages:
            wrapped_lines = self.wrap_text(
                msg,
                message_width
            )
            total_height += len(wrapped_lines) * 24 + 5

        visible_height = self.input_box.rect.top - self.rect.y - 10

        max_scroll = max(
            0,
            total_height - visible_height
        )

        self.scroll_offset = -max_scroll

