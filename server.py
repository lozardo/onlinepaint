import socket
import sqlite3
import string
import threading
import pickle
import random
import bcrypt

import white_lib
import socket_help

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

connected_clients = {}  # Dictionary to store connected clients for each whiteboard
lock = threading.Lock()
private_key = None
public_key = None


def generate_rsa_key_pair():
    """
    Generates an RSA key pair.
    """
    global private_key, public_key
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    return private_key, public_key


def send_public_key(client_socket):
    """
    Sends the public RSA key to the client.
    """
    client_socket.sendall(len(public_key).to_bytes(4, byteorder='big'))
    client_socket.sendall(public_key)


def decrypt_aes_key(encrypted_aes_key, encrypted_iv):
    """
    Decrypts the AES key and IV using the server's private RSA key.
    """
    cipher = PKCS1_OAEP.new(RSA.import_key(private_key))
    aes_key = cipher.decrypt(encrypted_aes_key)
    iv = cipher.decrypt(encrypted_iv)
    return aes_key, iv


def generate_unique_whiteboard_id():
    """
    Generates a unique 6-character alphanumeric ID for a new whiteboard.
    """
    id_length = 6
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=id_length))
        if not whiteboard_exists_in_db(new_id):
            return new_id


def send_to_all_clients(message, whiteboard_id):
    """
    Sends a message to all clients connected to the specified whiteboard.
    """
    with lock:
        for client_socket, addr, username, aes_info in connected_clients.get(whiteboard_id, []):
            socket_help.send_message(client_socket, aes_info[0], aes_info[1], message)


def handle_client(client_socket, addr):
    """
    Handles communication with a connected client.
    """
    send_public_key(client_socket)
    data_size = socket_help.recvall(client_socket, 4)
    data = socket_help.recvall(client_socket, int.from_bytes(data_size, byteorder='big'))
    enc_aes_info = pickle.loads(data)
    aes_info = decrypt_aes_key(enc_aes_info[0], enc_aes_info[1])

    username = ""
    whiteboard_id = -1
    client_stuff = None

    try:
        while True:
            message = socket_help.receive_encrypted_message(client_socket, aes_info[0], aes_info[1])
            if message:
                message_type = message[0]
                if message_type == 'sign':
                    register_result = register_client(message[1])
                    socket_help.send_message(client_socket, aes_info[0], aes_info[1], (register_result, ''))
                    if register_result:
                        username = message[1][0]
                        break
                elif message_type == 'log':
                    login_result = authenticate_client(message[1])
                    socket_help.send_message(client_socket, aes_info[0], aes_info[1], (login_result, ''))
                    if login_result:
                        username = message[1][0]
                        break

        client_stuff = (client_socket, addr, username, aes_info)

        while True:
            message = socket_help.receive_encrypted_message(client_socket, aes_info[0], aes_info[1])
            if message:
                print(connected_clients)
                message_type = message[0]

                if message_type == "join":
                    whiteboard_id = message[1]
                    if not whiteboard_exists_in_db(whiteboard_id):
                        socket_help.send_message(client_socket, aes_info[0], aes_info[1], (False, -1))
                    else:
                        if whiteboard_id not in whiteboards:
                            whiteboards[whiteboard_id] = white_lib.WhiteboardApp()
                            whiteboards[whiteboard_id].initialize(False)
                            whiteboards[whiteboard_id].set_image(f"whiteboard_{whiteboard_id}.bmp")
                        with lock:
                            connected_clients.setdefault(whiteboard_id, []).append(client_stuff)
                        socket_help.send_message(client_socket, aes_info[0], aes_info[1], (True, whiteboard_id))

                elif message_type == "create":
                    new_whiteboard_id = generate_unique_whiteboard_id()
                    whiteboards[new_whiteboard_id] = white_lib.WhiteboardApp()
                    whiteboards[new_whiteboard_id].initialize(False)
                    create_whiteboard(new_whiteboard_id, username)
                    socket_help.send_message(client_socket, aes_info[0], aes_info[1], (True, new_whiteboard_id))
                    with lock:
                        connected_clients[new_whiteboard_id] = [client_stuff]
                    update_user_whiteboard_ids(username, new_whiteboard_id)
                    whiteboard_id = new_whiteboard_id

                elif message_type == "draw":
                    whiteboards[whiteboard_id].draw(*message[1])
                    send_to_all_clients(("drawing", message[1]), whiteboard_id)

                elif message_type == "img":
                    send_whiteboard_state_to_client(client_socket, aes_info, whiteboard_id)

                elif message_type == "save":
                    print(f'{whiteboard_id} is saved')
                    whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.bmp")

                elif message_type == "exit":
                    try:
                        if client_stuff and whiteboard_id in whiteboards:
                            whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.bmp")
                            print(connected_clients)
                            with lock:
                                connected_clients[whiteboard_id].remove(client_stuff)
                        socket_help.send_message(client_socket, aes_info[0], aes_info[1], ("exit", ''))
                    except:
                        pass



    except Exception as e:
        print(e)
        if client_stuff and whiteboard_id in whiteboards:
            whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.bmp")
            with lock:
                connected_clients[whiteboard_id].remove(client_stuff)
        client_socket.close()


def send_whiteboard_state_to_client(client_socket, aes_info, whiteboard_id):
    """
    Sends the current state of the whiteboard to the client.
    """
    file_path = f"whiteboard_{whiteboard_id}.bmp"
    whiteboards[whiteboard_id].save_picture_path(file_path)
    with open(file_path, "rb") as file:
        image_data = file.read()
        enc_img = socket_help.encrypt(aes_info[0], aes_info[1], image_data)
        client_socket.sendall(len(enc_img).to_bytes(4, byteorder="big"))
        client_socket.sendall(enc_img)


def start_server():
    """
    Starts the server and listens for incoming client connections.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 5555))
    server.listen(5)
    print("Server listening on port 5555")

    generate_rsa_key_pair()
    print(private_key.decode())
    print(public_key.decode())

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()


def update_user_whiteboard_ids(username, whiteboard_id):
    """
    Updates the list of whiteboards associated with a user.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT whiteboard_ids FROM users WHERE username=?", (username,))
    user_record = cursor.fetchone()
    if user_record:
        whiteboard_ids = set(user_record[0].split(',')) if user_record[0] else set()
        whiteboard_ids.add(whiteboard_id)
        new_whiteboard_ids = ','.join(whiteboard_ids)
        cursor.execute("UPDATE users SET whiteboard_ids=? WHERE username=?", (new_whiteboard_ids, username))
        conn.commit()
    conn.close()


def get_user_whiteboard_ids(username):
    """
    Retrieves the list of whiteboards associated with a user.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT whiteboard_ids FROM users WHERE username=?", (username,))
    user_record = cursor.fetchone()
    conn.close()
    if user_record:
        return set(user_record[0].split(',')) if user_record[0] else set()
    return set()


def register_client(credentials):
    """
    Registers a new user with the provided credentials.
    """
    username, password = credentials
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        print(f"Username '{username}' already exists.")
        conn.close()
        return False

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()
    return True


def authenticate_client(credentials):
    """
    Authenticates a user with the provided credentials.
    """
    username, password = credentials
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[0].encode('utf-8')):
        print(f"Authentication successful for user '{username}'.")
        conn.close()
        return True

    print(f"Authentication failed for user '{username}'.")
    conn.close()
    return False


def create_whiteboard(whiteboard_id, creator_username):
    """
    Creates a new whiteboard in the database.
    """
    conn = sqlite3.connect('whiteboards.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO whiteboards (ID, creator) VALUES (?, ?)", (whiteboard_id, creator_username))
    conn.commit()
    conn.close()


def whiteboard_exists_in_db(whiteboard_id):
    """
    Checks if a whiteboard exists in the database.
    """
    conn = sqlite3.connect('whiteboards.db')
    cursor = conn.cursor()
    cursor.execute("SELECT ID FROM whiteboards WHERE ID=?", (whiteboard_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


if __name__ == "__main__":
    whiteboards = {}  # Dictionary to store instances of WhiteboardApp

    # Initialize the SQLite databases
    conn_users = sqlite3.connect('users.db')
    cursor_users = conn_users.cursor()
    cursor_users.execute('''CREATE TABLE IF NOT EXISTS users (
                                username TEXT PRIMARY KEY,
                                password TEXT,
                                whiteboard_ids TEXT
                            )''')
    conn_users.commit()
    conn_users.close()

    conn_whiteboards = sqlite3.connect('whiteboards.db')
    cursor_whiteboards = conn_whiteboards.cursor()
    cursor_whiteboards.execute('''CREATE TABLE IF NOT EXISTS whiteboards (
                                    ID TEXT PRIMARY KEY,
                                    creator TEXT
                                )''')
    conn_whiteboards.commit()
    conn_whiteboards.close()

    start_server()
