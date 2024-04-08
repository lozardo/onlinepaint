import os
import socket
import struct
from tkinter import ttk
import tkinter as tk
from tkinter.ttk import *
from tkinter import simpledialog
import pygame_widgets
from white_lib import WhiteboardApp
import pickle
import pygame
import sys
import threading
# import pygame_textinput
from pygame_widgets.slider import Slider
from pygame_widgets.button import Button


class ClientApp(WhiteboardApp):
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.username = ''
        self.ID = ''
        # Connect to the server
        server_address = ("192.168.1.23", 5555)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(server_address)
        # Get credentials from the user
        if self.get_credentials():
            self.run()
        # Initialize the whiteboard

    def recvall(self, sock, size):
        data = b''
        while len(data) < size:
            packet = sock.recv(size - len(data))
            if not packet:
                return None #close connection
            data += packet
        return data

    def receive_image(self):
        # Receive the image size from the server
        image_size_data = self.recvall(self.client_socket, 4)
        image_size = int.from_bytes(image_size_data, byteorder="big")
        # Receive the image data from the server
        image_data = self.recvall(self.client_socket, image_size)
        print(image_data)
        print("AAAAAAAAAAAAA")
        return image_data

    def receive_messages(self):
        while True:
            try:
                print("rcving")
                data_size = self.recvall(self.client_socket, 4)
                data = self.recvall(self.client_socket, int.from_bytes(data_size, byteorder='big'))
                print("a")
                if data:
                    message = pickle.loads(data)
                    print(message)
                    if message[0] == 'drawing':
                        self.draw(message[1][0], message[1][1], message[1][2], message[1][3])
                    if message[0] == 'img':
                        self.initialize_whiteboard_with_image(self.receive_image())

                    print(f"Received message from server: {message}")
            except Exception as e:
                print(f"Error receiving data from server: {e}")

    def receive_message(self):
        try:
            print("rcving 1")
            data_size = self.client_socket.recv(4)
            data = self.client_socket.recv(int.from_bytes(data_size, byteorder='big'))
            if data:
                message = pickle.loads(data)
                print(f"Received message from server: {message}")
                return message
        except Exception as e:
            print(f"Error receiving data from server: {e}")

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

    def send_action(self, action_type, data=''):
        action = (action_type, data)
        try:
            pickled_message = pickle.dumps(action)
            self.client_socket.sendall(len(pickled_message).to_bytes(4, byteorder="big") + pickled_message)

        except:
            print(f"Error sending data to server")

    def run(self):
        self.create_or_join()
        while True:
            message = self.receive_message()
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
        self.send_action("img")

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
                    self.send_action("width", int(self.width_slider.getValue()))
                # Handle button events
                self.save_button.listen(event)
            self.draw_toolbar()
            self.draw_bottom_toolbar()
            if len(self.points) > 0:
                self.send_action("draw", (self.points, self.draw_color, self.line_width, self.last_circle_position))
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
            self.send_action("log", credentials)
            message = self.receive_message()
            if message == False:
                self.popup_notice("Username or password incorrect")
            self.return_input = message

        def signup():
            username = username_entry.get()
            password = password_entry.get()
            if len(password) < 6:
                password_req_label.config(text="Password must be at least 6 characters", fg="red")
                return
            credentials = (username, password)
            dialog.destroy()
            self.username = credentials[0]
            self.send_action("sign", credentials)
            message = self.receive_message()
            if message == False:
                self.popup_notice("Username already exists or password is too short")
            self.return_input = message

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
                self.send_action("join", self.ID)
            else:
                # Handle case where no ID is entered (optional)
                print("Please enter a whiteboard ID.")

        # Join button to the left of the textbox
        join_button = tk.Button(dialog, text="Join Whiteboard", command=join_whiteboard, font=default_font, padx=20,
                                pady=10)
        join_button.grid(row=1, column=0, sticky="e", padx=20)  # Place to the right (east) in row 1

        def create_whiteboard():
            dialog.destroy()
            self.send_action("create")

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
