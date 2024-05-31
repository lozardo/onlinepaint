import pickle

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def encrypt(aes_key, aes_iv, data):
    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    padded_plaintext = pad(data, AES.block_size)
    encrypted_message = aes_cipher.encrypt(padded_plaintext)
    return encrypted_message


def receive_encrypted_message(sock, aes_key, aes_iv, pickled=True):
    data_size = recvall(sock, 4)
    encrypted_data = recvall(sock, int.from_bytes(data_size, byteorder='big'))

    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    decrypted_data = aes_cipher.decrypt(encrypted_data)
    message = unpad(decrypted_data, AES.block_size)
    if message:
        if pickled:
            message = pickle.loads(message)
        return message
    return None


def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None  # close connection
        data += packet
    return data


def send_message(socket, aes_key, aes_iv, message):
    pickled_message = pickle.dumps(message)
    encrypted_message = encrypt(aes_key, aes_iv, pickled_message)
    socket.sendall(len(encrypted_message).to_bytes(4, byteorder="big") + encrypted_message)
