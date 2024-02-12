import os
import socket
import sqlite3
import struct
import threading
import pickle

import white_lib

connected_clients = {}  # Dictionary to store connected clients for each whiteboard
lock = threading.Lock()


def send_to_all_clients(message, whiteboard_id):
    with lock:
        for client_socket, client_addr in connected_clients[whiteboard_id]:
            try:
                print(f"{client_addr}")
                pickled_message = pickle.dumps(message)
                client_socket.sendall(len(pickled_message).to_bytes(4, byteorder="big")+pickled_message)
            except Exception as e:
                print(f"Error sending message to {client_addr}: {e}")
                #client_socket.sendall(pickle.dumps(message))


def handle_client(client_socket, addr):
    username = ""
    whiteboard_id = -1
    try:
        while True:
            data = client_socket.recv(1024)
            if data:
                message = pickle.loads(data)
                print(f"{addr}: {message}")
                message_type = message[0]

                if message_type == 'sign':
                    print("sign")
                    register_result = register_client(message[1])
                    client_socket.sendall(pickle.dumps((register_result)))
                    if register_result:
                        username = message[1][0]
                        break

                if message_type == 'log':
                    print("log")
                    register_result = authenticate_client(message[1])
                    client_socket.sendall(pickle.dumps((register_result)))
                    if register_result:
                        username = message[1][0]
                        break

        while True:
            data = client_socket.recv(1024)
            if data:
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

    except Exception as e:
        print(f"{username} left board {whiteboard_id}")
        whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.png")
        connected_clients[whiteboard_id].remove((client_socket, addr))
        client_socket.close()


def send_whiteboard_state_to_client(client_socket, whiteboard_id):
    temp_file_path = f"whiteboard_{whiteboard_id}.png"

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
    server.bind(("192.168.0.239", 5555))
    server.listen(5)
    print("Server listening on port 5040")

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()


def register_client(credentials):
    # Extract username and password from credentials
    username, password = credentials

    # Connect to the SQLite database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Check if the username already exists
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    existing_user = cursor.fetchone()
    print(existing_user)

    if existing_user:
        print(f"Username '{username}' already exists.")
        # Inform the client that registration failed
        conn.close()
        return False

    # Insert the new user into the database
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    return True


def authenticate_client(credentials):
    # Extract username and password from credentials
    username, password = credentials

    # Connect to the SQLite database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Check if the username and password match
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()

    if user:
        print(f"Authentication successful for user '{username}'.")
        # Inform the client that authentication was successful
        conn.close()
        return True
    else:
        print(f"Authentication failed for user '{username}'.")
        # Inform the client that authentication failed
        conn.close()
        return False


if __name__ == "__main__":
    whiteboards = {}  # Dictionary to store instances of WhiteboardApp

    # Initialize the SQLite database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Create users table if it does not exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT
                    )''')
    conn.commit()
    conn.close()

    start_server()
