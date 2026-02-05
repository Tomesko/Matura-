import pygame
import random
import math
import time
import sqlite3
import datetime

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 30
BOSS_SPAWN_TIME = 900 

# --- BARVY ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLUE = (50, 150, 255)
GOLD = (255, 215, 0)
RED = (255, 50, 50)
GREEN = (50, 200, 50)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
PURPLE = (150, 0, 150)

# Barvy monster
COLOR_RAT = (120, 120, 120)
COLOR_SLIME = (100, 220, 100)
COLOR_SKELETON = (230, 230, 230)
COLOR_ZOMBIE = (40, 100, 40)
COLOR_WOLF = (139, 69, 19)
COLOR_KNIGHT = (100, 0, 0)
COLOR_GHOST = (200, 200, 255)
COLOR_BOSS = (148, 0, 211)

# --- KONFIGURACE CLASS ---
CLASSES = {
    "WARRIOR": {
        "desc": "Tank. Vysoké HP a Obrana.",
        "stats": {"vigor": 15, "str": 12, "dex": 8, "int": 5, "luck": 5, "def": 2},
        "weapon": ("Rezavý Meč", 6, 10, "str", 1.0, 0),
        "armor": ("Kroužková košile", 10, 2, 0)
    },
    "ROGUE": {
        "desc": "DPS. Vysoký Crit a Rychlost.",
        "stats": {"vigor": 8, "str": 8, "dex": 15, "int": 5, "luck": 15, "def": 0},
        "weapon": ("Zlodějská Dýka", 5, 9, "dex", 1.2, 0),
        "armor": ("Kožená vesta", 5, 1, 0)
    },
    "MAGE": {
        "desc": "Glass Cannon. Obří DMG, papírové HP.",
        "stats": {"vigor": 6, "str": 5, "dex": 10, "int": 16, "luck": 10, "def": 0},
        "weapon": ("Učednická Hůl", 8, 14, "int", 1.3, 0),
        "armor": ("Róba", 0, 0, 0)
    },
    # SECRET CLASS
    "REAPER": {
        "desc": "??? (Secret)",
        "stats": {"vigor": 5, "str": 15, "dex": 15, "int": 5, "luck": 20, "def": 0},
        "weapon": ("Kosa Smrti", 15, 25, "dex", 1.5, 0),
        "armor": ("Černý Plášť", 0, 0, 0)
    }
}

# --- BESTIÁŘ ---
ENEMY_TYPES = [
    ("Krysa",      0,   COLOR_RAT,      15,  3,  5,  2),
    ("Sliz",       0,   COLOR_SLIME,    20,  4,  8,  4),
    ("Kostlivec",  60,  COLOR_SKELETON, 35,  8,  15, 8),
    ("Zombie",     120, COLOR_ZOMBIE,   50,  10, 25, 12),
    ("Vlk",        180, COLOR_WOLF,     40,  18, 35, 15),
    ("Duch",       300, COLOR_GHOST,    60,  15, 45, 20),
    ("Temný Rytíř",480, COLOR_KNIGHT,   100, 25, 80, 50),
]

# --- DATABÁZE ---
class DatabaseManager:
    def __init__(self, db_name="dungeon_v9.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS highscores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                class_name TEXT,
                duration_sec INTEGER,
                level INTEGER,
                gold INTEGER,
                score INTEGER
            )
        ''')
        self.conn.commit()

    def save_run(self, class_name, duration, level, gold):
        score = (level * 100) + gold + int(duration * 2)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute('''
            INSERT INTO highscores (date, class_name, duration_sec, level, gold, score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date_str, class_name, int(duration), level, gold, score))
        self.conn.commit()

    def get_top_scores(self, limit=5):
        self.cursor.execute('SELECT date, class_name, duration_sec, level, gold, score FROM highscores ORDER BY score DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()

# --- ITEMY ---
class Item:
    def __init__(self, name, value):
        self.name, self.value = name, value

class Weapon(Item):
    def __init__(self, name, min_dmg, max_dmg, scaling_stat, scaling_rank, value):
        super().__init__(name, value)
        self.min_dmg, self.max_dmg = min_dmg, max_dmg
        self.scaling_stat, self.scaling_rank = scaling_stat, scaling_rank
    
    def get_grade(self):
        if self.scaling_rank >= 1.8: return "S"
        elif self.scaling_rank >= 1.4: return "A"
        elif self.scaling_rank >= 1.0: return "B"
        return "C"

class Armor(Item):
    def __init__(self, name, bonus_hp, bonus_def, value):
        super().__init__(name, value)
        self.bonus_hp, self.bonus_def = bonus_hp, bonus_def

class Potion(Item):
    def __init__(self, name, heal_amount, value):
        super().__init__(name, value)
        self.heal_amount = heal_amount

# --- ENTITY ---
class Player:
    def __init__(self, class_key="WARRIOR"):
        self.grid_x, self.grid_y = 0, 0
        self.class_name = class_key
        
        # Načtení statů z Class Configu
        c_data = CLASSES[class_key]
        # Kopírujeme slovník, abychom nepřepisovali originál
        self.stats = c_data["stats"].copy()
        
        self.level, self.xp, self.xp_next, self.gold = 1, 0, 100, 0
        
        # Načtení equipu z Class Configu
        w_data = c_data["weapon"]
        self.weapon = Weapon(w_data[0], w_data[1], w_data[2], w_data[3], w_data[4], w_data[5])
        
        a_data = c_data["armor"]
        self.armor = Armor(a_data[0], a_data[1], a_data[2], a_data[3])
        
        self.inventory = [Potion("Lektvar", 30, 20)]
        
        self.current_hp = 0
        self.max_hp = 0
        self.total_def = 0
        
        self.recalculate_stats()
        self.current_hp = self.max_hp

    def recalculate_stats(self):
        self.max_hp = (self.stats["vigor"] * 10) + self.armor.bonus_hp
        self.total_def = (self.stats["def"] // 2) + self.armor.bonus_def
        if self.current_hp > self.max_hp: self.current_hp = self.max_hp

    def get_crit_chance(self): return min(self.stats["luck"], 75)

    def attack(self):
        base = random.randint(self.weapon.min_dmg, self.weapon.max_dmg)
        stat_val = self.stats.get(self.weapon.scaling_stat, 10)
        bonus = int(stat_val * self.weapon.scaling_rank)
        total = base + bonus
        is_crit = False
        if random.randint(1, 100) <= self.get_crit_chance():
            is_crit = True
            total = int(total * (1.5 + (self.stats["dex"] * 0.01)))
        return total, is_crit

    def take_damage(self, amount):
        real = max(1, amount - self.total_def)
        self.current_hp -= real
        return real

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            return True
        return False

class Enemy:
    def __init__(self, time_played_sec, is_boss=False):
        self.is_boss = is_boss
        time_mult = 1.0 + ((time_played_sec / 60) * 0.25) # Trochu rychlejší škálování
        
        if is_boss:
            self.name = "SMRŤÁK"
            self.color = COLOR_BOSS
            self.hp = int(1200 * time_mult)
            self.dmg = int(55 * time_mult)
            self.xp, self.gold = 2000, 1000
        else:
            available = [e for e in ENEMY_TYPES if e[1] <= time_played_sec]
            if not available: available = [ENEMY_TYPES[0]]
            choice = random.choice(available)
            name, mt, col, b_hp, b_dmg, b_xp, b_gold = choice
            
            self.name = name
            self.color = col
            self.hp = int(b_hp * time_mult)
            self.dmg = int(b_dmg * time_mult)
            self.xp = int(b_xp * time_mult)
            self.gold = int(b_gold * time_mult)
        self.max_hp = self.hp

class Room:
    def __init__(self, x, y, from_dir=None):
        self.visited = False
        # Místo jednoho enemy teď máme seznam (LIST)
        self.enemies = [] 
        
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
        pygame.display.set_caption("Solo Survivors - v9.0 Multi-Enemy & Classes")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 60, bold=True)
        
        self.db = DatabaseManager()
        
        self.shop_items = [
            Potion("Velký Lektvar", 100, 50),
            Weapon("Železná Dýka", 8, 12, "dex", 1.0, 100),
            Weapon("Válečná Sekera", 14, 20, "str", 1.1, 150),
            Weapon("Katana (DEX)", 12, 18, "dex", 1.2, 200),
            Weapon("Magická Hůl (INT)", 10, 30, "int", 1.5, 300),
            Armor("Rytířské brnění", 50, 5, 400),
            Weapon("Gilded Katana (DEX)", 20, 28, "dex", 1.8, 550),
            Weapon("Těžký Palcát", 25, 40, "str", 1.6, 600),
            Weapon("Shojins Lost Katana", 30, 48, "dex", 2.1, 950),
            Weapon("Demons GreatHammer", 35, 55, "str", 2.0, 1100),
            Armor("Dračí kůže", 100, 10, 1200),
            "UPGRADE (+5 DMG)"
        ]
        
        self.shop_selection = 0
        self.selected_class = "WARRIOR" # Default
        self.state = "MENU" # Start in Menu

    def start_new_game(self):
        # Hráč se vytvoří podle vybrané classy
        self.player = Player(self.selected_class)
        self.map = {(0,0): Room(0,0)}
        self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
        self.elapsed_time = 0
        self.boss_spawned = False
        self.message_log = ["Místnosti jsou plné monster!"]

    def log(self, text):
        self.message_log.append(text)
        if len(self.message_log) > 8: self.message_log.pop(0)

    def get_time_str(self):
        mins = int(self.elapsed_time // 60)
        secs = int(self.elapsed_time % 60)
        return f"{mins:02}:{secs:02}"

    def generate_room(self, x, y, from_dir):
        if (x, y) not in self.map:
            room = Room(x, y, from_dir)
            
            # BOSS LOGIKA
            if self.elapsed_time > BOSS_SPAWN_TIME and not self.boss_spawned:
                room.enemies.append(Enemy(self.elapsed_time, is_boss=True))
                self.boss_spawned = True
                self.log("!!! PŘICHÁZÍ SMRT !!!")
            
            # NORMÁLNÍ SPAWN - TEĎ VÍC MONSTER
            elif (x!=0 or y!=0):
                spawn_chance = 0.6 + (self.elapsed_time / 1000)
                if spawn_chance > 0.95: spawn_chance = 0.95
                
                if random.random() < spawn_chance:
                    # Počet monster roste s časem
                    # 0-2 min: 1 enemy
                    # 2-5 min: 1-2 enemies
                    # 5+ min: 1-3 enemies
                    # 10+ min: 2-4 enemies
                    mins = self.elapsed_time / 60
                    min_count = 1
                    max_count = 1
                    if mins > 2: max_count = 2
                    if mins > 5: max_count = 3
                    if mins > 10: min_count = 2; max_count = 4
                    
                    count = random.randint(min_count, max_count)
                    for _ in range(count):
                        room.enemies.append(Enemy(self.elapsed_time))
            
            self.map[(x, y)] = room

    def move_player(self, dx, dy, direction):
        curr_room = self.map[(self.player.grid_x, self.player.grid_y)]
        
        # Pokud jsou v místnosti nějací nepřátelé, zamčeno
        if len(curr_room.enemies) > 0:
            self.log(f"Místnost plná! ({len(curr_room.enemies)} nepřátel)")
            return
            
        if not curr_room.exits.get(direction):
            self.log("Zeď.")
            return

        nx, ny = self.player.grid_x + dx, self.player.grid_y + dy
        from_dir = {'N':'S', 'S':'N', 'E':'W', 'W':'E'}[direction]
        self.generate_room(nx, ny, from_dir)
        self.player.grid_x, self.player.grid_y = nx, ny
        
        new_room = self.map[(nx, ny)]
        if len(new_room.enemies) > 0:
            self.state = "COMBAT"
            self.log(f"PŘEPADENÍ! {len(new_room.enemies)} nepřátel!")

    def combat_round(self, action):
        curr_room = self.map[(self.player.grid_x, self.player.grid_y)]
        
        # Vždy útočíme na prvního v seznamu (target)
        target = curr_room.enemies[0]
        
        if action == "RUN":
            # Cena za útěk roste s počtem nepřátel
            cost = (50 + int(self.elapsed_time / 10)) * len(curr_room.enemies)
            if self.player.gold >= cost:
                self.player.gold -= cost
                self.log(f"Utekl jsi (-{cost} G)!")
                curr_room.enemies = [] # Nepřátelé zmizí (utekl jsi jim)
                self.state = "EXPLORE"
                return
            else: self.log(f"Nemáš {cost} G na útěk!")
            
        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            target.hp -= dmg
            self.log(f"Zásah do {target.name} za {dmg}!")
            
            if target.hp <= 0:
                self.log(f"Zabil jsi {target.name}!")
                self.player.gold += target.gold + (self.player.stats["luck"] * 2)
                lvl_up = self.player.gain_xp(target.xp)
                if random.randint(1,100) < (20 + self.player.stats["luck"]):
                    self.player.inventory.append(Potion("Lektvar", 30, 20))
                    self.log("Drop: Lektvar!")
                
                is_win = target.is_boss
                
                # Odstraníme mrtvolu ze seznamu
                curr_room.enemies.pop(0)
                
                if is_win:
                    self.db.save_run(self.player.class_name, self.elapsed_time, self.player.level, self.player.gold)
                    self.state = "VICTORY"
                    return
                elif lvl_up: 
                    self.state = "LEVELUP"
                    return
                
                # Pokud už nejsou nepřátelé, konec boje
                if len(curr_room.enemies) == 0:
                    self.state = "EXPLORE"
                    return

        elif action == "HEAL":
            potions = [i for i in self.player.inventory if isinstance(i, Potion)]
            if potions:
                pot = potions[0]
                self.player.current_hp = min(self.player.max_hp, self.player.current_hp + pot.heal_amount)
                self.player.inventory.remove(pot)
                self.log(f"Heal: {pot.name}.")
            else: self.log("Nemáš lektvary!")

        # --- TAH NEPŘÁTEL (VŠICHNI ŽIVÍ ÚTOČÍ) ---
        total_dmg = 0
        for e in curr_room.enemies:
            dmg = self.player.take_damage(e.dmg)
            total_dmg += dmg
        
        if total_dmg > 0:
            self.log(f"Dostal jsi {total_dmg} DMG od hordy!")
            
        if self.player.current_hp <= 0:
            self.db.save_run(self.player.class_name, self.elapsed_time, self.player.level, self.player.gold)
            self.state = "GAMEOVER"

    # --- RENDER ---
    def draw_menu(self):
        self.screen.fill(BLACK)
        t = self.big_font.render("SURVIVORS RPG", True, RED)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 50))
        
        # HIGHSCORES
        t = self.title_font.render("HIGHSCORES", True, GOLD)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 130))
        scores = self.db.get_top_scores(4)
        y = 170
        if scores:
            for row in scores:
                # row: date, class, dur, lvl, gold, score
                mins = row[2] // 60
                txt = f"{row[1][:3]} | Lvl {row[3]} | {mins}m | {row[5]} pts"
                t = self.font.render(txt, True, WHITE)
                self.screen.blit(t, (WIDTH//2 - 150, y))
                y += 25

        # CLASS SELECTION
        t = self.title_font.render("VYBER CLASSU (1-3)", True, BLUE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 300))
        
        classes = ["WARRIOR", "ROGUE", "MAGE"]
        cx = WIDTH // 2 - 250
        for i, c_name in enumerate(classes):
            col = YELLOW if self.selected_class == c_name else GRAY
            pygame.draw.rect(self.screen, col, (cx + (i*180), 350, 160, 100), 2)
            self.screen.blit(self.font.render(c_name, True, col), (cx + (i*180) + 10, 360))
            
            # Popis
            desc = CLASSES[c_name]["desc"]
            # Zalamování popisu jen velmi jednoduše
            words = desc.split(". ")
            self.screen.blit(self.font.render(words[0], True, WHITE), (cx + (i*180) + 10, 390))
        
        # Pokud je vybrána tajná classa
        if self.selected_class == "REAPER":
             self.screen.blit(self.title_font.render("SECRET: REAPER SELECTED", True, RED), (WIDTH//2 - 150, 480))

        t = self.title_font.render("[ENTER] Start   [Q] Quit", True, WHITE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 550))

    def draw_map(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                mx, my = self.player.grid_x + dx, self.player.grid_y - dy 
                sx, sy = cx + (dx * TILE_SIZE), cy + (dy * TILE_SIZE)
                if (mx, my) in self.map:
                    room = self.map[(mx, my)]
                    has_enemy = len(room.enemies) > 0
                    
                    col = GRAY if not has_enemy else (50, 50, 50)
                    pygame.draw.rect(self.screen, col, (sx, sy, TILE_SIZE, TILE_SIZE))
                    
                    border_col = BLACK
                    if has_enemy: border_col = RED
                    pygame.draw.rect(self.screen, border_col, (sx, sy, TILE_SIZE, TILE_SIZE), 3 if has_enemy else 1)
                    
                    # Dveře
                    d_col = WHITE
                    if room.exits['N']: pygame.draw.rect(self.screen, d_col, (sx+25, sy, 10, 5))
                    if room.exits['S']: pygame.draw.rect(self.screen, d_col, (sx+25, sy+55, 10, 5))
                    if room.exits['W']: pygame.draw.rect(self.screen, d_col, (sx, sy+25, 5, 10))
                    if room.exits['E']: pygame.draw.rect(self.screen, d_col, (sx+55, sy+25, 5, 10))
                    
                    # Tečky za nepřátele (až 4)
                    if has_enemy:
                        # Vykreslíme tolik teček, kolik je monster
                        offset = 15
                        for i, e in enumerate(room.enemies):
                            ox = (i % 2) * offset
                            oy = (i // 2) * offset
                            pygame.draw.circle(self.screen, e.color, (sx+20+ox, sy+20+oy), 6)
                            
        pygame.draw.circle(self.screen, BLUE, (cx+30, cy+30), 12)

    def draw_ui(self):
        px = WIDTH - 270
        pygame.draw.rect(self.screen, DARK_GRAY, (px, 0, 270, HEIGHT))
        pygame.draw.line(self.screen, WHITE, (px, 0), (px, HEIGHT), 2)
        y = 20
        def txt(text, col=WHITE, s=0):
            nonlocal y
            f = self.title_font if s else self.font
            self.screen.blit(f.render(text, True, col), (px+10, y))
            y += 30 + s
        
        tc = RED if self.elapsed_time > BOSS_SPAWN_TIME else CYAN
        txt(f"TIME: {self.get_time_str()}", tc, 5)
        
        # Zobrazení classy
        txt(f"Class: {self.player.class_name}", GOLD)
        
        y+=10
        txt(f"Lvl: {self.player.level}", WHITE)
        hp_perc = self.player.current_hp / self.player.max_hp
        pygame.draw.rect(self.screen, BLACK, (px+10, y, 200, 20))
        pygame.draw.rect(self.screen, RED, (px+10, y, 200*hp_perc, 20))
        self.screen.blit(self.font.render(f"{self.player.current_hp}/{self.player.max_hp}", True, WHITE), (px+80, y))
        y += 25
        xp_perc = self.player.xp / self.player.xp_next
        pygame.draw.rect(self.screen, BLACK, (px+10, y, 200, 10))
        pygame.draw.rect(self.screen, YELLOW, (px+10, y, 200*xp_perc, 10))
        self.screen.blit(self.font.render(f"XP: {self.player.xp}/{self.player.xp_next}", True, WHITE), (px+80, y-2))
        y += 20
        txt(f"Gold: {self.player.gold}", GOLD)
        y += 10
        txt("STATS:", col=GOLD, s=2)
        txt(f"STR: {self.player.stats['str']} | DEX: {self.player.stats['dex']}")
        txt(f"INT: {self.player.stats['int']} | LUC: {self.player.stats['luck']}")
        txt(f"Crit: {self.player.get_crit_chance()}% | DEF: {self.player.total_def}", CYAN)
        y+=10
        w = self.player.weapon
        txt(f"{w.name}", BLUE)
        txt(f"DMG: {w.min_dmg}-{w.max_dmg}", GRAY)
        txt(f"Rank: {w.get_grade()}", GOLD if w.get_grade()=="S" else WHITE)

        log_y = HEIGHT - 200
        pygame.draw.line(self.screen, WHITE, (0, log_y), (px, log_y))
        for i, msg in enumerate(self.message_log):
            c = WHITE
            if "SMRT" in msg or "BOSS" in msg: c = RED
            elif "Drop" in msg: c = GREEN
            self.screen.blit(self.font.render(msg, True, c), (20, log_y + 10 + i*20))

    def draw_shop(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0,0))
        t = self.title_font.render("SHOP (Paused)", True, BLUE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 30))
        t = self.font.render(f"Gold: {self.player.gold}", True, GOLD)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 70))
        
        start_y = 120
        items_per_col = 10
        col_width = 450
        for i, item in enumerate(self.shop_items):
            col_idx = i // items_per_col
            row_idx = i % items_per_col
            x_pos = 50 + (col_idx * col_width)
            y_pos = start_y + (row_idx * 50)
            
            color = WHITE
            prefix = ""
            if i == self.shop_selection:
                color = YELLOW
                prefix = "> "
            
            if isinstance(item, str):
                txt = f"{prefix}{item} (500 G)"
                price = 500
            else:
                rank = ""
                if isinstance(item, Weapon): rank = f" [{item.get_grade()}]"
                txt = f"{prefix}{item.name}{rank} ({item.value} G)"
                price = item.value
            
            if self.player.gold < price and i != self.shop_selection: color = GRAY
            self.screen.blit(self.font.render(txt, True, color), (x_pos, y_pos))
            
        s = self.font.render("Šipky = Výběr, ENTER = Koupit, [B] = Zpět", True, RED)
        self.screen.blit(s, (WIDTH//2 - s.get_width()//2, HEIGHT - 50))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            if self.state in ["EXPLORE", "COMBAT"]:
                self.elapsed_time += dt / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if self.state == "MENU":
                        # Výběr class
                        if event.key == pygame.K_1: self.selected_class = "WARRIOR"
                        elif event.key == pygame.K_2: self.selected_class = "ROGUE"
                        elif event.key == pygame.K_3: self.selected_class = "MAGE"
                        elif event.key == pygame.K_9: self.selected_class = "REAPER" # SECRET
                        
                        elif event.key == pygame.K_RETURN: 
                            self.start_new_game()
                            self.state = "EXPLORE"
                        elif event.key == pygame.K_q: running = False
                    
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
                        elif event.key == pygame.K_DOWN: self.shop_selection = (self.shop_selection + 1) % len(self.shop_items)
                        elif event.key == pygame.K_UP: self.shop_selection = (self.shop_selection - 1) % len(self.shop_items)
                        elif event.key == pygame.K_RETURN:
                            itm = self.shop_items[self.shop_selection]
                            price = 500 if isinstance(itm, str) else itm.value
                            if self.player.gold >= price:
                                self.player.gold -= price
                                if isinstance(itm, str):
                                    self.player.weapon.min_dmg += 5
                                    self.player.weapon.max_dmg += 5
                                    self.log("UPGRADE: +5 DMG")
                                else:
                                    if isinstance(itm, Weapon): self.player.weapon = itm
                                    elif isinstance(itm, Armor): self.player.armor = itm; self.player.recalculate_stats()
                                    else: self.player.inventory.append(itm)
                                    self.log(f"Koupeno: {itm.name}")
                            else: self.log("Na to nemáš zlato!")

                    elif self.state == "LEVELUP":
                        k = event.key
                        m = {pygame.K_1:'vigor', pygame.K_2:'str', pygame.K_3:'dex', pygame.K_4:'int', pygame.K_5:'luck', pygame.K_6:'def'}
                        if k in m:
                            s = m[k]
                            for st in self.player.stats: self.player.stats[st] += 1
                            self.player.stats[s] += 1
                            self.player.recalculate_stats()
                            self.player.current_hp = self.player.max_hp
                            self.state = "EXPLORE"
                    elif self.state in ["GAMEOVER", "VICTORY"]:
                        if event.key == pygame.K_RETURN: self.state = "MENU"

            self.screen.fill(BLACK)
            if self.state == "MENU": self.draw_menu()
            elif self.state in ["EXPLORE", "COMBAT"]:
                self.draw_map()
                self.draw_ui()
                if self.state == "COMBAT":
                    # Kreslení souboje s více nepřáteli
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 180))
                    self.screen.blit(overlay, (0,0))
                    
                    curr_room = self.map[(self.player.grid_x, self.player.grid_y)]
                    # Zobrazíme jen prvního nepřítele (target) detailně
                    if len(curr_room.enemies) > 0:
                        e = curr_room.enemies[0]
                        cx, cy = WIDTH//2, HEIGHT//2
                        pygame.draw.rect(self.screen, e.color, (cx-150, cy-100, 300, 200), 4)
                        pygame.draw.rect(self.screen, e.color, (cx-40, cy-80, 80, 80))
                        
                        count_info = f" (+{len(curr_room.enemies)-1} DALŠÍCH)" if len(curr_room.enemies) > 1 else ""
                        self.screen.blit(self.title_font.render(e.name + count_info, True, WHITE), (cx-150, cy-130))
                        self.screen.blit(self.font.render(f"HP: {e.hp}/{e.max_hp}", True, WHITE), (cx-50, cy+10))
                        self.screen.blit(self.font.render("[SPACE] Attack  [H] Heal", True, GOLD), (cx-100, cy+50))

            elif self.state == "SHOP": self.draw_shop()
            elif self.state == "LEVELUP":
                self.screen.fill(BLACK)
                self.screen.blit(self.title_font.render("LEVEL UP! (1-6)", True, GOLD), (400, 100))
                opts = ["1. VIGOR", "2. STR", "3. DEX", "4. INT", "5. LUCK", "6. DEF"]
                for i,o in enumerate(opts): self.screen.blit(self.font.render(o, True, WHITE), (450, 150+i*40))
            elif self.state in ["GAMEOVER", "VICTORY"]:
                msg = "ZEMŘEL JSI" if self.state == "GAMEOVER" else "VÍTĚZSTVÍ"
                col = RED if self.state == "GAMEOVER" else GOLD
                t = self.big_font.render(msg, True, col)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
                t = self.font.render("[ENTER] Menu", True, WHITE)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 + 80))
            
            pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
