#!/usr/bin/env python3
"""
patch_auth_sqlite.py
- Système d'inscription/connexion avec SQLite
- Suppression de l'ancien système mono/multi-code
- Footer LinkedIn à la place de GitHub
- Page login/register moderne

Exécuter depuis SenGenoScope/ :
  python3 patch_auth_sqlite.py
"""
import os, re

# ─────────────────────────────────────────────────────────────
# 1. CRÉER templates/login.html (inscription + connexion)
# ─────────────────────────────────────────────────────────────
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta name="google" content="notranslate">
<link rel="icon" href="/static/favicon.ico">
<title>SenGenoScope — Access</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"DM Sans",sans-serif;background:linear-gradient(135deg,#0c6e9c 0%,#7c3aed 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#fff;border-radius:20px;padding:44px 40px;width:100%;max-width:440px;box-shadow:0 24px 60px rgba(0,0,0,.2)}
.logo{display:flex;align-items:center;gap:10px;margin-bottom:28px;justify-content:center}
.logo-icon{width:44px;height:44px;background:linear-gradient(135deg,#0c6e9c,#7c3aed);border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:22px}
.logo-text{font-size:22px;font-weight:800;color:#1a2332}
.logo-text span{color:#0c6e9c}
.tabs{display:flex;background:#f0f4f8;border-radius:10px;padding:4px;margin-bottom:28px}
.tab{flex:1;text-align:center;padding:9px;border-radius:7px;font-size:14px;font-weight:600;cursor:pointer;color:#6b7a8d;border:none;background:none;font-family:inherit;transition:all .15s}
.tab.active{background:#fff;color:#0c6e9c;box-shadow:0 1px 4px rgba(0,0,0,.1)}
.panel{display:none}.panel.active{display:block}
label{font-size:13px;font-weight:600;color:#1a2332;display:block;margin-bottom:5px}
input{width:100%;padding:11px 14px;border:1.5px solid #dde3ea;border-radius:9px;font-size:14px;font-family:inherit;outline:none;transition:border .15s;color:#1a2332;margin-bottom:14px}
input:focus{border-color:#0c6e9c}
.btn{width:100%;padding:13px;background:#0c6e9c;color:#fff;border:none;border-radius:9px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s;margin-top:4px}
.btn:hover{background:#085880}
.error{background:#fee2e2;color:#b91c1c;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:14px}
.success{background:#dcfce7;color:#15803d;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:14px}
.badge{background:#f0f4f8;border-radius:6px;padding:4px 10px;font-size:12px;color:#6b7a8d;text-align:center;margin-bottom:20px;display:block}
.hint{font-size:12px;color:#9aa3af;margin-top:-10px;margin-bottom:14px}
.back{text-align:center;margin-top:18px;font-size:13px;color:#6b7a8d}
.back a{color:#0c6e9c;text-decoration:none;font-weight:600}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🧬</div>
    <div class="logo-text"><span>Sen</span>GenoScope</div>
  </div>
  <span class="badge">🔬 Clinical Oncogenomics Platform · Free Access</span>

  <div class="tabs">
    <button class="tab active" onclick="switchTab('login',this)">Sign in</button>
    <button class="tab" onclick="switchTab('register',this)">Create account</button>
  </div>

  <!-- LOGIN -->
  <div class="panel active" id="panel-login">
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="login">
      <label>Email</label>
      <input type="email" name="email" placeholder="your@email.com" autofocus autocomplete="email"/>
      <label>Password</label>
      <input type="password" name="password" placeholder="Your password" autocomplete="current-password"/>
      <button type="submit" class="btn">🚀 Sign in</button>
    </form>
  </div>

  <!-- REGISTER -->
  <div class="panel" id="panel-register">
    {% if reg_error %}<div class="error">{{ reg_error }}</div>{% endif %}
    {% if reg_success %}<div class="success">{{ reg_success }}</div>{% endif %}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="register">
      <label>Full name</label>
      <input type="text" name="name" placeholder="Dr. Firstname Lastname" autocomplete="name"/>
      <label>Institution (optional)</label>
      <input type="text" name="institution" placeholder="UCAD, CHU de Dakar…" autocomplete="organization"/>
      <label>Email</label>
      <input type="email" name="email" placeholder="your@email.com" autocomplete="email"/>
      <label>Password</label>
      <input type="password" name="password" placeholder="Min. 6 characters" autocomplete="new-password"/>
      <p class="hint">Your data is stored securely and never shared.</p>
      <button type="submit" class="btn">✅ Create my account</button>
    </form>
  </div>

  <div class="back"><a href="/">← Back to home</a></div>
</div>

<script>
function switchTab(tab, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('panel-' + tab).classList.add('active');
}
// Si erreur d'inscription, afficher l'onglet register
{% if reg_error or reg_success %}
document.querySelector('.tab:last-child').click();
{% endif %}
</script>
</body>
</html>'''

os.makedirs('templates', exist_ok=True)
with open('templates/login.html', 'w') as f:
    f.write(LOGIN_HTML)
print("✅ templates/login.html créé (inscription + connexion)")

# ─────────────────────────────────────────────────────────────
# 2. PATCH app.py — remplacer l'auth par SQLite
# ─────────────────────────────────────────────────────────────
with open('app.py', 'r') as f:
    content = f.read()

# Ajouter imports SQLite en tête (après les imports existants)
SQLITE_IMPORTS = '''import sqlite3, hashlib, secrets as _secrets
from datetime import timedelta
'''

if 'import sqlite3' not in content:
    content = content.replace(
        'import requests as req\nimport io, csv, os, json, base64',
        'import requests as req\nimport io, csv, os, json, base64\nimport sqlite3, hashlib\nfrom datetime import timedelta'
    )
    print("✅ Imports SQLite ajoutés")
else:
    print("✅ Imports SQLite déjà présents")

# Remplacer le système ACCESS_CODES par SQLite
OLD_AUTH = '''app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Multi-codes : ACCESS_CODES = "CODE1,CODE2,CODE3" dans les variables Render
_raw = os.environ.get("ACCESS_CODES", os.environ.get("ACCESS_CODE", "sengenoscope2026"))
ACCESS_CODES = [c.strip() for c in _raw.split(",") if c.strip()]'''

NEW_AUTH = '''app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=30)

# ── Base de données utilisateurs SQLite ─────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_db():
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
    conn.close()

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def create_user(name, institution, email, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO users (name, institution, email, password_hash) VALUES (?,?,?,?)",
            (name, institution, email, hash_password(password))
        )
        conn.commit()
        conn.close()
        return True, None
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    except Exception as e:
        return False, str(e)

def verify_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, name, institution FROM users WHERE email=? AND password_hash=?",
        (email, hash_password(password))
    ).fetchone()
    conn.close()
    return row  # (id, name, institution) ou None

init_db()'''

if OLD_AUTH in content:
    content = content.replace(OLD_AUTH, NEW_AUTH)
    print("✅ Système SQLite remplace ACCESS_CODES")
else:
    # Fallback : remplacer juste la ligne ACCESS_CODES
    content = re.sub(
        r'app\.secret_key = os\.environ\.get.*?\nACCESS_CODES.*?\n',
        NEW_AUTH + '\n',
        content, flags=re.DOTALL, count=1
    )
    print("✅ Système SQLite inséré (fallback)")

# Remplacer les routes login/logout/login_required
OLD_LOGIN_REQUIRED = '''def login_required(f):'''

NEW_LOGIN_BLOCK = '''def login_required(f):'''

# Remplacer toute la logique d'authentification
# Trouver et remplacer le bloc complet login_required + route /login + route /logout
AUTH_BLOCK_PATTERN = r'def login_required\(f\):.*?def logout\(\):.*?return redirect\(url_for\("landing_page"\)\)'

NEW_AUTH_BLOCK = '''def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    reg_error = None
    reg_success = None

    if request.method == "POST":
        action = request.form.get("action", "login")

        if action == "register":
            name = request.form.get("name", "").strip()
            institution = request.form.get("institution", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not name or not email or not password:
                reg_error = "Please fill in all required fields."
            elif len(password) < 6:
                reg_error = "Password must be at least 6 characters."
            else:
                ok, err = create_user(name, institution, email, password)
                if ok:
                    reg_success = f"Account created for {name}! You can now sign in."
                else:
                    reg_error = err

        else:  # login
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = verify_user(email, password)
            if user:
                session["authenticated"] = True
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_institution"] = user[2]
                session.permanent = True
                return redirect(url_for("app_main"))
            else:
                error = "❌ Incorrect email or password."

    return render_template("login.html", error=error, reg_error=reg_error, reg_success=reg_success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing_page"))'''

if re.search(AUTH_BLOCK_PATTERN, content, re.DOTALL):
    content = re.sub(AUTH_BLOCK_PATTERN, NEW_AUTH_BLOCK, content, flags=re.DOTALL)
    print("✅ Routes login/logout remplacées")
else:
    # Chercher et remplacer manuellement
    if 'def login_required' in content:
        # Trouver la position
        idx_start = content.find('def login_required')
        idx_end = content.find('\n@app.route', idx_start + 100)
        # Trouver la fin du bloc logout
        idx_logout = content.find('def logout', idx_end)
        if idx_logout > 0:
            idx_end_logout = content.find('\n\n@app.route', idx_logout)
            if idx_end_logout > 0:
                content = content[:idx_start] + NEW_AUTH_BLOCK + content[idx_end_logout:]
                print("✅ Routes login/logout remplacées (méthode 2)")
            else:
                print("⚠️  Fin du bloc logout non trouvée")
        else:
            print("⚠️  def logout non trouvée")
    else:
        print("❌ login_required non trouvé — insertion manuelle")

# Ajouter route /api/users/count pour stats (optionnel)
STATS_ROUTE = '''
@app.route("/api/users/count")
def users_count():
    """Nombre d'utilisateurs inscrits (public, sans données perso)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return jsonify({"count": count})
    except:
        return jsonify({"count": 0})

'''

if '/api/users/count' not in content:
    # Insérer avant la route /morpho_analyze
    content = content.replace(
        "@app.route('/morpho_analyze'",
        STATS_ROUTE + "@app.route('/morpho_analyze'"
    )
    print("✅ Route /api/users/count ajoutée")

with open('app.py', 'w') as f:
    f.write(content)

print("✅ app.py patché")

# ─────────────────────────────────────────────────────────────
# 3. PATCH landing.html — remplacer GitHub par LinkedIn
# ─────────────────────────────────────────────────────────────
LANDING_PATH = 'templates/landing.html'
if os.path.exists(LANDING_PATH):
    with open(LANDING_PATH, 'r') as f:
        landing = f.read()

    # Remplacer le lien GitHub par LinkedIn
    landing = re.sub(
        r'<a href="https://github\.com/[^"]*"[^>]*>GitHub</a>',
        '<a href="https://www.linkedin.com/in/moustapha-gassama" target="_blank">LinkedIn</a>',
        landing
    )
    # Supprimer "· GitHub" si présent seul
    landing = landing.replace(' · GitHub', '')
    landing = landing.replace('GitHub ·', '')

    with open(LANDING_PATH, 'w') as f:
        f.write(landing)
    print("✅ Footer landing.html : GitHub → LinkedIn")
else:
    print("⚠️  landing.html non trouvé")

# ─────────────────────────────────────────────────────────────
# 4. Ajouter users.db dans .gitignore
# ─────────────────────────────────────────────────────────────
GITIGNORE_PATH = '.gitignore'
gitignore_content = open(GITIGNORE_PATH).read() if os.path.exists(GITIGNORE_PATH) else ''
if 'users.db' not in gitignore_content:
    with open(GITIGNORE_PATH, 'a') as f:
        f.write('\n# Base de données utilisateurs (ne pas committer)\nusers.db\n*.db\n')
    print("✅ users.db ajouté dans .gitignore")
else:
    print("✅ users.db déjà dans .gitignore")

# ─────────────────────────────────────────────────────────────
# 5. Vérifications finales
# ─────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("VÉRIFICATIONS FINALES")
with open('app.py', 'r') as f:
    final = f.read()

checks = {
    'SQLite init_db': 'def init_db' in final,
    'create_user': 'def create_user' in final,
    'verify_user': 'def verify_user' in final,
    'Route /login': '"/login"' in final,
    'Route /logout': '"/logout"' in final,
    'login_required': 'def login_required' in final,
    '/app protégé': '@login_required\ndef app_main' in final,
    'users.db gitignore': 'users.db' in open('.gitignore').read(),
}
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print()
print("COMMANDES SUIVANTES :")
print("  git add app.py templates/login.html templates/landing.html .gitignore")
print('  git commit -m "feat: authentification SQLite + inscription publique + footer LinkedIn"')
print("  git push origin main")
print()
print("NOTE : Sur Render, assurez-vous que SECRET_KEY est défini dans Environment.")
print("       La base users.db sera créée automatiquement au premier démarrage.")
