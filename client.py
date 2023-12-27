import os
import pickle
import socket
from asyncio import events
from tkinter import filedialog  # for saving image

import pygame
import sys

import pygame_widgets
from pygame_widgets import slider, button
from pygame_widgets.slider import Slider
from pygame_widgets.button import Button

class WhiteboardApp:
    def __init__(self, width, height):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(("localhost", 5555))
        pygame.init()

        self.width = width
        self.height = height

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Whiteboard App")

        self.clock = pygame.time.Clock()

        self.setup()

    def setup(self):
        self.line_color_index = 0
        self.available_colors = [
            [(0, 0, 0), (20, 20, 20)],    # Black
            [(255, 0, 0), (240, 0, 0)],  # Red
            [(0, 255, 0), (0, 240, 0)],  # Green
            [(0, 0, 255), (0, 0, 240)],  # Blue
            [(128, 0, 128), (113, 0, 113)],  # Purple
            [(139, 69, 19), (124, 54, 4)],   # Brown
            [(0, 128, 0), (0, 113, 0)],   # Green
            [(128, 128, 128), (113, 113, 113)],  # Gray
            [(255, 255, 255), (240, 240, 240)]   # White
        ]
        self.draw_color = self.available_colors[self.line_color_index][0]

        self.line_width_options = [1, 4, 8, 12]
        self.line_width_index = 0
        self.line_width = self.line_width_options[self.line_width_index]

        self.drawing = False
        self.points = []
        self.last_circle_position = (0, 0)

        # Top toolbar
        self.toolbar_height = 40
        self.toolbar_color = (200, 200, 200)
        self.color_buttons = []

        # Creating color buttons dynamically based on available colors
        button_width = 40  # Set the width of each color button
        for i, (inactive_color, active_color) in enumerate(self.available_colors):
            color_button = Button(self.screen, i * button_width, 0, button_width, self.toolbar_height, text='',
                                  fontSize=15, inactiveColour=inactive_color,
                                  hoverColour=active_color, onClick=self.change_color, onClickParams=[i])
            self.color_buttons.append(color_button)

        # Width slider
        self.width_slider = Slider(self.screen, self.width - 200, 10, 150, 20, min=1, max=9, step=1,
                                  initial=self.line_width_options[self.line_width_index], colour=(255, 255, 255),
                                  handleColour=(0, 0, 0), handleRadius=10)

        # Bottom toolbar
        self.bottom_toolbar_height = 40
        self.save_button = Button(self.screen, self.width - 120, self.height - self.bottom_toolbar_height + 10,
                                  100, 20, text='Save', fontSize=15, margin=20, inactiveColour=(255, 255, 255),
                                  colour=(100, 100, 100), onClick=self.save_picture)

    def change_color(self, args):
        index = args
        self.line_color_index = index
        self.draw_color = self.available_colors[self.line_color_index][0]
        self.send_action("color", self.draw_color)
        print(self.draw_color)

    def save_picture(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")])

        if file_path:
            # Save only the region between the top and bottom toolbar
            capture_rect = pygame.Rect(0, self.toolbar_height, self.width,
                                       self.height - self.toolbar_height - self.bottom_toolbar_height)
            captured_image = self.screen.subsurface(capture_rect)
            pygame.image.save(captured_image, file_path)
            print(f"Picture saved to {file_path}")

    def draw_toolbar(self):
        pygame.draw.rect(self.screen, self.toolbar_color, (0, 0, self.width, self.toolbar_height))

        # Draw color buttons
        for color_button in self.color_buttons:
            color_button.draw()

        # Draw width slider
        self.width_slider.draw()

    def draw_bottom_toolbar(self):
        pygame.draw.rect(self.screen, self.toolbar_color,
                         (0, self.height - self.bottom_toolbar_height, self.width, self.bottom_toolbar_height))

        # Draw save button
        self.save_button.draw()

    def send_action(self, action_type, data):
        drawing_action = (action_type, data)
        try:
            self.client_socket.sendall(pickle.dumps(drawing_action))
        except socket.error as e:
            print(f"Error sending data to server: {e}")

    def run(self):
        self.screen.fill((255, 255, 255))  # White background
        self.send_action("join", '')
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
                    self.send_action("line", self.points)
                elif event.type == pygame.MOUSEMOTION:
                    if self.drawing and event.pos[1] > self.toolbar_height:
                        self.points.append(event.pos)

                # Handle slider events
                self.line_width = int(self.width_slider.getValue())

                # Handle button events
                self.save_button.listen(event)

            self.draw_toolbar()
            self.draw_bottom_toolbar()

            if len(self.points) > 0:
                for p in self.points:
                    pygame.draw.circle(self.screen, self.draw_color, p, self.line_width * 2)

                if self.drawing and len(self.points) > 0:
                    if self.last_circle_position is not None:
                        pygame.draw.line(self.screen, self.draw_color, self.last_circle_position, self.points[-1],
                                         self.line_width * 5)
                    self.last_circle_position = self.points[-1]

            if not self.drawing:
                self.last_circle_position = None

            pygame.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    app = WhiteboardApp(800, 600)
    app.run()
