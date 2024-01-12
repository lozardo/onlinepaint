import socket
import threading
import pickle

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


def handle_client(client_socket, addr):
    while True:
        data = client_socket.recv(1024)
        message = pickle.loads(data)
        print(f"{addr}: {message}")
        message_type = message[0]

        if message_type == "join":
            connected_clients.append((client_socket, addr))
        elif message_type == "draw":
            # Broadcast drawing updates to other clients
            broadcast_message = ("drawing", message[1])

            send_to_all_clients(broadcast_message)
    # Remove user when they disconnect
    connected_clients.remove((client_socket, addr))

    client_socket.close()


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
