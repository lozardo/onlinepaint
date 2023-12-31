import socket
import threading
import json
import pickle

# Store user information including colors
user_colors = {}
connected_clients = []  # List to store connected clients
lock = threading.Lock()

def send_to_all_clients(message):
    with lock:
        print(message)
        for client_socket, client_addr in connected_clients:
            try:
                client_socket.sendall(pickle.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_addr}: {e}")

def handle_client(client_socket, addr):
    while True:
        #try:
        data = client_socket.recv(1024)
        message = pickle.loads(data)
        print(f"{addr}: {message}")
        message_type = message[0]

        if message_type == "join":
            # Assign a color to the user
            user_colors[str(addr)] = (0, 0, 0)  # Convert tuple to string
        elif message_type == "color":
            user_colors[str(addr)] = message[1]  # Convert tuple to string
        elif message_type == "draw":
            # Print the message to debug

            # Broadcast drawing updates to other clients
            color = user_colors[str(addr)]  # Convert tuple to string
            broadcast_message = {"type": "drawing", "data": [message[1], color]}

            send_to_all_clients(broadcast_message)
        '''except Exception as e:
            print(f"Error handling client {addr}: {e}")
            break'''

    # Remove user when they disconnect
    print(user_colors[str(addr)])  # Convert tuple to string
    del user_colors[str(addr)]  # Convert tuple to string
    client_socket.close()

    # Remove user when they

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 5555))
    server.listen(5)
    print("Server listening on port 5555")

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()

if __name__ == "__main__":
    start_server()
