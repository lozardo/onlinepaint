import os
import socket
import struct
import threading
import pickle

import white_lib

connected_clients = {}  # Dictionary to store connected clients for each whiteboard
lock = threading.Lock()


def send_to_all_clients(message, whiteboard_id):
    with lock:
        print(message)
        for client_socket, client_addr in connected_clients[whiteboard_id]:
            try:
                print(f"{client_socket} - {client_addr}")
                client_socket.sendall(pickle.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_addr}: {e}")


def handle_client(client_socket, addr):
    whiteboard_id = -1
    while True:
        data = client_socket.recv(1024)
        message = pickle.loads(data)
        print(f"{addr}: {message}")
        message_type = message[0]

        if message_type == "join":
            whiteboard_id = message[1]
            if whiteboard_id not in whiteboards:
                whiteboards[whiteboard_id] = white_lib.WhiteboardApp()
                whiteboards[whiteboard_id].initialize(False)
                connected_clients[whiteboard_id] = []

            send_whiteboard_state_to_client(client_socket, whiteboard_id)
            connected_clients[whiteboard_id].append((client_socket, addr))

        elif message_type == "draw":
            # Broadcast drawing updates to other clients
            broadcast_message = ("drawing", message[1])
            whiteboards[whiteboard_id].draw(message[1][0], message[1][1], message[1][2], message[1][3])

            send_to_all_clients(broadcast_message, whiteboard_id)

    # Remove user when they disconnect
    connected_clients[whiteboard_id].remove((client_socket, addr))
    client_socket.close()


def send_whiteboard_state_to_client(client_socket, whiteboard_id):
    temp_file_path = f"temp_whiteboard_{whiteboard_id}.png"

    # Save the whiteboard image
    whiteboard = whiteboards[whiteboard_id]
    whiteboard.save_picture_path(temp_file_path)

    with open(temp_file_path, "rb") as file:
        # Read the image file as binary data
        image_data = file.read()
        # Send the image size to the client
        client_socket.sendall(len(image_data).to_bytes(4, byteorder="big"))
        # Send the image data to the client
        client_socket.sendall(image_data)

    # Remove the temporary file
    #os.remove(temp_file_path)


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
    whiteboards = {}  # Dictionary to store instances of WhiteboardApp

    start_server()
