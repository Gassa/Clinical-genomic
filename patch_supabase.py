#!/usr/bin/env python3
"""
patch_supabase.py
Migration de SQLite vers Supabase (PostgreSQL).
Nécessite DATABASE_URL dans les variables d'environnement Render.

Exécuter depuis SenGenoScope/ :
  python3 patch_supabase.py
"""
import os, re

# ─────────────────────────────────────────────────────────────
# 1. Ajouter psycopg2 dans requirements.txt
# ─────────────────────────────────────────────────────────────
with open('requirements.txt', 'r') as f:
    reqs = f.read()

if 'psycopg2' not in reqs:
    with open('requirements.txt', 'a') as f:
        f.write('\npsycopg2-binary>=2.9.9\n')
    print("✅ psycopg2-binary ajouté dans requirements.txt")
else:
    print("✅ psycopg2 déjà présent")

# ─────────────────────────────────────────────────────────────
# 2. PATCH app.py — remplacer SQLite par PostgreSQL/SQLite hybride
# ─────────────────────────────────────────────────────────────
with open('app.py', 'r') as f:
    content = f.read()

# Remplacer le bloc init_db complet par version hybride
OLD_DB_BLOCK = '''app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
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
    conn.close()

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()'''

NEW_DB_BLOCK = '''app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=30)

# ── Base de données — PostgreSQL (Supabase) ou SQLite fallback ───────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

import logging
logging.basicConfig(level=logging.INFO)

def get_conn():
    """Retourne une connexion PostgreSQL ou SQLite selon l'environnement."""
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn, "pg"
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def init_db():
    conn, db_type = get_conn()
    cur = conn.cursor()
    if db_type == "pg":
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            institution TEXT DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            last_login TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS login_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            email TEXT,
            ip TEXT,
            login_at TIMESTAMP DEFAULT NOW()
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            institution TEXT DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            email TEXT,
            ip TEXT,
            login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    conn.commit()
    conn.close()
    logging.info(f"[DB] Initialisée — mode: {'PostgreSQL/Supabase' if USE_POSTGRES else 'SQLite (local)'}")

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()'''

if OLD_DB_BLOCK in content:
    content = content.replace(OLD_DB_BLOCK, NEW_DB_BLOCK)
    print("✅ init_db migré vers PostgreSQL/SQLite hybride")
else:
    print("⚠️  Bloc DB non trouvé exactement — vérifier manuellement")

# Remplacer create_user pour supporter PostgreSQL
OLD_CREATE_USER = '''def create_user(name, institution, email, password):
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
        return False, str(e)'''

NEW_CREATE_USER = '''def create_user(name, institution, email, password):
    try:
        conn, db_type = get_conn()
        ph = hash_password(password)
        if db_type == "pg":
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, institution, email, password_hash) VALUES (%s,%s,%s,%s)",
                (name, institution, email, ph)
            )
        else:
            conn.execute(
                "INSERT INTO users (name, institution, email, password_hash) VALUES (?,?,?,?)",
                (name, institution, email, ph)
            )
        conn.commit()
        conn.close()
        logging.info(f"[REGISTER] Nouvel utilisateur: {name} <{email}>")
        return True, None
    except Exception as e:
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            return False, "This email is already registered."
        return False, err'''

if OLD_CREATE_USER in content:
    content = content.replace(OLD_CREATE_USER, NEW_CREATE_USER)
    print("✅ create_user migré")

# Remplacer verify_user
OLD_VERIFY_USER = '''def verify_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, name, institution FROM users WHERE email=? AND password_hash=?",
        (email, hash_password(password))
    ).fetchone()
    conn.close()
    return row  # (id, name, institution) ou None'''

NEW_VERIFY_USER = '''def verify_user(email, password):
    conn, db_type = get_conn()
    ph = hash_password(password)
    if db_type == "pg":
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, institution FROM users WHERE email=%s AND password_hash=%s",
            (email, ph)
        )
        row = cur.fetchone()
    else:
        row = conn.execute(
            "SELECT id, name, institution FROM users WHERE email=? AND password_hash=?",
            (email, ph)
        ).fetchone()
    conn.close()
    return row'''

if OLD_VERIFY_USER in content:
    content = content.replace(OLD_VERIFY_USER, NEW_VERIFY_USER)
    print("✅ verify_user migré")

# Remplacer log_login
OLD_LOG_LOGIN = '''def log_login(user_id, name, email, ip):
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
        logging.error(f"[LOGIN LOG ERROR] {e}")'''

NEW_LOG_LOGIN = '''def log_login(user_id, name, email, ip):
    """Enregistre chaque connexion dans login_logs et met à jour last_login."""
    logging.info(f"[LOGIN] {name} <{email}> depuis {ip}")
    try:
        conn, db_type = get_conn()
        if db_type == "pg":
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO login_logs (user_id, name, email, ip) VALUES (%s,%s,%s,%s)",
                (user_id, name, email, ip)
            )
            cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user_id,))
        else:
            conn.execute(
                "INSERT INTO login_logs (user_id, name, email, ip) VALUES (?,?,?,?)",
                (user_id, name, email, ip)
            )
            conn.execute(
                "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user_id,)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"[LOGIN LOG ERROR] {e}")'''

if OLD_LOG_LOGIN in content:
    content = content.replace(OLD_LOG_LOGIN, NEW_LOG_LOGIN)
    print("✅ log_login migré")

# Remplacer le dashboard admin pour PostgreSQL
OLD_ADMIN = '''    conn = _sq.connect(DB_PATH)
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

    conn.close()'''

NEW_ADMIN = '''    conn, db_type = get_conn()
    if db_type == "pg":
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, name, institution, email, created_at, last_login FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        cur.execute("SELECT COUNT(*) as c FROM users WHERE DATE(created_at)=CURRENT_DATE")
        new_today = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM login_logs WHERE DATE(login_at)=CURRENT_DATE")
        logins_today = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM login_logs WHERE login_at >= NOW() - INTERVAL '7 days'")
        logins_week = cur.fetchone()["c"]
        cur.execute("SELECT name, email, ip, login_at FROM login_logs ORDER BY login_at DESC LIMIT 50")
        logs = cur.fetchall()
    else:
        import sqlite3 as _sq2
        conn2 = _sq2.connect(DB_PATH)
        conn2.row_factory = _sq2.Row
        users = conn2.execute("SELECT id, name, institution, email, created_at, last_login FROM users ORDER BY created_at DESC").fetchall()
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        new_today = conn2.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at)=?", (today,)).fetchone()[0]
        logins_today = conn2.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_at)=?", (today,)).fetchone()[0]
        logins_week = conn2.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(login_at)>=?", (week_ago,)).fetchone()[0]
        logs = conn2.execute("SELECT name, email, ip, login_at FROM login_logs ORDER BY login_at DESC LIMIT 50").fetchall()
        conn2.close()

    stats = {
        "total_users": len(users),
        "new_today": new_today,
        "logins_today": logins_today,
        "logins_week": logins_week,
    }'''

if OLD_ADMIN in content:
    content = content.replace(OLD_ADMIN, NEW_ADMIN)
    print("✅ Admin dashboard migré vers PostgreSQL")

# Supprimer le conn.close() orphelin après le bloc admin
content = content.replace(
    NEW_ADMIN + "\n    conn.close()\n    return render_template",
    NEW_ADMIN + "\n    conn.close()\n    return render_template"
)

with open('app.py', 'w') as f:
    f.write(content)

print("✅ app.py patché")

# ─────────────────────────────────────────────────────────────
# 3. Vérifications
# ─────────────────────────────────────────────────────────────
with open('app.py', 'r') as f:
    final = f.read()

print("\n" + "="*55)
checks = {
    'get_conn hybride': 'def get_conn' in final,
    'USE_POSTGRES': 'USE_POSTGRES' in final,
    'psycopg2 requirements': 'psycopg2' in open('requirements.txt').read(),
    'create_user PG': '%s,%s,%s,%s' in final,
    'verify_user PG': 'WHERE email=%s' in final,
    'log_login PG': 'NOW()' in final,
    'admin PG': 'RealDictCursor' in final,
}
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print()
print("COMMANDES SUIVANTES :")
print("  git add app.py requirements.txt")
print('  git commit -m "feat: migration Supabase PostgreSQL + SQLite fallback"')
print("  git push origin main")
print()
print("Sur Render → Environment, ajoutez :")
print("  DATABASE_URL = postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres")
print()
print("Sans DATABASE_URL → SQLite local (développement)")
print("Avec DATABASE_URL → Supabase PostgreSQL (production)")
