import os
import socket
import struct
import threading
import pickle

import white_lib

connected_clients = []  # List to store connected clients
lock = threading.Lock()


def send_to_all_clients(message):
    with lock:
        print(message)
        for client_socket, client_addr in connected_clients:
            try:
                print(f"{client_socket} - {client_addr}")
                client_socket.sendall(pickle.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_addr}: {e}")


def handle_client(client_socket, addr, whiteboard):
    while True:
        data = client_socket.recv(1024)
        message = pickle.loads(data)
        print(f"{addr}: {message}")
        message_type = message[0]

        if message_type == "join":
            send_whiteboard_state_to_client(client_socket, whiteboard)
            connected_clients.append((client_socket, addr))
        elif message_type == "draw":
            # Broadcast drawing updates to other clients
            broadcast_message = ("drawing", message[1])
            whiteboard.draw(message[1][0], message[1][1], message[1][2], message[1][3])

            send_to_all_clients(broadcast_message)
    # Remove user when they disconnect
    connected_clients.remove((client_socket, addr))

    client_socket.close()



def send_whiteboard_state_to_client(client_socket, whiteboard):
    temp_file_path = "temp_whiteboard.png"

    # Save the whiteboard image
    whiteboard.save_picture_path(temp_file_path)

    with open(temp_file_path, "rb") as file:
        # Read the image file as binary data
        image_data = file.read()
        # Send the image size to the client
        client_socket.sendall(len(image_data).to_bytes(4, byteorder="big"))
        # Send the image data to the client
        client_socket.sendall(image_data)

    # Read the image file as binary data
    '''with open(temp_file_path, "rb") as file:
        chunk_size = 1024  # Set an appropriate chunk size
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            # Send each chunk with size information
            send_data_with_size(client_socket, chunk)

    # Send an empty chunk to indicate the end of data
    send_data_with_size(client_socket, b"")'''

    # Remove the temporary file
    os.remove(temp_file_path)

def send_data_with_size(client_socket, data):
    data_size = len(data)
    size_data = struct.pack("!I", data_size)
    client_socket.sendall(size_data)
    client_socket.sendall(data)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 5555))
    server.listen(5)
    print("Server listening on port 5555")

    server_whiteboard = white_lib.WhiteboardApp()
    server_whiteboard.initialize(False)

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client, addr, server_whiteboard))
        client_handler.start()


if __name__ == "__main__":
    start_server()
