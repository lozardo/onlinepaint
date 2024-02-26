import os
import socket
import struct
import tkinter as tk
from tkinter import simpledialog
import pygame_widgets
from pygame.examples.textinput import TextInput

from white_lib import WhiteboardApp
import pickle
import pygame
import sys
import threading

from pygame_widgets.slider import Slider
from pygame_widgets.button import Button
from pygame_widgets.textbox import TextBox

class ClientApp(WhiteboardApp):
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.username = ''
        self.whiteboard_id = ''
        # Connect to the server
        server_address = ("127.0.0.1", 5555)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(server_address)

        # Get credentials from the user
        while not self.get_credentials():
            pass
        while not self.get_id():
            pass

        # Initialize the whiteboard
        self.initialize(True)

        self.run()

    def receive_image(self):
        # Receive the image size from the server
        image_size_data = self.client_socket.recv(4)
        image_size = int.from_bytes(image_size_data, byteorder="big")
        # Receive the image data from the server
        image_data = self.client_socket.recv(image_size)

        return image_data

    def receive_messages(self):
        image = self.receive_image()

        self.initialize_whiteboard_with_image(image)
        print(f"Received message from server: {image}")

        while True:
            try:
                data_size = self.client_socket.recv(4)
                data = self.client_socket.recv(int.from_bytes(data_size, byteorder='big'))
                print("a")
                if data:
                    message = pickle.loads(data)
                    if message[0] == 'drawing':
                        self.draw(message[1][0], message[1][1], message[1][2], message[1][3])
                    print(f"Received message from server: {message}")
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

    def send_action(self, action_type, data):
        drawing_action = (action_type, data)
        try:
            pickled_message = pickle.dumps(drawing_action)
            self.client_socket.sendall(len(pickled_message).to_bytes(4, byteorder="big") + pickled_message)

        except:
            print(f"Error sending data to server")

    def run(self):
        self.screen.fill((255, 255, 255))  # White background
        self.send_action("join", self.whiteboard_id)
        threading.Thread(target=self.receive_messages).start()
        while True:
            events = pygame.event.get()
            pygame_widgets.update(events)
            pygame.display.update()
            for event in events:
                if event.type == pygame.QUIT:
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
        # Pygame setup
        screen_width, screen_height = 800, 600
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Login")
        username = ""
        pw = ""
        action = ""
        # Fonts
        font = pygame.font.Font(None, 36)
        # Text input fields
        username_textbox = TextBox(screen, screen_width // 2 - 100, screen_height // 2 - 50, 200, 40,
                                   fontSize=36)
        password_textbox = TextBox(screen, screen_width // 2 - 100, screen_height // 2 + 50, 200, 40,
                                                  fontSize=36, password=True, textColour=(0, 200, 0))
        login_button = Button(screen, screen_width // 2 + 100, screen_height // 2 + 120, 100, 40, text="log in", inactiveColour=(200, 50, 0), hoverColour=(150, 0, 0), pressedColour=(0, 200, 20))

        sign_button = Button(screen, screen_width // 2 - 200, screen_height // 2 + 120, 100, 40, text="sign up", onClick=end_run, inactiveColour=(200, 50, 0), hoverColour=(150, 0, 0), pressedColour=(0, 200, 20))
#need to make it send info to server and pop up a window on a correct response, if its fine close this. HOW THE FUCK!??!?!?!?!
        run = True
        while run:
            screen.fill((200, 200, 200))

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                    break

            # Update text inputs
            pygame_widgets.update(events)
            pygame.display.update()
            username = username_textbox.getText()
            pw = password_textbox.getText()

        print(username)
        print(pw)

    def get_id(self):
        # Initialize Pygame
        pygame.init()

        # Set up the screen
        screen_width = 800
        screen_height = 600
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Whiteboard Setup")

        # Set up fonts
        font = pygame.font.SysFont(None, 40)

        create_button = pygame_widgets.Button(
            screen, 200, 200, 400, 50, text="Create Whiteboard", fontSize=30, margin=20, inactiveColour=(200, 200, 200),
            pressedColour=(150, 150, 150), onClick=self.create_whiteboard
        )

        join_button = pygame_widgets.Button(
            screen, 200, 300, 400, 50, text="Join Existing Whiteboard", fontSize=30, margin=20,
            inactiveColour=(200, 200, 200),
            pressedColour=(150, 150, 150), onClick=self.join_existing_whiteboard
        )

        running = True
        while running:
            screen.fill((255, 255, 255))

            create_button.listen(pygame.event.get())
            join_button.listen(pygame.event.get())

            create_button.draw()
            join_button.draw()

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

        pygame.quit()

    def create_whiteboard(self, private):
        # Create a dialog to get the whiteboard ID
        dialog = tk.Toplevel()
        dialog.title("Create Whiteboard")

        if private:
            tk.Label(dialog, text="Enter password for private whiteboard:").pack()
            password_entry = tk.Entry(dialog, show="*")
            password_entry.pack()

        def submit():
            dialog.destroy()
            password = password_entry.get() if private else None
            self.send_action(("create", password))

        submit_button = tk.Button(dialog, text="Submit", command=submit)
        submit_button.pack()

    def join_existing_whiteboard(self):
        # Create a dialog to get the whiteboard ID
        dialog = tk.Toplevel()
        dialog.title("Join Whiteboard")

        tk.Label(dialog, text="Enter whiteboard ID:").pack()
        id_entry = tk.Entry(dialog)
        id_entry.pack()

        def submit():
            dialog.destroy()
            self.whiteboard_id = ("join", id_entry.get())
            self.send_action(*self.whiteboard_id)

        submit_button = tk.Button(dialog, text="Submit", command=submit)
        submit_button.pack()





if __name__ == "__main__":
    app = ClientApp()
