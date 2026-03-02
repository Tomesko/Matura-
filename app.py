import pygame
import random
import math
import time
import sqlite3
import datetime
import pickle
import os

# --- KONFIGURACE ---
WIDTH, HEIGHT = 1000, 800
TILE_SIZE = 60
FPS = 60

# --- BARVY ---
BG_COLOR = (5, 8, 15)
GRID_COLOR = (20, 25, 40)
NEON_BLUE = (0, 190, 255)
NEON_RED = (255, 40, 40)
NEON_GOLD = (255, 215, 0)
NEON_PURPLE = (180, 50, 255)
NEON_GREEN = (50, 255, 100)
NEON_GRAY = (100, 100, 120)
TXT_WHITE = (240, 240, 255)
TXT_GRAY = (150, 150, 170)
MANA_BLUE = (0, 100, 255)

# --- LOOT SYSTÉM ---
LOOT_DB = {
    "Demon Horn": 15, "Torn Cloth": 5, "Beast Fang": 25,
    "Shadow Core": 50, "Broken Bone": 10, "Magic Dust": 35
}

# --- BESTIÁŘ ---
DEMON_TYPES = [
    ("Low Rank Demon", 1, (150, 150, 150), 20, 5, 5, 10),
    ("Flying Demon", 3, (180, 120, 120), 30, 8, 10, 15),
    ("Cerberus", 5, (200, 100, 50), 60, 15, 25, 50),
    ("High Orc", 10, (50, 150, 50), 80, 20, 35, 40),
    ("Demon Knight", 15, (100, 100, 200), 120, 30, 60, 80),
    ("Arch-Lich", 20, (150, 50, 200), 150, 50, 100, 150),
]

# --- DEFINICE SKILLŮ ---
SKILLS_DB = {
    "FIGHTER": {"Q": ("Smash", 10, 3, 2.0, "DMG"), "W": ("Iron Skin", 15, 5, 10, "BUFF"),
                "E": ("War Cry", 20, 8, 0.5, "HEAL")},
    "ASSASSIN": {"Q": ("Vital Strike", 10, 2, 1.5, "DMG"), "W": ("Poison Edge", 15, 4, 2.5, "DMG"),
                 "E": ("Shadow Step", 20, 6, 0, "ESCAPE")},
    "MAGE": {"Q": ("Fireball", 15, 2, 2.5, "DMG"), "W": ("Ice Barrier", 20, 5, 20, "BUFF"),
             "E": ("Meteor", 50, 10, 5.0, "DMG")},
    "MONARCH": {"Q": ("Dominator's Touch", 10, 1, 2.0, "DMG"), "W": ("Ruler's Authority", 20, 4, 3.0, "DMG"),
                "E": ("Full Recovery", 50, 10, 1.0, "HEAL")}
}

# --- CLASSES ---
CLASSES = {
    "FIGHTER": {"stats": {"vigor": 15, "str": 12, "dex": 5, "int": 5, "sense": 5, "def": 3, "mana": 30},
                "weapon": ("Vanguard Shield", 8, 12, "str", 1.0, 0)},
    "ASSASSIN": {"stats": {"vigor": 8, "str": 8, "dex": 16, "int": 10, "sense": 15, "def": 0, "mana": 40},
                 "weapon": ("Kasaka's Fang", 10, 18, "dex", 1.3, 0)},
    "MAGE": {"stats": {"vigor": 6, "str": 4, "dex": 8, "int": 20, "sense": 10, "def": 0, "mana": 100},
             "weapon": ("Orb of Greed", 12, 20, "int", 1.4, 0)},
    "MONARCH": {"stats": {"vigor": 15, "str": 15, "dex": 15, "int": 20, "sense": 15, "def": 2, "mana": 80},
                "weapon": ("Kamish's Wrath", 25, 40, "str", 1.8, 0)}
}


# --- DATABÁZE ---
class DatabaseManager:
    def __init__(self, db_name="sololeveling_v15.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS hunters (id INTEGER PRIMARY KEY, date TEXT, name TEXT, class TEXT, floor INTEGER, level INTEGER, souls INTEGER)''')
        self.conn.commit()

    def verify_login(self, username, password):
        self.cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = self.cursor.fetchone()
        if user is None:
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            self.conn.commit()
            return True
        else:
            return user[1] == password

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
        self.souls, self.shadows = 0, 0
        self.stat_points = 0  # NOVÉ: Neutracené body atributů

        w = c["weapon"]
        self.weapon = Weapon(w[0], w[1], w[2], w[3], w[4], w[5])
        self.inventory = ["Healing Stone"]

        self.max_hp, self.current_hp = 0, 0
        self.max_mana, self.current_mana = 0, 0
        self.total_def = 0
        self.cooldowns = {"Q": 0, "W": 0, "E": 0}

        self.recalculate()
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana

    def recalculate(self):
        self.max_hp = (self.stats["vigor"] * 10)
        self.max_mana = (self.stats["int"] * 5) + self.stats.get("mana", 20)
        self.total_def = self.stats["def"] + (self.stats["str"] // 5)
        if self.current_hp > self.max_hp: self.current_hp = self.max_hp
        if self.current_mana > self.max_mana: self.current_mana = self.max_mana

    # NOVÉ: Logika Level Upování oddělená pro čistší kód
    def check_level_up(self):
        leveled_up = False
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            self.stat_points += 5  # 5 Bodů za každý level!
            self.xp_next = int(self.xp_next * 1.2)
            leveled_up = True

        if leveled_up:
            self.recalculate()
            # Automatické doléčení při level upu
            self.current_hp = self.max_hp
            self.current_mana = self.max_mana
        return leveled_up

    def tick_cooldowns(self):
        for k in self.cooldowns:
            if self.cooldowns[k] > 0: self.cooldowns[k] -= 1
        regen = max(1, int(self.max_mana * 0.05))
        self.current_mana = min(self.max_mana, self.current_mana + regen)

    def attack(self):
        base = random.randint(self.weapon.min_dmg, self.weapon.max_dmg)
        stat = self.stats.get(self.weapon.scaling_stat, 10)
        total = base + int(stat * self.weapon.scaling_rank)
        crit = random.randint(1, 100) <= min(self.stats["sense"], 50)
        if crit: total = int(total * 1.5)
        return total, crit

    def use_shadows(self):
        if self.shadows >= 3:
            self.shadows -= 3
            return self.stats["int"] * 5
        return 0

    def get_power_rating(self):
        avg_dmg = (self.weapon.min_dmg + self.weapon.max_dmg) / 2
        return self.max_hp + (avg_dmg * 6) + (self.total_def * 5)


class Enemy:
    def __init__(self, floor, is_boss=False):
        self.is_boss = is_boss
        scale = 1.0 + (floor * 0.15)
        if is_boss:
            if floor < 20:
                name = "VULCAN"
            elif floor < 50:
                name = "METUS"
            else:
                name = "BARAN"
            self.name = name;
            self.color = NEON_RED
            self.hp, self.dmg = int(300 * scale), int(30 * scale)
            self.xp, self.souls = int(500 * scale), int(300 * scale)
        else:
            avail = [e for e in DEMON_TYPES if e[1] <= floor] or [DEMON_TYPES[0]]
            n, _, c, hp, d, x, s = random.choice(avail)
            self.name, self.color = n, c
            self.hp, self.dmg = int(hp * scale), int(d * scale)
            self.xp, self.souls = int(x * scale), int(s * scale)
        self.max_hp = self.hp

    def get_power_rating(self):
        return self.max_hp + (self.dmg * 6)


class Room:
    def __init__(self, from_dir=None):
        self.enemies = []
        self.exits = {d: random.random() > 0.4 for d in "NSEW"}
        if from_dir: self.exits[{'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}[from_dir]] = True


# --- GRAPHICS HELPER ---
def draw_glow_rect(surface, color, rect, thickness=2, glow_size=10):
    pygame.draw.rect(surface, color, rect, thickness)
    for i in range(glow_size):
        alpha = int(100 - (i * (100 / glow_size)))
        s = pygame.Surface((rect[2] + i * 2, rect[3] + i * 2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2] + i * 2, rect[3] + i * 2), 1)
        surface.blit(s, (rect[0] - i, rect[1] - i))


# --- GAME ENGINE ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Solo Leveling: MMO Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 40)
        self.db = DatabaseManager()

        self.state = "LOGIN"
        self.input_user = ""
        self.input_pass = ""
        self.active_field = "user"
        self.login_error = ""

        self.selected_class = "FIGHTER"
        self.reset_game_data()
        self.save_file = "savegame_mmo.dat"

    def reset_game_data(self):
        self.player, self.map, self.log = None, {}, []
        self.floor = 1
        self.has_key, self.boss_spawned, self.boss_active = False, False, False
        self.boss_coords = None
        self.player_moves = 0
        self.store = [("Healing Stone", 100), ("Killer Dagger", 500), ("STR Boost", 300), ("AGI Boost", 300)]

    def save_game(self):
        data = {"player": self.player, "floor": self.floor, "map": self.map, "log": self.log, "has_key": self.has_key,
                "boss_spawned": self.boss_spawned, "boss_active": self.boss_active, "boss_coords": self.boss_coords,
                "store": self.store}
        try:
            with open(self.save_file, "wb") as f:
                pickle.dump(data, f)
        except:
            pass

    def load_game(self):
        if not os.path.exists(self.save_file): return False
        try:
            with open(self.save_file, "rb") as f:
                data = pickle.load(f)
            self.player = data["player"]

            # OPRAVA KOMPATIBILITY (Pokud hráč načte starý save bez stat_points)
            if not hasattr(self.player, 'stat_points'): self.player.stat_points = 0

            if self.player.name != self.input_user: return False
            self.floor, self.map, self.log = data["floor"], data["map"], data["log"]
            self.has_key, self.boss_spawned = data["has_key"], data.get("boss_spawned", False)
            self.boss_active, self.boss_coords = data.get("boss_active", False), data.get("boss_coords", None)
            self.store = data.get("store", [])
            return True
        except:
            return False

    def check_shop_unlocks(self):
        if self.floor >= 5:
            for i in [("Elixir of Life", 500), ("Shadow Armor", 1500)]:
                if i not in self.store: self.store.append(i)
        if self.floor >= 10:
            for i in [("Demon King's Sword", 2500), ("Orb of Avarice", 2000)]:
                if i not in self.store: self.store.append(i)

    def start_game(self):
        self.player = Player(self.input_user, self.selected_class)
        self.floor = 1
        self.map = {(0, 0): Room()}
        self.map[(0, 0)].exits = {'N': True, 'S': True, 'E': True, 'W': True}
        self.log = [f"SYSTEM: Welcome, Hunter {self.input_user}."]
        self.has_key, self.boss_spawned, self.boss_active = False, False, False
        self.boss_coords, self.player_moves = None, 0

    def add_log(self, txt):
        self.log.append(txt)
        if len(self.log) > 8: self.log.pop(0)

    def generate_room(self, x, y, from_dir):
        if (x, y) not in self.map:
            r = Room(from_dir)
            if random.random() < (0.5 + self.floor * 0.02) and (x != 0 or y != 0):
                for _ in range(random.randint(1, 3)): r.enemies.append(Enemy(self.floor))
            if self.has_key and not self.boss_spawned and math.hypot(x, y) > 5:
                r.enemies = [Enemy(self.floor, is_boss=True)]
                self.boss_spawned, self.boss_active, self.boss_coords = True, True, (x, y)
                self.add_log("WARNING: Boss Signature Detected!")
            self.map[(x, y)] = r

    def move_boss(self):
        if not self.boss_active or not self.boss_coords: return
        bx, by = self.boss_coords
        px, py = self.player.grid_x, self.player.grid_y
        if (bx, by) == (px, py): return
        nbx, nby = bx, by
        if bx < px:
            nbx += 1
        elif bx > px:
            nbx -= 1
        if nbx == bx:
            if by < py:
                nby += 1
            elif by > py:
                nby -= 1
        if (nbx, nby) in self.map:
            old_room, target_room = self.map[(bx, by)], self.map[(nbx, nby)]
            boss_obj = next((e for e in old_room.enemies if e.is_boss), None)
            if boss_obj:
                old_room.enemies.remove(boss_obj)
                target_room.enemies.append(boss_obj)
                self.boss_coords = (new_bx, new_by) = (nbx, nby)
                if (nbx, nby) == (px, py):
                    self.add_log("ALERT: BOSS HAS FOUND YOU!")
                    self.state = "COMBAT"

    def move(self, dx, dy, d_str):
        curr = self.map[(self.player.grid_x, self.player.grid_y)]
        if curr.enemies: return
        if not curr.exits.get(d_str): return

        nx, ny = self.player.grid_x + dx, self.player.grid_y + dy
        self.player.prev_x, self.player.prev_y = self.player.grid_x, self.player.grid_y
        self.generate_room(nx, ny, d_str)
        self.player.grid_x, self.player.grid_y = nx, ny

        self.player_moves += 1
        if self.player_moves % 2 == 0: self.move_boss()
        self.save_game()

        if self.map[(nx, ny)].enemies:
            self.state = "COMBAT"
            self.add_log(f"ENEMIES: {len(self.map[(nx, ny)].enemies)} targets.")

    def get_sellable_loot_value(self):
        return sum(LOOT_DB.get(item, 0) for item in self.player.inventory)

    def combat(self, action):
        room = self.map[(self.player.grid_x, self.player.grid_y)]
        target = room.enemies[0]
        turn_ended = True

        if action in ["Q", "W", "E"]:
            s_name, s_cost, s_cd, s_val, s_type = SKILLS_DB[self.player.class_name][action]
            if self.player.current_mana < s_cost:
                self.add_log("SYSTEM: Not enough Mana!");
                turn_ended = False
            elif self.player.cooldowns[action] > 0:
                self.add_log(f"SYSTEM: {s_name} is on CD!");
                turn_ended = False
            else:
                self.player.current_mana -= s_cost
                self.player.cooldowns[action] = s_cd
                self.add_log(f"SKILL: Used {s_name}!")

                if s_type == "DMG":
                    dmg, crit = self.player.attack()
                    dmg = int(dmg * s_val)
                    target.hp -= dmg
                    self.add_log(f"HIT: {dmg} Damage!")
                elif s_type == "HEAL":
                    heal = int(self.player.max_hp * s_val) if s_val < 1.0 else int(s_val)
                    self.player.current_hp = min(self.player.max_hp, self.player.current_hp + heal)
                    self.add_log(f"HEAL: Recovered {heal} HP.")
                elif s_type == "BUFF":
                    self.add_log("BUFF: Effect applied.")
                elif s_type == "ESCAPE":
                    room.enemies = [];
                    self.state = "EXPLORE";
                    self.add_log("SYSTEM: Vanished into shadows!")
                    return

        elif action == "RUN":
            cost = 50 * self.floor
            if self.player.souls >= cost:
                self.player.souls -= cost
                if target.is_boss:
                    self.player.grid_x, self.player.grid_y = self.player.prev_x, self.player.prev_y
                else:
                    room.enemies = []
                self.state = "EXPLORE";
                self.add_log("ESCAPED!");
                return
            else:
                self.add_log("SYSTEM: Insufficient Souls.");
                turn_ended = False

        elif action == "ATTACK":
            dmg, crit = self.player.attack()
            target.hp -= dmg
            self.add_log(f"ATTACK: {dmg}{' [CRIT]' if crit else ''}")

        elif action == "SHADOWS":
            dmg = self.player.use_shadows()
            if dmg > 0:
                self.add_log(f"ARISE: {dmg} DMG to all.")
                for e in room.enemies: e.hp -= dmg
            else:
                self.add_log("SYSTEM: Need 3 Shadows.");
                turn_ended = False

        # Hodnocení mrtvých a DROP LOOTU
        dead_enemies = [e for e in room.enemies if e.hp <= 0]
        room.enemies = [e for e in room.enemies if e.hp > 0]

        for e in dead_enemies:
            self.player.souls += e.souls
            self.player.xp += e.xp
            if e.is_boss: self.boss_active, self.boss_coords = False, None
            if random.random() < 0.3: self.player.shadows += 1

            if not e.is_boss and random.random() < 0.4:
                drop = random.choice(list(LOOT_DB.keys()))
                self.player.inventory.append(drop)
                self.add_log(f"DROPPED: {drop}")

            if not self.has_key and random.random() < 0.1:
                self.has_key = True;
                self.add_log("ITEM: Found Key.")

        # --- KONTROLA LEVEL UPU NA POZADÍ ---
        if self.player.check_level_up():
            self.add_log("SYSTEM: LEVEL UP! Press [C] to Upgrade Stats.")

        if not room.enemies:
            if any(e.is_boss for e in dead_enemies):
                self.floor += 1;
                self.check_shop_unlocks();
                self.state = "NEXT_FLOOR"
            else:
                self.state = "EXPLORE";
                self.save_game()
            return

        if turn_ended:
            self.player.tick_cooldowns()
            dmg_taken = sum(max(1, e.dmg - self.player.total_def) for e in room.enemies)
            if dmg_taken > 0:
                self.player.current_hp -= dmg_taken
                self.add_log(f"DEFENSE: Took {dmg_taken} dmg.")
            if self.player.current_hp <= 0:
                self.db.save_run(self.player.name, self.player.class_name, self.floor, self.player.level,
                                 self.player.souls)
                if os.path.exists(self.save_file): os.remove(self.save_file)
                self.state = "GAMEOVER"

    def get_name_color(self, enemy):
        p_pow = self.player.get_power_rating()
        e_pow = enemy.get_power_rating()
        if e_pow > p_pow * 1.3:
            return NEON_RED
        elif p_pow > e_pow * 1.5:
            return NEON_GRAY
        else:
            return NEON_GOLD

    # --- DRAWING ---
    def draw_bg(self):
        self.screen.fill(BG_COLOR)
        for x in range(0, WIDTH, 40): pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 40): pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WIDTH, y))
        pygame.draw.rect(self.screen, NEON_BLUE, (0, 0, WIDTH, HEIGHT), 2)

    def draw_game(self):
        self.draw_bg()
        cx, cy = WIDTH // 2, HEIGHT // 2
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                gx, gy = self.player.grid_x + dx, self.player.grid_y - dy
                sx, sy = cx + dx * TILE_SIZE, cy + dy * TILE_SIZE
                if (gx, gy) in self.map:
                    room = self.map[(gx, gy)]
                    col = NEON_RED if room.enemies else NEON_GRAY
                    pygame.draw.rect(self.screen, (10, 10, 15), (sx, sy, TILE_SIZE, TILE_SIZE))
                    draw_glow_rect(self.screen, col, (sx, sy, TILE_SIZE, TILE_SIZE), 1, 5)
                    if room.enemies:
                        ec = NEON_GOLD if room.enemies[0].is_boss else NEON_RED
                        pygame.draw.circle(self.screen, ec, (sx + 30, sy + 30), 10 + len(room.enemies) * 2)

        pygame.draw.circle(self.screen, NEON_BLUE, (cx + 30, cy + 30), 12)
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(s, (*NEON_BLUE, 100), (20, 20), 18)
        self.screen.blit(s, (cx + 10, cy + 10))

        # HUD
        px = WIDTH - 300
        pygame.draw.rect(self.screen, (5, 10, 15), (px, 0, 300, HEIGHT))
        pygame.draw.line(self.screen, NEON_BLUE, (px, 0), (px, HEIGHT), 2)
        y = 20

        def txt(t, c=TXT_WHITE, sz=24):
            nonlocal y
            self.screen.blit(pygame.font.Font(None, sz).render(t, True, c), (px + 20, y))
            y += sz + 5

        txt(f"FLOOR: {self.floor}", NEON_BLUE, 40)
        txt(f"{self.player.name} (Lvl {self.player.level})", NEON_GOLD)

        pygame.draw.rect(self.screen, (50, 0, 0), (px + 20, y, 250, 15))
        pygame.draw.rect(self.screen, NEON_RED, (px + 20, y, 250 * (self.player.current_hp / self.player.max_hp), 15));
        y += 20
        pygame.draw.rect(self.screen, (0, 0, 50), (px + 20, y, 250, 15))
        pygame.draw.rect(self.screen, NEON_BLUE,
                         (px + 20, y, 250 * (self.player.current_mana / self.player.max_mana), 15));
        y += 20
        txt(f"HP: {self.player.current_hp}/{self.player.max_hp}  MP: {int(self.player.current_mana)}/{self.player.max_mana}",
            TXT_WHITE)

        pygame.draw.rect(self.screen, (50, 50, 0), (px + 20, y, 250, 6))
        pygame.draw.rect(self.screen, NEON_GOLD, (px + 20, y, 250 * (self.player.xp / self.player.xp_next), 6));
        y += 15

        txt(f"Souls: {self.player.souls}", NEON_PURPLE)
        txt(f"Shadows: {self.player.shadows}", NEON_GRAY)

        y += 10;
        txt("SKILLS", NEON_BLUE)
        for k in ["Q", "W", "E"]:
            s_name, s_cost, _, _, _ = SKILLS_DB[self.player.class_name][k]
            cd = self.player.cooldowns[k]
            col = NEON_GOLD
            suffix = f" (-{s_cost} MP)"
            if cd > 0:
                col = TXT_GRAY; suffix = f" (CD: {cd})"
            elif self.player.current_mana < s_cost:
                col = NEON_RED
            self.screen.blit(self.font.render(f"[{k}] {s_name}{suffix}", True, col), (px + 20, y));
            y += 25

        y += 10
        txt("[I] Inv   [C] Char   [H] Help", NEON_GREEN)

        # --- BLIKAJÍCÍ UPOZORNĚNÍ NA BODY ---
        if self.player.stat_points > 0:
            if int(time.time() * 2) % 2 == 0:
                self.screen.blit(self.font.render(f"POINTS AVAILABLE: {self.player.stat_points} [C]", True, NEON_GOLD),
                                 (px + 20, y))
        y += 25

        y += 10
        curr = self.map.get((self.player.grid_x, self.player.grid_y))
        if curr:
            for d, pos in {'N': (100, 0), 'S': (100, 40), 'W': (60, 20), 'E': (140, 20)}.items():
                pygame.draw.rect(self.screen, NEON_GREEN if curr.exits[d] else NEON_RED,
                                 (px + 20 + pos[0], y + pos[1], 20, 20))

        for l in self.log:
            c = NEON_BLUE if "SYSTEM" in l else (NEON_RED if "COMBAT" in l else TXT_WHITE)
            self.screen.blit(self.font.render(l, True, c), (20, HEIGHT - 250 + self.log.index(l) * 25))

        if self.state == "COMBAT":
            e = self.map[(self.player.grid_x, self.player.grid_y)].enemies[0]
            col = self.get_name_color(e)
            draw_glow_rect(self.screen, col, (cx - 150, cy - 150, 300, 100), 2)
            pygame.draw.rect(self.screen, (0, 0, 0), (cx - 150, cy - 150, 300, 100))
            self.screen.blit(self.title_font.render(e.name, True, col), (cx - 100, cy - 130))
            self.screen.blit(self.font.render(f"HP: {e.hp}/{e.max_hp}", True, TXT_WHITE), (cx - 50, cy - 90))
            self.screen.blit(self.font.render("[SPACE] ATTACK   [Q/W/E] SKILLS", True, NEON_BLUE), (cx - 140, cy + 100))

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

                    if self.state == "LOGIN":
                        if event.key == pygame.K_TAB:
                            self.active_field = "pass" if self.active_field == "user" else "user"
                        elif event.key == pygame.K_RETURN:
                            if self.db.verify_login(self.input_user, self.input_pass):
                                self.state = "MENU"
                                self.login_error = ""
                            else:
                                self.login_error = "Wrong Password! (New names auto-register)"
                        elif event.key == pygame.K_BACKSPACE:
                            if self.active_field == "user":
                                self.input_user = self.input_user[:-1]
                            else:
                                self.input_pass = self.input_pass[:-1]
                        else:
                            if self.active_field == "user" and len(self.input_user) < 15:
                                self.input_user += event.unicode
                            elif self.active_field == "pass" and len(self.input_pass) < 15:
                                self.input_pass += event.unicode

                    elif self.state == "MENU":
                        if event.key == pygame.K_RETURN:
                            self.start_game()
                            self.state = "EXPLORE"
                        elif event.key == pygame.K_c:
                            if self.load_game():
                                self.state = "EXPLORE"
                                self.add_log("SYSTEM: Welcome back.")
                        if event.key == pygame.K_1: self.selected_class = "FIGHTER"
                        if event.key == pygame.K_2: self.selected_class = "ASSASSIN"
                        if event.key == pygame.K_3: self.selected_class = "MAGE"
                        if event.key == pygame.K_9: self.selected_class = "MONARCH"

                    elif self.state == "EXPLORE":
                        if event.key == pygame.K_UP:
                            self.move(0, 1, 'N')
                        elif event.key == pygame.K_DOWN:
                            self.move(0, -1, 'S')
                        elif event.key == pygame.K_RIGHT:
                            self.move(1, 0, 'E')
                        elif event.key == pygame.K_LEFT:
                            self.move(-1, 0, 'W')
                        elif event.key == pygame.K_b:
                            self.state = "STORE"
                        elif event.key == pygame.K_i:
                            self.state = "INVENTORY"
                        elif event.key == pygame.K_h:
                            self.state = "HELP"
                        elif event.key == pygame.K_c:
                            self.state = "CHARACTER"  # Otevřít Staty!

                    elif self.state == "INVENTORY":
                        if event.key in [pygame.K_i, pygame.K_ESCAPE]: self.state = "EXPLORE"

                    elif self.state == "HELP":
                        if event.key in [pygame.K_h, pygame.K_ESCAPE]: self.state = "EXPLORE"

                        # --- NOVÉ: ROZDĚLOVÁNÍ STATŮ ---
                    elif self.state == "CHARACTER":
                        if event.key in [pygame.K_c, pygame.K_ESCAPE]:
                            self.state = "EXPLORE"
                        elif self.player.stat_points > 0:
                            if event.key == pygame.K_1:
                                self.player.stats['str'] += 1; self.player.stat_points -= 1
                            elif event.key == pygame.K_2:
                                self.player.stats['dex'] += 1; self.player.stat_points -= 1
                            elif event.key == pygame.K_3:
                                self.player.stats['int'] += 1; self.player.stat_points -= 1
                            elif event.key == pygame.K_4:
                                self.player.stats['vigor'] += 1; self.player.stat_points -= 1
                            elif event.key == pygame.K_5:
                                self.player.stats['sense'] += 1; self.player.stat_points -= 1
                            self.player.recalculate()
                    # --------------------------------

                    elif self.state == "COMBAT":
                        if event.key == pygame.K_SPACE:
                            self.combat("ATTACK")
                        elif event.key == pygame.K_q:
                            self.combat("Q")
                        elif event.key == pygame.K_w:
                            self.combat("W")
                        elif event.key == pygame.K_e:
                            self.combat("E")
                        elif event.key == pygame.K_s:
                            self.combat("SHADOWS")
                        elif event.key == pygame.K_h:
                            self.combat("POTION")
                        elif event.key == pygame.K_u:
                            self.combat("RUN")

                    elif self.state == "STORE":
                        if event.key == pygame.K_b:
                            self.state = "EXPLORE"
                        elif event.key == pygame.K_SPACE:
                            val = self.get_sellable_loot_value()
                            if val > 0:
                                self.player.souls += val
                                self.player.inventory = [i for i in self.player.inventory if i not in LOOT_DB]
                                self.add_log(f"SOLD LOOT: +{val} Souls")
                        elif event.key == pygame.K_DOWN:
                            self.store_sel = (self.store_sel + 1) % len(self.store)
                        elif event.key == pygame.K_UP:
                            self.store_sel = (self.store_sel - 1) % len(self.store)
                        elif event.key == pygame.K_RETURN:
                            item = self.store[self.store_sel]
                            name, cost = item
                            if self.player.souls >= cost:
                                self.player.souls -= cost
                                if "Healing" in name or "Elixir" in name:
                                    self.player.inventory.append(name)
                                elif "Dagger" in name or "Orb" in name or "Sword" in name:
                                    self.player.weapon = Weapon(name, int(cost / 50), int(cost / 30), "str", 1.5, cost)
                                elif "Armor" in name:
                                    self.player.stats["def"] += 5; self.player.recalculate()
                                elif "Daily" in name:
                                    if "Strength" in name:
                                        self.player.stats["str"] += 2
                                    else:
                                        self.player.stats["dex"] += 2
                                    self.player.recalculate()
                                self.add_log(f"Purchased {name}.")
                            else:
                                self.add_log("Insufficient Souls.")

                    elif self.state == "NEXT_FLOOR":
                        if event.key == pygame.K_RETURN:
                            self.map = {(0, 0): Room()}
                            self.map[(0, 0)].exits = {'N': True, 'S': True, 'E': True, 'W': True}
                            self.player.grid_x, self.player.grid_y = 0, 0
                            self.has_key, self.boss_spawned = False, False
                            self.state = "EXPLORE"
                            self.save_game()

                    elif self.state == "GAMEOVER":
                        if event.key == pygame.K_RETURN: self.reset_game_data(); self.state = "MENU"

            self.draw_bg()

            if self.state == "LOGIN":
                self.screen.blit(self.title_font.render("SYSTEM LOGIN", True, NEON_BLUE), (WIDTH // 2 - 120, 200))

                c_user = NEON_GREEN if self.active_field == "user" else NEON_BLUE
                draw_glow_rect(self.screen, c_user, (WIDTH // 2 - 150, 280, 300, 40), 2)
                self.screen.blit(self.font.render(f"User: {self.input_user}", True, TXT_WHITE), (WIDTH // 2 - 140, 290))

                c_pass = NEON_GREEN if self.active_field == "pass" else NEON_BLUE
                draw_glow_rect(self.screen, c_pass, (WIDTH // 2 - 150, 350, 300, 40), 2)
                pwd_display = "*" * len(self.input_pass)
                self.screen.blit(self.font.render(f"Pass: {pwd_display}", True, TXT_WHITE), (WIDTH // 2 - 140, 360))

                self.screen.blit(self.font.render("[TAB] Switch Field   [ENTER] Login", True, TXT_GRAY),
                                 (WIDTH // 2 - 140, 430))
                if self.login_error:
                    self.screen.blit(self.font.render(self.login_error, True, NEON_RED), (WIDTH // 2 - 200, 480))

            elif self.state == "MENU":
                cx, cy = WIDTH // 2 - 200, 420
                for i, c in enumerate(["FIGHTER", "ASSASSIN", "MAGE"]):
                    col = NEON_GOLD if self.selected_class == c else NEON_GRAY
                    draw_glow_rect(self.screen, col, (cx + i * 140, cy, 120, 60), 2 if self.selected_class == c else 1)
                    self.screen.blit(self.font.render(c, True, col), (cx + i * 140 + 15, cy + 20))
                if os.path.exists(self.save_file):
                    self.screen.blit(
                        self.title_font.render(f"Welcome {self.input_user} | [C] CONTINUE", True, NEON_GREEN),
                        (WIDTH // 2 - 220, 570))
                self.screen.blit(self.font.render("Press [ENTER] for NEW GAME", True, TXT_WHITE),
                                 (WIDTH // 2 - 120, 630))

            elif self.state == "STORE":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
                overlay.fill((0, 0, 0, 240));
                self.screen.blit(overlay, (0, 0))
                self.screen.blit(self.title_font.render("SYSTEM STORE", True, NEON_BLUE), (100, 50))
                self.screen.blit(self.font.render(f"Souls: {self.player.souls}", True, NEON_PURPLE), (100, 100))

                sell_val = self.get_sellable_loot_value()
                if sell_val > 0:
                    self.screen.blit(
                        self.font.render(f"Press [SPACE] to Sell All Loot (+{sell_val} Souls)", True, NEON_GREEN),
                        (100, 140))
                else:
                    self.screen.blit(self.font.render("No loot to sell.", True, TXT_GRAY), (100, 140))

                for i, item in enumerate(self.store):
                    col = NEON_GOLD if i == self.store_sel else TXT_WHITE
                    self.screen.blit(
                        self.font.render(f"{'> ' if i == self.store_sel else ''}{item[0]} ... {item[1]} Souls", True,
                                         col), (100, 200 + i * 40))

            elif self.state == "NEXT_FLOOR":
                self.screen.blit(self.title_font.render("FLOOR CLEAR", True, NEON_GOLD), (WIDTH // 2 - 100, 300))
                self.screen.blit(self.font.render("[ENTER] Next Floor", True, TXT_WHITE), (WIDTH // 2 - 70, 350))

            elif self.state == "GAMEOVER":
                self.screen.blit(self.title_font.render("YOU DIED", True, NEON_RED), (WIDTH // 2 - 80, 300))
                self.screen.blit(self.font.render("[ENTER] Menu", True, TXT_WHITE), (WIDTH // 2 - 60, 360))

            else:
                self.draw_game()

                # --- OVERLAY CHARACTER (Staty) ---
                if self.state == "CHARACTER":
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
                    overlay.fill((0, 0, 0, 220));
                    self.screen.blit(overlay, (0, 0))
                    self.screen.blit(self.title_font.render("CHARACTER PROFILE", True, NEON_BLUE),
                                     (WIDTH // 2 - 150, 50))

                    self.screen.blit(self.font.render(f"Available Points: {self.player.stat_points}", True, NEON_GOLD),
                                     (WIDTH // 2 - 90, 120))

                    opts = [
                        (f"STR: {self.player.stats['str']}", "1", "+ DMG, Defense"),
                        (f"AGI: {self.player.stats['dex']}", "2", "+ Crit Damage"),
                        (f"INT: {self.player.stats['int']}", "3", "+ Max Mana, Shadow DMG"),
                        (f"VIT: {self.player.stats['vigor']}", "4", "+ Max HP"),
                        (f"SNS: {self.player.stats['sense']}", "5", "+ Crit Chance")
                    ]

                    cy = 180
                    for text, key, desc in opts:
                        self.screen.blit(self.font.render(text, True, TXT_WHITE), (WIDTH // 2 - 200, cy))
                        self.screen.blit(self.font.render(desc, True, TXT_GRAY), (WIDTH // 2 - 80, cy))
                        if self.player.stat_points > 0:
                            self.screen.blit(self.font.render(f"Press [{key}] to Upgrade", True, NEON_GREEN),
                                             (WIDTH // 2 + 100, cy))
                        cy += 40

                    self.screen.blit(self.font.render("Press [C] or [ESC] to Close", True, NEON_RED),
                                     (WIDTH // 2 - 120, HEIGHT - 100))

                # --- OVERLAY INVENTÁŘE ---
                elif self.state == "INVENTORY":
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
                    overlay.fill((0, 0, 0, 220));
                    self.screen.blit(overlay, (0, 0))
                    self.screen.blit(self.title_font.render("PLAYER INVENTORY", True, NEON_BLUE),
                                     (WIDTH // 2 - 150, 50))

                    self.screen.blit(self.font.render("--- EQUIPPED ---", True, NEON_GOLD), (WIDTH // 2 - 150, 120))
                    self.screen.blit(self.font.render(f"Weapon: {self.player.weapon.name}", True, TXT_WHITE),
                                     (WIDTH // 2 - 130, 150))
                    self.screen.blit(self.font.render(
                        f"Damage: {self.player.weapon.min_dmg} - {self.player.weapon.max_dmg} (+ scaling)", True,
                        TXT_GRAY), (WIDTH // 2 - 130, 180))
                    self.screen.blit(self.font.render(f"Total Defense: {self.player.total_def}", True, TXT_WHITE),
                                     (WIDTH // 2 - 130, 210))

                    self.screen.blit(self.font.render("--- LOOT & ITEMS ---", True, NEON_GREEN),
                                     (WIDTH // 2 - 150, 270))
                    counts = {}
                    for item in self.player.inventory: counts[item] = counts.get(item, 0) + 1

                    iy = 300
                    if not counts:
                        self.screen.blit(self.font.render("Inventory is empty.", True, TXT_GRAY),
                                         (WIDTH // 2 - 130, iy))
                    else:
                        for item, count in counts.items():
                            val = LOOT_DB.get(item, 0)
                            val_txt = f"({val} Souls each)" if val > 0 else "(Consumable)"
                            self.screen.blit(self.font.render(f"{count}x {item}  {val_txt}", True, TXT_WHITE),
                                             (WIDTH // 2 - 130, iy))
                            iy += 30

                    self.screen.blit(self.font.render("Press [I] or [ESC] to Close", True, NEON_RED),
                                     (WIDTH // 2 - 120, HEIGHT - 100))

                # --- OVERLAY NÁPOVĚDY ---
                elif self.state == "HELP":
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
                    overlay.fill((0, 0, 0, 220));
                    self.screen.blit(overlay, (0, 0))
                    self.screen.blit(self.title_font.render("SYSTEM CONTROLS", True, NEON_BLUE), (WIDTH // 2 - 150, 50))

                    controls = [
                        ("[ARROWS]", "Move through the Dungeon"),
                        ("[SPACE]", "Basic Attack in Combat / Sell Loot in Store"),
                        ("[Q], [W], [E]", "Use Class Skills (Requires Mana)"),
                        ("[S]", "Arise! Shadow Extraction AOE Attack"),
                        ("[H]", "Use Healing Potion in Combat"),
                        ("[U]", "Escape from Combat (Costs Souls)"),
                        ("[C]", "Open Character Stats / Level Up"),
                        ("[I]", "Open Inventory & Equipment"),
                        ("[B]", "Open Store (Only outside combat)"),
                    ]
                    cy = 150
                    for key, desc in controls:
                        self.screen.blit(self.font.render(key, True, NEON_GOLD), (WIDTH // 2 - 250, cy))
                        self.screen.blit(self.font.render(f"- {desc}", True, TXT_WHITE), (WIDTH // 2 - 100, cy))
                        cy += 40
                    self.screen.blit(self.font.render("Press [H] or [ESC] to Close", True, NEON_RED),
                                     (WIDTH // 2 - 120, HEIGHT - 100))

            pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()