import pygame
import random

# Inicializace
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dungeon Crawler")

clock = pygame.time.Clock()
FPS = 60

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
        # TODO: Přidej třeba inventář nebo XP systém

    def update(self, keys):
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
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.hp = 5

    def update(self):
        # TODO: Pohyb nepřítele (třeba směrem k hráči)
        pass


# Dungeon (jen placeholder grid)
TILE_SIZE = 40
dungeon = [[0 for _ in range(WIDTH // TILE_SIZE)] for _ in range(HEIGHT // TILE_SIZE)]
# TODO: Udělej generátor dungeonů (místnosti + chodby)

# Sprite skupiny
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()

player = Player(100, 100)
all_sprites.add(player)

# Spawn nepřátel
for i in range(5):
    enemy = Enemy(random.randint(0, WIDTH-40), random.randint(0, HEIGHT-40))
    all_sprites.add(enemy)
    enemies.add(enemy)

# Herní smyčka
running = True
while running:
    clock.tick(FPS)

    # Eventy
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    # Update
    all_sprites.update(keys)

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

pygame.quit()
