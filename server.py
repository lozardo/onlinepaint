# server.py
import socket
import threading
import json
import pickle

# Store user information including colors
user_colors = {}

def handle_client(client_socket, addr):
    while True:
        print(addr)
        try:
            data = client_socket.recv(1024)
            message = pickle.loads(data)
            print(message)
            message_type = message[0]

            if message_type == "join":
                # Assign a color to the user
                user_colors[addr] = (0, 0, 0)  # Initial color: black
            elif message_type == "color":
                user_colors[addr] = message[1]
            elif message_type == "drawing":
                # Broadcast drawing updates to other clients
                color = user_colors[addr]
                broadcast_message = {"type": "drawing", "data": {"points": message["data"]["points"], "color": color}}

                for client_address in user_colors:
                    if client_address != addr:
                        client_socket.sendto(json.dumps(broadcast_message).encode(), client_address)

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            break

    # Remove user when they disconnect
    print(user_colors[addr])
    del user_colors[addr]
    client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("Server listening on port 5555")

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()

if __name__ == "__main__":
    start_server()
