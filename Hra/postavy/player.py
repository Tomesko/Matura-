# player.py
import pygame
import os

from Hra.settings import screen_width, screen_height, player_color, player_speed

# aktuální složka, kde máš main.py
BASE_DIR = os.path.dirname(__file__)

# cesta ke složce
IMAGE_DIR = os.path.join(BASE_DIR, "hra")


class Player:
    def __init__(self):
        self.x = screen_width// 2  # Use imported width
        self.y = screen_height // 2  # Use imported height
        self.speed = player_speed  # Use imported speed
        self.color = player_color  # Use imported color
        self.rect = pygame.Rect(self.x, self.y, 50, 50)  # Example player size
    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.rect.topleft = (self.x, self.y)