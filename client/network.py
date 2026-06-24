# Thin client-side networking wrapper around the shared protocol.

# Pygame's main loop needs to stay responsive (rendering, input) and can't
# block on socket.recv(). So we run a background thread that does nothing
# but read incoming bytes and push decoded messages onto a thread-safe
# queue; the main loop drains that queue once per frame (see
# client/app.py's event pump).

# This file has no pygame-specific code, so it can be reused for any
# screen without per-screen networking boilerplate.


import queue
import threading

from shared.constants import SERVER_HOST, SERVER_PORT, RECV_BUFFER_SIZE
from shared import protocol


class NetworkClient:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.incoming = queue.Queue()
        self.connected = False
        self._recv_thread = None

    def connect(self):
        # Connects to the server and starts the background receive thread.
        # Raises OSError/socket.timeout on failure -- callers should catch
        # this and show an error on screen rather than crashing.
        self.sock = protocol.create_client_socket(self.host, self.port)
        self.connected = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def send(self, msg_type, data=None):
        if not self.connected or not self.sock:
            return
        try:
            protocol.send_message(self.sock, msg_type, data)
        except OSError:
            self.connected = False

    def poll(self):
        # Drains and returns all messages received since the last poll.
        # Call this once per frame from the main loop. Never blocks.
        messages = []
        while True:
            try:
                messages.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return messages

    def close(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    # background thread 
    def _recv_loop(self):
        buf = protocol.MessageBuffer()
        try:
            while self.connected:
                chunk = self.sock.recv(RECV_BUFFER_SIZE)
                if not chunk:
                    break  # server closed the connection
                for msg in buf.feed(chunk):
                    self.incoming.put(msg)
        except OSError:
            pass
        finally:
            self.connected = False
            # Let the UI know the connection dropped, so it can show a
            # message instead of silently freezing.
            self.incoming.put({"type": "DISCONNECTED", "data": {}})
