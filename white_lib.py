from tkinter import filedialog  # for saving image

import pygame
import sys

import pygame_widgets
from pygame_widgets.slider import Slider
from pygame_widgets.button import Button
import pyperclip

class WhiteboardApp:
    def initialize(self, with_head, ID = ''):
        pygame.init()
        self.id = ID
        self.width = 800
        self.height = 600
        if with_head:
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Whiteboard App")
        else:
            pygame.init()
            self.screen = pygame.Surface((self.width, self.height))
        self.clock = pygame.time.Clock()

        self.setup()


    def setup(self):
        self.line_color_index = 0
        self.available_colors = [
            [(0, 0, 0), (20, 20, 20)],    # Black
            [(255, 0, 0), (240, 0, 0)],  # Red
            [(0, 255, 0), (0, 240, 0)],  # Green
            [(0, 0, 255), (0, 0, 240)],  # Blue
            [(255, 255, 0), (240, 240, 0)],  # yellow
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

        # Calculate space for ID and adjust save button position
        self.save_button = Button(self.screen, self.width - 120, self.height - self.bottom_toolbar_height + 10,
                                  100, 20, text='Save', fontSize=15, margin=20, inactiveColour=(255, 255, 255),
                                  active_color=(240, 240, 240), onClick=self.save_picture)
        self.ID_button = Button(self.screen, self.width - 785, self.height - self.bottom_toolbar_height + 10,
                                100, 20, text=f"{self.id}", fontSize=15, margin=20, inactiveColour=(255, 255, 255),
                                active_color=(240, 240, 240), onClick=lambda: pyperclip.copy(f"{self.id}"))


        pygame.draw.circle(self.screen, (255, 255, 255), (600, 500), 1000)

    def change_color(self, args):
        index = args
        self.line_color_index = index
        if self.draw_color != self.available_colors[self.line_color_index][0]:
            self.draw_color = self.available_colors[self.line_color_index][0]
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


    def save_picture_path(self, file_path):
        capture_rect = pygame.Rect(0, 0, self.width,
                                   self.height)
        captured_image = self.screen.subsurface(capture_rect)
        pygame.image.save(captured_image, file_path)


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

        self.ID_button.draw()
        self.save_button.draw()

    def draw(self, points, draw_color, line_width, last_circle_position):
        for p in points:
            pygame.draw.circle(self.screen, draw_color, p, line_width * 2)

        if last_circle_position is not None:
            pygame.draw.line(self.screen, draw_color,last_circle_position, points[-1],
                             line_width * 5)

    def set_image(self, image_path):
        """
        Sets the current image to the image located at the given path.

        Parameters:
            image_path (str): The path to the image file.
        """
        try:
            self.screen.blit(pygame.image.load(image_path), (0, 0))
            pygame.display.update()
        except pygame.error as e:
            print(f"Error loading image: {e}")
