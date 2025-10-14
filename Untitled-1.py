import pygame
import random

#instalizace
pygame.int()
WIDTH, HEIGHT = 800, 600
screen = pygame.dysplay.set_mdoe(WIDTH, HEIGHT)
pygame.dysplay.set_caption("Dungeon Crawler")

#FPS hry
clock = pygame.time.Clock()
FPS = 30

#background color by lvl
level_colors = {
    1: (30, 30, 30), #dark grey lvl 1
    2: (100, 50, 50), #brown lvl 2
    3: (50, 100, 50), #greem lvl 3
    4: (50, 50, 100), #Blue lvl 4
    5: (100, 50, 100), #Purple lvl 5 final boss
}

current_level = 1 #start
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        #changing backgroudn clr by lvl of enemy

#Fill backgournd with the clr for the current lvl
screen.fill(level_colors.get(current_level, (0, 0, 0)))

# --- Enemy class ---
class Enemy:
    def __init__(self, x, y, level):
        self.x = x
        self.y = y
        self.level = level
        self.color = (200, 0, 0)
        self.size = 30

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, (self.x, self.y, self.size, self.size))

# --- Simulate some enemies on the map ---
enemies = [
    Enemy(100, 100, 1),
    Enemy(300, 200, 2),
    Enemy(500, 300, 3),
]

    # Randomly add a new enemy with a random level when pressing SPACE
    if event.type == pygame.KEYDOWN:
     if event.key == pygame.K_SPACE:
        new_enemy = Enemy(
            random.randint(0, WIDTH - 30),
            random.randint(0, HEIGHT - 30),
            random.randint(1, 5)
        )
        enemies.append(new_enemy)
    # Press 'C' to clear all enemies
    if event.key == pygame.K_c:
        enemies.clear()

    # --- Find highest level of enemies ---
    if enemies:
         highest_level = max(enemy.level for enemy in enemies)
    else:
        highest_level = 1  # Default to level 1 if no enemies

    bg_color = enemy_level_colors.get(highest_level, (0, 0, 0))
    screen.fill(bg_color)

# --- Draw enemies ---
for enemy in enemies:
    enemy.draw(screen)

    pygame.quit()
