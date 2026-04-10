#!/usr/bin/env python3
"""
patch_admin_dashboard.py
- Tableau de bord admin accessible sur /admin (protégé par ADMIN_PASSWORD)
- Log de chaque connexion dans la table login_logs (date, nom, email, IP)
- Logs visibles dans Render aussi
Exécuter depuis SenGenoScope/ :
  python3 patch_admin_dashboard.py
"""
import os, re

# ─────────────────────────────────────────────────────────────
# 1. CRÉER templates/admin.html
# ─────────────────────────────────────────────────────────────
ADMIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta name="google" content="notranslate">
<title>SenGenoScope — Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f0f4f8;color:#1a2332;min-height:100vh}
.topbar{background:#0c6e9c;color:#fff;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
.topbar h1{font-size:16px;font-weight:700}
.topbar a{color:rgba(255,255,255,.8);text-decoration:none;font-size:13px}
.container{max-width:1100px;margin:0 auto;padding:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:28px}
.stat{background:#fff;border-radius:12px;padding:20px 24px;border:1px solid #e2e8f0}
.stat-value{font-size:32px;font-weight:800;color:#0c6e9c}
.stat-label{font-size:13px;color:#6b7a8d;margin-top:4px}
.section{background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:20px;border:1px solid #e2e8f0}
.section h2{font-size:15px;font-weight:700;margin-bottom:16px;color:#1a2332}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;background:#f8fafc;color:#6b7a8d;font-weight:600;border-bottom:1px solid #e2e8f0}
td{padding:9px 12px;border-bottom:1px solid #f0f4f8;color:#1a2332}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f8fafc}
.badge{display:inline-block;padding:2px 8px;border-radius:5px;font-size:11px;font-weight:600}
.badge-new{background:#dcfce7;color:#15803d}
.badge-active{background:#dbeafe;color:#1d4ed8}
.logout{background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);color:#fff;padding:6px 14px;border-radius:7px;text-decoration:none;font-size:13px;font-weight:600}
.logout:hover{background:rgba(255,255,255,.3)}
.refresh{background:#0c6e9c;color:#fff;border:none;padding:7px 14px;border-radius:7px;font-size:13px;cursor:pointer;font-weight:600}
</style>
</head>
<body>
<div class="topbar">
  <h1>🧬 SenGenoScope — Admin Dashboard</h1>
  <div style="display:flex;gap:12px;align-items:center">
    <span style="font-size:13px;opacity:.8">Dr. Moustapha Gassama</span>
    <a href="/admin/logout" class="logout">Sign out</a>
  </div>
</div>

<div class="container">
  <!-- Stats -->
  <div class="stats">
    <div class="stat">
      <div class="stat-value">{{ stats.total_users }}</div>
      <div class="stat-label">Total users</div>
    </div>
    <div class="stat">
      <div class="stat-value">{{ stats.new_today }}</div>
      <div class="stat-label">New today</div>
    </div>
    <div class="stat">
      <div class="stat-value">{{ stats.logins_today }}</div>
      <div class="stat-label">Logins today</div>
    </div>
    <div class="stat">
      <div class="stat-value">{{ stats.logins_week }}</div>
      <div class="stat-label">Logins this week</div>
    </div>
  </div>

  <!-- Users table -->
  <div class="section">
    <h2>👥 Registered users ({{ users|length }})</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Institution</th>
          <th>Email</th>
          <th>Registered</th>
          <th>Last login</th>
        </tr>
      </thead>
      <tbody>
        {% for u in users %}
        <tr>
          <td>{{ u.id }}</td>
          <td><strong>{{ u.name }}</strong></td>
          <td style="color:#6b7a8d">{{ u.institution or '—' }}</td>
          <td style="color:#0c6e9c">{{ u.email }}</td>
          <td>{{ u.created_at[:10] }}</td>
          <td>{{ u.last_login or '—' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Login logs -->
  <div class="section">
    <h2>📋 Recent connections (last 50)</h2>
    <table>
      <thead>
        <tr>
          <th>Date & time</th>
          <th>Name</th>
          <th>Email</th>
          <th>IP address</th>
        </tr>
      </thead>
      <tbody>
        {% for log in logs %}
        <tr>
          <td style="color:#6b7a8d;font-family:monospace">{{ log.login_at }}</td>
          <td><strong>{{ log.name }}</strong></td>
          <td style="color:#0c6e9c">{{ log.email }}</td>
          <td style="font-family:monospace;color:#9aa3af">{{ log.ip or '—' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>'''

os.makedirs('templates', exist_ok=True)
with open('templates/admin.html', 'w') as f:
    f.write(ADMIN_HTML)
print("✅ templates/admin.html créé")

# ─────────────────────────────────────────────────────────────
# 2. Page login admin
# ─────────────────────────────────────────────────────────────
ADMIN_LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Admin — SenGenoScope</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0c6e9c;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;padding:40px;width:100%;max-width:360px;box-shadow:0 20px 50px rgba(0,0,0,.2)}
h1{font-size:20px;font-weight:700;margin-bottom:6px;text-align:center}
.sub{font-size:13px;color:#6b7a8d;text-align:center;margin-bottom:24px}
label{font-size:13px;font-weight:600;color:#1a2332;display:block;margin-bottom:5px}
input{width:100%;padding:11px 14px;border:1.5px solid #dde3ea;border-radius:9px;font-size:14px;font-family:inherit;outline:none;margin-bottom:14px}
input:focus{border-color:#0c6e9c}
.btn{width:100%;padding:12px;background:#0c6e9c;color:#fff;border:none;border-radius:9px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
.error{background:#fee2e2;color:#b91c1c;border-radius:8px;padding:9px 13px;font-size:13px;margin-bottom:14px}
</style>
</head>
<body>
<div class="card">
  <h1>🔐 Admin Access</h1>
  <p class="sub">SenGenoScope — Dr. Moustapha Gassama</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Admin password</label>
    <input type="password" name="password" autofocus placeholder="Admin password"/>
    <button type="submit" class="btn">Access dashboard</button>
  </form>
</div>
</body>
</html>'''

with open('templates/admin_login.html', 'w') as f:
    f.write(ADMIN_LOGIN_HTML)
print("✅ templates/admin_login.html créé")

# ─────────────────────────────────────────────────────────────
# 3. PATCH app.py
# ─────────────────────────────────────────────────────────────
with open('app.py', 'r') as f:
    content = f.read()

# 3a. Ajouter table login_logs + last_login dans init_db
OLD_INIT_DB = '''def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        institution TEXT DEFAULT '',
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()'''

NEW_INIT_DB = '''def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        institution TEXT DEFAULT '',
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        email TEXT,
        ip TEXT,
        login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()'''

if OLD_INIT_DB in content:
    content = content.replace(OLD_INIT_DB, NEW_INIT_DB)
    print("✅ Table login_logs ajoutée dans init_db")
else:
    print("⚠️  init_db non trouvé exactement — patch manuel nécessaire")

# 3b. Ajouter fonction log_login
LOG_LOGIN_FUNC = '''
def log_login(user_id, name, email, ip):
    """Enregistre chaque connexion dans login_logs et met à jour last_login."""
    import logging
    logging.info(f"[LOGIN] {name} <{email}> depuis {ip}")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO login_logs (user_id, name, email, ip) VALUES (?,?,?,?)",
            (user_id, name, email, ip)
        )
        conn.execute(
            "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"[LOGIN LOG ERROR] {e}")

'''

if 'def log_login' not in content:
    content = content.replace(
        'def hash_password',
        LOG_LOGIN_FUNC + 'def hash_password'
    )
    print("✅ Fonction log_login ajoutée")
else:
    print("✅ log_login déjà présente")

# 3c. Appeler log_login dans la route /login après vérification
OLD_LOGIN_SUCCESS = '''            if user:
                session["authenticated"] = True
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_institution"] = user[2]
                session.permanent = True
                return redirect(url_for("app_main"))'''

NEW_LOGIN_SUCCESS = '''            if user:
                session["authenticated"] = True
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_institution"] = user[2]
                session.permanent = True
                ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
                log_login(user[0], user[1], email, ip)
                return redirect(url_for("app_main"))'''

if OLD_LOGIN_SUCCESS in content:
    content = content.replace(OLD_LOGIN_SUCCESS, NEW_LOGIN_SUCCESS)
    print("✅ log_login appelé lors de la connexion")
else:
    print("⚠️  Bloc login success non trouvé exactement")

# 3d. Ajouter ADMIN_PASSWORD + routes /admin
ADMIN_ROUTES = '''
# ── Admin Dashboard ──────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-sgs-2026")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_authenticated"] = True
            return redirect("/admin")
        error = "Incorrect admin password."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    return redirect("/admin/login")

@app.route("/admin")
@admin_required
def admin_dashboard():
    import sqlite3 as _sq
    from datetime import datetime, timedelta
    conn = _sq.connect(DB_PATH)
    conn.row_factory = _sq.Row

    users = conn.execute(
        "SELECT id, name, institution, email, created_at, last_login FROM users ORDER BY created_at DESC"
    ).fetchall()

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    stats = {
        "total_users": len(users),
        "new_today": conn.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at)=?", (today,)
        ).fetchone()[0],
        "logins_today": conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE DATE(login_at)=?", (today,)
        ).fetchone()[0],
        "logins_week": conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE DATE(login_at)>=?", (week_ago,)
        ).fetchone()[0],
    }

    logs = conn.execute(
        "SELECT name, email, ip, login_at FROM login_logs ORDER BY login_at DESC LIMIT 50"
    ).fetchall()

    conn.close()
    return render_template("admin.html", users=users, stats=stats, logs=logs)

'''

if 'def admin_dashboard' not in content:
    content = content.replace(
        "@app.route('/morpho_analyze'",
        ADMIN_ROUTES + "@app.route('/morpho_analyze'"
    )
    print("✅ Routes admin ajoutées")
else:
    print("✅ Routes admin déjà présentes")

with open('app.py', 'w') as f:
    f.write(content)

print("✅ app.py patché")

# ─────────────────────────────────────────────────────────────
# 4. Vérifications
# ─────────────────────────────────────────────────────────────
with open('app.py', 'r') as f:
    final = f.read()

print("\n" + "="*55)
checks = {
    'login_logs table': 'login_logs' in final,
    'log_login function': 'def log_login' in final,
    'log_login appelé': 'log_login(user[0]' in final,
    'admin_dashboard': 'def admin_dashboard' in final,
    'ADMIN_PASSWORD': 'ADMIN_PASSWORD' in final,
    'admin_login template': os.path.exists('templates/admin_login.html'),
    'admin template': os.path.exists('templates/admin.html'),
}
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print()
print("COMMANDES SUIVANTES :")
print("  git add app.py templates/admin.html templates/admin_login.html")
print('  git commit -m "feat: admin dashboard + logs de connexion"')
print("  git push origin main")
print()
print("Sur Render → Environment, ajoutez :")
print("  ADMIN_PASSWORD = votre-mot-de-passe-admin-secret")
print()
print("Accès admin : https://clinical-genomic.onrender.com/admin")
