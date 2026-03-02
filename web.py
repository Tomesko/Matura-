from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'sololeveling_v15.db'


# --- INICIALIZACE DATABÁZE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS hunters (id INTEGER PRIMARY KEY, date TEXT, name TEXT, class TEXT, floor INTEGER, level INTEGER, souls INTEGER)''')
    conn.commit()
    conn.close()


init_db()

# --- HTML ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Solo Leveling | Hunter Association</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #05080f; color: #f0f0ff; font-family: 'Rajdhani', sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; }
        h1 { color: #00beff; font-size: 3em; text-transform: uppercase; text-shadow: 0 0 20px #00beff; margin-top: 30px;}
        .container { display: flex; width: 90%; max-width: 1200px; gap: 20px; margin-top: 20px; align-items: flex-start;}
        .box { background: #0a0d18; border: 2px solid #00beff; border-radius: 10px; padding: 20px; box-shadow: 0 0 15px rgba(0, 190, 255, 0.2); }

        .register-box { flex: 1; text-align: center; }
        .register-box input { width: 80%; padding: 10px; margin: 10px 0; background: #141928; border: 1px solid #00beff; color: white; font-size: 1.2em; font-family: 'Rajdhani';}
        .register-box button { background: #00beff; color: black; padding: 10px 20px; border: none; font-size: 1.2em; font-weight: bold; cursor: pointer; text-transform: uppercase;}
        .register-box button:hover { background: #50ff64; }

        .leaderboard-box { flex: 2; }
        table { width: 100%; border-collapse: collapse; }
        th { color: #ffd700; padding: 10px; border-bottom: 2px solid #00beff; text-transform: uppercase; }
        td { padding: 10px; text-align: center; border-bottom: 1px solid #141928; font-size: 1.2em;}
        .error { color: #ff2828; font-weight: bold; }
        .success { color: #50ff64; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Hunter Association Database</h1>
    <div class="container">

        <div class="box register-box">
            <h2 style="color:#00beff;">AWAKEN (Register)</h2>
            {% if msg %}<p class="success">{{ msg }}</p>{% endif %}
            {% if err %}<p class="error">{{ err }}</p>{% endif %}
            <form method="POST" action="/register">
                <input type="text" name="username" placeholder="Hunter Name" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Register to System</button>
            </form>
            <p style="color: #646478; font-size: 0.9em; margin-top:20px;">Use this account to login directly in the Game Client.</p>
        </div>

        <div class="box leaderboard-box">
            <h2 style="color:#ffd700; text-align:center;">GLOBAL RANKINGS</h2>
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
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, class, floor, level, souls FROM hunters ORDER BY floor DESC, level DESC LIMIT 10')
    hunters = c.fetchall()
    conn.close()

    msg = request.args.get('msg')
    err = request.args.get('err')
    return render_template_string(HTML_TEMPLATE, hunters=hunters, msg=msg, err=err)


@app.route('/register', methods=['POST'])
def register():
    user = request.form['username'].strip()
    pwd = request.form['password'].strip()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (user, pwd))
        conn.commit()
        conn.close()
        return redirect(
            url_for('index', msg=f"Hunter '{user}' successfully registered! You can now login in the game."))
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('index', err="Name already taken!"))


if __name__ == '__main__':
    app.run(debug=True, port=5000)