import pygame
import random
import math

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 30

# Barvy (Původní čistá paleta)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLUE = (50, 150, 255)      # Hráč
RED = (200, 50, 50)        # Nepřítel
PURPLE = (150, 0, 150)     # Boss
ORANGE = (255, 140, 0)     # Strážce klíče
GREEN = (50, 200, 50)      # Loot / OK
GOLD = (255, 215, 0)       # Zlato

# --- TŘÍDY PŘEDMĚTŮ ---

class Item:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Weapon(Item):
    def __init__(self, name, min_dmg, max_dmg, scaling_stat, scaling_rank, value):
        super().__init__(name, value)
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.scaling_stat = scaling_stat
        self.scaling_rank = scaling_rank

class Armor(Item):
    def __init__(self, name, bonus_hp, bonus_def, value):
        super().__init__(name, value)
        self.bonus_hp = bonus_hp
        self.bonus_def = bonus_def

class Potion(Item):
    def __init__(self, name, heal_amount, value):
        super().__init__(name, value)
        self.heal_amount = heal_amount

# --- ENTITY ---

class Player:
    def __init__(self):
        self.grid_x = 0
        self.grid_y = 0
        self.has_boss_key = False
        
        # Staty
        self.stats = {
            "vigor": 10, "str": 10, "dex": 10, 
            "int": 10, "luck": 5, "def": 0
        }
        
        self.level = 1
        self.xp = 0
        self.xp_next = 100
        self.gold = 150 # Startovní zlato
        
        # Startovní gear
        self.weapon = Weapon("Základní dýka", 5, 8, "dex", 0.5, 0)
        self.armor = Armor("Látkové hadry", 0, 1, 0)
        self.inventory = [Potion("Lektvar", 30, 20)]
        
        self.max_hp = 0
        self.current_hp = 0
        self.total_def = 0
        self.recalculate_stats()
        self.current_hp = self.max_hp

    def recalculate_stats(self):
        self.max_hp = (self.stats["vigor"] * 10) + self.armor.bonus_hp
        self.total_def = (self.stats["def"] // 2) + self.armor.bonus_def
        if self.current_hp > self.max_hp: self.current_hp = self.max_hp

    def get_crit_chance(self):
        return min(self.stats["luck"], 75)

    def attack(self):
        base = random.randint(self.weapon.min_dmg, self.weapon.max_dmg)
        stat_val = self.stats.get(self.weapon.scaling_stat, 10)
        bonus = int(stat_val * self.weapon.scaling_rank)
        total_dmg = base + bonus
        
        is_crit = False
        if random.randint(1, 100) <= self.get_crit_chance():
            is_crit = True
            crit_mult = 1.5 + (self.stats["dex"] * 0.01)
            total_dmg = int(total_dmg * crit_mult)
            
        return total_dmg, is_crit

    def take_damage(self, amount):
        real_dmg = max(1, amount - self.total_def)
        self.current_hp -= real_dmg
        return real_dmg

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            return True
        return False

class Enemy:
    def __init__(self, dist, is_boss=False, is_key_holder=False):
        self.is_boss = is_boss
        self.is_key_holder = is_key_holder
        scale = (dist // 3) + 1
        
        if is_boss:
            self.name = "BOSS: PÁN PODZEMÍ"
            self.hp = 200 * scale
            self.dmg = 25 * scale
            self.xp = 500 * scale
            self.gold = 300 * scale
        elif is_key_holder:
            self.name = "STRÁŽCE KLÍČE"
            self.hp = 60 * scale
            self.dmg = 12 * scale
            self.xp = 100 * scale
            self.gold = 50 * scale
        else:
            names = ["Goblin", "Sliz", "Kostlivec", "Skřet", "Netopýr"]
            self.name = random.choice(names)
            self.hp = 20 + (10 * scale)
            self.dmg = 5 + (2 * scale)
            self.xp = 20 * scale
            self.gold = random.randint(5, 15) * scale
        self.max_hp = self.hp

class Room:
    def __init__(self, x, y, from_dir=None):
        self.visited = False
        self.enemy = None
        self.exits = {'N': False, 'S': False, 'E': False, 'W': False}
        
        dirs = ['N', 'S', 'E', 'W']
        for d in dirs:
            if random.random() > 0.35: self.exits[d] = True
            
        if from_dir == 'N': self.exits['S'] = True
        if from_dir == 'S': self.exits['N'] = True
        if from_dir == 'E': self.exits['W'] = True
        if from_dir == 'W': self.exits['E'] = True

# --- HLAVNÍ ENGINE ---

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Solo Crawler v4.0 - Full Features")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 30, bold=True)
        
        self.player = Player()
        self.map = {(0,0): Room(0,0)}
        self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
        
        # --- SHOP (Obsahuje nové zbraně) ---
        self.shop_items = [
            Potion("Velký Lektvar", 100, 50),
            Weapon("Katana (DEX)", 12, 18, "dex", 1.2, 200),
            Weapon("Gilded Katana (DEX)", 20, 28, "dex", 1.8, 550),
            Weapon("Shojins Lost Katana", 30, 48, "dex", 2.1, 950),
            Weapon("Válečné Kladivo (STR)", 15, 25, "str", 1.2, 250),
            Weapon("Magická Hůl (INT)", 10, 30, "int", 1.5, 300),
            Armor("Rytířské brnění", 50, 5, 400),
            Armor("Dračí kůže", 100, 10, 1000),
            "UPGRADE (+5 DMG)"
        ]

        self.state = "EXPLORE"
        self.combat_enemy = None
        self.message_log = ["Vítej v podzemí! Šipky pohyb, B obchod."]

    def log(self, text):
        self.message_log.append(text)
        if len(self.message_log) > 8:
            self.message_log.pop(0)

    def generate_room(self, x, y, from_dir):
        if (x, y) not in self.map:
            room = Room(x, y, from_dir)
            
            dist = math.sqrt(x**2 + y**2)
            if dist > 0:
                if random.random() < 0.6: 
                    # Spawn logika (Boss vs Guardian vs Normal)
                    if self.player.has_boss_key and dist > 15 and random.random() < 0.1:
                        room.enemy = Enemy(dist, is_boss=True)
                    elif not self.player.has_boss_key and dist > 8 and random.random() < 0.15:
                        room.enemy = Enemy(dist, is_key_holder=True)
                        self.log("Cítíš silnou auru... Strážce Klíče!")
                    else:
                        room.enemy = Enemy(dist)
            
            self.map[(x, y)] = room

    def move_player(self, dx, dy, direction):
        curr_room = self.map[(self.player.grid_x, self.player.grid_y)]
        
        # Zamykání dveří v boji
        if curr_room.enemy is not None:
            self.log("Místnost je zamčená! Zabij ho nebo uteč [U].")
            return

        if not curr_room.exits.get(direction):
            self.log("Tudy nevedou dveře!")
            return

        nx, ny = self.player.grid_x + dx, self.player.grid_y + dy
        from_dir = {'N':'S', 'S':'N', 'E':'W', 'W':'E'}[direction]
        
        self.generate_room(nx, ny, from_dir)
        self.player.grid_x, self.player.grid_y = nx, ny
        
        new_room = self.map[(nx, ny)]
        if new_room.enemy:
            self.state = "COMBAT"
            self.combat_enemy = new_room.enemy
            self.log(f"NARAZIL JSI NA: {self.combat_enemy.name}!")

    def combat_round(self, action):
        enemy = self.combat_enemy
        
        # --- ÚTĚK ---
        if action == "RUN":
            if self.player.gold >= 50:
                self.player.gold -= 50
                self.log("Utekl jsi (-50 Gold)!")
                self.map[(self.player.grid_x, self.player.grid_y)].enemy = None
                self.combat_enemy = None
                self.state = "EXPLORE"
                return
            else:
                self.log("Nemáš 50 Goldů na útěk!")
        
        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            enemy.hp -= dmg
            crit_str = " (CRIT!)" if crit else ""
            self.log(f"Zasáhl jsi za {dmg}{crit_str}.")
            
            if enemy.hp <= 0:
                self.log(f"Zabil jsi {enemy.name}!")
                
                # Klíč
                if enemy.is_key_holder:
                    self.player.has_boss_key = True
                    self.log(">>> ZÍSKAL JSI KLÍČ K BOSSOVI! <<<")

                # Loot
                self.player.gold += enemy.gold + (self.player.stats["luck"] * 2)
                lvl_up = self.player.gain_xp(enemy.xp)
                
                # Item drop
                if random.randint(1,100) < (30 + self.player.stats["luck"]):
                    self.player.inventory.append(Potion("Lektvar", 30, 20))
                    self.log("Drop: Lektvar!")

                self.map[(self.player.grid_x, self.player.grid_y)].enemy = None
                self.combat_enemy = None
                
                if lvl_up: self.state = "LEVELUP"
                else: self.state = "EXPLORE"
                return

        elif action == "HEAL":
            potions = [i for i in self.player.inventory if isinstance(i, Potion)]
            if potions:
                pot = potions[0]
                self.player.current_hp = min(self.player.max_hp, self.player.current_hp + pot.heal_amount)
                self.player.inventory.remove(pot)
                self.log(f"Vypil jsi {pot.name}.")
            else:
                self.log("Nemáš lektvary!")
                return 

        # Enemy Turn
        if self.combat_enemy:
            p_dmg = self.player.take_damage(enemy.dmg)
            self.log(f"{enemy.name} ti dal za {p_dmg} dmg.")
            
            if self.player.current_hp <= 0:
                self.state = "GAMEOVER"

    def draw_map(self):
        # Původní čistý design mapy
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        range_view = 6
        
        for dy in range(-range_view, range_view+1):
            for dx in range(-range_view, range_view+1):
                map_x = self.player.grid_x + dx
                map_y = self.player.grid_y - dy 
                
                screen_x = center_x + (dx * TILE_SIZE)
                screen_y = center_y + (dy * TILE_SIZE)
                
                if (map_x, map_y) in self.map:
                    room = self.map[(map_x, map_y)]
                    
                    color = GRAY if not room.enemy else (80, 80, 80)
                    pygame.draw.rect(self.screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
                    
                    border_col = RED if room.enemy else BLACK
                    width = 3 if room.enemy else 1
                    pygame.draw.rect(self.screen, border_col, (screen_x, screen_y, TILE_SIZE, TILE_SIZE), width)
                    
                    door_w = 10
                    if room.exits['N']: pygame.draw.rect(self.screen, WHITE, (screen_x + TILE_SIZE//2 - door_w//2, screen_y, door_w, 5))
                    if room.exits['S']: pygame.draw.rect(self.screen, WHITE, (screen_x + TILE_SIZE//2 - door_w//2, screen_y + TILE_SIZE - 5, door_w, 5))
                    if room.exits['W']: pygame.draw.rect(self.screen, WHITE, (screen_x, screen_y + TILE_SIZE//2 - door_w//2, 5, door_w))
                    if room.exits['E']: pygame.draw.rect(self.screen, WHITE, (screen_x + TILE_SIZE - 5, screen_y + TILE_SIZE//2 - door_w//2, 5, door_w))
                    
                    if room.enemy:
                        ecolor = PURPLE if room.enemy.is_boss else (ORANGE if room.enemy.is_key_holder else RED)
                        pygame.draw.circle(self.screen, ecolor, (screen_x + TILE_SIZE//2, screen_y + TILE_SIZE//2), 10)

        pygame.draw.circle(self.screen, BLUE, (center_x + TILE_SIZE//2, center_y + TILE_SIZE//2), 12)

    def draw_ui(self):
        # Původní design panelu
        panel_x = WIDTH - 250
        pygame.draw.rect(self.screen, DARK_GRAY, (panel_x, 0, 250, HEIGHT))
        pygame.draw.line(self.screen, WHITE, (panel_x, 0), (panel_x, HEIGHT), 2)
        
        y = 20
        def draw_text(txt, col=WHITE, size_mod=0):
            nonlocal y
            f = self.title_font if size_mod else self.font
            s = f.render(txt, True, col)
            self.screen.blit(s, (panel_x + 10, y))
            y += 30 + size_mod
            
        draw_text("SOLO CRAWLER", GOLD, 5)
        draw_text(f"Level: {self.player.level}")
        draw_text(f"XP: {self.player.xp}/{self.player.xp_next}", GRAY)
        
        key_status = "MÁŠ KLÍČ" if self.player.has_boss_key else "-"
        draw_text(f"Boss Key: {key_status}", GREEN if self.player.has_boss_key else GRAY)
        
        y += 10
        hp_perc = self.player.current_hp / self.player.max_hp
        col = GREEN if hp_perc > 0.5 else RED
        draw_text(f"HP: {self.player.current_hp}/{self.player.max_hp}", col)
        draw_text(f"Gold: {self.player.gold}", GOLD)
        
        y += 20
        draw_text("STATS:", size_mod=5)
        draw_text(f"VIG (HP): {self.player.stats['vigor']}")
        draw_text(f"STR (Dmg): {self.player.stats['str']}")
        draw_text(f"DEX (Crit): {self.player.stats['dex']}")
        draw_text(f"INT (Mag): {self.player.stats['int']}")
        draw_text(f"LUCK: {self.player.stats['luck']}")
        draw_text(f"DEF: {self.player.total_def}")
        
        y += 20
        draw_text("Vybavení:", size_mod=5)
        draw_text(f"{self.player.weapon.name}", BLUE)
        draw_text(f"Dmg: {self.player.weapon.min_dmg}-{self.player.weapon.max_dmg}", GRAY)
        draw_text(f"{self.player.armor.name}", BLUE)
        draw_text(f"Lektvary: {len([x for x in self.player.inventory if isinstance(x, Potion)])}", GREEN)

        log_y = HEIGHT - 200
        pygame.draw.line(self.screen, WHITE, (0, log_y), (panel_x, log_y))
        for i, msg in enumerate(self.message_log):
            c = WHITE
            if "BOSS" in msg or "KLÍČ" in msg: c = GOLD
            elif "Drop" in msg: c = GREEN
            elif "Utekl" in msg: c = RED
            s = self.font.render(msg, True, c)
            self.screen.blit(s, (20, log_y + 10 + (i * 20)))

    def draw_combat_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0,0))
        
        cx, cy = WIDTH//2, HEIGHT//2
        enemy = self.combat_enemy
        
        pygame.draw.rect(self.screen, RED, (cx - 150, cy - 100, 300, 200), 2)
        color = PURPLE if enemy.is_boss else (ORANGE if enemy.is_key_holder else RED)
        pygame.draw.rect(self.screen, color, (cx - 40, cy - 80, 80, 80))
        
        s = self.title_font.render(f"{enemy.name}", True, WHITE)
        self.screen.blit(s, (cx - s.get_width()//2, cy - 130))
        
        s = self.font.render(f"HP: {enemy.hp}/{enemy.max_hp} | DMG: {enemy.dmg}", True, WHITE)
        self.screen.blit(s, (cx - s.get_width()//2, cy + 10))
        
        s = self.font.render("[SPACE] Útok  [H] Heal  [U] Útěk (50g)", True, GOLD)
        self.screen.blit(s, (cx - s.get_width()//2, cy + 50))

    def draw_shop(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0,0))
        
        t = self.title_font.render("--- SYSTEM SHOP ---", True, BLUE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 50))
        
        t = self.font.render(f"Tvé zlato: {self.player.gold}", True, GOLD)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 80))
        
        y = 120
        for i, item in enumerate(self.shop_items):
            txt = ""
            if isinstance(item, str):
                txt = f"{i+1}. {item} - 500 G"
            else:
                txt = f"{i+1}. {item.name} - {item.value} Gold"
            
            price = 500 if isinstance(item, str) else item.value
            color = WHITE if self.player.gold >= price else GRAY
            
            s = self.font.render(txt, True, color)
            self.screen.blit(s, (200, y))
            y += 40
            
        s = self.font.render("Stiskni číslo pro nákup nebo [B] pro odchod.", True, GRAY)
        self.screen.blit(s, (WIDTH//2 - s.get_width()//2, HEIGHT - 100))

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if self.state == "EXPLORE":
                        if event.key == pygame.K_UP: self.move_player(0, 1, 'N')
                        elif event.key == pygame.K_DOWN: self.move_player(0, -1, 'S')
                        elif event.key == pygame.K_RIGHT: self.move_player(1, 0, 'E')
                        elif event.key == pygame.K_LEFT: self.move_player(-1, 0, 'W')
                        elif event.key == pygame.K_b: self.state = "SHOP"
                    
                    elif self.state == "COMBAT":
                        if event.key == pygame.K_SPACE: self.combat_round("ATTACK")
                        elif event.key == pygame.K_h: self.combat_round("HEAL")
                        elif event.key == pygame.K_u: self.combat_round("RUN")
                    
                    elif self.state == "SHOP":
                        if event.key == pygame.K_b: self.state = "EXPLORE"
                        else:
                            try:
                                key_num = int(event.unicode)
                                idx = key_num - 1
                                if 0 <= idx < len(self.shop_items):
                                    item = self.shop_items[idx]
                                    price = 500 if isinstance(item, str) else item.value
                                    
                                    if self.player.gold >= price:
                                        self.player.gold -= price
                                        if isinstance(item, str):
                                            self.player.weapon.min_dmg += 5
                                            self.player.weapon.max_dmg += 5
                                            self.log("Upgrade: Zbraň vylepšena!")
                                        else:
                                            if isinstance(item, Weapon): self.player.weapon = item
                                            elif isinstance(item, Armor): self.player.armor = item; self.player.recalculate_stats()
                                            else: self.player.inventory.append(item)
                                            self.log(f"Koupeno: {item.name}")
                                    else:
                                        self.log("Nedostatek zlata!")
                            except: pass

                    # --- NOVÁ LOGIKA LEVEL UP (Vše +1, Výběr +1) ---
                    elif self.state == "LEVELUP":
                        k = event.key
                        stat_map = {
                            pygame.K_1: 'vigor', pygame.K_2: 'str', 
                            pygame.K_3: 'dex', pygame.K_4: 'int', 
                            pygame.K_5: 'luck', pygame.K_6: 'def'
                        }
                        
                        if k in stat_map:
                            selected = stat_map[k]
                            
                            # 1. Zvedneme vše o 1
                            for s in self.player.stats:
                                self.player.stats[s] += 1
                            
                            # 2. Zvedneme vybrané ještě o 1
                            self.player.stats[selected] += 1
                            
                            self.player.recalculate_stats()
                            self.player.current_hp = self.player.max_hp
                            self.log(f"Level UP! Vše +1, {selected.upper()} +2.")
                            self.state = "EXPLORE"

            self.screen.fill(BLACK)
            
            if self.state in ["EXPLORE", "COMBAT"]:
                self.draw_map()
            
            self.draw_ui()
            
            if self.state == "COMBAT": self.draw_combat_overlay()
            elif self.state == "SHOP": self.draw_shop()
            elif self.state == "LEVELUP":
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.fill(BLACK)
                self.screen.blit(overlay, (0,0))
                t = self.title_font.render("LEVEL UP! Vyber bonus (Vše +1, Bonus +1):", True, GOLD)
                self.screen.blit(t, (250, 100))
                opts = ["1. VIGOR (HP)", "2. STR (Dmg)", "3. DEX (Crit)", "4. INT (Mag)", "5. LUCK (Drop)", "6. DEF (Armor)"]
                for i, o in enumerate(opts):
                    s = self.font.render(o, True, WHITE)
                    self.screen.blit(s, (350, 180 + i*40))
            elif self.state == "GAMEOVER":
                t = self.title_font.render("KONEC HRY", True, RED)
                self.screen.blit(t, (WIDTH//2 - 100, HEIGHT//2))

            pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
