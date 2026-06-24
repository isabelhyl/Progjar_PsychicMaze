"""
client/scenes/base.py

Base class for every screen (login, mainMenu, gameOptions, lobbyList,
lobby). The App (client/app.py) holds exactly one active Scene at a
time and forwards pygame events, dt-based updates, network messages,
and draw calls to it.

A scene switches to another scene by calling self.app.set_scene(...);
it never imports other scenes directly, to avoid circular imports
between scene modules.
"""


class Scene:
    def __init__(self, app):
        self.app = app  # gives access to app.network, app.session, app.set_scene(), app.screen, app.fonts

    def on_enter(self, **kwargs):
        """Called right after this scene becomes active. kwargs carries
        whatever data the previous scene passed along (e.g. player_id)."""
        pass

    def on_exit(self):
        """Called right before switching away from this scene."""
        pass

    def handle_event(self, event):
        """Called once per pygame event (keyboard, mouse, etc.)."""
        pass

    def handle_message(self, msg_type, data):
        """Called once per message received from the server this frame."""
        pass

    def update(self, dt):
        """Called once per frame with the elapsed time in seconds."""
        pass

    def draw(self, surface):
        """Called once per frame; draw this scene's contents onto surface."""
        pass
