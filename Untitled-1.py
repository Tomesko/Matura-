  import pygame
import random
import math

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 30

# Barvy
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLUE = (50, 150, 255)      # Hráč
RED = (200, 50, 50)        # Nepřítel
PURPLE = (150, 0, 150)     # Boss
ORANGE = (255, 140, 0)     # Strážce
GREEN = (50, 200, 50)      # Loot
GOLD = (255, 215, 0)       # Zlato
CYAN = (0, 255, 255)       # Portal/Next Level

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
        self.scaling_rank = scaling_rank # Číslo (např 1.5)
    
    # Metoda pro hezké zobrazení ranku (S, A, B, C)
    def get_grade(self):
        if self.scaling_rank >= 1.8: return "S"
        elif self.scaling_rank >= 1.4: return "A"
        elif self.scaling_rank >= 1.0: return "B"
        else: return "C"

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
        
        self.stats = {
            "vigor": 10, "str": 10, "dex": 10, 
            "int": 10, "luck": 5, "def": 0
        }
        
        self.level = 1
        self.xp = 0
        self.xp_next = 100
        self.gold = 100
        
        # Startovní gear
        self.weapon = Weapon("Rezavý meč", 5, 8, "str", 0.8, 0)
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
        
        # Scaling
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
    def __init__(self, dist, floor, is_boss=False, is_key_holder=False):
        self.is_boss = is_boss
        self.is_key_holder = is_key_holder
        
        # --- FLOOR SCALING ---
        # Každé patro přidá 20% k síle monster
        floor_multiplier = 1.0 + ((floor - 1) * 0.2)
        dist_scale = (dist // 3) + 1
        
        total_scale = dist_scale * floor_multiplier
        
        if is_boss:
            self.name = f"BOSS: PÁN PATRA {floor}"
            self.hp = int(250 * total_scale)
            self.dmg = int(25 * total_scale)
            self.xp = int(500 * total_scale)
            self.gold = int(300 * total_scale)
        elif is_key_holder:
            self.name = "STRÁŽCE KLÍČE"
            self.hp = int(80 * total_scale)
            self.dmg = int(15 * total_scale)
            self.xp = int(150 * total_scale)
            self.gold = int(80 * total_scale)
        else:
            names = ["Goblin", "Sliz", "Kostlivec", "Skřet", "Netopýr", "Démon"]
            self.name = random.choice(names)
            self.hp = int(25 * total_scale)
            self.dmg = int(6 * total_scale)
            self.xp = int(25 * total_scale)
            self.gold = int(random.randint(5, 15) * total_scale)
            
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
        pygame.display.set_caption("Solo Crawler v5.0 - Infinite Floors")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 60, bold=True)
        
        self.player = Player()
        self.floor = 1 # Počítadlo pater
        self.reset_map()
        
        # Shop Items (s vypsanými ranky)
        self.shop_items = [
            Potion("Velký Lektvar", 100, 50),
            Weapon("Katana (DEX)", 12, 18, "dex", 1.2, 200),
            Weapon("Gilded Katana (DEX)", 20, 28, "dex", 1.8, 550),
            Weapon("Shojins Lost Katana", 30, 48, "dex", 2.1, 950),
            Weapon("Válečné Kladivo (STR)", 15, 25, "str", 1.2, 250),
            Weapon("Demons GreatHammer", 35, 55, "str", 2.0, 1100),
            Weapon("Magická Hůl (INT)", 10, 30, "int", 1.5, 300),
            Armor("Rytířské brnění", 50, 5, 400),
            Armor("Dračí kůže", 100, 10, 1000),
            "UPGRADE (+5 DMG)"
        ]

        self.state = "MENU" # Začínáme v menu
        self.combat_enemy = None
        self.message_log = []

    def log(self, text):
        self.message_log.append(text)
        if len(self.message_log) > 8:
            self.message_log.pop(0)

    def reset_map(self):
        """Vygeneruje novou mapu pro nové patro"""
        self.map = {(0,0): Room(0,0)}
        self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
        self.player.grid_x = 0
        self.player.grid_y = 0
        self.player.has_boss_key = False
        self.message_log = [f"Vítej v Patře {self.floor}!"]

    def generate_room(self, x, y, from_dir):
        if (x, y) not in self.map:
            room = Room(x, y, from_dir)
            dist = math.sqrt(x**2 + y**2)
            
            if dist > 0:
                if random.random() < 0.6: 
                    # Boss (Hard limit 15, key required)
                    if self.player.has_boss_key and dist > 12 and random.random() < 0.1:
                        room.enemy = Enemy(dist, self.floor, is_boss=True)
                    # Key Holder (Hard limit 8, no key yet)
                    elif not self.player.has_boss_key and dist > 6 and random.random() < 0.15:
                        room.enemy = Enemy(dist, self.floor, is_key_holder=True)
                        self.log("Cítíš přítomnost Strážce Klíče!")
                    # Normal Mob
                    else:
                        room.enemy = Enemy(dist, self.floor)
            
            self.map[(x, y)] = room

    def move_player(self, dx, dy, direction):
        curr_room = self.map[(self.player.grid_x, self.player.grid_y)]
        
        if curr_room.enemy is not None:
            self.log("Dveře jsou zamčené! Bojuj.")
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
            self.log(f"BOJ: {self.combat_enemy.name}!")

    def combat_round(self, action):
        enemy = self.combat_enemy
        
        if action == "RUN":
            cost = 50 * self.floor # Útěk je dražší v hlubších patrech
            if self.player.gold >= cost:
                self.player.gold -= cost
                self.log(f"Utekl jsi (-{cost} Gold)!")
                self.map[(self.player.grid_x, self.player.grid_y)].enemy = None
                self.combat_enemy = None
                self.state = "EXPLORE"
                return
            else:
                self.log(f"Nemáš {cost} Goldů na útěk!")
        
        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            enemy.hp -= dmg
            crit_str = " (CRIT!)" if crit else ""
            self.log(f"Útok za {dmg}{crit_str}.")
            
            if enemy.hp <= 0:
                self.log(f"Zabil jsi {enemy.name}!")
                
                # Logic drops
                if enemy.is_key_holder:
                    self.player.has_boss_key = True
                    self.log(">>> MÁŠ KLÍČ K BOSSOVI! <<<")
                
                self.player.gold += enemy.gold + (self.player.stats["luck"] * 2)
                lvl_up = self.player.gain_xp(enemy.xp)
                
                # Chance drop
                if random.randint(1,100) < (30 + self.player.stats["luck"]):
                    self.player.inventory.append(Potion("Lektvar", 30, 20))
                    self.log("Drop: Lektvar!")

                # BOSS DEFEATED -> NEXT FLOOR
                is_boss_kill = enemy.is_boss
                
                self.map[(self.player.grid_x, self.player.grid_y)].enemy = None
                self.combat_enemy = None
                
                if lvl_up: 
                    self.state = "LEVELUP"
                elif is_boss_kill:
                    self.state = "NEXT_FLOOR"
                else: 
                    self.state = "EXPLORE"
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
            self.log(f"{enemy.name} útočí za {p_dmg}.")
            
            if self.player.current_hp <= 0:
                self.state = "GAMEOVER"

    # --- DRAW FUNCTIONS ---

    def draw_menu(self):
        self.screen.fill(BLACK)
        t = self.big_font.render("SOLO CRAWLER", True, GOLD)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 200))
        
        t = self.font.render("Roguelike RPG Adventure", True, GRAY)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 260))
        
        t = self.title_font.render("[ENTER] Start Game", True, WHITE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 400))
        
        t = self.title_font.render("[Q] Quit", True, RED)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 450))

    def draw_map(self):
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
                    
                    col = GRAY if not room.enemy else (80, 80, 80)
                    pygame.draw.rect(self.screen, col, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
                    
                    b_col = RED if room.enemy else BLACK
                    pygame.draw.rect(self.screen, b_col, (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 3 if room.enemy else 1)
                    
                    # Dveře
                    door_w = 10
                    d_col = WHITE
                    if room.exits['N']: pygame.draw.rect(self.screen, d_col, (screen_x + TILE_SIZE//2 - door_w//2, screen_y, door_w, 5))
                    if room.exits['S']: pygame.draw.rect(self.screen, d_col, (screen_x + TILE_SIZE//2 - door_w//2, screen_y + TILE_SIZE - 5, door_w, 5))
                    if room.exits['W']: pygame.draw.rect(self.screen, d_col, (screen_x, screen_y + TILE_SIZE//2 - door_w//2, 5, door_w))
                    if room.exits['E']: pygame.draw.rect(self.screen, d_col, (screen_x + TILE_SIZE - 5, screen_y + TILE_SIZE//2 - door_w//2, 5, door_w))
                    
                    if room.enemy:
                        c = PURPLE if room.enemy.is_boss else (ORANGE if room.enemy.is_key_holder else RED)
                        pygame.draw.circle(self.screen, c, (screen_x + TILE_SIZE//2, screen_y + TILE_SIZE//2), 10)

        pygame.draw.circle(self.screen, BLUE, (center_x + TILE_SIZE//2, center_y + TILE_SIZE//2), 12)

    def draw_ui(self):
        panel_x = WIDTH - 270
        pygame.draw.rect(self.screen, DARK_GRAY, (panel_x, 0, 270, HEIGHT))
        pygame.draw.line(self.screen, WHITE, (panel_x, 0), (panel_x, HEIGHT), 2)
        
        y = 20
        def draw_text(txt, col=WHITE, size_mod=0):
            nonlocal y
            f = self.title_font if size_mod else self.font
            s = f.render(txt, True, col)
            self.screen.blit(s, (panel_x + 10, y))
            y += 30 + size_mod
            
        draw_text(f"FLOOR: {self.floor}", CYAN, 5)
        draw_text(f"Lvl: {self.player.level} (XP {self.player.xp}/{self.player.xp_next})", GRAY)
        
        key_status = "MÁŠ KLÍČ" if self.player.has_boss_key else "-"
        draw_text(f"Boss Key: {key_status}", GREEN if self.player.has_boss_key else GRAY)
        
        y += 10
        hp_perc = self.player.current_hp / self.player.max_hp
        col = GREEN if hp_perc > 0.5 else RED
        draw_text(f"HP: {self.player.current_hp}/{self.player.max_hp}", col)
        draw_text(f"Gold: {self.player.gold}", GOLD)
        
        y += 20
        draw_text("STATS:", size_mod=2)
        draw_text(f"STR: {self.player.stats['str']} | DEX: {self.player.stats['dex']}")
        draw_text(f"INT: {self.player.stats['int']} | LUC: {self.player.stats['luck']}")
        draw_text(f"DEF: {self.player.total_def}")
        
        y += 20
        # Vylepšené zobrazení zbraně s Rankem
        w = self.player.weapon
        draw_text(f"Weapon: {w.name}", BLUE)
        draw_text(f"DMG: {w.min_dmg}-{w.max_dmg}", GRAY)
        # Zobrazení scalingu
        scaling_txt = f"Scale: {w.scaling_stat.upper()} ({w.get_grade()})"
        scale_col = GOLD if w.get_grade() == "S" else WHITE
        draw_text(scaling_txt, scale_col)
        
        draw_text(f"Armor: {self.player.armor.name}", BLUE)
        draw_text(f"Potions: {len([x for x in self.player.inventory if isinstance(x, Potion)])}", GREEN)

        log_y = HEIGHT - 200
        pygame.draw.line(self.screen, WHITE, (0, log_y), (panel_x, log_y))
        for i, msg in enumerate(self.message_log):
            c = WHITE
            if "BOSS" in msg or "KLÍČ" in msg: c = GOLD
            elif "Drop" in msg: c = GREEN
            elif "Utekl" in msg: c = RED
            s = self.font.render(msg, True, c)
            self.screen.blit(s, (20, log_y + 10 + (i * 20)))

    def draw_shop(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0,0))
        
        t = self.title_font.render("--- SYSTEM SHOP ---", True, BLUE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 50))
        
        t = self.font.render(f"Gold: {self.player.gold}", True, GOLD)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 90))
        
        y = 120
        for i, item in enumerate(self.shop_items):
            txt = ""
            if isinstance(item, str):
                txt = f"{i+1}. {item} - 500 G"
            else:
                # Zobrazit Rank u zbraní
                rank_info = ""
                if isinstance(item, Weapon):
                    rank_info = f" [{item.scaling_stat.upper()}: {item.get_grade()}]"
                txt = f"{i+1}. {item.name}{rank_info} - {item.value} G"
            
            price = 500 if isinstance(item, str) else item.value
            col = WHITE if self.player.gold >= price else GRAY
            
            s = self.font.render(txt, True, col)
            self.screen.blit(s, (150, y))
            y += 40
            
        s = self.font.render("[B] Zpět", True, RED)
        self.screen.blit(s, (WIDTH//2 - s.get_width()//2, HEIGHT - 50))

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            
            # INPUT HANDLING
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    
                    # --- MENU INPUT ---
                    if self.state == "MENU":
                        if event.key == pygame.K_RETURN: self.state = "EXPLORE"
                        elif event.key == pygame.K_q: running = False
                    
                    # --- NEXT FLOOR INPUT ---
                    elif self.state == "NEXT_FLOOR":
                        if event.key == pygame.K_RETURN:
                            self.floor += 1
                            self.reset_map() # Generuj nové patro
                            self.state = "EXPLORE"

                    # --- GAME INPUTS ---
                    elif self.state == "EXPLORE":
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
                                            self.log("Upgrade: +5 DMG")
                                        else:
                                            if isinstance(item, Weapon): self.player.weapon = item
                                            elif isinstance(item, Armor): self.player.armor = item; self.player.recalculate_stats()
                                            else: self.player.inventory.append(item)
                                            self.log(f"Koupeno: {item.name}")
                                    else:
                                        self.log("Nedostatek zlata!")
                            except: pass

                    elif self.state == "LEVELUP":
                        k = event.key
                        stat_map = {pygame.K_1:'vigor', pygame.K_2:'str', pygame.K_3:'dex', pygame.K_4:'int', pygame.K_5:'luck', pygame.K_6:'def'}
                        if k in stat_map:
                            s = stat_map[k]
                            # Vše +1, Výběr +1
                            for st in self.player.stats: self.player.stats[st] += 1
                            self.player.stats[s] += 1
                            
                            self.player.recalculate_stats()
                            self.player.current_hp = self.player.max_hp
                            self.log(f"Level UP! Vše +1, {s.upper()} +2.")
                            
                            # Pokud levelup nastal po zabití bosse, musíme zkontrolovat, kam jít
                            if not self.combat_enemy and self.player.has_boss_key: # Teoreticky
                                self.state = "EXPLORE" # Fallback
                            else:
                                self.state = "EXPLORE"

            # DRAWING
            self.screen.fill(BLACK)
            
            if self.state == "MENU":
                self.draw_menu()
            
            elif self.state in ["EXPLORE", "COMBAT"]:
                self.draw_map()
                self.draw_ui()
                if self.state == "COMBAT": 
                    # Combat Overlay
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 180))
                    self.screen.blit(overlay, (0,0))
                    cx, cy = WIDTH//2, HEIGHT//2
                    enemy = self.combat_enemy
                    
                    pygame.draw.rect(self.screen, RED, (cx - 150, cy - 100, 300, 200), 2)
                    c = PURPLE if enemy.is_boss else (ORANGE if enemy.is_key_holder else RED)
                    pygame.draw.rect(self.screen, c, (cx - 40, cy - 80, 80, 80))
                    
                    s = self.title_font.render(f"{enemy.name}", True, WHITE)
                    self.screen.blit(s, (cx - s.get_width()//2, cy - 130))
                    s = self.font.render(f"HP: {enemy.hp}/{enemy.max_hp} | DMG: {enemy.dmg}", True, WHITE)
                    self.screen.blit(s, (cx - s.get_width()//2, cy + 10))
                    s = self.font.render("[SPACE] Útok  [H] Heal  [U] Útěk", True, GOLD)
                    self.screen.blit(s, (cx - s.get_width()//2, cy + 50))
            
            elif self.state == "SHOP":
                self.draw_shop()
            
            elif self.state == "LEVELUP":
                self.screen.fill(BLACK)
                t = self.title_font.render("LEVEL UP! Vyber bonus:", True, GOLD)
                self.screen.blit(t, (350, 100))
                opts = ["1. VIGOR", "2. STR", "3. DEX", "4. INT", "5. LUCK", "6. DEF"]
                for i, o in enumerate(opts):
                    s = self.font.render(o, True, WHITE)
                    self.screen.blit(s, (400, 180 + i*40))
            
            elif self.state == "NEXT_FLOOR":
                self.screen.fill(BLACK)
                t = self.big_font.render("BOSS PORAŽEN!", True, GOLD)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 200))
                t = self.title_font.render(f"Dokončeno patro {self.floor}", True, WHITE)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 280))
                t = self.font.render("Stiskni [ENTER] pro vstup do hlubšího patra.", True, CYAN)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 400))
                
            elif self.state == "GAMEOVER":
                t = self.big_font.render("KONEC HRY", True, RED)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))

            pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
