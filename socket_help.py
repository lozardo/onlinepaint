import pickle
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

def encrypt(aes_key, aes_iv, data):
    """
    Encrypts data using AES in CBC mode.
    Parameters:
        aes_key (bytes): The AES key.
        aes_iv (bytes): The AES initialization vector.
        data (bytes): The data to be encrypted.
    Returns:
        bytes: The encrypted data.
    """
    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    padded_plaintext = pad(data, AES.block_size)
    encrypted_message = aes_cipher.encrypt(padded_plaintext)
    return encrypted_message

def receive_encrypted_message(sock, aes_key, aes_iv, pickled=True):
    """
    Receives and decrypts an encrypted message from the socket.
    Parameters:
        sock (socket.socket): The socket to receive data from.
        aes_key (bytes): The AES key.
        aes_iv (bytes): The AES initialization vector.
        pickled (bool): If True, unpickle the decrypted data.
    Returns:
        Any: The decrypted message.
    """
    data_size = recvall(sock, 4)
    encrypted_data = recvall(sock, int.from_bytes(data_size, byteorder='big'))

    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    decrypted_data = aes_cipher.decrypt(encrypted_data)
    message = unpad(decrypted_data, AES.block_size)
    if message:
        if pickled:
            message = pickle.loads(message)
        print(message)
        return message
    return None

def recvall(sock, size):
    """
    Ensures all bytes of a message are received from the socket.
    Parameters:
        sock (socket.socket): The socket to receive data from.
        size (int): The total number of bytes to receive.
    Returns:
        bytes: The received data.
    """
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None  # Connection is closed
        data += packet
    return data

def send_message(socket, aes_key, aes_iv, message):
    """
    Encrypts and sends a message over the socket.
    Parameters:
        socket (socket.socket): The socket to send data through.
        aes_key (bytes): The AES key.
        aes_iv (bytes): The AES initialization vector.
        message (Any): The message to be sent.
    """
    pickled_message = pickle.dumps(message)
    encrypted_message = encrypt(aes_key, aes_iv, pickled_message)
    socket.sendall(len(encrypted_message).to_bytes(4, byteorder="big") + encrypted_message)
