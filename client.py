import os
import socket
import struct
import tkinter as tk
from tkinter import simpledialog
import pygame_widgets

from white_lib import WhiteboardApp
import pickle
import pygame
import sys
import threading
import pygame_textinput
from pygame_widgets.slider import Slider
from pygame_widgets.button import Button


class ClientApp(WhiteboardApp):
    def __init__(self):
        self.whiteboard_id = get_id()
        # Initialize pygame after obtaining the ID
        pygame.init()

        # Connect to the server
        server_address = ("127.0.0.1", 5555)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(server_address)
        self.initialize(True)


    def receive_image(self):
        # Receive the image size from the server
        image_size_data = self.client_socket.recv(4)
        image_size = int.from_bytes(image_size_data, byteorder="big")
        # Receive the image data from the server
        image_data = self.client_socket.recv(image_size)

        return image_data


    def receive_messages(self):
        getting_whiteboard_state = True
        image = self.receive_image()

        self.initialize_whiteboard_with_image(image)
        print(f"Received message from server: {image}")

        data = self.client_socket.recv(1024)
        while True:
            print("b")
            if data:
                message = pickle.loads(data)
                print(f"Received message from server: {message}")
            try:
                data = self.client_socket.recv(1024)
                print("a")
                if data:
                    message = pickle.loads(data)
                    if message[0] == 'drawing':
                        self.draw(message[1][0], message[1][1], message[1][2], message[1][3])
                    print(f"Received message from server: {message}")
            except Exception as e:
                print(f"Error receiving data from server: {e}")

            #except Exception as e:
            #    print(f"Error receiving data from server: {e}")

    def initialize_whiteboard_with_image(self, image_data):
        # Create a temporary file to save the received whiteboard image
        temp_file_path = "temp_received_whiteboard.png"

        # Write the image data to the temporary file
        with open(temp_file_path, "wb") as file:
            file.write(image_data)

        # Load the image and set it as the background
        background_image = pygame.image.load(temp_file_path)
        self.screen.blit(background_image, (0, 0))
        pygame.display.flip()

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
            self.client_socket.sendall(pickle.dumps(drawing_action))
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


def get_id():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Create a simple dialog to get the ID
    id = simpledialog.askstring("Whiteboard ID", "Enter the whiteboard ID:")
    return id

if __name__ == "__main__":
    app = ClientApp()
    app.run()
