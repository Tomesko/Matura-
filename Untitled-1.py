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

# Solo Leveling Colors
SL_BLACK = (10, 10, 15)
SL_BLUE = (0, 150, 255)
SL_TEXT = (200, 220, 255)
SL_RED = (255, 50, 50)
SL_PURPLE = (180, 50, 255)
SL_GOLD = (255, 215, 0)
SL_DARK_BLUE = (0, 50, 100)
SL_GREEN = (50, 255, 50)
SL_GRAY = (100, 100, 100)

# --- BESTIÁŘ ---
DEMON_TYPES = [
    ("Low Rank Demon", 1,  (100, 100, 100), 20, 5, 10),
    ("Flying Demon",   3,  (150, 100, 100), 30, 8, 15),
    ("Cerberus",       5,  (150, 50, 0),    60, 15, 50),
    ("High Orc",       10, (0, 100, 0),     80, 20, 40),
    ("Demon Knight",   15, (50, 0, 100),    120, 30, 80),
    ("Arch-Lich",      20, (100, 0, 200),   150, 50, 150),
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
    def __init__(self, db_name="sololeveling_v12.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hunters (
                id INTEGER PRIMARY KEY, 
                date TEXT, 
                name TEXT,
                class TEXT, 
                floor INTEGER, 
                level INTEGER, 
                souls INTEGER
            )
        ''')
        self.conn.commit()

    def save_run(self, name, p_class, floor, level, souls):
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute('INSERT INTO hunters (date, name, class, floor, level, souls) VALUES (?,?,?,?,?,?)', 
                           (date, name, p_class, floor, level, souls))
        self.conn.commit()

    def get_rankings(self):
        self.cursor.execute('SELECT * FROM hunters ORDER BY floor DESC, level DESC LIMIT 10')
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
        
        # --- NOVÉ: Ukládání minulé pozice pro útěk ---
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
            dmg = self.stats["int"] * 5
            return dmg
        return 0

class Enemy:
    def __init__(self, floor, is_boss=False):
        self.is_boss = is_boss
        scale = 1.0 + (floor * 0.15)
        
        if is_boss:
            if floor < 20: name = "VULCAN (Lower Boss)"
            elif floor < 50: name = "METUS (Guide of Souls)"
            else: name = "BARAN (Monarch)"
            self.name = name
            self.color = SL_RED
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

class Room:
    def __init__(self, from_dir=None):
        self.enemies = []
        self.exits = {'N':False, 'S':False, 'E':False, 'W':False}
        for d in ['N','S','E','W']: 
            if random.random() > 0.4: self.exits[d] = True
        if from_dir:
            opp = {'N':'S', 'S':'N', 'E':'W', 'W':'E'}
            self.exits[opp[from_dir]] = True

# --- GAME ENGINE ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Solo Leveling: v12.1 (Escape Fix)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Verdana", 16)
        self.title_font = pygame.font.SysFont("Verdana", 28, bold=True)
        
        self.db = DatabaseManager()
        self.state = "INPUT_NAME"
        self.input_text = ""
        self.selected_class = "FIGHTER"
        
        self.pending_level_up = False
        self.next_state_after_levelup = "EXPLORE"
        
        self.boss_active = False
        self.boss_coords = None
        self.player_moves = 0

        self.store = [
            ("Healing Stone", 100),
            ("Knight Killer (Dagger)", 500),
            ("Orb of Avarice (Magic)", 800),
            ("Demon King's Dagger", 2000),
            ("Shadow Armor", 1000),
            ("Daily Quest: Strength (+2 STR)", 300),
            ("Daily Quest: Speed (+2 DEX)", 300)
        ]
        self.store_sel = 0

    def start_game(self):
        name = self.input_text if self.input_text else "Unknown Hunter"
        self.player = Player(name, self.selected_class)
        self.floor = 1
        self.map = {(0,0): Room()}
        self.map[(0,0)].exits = {'N':True, 'S':True, 'E':True, 'W':True}
        self.log = ["SYSTEM: Welcome to the Demon Castle."]
        self.has_key = False
        self.boss_spawned = False
        self.boss_active = False
        self.boss_coords = None
        self.player_moves = 0
        self.pending_level_up = False

    def add_log(self, txt):
        self.log.append(txt)
        if len(self.log) > 6: self.log.pop(0)

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
                self.add_log("SYSTEM: A Boss presence is detected!")
            
            self.map[(x,y)] = r

    def move_boss(self):
        if not self.boss_active or not self.boss_coords:
            return

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
            
            boss_obj = None
            for e in old_room.enemies:
                if e.is_boss:
                    boss_obj = e
                    break
            
            if boss_obj:
                old_room.enemies.remove(boss_obj)
                target_room.enemies.append(boss_obj)
                self.boss_coords = (new_bx, new_by)
                
                if (new_bx, new_by) == (px, py):
                    self.add_log("SYSTEM: THE BOSS FOUND YOU!")
                    self.state = "COMBAT"
                else:
                    self.add_log("SYSTEM: Chills down your spine... (Boss moved)")

    def move(self, dx, dy, d_str):
        curr = self.map[(self.player.grid_x, self.player.grid_y)]
        if curr.enemies:
            self.add_log("SYSTEM: Cannot leave while in combat.")
            return
        if not curr.exits.get(d_str):
            self.add_log("SYSTEM: Path blocked.")
            return
            
        nx, ny = self.player.grid_x + dx, self.player.grid_y + dy
        
        # --- ULOŽENÍ PŘEDCHOZÍ POZICE PRO ÚTĚK ---
        self.player.prev_x = self.player.grid_x
        self.player.prev_y = self.player.grid_y
        # -----------------------------------------
        
        self.generate_room(nx, ny, d_str)
        self.player.grid_x, self.player.grid_y = nx, ny
        
        self.player_moves += 1
        if self.player_moves % 2 == 0:
            self.move_boss()
        
        new_r = self.map[(nx,ny)]
        if new_r.enemies:
            self.state = "COMBAT"
            self.add_log(f"COMBAT: {len(new_r.enemies)} demons appeared!")

    def combat(self, action):
        room = self.map[(self.player.grid_x, self.player.grid_y)]
        target = room.enemies[0]
        
        if action == "RUN":
            cost = 50 * self.floor
            if self.player.souls >= cost:
                self.player.souls -= cost
                
                # --- LOGIKA ÚTĚKU ---
                if target.is_boss:
                    # Pokud je to boss, posuneme hráče ZPĚT do minulé místnosti
                    self.add_log(f"SYSTEM: Retreated from Boss! (-{cost})")
                    self.player.grid_x = self.player.prev_x
                    self.player.grid_y = self.player.prev_y
                    self.state = "EXPLORE"
                else:
                    # Pokud jsou to normální mobové, despawnou se
                    room.enemies = [] 
                    self.add_log(f"SYSTEM: Escaped (-{cost} Souls)")
                    self.state = "EXPLORE"
                # --------------------
            else:
                self.add_log(f"SYSTEM: Need {cost} Souls to escape!")

        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            target.hp -= dmg
            c_txt = " [CRITICAL]" if crit else ""
            self.add_log(f"You hit {target.name} for {dmg}{c_txt}.")
            
            if target.hp <= 0:
                self.add_log(f"SYSTEM: {target.name} defeated.")
                self.player.souls += target.souls
                self.player.xp += target.xp
                
                if random.random() < 0.3:
                    self.player.shadows += 1
                    self.add_log("SYSTEM: Extracted Shadow Essence.")
                
                if self.player.xp >= self.player.xp_next:
                    self.pending_level_up = True
                    self.add_log("SYSTEM: Level Up available!")
                
                is_boss_kill = target.is_boss
                
                if not self.has_key and random.random() < 0.1:
                    self.has_key = True
                    self.add_log("ITEM: Obtained Entry Permit (Key).")

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
                        else:
                            self.next_state_after_levelup = "EXPLORE"
                        return

                    if is_boss_kill:
                        self.floor += 1
                        self.add_log(f"SYSTEM: Floor {self.floor-1} Cleared.")
                        self.state = "NEXT_FLOOR"
                    else:
                        self.state = "EXPLORE"
                return

        elif action == "SHADOWS":
            dmg = self.player.use_shadows()
            if dmg > 0:
                self.add_log(f"SKILL: 'Arise' deals {dmg} to ALL.")
                for e in room.enemies:
                    e.hp -= dmg
                alive = []
                for e in room.enemies:
                    if e.hp <= 0:
                        self.player.souls += e.souls
                        self.player.xp += e.xp
                        if e.is_boss: 
                            self.boss_active = False
                            self.boss_coords = None
                        if self.player.xp >= self.player.xp_next:
                            self.pending_level_up = True
                    else:
                        alive.append(e)
                room.enemies = alive
                
                if not room.enemies:
                    if self.pending_level_up:
                        self.state = "LEVELUP"
                        self.pending_level_up = False
                        self.next_state_after_levelup = "EXPLORE"
                    else:
                        self.state = "EXPLORE"
            else:
                self.add_log("SYSTEM: Not enough Shadows.")
                return

        elif action == "POTION":
            if "Healing Stone" in self.player.inventory:
                self.player.current_hp = min(self.player.max_hp, self.player.current_hp + 50)
                self.player.inventory.remove("Healing Stone")
                self.add_log("ITEM: Used Healing Stone.")
            else:
                self.add_log("SYSTEM: No items.")
                return

        if room.enemies:
            dmg_taken = 0
            for e in room.enemies:
                real_dmg = max(1, e.dmg - self.player.total_def)
                dmg_taken += real_dmg
            
            if dmg_taken > 0:
                self.player.current_hp -= dmg_taken
                self.add_log(f"COMBAT: Took {dmg_taken} dmg from horde.")
                
            if self.player.current_hp <= 0:
                self.db.save_run(self.player.name, self.player.class_name, self.floor, self.player.level, self.player.souls)
                self.state = "GAMEOVER"

    def draw_system_ui(self):
        pygame.draw.rect(self.screen, SL_DARK_BLUE, (0, 0, WIDTH, HEIGHT))
        pygame.draw.rect(self.screen, SL_BLUE, (0, 0, WIDTH, HEIGHT), 2)
        for i in range(0, HEIGHT, 4):
            pygame.draw.line(self.screen, (0, 20, 40), (0, i), (WIDTH, i))

    def draw_map(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                gx, gy = self.player.grid_x + dx, self.player.grid_y - dy
                sx, sy = cx + dx*TILE_SIZE, cy + dy*TILE_SIZE
                
                if (gx, gy) in self.map:
                    room = self.map[(gx, gy)]
                    col = (20, 20, 30) if not room.enemies else (50, 20, 20)
                    pygame.draw.rect(self.screen, col, (sx, sy, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(self.screen, SL_BLUE, (sx, sy, TILE_SIZE, TILE_SIZE), 1)
                    if room.enemies:
                        c = SL_GOLD if room.enemies[0].is_boss else SL_RED
                        pygame.draw.circle(self.screen, c, (sx+30, sy+30), 8 + (len(room.enemies)*2))

        pygame.draw.circle(self.screen, SL_BLUE, (cx+30, cy+30), 10)

    def draw_hud(self):
        px = WIDTH - 280
        pygame.draw.rect(self.screen, (0, 10, 20), (px, 0, 280, HEIGHT))
        pygame.draw.line(self.screen, SL_BLUE, (px, 0), (px, HEIGHT), 2)
        
        y = 20
        def txt(t, c=SL_TEXT, s=0):
            nonlocal y
            f = self.title_font if s else self.font
            self.screen.blit(f.render(t, True, c), (px+15, y))
            y += 30 + s

        txt(f"FLOOR: {self.floor}", SL_BLUE, 5)
        txt(f"{self.player.name.upper()}", SL_TEXT)
        txt(f"CLASS: {self.player.class_name}", SL_GOLD)
        
        y += 10
        pygame.draw.rect(self.screen, (50,0,0), (px+15, y, 200, 15))
        hp_p = self.player.current_hp / self.player.max_hp
        pygame.draw.rect(self.screen, SL_RED, (px+15, y, 200*hp_p, 15))
        y += 20
        pygame.draw.rect(self.screen, (50,50,0), (px+15, y, 200, 8))
        xp_p = self.player.xp / self.player.xp_next
        pygame.draw.rect(self.screen, SL_GOLD, (px+15, y, 200*xp_p, 8))
        y += 20
        
        txt(f"HP: {self.player.current_hp} / {self.player.max_hp}", SL_RED)
        txt(f"SOULS: {self.player.souls}", SL_PURPLE)
        txt(f"SHADOWS: {self.player.shadows}", (100, 100, 255))
        
        y += 20
        txt("NAVIGATION", SL_BLUE)
        curr = self.map[(self.player.grid_x, self.player.grid_y)]
        arrows = {'N':(100,0), 'S':(100,60), 'W':(60,30), 'E':(140,30)}
        base_x, base_y = px + 15, y
        for d, pos in arrows.items():
            color = SL_GREEN if curr.exits[d] else SL_RED
            rect = (base_x + pos[0], base_y + pos[1], 20, 20)
            pygame.draw.rect(self.screen, color, rect)
            self.screen.blit(self.font.render(d, True, SL_BLACK), (base_x + pos[0]+5, base_y + pos[1]))
            
        y += 100
        txt("EQUIPMENT", SL_BLUE, 2)
        txt(f"{self.player.weapon.name}", SL_TEXT)
        txt(f"Dmg: {self.player.weapon.min_dmg}-{self.player.weapon.max_dmg}", (150,150,150))
        
        key_txt = "OBTAINED" if self.has_key else "MISSING"
        col = SL_GREEN if self.has_key else SL_RED
        txt(f"PERMIT: {key_txt}", col)

        ly = HEIGHT - 200
        pygame.draw.line(self.screen, SL_BLUE, (0, ly), (px, ly))
        for i, l in enumerate(self.log):
            c = SL_TEXT
            if "SYSTEM" in l: c = SL_BLUE
            elif "COMBAT" in l: c = SL_RED
            elif "ITEM" in l: c = SL_GOLD
            self.screen.blit(self.font.render(l, True, c), (20, ly + 10 + i*25))

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            
            # --- ANTI-STUCK ---
            if self.state == "EXPLORE":
                curr_room = self.map.get((self.player.grid_x, self.player.grid_y))
                if curr_room and curr_room.enemies:
                    self.state = "COMBAT"

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                if event.type == pygame.KEYDOWN:
                    
                    if self.state == "INPUT_NAME":
                        if event.key == pygame.K_RETURN:
                            if len(self.input_text) > 0: self.state = "MENU"
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            if len(self.input_text) < 12: self.input_text += event.unicode
                    
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
                                if "Healing" in name: self.player.inventory.append(name)
                                elif "Dagger" in name or "Orb" in name: 
                                    self.player.weapon = Weapon(name, int(cost/50), int(cost/30), "str", 1.5, cost)
                                elif "Daily" in name:
                                    if "Strength" in name: self.player.stats["str"] += 2
                                    else: self.player.stats["dex"] += 2
                                    self.player.recalculate()
                                self.add_log(f"SYSTEM: Purchased {name}.")
                            else:
                                self.add_log("SYSTEM: Insufficient Souls.")

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
                         if event.key == pygame.K_RETURN: self.state = "MENU"

            # DRAWING
            if self.state == "INPUT_NAME":
                self.draw_system_ui()
                t = self.title_font.render("HUNTER REGISTRATION", True, SL_BLUE)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 200))
                pygame.draw.rect(self.screen, SL_BLACK, (WIDTH//2 - 150, 300, 300, 50))
                pygame.draw.rect(self.screen, SL_BLUE, (WIDTH//2 - 150, 300, 300, 50), 2)
                txt = self.font.render(self.input_text, True, SL_TEXT)
                self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 315))
                t2 = self.font.render("Enter Name & Press [ENTER]", True, SL_GRAY)
                self.screen.blit(t2, (WIDTH//2 - t2.get_width()//2, 360))

            elif self.state == "MENU":
                self.draw_system_ui()
                t = self.title_font.render("HUNTER GUILD DATABASE", True, SL_BLUE)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 50))
                t = self.title_font.render("TOP RANKINGS", True, SL_GOLD)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 110))
                head_y = 150
                headers = f"{'NAME':<12} {'CLASS':<10} {'FLOOR':<5} {'LVL':<4} {'SOULS'}"
                self.screen.blit(self.font.render(headers, True, SL_BLUE), (WIDTH//2 - 200, head_y))
                pygame.draw.line(self.screen, SL_BLUE, (WIDTH//2-220, head_y+25), (WIDTH//2+220, head_y+25))
                scores = self.db.get_rankings()
                y = 180
                if scores:
                    for row in scores:
                        nm = row[2] if row[2] else "Unknown"
                        cl = row[3]
                        fl = row[4]
                        lv = row[5]
                        sl = row[6]
                        line = f"{nm[:10]:<12} {cl[:9]:<10} {fl:<5} {lv:<4} {sl}"
                        self.screen.blit(self.font.render(line, True, SL_TEXT), (WIDTH//2 - 200, y))
                        y += 25
                else:
                    self.screen.blit(self.font.render("No Data Found.", True, SL_GRAY), (WIDTH//2 - 50, y))
                cx = WIDTH // 2 - 200
                cy = 450
                classes = ["FIGHTER", "ASSASSIN", "MAGE"]
                for i, c in enumerate(classes):
                    col = SL_GOLD if self.selected_class == c else (50,50,50)
                    pygame.draw.rect(self.screen, col, (cx + i*140, cy, 120, 50), 2)
                    self.screen.blit(self.font.render(c, True, SL_TEXT), (cx + i*140 + 10, cy+15))
                if self.selected_class == "MONARCH":
                    self.screen.blit(self.font.render("SECRET CLASS ACTIVE", True, SL_PURPLE), (WIDTH//2-100, 520))
                self.screen.blit(self.font.render("[ENTER] Start Simulation", True, SL_BLUE), (WIDTH//2-100, 580))

            else:
                self.draw_system_ui()
                self.draw_map()
                self.draw_hud()
                
                if self.state == "COMBAT":
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 150))
                    self.screen.blit(overlay, (0,0))
                    room = self.map[(self.player.grid_x, self.player.grid_y)]
                    e = room.enemies[0]
                    cx, cy = WIDTH//2, HEIGHT//2
                    c = SL_GOLD if e.is_boss else SL_RED
                    pygame.draw.rect(self.screen, c, (cx-100, cy-100, 200, 200), 2)
                    self.screen.blit(self.title_font.render(e.name, True, c), (cx-100, cy-140))
                    hp_txt = f"HP: {e.hp} / {e.max_hp}"
                    self.screen.blit(self.font.render(hp_txt, True, SL_TEXT), (cx-50, cy+10))
                    if len(room.enemies) > 1:
                         self.screen.blit(self.font.render(f"+{len(room.enemies)-1} others", True, SL_RED), (cx-50, cy+40))
                    self.screen.blit(self.font.render("[SPACE] Attack", True, SL_BLUE), (cx-120, cy+120))
                    self.screen.blit(self.font.render("[S] Arise", True, SL_PURPLE), (cx, cy+120))
                    self.screen.blit(self.font.render("[H] Heal", True, SL_GREEN), (cx-120, cy+150))
                    self.screen.blit(self.font.render("[U] ESCAPE", True, SL_GRAY), (cx, cy+150))
                
                elif self.state == "STORE":
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 220))
                    self.screen.blit(overlay, (0,0))
                    self.screen.blit(self.title_font.render("SYSTEM STORE", True, SL_BLUE), (100, 100))
                    self.screen.blit(self.font.render(f"Souls: {self.player.souls}", True, SL_PURPLE), (100, 150))
                    for i, item in enumerate(self.store):
                        col = SL_GOLD if i == self.store_sel else SL_TEXT
                        txt = f"{item[0]} ... {item[1]} Souls"
                        if i == self.store_sel: txt = "> " + txt
                        self.screen.blit(self.font.render(txt, True, col), (100, 200 + i*40))

                elif self.state == "LEVELUP":
                    self.screen.blit(self.title_font.render("LEVEL UP!", True, SL_GOLD), (WIDTH//2-50, 100))
                    t = "Choose Stat Bonus (1-5):"
                    self.screen.blit(self.font.render(t, True, SL_TEXT), (WIDTH//2-100, 150))
                    opts = ["1. STR (Physical Dmg)", "2. AGI (Speed/Crit)", "3. INT (Mana/Shadows)", "4. VIT (Health)", "5. SENSE (Crit Chance)"]
                    for i, o in enumerate(opts):
                         self.screen.blit(self.font.render(o, True, SL_BLUE), (WIDTH//2-100, 200+i*30))
                         
                elif self.state == "NEXT_FLOOR":
                    t = self.title_font.render(f"FLOOR {self.floor-1} CLEARED", True, SL_GOLD)
                    self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
                    t = self.font.render("Press [ENTER] to ascend.", True, SL_TEXT)
                    self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 + 50))
                
                elif self.state == "GAMEOVER":
                    t = self.title_font.render("PLAYER DIED", True, SL_RED)
                    self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
                    
            pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.start_game()
    game.run()
