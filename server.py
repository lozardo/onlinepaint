import os
import socket
import sqlite3
import string
import struct
import threading
import pickle
import random

import pygame
from Crypto.Util.Padding import unpad, pad

import white_lib

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES

connected_clients = {}  # Dictionary to store connected clients for each whiteboard
lock = threading.Lock()
private_key = ''
public_key = ''

def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None  # close connection
        data += packet
    return data


def generate_rsa_key_pair():
    # Generate RSA key pair
    global public_key
    global private_key
    key = RSA.generate(2048)

    # Get the private key
    private_key = key.export_key()

    # Get the public key
    public_key = key.publickey().export_key()

    return private_key, public_key


def send_public_key(client_socket):
    # Generate RSA key pair
    client_socket.sendall(len(public_key).to_bytes(4, byteorder='big'))  # Send size of public key
    client_socket.sendall(public_key)


def decrypt_aes_key(encrypted_aes_key, encrypted_iv):
    cipher = PKCS1_OAEP.new(RSA.import_key(private_key))
    aes_key = cipher.decrypt(encrypted_aes_key)
    iv = cipher.decrypt(encrypted_iv)
    aes_info = (aes_key, iv)
    return aes_info


def receive_encrypted_message(sock, aes_info):
    data_size = recvall(sock, 4)
    encrypted_data = recvall(sock, int.from_bytes(data_size, byteorder='big'))

    aes_cipher = AES.new(aes_info[0], AES.MODE_CBC, aes_info[1])
    decrypted_data = aes_cipher.decrypt(encrypted_data)
    plaintext = unpad(decrypted_data, AES.block_size)

    return plaintext


def encrypt(aes_info, data):
    print(aes_info)
    aes_cipher = AES.new(aes_info[0], AES.MODE_CBC, aes_info[1])
    padded_plaintext = pad(data, AES.block_size)
    encrypted_message = aes_cipher.encrypt(padded_plaintext)
    return encrypted_message

def generate_unique_whiteboard_id():
    # Generate a random alphanumeric ID of length 6
    id_length = 6
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=id_length))
        # Check if the ID already exists in the database
        if not whiteboard_exists_in_db(new_id):
            return new_id


def send_to_all_clients(message, whiteboard_id):
    with lock:
        for client_socket, addr, username, aes_info in connected_clients[whiteboard_id]:
            #try:
            print(f"{addr}")
            send_to_client(client_socket, aes_info, message)
            #except Exception as e:
            #    print(f"Error sending message to {client_addr}: {e}")
                #client_socket.sendall(pickle.dumps(message))


def send_to_client(client_socket, aes_info, message):
    pickled_message = pickle.dumps(message)
    encrypted_message = encrypt(aes_info, pickled_message)
    client_socket.sendall(len(encrypted_message).to_bytes(4, byteorder="big") + encrypted_message)


def handle_client(client_socket, addr):
    send_public_key(client_socket)

    data_size = recvall(client_socket, 4)
    data = recvall(client_socket, int.from_bytes(data_size, byteorder='big'))
    enc_aes_info = pickle.loads(data)
    aes_info = decrypt_aes_key(enc_aes_info[0], enc_aes_info[1])
    print(aes_info)
    print('a')
    username = ""
    try:
        while True:
            data = receive_encrypted_message(client_socket, aes_info)
            if data:
                message = pickle.loads(data)
                print(f"{addr}: {message}")
                message_type = message[0]

                if message_type == 'sign':
                    print("sign")
                    register_result = register_client(message[1])
                    send_to_client(client_socket, aes_info, (register_result, ''))
                    if register_result:
                        username = message[1][0]
                        break

                if message_type == 'log':
                    print("log")
                    register_result = authenticate_client(message[1])
                    send_to_client(client_socket, aes_info, (register_result, ''))
                    if register_result:
                        username = message[1][0]
                        #whiteboard_ids = get_user_whiteboard_ids(username)
                        break

        client_stuff = (client_socket, addr, username, aes_info)

        while True:
            data = receive_encrypted_message(client_socket, aes_info)
            if data:
                message = pickle.loads(data)
                print(f"{addr}: {message}")
                message_type = message[0]

                if message_type == "join":
                    whiteboard_id = message[1]

                    if not whiteboard_exists_in_db(whiteboard_id):
                        # return false for not existing
                        send_to_client(client_socket, aes_info, (False, -1))

                    else:
                        if whiteboard_id not in whiteboards:
                            print("redo")
                            whiteboards[whiteboard_id] = white_lib.WhiteboardApp()
                            whiteboards[whiteboard_id].initialize(False)
                            whiteboards[whiteboard_id].set_image(f"whiteboard_{whiteboard_id}.bmp")

                        else:
                            try:
                                connected_clients[whiteboard_id].append(client_stuff)

                            except Exception as e:
                                print(e)
                                connected_clients[whiteboard_id] = [client_stuff]

                        send_to_client(client_socket, aes_info, (True, whiteboard_id))

                elif message_type == "create":
                    # Generate a unique whiteboard ID
                    new_whiteboard_id = generate_unique_whiteboard_id()
                    # Create the whiteboard
                    whiteboards[new_whiteboard_id] = white_lib.WhiteboardApp()
                    whiteboards[new_whiteboard_id].initialize(False)
                    # Add the whiteboard to the database
                    create_whiteboard(new_whiteboard_id, username)
                    # Send the new whiteboard ID to the client
                    print("sending whiteboard ID")
                    send_to_client(client_socket, aes_info, (True, new_whiteboard_id))
                    print("sent")
                    # Join the user to the newly created whiteboard
                    connected_clients[new_whiteboard_id] = [client_stuff]
                    update_user_whiteboard_ids(username, new_whiteboard_id)
                    whiteboard_id = new_whiteboard_id

                elif message_type == "draw":
                    # Broadcast drawing updates to other clients
                    broadcast_message = ("drawing", message[1])
                    whiteboards[whiteboard_id].draw(message[1][0], message[1][1], message[1][2], message[1][3])

                    send_to_all_clients(broadcast_message, whiteboard_id)

                elif message_type == "img":
                    send_whiteboard_state_to_client(client_socket, aes_info, whiteboard_id)
                
                elif message_type == "save":
                    whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.bmp")

    except Exception as e:
        print(e)
        print(f"{client_stuff} left board {whiteboard_id}")
        whiteboards[whiteboard_id].save_picture_path(f"whiteboard_{whiteboard_id}.bmp")
        connected_clients[whiteboard_id].remove((client_socket, addr))
        # Remove the whiteboard ID from the user's record when they leave
        remove_user_whiteboard_id(username, whiteboard_id)
        client_socket.close()


def send_whiteboard_state_to_client(client_socket, aes_info, whiteboard_id):
    file_path = f"whiteboard_{whiteboard_id}.bmp"

    # Save the whiteboard image
    whiteboards[whiteboard_id].save_picture_path(file_path)

    send_to_client(client_socket, aes_info, ("img", ''))
    print("ready")
    with open(file_path, "rb") as file:
        # Read the image file as binary data
        image_data = file.read()
        enc_img = encrypt(aes_info, image_data)

        # Send the image size to the client
        client_socket.sendall(len(enc_img).to_bytes(4, byteorder="big"))
        # Send the image data to the client
        client_socket.sendall(enc_img)
        print("sent")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 5555))
    server.listen(5)
    print("Server listening on port 5040")

    private_key, public_key = generate_rsa_key_pair()
    print(private_key.decode())
    print(public_key.decode())

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr}")

        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()


def update_user_whiteboard_ids(username, whiteboard_id):
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


def remove_user_whiteboard_id(username, whiteboard_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT whiteboard_ids FROM users WHERE username=?", (username,))
    user_record = cursor.fetchone()
    if user_record:
        whiteboard_ids = set(user_record[0].split(',')) if user_record[0] else set()
        if whiteboard_id in whiteboard_ids:
            whiteboard_ids.remove(whiteboard_id)
            new_whiteboard_ids = ','.join(whiteboard_ids)
            cursor.execute("UPDATE users SET whiteboard_ids=? WHERE username=?", (new_whiteboard_ids, username))
            conn.commit()
    conn.close()


def get_user_whiteboard_ids(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT whiteboard_ids FROM users WHERE username=?", (username,))
    user_record = cursor.fetchone()
    conn.close()
    if user_record:
        return set(user_record[0].split(',')) if user_record[0] else set()
    else:
        return set()


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


def create_whiteboard(whiteboard_id, creator_username):
    conn = sqlite3.connect('whiteboards.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO whiteboards (ID, creator) VALUES (?, ?)",
                   (whiteboard_id, creator_username))
    conn.commit()
    conn.close()


def whiteboard_exists_in_db(whiteboard_id):
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

    # Create users table if it does not exist
    cursor_users.execute('''CREATE TABLE IF NOT EXISTS users (
                                username TEXT PRIMARY KEY,
                                password TEXT,
                                whiteboard_ids TEXT
                            )''')
    conn_users.commit()
    conn_users.close()

    conn_whiteboards = sqlite3.connect('whiteboards.db')
    cursor_whiteboards = conn_whiteboards.cursor()

    # Create whiteboards table if it does not exist
    cursor_whiteboards.execute('''CREATE TABLE IF NOT EXISTS whiteboards (
                                    ID TEXT PRIMARY KEY,
                                    creator TEXT
                                )''')
    conn_whiteboards.commit()
    conn_whiteboards.close()

    start_server()
