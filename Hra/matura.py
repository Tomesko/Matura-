import os
import sys
import pygame
from pygame.examples.grid import TILE_SIZE
from pygame.examples.moveit import WIDTH

# aktuální složka, kde máš main.py
BASE_DIR = os.path.dirname(__file__)

# cesta ke složce s postavami
IMAGE_DIR = os.path.join(BASE_DIR, "postavy")

# Inicializace
pygame.init()
pygame.display.set_caption("Dungeon Crawler")

clock = pygame.time.Clock()
FPS = 60

#Screen
#info = pygame.display.Info()
#screen_width = info.current_w
#screen_height = info.current_h
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

#full-screen
#screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)

# Barvy
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)

# Hráč
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.speed = 4
        self.hp = 10
        self.xp = 0
        # TODO: Přidej třeba inventář nebo XP systém

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed
        # TODO: Omez pohyb jen na mapu (nesejdi z dungeon dlaždic)


# Nepřítel
skeleton_sheet = pygame.image.load("skeleton1.png").convert_alpha()

frame_width = 32
frame_height = 32
#x radek animace
idle_frame = []
for i in range(7):  #kolik frame ma animece
    frame = skeleton_sheet.subsurface(pygame.Rect(i * frame_width, 0, frame_width, frame_height))
    idle_frame.append(frame)
#enemy class
class Skeleton(pygame.sprite.Sprite):
    def __init__(self, level=1):
        super().__init__()
        self.level = level
        self.frames = idle_frame
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=(400, 300))
        self.animation_timer = 0

    def update(self, dt):
        self.animationn.timer += dt
        if self.animation_timer > 150: #ms mezi snimky
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.image = self.frames[self.current_frame]
            self.animation_timer = 0

#skeleton lvl1
class Enemy(pygame.sprite.Sprite):
    def __int__(self):
        super().__init__()
        self.level = level = 1
        enemy = Enemy(level=1)

all_sprites = pygame.sprite.Group(Enemy)


def screen_fill(param):
    pass

# Dungeon (jen placeholder grid)
title_size = 40

dungeon = [[0 for _ in range(WIDTH // TILE_SIZE)] for _ in range]
# TODO: Udělej generátor dungeonů (místnosti + chodby)

# Sprite skupiny
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
player: Player = Player(100, 100)
all_sprites.add(player)


# Herní smyčka
running = True
while running:
    clock.tick(FPS)

    # Eventy
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    all_sprites.update()

    # Update



    # Kolize hráč vs. nepřítel
    hits = pygame.sprite.spritecollide(player, enemies, False)
    for enemy in hits:
        player.hp -= 1
        print("Hráč HP:", player.hp)
        # TODO: Udělej jednoduchý souboj systém (útok hráče vs. útok nepřítele)

    # Render
    screen.fill(BLACK)
    all_sprites.draw(screen)

    # HP bar
    pygame.draw.rect(screen, RED, (10, 10, 100, 20))
    pygame.draw.rect(screen, GREEN, (10, 10, player.hp * 10, 20))  # HP bar podle života

    pygame.display.flip()

#main loop
    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            pygame.quit()
            sys.exit()

        all_sprites.update(dt)
        screen_fill((30, 30, 30))
        all_sprites.draw(screen)
        pygame.display.flip()

pygame.quit()
