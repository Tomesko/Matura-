#Screen
import pygame
from pygame.examples.video import backgrounds

screen_width = 1200
screen_height = 800




# Barvy
class color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (0, 200, 0)
    RED = (200, 0, 0)
    DARK_RED = (75, 0, 0)

backgrounds = backgrounds_color = color.DARK_RED

#player
player_color = color.GREEN
player_speed = 5

#enemy
enemy_color = color.RED
enemy_speed = 2,5


# settings.py (add these lines)
RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720)
]
CURRENT_RESOLUTION = RESOLUTIONS[0]  # Default to first one
BACKGROUND_COLOR = color.DARK_RED