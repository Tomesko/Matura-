import pygame
import random
import math
import time
import sqlite3
import datetime

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 60

# --- BARVY (SOLO LEVELING NEON PALETTE) ---
# Tmavé pozadí
BG_COLOR = (5, 8, 15)
GRID_COLOR = (20, 25, 40)

# Neony
NEON_BLUE = (0, 190, 255)     # System / Player
NEON_RED = (255, 40, 40)      # Enemy / Danger
NEON_GOLD = (255, 215, 0)     # Boss / S-Rank
NEON_PURPLE = (180, 50, 255)  # Magic / Shadows
NEON_GREEN = (50, 255, 100)   # Buffs / Exit
NEON_GRAY = (100, 100, 120)   # Walls / Weak

# Texty
TXT_WHITE = (240, 240, 255)
TXT_GRAY = (150, 150, 170)

# --- BESTIÁŘ ---
DEMON_TYPES = [
    ("Low Rank Demon", 1,  (150, 150, 150), 20, 5, 10),
    ("Flying Demon",   3,  (180, 120, 120), 30, 8, 15),
    ("Cerberus",       5,  (200, 100, 50),  60, 15, 50),
    ("High Orc",       10, (50, 150, 50),   80, 20, 40),
    ("Demon Knight",   15, (100, 100, 200), 120, 30, 80),
    ("Arch-Lich",      20, (150, 50, 200),  150, 50, 150),
]

# --- CLASSES ---
CLASSES = {
    "FIGHTER": {
        "stats": {"vigor": 15, "str": 12, "dex": 5, "int": 5, "sense": 5, "def": 3},
        "weapon": ("Vanguard Shield", 8, 12, "str", 1.0, 0)
    },
    "ASSASSIN": {
        "stats": {"vigor": 8, "str": 8, "dex": 16, "int": 5, "sense": 15, "def": 0},
        "weapon": ("Kasaka's Fang", 10, 18, "dex", 1.3, 0)
    },
    "MAGE": {
        "stats": {"vigor": 6, "str": 4, "dex": 8, "int": 18, "sense": 10, "def": 0},
        "weapon": ("Orb of Greed", 12, 20, "int", 1.4, 0)
    },
    "MONARCH": {
        "stats": {"vigor": 10, "str": 15, "dex": 15, "int": 15, "sense": 15, "def": 2},
        "weapon": ("Kamish's Wrath", 25, 40, "str", 1.8, 0)
    }
}

# --- DATABÁZE ---
class DatabaseManager:
    def __init__(self, db_name="sololeveling_v13_5.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hunters (
                id INTEGER PRIMARY KEY, date TEXT, name TEXT, class TEXT, 
                floor INTEGER, level INTEGER, souls INTEGER
            )
        ''')
        self.conn.commit()

    def save_run(self, name, p_class, floor, level, souls):
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute('INSERT INTO hunters (date, name, class, floor, level, souls) VALUES (?,?,?,?,?,?)', 
                           (date, name, p_class, floor, level, souls))
        self.conn.commit()

    def get_rankings(self):
        self.cursor.execute('SELECT * FROM hunters ORDER BY floor DESC, level DESC LIMIT 8')
        return self.cursor.fetchall()

# --- ENTITY ---
class Weapon:
    def __init__(self, name, min_d, max_d, stat, rank, val):
        self.name, self.min_dmg, self.max_dmg = name, min_d, max_d
        self.scaling_stat, self.scaling_rank, self.value = stat, rank, val

class Player:
    def __init__(self, name, class_key="FIGHTER"):
        self.name = name
        self.grid_x, self.grid_y = 0, 0
        self.prev_x, self.prev_y = 0, 0
        self.class_name = class_key
        
        c = CLASSES[class_key]
        self.stats = c["stats"].copy()
        
        self.level, self.xp, self.xp_next = 1, 0, 100
        self.souls = 0
        self.shadows = 0
        
        w = c["weapon"]
        self.weapon = Weapon(w[0], w[1], w[2], w[3], w[4], w[5])
        self.inventory = ["Healing Stone"]
        
        self.max_hp = 0
        self.current_hp = 0
        self.total_def = 0
        
        self.recalculate()
        self.current_hp = self.max_hp

    def recalculate(self):
        self.max_hp = (self.stats["vigor"] * 10)
        self.total_def = self.stats["def"] + (self.stats["str"] // 5)
        if self.current_hp > self.max_hp: self.current_hp = self.max_hp

    def attack(self):
        base = random.randint(self.weapon.min_dmg, self.weapon.max_dmg)
        stat = self.stats.get(self.weapon.scaling_stat, 10)
        bonus = int(stat * self.weapon.scaling_rank)
        total = base + bonus
        
        crit_chance = min(self.stats["sense"], 50)
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit: total = int(total * 1.5)
        return total, is_crit

    def use_shadows(self):
        if self.shadows >= 3:
            self.shadows -= 3
            return self.stats["int"] * 5
        return 0
    
    def get_power_rating(self):
        avg_dmg = (self.weapon.min_dmg + self.weapon.max_dmg) / 2
        stat_bonus = self.stats[self.weapon.scaling_stat] * self.weapon.scaling_rank
        return self.max_hp + ((avg_dmg + stat_bonus) * 6) + (self.total_def * 5)

class Enemy:
    def __init__(self, floor, is_boss=False):
        self.is_boss = is_boss
        scale = 1.0 + (floor * 0.15)
        
        if is_boss:
            if floor < 20: name = "VULCAN"
            elif floor < 50: name = "METUS"
            else: name = "BARAN"
            self.name = name
            self.color = NEON_RED # Boss is Red/Gold logic handled in draw
            self.hp = int(300 * scale)
            self.dmg = int(30 * scale)
            self.xp, self.souls = int(500 * scale), int(300 * scale)
        else:
            avail = [e for e in DEMON_TYPES if e[1] <= floor]
            if not avail: avail = [DEMON_TYPES[0]]
            choice = random.choice(avail)
            self.name = choice[0]
            self.color = choice[2]
            self.hp = int(choice[3] * scale)
            self.dmg = int(choice[4] * scale)
            self.xp = int(20 * scale)
            self.souls = int(choice[5] * scale)
        self.max_hp = self.hp

    def get_power_rating(self):
        return self.max_hp + (self.dmg * 6)

class Room:
    def __init__(self, from_dir=None):
        self.enemies = []
        self.exits = {'N':False, 'S':False, 'E':False, 'W':False}
        for d in ['N','S','E','W']: 
            if random.random() > 0.4: self.exits[d] = True
        if from_dir:
            opp = {'N':'S', 'S':'N', 'E':'W', 'W':'E'}
            self.exits[opp[from_dir]] = True

# --- GRAPHICS HELPER ---
def draw_glow_rect(surface, color, rect, thickness=2, glow_size=10):
    # Main rect
    pygame.draw.rect(surface, color, rect, thickness)
    # Glow effect
    for i in range(glow_size):
        alpha = int(100 - (i * (100/glow_size)))
        s = pygame.Surface((rect[2] + i*2, rect[3] + i*2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2] + i*2, rect[3] + i*2), 1)
        surface.blit(s, (rect[0] - i, rect[1] - i))

# --- GAME ENGINE ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Solo Leveling: System Interface")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 40)
        self.db = DatabaseManager()
        
        self.state = "INPUT_NAME"
        self.input_text = ""
        self.selected_class = "FIGHTER"
        self.store = []
        self.reset_game_data()

    def reset_game_data(self):
        self.player = None
        self.floor = 1
        self.map = {}
        self.log = []
        self.has_key = False
        self.boss_spawned = False
        self.boss_active = False
        self.boss_coords = None
        self.player_moves = 0
        self.pending_level_up = False
        self.store = [
            ("Healing Stone", 100),
            ("Knight Killer (Dagger)", 500),
            ("Daily Quest: Strength (+2 STR)", 300),
            ("Daily Quest: Speed (+2 DEX)", 300)
        ]

    def check_shop_unlocks(self):
        if self.floor >= 5:
            for i in [("Elixir of Life", 500), ("Shadow Armor", 1500)]:
                if i not in self.store: self.store.append(i)
        if self.floor >= 10:
            for i in [("Demon King's Sword", 2500), ("Orb of Avarice", 2000)]:
                if i not in self.store: self.store.append(i)
        if self.floor >= 15:
            for i in [("Monarch's Daggers", 5000), ("Rune: Stealth", 3000)]:
                if i not in self.store: self.store.append(i)

    def start_game(self):
        name = self.input_text if self.input_text else "Hunter"
        self.player = Player(name, self.selected_class)
        self.floor = 1
        self.map = {(0,0): Room()}
        self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
        self.log = ["SYSTEM: Welcome Player."]
        self.has_key = False
        self.boss_spawned = False
        self.boss_active = False
        self.boss_coords = None
        self.player_moves = 0
        self.pending_level_up = False

    def add_log(self, txt):
        self.log.append(txt)
        if len(self.log) > 8: self.log.pop(0)

    def generate_room(self, x, y, from_dir):
        if (x,y) not in self.map:
            r = Room(from_dir)
            spawn_chance = 0.5 + (self.floor * 0.02)
            if random.random() < spawn_chance:
                count = random.randint(1, 3)
                for _ in range(count):
                    r.enemies.append(Enemy(self.floor))
            
            dist = math.sqrt(x**2 + y**2)
            if self.has_key and not self.boss_spawned and dist > 5:
                boss = Enemy(self.floor, is_boss=True)
                r.enemies = [boss]
                self.boss_spawned = True
                self.boss_active = True
                self.boss_coords = (x, y)
                self.add_log("WARNING: Boss Signature Detected!")
            self.map[(x,y)] = r

    def move_boss(self):
        if not self.boss_active or not self.boss_coords: return
        bx, by = self.boss_coords
        px, py = self.player.grid_x, self.player.grid_y
        if (bx, by) == (px, py): return

        new_bx, new_by = bx, by
        if bx < px: new_bx += 1
        elif bx > px: new_bx -= 1
        if new_bx == bx:
            if by < py: new_by += 1
            elif by > py: new_by -= 1
        
        if (new_bx, new_by) in self.map:
            old_room = self.map[(bx, by)]
            target_room = self.map[(new_bx, new_by)]
            boss_obj = next((e for e in old_room.enemies if e.is_boss), None)
            
            if boss_obj:
                old_room.enemies.remove(boss_obj)
                target_room.enemies.append(boss_obj)
                self.boss_coords = (new_bx, new_by)
                if (new_bx, new_by) == (px, py):
                    self.add_log("ALERT: BOSS HAS FOUND YOU!")
                    self.state = "COMBAT"
                else:
                    self.add_log("ALERT: Boss is moving...")

    def move(self, dx, dy, d_str):
        curr = self.map[(self.player.grid_x, self.player.grid_y)]
        if curr.enemies:
            self.add_log("COMBAT: Cannot leave.")
            return
        if not curr.exits.get(d_str):
            self.add_log("SYSTEM: Path Blocked.")
            return
            
        nx, ny = self.player.grid_x + dx, self.player.grid_y + dy
        self.player.prev_x, self.player.prev_y = self.player.grid_x, self.player.grid_y
        self.generate_room(nx, ny, d_str)
        self.player.grid_x, self.player.grid_y = nx, ny
        
        self.player_moves += 1
        if self.player_moves % 2 == 0: self.move_boss()
        
        new_r = self.map[(nx,ny)]
        if new_r.enemies:
            self.state = "COMBAT"
            self.add_log(f"ENEMIES: {len(new_r.enemies)} targets.")

    def combat(self, action):
        room = self.map[(self.player.grid_x, self.player.grid_y)]
        target = room.enemies[0]
        
        if action == "RUN":
            cost = 50 * self.floor
            if self.player.souls >= cost:
                self.player.souls -= cost
                if target.is_boss:
                    self.add_log(f"RETREAT: Moved back (-{cost})")
                    self.player.grid_x, self.player.grid_y = self.player.prev_x, self.player.prev_y
                else:
                    room.enemies = [] 
                    self.add_log(f"ESCAPE: Success (-{cost})")
                self.state = "EXPLORE"
            else: self.add_log("SYSTEM: Insufficient Souls to escape.")

        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            target.hp -= dmg
            tag = " [CRIT]" if crit else ""
            self.add_log(f"ATTACK: {dmg}{tag}")
            
            if target.hp <= 0:
                self.add_log(f"KILL: {target.name}")
                self.player.souls += target.souls
                self.player.xp += target.xp
                if random.random() < 0.3: self.player.shadows += 1
                if self.player.xp >= self.player.xp_next: self.pending_level_up = True
                
                is_boss_kill = target.is_boss
                if not self.has_key and random.random() < 0.1:
                    self.has_key = True
                    self.add_log("ITEM: Entry Permit Obtained.")

                room.enemies.pop(0)
                if not room.enemies:
                    if is_boss_kill:
                        self.boss_active = False
                        self.boss_coords = None
                    if self.pending_level_up:
                        self.state = "LEVELUP"
                        self.pending_level_up = False
                        if is_boss_kill:
                            self.next_state_after_levelup = "NEXT_FLOOR"
                            self.floor += 1
                            self.check_shop_unlocks()
                        else: self.next_state_after_levelup = "EXPLORE"
                        return
                    if is_boss_kill:
                        self.floor += 1
                        self.check_shop_unlocks()
                        self.add_log(f"SYSTEM: Floor {self.floor-1} Cleared.")
                        self.state = "NEXT_FLOOR"
                    else: self.state = "EXPLORE"
                return

        elif action == "SHADOWS":
            dmg = self.player.use_shadows()
            if dmg > 0:
                self.add_log(f"SKILL: Arise deals {dmg} to all.")
                for e in room.enemies: e.hp -= dmg
                alive = [e for e in room.enemies if e.hp > 0]
                
                # Check dead
                for e in room.enemies:
                    if e.hp <= 0:
                        self.player.souls += e.souls
                        self.player.xp += e.xp
                        if e.is_boss: 
                            self.boss_active = False; self.boss_coords = None
                        if self.player.xp >= self.player.xp_next: self.pending_level_up = True
                
                room.enemies = alive
                if not room.enemies:
                    if self.pending_level_up:
                        self.state = "LEVELUP"
                        self.pending_level_up = False
                        self.next_state_after_levelup = "EXPLORE"
                    else: self.state = "EXPLORE"
            else: self.add_log("SYSTEM: Need 3 Shadows.")

        elif action == "POTION":
            if "Healing Stone" in self.player.inventory:
                self.player.current_hp = min(self.player.max_hp, self.player.current_hp + 50)
                self.player.inventory.remove("Healing Stone")
                self.add_log("USED: Healing Stone.")
            elif "Elixir of Life" in self.player.inventory:
                self.player.current_hp = self.player.max_hp
                self.player.inventory.remove("Elixir of Life")
                self.add_log("USED: Elixir of Life.")
            else: self.add_log("SYSTEM: No healing items.")

        if room.enemies:
            dmg_taken = sum(max(1, e.dmg - self.player.total_def) for e in room.enemies)
            if dmg_taken > 0:
                self.player.current_hp -= dmg_taken
                self.add_log(f"DAMAGE: Took {dmg_taken} dmg.")
            if self.player.current_hp <= 0:
                self.db.save_run(self.player.name, self.player.class_name, self.floor, self.player.level, self.player.souls)
                self.state = "GAMEOVER"

    def get_name_color(self, enemy):
        p_pow = self.player.get_power_rating()
        e_pow = enemy.get_power_rating()
        if e_pow > p_pow * 1.3: return NEON_RED
        elif p_pow > e_pow * 1.5: return NEON_GRAY
        else: return NEON_GOLD

    # --- DRAWING SYSTEM ---
    def draw_bg(self):
        self.screen.fill(BG_COLOR)
        # Grid lines
        for x in range(0, WIDTH, 40):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WIDTH, y))
        # Main border
        pygame.draw.rect(self.screen, NEON_BLUE, (0,0,WIDTH,HEIGHT), 2)

    def draw_menu(self):
        self.draw_bg()
        t = self.title_font.render("SOLO LEVELING", True, NEON_BLUE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 50))
        
        # Rankings Box
        pygame.draw.rect(self.screen, (0,0,0), (WIDTH//2 - 250, 120, 500, 250))
        draw_glow_rect(self.screen, NEON_BLUE, (WIDTH//2 - 250, 120, 500, 250), 2)
        
        scores = self.db.get_rankings()
        y = 140
        self.screen.blit(self.font.render("TOP HUNTERS", True, NEON_GOLD), (WIDTH//2-60, y))
        y += 30
        if scores:
            for row in scores:
                t = f"{row[2][:10]:<12} {row[3]:<8} Flr:{row[4]} Lvl:{row[5]}"
                self.screen.blit(self.font.render(t, True, TXT_WHITE), (WIDTH//2 - 220, y))
                y += 25
        else:
            self.screen.blit(self.font.render("No Data.", True, TXT_GRAY), (WIDTH//2-40, y))

        # Class Selection
        cx = WIDTH // 2 - 200
        cy = 450
        classes = ["FIGHTER", "ASSASSIN", "MAGE"]
        for i, c in enumerate(classes):
            col = NEON_GOLD if self.selected_class == c else NEON_GRAY
            rect = (cx + i*140, cy, 120, 60)
            pygame.draw.rect(self.screen, (10,10,20), rect)
            draw_glow_rect(self.screen, col, rect, 2 if self.selected_class == c else 1)
            self.screen.blit(self.font.render(c, True, col), (cx + i*140 + 15, cy+20))
        
        if self.selected_class == "MONARCH":
            self.screen.blit(self.font.render(">>> SECRET CLASS ACTIVE <<<", True, NEON_PURPLE), (WIDTH//2-140, 530))

        t = self.font.render("Press [ENTER] to Initialize", True, TXT_WHITE)
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 600))

    def draw_game(self):
        self.draw_bg()
        
        # --- MAP ---
        cx, cy = WIDTH // 2, HEIGHT // 2
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                gx, gy = self.player.grid_x + dx, self.player.grid_y - dy
                sx, sy = cx + dx*TILE_SIZE, cy + dy*TILE_SIZE
                
                if (gx, gy) in self.map:
                    room = self.map[(gx, gy)]
                    has_enemy = len(room.enemies) > 0
                    
                    # Wall Glow
                    color = NEON_RED if has_enemy else NEON_GRAY
                    pygame.draw.rect(self.screen, (10,10,15), (sx, sy, TILE_SIZE, TILE_SIZE))
                    draw_glow_rect(self.screen, color, (sx, sy, TILE_SIZE, TILE_SIZE), 1, 5)
                    
                    # Enemies
                    if has_enemy:
                        ec = NEON_GOLD if room.enemies[0].is_boss else NEON_RED
                        pygame.draw.circle(self.screen, ec, (sx+30, sy+30), 10 + len(room.enemies)*2)

        # Player
        pygame.draw.circle(self.screen, NEON_BLUE, (cx+30, cy+30), 12)
        s = pygame.Surface((40,40), pygame.SRCALPHA)
        pygame.draw.circle(s, (*NEON_BLUE, 100), (20,20), 18)
        self.screen.blit(s, (cx+10, cy+10))

        # --- HUD ---
        px = WIDTH - 300
        pygame.draw.rect(self.screen, (5, 10, 15), (px, 0, 300, HEIGHT))
        pygame.draw.line(self.screen, NEON_BLUE, (px, 0), (px, HEIGHT), 2)
        
        y = 20
        def txt(t, c=TXT_WHITE, sz=24):
            nonlocal y
            f = pygame.font.Font(None, sz)
            self.screen.blit(f.render(t, True, c), (px+20, y))
            y += sz + 5

        txt(f"FLOOR: {self.floor}", NEON_BLUE, 40)
        txt(f"{self.player.name}", TXT_WHITE)
        txt(f"{self.player.class_name}", NEON_GOLD)
        y+=10
        # Bars
        pygame.draw.rect(self.screen, (50,0,0), (px+20, y, 250, 15))
        pygame.draw.rect(self.screen, NEON_RED, (px+20, y, 250*(self.player.current_hp/self.player.max_hp), 15))
        y+=20
        pygame.draw.rect(self.screen, (50,50,0), (px+20, y, 250, 8))
        pygame.draw.rect(self.screen, NEON_GOLD, (px+20, y, 250*(self.player.xp/self.player.xp_next), 8))
        y+=15
        
        txt(f"HP: {self.player.current_hp}/{self.player.max_hp}", NEON_RED)
        txt(f"Souls: {self.player.souls}", NEON_PURPLE)
        txt(f"Shadows: {self.player.shadows}", NEON_BLUE)
        
        y+=10
        txt("STATS", NEON_BLUE)
        s = self.player.stats
        txt(f"STR: {s['str']}  INT: {s['int']}", TXT_GRAY)
        txt(f"AGI: {s['dex']}  VIT: {s['vigor']}", TXT_GRAY)
        txt(f"SNS: {s['sense']}  DEF: {self.player.total_def}", TXT_GRAY)
        
        y+=10
        txt("WEAPON", NEON_BLUE)
        txt(f"{self.player.weapon.name}", TXT_WHITE)
        
        # Navigation
        y+=20
        curr = self.map.get((self.player.grid_x, self.player.grid_y))
        if curr:
            for d, pos in {'N':(100,0), 'S':(100,60), 'W':(60,30), 'E':(140,30)}.items():
                c = NEON_GREEN if curr.exits[d] else NEON_RED
                pygame.draw.rect(self.screen, c, (px+20+pos[0], y+pos[1], 20, 20))
        y+=100
        
        # Log
        for l in self.log:
            c = NEON_BLUE if "SYSTEM" in l else (NEON_RED if "COMBAT" in l else TXT_WHITE)
            self.screen.blit(self.font.render(l, True, c), (20, HEIGHT - 250 + self.log.index(l)*25))

        # Combat Overlay
        if self.state == "COMBAT":
            e = self.map[(self.player.grid_x, self.player.grid_y)].enemies[0]
            col = self.get_name_color(e)
            draw_glow_rect(self.screen, col, (cx-150, cy-150, 300, 100), 2)
            pygame.draw.rect(self.screen, (0,0,0), (cx-150, cy-150, 300, 100))
            self.screen.blit(self.title_font.render(e.name, True, col), (cx-100, cy-130))
            self.screen.blit(self.font.render(f"HP: {e.hp}/{e.max_hp}", True, TXT_WHITE), (cx-50, cy-90))
            
            instr = "[SPACE] ATTACK   [S] ARISE   [U] ESCAPE"
            self.screen.blit(self.font.render(instr, True, NEON_BLUE), (cx-140, cy+100))

    def run(self):
        running = True
        self.store_sel = 0
        while running:
            self.clock.tick(FPS)
            if self.state == "EXPLORE":
                curr_room = self.map.get((self.player.grid_x, self.player.grid_y))
                if curr_room and curr_room.enemies: self.state = "COMBAT"

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    
                    if self.state == "INPUT_NAME":
                        if event.key == pygame.K_RETURN and self.input_text: self.state = "MENU"
                        elif event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                        else: self.input_text += event.unicode
                    
                    elif self.state == "MENU":
                        if event.key == pygame.K_1: self.selected_class = "FIGHTER"
                        elif event.key == pygame.K_2: self.selected_class = "ASSASSIN"
                        elif event.key == pygame.K_3: self.selected_class = "MAGE"
                        elif event.key == pygame.K_9: self.selected_class = "MONARCH"
                        elif event.key == pygame.K_RETURN: 
                            self.start_game()
                            self.state = "EXPLORE"
                    
                    elif self.state == "EXPLORE":
                        if event.key == pygame.K_UP: self.move(0, 1, 'N')
                        elif event.key == pygame.K_DOWN: self.move(0, -1, 'S')
                        elif event.key == pygame.K_RIGHT: self.move(1, 0, 'E')
                        elif event.key == pygame.K_LEFT: self.move(-1, 0, 'W')
                        elif event.key == pygame.K_b: self.state = "STORE"
                    
                    elif self.state == "COMBAT":
                        if event.key == pygame.K_SPACE: self.combat("ATTACK")
                        elif event.key == pygame.K_s: self.combat("SHADOWS")
                        elif event.key == pygame.K_h: self.combat("POTION")
                        elif event.key == pygame.K_u: self.combat("RUN")
                    
                    elif self.state == "STORE":
                        if event.key == pygame.K_b: self.state = "EXPLORE"
                        elif event.key == pygame.K_DOWN: self.store_sel = (self.store_sel + 1) % len(self.store)
                        elif event.key == pygame.K_UP: self.store_sel = (self.store_sel - 1) % len(self.store)
                        elif event.key == pygame.K_RETURN:
                            item = self.store[self.store_sel]
                            name, cost = item
                            if self.player.souls >= cost:
                                self.player.souls -= cost
                                if "Healing" in name or "Elixir" in name: self.player.inventory.append(name)
                                elif "Dagger" in name or "Orb" in name or "Sword" in name: 
                                    self.player.weapon = Weapon(name, int(cost/50), int(cost/30), "str", 1.5, cost)
                                elif "Armor" in name:
                                    self.player.stats["def"] += 5
                                    self.player.recalculate()
                                elif "Daily" in name:
                                    if "Strength" in name: self.player.stats["str"] += 2
                                    else: self.player.stats["dex"] += 2
                                    self.player.recalculate()
                                self.add_log(f"SYSTEM: Purchased {name}.")
                            else: self.add_log("SYSTEM: Insufficient Souls.")
                    
                    elif self.state == "LEVELUP":
                        k = event.key
                        m = {pygame.K_1:'str', pygame.K_2:'dex', pygame.K_3:'int', pygame.K_4:'vigor', pygame.K_5:'sense'}
                        if k in m:
                            for s in self.player.stats: self.player.stats[s] += 1
                            self.player.stats[m[k]] += 2
                            self.player.level += 1
                            self.player.xp -= self.player.xp_next
                            self.player.xp_next = int(self.player.xp_next * 1.2)
                            self.player.recalculate()
                            self.player.current_hp = self.player.max_hp
                            self.state = self.next_state_after_levelup
                    
                    elif self.state == "NEXT_FLOOR":
                        if event.key == pygame.K_RETURN:
                            self.map = {(0,0): Room()}
                            self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
                            self.player.grid_x, self.player.grid_y = 0, 0
                            self.has_key = False
                            self.boss_spawned = False
                            self.state = "EXPLORE"
                    
                    elif self.state == "GAMEOVER":
                        if event.key == pygame.K_RETURN:
                            self.reset_game_data() # RESET DATA
                            self.state = "MENU"

            self.screen.fill(BG_COLOR)
            
            if self.state == "INPUT_NAME":
                t = self.title_font.render("HUNTER REGISTRATION", True, NEON_BLUE)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 200))
                draw_glow_rect(self.screen, NEON_BLUE, (WIDTH//2 - 150, 300, 300, 50), 2)
                txt = self.font.render(self.input_text, True, TXT_WHITE)
                self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 315))
                t2 = self.font.render("Enter Name & Press [ENTER]", True, TXT_GRAY)
                self.screen.blit(t2, (WIDTH//2 - t2.get_width()//2, 360))
                
            elif self.state == "MENU":
                self.draw_menu()
            
            elif self.state == "STORE":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 240))
                self.screen.blit(overlay, (0,0))
                self.screen.blit(self.title_font.render("SYSTEM STORE", True, NEON_BLUE), (100, 50))
                self.screen.blit(self.font.render(f"Souls: {self.player.souls}", True, NEON_PURPLE), (100, 100))
                for i, item in enumerate(self.store):
                    col = NEON_GOLD if i == self.store_sel else TXT_WHITE
                    txt = f"{item[0]} ... {item[1]} Souls"
                    if i == self.store_sel: txt = "> " + txt
                    self.screen.blit(self.font.render(txt, True, col), (100, 150 + i*40))
            
            elif self.state == "LEVELUP":
                self.screen.fill(BG_COLOR)
                self.screen.blit(self.title_font.render("LEVEL UP!", True, NEON_GOLD), (WIDTH//2-80, 100))
                opts = ["1. STR", "2. AGI", "3. INT", "4. VIT", "5. SENSE"]
                for i, o in enumerate(opts):
                    self.screen.blit(self.font.render(o, True, NEON_BLUE), (WIDTH//2-100, 200+i*40))
            
            elif self.state == "NEXT_FLOOR":
                self.screen.fill(BG_COLOR)
                t = self.title_font.render("FLOOR CLEARED", True, NEON_GOLD)
                self.screen.blit(t, (WIDTH//2-100, HEIGHT//2))
                self.screen.blit(self.font.render("[ENTER] Ascend", True, TXT_WHITE), (WIDTH//2-60, HEIGHT//2+50))
                
            elif self.state == "GAMEOVER":
                self.screen.fill((10,0,0))
                t = self.title_font.render("YOU DIED", True, NEON_RED)
                self.screen.blit(t, (WIDTH//2-80, HEIGHT//2))
                self.screen.blit(self.font.render("[ENTER] Return to Menu", True, TXT_WHITE), (WIDTH//2-100, HEIGHT//2+60))
                
            else:
                self.draw_game()

            pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
