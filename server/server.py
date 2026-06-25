# run: py server.server


# - One TCP listener socket accepts incoming connections
# - Each connected client gets its own handler thread (handle_client).
# - All shared state (players, lobbies) lives in a single GameState instance (server/state.py), 
#   protected by a lock, so multiple threads can safely mutate it.
# - After any action that changes a lobby's state, the server broadcasts
#   a fresh LOBBY_STATE message to every player currently in that lobby.
#   Clients never need to compute lobby state themselves, they just render whatever the server last sent them.
# - When the host starts a game, a GameSession (server/game.py) is
#   created and runs the maze simulation in its own thread. MOVE messages
#   from clients are routed into the session; the session broadcasts
#   GAME_STATE each tick and GAME_OVER / PLAYER_DIED as events fire.


import socket
import threading

from shared.constants import SERVER_HOST, SERVER_PORT, RECV_BUFFER_SIZE
from shared import protocol
from server.state import GameState
from server.game import GameSession


class ClientConnection:
    """Bundles a socket with the player_id it's authenticated as,
    plus a lock so sends from different threads don't interleave."""

    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.player_id = None
        self.send_lock = threading.Lock()

    def send(self, msg_type, data=None):
        try:
            with self.send_lock:
                protocol.send_message(self.conn, msg_type, data)
        except OSError:
            pass 


class Server:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.host = host
        self.port = port
        self.state = GameState()

        # player_id -> ClientConnection, so we can push messages to specific players at any time (from any thread)
        self.connections = {}
        self.connections_lock = threading.Lock()

        # lobby_id -> GameSession, for lobbies mid round
        # removed once the round ends
        self.game_sessions = {}
        self.game_sessions_lock = threading.Lock()

    def start(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen()
        print(f"[SERVER] Listening on {self.host}:{self.port}")

        try:
            while True:
                conn, addr = listener.accept()
                client = ClientConnection(conn, addr)
                thread = threading.Thread(target=self.handle_client, args=(client,), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("[SERVER] Shutting down.")
        finally:
            listener.close()

  
    # recv loop per connection
    def handle_client(self, client):
        print(f"[SERVER] Connection from {client.addr}")
        buf = protocol.MessageBuffer()
        try:
            while True:
                chunk = client.conn.recv(RECV_BUFFER_SIZE)
                if not chunk:
                    break
                for msg in buf.feed(chunk):
                    self.dispatch(client, msg)
        except (ConnectionResetError, OSError):
            pass
        finally:
            self.on_disconnect(client)

    def dispatch(self, client, msg):
        msg_type = msg.get("type")
        data = msg.get("data", {})
        handler_name = f"handle_{msg_type.lower()}" if msg_type else None
        handler = getattr(self, handler_name, None) if handler_name else None
        if handler is None:
            client.send(protocol.ERROR, {"message": f"Unknown message type: {msg_type}"})
            return
        try:
            handler(client, data)
        except ValueError as e:
            client.send(protocol.ERROR, {"message": str(e)})

    def on_disconnect(self, client):
        print(f"[SERVER] Disconnected: {client.addr}")
        if client.player_id:
            lobby = self.state.get_lobby_for_player(client.player_id)
            self.state.remove_player(client.player_id)
            with self.connections_lock:
                self.connections.pop(client.player_id, None)
            if lobby:
                # if a round is in progress, mark the disconnected player as dead in the simulation so win/lose can still continue
                session = self._get_session(lobby.lobby_id)
                if session:
                    session.mark_player_disconnected(client.player_id)
                self.broadcast_lobby_state(lobby.lobby_id)
        try:
            client.conn.close()
        except OSError:
            pass

    # message handlers

    def handle_login(self, client, data):
        name = (data.get("name") or "").strip()
        if not name:
            client.send(protocol.ERROR, {"message": "Name cannot be empty"})
            return
        player = self.state.add_player(name)
        client.player_id = player.player_id
        with self.connections_lock:
            self.connections[player.player_id] = client
        client.send(protocol.LOGIN_OK, {"player_id": player.player_id, "name": player.name})

    def handle_list_lobbies(self, client, data):
        client.send(protocol.LOBBY_LIST, {"lobbies": self.state.list_lobby_summaries()})

    def handle_create_game(self, client, data):
        player = self._require_player(client)
        lobby = self.state.create_lobby(player)
        lobby.options.update(
            num_players=data.get("num_players"),
            spiritualist_mode=data.get("spiritualist_mode"),
            num_ghosts=data.get("num_ghosts"),
        )
        client.send(protocol.LOBBY_STATE, lobby.to_public_dict())
        client.send(
            protocol.CHAT_HISTORY,
            {
                "messages": []
            }
        )

    def handle_join_game(self, client, data):
        player = self._require_player(client)
        lobby_id = data.get("lobby_id")
        lobby = self.state.get_lobby(lobby_id)
        if not lobby:
            client.send(protocol.ERROR, {"message": "Lobby not found"})
            return
        lobby.add_player(player)
        self.broadcast_lobby_state(lobby.lobby_id)
        client.send(
            protocol.CHAT_HISTORY,
            {
                "messages": lobby.chat_messages
            }
        )

    def handle_set_options(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        self._require_host(lobby, player)
        lobby.options.update(
            num_players=data.get("num_players"),
            spiritualist_mode=data.get("spiritualist_mode"),
            num_ghosts=data.get("num_ghosts"),
        )
        self.broadcast_lobby_state(lobby.lobby_id)

    def handle_set_spiritualist(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        self._require_host(lobby, player)
        target_id = data.get("player_id")
        if target_id not in lobby.players:
            raise ValueError("That player is not in this lobby")
        if lobby.options.spiritualist_mode != "manual":
            raise ValueError("Spiritualist mode is not set to manual")
        lobby.spiritualist_id = target_id
        self.broadcast_lobby_state(lobby.lobby_id)

    def handle_start_game(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        self._require_host(lobby, player)
        if not lobby.can_start():
            raise ValueError("Not enough players to start yet")
        if lobby.spiritualist_id is None:
            lobby.assign_spiritualist()
        lobby.started = True
        self.broadcast_lobby_state(lobby.lobby_id)

        session = GameSession(lobby, self.broadcast_to_lobby)
        with self.game_sessions_lock:
            self.game_sessions[lobby.lobby_id] = session

        # GAME_STARTING is personalized (each player gets their own role)
        # so send individually rather than via broadcast_to_lobby
        with self.connections_lock:
            targets = {pid: self.connections.get(pid) for pid in lobby.players.keys()}
        for pid, target_client in targets.items():
            if target_client:
                target_client.send(protocol.GAME_STARTING, session.build_starting_payload(pid))

        session.start()

    def handle_end_game(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        self._require_host(lobby, player)

        self._stop_session(lobby.lobby_id)
        self.broadcast_to_lobby(lobby.lobby_id, protocol.RETURN_TO_MENU, {"reason": "Host ended the game"})

        for pid in list(lobby.players.keys()):
            p = self.state.get_player(pid)
            if p:
                p.lobby_id = None
        self.state.lobbies.pop(lobby.lobby_id, None)

    def handle_exit_lobby(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        if lobby.is_host(player.player_id):
            raise ValueError("Host cannot exit; use END_GAME instead")
        lobby.remove_player(player.player_id)
        player.lobby_id = None
        self.state.remove_lobby_if_empty(lobby.lobby_id)
        self.broadcast_lobby_state(lobby.lobby_id)

    def handle_move(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        session = self._get_session(lobby.lobby_id)
        if not session:
            return
        dx = float(data.get("dx", 0.0))
        dy = float(data.get("dy", 0.0))
        session.set_player_input(player.player_id, dx, dy)

    def handle_exit_game_to_lobby(self, client, data):
        """Sent after a player dismisses the game-over popup.
        Cleans up the finished session and returns LOBBY_STATE
        so the client can re-render the waiting lobby."""
        player = self._require_player(client)
        lobby = self._require_lobby(player)
        self._cleanup_session_if_finished(lobby.lobby_id)
        client.send(protocol.LOBBY_STATE, lobby.to_public_dict())


    # helpers
    def _require_player(self, client):
        player = self.state.get_player(client.player_id) if client.player_id else None
        if not player:
            raise ValueError("Not logged in")
        return player

    def _require_lobby(self, player):
        lobby = self.state.get_lobby_for_player(player.player_id)
        if not lobby:
            raise ValueError("Not currently in a lobby")
        return lobby

    def _require_host(self, lobby, player):
        if not lobby.is_host(player.player_id):
            raise ValueError("Only the host can do that")

    def _get_session(self, lobby_id):
        with self.game_sessions_lock:
            return self.game_sessions.get(lobby_id)

    def _stop_session(self, lobby_id):
        with self.game_sessions_lock:
            session = self.game_sessions.pop(lobby_id, None)
        if session:
            session.stop()

    def _cleanup_session_if_finished(self, lobby_id):
        with self.game_sessions_lock:
            session = self.game_sessions.get(lobby_id)
            if not (session and session._finished):
                return
            session.stop()
            self.game_sessions.pop(lobby_id, None)
        lobby = self.state.get_lobby(lobby_id)
        if lobby:
            lobby.started = False
            lobby.spiritualist_id = None

    def broadcast_to_lobby(self, lobby_id, msg_type, data):
        lobby = self.state.get_lobby(lobby_id)
        if not lobby:
            return
        with self.connections_lock:
            targets = [self.connections.get(pid) for pid in lobby.players.keys()]
        for client in targets:
            if client:
                client.send(msg_type, data)

    def broadcast_lobby_state(self, lobby_id):
        lobby = self.state.get_lobby(lobby_id)
        if not lobby:
            return
        self.broadcast_to_lobby(lobby_id, protocol.LOBBY_STATE, lobby.to_public_dict())

    def handle_chat_message(self, client, data):
        player = self._require_player(client)
        lobby = self._require_lobby(player)

        msg = {
            "sender": player.name,
            "text": data.get("text", "")
        }

        lobby.chat_messages.append(msg)

        self.broadcast_to_lobby(
            lobby.lobby_id,
            protocol.CHAT_MESSAGE,
            msg
        )

if __name__ == "__main__":
    Server().start()
