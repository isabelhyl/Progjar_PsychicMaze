import socket
import threading

class NetworkChat:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.messages = []  # Store incoming messages here
        self.running = True

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            # Start a background thread that constantly listens for messages
            listen_thread = threading.Thread(target=self._receive_messages)
            listen_thread.daemon = True # Closes when main program closes
            listen_thread.start()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send_message(self, text):
        try:
            self.client_socket.send(text.encode('utf-8'))
        except Exception as e:
            print(f"Failed to send: {e}")

    def _receive_messages(self):
        # This runs in the background!
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    self.messages.append(message)
            except:
                print("Disconnected from server.")
                self.running = False
                break

    def get_new_messages(self):
        # Your main.py calls this to check for messages without freezing
        new_msgs = self.messages.copy()
        self.messages.clear()
        return new_msgs


if __name__ == "__main__":
    import time
    
    # Connect to your local area network
    # Use ipconfig in PowerShell and find the IPv4 address
    # The IP Address of the apartment's router is 192.168.1.12
    chat = NetworkChat('192.168.0.242', 5555)
    
    if chat.connect():
        print("Connected to server! Type a message and press Enter.")
        
        # A simple loop to type messages in the terminal
        while True:
            msg = input()
            if msg.lower() == 'quit':
                chat.running = False
                break
            chat.send_message(msg)
            
            # Quickly check if we received anything back
            # (In reality, your Pygame loop will do this checking)
            incoming = chat.get_new_messages()
            for new_msg in incoming:
                print(f"Friend says: {new_msg}")