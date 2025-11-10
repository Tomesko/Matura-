#enemy.py
import pygame
import os

from Hra.settings import screen_width, screen_height, enemy_speed

# aktuální složka, kde máš main.py
BASE_DIR = os.path.dirname(__file__)

 #cesta ke složce
IMAGE_DIR = os.path.join(BASE_DIR, "hra")

class Enemy:
    def __init__(self):
        self.speed = enemy_speed
        self.color = (200, 0, 0)
        self.x = screen_width // 2
        self.y = screen_height // 2
        self.rect = pygame.Rect(self.x, self.y, 60,60) #enemy size

