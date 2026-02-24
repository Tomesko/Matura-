import pygame
import random
import math
import time
import sqlite3
import datetime

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 60 # Zvednuto na 60 pro plynulost animací

# --- NEON COLORS (CYBERPUNK PALETTE) ---
BG_COLOR = (5, 5, 10)
GRID_COLOR = (20, 20, 30)

# Neonky
C_PLAYER = (0, 255, 255)      # Cyan
C_WALL = (40, 40, 60)         # Dark Blue Gray
C_FLOOR = (10, 10, 15)
C_TEXT = (255, 255, 255)
C_GOLD = (255, 215, 0)
C_RED = (255, 40, 40)         # Bright Red
C_GREEN = (50, 255, 100)      # Neon Green
C_PURPLE = (180, 50, 255)

# --- BESTIÁŘ ---
DEMON_TYPES = [
    ("Low Demon", 1,  (150, 150, 150), 20, 5, 10),
    ("Imp",       3,  (200, 100, 100), 30, 8, 15),
    ("Cerberus",  5,  (255, 100, 0),   60, 15, 50),
    ("High Orc",  10, (50, 200, 50),   80, 20, 40),
    ("Knight",    15, (100, 100, 255), 120, 30, 80),
    ("Lich",      20, (200, 50, 200),  150, 50, 150),
]

# --- CLASSES ---
CLASSES = {
    "FIGHTER": {"stats": {"vigor": 15, "str": 12, "dex": 5, "int": 5, "sense": 5, "def": 3}, "w": ("Shield", 8, 12, "str", 1.0, 0)},
    "ASSASSIN": {"stats": {"vigor": 8, "str": 8, "dex": 16, "int": 5, "sense": 15, "def": 0}, "w": ("Dagger", 10, 18, "dex", 1.3, 0)},
    "MAGE": {"stats": {"vigor": 6, "str": 4, "dex": 8, "int": 18, "sense": 10, "def": 0}, "w": ("Staff", 12, 20, "int", 1.4, 0)},
    "MONARCH": {"stats": {"vigor": 10, "str": 15, "dex": 15, "int": 15, "sense": 15, "def": 2}, "w": ("Kamish", 25, 40, "str", 1.8, 0)}
}

# --- PARTICLES SYSTEM (Částicové efekty) ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(20, 40)
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, surface):
        if self.life > 0:
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, min(255, self.life * 10)), (self.size, self.size), self.size)
            surface.blit(s, (self.x - self.size, self.y - self.size))

# --- DATABÁZE ---
class DatabaseManager:
    def __init__(self, db_name="sololeveling_final.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS hunters (id INTEGER PRIMARY KEY, date TEXT, name TEXT, class TEXT, floor INTEGER, level INTEGER, souls INTEGER)')
        self.conn.commit()

    def save_run(self, name, p_class, floor, level, souls):
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute('INSERT INTO hunters (date, name, class, floor, level, souls) VALUES (?,?,?,?,?,?)', (date, name, p_class, floor, level, souls))
        self.conn.commit()

    def get_rankings(self):
        self.cursor.execute('SELECT * FROM hunters ORDER BY floor DESC, level DESC LIMIT 8')
        return self.cursor.fetchall()

# --- ENTITY ---
class Weapon:
    def __init__(self, name, min_d, max_d, stat, rank, val):
        self.name, self.min_dmg, self.max_dmg, self.scaling_stat, self.scaling_rank, self.value = name, min_d, max_d, stat, rank, val

class Player:
    def __init__(self, name, class_key="FIGHTER"):
        self.name = name
        self.grid_x, self.grid_y = 0, 0
        self.prev_x, self.prev_y = 0, 0
        self.class_name = class_key
        c = CLASSES[class_key]
        self.stats = c["stats"].copy()
        self.level, self.xp, self.xp_next = 1, 0, 100
        self.souls, self.shadows = 0, 0
        self.weapon = Weapon(*c["w"])
        self.inventory = ["Healing Stone"]
        self.max_hp, self.current_hp, self.total_def = 0, 0, 0
        self.recalculate()
        self.current_hp = self.max_hp

    def recalculate(self):
        self.max_hp = (self.stats["vigor"] * 10)
        self.total_def = self.stats["def"] + (self.stats["str"] // 5)
        if self.current_hp > self.max_hp: self.current_hp = self.max_hp

    def attack(self):
        base = random.randint(self.weapon.min_dmg, self.weapon.max_dmg)
        bonus = int(self.stats.get(self.weapon.scaling_stat, 10) * self.weapon.scaling_rank)
        total = base + bonus
        is_crit = random.randint(1, 100) <= min(self.stats["sense"], 50)
        if is_crit: total = int(total * 1.5)
        return total, is_crit

    def get_power_rating(self):
        return self.max_hp + (self.weapon.max_dmg * 5) + (self.total_def * 5)

class Enemy:
    def __init__(self, floor, is_boss=False):
        self.is_boss = is_boss
        scale = 1.0 + (floor * 0.15)
        if is_boss:
            self.name = "BOSS"
            self.color = C_GOLD
            self.hp = int(300 * scale)
            self.dmg = int(30 * scale)
            self.xp, self.souls = int(500 * scale), int(300 * scale)
        else:
            avail = [e for e in DEMON_TYPES if e[1] <= floor] or [DEMON_TYPES[0]]
            choice = random.choice(avail)
            self.name, _, self.color, bhp, bdmg, bxp, bsouls = choice
            self.hp = int(bhp * scale)
            self.dmg = int(bdmg * scale)
            self.xp = int(bxp * scale)
            self.souls = int(bsouls * scale)
        self.max_hp = self.hp

    def get_power_rating(self): return self.max_hp + (self.dmg * 5)

class Room:
    def __init__(self, from_dir=None):
        self.enemies = []
        self.exits = {d: (random.random()>0.4) for d in "NSEW"}
        if from_dir: self.exits[{'N':'S','S':'N','E':'W','W':'E'}[from_dir]] = True

# --- GAME ENGINE ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SOLO LEVELING: ARISE")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 48)
        self.db = DatabaseManager()
        self.particles = []
        self.shake_timer = 0
        self.state = "INPUT_NAME"
        self.input_text = ""
        self.selected_class = "FIGHTER"
        self.store = [("Healing Stone", 100), ("Killer Dagger", 500), ("STR Boost", 300), ("AGI Boost", 300)]
        self.store_sel = 0

    def spawn_particles(self, x, y, color, count=10):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def screen_shake(self, intensity=5):
        self.shake_timer = intensity

    def start_game(self):
        name = self.input_text if self.input_text else "Hunter"
        self.player = Player(name, self.selected_class)
        self.floor = 1
        self.map = {(0,0): Room()}
        self.map[(0,0)].exits = {k:True for k in "NSEW"}
        self.log = ["SYSTEM: Initialization Complete."]
        self.has_key, self.boss_spawned, self.boss_active = False, False, False
        self.boss_coords = None
        self.player_moves = 0
        self.pending_level_up = False
        self.particles = [] # Reset particles

    def add_log(self, txt):
        self.log.append(txt)
        if len(self.log) > 8: self.log.pop(0)

    def generate_room(self, x, y, from_dir):
        if (x,y) not in self.map:
            r = Room(from_dir)
            if random.random() < (0.5 + self.floor*0.02) and (x!=0 or y!=0):
                for _ in range(random.randint(1, 3)): r.enemies.append(Enemy(self.floor))
            if self.has_key and not self.boss_spawned and math.hypot(x,y) > 5:
                r.enemies = [Enemy(self.floor, True)]
                self.boss_spawned = True
                self.boss_active = True
                self.boss_coords = (x, y)
                self.add_log("WARNING: High Magic Energy Detected!")
            self.map[(x,y)] = r

    def move_boss(self):
        if not self.boss_active or not self.boss_coords: return
        bx, by = self.boss_coords
        px, py = self.player.grid_x, self.player.grid_y
        if (bx,by) == (px,py): return
        
        nbx, nby = bx, by
        if bx < px: nbx += 1
        elif bx > px: nbx -= 1
        if nbx == bx:
            if by < py: nby += 1
            elif by > py: nby -= 1
            
        if (nbx, nby) in self.map:
            old = self.map[(bx,by)]
            new = self.map[(nbx,nby)]
            boss = next((e for e in old.enemies if e.is_boss), None)
            if boss:
                old.enemies.remove(boss)
                new.enemies.append(boss)
                self.boss_coords = (nbx, nby)
                if (nbx, nby) == (px, py):
                    self.add_log("BOSS HAS FOUND YOU!")
                    self.screen_shake(10)
                    self.state = "COMBAT"

    def move(self, dx, dy, d_str):
        if self.map[(self.player.grid_x, self.player.grid_y)].enemies: return
        if not self.map[(self.player.grid_x, self.player.grid_y)].exits.get(d_str): return
        
        self.player.prev_x, self.player.prev_y = self.player.grid_x, self.player.grid_y
        self.player.grid_x += dx
        self.player.grid_y += dy
        self.generate_room(self.player.grid_x, self.player.grid_y, d_str)
        
        self.player_moves += 1
        if self.player_moves % 2 == 0: self.move_boss()
        
        if self.map[(self.player.grid_x, self.player.grid_y)].enemies:
            self.state = "COMBAT"
            self.add_log("COMBAT STARTED")

    def combat(self, action):
        room = self.map[(self.player.grid_x, self.player.grid_y)]
        target = room.enemies[0]
        
        if action == "RUN":
            cost = 50 * self.floor
            if self.player.souls >= cost:
                self.player.souls -= cost
                if target.is_boss:
                    self.player.grid_x, self.player.grid_y = self.player.prev_x, self.player.prev_y
                else: room.enemies = []
                self.state = "EXPLORE"
                self.add_log("ESCAPED!")
            else: self.add_log("NOT ENOUGH SOULS!")
            
        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            target.hp -= dmg
            
            # Visuals
            self.spawn_particles(WIDTH//2, HEIGHT//2 - 100, C_RED, 5)
            if crit: 
                self.screen_shake(5)
                self.spawn_particles(WIDTH//2, HEIGHT//2 - 100, C_GOLD, 10)
                self.add_log(f"CRITICAL HIT: {dmg}")
            else: self.add_log(f"Hit: {dmg}")
            
            if target.hp <= 0:
                self.spawn_particles(WIDTH//2, HEIGHT//2 - 100, target.color, 20)
                self.player.souls += target.souls
                self.player.xp += target.xp
                if self.player.xp >= self.player.xp_next: self.pending_level_up = True
                if target.is_boss:
                    is_boss_kill = True
                    self.boss_active = False
                else: is_boss_kill = False
                
                if not self.has_key and random.random() < 0.1:
                    self.has_key = True
                    self.add_log("KEY OBTAINED!")
                
                room.enemies.pop(0)
                if not room.enemies:
                    if self.pending_level_up:
                        self.state = "LEVELUP"
                        self.pending_level_up = False
                        self.next_state_after_levelup = "NEXT_FLOOR" if is_boss_kill else "EXPLORE"
                    elif is_boss_kill:
                        self.floor += 1
                        self.state = "NEXT_FLOOR"
                    else: self.state = "EXPLORE"
                return

        # Enemy Turn
        if room.enemies:
            dmg_taken = sum(max(1, e.dmg - self.player.total_def) for e in room.enemies)
            self.player.current_hp -= dmg_taken
            self.spawn_particles(WIDTH//2, HEIGHT//2 + 50, C_PLAYER, 5)
            self.screen_shake(2)
            self.add_log(f"Took {dmg_taken} damage.")
            if self.player.current_hp <= 0:
                self.db.save_run(self.player.name, self.player.class_name, self.floor, self.player.level, self.player.souls)
                self.state = "GAMEOVER"

    # --- GLOW DRAWING FUNCTION ---
    def draw_glow_rect(self, x, y, w, h, color, thickness=1):
        # Main rect
        pygame.draw.rect(self.screen, color, (x, y, w, h), thickness)
        # Glow (simulated by thicker transparent lines)
        s = pygame.Surface((w+10, h+10), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, 50), (5, 5, w, h), thickness+4)
        self.screen.blit(s, (x-5, y-5))

    def draw_system_ui(self):
        # Cyber grid background
        self.screen.fill(BG_COLOR)
        for x in range(0, WIDTH, 40): pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 40): pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WIDTH, y))
        pygame.draw.rect(self.screen, C_PLAYER, (0, 0, WIDTH, HEIGHT), 2)

    def draw_game(self):
        # SHAKE OFFSET
        off_x, off_y = 0, 0
        if self.shake_timer > 0:
            off_x = random.randint(-5, 5)
            off_y = random.randint(-5, 5)
            self.shake_timer -= 1

        # MAP
        cx, cy = WIDTH // 2 + off_x, HEIGHT // 2 + off_y
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                gx, gy = self.player.grid_x + dx, self.player.grid_y - dy
                sx, sy = cx + dx*TILE_SIZE, cy + dy*TILE_SIZE
                if (gx, gy) in self.map:
                    room = self.map[(gx, gy)]
                    has_enemy = len(room.enemies) > 0
                    color = C_RED if has_enemy else C_WALL
                    self.draw_glow_rect(sx, sy, TILE_SIZE, TILE_SIZE, color, 1)
                    
                    # Enemies (Circles with Glow)
                    if room.enemies:
                        c = C_GOLD if room.enemies[0].is_boss else C_RED
                        pygame.draw.circle(self.screen, c, (sx+30, sy+30), 10)
                        # Glow
                        s = pygame.Surface((30, 30), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*c, 100), (15, 15), 14)
                        self.screen.blit(s, (sx+15, sy+15))

        # PLAYER
        pygame.draw.circle(self.screen, C_PLAYER, (cx+30, cy+30), 12)
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(s, (*C_PLAYER, 80), (20, 20), 18)
        self.screen.blit(s, (cx+10, cy+10))

        # PARTICLES
        for p in self.particles:
            p.update()
            p.draw(self.screen)
        self.particles = [p for p in self.particles if p.life > 0]

        # HUD
        px = WIDTH - 300
        pygame.draw.rect(self.screen, (0, 10, 20), (px, 0, 300, HEIGHT))
        pygame.draw.line(self.screen, C_PLAYER, (px, 0), (px, HEIGHT), 2)
        
        y = 20
        def txt(t, c=C_TEXT, sz=24):
            nonlocal y
            f = pygame.font.Font(None, sz)
            self.screen.blit(f.render(t, True, c), (px+20, y))
            y += sz + 10

        txt(f"FLOOR: {self.floor}", C_PLAYER, 40)
        txt(f"{self.player.name}", C_TEXT)
        txt(f"{self.player.class_name}", C_GOLD)
        y += 10
        # HP BAR
        pygame.draw.rect(self.screen, (50,0,0), (px+20, y, 250, 20))
        pygame.draw.rect(self.screen, C_RED, (px+20, y, 250*(self.player.current_hp/self.player.max_hp), 20))
        y += 25
        txt(f"HP: {self.player.current_hp}/{self.player.max_hp}", C_RED)
        txt(f"SOULS: {self.player.souls}", C_PURPLE)
        y += 20
        
        # COMBAT UI OVERLAY
        if self.state == "COMBAT":
            e = self.map[(self.player.grid_x, self.player.grid_y)].enemies[0]
            # Name Color logic
            p_pow = self.player.get_power_rating()
            e_pow = e.get_power_rating()
            ec = C_RED if e_pow > p_pow*1.3 else (C_TEXT if p_pow > e_pow*1.5 else C_GOLD)
            
            # Enemy Card
            pygame.draw.rect(self.screen, (0,0,0), (cx-150, cy-150, 300, 80))
            self.draw_glow_rect(cx-150, cy-150, 300, 80, ec, 2)
            name_surf = self.title_font.render(e.name, True, ec)
            self.screen.blit(name_surf, (cx - name_surf.get_width()//2, cy-140))
            hp_surf = self.font.render(f"HP: {e.hp}/{e.max_hp}", True, C_TEXT)
            self.screen.blit(hp_surf, (cx - hp_surf.get_width()//2, cy-100))
            
            # Controls
            instr = "[SPACE] ATTACK   [U] ESCAPE"
            self.screen.blit(self.font.render(instr, True, C_PLAYER), (cx-100, cy+100))

        # LOG
        ly = HEIGHT - 250
        for l in self.log:
            c = C_PLAYER if "SYSTEM" in l else (C_RED if "COMBAT" in l else C_TEXT)
            self.screen.blit(self.font.render(l, True, c), (20, ly))
            ly += 25

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            
            # INPUT
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    
                    if self.state == "INPUT_NAME":
                        if event.key == pygame.K_RETURN and self.input_text: self.state = "MENU"
                        elif event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                        else: self.input_text += event.unicode
                        
                    elif self.state == "MENU":
                        if event.key == pygame.K_RETURN: 
                            self.start_game()
                            self.state = "EXPLORE"
                        if event.key == pygame.K_1: self.selected_class = "FIGHTER"
                        if event.key == pygame.K_2: self.selected_class = "ASSASSIN"
                        if event.key == pygame.K_3: self.selected_class = "MAGE"
                        if event.key == pygame.K_9: self.selected_class = "MONARCH"

                    elif self.state == "EXPLORE":
                        if event.key == pygame.K_UP: self.move(0, 1, 'N')
                        elif event.key == pygame.K_DOWN: self.move(0, -1, 'S')
                        elif event.key == pygame.K_RIGHT: self.move(1, 0, 'E')
                        elif event.key == pygame.K_LEFT: self.move(-1, 0, 'W')
                        
                    elif self.state == "COMBAT":
                        if event.key == pygame.K_SPACE: self.combat("ATTACK")
                        elif event.key == pygame.K_u: self.combat("RUN")
                        
                    elif self.state == "GAMEOVER":
                        if event.key == pygame.K_RETURN: 
                            self.state = "MENU" # Návrat do menu

                    elif self.state == "LEVELUP":
                        k = event.key
                        m = {pygame.K_1:'str', pygame.K_2:'dex', pygame.K_3:'int', pygame.K_4:'vigor', pygame.K_5:'sense'}
                        if k in m:
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
                            self.map[(0,0)].exits = {k:True for k in "NSEW"}
                            self.player.grid_x, self.player.grid_y = 0, 0
                            self.has_key, self.boss_spawned = False, False
                            self.state = "EXPLORE"

            # DRAWING
            self.draw_system_ui()
            
            if self.state == "INPUT_NAME":
                t = self.title_font.render("ENTER HUNTER NAME", True, C_PLAYER)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 300))
                self.draw_glow_rect(WIDTH//2-150, 350, 300, 50, C_PLAYER)
                self.screen.blit(self.font.render(self.input_text, True, C_TEXT), (WIDTH//2-140, 365))
                
            elif self.state == "MENU":
                t = self.title_font.render("SOLO LEVELING", True, C_PLAYER)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 100))
                # Rankings
                r = self.db.get_rankings()
                y = 200
                self.screen.blit(self.font.render("TOP HUNTERS", True, C_GOLD), (WIDTH//2-60, 160))
                for row in r:
                    self.screen.blit(self.font.render(f"{row[2]} (Lvl {row[5]}) - Floor {row[4]}", True, C_TEXT), (WIDTH//2-100, y))
                    y+=30
                self.screen.blit(self.font.render("SELECT CLASS (1-3) & ENTER", True, C_GREEN), (WIDTH//2-120, 500))
                
            elif self.state == "GAMEOVER":
                t = self.title_font.render("YOU DIED", True, C_RED)
                self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
                t2 = self.font.render("Press [ENTER] to Return to Menu", True, C_TEXT)
                self.screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 60))
                
            elif self.state == "LEVELUP":
                self.screen.blit(self.title_font.render("LEVEL UP!", True, C_GOLD), (WIDTH//2-50, 200))
                opts = ["1. STR", "2. AGI", "3. INT", "4. VIT", "5. SENSE"]
                for i, o in enumerate(opts):
                    self.screen.blit(self.font.render(o, True, C_PLAYER), (WIDTH//2-50, 260 + i*40))
                    
            elif self.state == "NEXT_FLOOR":
                self.screen.blit(self.title_font.render("FLOOR CLEARED", True, C_GOLD), (WIDTH//2-100, 300))
                self.screen.blit(self.font.render("[ENTER] Ascend", True, C_TEXT), (WIDTH//2-60, 360))
                
            else:
                self.draw_game()

            pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
