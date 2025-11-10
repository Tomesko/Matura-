import pygame
import os

from Hra.settings import backgrounds_color
from settings import screen_width, screen_height
from postavy import player, enemy
from main_menu import Menu  # Import menu class

pygame.init()
pygame.display.set_caption("Dungeon Crawler")
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

menu = Menu(screen)
start_game = menu.wait_for_start()

if not start_game:
    pygame.quit()
    exit()

# Initialize player and enemy after starting the game
player = player.Player()
enemy = enemy.Enemy(100, 100)

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Handle input
    keys = pygame.key.get_pressed()
    dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
    dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
    player.move(dx, dy)
    enemy.move_towards_player(player)

    # Draw everything
    screen.fill(backgrounds_color)
    pygame.draw.rect(screen, player.color, player.rect)
    pygame.draw.rect(screen, enemy.color, enemy.rect)
    pygame.display.flip()

    clock.tick(60)

pygame.quit()
