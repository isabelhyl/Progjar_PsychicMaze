# Holds the small amount of state that needs to survive across scene
# transitions: who am I, and what's the last lobby/lobby-list snapshot
# the server sent us. This is NOT game state -- it's just "what does the
# client currently know", refreshed every time a server message arrives

# Scenes read/write this via app.session rather than passing data through
# constructor args, so any scene can grab "my player_id" without the
# previous scene needing to know about it



class Session:
    def __init__(self):
        self.player_id = None
        self.player_name = None

        self.lobby_list = []      # last LOBBY_LIST data.lobbies
        self.lobby_state = None   # last LOBBY_STATE data (dict) or None if not in a lobby

        self.error_message = None  # last ERROR message text, shown by whichever scene is active

    def is_host(self):
        if not self.lobby_state or not self.player_id:
            return False
        return self.lobby_state.get("host_id") == self.player_id

    def is_spiritualist(self):
        if not self.lobby_state or not self.player_id:
            return False
        return self.lobby_state.get("spiritualist_id") == self.player_id

    def reset_lobby(self):
        self.lobby_state = None
