import socket
import threading

# Server configuration
HOST = '0.0.0.0' # Listen on all available network adapters
PORT = 5555

# Note on connecting through LAN
# use ipconfig in powershell to find your ipv4 address
# insert that ip address into chat.py's
# chat = NetworkChat('192.168.0.242', 5555)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []

def broadcast(message, sender_client):
    """Sends a message to all connected clients except the sender."""
    for client in clients:
        if client != sender_client:
            try:
                client.send(message)
            except:
                clients.remove(client)

def handle_client(client):
    """Listens for messages from a specific client."""
    while True:
        try:
            message = client.recv(1024)
            broadcast(message, client)
        except:
            clients.remove(client)
            client.close()
            break

print(f"Server is listening on {HOST}:{PORT}...")

# Keep accepting new connections
while True:
    client, address = server.accept()
    print(f"Connected with {str(address)}")
    clients.append(client)
    
    # Start a new thread for this client so it doesn't block others
    thread = threading.Thread(target=handle_client, args=(client,))
    thread.start()