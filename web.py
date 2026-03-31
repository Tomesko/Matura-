from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'sololeveling_v15.db'

# --- HERNÍ DATA PRO WIKI ---
LOOT_DB = {
    "Demon Horn": 15, "Torn Cloth": 5, "Beast Fang": 25,
    "Shadow Core": 50, "Broken Bone": 10, "Magic Dust": 35,
    "Goblin Ear": 8, "Wolf Pelt": 12,
    "Iron Ore": 10, "Magic Crystal": 20,
    "Weapon Scraps": 150, "Armor Scraps": 100
}

BOSS_WEAPONS = {
    "Vulcan's Club": (15, 25, "STR", 1.5, 1000),
    "Metus' Scythe": (10, 30, "INT", 1.6, 1500),
    "Baran's Daggers": (20, 35, "DEX", 1.8, 2500)
}

# (Jméno, Typ, Staty/Efekt, Odemknutí, Cena)
STORE_EQUIPMENT = [
    ("Killer Dagger", "Weapon", "10 - 16 DMG (STR scaling)", "Available from Start", 500),
    ("Shadow Armor", "Armor", "+5 Total DEF", "Unlocks at Floor 5", 1500),
    ("Demon King's Sword", "Weapon", "50 - 83 DMG (STR scaling)", "Unlocks at Floor 10", 2500),
    ("Orb of Avarice", "Weapon", "40 - 66 DMG (STR scaling)", "Unlocks at Floor 10", 2000),
]

# (Jméno, Min Patro, HP, DMG, XP, Souls)
DEMON_TYPES = [
    ("Goblin", 1, 15, 3, 4, 5),
    ("Low Rank Demon", 1, 20, 5, 5, 10),
    ("Dire Wolf", 2, 25, 6, 8, 12),
    ("Flying Demon", 3, 30, 8, 10, 15),
    ("Hobgoblin", 4, 45, 12, 18, 25),
    ("Cerberus", 5, 60, 15, 25, 50),
    ("Shadow Beast", 7, 70, 18, 30, 35),
    ("High Orc", 10, 80, 20, 35, 40),
    ("Vampire", 12, 100, 25, 45, 60),
    ("Demon Knight", 15, 120, 30, 60, 80),
    ("Death Knight", 18, 140, 40, 80, 100),
    ("Arch-Lich", 20, 150, 50, 100, 150),
    ("Bone Dragon", 25, 200, 60, 150, 200),
    ("VULCAN (Boss)", 10, 345, 34, 575, 345),
    ("METUS (Boss)", 20, 1200, 120, 2000, 1200),
    ("BARAN (Boss)", 30, 1650, 165, 2750, 1650),
]

# --- HTML ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Solo Leveling | Hunter Association</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #05080f; color: #f0f0ff; font-family: 'Rajdhani', sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; padding-bottom: 50px;}
        h1 { color: #00beff; font-size: 3em; text-transform: uppercase; text-shadow: 0 0 20px #00beff; margin-top: 30px;}

        /* TABS STYLING */
        .tabs { display: flex; gap: 15px; margin-top: 20px; margin-bottom: 20px; }
        .tab-btn { background: #0a0d18; color: #00beff; border: 2px solid #00beff; padding: 10px 25px; font-size: 1.2em; font-family: 'Rajdhani'; font-weight: bold; cursor: pointer; text-transform: uppercase; border-radius: 5px; transition: 0.3s;}
        .tab-btn:hover { background: rgba(0, 190, 255, 0.2); box-shadow: 0 0 10px #00beff; }
        .tab-btn.active { background: #00beff; color: #05080f; box-shadow: 0 0 15px #00beff; }

        .tab-content { display: none; width: 90%; max-width: 1000px; background: #0a0d18; border: 2px solid #00beff; border-radius: 10px; padding: 20px; box-shadow: 0 0 15px rgba(0, 190, 255, 0.2); }
        .tab-content.active { display: block; }

        /* TABLES */
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { color: #ffd700; padding: 10px; border-bottom: 2px solid #00beff; text-transform: uppercase; }
        td { padding: 10px; text-align: center; border-bottom: 1px solid #141928; font-size: 1.2em;}
        tr:hover { background-color: #141928; }

        /* REGISTER FORM */
        .register-form { display: flex; flex-direction: column; align-items: center; gap: 15px; }
        .register-form input[type="text"], .register-form input[type="password"] { width: 300px; padding: 10px; background: #141928; border: 1px solid #00beff; color: white; font-size: 1.2em; font-family: 'Rajdhani'; text-align: center;}
        .checkbox-container { display: flex; align-items: center; gap: 10px; font-size: 1.2em; color: #50ff64;}
        .register-form button { background: #00beff; color: black; padding: 10px 30px; border: none; font-size: 1.3em; font-weight: bold; cursor: pointer; text-transform: uppercase;}
        .register-form button:hover { background: #50ff64; box-shadow: 0 0 15px #50ff64;}

        .error { color: #ff2828; font-weight: bold; font-size: 1.2em; text-shadow: 0 0 5px #ff2828;}
        .success { color: #50ff64; font-weight: bold; font-size: 1.2em; text-shadow: 0 0 5px #50ff64;}
    </style>
    <script>
        function showTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }
    </script>
</head>
<body>
    <h1>Hunter Association</h1>

    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('rankings')">Rankings</button>
        <button class="tab-btn" onclick="showTab('register')">Register</button>
        <button class="tab-btn" onclick="showTab('bestiary')">Bestiary</button>
        <button class="tab-btn" onclick="showTab('items')">Item Database</button>
    </div>

    <div id="rankings" class="tab-content active">
        <h2 style="color:#ffd700; text-align:center;">Global Rankings</h2>
        <table>
            <tr><th>Rank</th><th>Hunter</th><th>Class</th><th>Max Floor</th><th>Level</th><th>Souls</th></tr>
            {% for h in hunters %}
            <tr>
                <td style="color:#ffd700; font-weight:bold;">#{{ loop.index }}</td>
                <td>{{ h[0] }}</td><td style="color:#b432ff;">{{ h[1] }}</td>
                <td style="color:#00beff;">{{ h[2] }}</td><td style="color:#50ff64;">{{ h[3] }}</td>
                <td style="color:#ff2828;">{{ h[4] }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div id="register" class="tab-content">
        <h2 style="color:#00beff; text-align:center;">Awakening Registration</h2>
        <div style="text-align: center; margin-bottom: 20px;">
            {% if msg %}<p class="success">{{ msg }}</p>{% endif %}
            {% if err %}<p class="error">{{ err }}</p>{% endif %}
            <p style="color: #646478;">You MUST register here before logging into the Game Client.</p>
        </div>
        <form class="register-form" method="POST" action="/register">
            <input type="text" name="username" placeholder="Enter Hunter Name" required>
            <input type="password" name="password" placeholder="Enter Password" required>
            <div class="checkbox-container">
                <input type="checkbox" name="not_a_bot" id="bot" required>
                <label for="bot">I confirm I am not a Monster/Bot</label>
            </div>
            <button type="submit">Complete Awakening</button>
        </form>
    </div>

    <div id="bestiary" class="tab-content">
        <h2 style="color:#ff2828; text-align:center;">System Bestiary</h2>
        <table>
            <tr><th>Demon Name</th><th>Found From Floor</th><th>Base HP</th><th>Base DMG</th><th>Base XP</th><th>Souls Drop</th></tr>
            {% for d in demons %}
            <tr>
                <td style="color: {% if 'Boss' in d[0] %}#ffd700{% else %}#f0f0ff{% endif %}; font-weight:bold;">{{ d[0] }}</td>
                <td style="color:#00beff;">{{ d[1] }}</td>
                <td style="color:#ff2828;">{{ d[2] }}</td>
                <td style="color:#ff2828;">{{ d[3] }}</td>
                <td style="color:#50ff64;">{{ d[4] }}</td>
                <td style="color:#b432ff;">{{ d[5] }}</td>
            </tr>
            {% endfor %}
        </table>
        <p style="text-align:center; color:#646478; margin-top:15px;">Note: Stats multiply scaling up with higher floors.</p>
    </div>

    <div id="items" class="tab-content">
        <h2 style="color:#50ff64; text-align:center;">Item & Equipment Database</h2>

        <h3 style="color:#50ff64; border-bottom: 1px solid #50ff64;">Store Equipment & Unlocks</h3>
        <table>
            <tr><th>Item Name</th><th>Type</th><th>Stats / Effect</th><th>Unlock Condition</th><th>Price (Souls)</th></tr>
            {% for item in store_equip %}
            <tr>
                <td style="color:#f0f0ff; font-weight:bold;">{{ item[0] }}</td>
                <td style="color:#b432ff;">{{ item[1] }}</td>
                <td style="color:#ff2828;">{{ item[2] }}</td>
                <td style="color:#00beff;">{{ item[3] }}</td>
                <td style="color:#ffd700;">{{ item[4] }}</td>
            </tr>
            {% endfor %}
        </table>

        <h3 style="color:#ffd700; border-bottom: 1px solid #ffd700; margin-top:30px;">Boss Rare Weapons (30% Drop Chance)</h3>
        <table>
            <tr><th>Weapon Name</th><th>Damage Range</th><th>Scaling Stat</th><th>Scale Multiplier</th><th>Sell Value (Souls)</th></tr>
            {% for name, stats in weapons.items() %}
            <tr>
                <td style="color:#ffd700;">{{ name }}</td>
                <td>{{ stats[0] }} - {{ stats[1] }}</td>
                <td style="color:#00beff;">{{ stats[2] }}</td>
                <td>x{{ stats[3] }}</td>
                <td style="color:#b432ff;">{{ stats[4] }}</td>
            </tr>
            {% endfor %}
        </table>

        <h3 style="color:#00beff; border-bottom: 1px solid #00beff; margin-top:30px;">Standard Loot & Materials</h3>
        <table>
            <tr><th>Item Name</th><th>Type</th><th>Sell Value (Souls)</th></tr>
            {% for name, val in loot.items() %}
            <tr>
                <td style="color:#f0f0ff;">{{ name }}</td>
                <td style="color:#646478;">{% if val >= 100 %}Scrap Material{% elif 'Ore' in name or 'Crystal' in name %}Crafting Material{% else %}Monster Loot{% endif %}</td>
                <td style="color:#b432ff;">{{ val }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    {% if msg or err %}
    <script>
        showTab('register');
    </script>
    {% endif %}
</body>
</html>
"""


@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT name, class, floor, level, souls FROM hunters ORDER BY floor DESC, level DESC LIMIT 10')
        hunters = c.fetchall()
    except sqlite3.OperationalError:
        hunters = []  # Pokud tabulka ještě neexistuje
    finally:
        conn.close()

    msg = request.args.get('msg')
    err = request.args.get('err')
    return render_template_string(HTML_TEMPLATE, hunters=hunters, loot=LOOT_DB, weapons=BOSS_WEAPONS,
                                  store_equip=STORE_EQUIPMENT, demons=DEMON_TYPES, msg=msg, err=err)


@app.route('/register', methods=['POST'])
def register():
    user = request.form['username'].strip()
    pwd = request.form['password'].strip()
    bot_check = request.form.get('not_a_bot')

    if not bot_check:
        return redirect(url_for('index', err="You must confirm you are not a bot!"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (user, pwd))
        conn.commit()
        return redirect(url_for('index', msg=f"Hunter '{user}' Awakened! You can now login in the game."))
    except sqlite3.IntegrityError:
        return redirect(url_for('index', err="Hunter Name already taken!"))
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)