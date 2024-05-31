import os
import pickle
import socket
import tkinter as tk
import pygame_widgets
import rsa
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

from white_lib import WhiteboardApp

import pygame
import sys
import threading
from Crypto.Cipher import PKCS1_OAEP

import socket_help

# Generate AES key
def generate_aes_key():
    return os.urandom(32)  # 256-bit key for AES-256

# Encrypt AES key using RSA public key
def encrypt_aes_key(aes_key, rsa_public_key):
    # Create an RSA public key object from the provided key bytes
    rsa_key = RSA.import_key(rsa_public_key)

    # Create an RSA cipher object for encryption
    rsa_cipher = PKCS1_OAEP.new(rsa_key)

    # Encrypt the AES key using the RSA public key
    encrypted_aes_key = rsa_cipher.encrypt(aes_key)

    return encrypted_aes_key

# Decrypt AES key using RSA private key
def decrypt_aes_key(encrypted_aes_key, rsa_private_key):
    decrypted_aes_key = rsa.decrypt(encrypted_aes_key, rsa_private_key)
    return decrypted_aes_key



class ClientApp(WhiteboardApp):
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.username = ''
        self.ID = ''
        self.server_public_key = None
        self.aes_key = ''
        self.iv = ''
        # Connect to the server
        server_address = ("127.0.0.1", 5555)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(server_address)
        # Get credentials from the user
        self.run()

    def receive_messages(self):
        while True:
            try:
                print("rcving")
                message = socket_help.receive_encrypted_message(self.client_socket,self.aes_key, self.iv)
                print("a")
                print(message)
                if message[0] == 'drawing':
                    self.draw(message[1][0], message[1][1], message[1][2], message[1][3])
                if message[0] == 'img':
                    image_data = socket_help.receive_encrypted_message(self.client_socket,self.aes_key, self.iv, False)
                    print(image_data)
                    self.initialize_whiteboard_with_image(image_data)

                    print(f"Received message from server: {message}")
            except Exception as e:
                print(f"Error receiving data from server: {e}")

    def receive_server_public_key(self):
        try:
            data_size = socket_help.recvall(self.client_socket, 4)
            server_public_key_pem = socket_help.recvall(self.client_socket, int.from_bytes(data_size, byteorder='big'))
            self.server_public_key = server_public_key_pem
            print("Received server's public key")
        except Exception as e:
            print(f"Error receiving server's public key: {e}")

    def initialize_whiteboard_with_image(self, image_data):
        # Create a temporary file to save the received whiteboard image
        temp_file_path = "temp_received_whiteboard.png"
        # Write the image data to the temporary file
        with open(temp_file_path, "wb") as file:
            file.write(image_data)
        # Load the image and set it as the background
        self.set_image(temp_file_path)
        # Remove the temporary file
        pygame.time.wait(1000)  # Wait for 1 second to ensure the file is closed
        pygame.display.flip()
        os.remove(temp_file_path)

    def update_image_with_chunk(self, chunk):
        # Assuming self.image is a pygame.Surface representing your whiteboard image
        if not hasattr(self, 'image'):
            # Load the initial image when it's received
            self.image = pygame.image.load(chunk)
        else:
            # Update the image with additional chunks
            self.image.blit(pygame.image.load(chunk), (0, 0))
        # Redraw the entire screen with the updated image
        self.screen.fill((255, 255, 255))
        self.screen.blit(self.image, (0, 0))
        pygame.display.flip()

    def run(self):
        self.receive_server_public_key()
        print(self.server_public_key)
        print("a")
        self.aes_key = get_random_bytes(32)
        self.iv = get_random_bytes(16)

        cipher = PKCS1_OAEP.new(RSA.import_key(self.server_public_key))
        encrypted_aes_key = cipher.encrypt(self.aes_key)
        encrypted_iv = cipher.encrypt(self.iv)
        aes_info = (encrypted_aes_key, encrypted_iv)
        message = pickle.dumps(aes_info)
        self.client_socket.sendall(len(message).to_bytes(4, byteorder="big") + message)

        print(self.aes_key)

        while not self.get_credentials():
            pass
        self.create_or_join()
        while True:
            message = socket_help.receive_encrypted_message(self.client_socket, self.aes_key, self.iv)
            if message:
                if not message[0]:  # false if cant join
                    self.popup_notice("whiteboard doesnt exist")
                    self.create_or_join()
                else:
                    self.ID = message[1]
                    break
        print(message[1])



        print(self.ID)
        self.initialize(True, self.ID)
        self.draw_toolbar()
        self.draw_bottom_toolbar()
        print(self.screen)
        message = ("img", '')
        socket_help.send_message(self.client_socket, self.aes_key, self.iv,message)

        recv_thread = threading.Thread(target=self.receive_messages)
        recv_thread.start()

        while True:
            events = pygame.event.get()
            pygame_widgets.update(events)
            pygame.display.update()
            for event in events:
                if event.type == pygame.QUIT:
                    recv_thread.join(1)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # Check if clicked on a color button
                        for i, color_button in enumerate(self.color_buttons):
                            color_button.listen(event)  # Use listen method
                            if color_button.clicked:
                                self.change_color(i)
                                break
                        else:
                            self.drawing = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.drawing = False
                    self.points = []
                elif event.type == pygame.MOUSEMOTION:
                    if self.drawing and event.pos[1] > self.toolbar_height:
                        if len(self.points) > 1:
                            self.points = [self.points[-1], event.pos]
                        else:
                            self.points = [event.pos]
                # Handle slider events
                if self.line_width != int(self.width_slider.getValue()):
                    self.line_width = int(self.width_slider.getValue())
                # Handle button events
                self.save_button.listen(event)
            self.draw_toolbar()
            self.draw_bottom_toolbar()
            if len(self.points) > 0:
                message = ("draw", (self.points, self.draw_color, self.line_width, self.last_circle_position))
                socket_help.send_message(self.client_socket, self.aes_key, self.iv,message)
                print(self.points)
                # self.draw(self.points, self.draw_color, self.line_width, self.last_circle_position)
                self.last_circle_position = self.points[-1]
            if not self.drawing:
                self.last_circle_position = None
            pygame.display.flip()
            self.clock.tick(60)

    def get_credentials(self):
        # Get credentials from the user and send them to the server
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        self.return_input = False

        # Create a login dialog
        dialog = tk.Toplevel(root)
        dialog.title("Login")
        dialog.geometry("600x400")  # Set the window size

        # Increase font size for better readability
        default_font = ("Arial", 14)

        # Background color
        dialog.configure(bg="#f5f5f5")

        # Grid layout with spacing
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=2)
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        dialog.grid_rowconfigure(2, weight=1)
        dialog.grid_rowconfigure(3, weight=1)

        # Labels
        username_label = tk.Label(dialog, text="Username:", font=default_font)
        username_label.grid(row=0, column=0, sticky="e", padx=10, pady=10)
        password_label = tk.Label(dialog, text="Password:", font=default_font)
        password_label.grid(row=1, column=0, sticky="e", padx=10, pady=10)

        # Entries
        username_entry = tk.Entry(dialog, font=default_font)
        username_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        password_entry = tk.Entry(dialog, show="*", font=default_font)
        password_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Password requirements label (red for emphasis)
        password_req_label = tk.Label(dialog, text="Password must be at least 6 characters", fg="red",
                                      font=default_font)
        password_req_label.grid(row=2, column=1, padx=0, pady=5, sticky="w")

        # Functions for login and signup
        def login():
            username = username_entry.get()
            password = password_entry.get()
            credentials = (username, password)
            dialog.destroy()
            self.username = credentials[0]
            message = ("log", credentials)
            socket_help.send_message(self.client_socket, self.aes_key, self.iv, message)
            confirmation = socket_help.receive_encrypted_message(self.client_socket, self.aes_key, self.iv)[0]
            if confirmation == False:
                self.popup_notice("Username or password incorrect")
            self.return_input = confirmation

        def signup():
            username = username_entry.get()
            password = password_entry.get()
            if len(password) < 6:
                password_req_label.config(text="Password must be at least 6 characters", fg="red")
                return
            credentials = (username, password)
            dialog.destroy()
            self.username = credentials[0]
            message = ("sign", credentials)
            socket_help.send_message(self.client_socket, self.aes_key, self.iv, message)
            confirmation = socket_help.receive_encrypted_message(self.client_socket, self.aes_key, self.iv)[0]
            if confirmation == False:
                self.popup_notice("Username already exists or password is too short")
            self.return_input = confirmation

        # Buttons with adjusted padding
        login_button = tk.Button(dialog, text="Login", command=login, font=default_font, padx=20, pady=10)
        signup_button = tk.Button(dialog, text="Sign Up", command=signup, font=default_font, padx=20, pady=10)

        login_button.grid(row=3, column=0, sticky="e", padx=40, pady=10)
        signup_button.grid(row=3, column=1, sticky="w", padx=60, pady=10)

        root.wait_window(dialog)
        return self.return_input  # False if return input exists, otherwise True

    def create_or_join(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        # Create a dialog
        dialog = tk.Toplevel(root)
        dialog.title("Whiteboard Setup")
        dialog.geometry("600x800")  # Set the window size

        # Increase font sizes for better readability
        default_font = ("Arial", 16)
        label_font = (default_font[0], default_font[1] + 2)  # Slightly larger for label

        # Background color
        dialog.configure(bg="#f5f5f5")

        # Grid layout with 2 rows and 1 column
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=2)

        # Label (optional)
        label = tk.Label(dialog, text="Whiteboard ID:", font=label_font)
        label.grid(row=0, column=0, pady=20)  # Place label in row 0

        # Textbox for input (limited to 6 characters)
        whiteboard_id_entry = tk.Entry(dialog, font=("Arial", 20), width=7)
        whiteboard_id_entry.grid(row=1, column=0, padx=20, pady=10)  # Place in row 1

        def join_whiteboard():
            whiteboard_id = whiteboard_id_entry.get()
            if whiteboard_id:  # Check if any text is entered
                dialog.destroy()
                self.ID = whiteboard_id
                message = ("join", self.ID)
                socket_help.send_message(self.client_socket, self.aes_key, self.iv, message)
            else:
                # Handle case where no ID is entered (optional)
                print("Please enter a whiteboard ID.")

        # Join button to the left of the textbox
        join_button = tk.Button(dialog, text="Join Whiteboard", command=join_whiteboard, font=default_font, padx=20,
                                pady=10)
        join_button.grid(row=1, column=0, sticky="e", padx=20)  # Place to the right (east) in row 1

        def create_whiteboard():
            dialog.destroy()
            message = ("create", '')
            socket_help.send_message(self.client_socket, self.aes_key, self.iv, message)

        # Create Button above the textbox and join button
        create_button = tk.Button(dialog, text="Create New Whiteboard", command=create_whiteboard, font=default_font,
                                  padx=20, pady=10)
        create_button.grid(row=0, column=0, sticky="s", pady=15)  # Place at the bottom (south) of row 0

        # Window Icon (optional)
        # dialog.iconbitmap("my_icon.ico")  # Replace with your icon file path

        root.wait_window(dialog)

    def popup_notice(self, message):
        """
        Displays a popup notification with the given message.

        Args:
            message (str): The message to display in the popup.
        """

        root = tk.Tk()
        root.withdraw()  # Hide the main window

        # Create a popup window
        popup = tk.Toplevel(root)
        popup.title("Notification")

        # Set window size and background color
        popup.geometry("300x150")
        popup.configure(bg="#f5f5f5")

        # Frame for message and buttons (optional for better organization)
        message_frame = tk.Frame(popup, bg="#f5f5f5")
        message_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Message label with increased font size and padding
        message_label = tk.Label(message_frame, text=message, font=("Arial", 16), wraplength=250, justify="center")
        message_label.pack(padx=20, pady=20)

        # Button with adjusted padding and slightly bigger font
        dismiss_button = tk.Button(message_frame, text="Dismiss", font=("Arial", 14), command=popup.destroy, padx=25,
                                   pady=10)
        dismiss_button.pack()

        root.wait_window(popup)


if __name__ == "__main__":
    app = ClientApp()
