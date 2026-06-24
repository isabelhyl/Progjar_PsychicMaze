# Defines the wire format for client <-> server communication, plus small helpers for sending/receiving framed JSON messages over a TCP socket

# 1. WIRE FORMAT
# Every message is a single JSON object followed by a newline ("\n"):
# {"type": "<MESSAGE_TYPE>", "data": { ... }}\n

# Because TCP is a stream (no built-in message boundaries), we use the newline as a delimiter
# this means the JSON payload itself must never contain a literal, un-escaped newline character
# json.dumps() already guarantees this for us, so as long as both sides always use send_message / recv_messages from this file, framing stays consistent.

# 2. MESSAGE TYPES (client -> server)
# LOGIN          {"name": str}
# CREATE_GAME    {"num_players": int, "spiritualist_mode": "random"|"manual", "num_ghosts": int}
#                -> server creates a lobby with these options, sender becomes host
# JOIN_GAME      {"lobby_id": str}
# LIST_LOBBIES   {}
# SET_OPTIONS    {"num_players": int, "spiritualist_mode": "random"|"manual", "num_ghosts": int}
#                (host only; adjusts options on an already-created lobby)
# SET_SPIRITUALIST {"player_id": str}                (host only, manual mode only)
# START_GAME     {}                                  (host only)
# END_GAME       {}                                  (host only)
# EXIT_LOBBY     {}                                  (non-host leaves lobby)
# MOVE           {"dx": float, "dy": float}          (per-frame input direction, magnitude <= 1)
# EXIT_GAME_TO_LOBBY {}                               (sent by client after seeing a game-over popup)

# MESSAGE TYPES (server -> client)
# ---------------------------------
# LOGIN_OK       {"player_id": str, "name": str}
# ERROR          {"message": str}
# LOBBY_LIST     {"lobbies": [{"lobby_id", "host_name", "num_players", "max_players"}, ...]}
# LOBBY_STATE    {"lobby_id", "host_id", "host_name", "players": [...],
#                 "options": {...}, "spiritualist_id": str|None,
#                 "can_start": bool}
# RETURN_TO_MENU {"reason": str}                     (host ended game, or kicked, etc.)
# GAME_STARTING  {"lobby_id": str, "maze": {...}, "your_role": "spiritualist"|"explorer"}
# GAME_STATE     {"players": [{"player_id","x","y","alive","role"}, ...],
#                 "ghosts": [{"x","y"}, ...]}        (broadcast every tick)
# PLAYER_DIED    {"player_id": str}                  (sent to everyone the instant a ghost catches someone;
#                                                      the caught player's client shows "BOO, YOU'RE DEAD")
# GAME_OVER      {"result": "win"|"lose"}            (sent to everyone once the match ends:
#                                                      "win" -> survivors escaped, "lose" -> everyone died)


import json
import socket


# Client: Server message types
LOGIN = "LOGIN"
CREATE_GAME = "CREATE_GAME"
JOIN_GAME = "JOIN_GAME"
LIST_LOBBIES = "LIST_LOBBIES"
SET_OPTIONS = "SET_OPTIONS"
SET_SPIRITUALIST = "SET_SPIRITUALIST"
START_GAME = "START_GAME"
END_GAME = "END_GAME"
EXIT_LOBBY = "EXIT_LOBBY"
MOVE = "MOVE"
EXIT_GAME_TO_LOBBY = "EXIT_GAME_TO_LOBBY"

# Server: Client message types
LOGIN_OK = "LOGIN_OK"
ERROR = "ERROR"
LOBBY_LIST = "LOBBY_LIST"
LOBBY_STATE = "LOBBY_STATE"
RETURN_TO_MENU = "RETURN_TO_MENU"
GAME_STARTING = "GAME_STARTING"
GAME_STATE = "GAME_STATE"
PLAYER_DIED = "PLAYER_DIED"
PLAYER_ESCAPED = "PLAYER_ESCAPED"
GAME_OVER = "GAME_OVER"


def make_message(msg_type, data=None):
    """Builds a message dict ready for json.dumps."""
    return {"type": msg_type, "data": data or {}}


def encode_message(msg_type, data=None):
    """Encodes a message into bytes ready to send over a socket."""
    payload = json.dumps(make_message(msg_type, data))
    return (payload + "\n").encode("utf-8")


def send_message(sock, msg_type, data=None):
    """Sends a single framed JSON message over the given socket."""
    sock.sendall(encode_message(msg_type, data))


class MessageBuffer:
    # Accumulates raw bytes received from a TCP socket and yields complete,
    # newline-delimited JSON messages as they become available.

    # TCP can deliver partial messages or multiple messages in one recv(),
    # so we can't just json.loads() the raw recv() output directly. This
    # buffer handles that splitting for both client and server.

    # Usage:
    #     buf = MessageBuffer()
    #     chunk = sock.recv(RECV_BUFFER_SIZE)
    #     if not chunk:
    #         # connection closed
    #         ...
    #     for msg in buf.feed(chunk):
    #         handle(msg)

    def __init__(self):
        self._raw = b""

    def feed(self, chunk):
        # Feeds newly-received bytes into the buffer and returns a list of
        # complete decoded messages (dicts with "type" and "data").
        # Malformed lines are skipped rather than raising, so one bad
        # message can't take down a connection.
        self._raw += chunk
        messages = []

        while b"\n" in self._raw:
            line, self._raw = self._raw.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                messages.append(json.loads(line.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # skip malformed message rather than crashing the connection.
                continue

        return messages


def create_client_socket(host, port, timeout=5):
    """Creates and connects a TCP socket to the given server address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    sock.settimeout(None)  # switch to blocking mode after connecting
    return sock
