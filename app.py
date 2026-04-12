"""
app.py — SenGenoScope v1.0
Flask backend complet — sans clé API Claude requise
"""
import logging
from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for
try:
    from flask_wtf.csrf import CSRFProtect
    _has_csrf = True
except ImportError:
    _has_csrf = False

# CORS — autoriser seulement le domaine de production
from flask_cors import CORS
import os, secrets, logging
from pubmed import search_pubmed, fetch_articles
try:
    from pubmed import get_article_count
except ImportError:
    def get_article_count(query):
        try:
            import requests as _r
            r = _r.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db":"pubmed","term":query,"retmax":0,"retmode":"json"},timeout=8)
            return int(r.json()["esearchresult"].get("count",0))
        except: return 0
from gene_extractor import extract_genes_from_abstracts, extract_pathogenicity_context
from databases import search_clinvar, search_omim, search_cosmic, search_clingen, get_guidelines
from pdf_report import generate_pdf_report, generate_clinician_pdf
from genomic_tools import (parse_fasta, analyze_sequence, compare_sequences,
    predict_variant_impact, classify_acmg, calculate_hereditary_risk, get_all_syndromes)
from clinical_modules import (calculate_prs, get_prs_cancers, get_founder_mutations,
    get_populations, get_guidelines_comparison, get_gene_groups,
    get_penetrance_data, get_penetrance_genes, interpret_ngs_variant,
    parse_ngs_report, CONSEQUENCE_EXPLANATIONS)
# Claude AI optionnel — fonctionne sans clé API
try:
    from claude_ai import (analyze_uploaded_file, clinical_chat, synthesize_pubmed_results,
        generate_clinical_report, interpret_vcf_variant, check_api_status,
        pharmacogenomics_analysis)
    CLAUDE_AVAILABLE = True
except Exception:
    CLAUDE_AVAILABLE = False
    def analyze_uploaded_file(*a,**k): return {"error":"Claude AI non configuré (clé API manquante)"}
    def clinical_chat(*a,**k): return {"error":"Claude AI non configuré"}
    def synthesize_pubmed_results(*a,**k): return {"error":"Claude AI non configuré"}
    def generate_clinical_report(*a,**k): return {"error":"Claude AI non configuré"}
    def interpret_vcf_variant(*a,**k): return {"error":"Claude AI non configuré"}
    def check_api_status(): return {"available":False,"message":"Pas de clé API Claude configurée"}
    def pharmacogenomics_analysis(*a,**k): return {"error":"Claude AI non configuré"}
import requests as req
import io, csv, os, json, base64
import sqlite3, hashlib
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
if _has_csrf:
    csrf = CSRFProtect(app)
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False
CORS(app, origins=['https://clinical-genomic.onrender.com'])
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=30)

# ── Base de données utilisateurs SQLite ─────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)
            return conn, "pg"
        except Exception as e:
            logging.error(f"[DB] PostgreSQL indisponible: {e} — fallback SQLite")
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS login_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            email TEXT,
            ip TEXT,
            user_agent TEXT,
            login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS consultations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            clinician_id TEXT NOT NULL,
            clinician_name TEXT NOT NULL,
            clinician_specialty TEXT DEFAULT '',
            title TEXT DEFAULT '',
            messages TEXT NOT NULL,
            patient_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT DEFAULT '',
            date_naissance TEXT DEFAULT '',
            numero_dossier TEXT DEFAULT '',
            diagnostic TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            user_agent TEXT,
            login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            clinician_id TEXT NOT NULL,
            clinician_name TEXT NOT NULL,
            clinician_specialty TEXT DEFAULT '',
            title TEXT DEFAULT '',
            messages TEXT NOT NULL,
            patient_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT DEFAULT '',
            date_naissance TEXT DEFAULT '',
            numero_dossier TEXT DEFAULT '',
            diagnostic TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS patient_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type_analyse TEXT NOT NULL,
            titre TEXT DEFAULT '',
            resume TEXT DEFAULT '',
            resultat TEXT DEFAULT '',
            classification TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    conn.commit()
    conn.close()



# ══ MIGRATION DB ════════════════════════════════════════
def migrate_db():
    """Ajoute les colonnes/tables manquantes sans recréer."""
    try:
        conn, _db = get_conn()
        cur = conn.cursor()
        if _db == "pg":
            # Ajouter patient_id si manquant
            cur.execute("""
                ALTER TABLE consultations ADD COLUMN IF NOT EXISTS patient_id INTEGER DEFAULT NULL
            """)
            # Créer table patients si manquante
            cur.execute("""CREATE TABLE IF NOT EXISTS patients (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                nom TEXT NOT NULL,
                prenom TEXT DEFAULT '',
                date_naissance TEXT DEFAULT '',
                numero_dossier TEXT DEFAULT '',
                diagnostic TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        else:
            # SQLite — vérifier si colonne existe
            cur.execute("PRAGMA table_info(consultations)")
            cols = [r[1] for r in cur.fetchall()]
            if 'patient_id' not in cols:
                cur.execute("ALTER TABLE consultations ADD COLUMN patient_id INTEGER DEFAULT NULL")
            # Créer table patients si manquante
            cur.execute("""CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nom TEXT NOT NULL,
                prenom TEXT DEFAULT '',
                date_naissance TEXT DEFAULT '',
                numero_dossier TEXT DEFAULT '',
                diagnostic TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.commit()
        conn.close()
        logging.info("[DB] Migration OK")
    except Exception as e:
        logging.error(f"[DB] Migration erreur: {e}")

# ══ EMAIL ALERTES ══════════════════════════════════════════════════════════
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def db_execute(conn, db_type, sql, params=()):
    """Execute SQL compatible SQLite (?) et PostgreSQL (%s)."""
    cur = conn.cursor()
    if db_type == "pg":
        sql = sql.replace("?", "%s")
    cur.execute(sql, params)
    return cur

def db_fetchone(conn, db_type, sql, params=()):
    cur = db_execute(conn, db_type, sql, params)
    row = cur.fetchone()
    if row and db_type == "pg":
        # psycopg2 retourne des tuples, pas sqlite3.Row
        return row
    return row

def db_lastrowid(cur, conn, db_type):
    if db_type == "pg":
        cur.execute("SELECT LASTVAL()")
        return cur.fetchone()[0]
    return cur.lastrowid


def send_admin_email(subject, body):
    """Envoie un email d'alerte à l'admin."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    admin_email = os.environ.get("ADMIN_EMAIL", smtp_user)
    
    if not smtp_user or not smtp_pass:
        logging.info(f"[EMAIL] Non configuré — sujet: {subject}")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = admin_email
        msg["Subject"] = f"🧬 SenGenoScope — {subject}"
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, admin_email, msg.as_string())
        logging.info(f"[EMAIL] Envoyé: {subject}")
        return True
    except Exception as e:
        logging.error(f"[EMAIL] Erreur: {e}")
        return False

def log_login(user_id, name, email, ip, user_agent=''):
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
        logging.error(f"[LOGIN LOG ERROR] {e}")

def hash_password(pwd):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pwd, method='pbkdf2:sha256', salt_length=16)

def check_password(pwd, pwd_hash):
    from werkzeug.security import check_password_hash
    # Compatibilité avec anciens hash SHA-256
    if len(pwd_hash) == 64 and ':' not in pwd_hash:
        import hashlib
        return hashlib.sha256(pwd.encode()).hexdigest() == pwd_hash
    return check_password_hash(pwd_hash, pwd)

def create_user(name, institution, email, password):
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
        return False, err

def verify_user(email, password):
    conn, db_type = get_conn()
    if db_type == "pg":
        cur = conn.cursor()
        cur.execute("SELECT id, name, institution, password_hash FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
    else:
        row = conn.execute("SELECT id, name, institution, password_hash FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if row and check_password(password, row[3]):
        return (row[0], row[1], row[2])
    return None

init_db()
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max
_last_result = {}
_chat_history = []

ALLOWED_EXTENSIONS = {'vcf', 'csv', 'tsv', 'txt', 'json', 'pdf', 'fasta', 'fa', 'fastq'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Index ──────────────────────────────────────────────────────────────────────

@app.route('/manifest.json')
def manifest():
    return send_file('templates/manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return send_file('templates/sw.js', mimetype='application/javascript')




# ══ SECURITY HEADERS ═════════════════════════════════════════════════════
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=(self)'
    # CSP permissive pour permettre fonts Google et APIs externes
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://api.anthropic.com https://eutils.ncbi.nlm.nih.gov https://clinicaltrials.gov https://hpo.jax.org https://dgidb.org; "
        "img-src 'self' data:; "
        "frame-ancestors 'self';"
    )
    return response

# ══ RATE LIMITING MANUEL ═════════════════════════════════════════════════
from collections import defaultdict
import time as _time

_rate_store = defaultdict(list)

def check_rate_limit(key, max_calls=10, window=60):
    now = _time.time()
    calls = _rate_store[key]
    _rate_store[key] = [t for t in calls if now - t < window]
    if len(_rate_store[key]) >= max_calls:
        return False
    _rate_store[key].append(now)
    return True

# ══ AUTHENTIFICATION ══════════════════════════════════════════════════════

def login_required(f):
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
            ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
            if not check_rate_limit(f"login_{ip}", max_calls=5, window=60):
                error = "⏱️ Too many attempts. Please wait 1 minute."
            else:
                user = verify_user(email, password)
            if user:
                session["authenticated"] = True
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_institution"] = user[2]
                session.permanent = True
                ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
                log_login(user[0], user[1], email, ip)
                return redirect(url_for("app_main"))
            else:
                error = "❌ Incorrect email or password."

    return render_template("login.html", error=error, reg_error=reg_error, reg_success=reg_success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing_page"))


# ══ ADMIN DASHBOARD ══════════════════════════════════════════════════════

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/")
def landing_page():
    return render_template("landing.html")

@app.route("/app")
@login_required
def app_main():
    return render_template("index.html")

# ── HPO ────────────────────────────────────────────────────────────────────────
@app.route("/hpo_search")
def hpo_search():
    term = request.args.get("term","").strip()
    if not term: return jsonify([])
    try:
        r = req.get(f"https://hpo.jax.org/api/hpo/search/?q={req.utils.quote(term)}&max=15&offset=0&category=terms", timeout=8)
        terms = r.json().get("terms",[])
        return jsonify([{"id":t.get("id",""),"name":t.get("name",""),"definition":t.get("definition","")} for t in terms])
    except: return jsonify([])

# ── Article count ──────────────────────────────────────────────────────────────
@app.route("/article_count")
def article_count():
    query = request.args.get("query","").strip()
    if not query: return jsonify({"count":0})
    return jsonify({"count": get_article_count(query)})

# ── Gene info NCBI ─────────────────────────────────────────────────────────────
@app.route("/gene_info/<gene>")
def gene_info(gene):
    try:
        r = req.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term={gene}[gene]+AND+Homo+sapiens[orgn]&retmax=1&retmode=json", timeout=8)
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return jsonify({"error":"Gene not found"})
        r2 = req.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&id={ids[0]}&retmode=json", timeout=8)
        d = r2.json().get("result",{}).get(ids[0],{})
        return jsonify({"name":d.get("name",""),"description":d.get("description",""),"chromosome":d.get("chromosome",""),"location":d.get("maplocation",""),"summary":d.get("summary",""),"type":d.get("type_of_gene",""),"aliases":d.get("otheraliases",""),"ncbi_id":ids[0]})
    except Exception as e: return jsonify({"error":str(e)})

# ── Variant types ClinVar ──────────────────────────────────────────────────────
@app.route("/variant_types/<gene>")
def variant_types(gene):
    try:
        r = req.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term={gene}[gene]&retmax=500&retmode=json", timeout=12)
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return jsonify({"gene":gene,"types":{},"pathogenicity":{},"total":0})
        types,patho={},{}
        for i in range(0,min(len(ids),300),80):
            batch=ids[i:i+80]
            r2 = req.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={','.join(batch)}&retmode=json", timeout=15)
            result = r2.json().get("result",{})
            for uid,item in result.items():
                if uid=="uids": continue
                vt = item.get("variation_type","Unknown") or "Unknown"
                types[vt] = types.get(vt,0)+1
                cs = item.get("clinical_significance",{})
                sig = cs.get("description","Unknown") if isinstance(cs,dict) else str(cs)
                patho[sig] = patho.get(sig,0)+1
        return jsonify({"gene":gene.upper(),"types":types,"pathogenicity":patho,"total":len(ids)})
    except Exception as e: return jsonify({"gene":gene.upper(),"types":{},"pathogenicity":{},"error":str(e)})

# ── gnomAD ─────────────────────────────────────────────────────────────────────
@app.route("/gnomad/<gene>")
def gnomad_data(gene):
    try:
        query = '{ gene(gene_symbol: "%s", reference_genome: GRCh38) { variants(dataset: gnomad_r4) { variant_id consequence hgvsc hgvsp genome { af populations { id af } } } } }' % gene.upper()
        r = req.post("https://gnomad.broadinstitute.org/api", json={"query":query}, timeout=25)
        variants = r.json().get("data",{}).get("gene",{}).get("variants",[])
        simplified=[{"id":v.get("variant_id",""),"consequence":v.get("consequence",""),"hgvsc":v.get("hgvsc",""),"hgvsp":v.get("hgvsp",""),"af_global":round((v.get("genome") or {}).get("af",0) or 0,8),"populations":{p["id"]:round(p.get("af") or 0,8) for p in ((v.get("genome") or {}).get("populations",[]) or []) if p.get("id")}} for v in variants[:50]]
        return jsonify({"gene":gene.upper(),"variants":simplified,"total":len(variants)})
    except Exception as e: return jsonify({"gene":gene.upper(),"variants":[],"error":str(e)})

# ── Clinical trials ────────────────────────────────────────────────────────────
@app.route("/clinical_trials/<gene>")
def clinical_trials(gene):
    try:
        r = req.get(f"https://clinicaltrials.gov/api/v2/studies?query.term={gene}+cancer&pageSize=12&format=json", timeout=12)
        studies = r.json().get("studies",[])
        results=[]
        for s in studies:
            proto=s.get("protocolSection",{}); ident=proto.get("identificationModule",{}); status=proto.get("statusModule",{}); desc=proto.get("descriptionModule",{})
            results.append({"nct_id":ident.get("nctId",""),"title":ident.get("briefTitle",""),"status":status.get("overallStatus",""),"brief_summary":(desc.get("briefSummary","")[:250] if desc.get("briefSummary") else ""),"url":f"https://clinicaltrials.gov/study/{ident.get('nctId','')}"})
        return jsonify({"gene":gene.upper(),"trials":results})
    except Exception as e: return jsonify({"gene":gene.upper(),"trials":[],"error":str(e)})

# ── Drug interactions ──────────────────────────────────────────────────────────
@app.route("/drug_interactions/<gene>")
def drug_interactions(gene):
    try:
        query='{ genes(names: ["%s"]) { nodes { name interactions { drug { name } interactionTypes { type } publications { pmid } } } } }' % gene.upper()
        r = req.post("https://dgidb.org/api/graphql", json={"query":query}, timeout=15)
        nodes=r.json().get("data",{}).get("genes",{}).get("nodes",[])
        interactions=[]
        if nodes:
            for inter in nodes[0].get("interactions",[])[:20]:
                drug=inter.get("drug",{}).get("name",""); types=[t.get("type","") for t in inter.get("interactionTypes",[])]
                if drug: interactions.append({"drug":drug,"types":types,"pmids":[p.get("pmid","") for p in inter.get("publications",[])[:2]]})
        return jsonify({"gene":gene.upper(),"interactions":interactions})
    except Exception as e: return jsonify({"gene":gene.upper(),"interactions":[],"error":str(e)})

# ── VEP Prediction ────────────────────────────────────────────────────────────
@app.route("/predict_variant", methods=["POST"])
def predict_variant():
    data = request.get_json()
    chrom=str(data.get("chrom","")).replace("chr",""); pos=data.get("pos"); ref=str(data.get("ref","")).upper(); alt=str(data.get("alt","")).upper()
    assembly=data.get("assembly","GRCh38")
    if not all([chrom,pos,ref,alt]): return jsonify({"error":"Paramètres manquants"}),400
    return jsonify(predict_variant_impact(chrom,int(pos),ref,alt,assembly))

# ── Sequence analysis ──────────────────────────────────────────────────────────
@app.route("/analyze_sequence", methods=["POST"])
def analyze_sequence_ep():
    data=request.get_json(); fasta=data.get("sequence","").strip(); seq2=data.get("sequence2","").strip()
    if not fasta: return jsonify({"error":"Séquence manquante"}),400
    parsed=parse_fasta(fasta); seq=parsed["sequence"]
    if len(seq)<3: return jsonify({"error":"Séquence trop courte"}),400
    result=analyze_sequence(seq); result["header"]=parsed["header"]; result["sequence_preview"]=seq[:80]+("..." if len(seq)>80 else "")
    if seq2: parsed2=parse_fasta(seq2); result["comparison"]=compare_sequences(seq,parsed2["sequence"])
    return jsonify(result)

# ── ACMG ──────────────────────────────────────────────────────────────────────
@app.route("/classify_acmg", methods=["POST"])
def classify_acmg_ep():
    data=request.get_json(); criteria=data.get("criteria",{})
    if not criteria: return jsonify({"error":"Critères manquants"}),400
    return jsonify(classify_acmg(criteria))

# ── Hereditary risk ────────────────────────────────────────────────────────────
@app.route("/hereditary_risk", methods=["POST"])
def hereditary_risk():
    data=request.get_json(); syndrome=data.get("syndrome",""); criteria=data.get("criteria",[])
    if not syndrome: return jsonify({"error":"Syndrome manquant"}),400
    return jsonify(calculate_hereditary_risk(syndrome,criteria))

@app.route("/syndromes")
def get_syndromes():
    return jsonify(get_all_syndromes())

# ── PRS ────────────────────────────────────────────────────────────────────────
@app.route("/prs_cancers")
def prs_cancers():
    return jsonify(get_prs_cancers())

@app.route("/calculate_prs", methods=["POST"])
def calculate_prs_ep():
    data=request.get_json(); cancer_type=data.get("cancer_type",""); risk_alleles=data.get("risk_alleles",{})
    if not cancer_type: return jsonify({"error":"Cancer type manquant"}),400
    return jsonify(calculate_prs(cancer_type,risk_alleles))

# ── Founder mutations ──────────────────────────────────────────────────────────
@app.route("/founder_mutations")
def founder_mutations():
    population=request.args.get("population","")
    return jsonify(get_founder_mutations(population or None))

@app.route("/populations")
def populations():
    return jsonify(get_populations())

# ── Guidelines ─────────────────────────────────────────────────────────────────
@app.route("/guidelines_comparison")
def guidelines_comparison():
    gene_group=request.args.get("gene_group","")
    return jsonify(get_guidelines_comparison(gene_group or None))

@app.route("/gene_groups")
def gene_groups():
    return jsonify(get_gene_groups())

# ── Penetrance ─────────────────────────────────────────────────────────────────
@app.route("/penetrance")
def penetrance():
    gene=request.args.get("gene","")
    data=get_penetrance_data(gene if gene else None)
    if gene and isinstance(data,dict) and gene.upper() in data:
        return jsonify(data[gene.upper()])
    return jsonify(data)

@app.route("/penetrance_genes")
def penetrance_genes():
    return jsonify(get_penetrance_genes())

# ── NGS interpreter ────────────────────────────────────────────────────────────
@app.route("/interpret_variant", methods=["POST"])
def interpret_variant_ngs():
    data=request.get_json()
    return jsonify(interpret_ngs_variant(consequence=data.get("consequence",""),gene=data.get("gene",""),hgvsc=data.get("hgvsc",""),hgvsp=data.get("hgvsp",""),af_gnomad=data.get("af_gnomad"),acmg_classification=data.get("acmg_classification","")))

@app.route("/parse_ngs_report", methods=["POST"])
def parse_ngs_report_ep():
    data=request.get_json(); text=data.get("text","")
    if not text: return jsonify({"error":"Texte manquant"}),400
    variants=parse_ngs_report(text)
    return jsonify({"variants":variants,"count":len(variants)})

@app.route("/consequence_types")
def consequence_types():
    return jsonify(list(CONSEQUENCE_EXPLANATIONS.keys()))

# ── Main analyze ──────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    ip = request.remote_addr
    if not check_rate_limit(f"analyze_{ip}", max_calls=15, window=60):
        return jsonify({"error": "Rate limit exceeded. Max 15 requests/minute."}), 429
    global _last_result
    data=request.get_json()
    query=data.get("query","").strip(); max_results=int(data.get("max_results",0)); gene_filter=data.get("gene_filter","").strip().upper(); hpo_term=data.get("hpo_term","").strip()
    sort_by=data.get("sort_by","relevance")
    if not query and not hpo_term: return jsonify({"error":"Veuillez entrer un terme."}),400
    search_query=f"{query} {hpo_term}".strip() if hpo_term else query

    pmids=search_pubmed(search_query,max_results,sort=sort_by)
    if not pmids: return jsonify({"error":"Aucun article trouvé sur PubMed."}),404
    articles=fetch_articles(pmids)
    if not articles: return jsonify({"error":"Aucun abstract disponible."}),404

    gene_data=extract_genes_from_abstracts(articles)
    patho_contexts=[]
    for art in articles[:10]:
        ctx=extract_pathogenicity_context(art["abstract"])
        if ctx: patho_contexts.append({"pmid":art["pmid"],"title":art["title"],"sentences":ctx})

    cv_query=gene_filter if gene_filter else search_query
    clinvar=search_clinvar(cv_query,max_results=15)
    _last_result={"query":search_query,"articles":articles,"gene_data":gene_data,"clinvar":clinvar}

    return jsonify({
        "query":search_query,"articles_count":len(articles),"total_pmids":len(pmids),
        "articles":articles,"gene_frequency":gene_data["frequency"],
        "gene_sources":gene_data["sources"],"patho_contexts":patho_contexts,
        "clinvar":clinvar,"omim_links":search_omim(search_query),
        "cosmic_links":search_cosmic(gene_filter or search_query.split()[0]),
        "clingen_links":search_clingen(gene_filter or search_query.split()[0]),
        "guidelines":get_guidelines(),
        "mesh_summary": _get_mesh_summary(articles),
        "pub_type_summary": _get_pub_types(articles),
        "year_distribution": _get_year_dist(articles),
    })

# ══════════════════════════════════════════════════════════════════════════════
# ── NOUVEAUX ENDPOINTS CLAUDE AI ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# ── Statut API Claude ─────────────────────────────────────────────────────────
@app.route("/ai/status")
def ai_status():
    return jsonify(check_api_status())

# ── Upload et analyse de fichier par Claude AI ────────────────────────────────
@app.route("/ai/upload", methods=["POST"])
def ai_upload():
    """
    Upload d'un fichier génomique (VCF, CSV, TXT, PDF, FASTA)
    et analyse intelligente par Claude AI.
    """
    user_api_key = request.headers.get("X-User-Api-Key", "").strip()
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400

    file = request.files['file']
    question = request.form.get('question', '')

    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Format non supporté. Formats acceptés: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    try:
        file_content = file.read()

        if ext == 'pdf':
            # PDF → base64
            b64_content = base64.b64encode(file_content).decode('utf-8')
            result = analyze_uploaded_file(filename, b64_content, "pdf_b64", question, user_api_key=user_api_key)
        else:
            # Fichier texte
            try:
                content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content = file_content.decode('latin-1', errors='replace')

            result = analyze_uploaded_file(filename, content, ext, question, user_api_key=user_api_key)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ── Chat médical Claude AI ────────────────────────────────────────────────────
@app.route("/ai/chat", methods=["POST"])
def ai_chat():
    ip = request.remote_addr
    if not check_rate_limit(f"ai_chat_{ip}", max_calls=20, window=60):
        return jsonify({"error": "Rate limit exceeded. Max 20 requests/minute."}), 429
    """Chat médical spécialisé avec Claude AI."""
    global _chat_history
    data = request.get_json()
    message = data.get("message", "").strip()
    reset = data.get("reset", False)

    if not message:
        return jsonify({"error": "Message vide"}), 400

    if reset:
        _chat_history = []

    # Contexte de session
    context = {}
    if _last_result:
        context["last_query"] = _last_result.get("query", "")
        context["genes_found"] = list(_last_result.get("gene_data", {}).get("frequency", {}).keys())[:10]
        context["clinvar_variants"] = _last_result.get("clinvar", [])

    user_api_key = request.headers.get('X-User-Api-Key', '').strip()
    result = clinical_chat(_chat_history, message, context, user_api_key=user_api_key)

    if result["success"]:
        _chat_history.append({"role": "user", "content": message})
        _chat_history.append({"role": "assistant", "content": result["response"]})
        # Limiter l'historique
        if len(_chat_history) > 40:
            _chat_history = _chat_history[-40:]

    return jsonify(result)

# ── Synthèse PubMed par Claude AI ────────────────────────────────────────────
@app.route("/ai/synthesize", methods=["POST"])
def ai_synthesize():
    """Synthèse intelligente des résultats PubMed par Claude AI."""
    if not _last_result:
        return jsonify({"error": "Effectuez d'abord une recherche PubMed"}), 400
    user_api_key = request.headers.get("X-User-Api-Key", "").strip()
    result = synthesize_pubmed_results(
        query=_last_result.get("query", ""),
        articles=_last_result.get("articles", []),
        genes=list(_last_result.get("gene_data", {}).get("frequency", {}).keys()),
        user_api_key=user_api_key
    )
    return jsonify(result)

# ── Rapport clinique ACMG par Claude AI ──────────────────────────────────────
@app.route("/ai/clinical_report", methods=["POST"])
def ai_clinical_report():
    """Génère un rapport clinique ACMG structuré par Claude AI."""
    data = request.get_json()
    user_api_key = request.headers.get("X-User-Api-Key", "").strip()
    variant_data = data.get("variant_data", {})
    patient_context = data.get("patient_context", "")

    if not variant_data:
        return jsonify({"error": "Données du variant manquantes"}), 400

    result = generate_clinical_report(variant_data, patient_context)
    return jsonify(result)

# ── Interprétation VCF par Claude AI ─────────────────────────────────────────
@app.route("/ai/interpret_variant", methods=["POST"])
def ai_interpret_variant():
    """Interprétation ACMG d'un variant par Claude AI."""
    data = request.get_json()
    chrom = data.get("chrom", "")
    pos = data.get("pos", "")
    ref = data.get("ref", "")
    alt = data.get("alt", "")
    gene = data.get("gene", "")
    existing = data.get("existing_data", {})

    if not all([chrom, pos, ref, alt]):
        return jsonify({"error": "Paramètres manquants: chrom, pos, ref, alt requis"}), 400

    result = interpret_vcf_variant(chrom, str(pos), ref, alt, gene, existing)
    return jsonify(result)

# ── Réinitialiser chat ────────────────────────────────────────────────────────
@app.route("/ai/chat/reset", methods=["POST"])
def ai_chat_reset():
    global _chat_history
    _chat_history = []
    return jsonify({"success": True, "message": "Historique effacé"})

# ══════════════════════════════════════════════════════════════════════════════
# ── HELPERS ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _get_mesh_summary(articles):
    mesh={}
    for a in articles:
        for m in a.get("mesh_terms",[]):
            mesh[m]=mesh.get(m,0)+1
    return dict(sorted(mesh.items(),key=lambda x:-x[1])[:15])

def _get_pub_types(articles):
    types={}
    for a in articles:
        for pt in a.get("pub_types",[]):
            types[pt]=types.get(pt,0)+1
    return dict(sorted(types.items(),key=lambda x:-x[1])[:10])

def _get_year_dist(articles):
    years={}
    for a in articles:
        y=a.get("year","")
        if y and y.isdigit():
            years[y]=years.get(y,0)+1
    return dict(sorted(years.items()))

# ── Export PDF ─────────────────────────────────────────────────────────────────
@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    if not _last_result: return jsonify({"error":"Aucune analyse."}),400
    pdf_bytes=generate_pdf_report(query=_last_result.get("query",""),articles=_last_result.get("articles",[]),gene_data=_last_result.get("gene_data",{}),clinvar_results=_last_result.get("clinvar",[]))
    return send_file(io.BytesIO(pdf_bytes),mimetype="application/pdf",as_attachment=True,download_name="rapport_sengenoscope.pdf")

# ── Export CSV ─────────────────────────────────────────────────────────────────
@app.route("/export_csv", methods=["POST"])
def export_csv():
    if not _last_result: return jsonify({"error":"Aucune analyse."}),400
    output=io.StringIO(); w=csv.writer(output)
    w.writerow(["SenGenoScope v6 — Moustapha Gassama"])
    w.writerow(["Requête:",_last_result.get("query","")]); w.writerow([])
    w.writerow(["=== GÈNES IDENTIFIÉS ==="]);w.writerow(["Rang","Gène","Fréquence","Sources PMIDs"])
    for i,(g,c) in enumerate((_last_result.get("gene_data",{}).get("frequency",{})).items(),1):
        srcs="; ".join([s["pmid"] for s in _last_result.get("gene_data",{}).get("sources",{}).get(g,[])])
        w.writerow([i,g,c,srcs])
    w.writerow([]);w.writerow(["=== VARIANTS CLINVAR ==="]);w.writerow(["Gène","Titre","Signification","URL"])
    for v in _last_result.get("clinvar",[]):
        if "error" not in v: w.writerow([v.get("gene",""),v.get("title",""),v.get("significance",""),v.get("url","")])
    w.writerow([]);w.writerow(["=== ARTICLES PUBMED ==="]);w.writerow(["PMID","Titre","Auteurs","Journal","Année","DOI","MeSH","URL"])
    for a in _last_result.get("articles",[]):
        w.writerow([a.get("pmid",""),a.get("title",""),a.get("authors",""),a.get("journal",""),a.get("year",""),a.get("doi",""),"; ".join(a.get("mesh_terms",[])),a.get("url","")])
    output.seek(0)
    return Response(output.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=rapport_sengenoscope.csv"})


# ══════════════════════════════════════════════════════════════════════════════
# ── MODULES AVANCÉS (advanced_modules.py) ────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
from advanced_modules import (
    calculate_manchester_score, calculate_tyrer_cuzick,
    search_clinvar_by_hgvs, hpo_to_genes, parse_vcf_content,
    generate_genetic_counseling_letter, compare_two_variants,
    record_search, record_vep, record_acmg, record_risk,
    get_stats, get_lollipop_data
)

# ── Manchester / Tyrer-Cuzick ─────────────────────────────────────────────────
@app.route("/manchester", methods=["POST"])
def manchester():
    data = request.get_json()
    family = data.get("family_history", {})
    return jsonify(calculate_manchester_score(family))

@app.route("/tyrer_cuzick", methods=["POST"])
def tyrer_cuzick():
    data = request.get_json()
    return jsonify(calculate_tyrer_cuzick(data))

# ── ClinVar par HGVS ──────────────────────────────────────────────────────────
@app.route("/clinvar_hgvs", methods=["POST"])
def clinvar_hgvs():
    data = request.get_json()
    hgvs = data.get("hgvs", "").strip()
    if not hgvs:
        return jsonify({"error": "HGVS manquant"}), 400
    return jsonify(search_clinvar_by_hgvs(hgvs))

# ── HPO → Gènes candidats ─────────────────────────────────────────────────────
@app.route("/hpo_genes", methods=["POST"])
def hpo_genes():
    data = request.get_json()
    hpo_ids = data.get("hpo_ids", [])
    if not hpo_ids:
        return jsonify({"error": "HPO IDs manquants"}), 400
    return jsonify(hpo_to_genes(hpo_ids))

# ── Parse VCF (sans upload — texte collé) ────────────────────────────────────
@app.route("/parse_vcf", methods=["POST"])
def parse_vcf():
    data = request.get_json()
    vcf_text = data.get("vcf_text", "").strip()
    if not vcf_text:
        return jsonify({"error": "Contenu VCF manquant"}), 400
    return jsonify(parse_vcf_content(vcf_text))

# ── Lettre de conseil génétique ───────────────────────────────────────────────
@app.route("/genetic_letter", methods=["POST"])
def genetic_letter():
    data = request.get_json()
    return jsonify(generate_genetic_counseling_letter(data))

# ── Comparateur de variants ───────────────────────────────────────────────────
@app.route("/compare_variants", methods=["POST"])
def compare_variants():
    data = request.get_json()
    v1 = data.get("variant1", {})
    v2 = data.get("variant2", {})
    if not v1 or not v2:
        return jsonify({"error": "Deux variants requis"}), 400
    return jsonify(compare_two_variants(v1, v2))

# ── Statistiques dashboard ────────────────────────────────────────────────────
@app.route("/me")
@login_required
def me():
    uid = session.get('user_id')
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        cur.execute(f"SELECT name, institution FROM users WHERE id={ph}", (uid,))
        r = cur.fetchone()
        conn.close()
        if r:
            session["user_name"] = r[0] or ""
            session["user_institution"] = r[1] or ""
        return jsonify({
            "name": session.get("user_name", ""),
            "institution": session.get("user_institution", "")
        })
    except Exception as e:
        conn.close()
        return jsonify({
            "name": session.get("user_name", ""),
            "institution": session.get("user_institution", "")
        })

@app.route("/profile", methods=["GET", "PUT"])
@login_required
def profile():
    uid = session['user_id']
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        if request.method == "GET":
            cur.execute(f"SELECT name, institution, email FROM users WHERE id={ph}", (uid,))
            r = cur.fetchone()
            conn.close()
            if not r:
                return jsonify({"name": "", "institution": "", "email": ""})
            return jsonify({"name": r[0] or "", "institution": r[1] or "", "email": r[2] or ""})
        else:
            data = request.json or {}
            name = data.get("name", "").strip()
            institution = data.get("institution", "").strip()
            if not name:
                return jsonify({"success": False, "error": "Nom requis"})
            cur.execute(f"UPDATE users SET name={ph}, institution={ph} WHERE id={ph}", (name, institution, uid))
            conn.commit()
            conn.close()
            session["user_name"] = name
            session["user_institution"] = institution
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/stats")
def stats():
    record_search("", [])  # ping stats
    return jsonify(get_stats())

# ── Lollipop data pour visualisation ─────────────────────────────────────────
@app.route("/lollipop/<gene>")
def lollipop(gene):
    return jsonify(get_lollipop_data(gene))

# ── Literature lookup (PMID / DOI) ────────────────────────────────────────────
@app.route("/lit_lookup")
def lit_lookup():
    q = req.utils.quote(request.args.get("q","").strip()) if hasattr(req,'utils') else request.args.get("q","").strip()
    raw = request.args.get("q","").strip()
    if not raw: return jsonify({"error":"Requête vide"})
    try:
        import re
        # DOI detection
        doi_match = re.match(r'10\.\d{4,}[/\-.].+', raw)
        pmid_match = re.match(r'^\d{6,9}$', raw.strip())
        pmcid_match = re.match(r'^PMC\d+$', raw.strip(), re.IGNORECASE)

        if doi_match:
            # CrossRef DOI lookup
            r1 = req.get(f"https://api.crossref.org/works/{raw}", timeout=10, headers={"User-Agent":"SenGenoScope/1.0"})
            if r1.status_code==200:
                msg = r1.json().get("message",{})
                title = msg.get("title",[""])[0]
                authors = ", ".join([f"{a.get('given','')} {a.get('family','')}".strip() for a in msg.get("author",[])][:3])
                journal = msg.get("container-title",[""])[0]
                year = str(msg.get("published",{}).get("date-parts",[[""]])[0][0])
                abstract = msg.get("abstract","")
                # Clean HTML tags from abstract
                abstract = re.sub(r'<[^>]+>', '', abstract)
                return jsonify({"title":title,"authors":authors,"journal":journal,"year":year,"doi":raw,"abstract":abstract})
            return jsonify({"error":f"DOI non trouvé: {raw}"})

        elif pmid_match or pmcid_match:
            pmid = raw
            r1 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db":"pubmed","id":pmid,"retmode":"json"}, timeout=10)
            j1 = r1.json().get("result",{}).get(pmid,{})
            title = j1.get("title","")
            authors = ", ".join([a.get("name","") for a in j1.get("authors",[])[:3]])
            journal = j1.get("source","")
            year = j1.get("pubdate","")[:4]
            # Fetch abstract
            r2 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params={"db":"pubmed","id":pmid,"rettype":"abstract","retmode":"text"}, timeout=10)
            abstract = r2.text[:2000] if r2.status_code==200 else ""
            return jsonify({"title":title,"authors":authors,"journal":journal,"year":year,"pmid":pmid,"abstract":abstract})

        else:
            return jsonify({"error":"Format non reconnu. Utilisez un PMID (ex: 28228671), un DOI (ex: 10.1038/...) ou un PMC ID."})
    except Exception as e:
        return jsonify({"error":str(e)})

# ── Literature search (PubMed / Europe PMC / CrossRef) ───────────────────────
@app.route("/lit_search")
def lit_search():
    q = request.args.get("q","").strip()
    source = request.args.get("source","pubmed")
    max_res = int(request.args.get("max","10"))
    if not q: return jsonify({"error":"Requête vide"})
    try:
        articles = []
        if source == "pubmed":
            r1 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db":"pubmed","term":q,"retmax":max_res,"retmode":"json"}, timeout=10)
            ids = r1.json().get("esearchresult",{}).get("idlist",[])
            if ids:
                r2 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                    params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, timeout=10)
                res = r2.json().get("result",{})
                for pid in ids:
                    a = res.get(pid,{})
                    articles.append({
                        "title": a.get("title",""),
                        "authors": ", ".join([x.get("name","") for x in a.get("authors",[])[:3]]),
                        "journal": a.get("source",""),
                        "year": a.get("pubdate","")[:4],
                        "pmid": pid,
                        "abstract": ""
                    })
        elif source == "europepmc":
            r1 = req.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query":q,"resultType":"core","pageSize":max_res,"format":"json"}, timeout=10)
            for a in r1.json().get("resultList",{}).get("result",[]):
                articles.append({
                    "title": a.get("title",""),
                    "authors": a.get("authorString","")[:100],
                    "journal": a.get("journalTitle",""),
                    "year": str(a.get("pubYear","")),
                    "pmid": a.get("pmid",""),
                    "doi": a.get("doi",""),
                    "abstract": a.get("abstractText","")[:500] if a.get("abstractText") else ""
                })
        elif source == "crossref":
            r1 = req.get("https://api.crossref.org/works",
                params={"query":q,"rows":max_res}, timeout=10, headers={"User-Agent":"SenGenoScope/1.0"})
            for a in r1.json().get("message",{}).get("items",[]):
                articles.append({
                    "title": a.get("title",[""])[0],
                    "authors": ", ".join([f"{x.get('given','')} {x.get('family','')}".strip() for x in a.get("author",[])[:3]]),
                    "journal": a.get("container-title",[""])[0],
                    "year": str(a.get("published",{}).get("date-parts",[[""]])[0][0]),
                    "doi": a.get("DOI",""),
                    "abstract": ""
                })
        return jsonify({"articles": articles})
    except Exception as e:
        return jsonify({"error": str(e)})

# ── Literature extract variants/genes from text ───────────────────────────────
@app.route("/lit_extract", methods=["POST"])
def lit_extract():
    import re
    data = request.get_json()
    text = data.get("text","")
    source = data.get("source","")
    if not text: return jsonify({"error":"Texte vide"})
    # Gene pattern
    gene_pat = r'\b([A-Z][A-Z0-9]{1,7}(?:1|2)?)\b'
    known_genes = {"BRCA1","BRCA2","TP53","MLH1","MSH2","MSH6","PMS2","APC","RB1","PTEN",
                   "VHL","NF1","NF2","RET","MEN1","STK11","CDH1","PALB2","CHEK2","ATM",
                   "EGFR","KRAS","BRAF","ALK","ERBB2","MET","PIK3CA","NRAS","IDH1","IDH2",
                   "FLT3","NPM1","RUNX1","WT1","CDKN2A","SMAD4","NOTCH1","JAK2","BCR"}
    # Variant patterns
    var_pat = r'c\.[A-Za-z0-9_>+\-*]{3,30}|p\.[A-Za-z]{1,3}\d+[A-Za-z*?]{0,10}|g\.\d+[A-Za-z>]{2,10}'
    # Disease patterns  
    dis_pat = r'(?:cancer|carcinoma|syndrome|tumor|tumour|mutation|variant|disease|disorder|Lynch|BRCA|Li-Fraumeni|Cowden|FAP|MEN)[^\.\,]{0,40}'
    # ACMG classifications
    acmg_pat = r'(?:Pathogenic|Likely pathogenic|Benign|Likely benign|VUS|Variant of uncertain significance|Class [1-5])'

    genes = list(set(g for g in re.findall(gene_pat, text) if g in known_genes))
    variants = list(set(re.findall(var_pat, text)))[:10]
    diseases = list(set(re.findall(dis_pat, text, re.IGNORECASE)))[:5]
    classifications = list(set(re.findall(acmg_pat, text, re.IGNORECASE)))[:5]

    return jsonify({
        "genes": genes,
        "variants": variants,
        "diseases": [d.strip() for d in diseases],
        "classifications": classifications,
        "source": source
    })

# ── Pharmacogénomique par Claude AI ──────────────────────────────────────────
@app.route("/ai/pharmacogenomics", methods=["POST"])
def ai_pharmacogenomics():
    """Analyse pharmacogénomique d'un gène/variant par Claude AI."""
    data = request.get_json()
    user_api_key = request.headers.get("X-User-Api-Key", "").strip()
    gene = data.get("gene", "").strip()
    variant = data.get("variant", "").strip()
    drug = data.get("drug", "").strip()
    if not gene:
        return jsonify({"error": "Gène requis"}), 400
    result = pharmacogenomics_analysis(gene, variant, drug, user_api_key=user_api_key)
    return jsonify(result)


@app.route("/clinvar_lookup")
def clinvar_lookup():
    q = request.args.get("q","").strip()
    if not q: return jsonify({"error":"Requete vide"})
    try:
        r1 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db":"clinvar","term":q,"retmax":1,"retmode":"json"}, timeout=10)
        ids = r1.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return jsonify({"error":f"Aucun resultat pour: {q}"})
        uid = ids[0]
        r2 = req.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db":"clinvar","id":uid,"retmode":"json"}, timeout=10)
        item = r2.json().get("result",{}).get(uid,{})
        cs = item.get("clinical_significance",{})
        sig = cs.get("description","") if isinstance(cs,dict) else str(cs)
        return jsonify({"clinvar_id":uid,"title":item.get("title",""),"gene":item.get("gene_sort",""),"hgvsc":"","hgvsp":"","af_gnomad":None,"classification":sig,"clinvar_url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── Test/Debug route ─────────────────────────────────────────────────────────

# ══ CLINICIENS VIRTUELS ═══════════════════════════════════════════════════

@app.route("/clinicians/test", methods=["GET"])
def test_clinicians():
    try:
        from virtual_clinicians import get_all_clinicians, CLINICIANS
        return jsonify({"ok": True, "count": len(CLINICIANS), "ids": [c["id"] for c in CLINICIANS]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/clinicians/chat", methods=["POST"])
def clinician_chat():
    ip = request.remote_addr
    if not check_rate_limit(f"clinician_{ip}", max_calls=10, window=60):
        return jsonify({"error": "Rate limit exceeded. Max 10 requests/minute."}), 429
    from virtual_clinicians import get_clinician_response
    data = request.json or {}
    clinician_id = data.get("clinician_id", "")
    messages     = data.get("messages", [])
    user_key     = request.headers.get("X-User-Api-Key", "")
    if not clinician_id or not messages:
        return jsonify({"success": False, "error": "clinician_id et messages requis"}), 400
    result = get_clinician_response(clinician_id, messages, api_key=user_key or None)
    return jsonify(result)

@app.route("/test")
def test_route():
    import sys, platform
    return jsonify({
        "status": "ok",
        "python": sys.version,
        "platform": platform.platform(),
        "flask": "running",
        "modules": {
            "pubmed": True,
            "genomic_tools": True,
            "clinical_modules": True,
            "advanced_modules": True
        },
        "message": "SenGenoScope v1.0 fonctionne correctement"
    })


# ══ ADMIN LOGS (protégé par mot de passe) ═══════════════════════════════════
import os as _os
ADMIN_PASSWORD = _os.environ.get("ADMIN_PASSWORD", "SenGeno2026!")

@app.route("/admin/logs", methods=["GET", "POST"])
def admin_logs():
    pwd = request.args.get("pwd", "") or request.form.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return """<form style='font-family:monospace;padding:20px' method='GET'>
            <h2>🔐 Admin Access</h2>
            <input type='password' name='pwd' placeholder='Mot de passe admin' style='padding:8px;width:300px'>
            <button type='submit' style='padding:8px 16px;margin-left:8px'>Entrer</button>
        </form>""", 401
    
    import sqlite3
    conn = sqlite3.connect(DB_PATH, timeout=30)
    
    logs = conn.execute("""
        SELECT login_at, name, email, ip, user_agent 
        FROM login_logs 
        WHERE login_at >= datetime('now', '-48 hours')
        ORDER BY login_at DESC
    """).fetchall()
    
    logs_all = conn.execute("""
        SELECT COUNT(*) FROM login_logs
    """).fetchone()[0]
    
    # Stats par utilisateur sur 48h
    stats_48h = conn.execute("""
        SELECT name, email, COUNT(*) as nb_connexions, MAX(login_at) as derniere
        FROM login_logs 
        WHERE login_at >= datetime('now', '-48 hours')
        GROUP BY email
        ORDER BY nb_connexions DESC
    """).fetchall()
    
    users = conn.execute("""
        SELECT name, email, institution, created_at, last_login 
        FROM users ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    
    rows_stats = "".join(f"""<tr>
        <td><b>{s[0]}</b></td><td>{s[1]}</td>
        <td style='text-align:center'><b>{s[2]}</b></td><td>{s[3]}</td>
    </tr>""" for s in stats_48h)
    rows_logs = "".join(f"""<tr>
        <td>{r[0]}</td><td><b>{r[1]}</b></td><td>{r[2]}</td>
        <td>{r[3]}</td><td style='font-size:11px;color:#666'>{(r[4] or '')[:80]}</td>
    </tr>""" for r in logs)
    
    rows_users = "".join(f"""<tr>
        <td><b>{u[0]}</b></td><td>{u[1]}</td><td>{u[2]}</td>
        <td>{u[3]}</td><td>{u[4] or '—'}</td>
    </tr>""" for u in users)
    
    return f"""<!DOCTYPE html><html><head>
    <title>SenGenoScope Admin</title>
    <style>
        body{{font-family:monospace;padding:20px;background:#0f172a;color:#e2e8f0}}
        h2{{color:#38bdf8}} table{{width:100%;border-collapse:collapse;margin-bottom:30px}}
        th{{background:#1e3a5f;padding:8px;text-align:left;color:#7dd3fc}}
        td{{padding:6px 8px;border-bottom:1px solid #1e293b;font-size:13px}}
        tr:hover td{{background:#1e293b}}
        .badge{{background:#0e7490;padding:2px 8px;border-radius:10px;font-size:11px}}
    </style></head><body>
    <h2>🧬 SenGenoScope — Admin Dashboard</h2>
    <p>👥 <b>{len(users)}</b> utilisateurs inscrits · 🔑 <b>{len(logs)}</b> connexions dans les 48h · 📊 <b>{logs_all}</b> total</p>
    
    <h3>⚡ Activité dernières 48h — par utilisateur</h3>
    <table><tr><th>Nom</th><th>Email</th><th>Connexions</th><th>Dernière activité</th></tr>
    {rows_stats}</table>
    
    <h3>🔑 Connexions détaillées (48h)</h3>
    <table><tr><th>Date/Heure</th><th>Nom</th><th>Email</th><th>IP</th><th>Navigateur</th></tr>
    {rows_logs}</table>
    
    <h3>👥 Utilisateurs inscrits</h3>
    <table><tr><th>Nom</th><th>Email</th><th>Institution</th><th>Inscrit le</th><th>Dernière connexion</th></tr>
    {rows_users}</table>
    </body></html>"""


# ══ CIViC API — Clinical Interpretation of Variants in Cancer ═══════════════
@app.route("/civic_lookup")
def civic_lookup():
    """Recherche CIViC pour un gène ou variant."""
    gene = request.args.get("gene", "").strip().upper()
    variant = request.args.get("variant", "").strip()
    if not gene:
        return jsonify({"error": "Gène requis"}), 400
    try:
        import requests as req
        # API CIViC GraphQL
        query = """
        query {
          genes(name: "%s") {
            nodes {
              name
              variants {
                nodes {
                  name
                  variantAliases
                  evidenceItems {
                    nodes {
                      evidenceLevel
                      evidenceType
                      significance
                      description
                      disease { name }
                      therapies { nodes { name } }
                      source { citation citationId sourceType }
                    }
                  }
                }
              }
            }
          }
        }
        """ % gene
        r = req.post(
            "https://civicdb.org/api/graphql",
            json={"query": query},
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        data = r.json()
        genes = data.get("data", {}).get("genes", {}).get("nodes", [])
        if not genes:
            return jsonify({"gene": gene, "variants": [], "message": "Aucun résultat CIViC"})
        
        results = []
        for g in genes[:1]:
            for v in g.get("variants", {}).get("nodes", [])[:10]:
                v_name = v.get("name", "")
                if variant and variant.upper() not in v_name.upper():
                    continue
                evidence_list = []
                for ev in v.get("evidenceItems", {}).get("nodes", [])[:5]:
                    therapies = [t["name"] for t in ev.get("therapies", {}).get("nodes", [])]
                    evidence_list.append({
                        "level": ev.get("evidenceLevel"),
                        "type": ev.get("evidenceType"),
                        "significance": ev.get("significance"),
                        "disease": ev.get("disease", {}).get("name") if ev.get("disease") else None,
                        "therapies": therapies,
                        "description": ev.get("description", "")[:200],
                        "citation": ev.get("source", {}).get("citation", "")
                    })
                results.append({
                    "variant": v_name,
                    "aliases": v.get("variantAliases", []),
                    "evidence": evidence_list
                })
        return jsonify({"gene": gene, "variants": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══ OncoKB API — Thérapies FDA approuvées ════════════════════════════════════
@app.route("/oncokb_lookup")
def oncokb_lookup():
    """Recherche OncoKB pour un variant."""
    gene = request.args.get("gene", "").strip().upper()
    alteration = request.args.get("alteration", "").strip()
    tumor_type = request.args.get("tumor_type", "").strip()
    if not gene:
        return jsonify({"error": "Gène requis"}), 400
    try:
        import requests as req
        oncokb_token = os.environ.get("ONCOKB_TOKEN", "")
        headers = {"Authorization": f"Bearer {oncokb_token}"} if oncokb_token else {}
        
        url = f"https://www.oncokb.org/api/v1/annotate/mutations/byProteinChange"
        params = {
            "hugoSymbol": gene,
            "alteration": alteration or "any",
            "tumorType": tumor_type or ""
        }
        r = req.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 401:
            return jsonify({
                "gene": gene,
                "message": "OncoKB nécessite un token API. Visitez oncokb.org pour en obtenir un gratuit.",
                "oncokb_url": f"https://www.oncokb.org/gene/{gene}"
            })
        data = r.json()
        return jsonify({
            "gene": gene,
            "alteration": alteration,
            "oncogenic": data.get("oncogenic"),
            "mutationEffect": data.get("mutationEffect", {}).get("knownEffect"),
            "highestSensitiveLevel": data.get("highestSensitiveLevel"),
            "highestResistanceLevel": data.get("highestResistanceLevel"),
            "treatments": data.get("treatments", [])[:5],
            "oncokb_url": f"https://www.oncokb.org/gene/{gene}/{alteration}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══ RCP VIRTUELLE — Réunion de Concertation Pluridisciplinaire ═══════════════
@app.route("/ai/rcp", methods=["POST"])
def ai_rcp():
    """RCP virtuelle: consultation séquentielle de plusieurs cliniciens."""
    data = request.get_json()
    case = data.get("case", "").strip()
    specialists = data.get("specialists", ["oncogeneticist", "oncologist", "pathologist"])
    user_api_key = request.headers.get("X-User-Api-Key", "").strip()
    
    if not case:
        return jsonify({"error": "Description du cas requise"}), 400
    
    from virtual_clinicians import CLINICIANS, consult_clinician
    
    results = []
    clinician_map = {c["id"]: c for c in CLINICIANS}
    
    for spec_id in specialists[:4]:  # Max 4 spécialistes
        clinician = clinician_map.get(spec_id)
        if not clinician:
            continue
        result = consult_clinician(clinician, case, user_api_key=user_api_key)
        if result.get("success"):
            results.append({
                "clinician": clinician["name"],
                "specialty": clinician["specialty"],
                "icon": clinician.get("icon", "🩺"),
                "response": result["response"]
            })
    
    if not results:
        return jsonify({"error": "Aucune réponse obtenue"}), 500
    
    # Synthèse finale par Claude
        opinions_text = "\n\n".join([
        f"--- {r['specialty']} ({r['clinician']}) ---\n{r['response'][:500]}"
        for r in results
    ])
    synthesis_prompt = (
        f"Tu es coordinateur d une RCP (Réunion de Concertation Pluridisciplinaire).\n\n"
        f"CAS CLINIQUE: {case}\n\n"
        f"AVIS DES SPÉCIALISTES:\n{opinions_text}\n\n"
        "Produisez une SYNTHÈSE RCP structurée:\n"
        "1. POINTS DE CONSENSUS entre les spécialistes\n"
        "2. POINTS DE DIVERGENCE ou complémentarités\n"
        "3. DÉCISION THÉRAPEUTIQUE RECOMMANDÉE (votée par la RCP)\n"
        "4. PLAN DE SUIVI et examens complémentaires\n"
        "5. CRITÈRES DE RÉÉVALUATION\n\n"
        "Format: synthèse concise, cliniquement actionnable, niveau de preuve indiqué."
    )

    try:
        import anthropic
        api_key = user_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        synthesis = response.content[0].text if response.content else ""
    except Exception as e:
        synthesis = f"Synthèse non disponible: {e}"
    
    return jsonify({
        "success": True,
        "case": case,
        "specialists_consulted": len(results),
        "opinions": results,
        "synthesis": synthesis
    })




# ══ ROUTES CLINICIENS VIRTUELS ══════════════════════════════════════════

@app.route('/ai/clinicians', methods=['GET'])
def get_clinicians_list():
    try:
        from virtual_clinicians import get_all_clinicians
        return jsonify({"success": True, "clinicians": get_all_clinicians()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/ai/clinician', methods=['POST'])
def consult_clinician_route():
    try:
        data = request.get_json() or {}
        clinician_id = data.get('clinician_id', '')
        message = data.get('message', '')
        history = data.get('history', [])
        user_api_key = data.get('user_api_key') or request.headers.get('X-User-Api-Key')
        if not clinician_id or not message:
            return jsonify({"success": False, "error": "clinician_id et message requis"}), 400
        from virtual_clinicians import consult_clinician_ai
        result = consult_clinician_ai(clinician_id, message, history, user_api_key)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500

@app.route('/ai/rcp', methods=['POST'])
def rcp_consultation_route():
    try:
        data = request.get_json() or {}
        case = data.get('case', '')
        user_api_key = data.get('user_api_key') or request.headers.get('X-User-Api-Key')
        if not case:
            return jsonify({"success": False, "error": "Description du cas requise"}), 400
        from virtual_clinicians import get_all_clinicians, consult_clinician_ai
        clinicians = [c for c in get_all_clinicians() if c.get('id') != 'rcp_coordinator'][:4]
        results = [r for c in clinicians
                   for r in [consult_clinician_ai(c['id'], case, [], user_api_key)]
                   if r.get('success')]
        if not results:
            return jsonify({"success": False, "error": "Aucun clinicien disponible"}), 500
        opinions_text = "\n\n".join([
            f"--- {r['specialty']} ({r['clinician']}) ---\n{r['response'][:500]}"
            for r in results
        ])
        synthesis_prompt = (
            "Tu coordonnes une RCP. Synthèse structurée:\n"
            "1. CONSENSUS\n2. DIVERGENCES\n3. DÉCISION THÉRAPEUTIQUE\n"
            "4. PLAN DE SUIVI\n5. CRITÈRES DE RÉÉVALUATION\n\n"
            f"CAS: {case}\n\nAVIS:\n{opinions_text}"
        )
        try:
            import anthropic, os
            client = anthropic.Anthropic(api_key=user_api_key or os.environ.get("ANTHROPIC_API_KEY",""))
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=1000,
                messages=[{"role":"user","content":synthesis_prompt}])
            synthesis = resp.content[0].text if resp.content else ""
        except Exception as e:
            synthesis = f"Synthèse non disponible: {e}"
        return jsonify({"success":True,"opinions":results,"synthesis":synthesis,"specialists_consulted":len(results)})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500

# ══ FIN ROUTES CLINICIENS ════════════════════════════════════════════════

@app.route('/export_clinician_pdf', methods=['POST'])
@login_required
def export_clinician_pdf():
    try:
        data = request.get_json() or {}
        messages = data.get('messages', [])
        if not messages: return jsonify({"error": "Aucun message"}), 400
        pdf_bytes = generate_clinician_pdf(
            clinician_id=data.get('clinician_id',''), clinician_name=data.get('clinician_name','Clinicien'),
            clinician_specialty=data.get('clinician_specialty',''), messages=messages,
            patient_context=data.get('patient_context',''))
        name = data.get('clinician_name','Clinicien').replace(' ','_')
        return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True,
                         download_name=f"consultation_{name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/consultations/save', methods=['POST'])
@login_required
def save_consultation():
    try:
        import json as J
        data = request.get_json() or {}
        uid = session.get('user_id'); cid = data.get('id')
        msgs = data.get('messages',[]); clin_id = data.get('clinician_id','')
        if not clin_id or not msgs: return jsonify({"error":"requis"}),400
        title = data.get('title','') or next((m['content'] for m in msgs if m.get('role')=='user'),'')[:60]
        mj = J.dumps(msgs, ensure_ascii=False)
        conn, _db = get_conn()
        if cid:
            conn.execute("UPDATE consultations SET messages=?,title=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",(mj,title,cid,uid))
            conn.commit(); conn.close(); return jsonify({"success":True,"id":cid})
        cur = conn.execute("INSERT INTO consultations(user_id,clinician_id,clinician_name,clinician_specialty,title,messages) VALUES(?,?,?,?,?,?)",
                           (uid,clin_id,data.get('clinician_name',''),data.get('clinician_specialty',''),title,mj))
        nid=cur.lastrowid; conn.commit(); conn.close(); return jsonify({"success":True,"id":nid})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/consultations/list', methods=['GET'])
@login_required
def list_consultations():
    try:
        uid=session.get('user_id'); lim=min(int(request.args.get('limit',20)),50)
        conn,_db=get_conn()
        cur=conn.cursor()
        ph="%s" if _db=="pg" else "?"
        cur.execute(f"SELECT id,clinician_id,clinician_name,clinician_specialty,title,created_at,updated_at FROM consultations WHERE user_id={ph} ORDER BY updated_at DESC LIMIT {ph}",(uid,lim))
        rows=cur.fetchall()
        conn.close()
        return jsonify({"success":True,"consultations":[{"id":r[0],"clinician_id":r[1],"clinician_name":r[2],"clinician_specialty":r[3],"title":r[4],"created_at":r[5],"updated_at":r[6]} for r in rows]})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/consultations/<int:cid>', methods=['GET'])
@login_required
def get_consultation(cid):
    try:
        import json as J; uid=session.get('user_id')
        conn,_db=get_conn()
        cur=conn.cursor()
        ph="%s" if _db=="pg" else "?"
        cur.execute(f"SELECT id,clinician_id,clinician_name,clinician_specialty,title,messages,created_at,updated_at FROM consultations WHERE id={ph} AND user_id={ph}",(cid,uid))
        row=cur.fetchone()
        conn.close()
        if not row: return jsonify({"error":"introuvable"}),404
        return jsonify({"success":True,"id":row[0],"clinician_id":row[1],"clinician_name":row[2],"clinician_specialty":row[3],"title":row[4],"messages":J.loads(row[5]),"created_at":row[6],"updated_at":row[7]})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/consultations/<int:cid>', methods=['DELETE'])
@login_required
def delete_consultation(cid):
    try:
        uid=session.get('user_id'); conn,_db=get_conn()
        cur=conn.cursor()
        ph="%s" if _db=="pg" else "?"
        cur.execute(f"DELETE FROM consultations WHERE id={ph} AND user_id={ph}",(cid,uid)); conn.commit(); conn.close()
        return jsonify({"success":True})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/consultations/rate', methods=['POST'])
@login_required
def rate_consultation_message():
    try:
        import json as J; data=request.get_json() or {}
        cid=data.get('consultation_id'); idx=data.get('msg_index'); rating=data.get('rating')
        if not cid or idx is None or rating not in (1,-1): return jsonify({"error":"invalide"}),400
        uid=session.get('user_id'); conn,_db=get_conn()
        cur=conn.cursor()
        ph="%s" if _db=="pg" else "?"
        cur.execute(f"SELECT messages FROM consultations WHERE id={ph} AND user_id={ph}",(cid,uid))
        row=cur.fetchone()
        if not row: conn.close(); return jsonify({"error":"introuvable"}),404
        msgs=J.loads(row[0])
        if 0<=idx<len(msgs): msgs[idx]['rating']=rating
        conn.execute("UPDATE consultations SET messages=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(J.dumps(msgs,ensure_ascii=False),cid))
        conn.commit(); conn.close(); return jsonify({"success":True})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/consultations/soap', methods=['POST'])
@login_required
def generate_soap_summary():
    try:
        import anthropic as _ant
        data = request.get_json() or {}
        msgs = data.get('messages', [])
        cname = data.get('clinician_name', 'Clinicien')
        api_key = data.get('user_api_key', '').strip() or os.environ.get("ANTHROPIC_API_KEY", "")
        if not msgs or len(msgs) < 2:
            return jsonify({"error": "Consultation insuffisante"}), 400
        if not api_key:
            return jsonify({"error": "Cle API manquante"}), 400
        parts = []
        for m in msgs:
            if m.get('content'):
                role = 'PATIENT' if m['role'] == 'user' else cname.upper()
                parts.append(role + ':\n' + m['content'])
        transcript = '\n\n'.join(parts)[:4000]
        prompt = (
            "Genere un resume SOAP en francais pour cette consultation avec " + cname + ".\n\n"
            "TRANSCRIPTION:\n" + transcript + "\n\n"
            "## S - Subjectif\n[Motif, symptomes, antecedents, contexte familial]\n\n"
            "## O - Objectif\n[Variants, resultats biologiques, imagerie, scores de risque]\n\n"
            "## A - Assessment\n[Diagnostic principal, differentiels, ACMG si applicable]\n\n"
            "## P - Plan\n[Examens, traitements, essais cliniques, suivi, conseil genetique]\n\n"
            "---\nClinician: " + cname + " | Date: " + datetime.now().strftime('%d/%m/%Y') + "\n"
            "Resume IA - a valider par le clinicien responsable"
        )
        client = _ant.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return jsonify({"success": True, "soap": resp.content[0].text if resp.content else ""})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/stats/dashboard', methods=['GET'])
@login_required
def stats_dashboard():
    try:
        import json as J; conn,_db=get_conn()
        cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM consultations")
        total=cur.fetchone()[0]
        by_clin=conn.execute("SELECT clinician_name,clinician_id,COUNT(*) FROM consultations GROUP BY clinician_id ORDER BY COUNT(*) DESC").fetchall()
        by_day=conn.execute("SELECT DATE(created_at),COUNT(*) FROM consultations WHERE created_at>=DATE('now','-30 days') GROUP BY DATE(created_at) ORDER BY DATE(created_at)").fetchall()
        all_m=conn.execute("SELECT messages FROM consultations").fetchall()
        total_msgs=tu=td=0
        for (m,) in all_m:
            try:
                ml=J.loads(m); total_msgs+=len(ml)
                for msg in ml:
                    r=msg.get('rating',0)
                    if r==1: tu+=1
                    elif r==-1: td+=1
            except: pass
        users=conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        uid=session.get('user_id')
        mine=conn.execute("SELECT COUNT(*) FROM consultations WHERE user_id=?",(uid,)).fetchone()[0]
        week=conn.execute("SELECT COUNT(*) FROM consultations WHERE created_at>=DATE('now','-7 days')").fetchone()[0]
        conn.close()
        tot_r=tu+td; sat=round(tu/tot_r*100) if tot_r>0 else None
        return jsonify({"success":True,"total_consultations":total,"my_consultations":mine,"total_messages":total_msgs,
                        "user_count":users,"week_count":week,"satisfaction":sat,
                        "by_clinician":[{"name":r[0],"id":r[1],"count":r[2]} for r in by_clin],
                        "by_day":[{"day":r[0],"count":r[1]} for r in by_day]})
    except Exception as e: return jsonify({"error":str(e)}),500


# Exempter les routes API JSON du CSRF (protégées par JWT Supabase)
if _has_csrf:
    _csrf_exempt_list = [
        'api_login','api_register','api_logout','log_login',
        'api_get_patients','api_create_patient','api_save_analysis',
        'interpret_ngs','analyze_cnv','analyze_fusions',
        'analyze_signatures','tumor_board','compare_therapeutics',
        'calculate_hrd','generate_clinical_pdf'
    ]
    import sys as _sys
    _mod = _sys.modules[__name__]
    for _fname in _csrf_exempt_list:
        _f = getattr(_mod, _fname, None)
        if _f: csrf.exempt(_f)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


@app.route("/api/users/count")
def users_count():
    """Nombre d'utilisateurs inscrits (public, sans données perso)."""
    try:
        conn, _db = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return jsonify({"count": count})
    except:
        return jsonify({"count": 0})


# ── Admin Dashboard ──────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-sgs-2026")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get("key", "")
        if key != os.environ.get("ADMIN_PASSWORD", "admin2026"):
            return "<h2 style='font-family:sans-serif;padding:40px'>Access denied — provide ?key=YOUR_ADMIN_PASSWORD</h2>", 403
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    return "", 403

@app.route("/admin")
@admin_required
def admin_dashboard():
    import sqlite3 as _sq
    from datetime import datetime, timedelta
    conn, db_type = get_conn()
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
    }
    return render_template("admin.html", users=users, stats=stats, logs=logs)

@app.route('/morpho_analyze', methods=['POST'])
def morpho_analyze():
    """Route backend pour analyse morpho-génétique via Claude AI."""
    import base64 as b64
    data = request.get_json() or {}
    cancer_type = data.get('cancer_type', 'sein')
    sample = data.get('sample', 'Biopsie core-needle')
    stain = data.get('stain', 'HE')
    context = data.get('context', '')
    image_b64 = data.get('image_b64', '')
    image_type = data.get('image_type', 'image/jpeg')

    LABELS = {
        'sein': 'Cancer du sein',
        'prostate': 'Cancer de la prostate',
        'pediatrique': 'Cancers pédiatriques'
    }
    label = LABELS.get(cancer_type, cancer_type)

    prompt = f"""Tu es un expert en anatomopathologie oncologique spécialisé dans les populations africaines subsahariennes.

Cancer analysé: {label}
Prélèvement: {sample} | Coloration: {stain}
{f'Contexte clinique: {context}' if context else ''}
{f'Une image histologique est jointe.' if image_b64 else 'Génère une analyse typique pour ce cancer dans les populations africaines.'}

Réponds UNIQUEMENT en JSON valide (sans balises markdown) :
{{
  "type_tumoral": "...",
  "grade": "...",
  "stade_probable": "...",
  "recepteurs": "...",
  "morpho_description": "Description morphologique détaillée (3-4 phrases)",
  "mutations_probables": ["GENE1", "GENE2"],
  "niveau_confiance": "Élevé|Modéré|Faible",
  "guidelines": "...",
  "contexte_africain": "Spécificités épidémiologiques et génétiques populations africaines (2-3 phrases)",
  "examens_complementaires": "..."
}}"""

    if not CLAUDE_AVAILABLE:
        return jsonify({'error': 'Claude AI non configuré — clé API manquante'})

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY',''))

        content = []
        if image_b64:
            content.append({
                'type': 'image',
                'source': {'type': 'base64', 'media_type': image_type, 'data': image_b64}
            })
        content.append({'type': 'text', 'text': prompt})

        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': content}]
        )
        text = resp.content[0].text.strip().replace('```json','').replace('```','').strip()
        import json as _json
        parsed = _json.loads(text)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


app.config['PERMANENT_SESSION_LIFETIME'] = __import__('datetime').timedelta(minutes=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# ══ PATIENTS ══════════════════════════════════════════════════════
@app.route('/patients/list')
@login_required
def list_patients():
    try:
        uid = session['user_id']
        conn, _db = get_conn()
        cur = conn.cursor()
        ph = "%s" if _db == "pg" else "?"
        cur.execute(f"SELECT id,nom,prenom,date_naissance,numero_dossier,diagnostic,notes,created_at FROM patients WHERE user_id={ph} ORDER BY nom ASC", (uid,))
        rows = cur.fetchall()
        conn.close()
        patients = [{"id":r[0],"nom":r[1],"prenom":r[2],"date_naissance":r[3],"numero_dossier":r[4],"diagnostic":r[5],"notes":r[6],"created_at":str(r[7])} for r in rows]
        return jsonify({"success": True, "patients": patients})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/create', methods=['POST'])
@login_required
def create_patient():
    try:
        uid = session['user_id']
        data = request.json or {}
        nom = data.get('nom', '').strip()
        if not nom:
            return jsonify({"success": False, "error": "Nom requis"})
        conn, _db = get_conn()
        cur = conn.cursor()
        ph = "%s" if _db == "pg" else "?"
        cur.execute(f"INSERT INTO patients (user_id,nom,prenom,date_naissance,numero_dossier,diagnostic,notes) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
            (uid, nom, data.get('prenom',''), data.get('date_naissance',''), data.get('numero_dossier',''), data.get('diagnostic',''), data.get('notes','')))
        conn.commit()
        if _db == "pg":
            cur.execute("SELECT LASTVAL()")
            pid = cur.fetchone()[0]
        else:
            pid = cur.lastrowid
        conn.close()
        return jsonify({"success": True, "id": pid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/<int:pid>', methods=['GET','PUT','DELETE'])
@login_required
def patient_detail(pid):
    uid = session['user_id']
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        if request.method == 'GET':
            cur.execute(f"SELECT id,nom,prenom,date_naissance,numero_dossier,diagnostic,notes,created_at FROM patients WHERE id={ph} AND user_id={ph}", (pid,uid))
            r = cur.fetchone()
            if not r:
                return jsonify({"success": False, "error": "Patient non trouve"})
            cur.execute(f"SELECT id,clinician_name,clinician_specialty,title,updated_at FROM consultations WHERE patient_id={ph} AND user_id={ph} ORDER BY updated_at DESC", (pid,uid))
            consults = [{"id":c[0],"clinician_name":c[1],"clinician_specialty":c[2],"title":c[3],"updated_at":str(c[4])} for c in cur.fetchall()]
            conn.close()
            return jsonify({"success":True,"patient":{"id":r[0],"nom":r[1],"prenom":r[2],"date_naissance":r[3],"numero_dossier":r[4],"diagnostic":r[5],"notes":r[6],"created_at":str(r[7])},"consultations":consults})
        elif request.method == 'PUT':
            data = request.json or {}
            cur.execute(f"UPDATE patients SET nom={ph},prenom={ph},date_naissance={ph},numero_dossier={ph},diagnostic={ph},notes={ph} WHERE id={ph} AND user_id={ph}",
                (data.get('nom',''),data.get('prenom',''),data.get('date_naissance',''),data.get('numero_dossier',''),data.get('diagnostic',''),data.get('notes',''),pid,uid))
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            cur.execute(f"DELETE FROM patients WHERE id={ph} AND user_id={ph}", (pid,uid))
            conn.commit()
            conn.close()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/attach', methods=['POST'])
@login_required
def attach_patient():
    try:
        uid = session['user_id']
        data = request.json or {}
        conn, _db = get_conn()
        cur = conn.cursor()
        ph = "%s" if _db == "pg" else "?"
        cur.execute(f"UPDATE consultations SET patient_id={ph} WHERE id={ph} AND user_id={ph}",
            (data.get('patient_id'), data.get('consultation_id'), uid))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/<int:pid>/export_pdf')
@login_required
def export_patient_pdf(pid):
    """Exporte le dossier complet d'un patient en PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        import io, json
        from datetime import datetime

        uid = session['user_id']
        conn, _db = get_conn()
        cur = conn.cursor()
        ph = "%s" if _db == "pg" else "?"

        cur.execute(f"SELECT id,nom,prenom,date_naissance,numero_dossier,diagnostic,notes,created_at FROM patients WHERE id={ph} AND user_id={ph}", (pid, uid))
        p = cur.fetchone()
        if not p:
            return jsonify({"success": False, "error": "Patient non trouve"}), 404

        cur.execute(f"SELECT id,clinician_name,clinician_specialty,title,messages,updated_at FROM consultations WHERE patient_id={ph} AND user_id={ph} ORDER BY updated_at ASC", (pid, uid))
        consults = cur.fetchall()
        conn.close()

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Titre
        title_style = ParagraphStyle('title', fontSize=20, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d9488'), spaceAfter=6)
        sub_style = ParagraphStyle('sub', fontSize=11, fontName='Helvetica', textColor=colors.HexColor('#64748b'), spaceAfter=16)
        h2_style = ParagraphStyle('h2', fontSize=13, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'), spaceBefore=14, spaceAfter=8)
        body_style = ParagraphStyle('body', fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#374151'), spaceAfter=4, leading=14)
        label_style = ParagraphStyle('label', fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#6b7280'), spaceAfter=2)
        msg_user_style = ParagraphStyle('mu', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#1e40af'), spaceAfter=4, leftIndent=20, leading=13)
        msg_ai_style = ParagraphStyle('ma', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#374151'), spaceAfter=8, leftIndent=20, leading=13)

        story.append(Paragraph("SenGenoScope", title_style))
        story.append(Paragraph("Dossier Patient — Oncogénomique Clinique", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 12))

        # Infos patient
        story.append(Paragraph("Informations Patient", h2_style))
        nom_complet = (p[1] or '') + ' ' + (p[2] or '')
        data_table = [
            ['Nom complet', nom_complet.strip()],
            ['Date de naissance', p[3] or 'Non renseignée'],
            ['N° dossier', p[4] or 'Non renseigné'],
            ['Diagnostic principal', p[5] or 'Non renseigné'],
            ['Notes', p[6] or ''],
            ['Dossier créé le', str(p[7])[:10] if p[7] else ''],
        ]
        t = Table(data_table, colWidths=[4*cm, 13*cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#6b7280')),
            ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor('#1e293b')),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 16))

        # Consultations
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph(f"Consultations ({len(consults)})", h2_style))

        if not consults:
            story.append(Paragraph("Aucune consultation associée à ce patient.", body_style))
        else:
            for i, c in enumerate(consults):
                cid, clin_name, clin_spec, title, messages_json, updated_at = c
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"Consultation {i+1} — {clin_name}", ParagraphStyle('ch', fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d9488'), spaceAfter=2)))
                story.append(Paragraph(f"{clin_spec or ''} · {str(updated_at)[:10]}", label_style))
                if title:
                    story.append(Paragraph(f"Sujet: {title}", label_style))
                story.append(Spacer(1, 4))
                try:
                    msgs = json.loads(messages_json) if messages_json else []
                    for msg in msgs[:20]:
                        role = msg.get('role', '')
                        content = (msg.get('content', '') or '')[:500]
                        content = content.replace('<', '&lt;').replace('>', '&gt;').replace('**', '').replace('*', '')
                        if role == 'user':
                            story.append(Paragraph(f"<b>Patient:</b> {content}", msg_user_style))
                        elif role == 'assistant':
                            story.append(Paragraph(f"<b>{clin_name}:</b> {content}", msg_ai_style))
                except:
                    pass
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#f1f5f9')))

        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — SenGenoScope v1.0", ParagraphStyle('footer', fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)))

        doc.build(story)
        buf.seek(0)
        from flask import send_file
        safe_name = (p[1] or 'patient').replace(' ', '_')
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'dossier_{safe_name}_{pid}.pdf')

    except Exception as e:
        logging.error(f"Export PDF patient: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/clinicians/stream', methods=['POST'])
@login_required
def stream_clinician():
    """Streaming SSE pour les réponses des cliniciens."""
    import anthropic as _anthropic
    from flask import Response, stream_with_context
    import json as _json

    data = request.json or {}
    clinician_id = data.get('clinician_id', '')
    messages = data.get('messages', [])
    api_key = data.get('user_api_key') or os.environ.get('ANTHROPIC_API_KEY', '')

    try:
        from virtual_clinicians import get_all_clinicians
        clinicians = get_all_clinicians()
        clinician = next((c for c in clinicians if c['id'] == clinician_id), None)
        if not clinician:
            return jsonify({"error": "Clinicien non trouvé"}), 404

        DOMAINS = {
            "oncogeneticist": "variants genetiques, predispositions hereditaires, BRCA1/2, Lynch",
            "oncologist": "oncologie, therapies ciblees, immunotherapie, biomarqueurs",
            "pathologist": "anatomopathologie, histologie, IHC, MSI/MMR, TMB",
            "geneticist": "genetique clinique, maladies rares, phenotypage HPO",
            "generalist": "medecine generale, orientation diagnostique, prevention",
            "internist": "medecine interne, maladies systemiques, auto-immunite",
            "hematologist": "hematologie, leucemies, lymphomes, drepanocytose",
            "radiologist": "imagerie medicale, echographie, scanner, IRM",
            "gynecologist": "gynecologie, obstetrique, oncogynecologie",
            "pediatric_oncologist": "oncologie pediatrique, tumeurs pediatriques",
            "pain_specialist": "douleur chronique, soins palliatifs",
            "rcp_coordinator": "coordination pluridisciplinaire, consensus RCP",
        }
        domain = DOMAINS.get(clinician_id, "ma specialite")
        clin_name = clinician.get("name", "le clinicien")
        clin_spec = clinician.get("specialty", "specialiste")
        system = (
            "IDENTITE ABSOLUE: Tu es " + clin_name + ", " + clin_spec + ". "
            "Tu N'ES PAS Claude. Tu es un clinicien reel. "
            "Ne mentionne JAMAIS Claude, Anthropic, IA ou modele de langage.\n\n"
            "RESTRICTION DE DOMAINE: Tu es specialiste en " + domain + ". "
            "Si hors domaine, oriente vers le bon specialiste.\n\n"
        ) + clinician.get("system_prompt", "")

        api_msgs = [{"role": m["role"], "content": m["content"]} for m in messages
                    if m.get("role") in ("user", "assistant") and m.get("content")]

        def generate():
            client = _anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                system=system,
                messages=api_msgs
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {_json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream',
                       headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══ INTERPRÉTEUR NGS AUTOMATIQUE ═════════════════════════════════════════════
@app.route('/interpret_ngs', methods=['POST'])
@login_required
def interpret_ngs():
    """Interpréter un rapport NGS avec classification ACMG et recommandations."""
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key', '') or data.get('user_api_key', '')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify({"success": False, "error": "Clé API manquante. Configurez votre clé via le bouton Clé API."})
        ngs_text = data.get('text', '').strip()
        context = data.get('context', '')

        if not ngs_text:
            return jsonify({"success": False, "error": "Aucun texte NGS fourni"})

        if len(ngs_text) > 50000:
            ngs_text = ngs_text[:50000]

        system_prompt = """Tu es un expert en génomique oncologique clinique.
Tu dois analyser un rapport NGS et produire une interprétation structurée en JSON strict.

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.

Format de réponse:
{
  "variants": [
    {
      "gene": "BRCA1",
      "variant": "c.5266dupC",
      "protein": "p.Gln1756Profs",
      "type": "frameshift",
      "zygosity": "heterozygote",
      "acmg_class": "Pathogène",
      "acmg_criteria": ["PVS1", "PM2", "PP5"],
      "vaf": "45%",
      "depth": "150x",
      "clinical_significance": "Prédisposition syndrome Sein/Ovaire héréditaire",
      "action": "Consultation oncogénétique recommandée. Test cascade famille."
    }
  ],
  "tmb": {"value": "12 mut/Mb", "interpretation": "Intermédiaire"},
  "msi": {"status": "MSS", "interpretation": "Stable"},
  "summary": "Résumé clinique en 2-3 phrases",
  "recommendations": ["Recommandation 1", "Recommandation 2"],
  "guidelines": ["NCCN 2024: ...", "ESMO: ..."],
  "urgent": false,
  "urgent_reason": ""
}

Si une donnée est absente du rapport, mets null.
Classe ACMG: Pathogène, Probablement pathogène, VUS, Probablement bénin, Bénin."""

        user_msg = "Analyse ce rapport NGS:\n\n" + ngs_text
        if context:
            user_msg += "\n\nContexte clinique: " + context

        import anthropic as _anth
        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}]
        )

        import json as _json
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = _json.loads(raw)
        return jsonify({"success": True, "result": result, "raw": raw})

    except Exception as e:
        logging.error(f"interpret_ngs error: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/ngs_to_pdf', methods=['POST'])
@login_required
def ngs_to_pdf():
    """Générer un rapport PDF depuis l'analyse NGS."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER
        import io, json as _json
        from datetime import datetime

        data = request.json or {}
        result = data.get('result', {})
        context = data.get('context', '')

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)

        styles = getSampleStyleSheet()
        title_s = ParagraphStyle('t', fontSize=18, fontName='Helvetica-Bold',
                                textColor=colors.HexColor('#0d9488'), spaceAfter=4)
        sub_s = ParagraphStyle('s', fontSize=10, fontName='Helvetica',
                              textColor=colors.HexColor('#64748b'), spaceAfter=16)
        h2_s = ParagraphStyle('h2', fontSize=13, fontName='Helvetica-Bold',
                             textColor=colors.HexColor('#1e293b'), spaceBefore=14, spaceAfter=8)
        body_s = ParagraphStyle('b', fontSize=10, fontName='Helvetica',
                               textColor=colors.HexColor('#374151'), spaceAfter=4, leading=14)
        urgent_s = ParagraphStyle('u', fontSize=11, fontName='Helvetica-Bold',
                                 textColor=colors.HexColor('#dc2626'), spaceAfter=8)

        ACMG_COLORS = {
            'Pathogène': '#dc2626', 'Probablement pathogène': '#f97316',
            'VUS': '#f59e0b', 'Probablement bénin': '#84cc16', 'Bénin': '#22c55e'
        }

        story = []
        story.append(Paragraph("SenGenoScope — Rapport NGS", title_s))
        story.append(Paragraph(f"Analyse génomique oncologique · {datetime.now().strftime('%d/%m/%Y')}", sub_s))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 10))

        if result.get('urgent'):
            story.append(Paragraph(f"ALERTE URGENTE: {result.get('urgent_reason', '')}", urgent_s))

        if result.get('summary'):
            story.append(Paragraph("Résumé clinique", h2_s))
            story.append(Paragraph(result['summary'], body_s))

        variants = result.get('variants', [])
        if variants:
            story.append(Paragraph(f"Variants identifiés ({len(variants)})", h2_s))
            for v in variants:
                acmg = v.get('acmg_class', 'VUS')
                col = colors.HexColor(ACMG_COLORS.get(acmg, '#f59e0b'))
                v_data = [
                    ['Gène', v.get('gene', '-'), 'Variant', v.get('variant', '-')],
                    ['Classe ACMG', acmg, 'Zygosité', v.get('zygosity', '-')],
                    ['VAF', v.get('vaf', '-'), 'Profondeur', v.get('depth', '-')],
                    ['Critères', ', '.join(v.get('acmg_criteria', [])), 'Type', v.get('type', '-')],
                ]
                t = Table(v_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 4.5*cm])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                    ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
                    ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1e293b')),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('BOX', (0,0), (-1,-1), 0.5, col),
                    ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
                ]))
                story.append(t)
                if v.get('clinical_significance'):
                    story.append(Paragraph(f"Signification: {v['clinical_significance']}", body_s))
                if v.get('action'):
                    story.append(Paragraph(f"Conduite: {v['action']}", ParagraphStyle('a', fontSize=10,
                        fontName='Helvetica-Bold', textColor=colors.HexColor('#0d9488'), spaceAfter=10)))

        tmb = result.get('tmb')
        msi = result.get('msi')
        if tmb or msi:
            story.append(Paragraph("Biomarqueurs", h2_s))
            bm_data = []
            if tmb: bm_data.append(['TMB', str(tmb.get('value','-')), tmb.get('interpretation','')])
            if msi: bm_data.append(['MSI', str(msi.get('status','-')), msi.get('interpretation','')])
            if bm_data:
                t2 = Table([['Marqueur','Valeur','Interprétation']] + bm_data,
                           colWidths=[4*cm, 4*cm, 9*cm])
                t2.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d9488')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(t2)

        recs = result.get('recommendations', [])
        if recs:
            story.append(Paragraph("Recommandations", h2_s))
            for i, r in enumerate(recs, 1):
                story.append(Paragraph(f"{i}. {r}", body_s))

        guides = result.get('guidelines', [])
        if guides:
            story.append(Paragraph("Guidelines", h2_s))
            for g in guides:
                story.append(Paragraph(f"• {g}", body_s))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph(
            f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} par SenGenoScope v1.0 — Usage clinique confidentiel",
            ParagraphStyle('footer', fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)))

        doc.build(story)
        buf.seek(0)
        from flask import send_file
        return send_file(buf, mimetype='application/pdf', as_attachment=True,
                        download_name=f'rapport_ngs_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf')

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/analyze_cnv', methods=['POST'])
@login_required
def analyze_cnv():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key', '') or data.get('user_api_key', '')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify({"success": False, "error": "Cle API manquante."})
        cnv_text = data.get('text', '').strip()
        context  = data.get('context', '')
        if not cnv_text:
            return jsonify({"success": False, "error": "Aucune donnee CNV fournie."})
        if len(cnv_text) > 60000:
            cnv_text = cnv_text[:60000]
        system_prompt = """Tu es expert en oncogenomique clinique specialise dans les CNV.
Reponds UNIQUEMENT en JSON valide strict, sans texte avant/apres.
Format:
{
  "cnvs": [{"gene":"ERBB2","chromosome":"17q12","type":"amplification","copy_number":12,"log2_ratio":2.58,"size_mb":1.2,"clinical_significance":"Surexpression HER2","therapeutic_targets":["Trastuzumab","Pertuzumab"],"acmg_class":"Pathogene","databases":["OncoKB Tier 1"],"action":"Test HER2 confirmateur recommande."}],
  "summary":"Resume clinique","genome_instability":"Elevee",
  "recommendations":["Recommandation 1"],
  "urgent":false,"urgent_reason":""
}
Types: amplification (CN>4), gain (CN 3-4), perte (CN 1), deletion_homozygote (CN 0).
Si donnee absente: null."""
        user_msg = "Analyse ces donnees CNV:\n\n" + cnv_text
        if context:
            user_msg += "\n\nContexte: " + context
        import anthropic as _anth
        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=3000,
            system=system_prompt, messages=[{"role":"user","content":user_msg}])
        import json as _json
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        return jsonify({"success": True, "result": _json.loads(raw)})
    except Exception as e:
        import logging; logging.error(f"analyze_cnv error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/analyze_fusions', methods=['POST'])
@login_required
def analyze_fusions():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key', '') or data.get('user_api_key', '')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify({"success": False, "error": "Cle API manquante."})
        fusion_text = data.get('text', '').strip()
        context     = data.get('context', '')
        if not fusion_text:
            return jsonify({"success": False, "error": "Aucune donnee de fusion fournie."})
        if len(fusion_text) > 60000:
            fusion_text = fusion_text[:60000]
        system_prompt = """Tu es expert en fusions geniques oncologiques.
Reponds UNIQUEMENT en JSON valide strict.
Format:
{
  "fusions":[{"name":"EML4-ALK","gene5":"EML4","gene3":"ALK","breakpoint5":"2p21 exon 13","breakpoint3":"2p23 exon 20","variant_type":"inversion","read_support":45,"allele_frequency":"18%","oncogenic":true,"tier":"Tier I","cancer_types":["NSCLC"],"therapeutic_targets":["Crizotinib","Alectinib"],"resistance_mechanisms":["ALK G1202R"],"databases":["OncoKB Tier 1"],"action":"Eligible inhibiteurs ALK."}],
  "summary":"Resume","total_fusions":1,"oncogenic_fusions":1,"actionable_fusions":1,
  "recommendations":["Recommandation 1"],
  "urgent":false,"urgent_reason":""
}
Si donnee absente: null."""
        user_msg = "Analyse ces donnees de fusions geniques:\n\n" + fusion_text
        if context:
            user_msg += "\n\nContexte: " + context
        import anthropic as _anth
        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=3000,
            system=system_prompt, messages=[{"role":"user","content":user_msg}])
        import json as _json
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        return jsonify({"success": True, "result": _json.loads(raw)})
    except Exception as e:
        import logging; logging.error(f"analyze_fusions error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/analyze_signatures', methods=['POST'])
@login_required
def analyze_signatures():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key', '') or data.get('user_api_key', '')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify({"success": False, "error": "Cle API manquante."})
        sig_text = data.get('text', '').strip()
        context  = data.get('context', '')
        if not sig_text:
            return jsonify({"success": False, "error": "Aucune donnee de signature fournie."})
        if len(sig_text) > 60000:
            sig_text = sig_text[:60000]
        system_prompt = """Tu es expert en signatures mutationnelles COSMIC.
Reponds UNIQUEMENT en JSON valide strict.
Format:
{
  "signatures":[{"id":"SBS3","name":"Deficit HRR","contribution":42.5,"contribution_pct":"42.5%","etiology":"Deficit BRCA1/BRCA2","cancer_types":["Sein","Ovaire"],"clinical_implications":"Sensibilite inhibiteurs PARP","therapeutic_targets":["Olaparib","Niraparib"],"associated_genes":["BRCA1","BRCA2"],"confidence":"Haute"}],
  "dominant_signature":"SBS3","tmb":"12.4 mut/Mb","tmb_class":"Eleve",
  "hrd_score":42,"hrd_status":"Positif","msi_predicted":"MSS",
  "summary":"Resume","immunotherapy_prediction":"Moderee","parp_inhibitor_prediction":"Bonne sensibilite",
  "recommendations":["Recommandation 1"],
  "urgent":false,"urgent_reason":""
}
Signatures cles: SBS1 horloge | SBS2/13 APOBEC | SBS3 HRR/BRCA | SBS4 tabac | SBS6/15/20/26 MMR | SBS7 UV | SBS10 POLE.
Si donnee absente: null."""
        user_msg = "Analyse ces signatures mutationnelles:\n\n" + sig_text
        if context:
            user_msg += "\n\nContexte: " + context
        import anthropic as _anth
        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=3000,
            system=system_prompt, messages=[{"role":"user","content":user_msg}])
        import json as _json
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        return jsonify({"success": True, "result": _json.loads(raw)})
    except Exception as e:
        import logging; logging.error(f"analyze_signatures error: {e}")
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════
# AUTH — LOGIN / REGISTER / LOGOUT
# ════════════════════════════════════════════════════════


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    try:
        from supabase_client import get_supabase
        data = request.json or {}
        email    = data.get('email','').strip()
        password = data.get('password','').strip()
        name     = data.get('full_name','').strip()
        role     = data.get('role','medecin')
        institution = data.get('institution','').strip()

        if not email or not password:
            return jsonify({"success": False, "error": "Email et mot de passe requis"})

        sb = get_supabase()
        res = sb.auth.sign_up({"email": email, "password": password})
        user = res.user
        if not user:
            return jsonify({"success": False, "error": "Erreur inscription"})

        # Créer institution si nouvelle
        inst_id = None
        if institution:
            inst_res = sb.table('institutions').insert({"name": institution, "country": "Sénégal"}).execute()
            if inst_res.data:
                inst_id = inst_res.data[0]['id']

        # Créer profil
        sb.table('user_profiles').insert({
            "id": user.id,
            "email": email,
            "full_name": name,
            "role": role,
            "institution_id": inst_id
        }).execute()

        return jsonify({"success": True, "message": "Compte créé. Vérifiez votre email."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        from supabase_client import get_supabase
        data = request.json or {}
        email    = data.get('email','').strip()
        password = data.get('password','').strip()

        sb = get_supabase()
        res = sb.auth.sign_in_with_password({"email": email, "password": password})

        if not res.user:
            return jsonify({"success": False, "error": "Email ou mot de passe incorrect"})

        session['access_token'] = res.session.access_token
        session['user_id']      = res.user.id
        session['user_email']   = res.user.email
        session['authenticated'] = True

        # Récupérer profil
        profile_res = sb.table('user_profiles').select('*').eq('id', res.user.id).execute()
        profile = profile_res.data[0] if profile_res.data else {}
        session['user_name'] = profile.get('full_name', email)
        session['user_role'] = profile.get('role', 'medecin')

        # Récupérer institution
        inst_id = profile.get('institution_id')
        if inst_id:
            try:
                inst_res = sb.table('institutions').select('name').eq('id', inst_id).execute()
                if inst_res.data:
                    session['user_institution'] = inst_res.data[0].get('name', '')
                else:
                    session['user_institution'] = ''
            except:
                session['user_institution'] = ''
        else:
            session['user_institution'] = ''

        return jsonify({"success": True, "redirect": "/"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True, "redirect": "/login"})

@app.route('/api/auth/me')
def api_me():
    if 'user_email' not in session:
        return jsonify({"authenticated": False})
    return jsonify({
        "authenticated": True,
        "email": session.get('user_email'),
        "name":  session.get('user_name'),
        "role":  session.get('user_role')
    })


# ════════════════════════════════════════════════════════
# PATIENTS — CRUD
# ════════════════════════════════════════════════════════
@app.route('/api/patients', methods=['GET'])
def api_get_patients():
    try:
        from supabase_client import get_supabase
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Non authentifié"}), 401
        sb = get_supabase()
        res = sb.table('patients').select('*').eq('created_by', session['user_id']).order('created_at', desc=True).execute()
        return jsonify({"success": True, "patients": res.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/patients', methods=['POST'])
def api_create_patient():
    try:
        from supabase_client import get_supabase
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Non authentifié"}), 401
        data = request.json or {}
        sb = get_supabase()
        patient = {
            "created_by":   session['user_id'],
            "patient_code": data.get('patient_code', ''),
            "first_name":   data.get('first_name', ''),
            "last_name":    data.get('last_name', ''),
            "sex":          data.get('sex', ''),
            "cancer_type":  data.get('cancer_type', ''),
            "stage":        data.get('stage', ''),
            "notes":        data.get('notes', ''),
        }
        if data.get('date_of_birth'):
            patient['date_of_birth'] = data['date_of_birth']
        res = sb.table('patients').insert(patient).execute()
        return jsonify({"success": True, "patient": res.data[0] if res.data else {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/patients/<patient_id>/analyses', methods=['GET'])
def api_get_patient_analyses(patient_id):
    try:
        from supabase_client import get_supabase
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Non authentifié"}), 401
        sb = get_supabase()
        res = sb.table('analyses').select('*').eq('patient_id', patient_id).order('created_at', desc=True).execute()
        return jsonify({"success": True, "analyses": res.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/analyses/save', methods=['POST'])
def api_save_analysis():
    try:
        from supabase_client import get_supabase
        import json as _json
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Non authentifié"}), 401
        data = request.json or {}
        sb = get_supabase()
        analysis = {
            "patient_id":     data.get('patient_id'),
            "created_by":     session['user_id'],
            "analysis_type":  data.get('analysis_type','ngs'),
            "input_text":     data.get('input_text',''),
            "context":        data.get('context',''),
            "result":         data.get('result', {}),
            "status":         "completed"
        }
        res = sb.table('analyses').insert(analysis).execute()
        return jsonify({"success": True, "analysis": res.data[0] if res.data else {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════
# TUMEUR BOARD IA (MTB) — Synthèse multi-omique
# ════════════════════════════════════════════════════════
@app.route('/tumor_board', methods=['POST'])
def tumor_board():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key','') or data.get('user_api_key','')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY','')
        if not api_key:
            return jsonify({"success": False, "error": "Clé API manquante."})

        patient_info = data.get('patient_info','')
        ngs_result   = data.get('ngs_result', {})
        cnv_result   = data.get('cnv_result', {})
        fusion_result= data.get('fusion_result',{})
        sig_result   = data.get('sig_result',  {})

        import json as _json, anthropic as _anth

        context_parts = []
        if patient_info: context_parts.append("PATIENT: " + patient_info)
        if ngs_result:   context_parts.append("NGS/VARIANTS: " + _json.dumps(ngs_result, ensure_ascii=False)[:3000])
        if cnv_result:   context_parts.append("CNV: " + _json.dumps(cnv_result, ensure_ascii=False)[:2000])
        if fusion_result:context_parts.append("FUSIONS: " + _json.dumps(fusion_result, ensure_ascii=False)[:2000])
        if sig_result:   context_parts.append("SIGNATURES: " + _json.dumps(sig_result, ensure_ascii=False)[:2000])

        system_prompt = """Tu es un expert en oncologie moléculaire de niveau international, specialiste des tumeur boards multidisciplinaires (RCP/MTB).
Tu synthétises des données multi-omiques complexes en une décision thérapeutique cliniquement actionnables.
Réponds UNIQUEMENT en JSON valide strict.

Format de réponse:
{
  "patient_summary": "Résumé patient en 2-3 phrases",
  "genomic_complexity": "Faible|Modérée|Élevée|Très élevée",
  "key_findings": [
    {"finding": "ERBB2 amplifié CN=12", "significance": "Cible thérapeutique Tier I", "urgency": "haute"}
  ],
  "therapeutic_priorities": [
    {
      "rank": 1,
      "therapy": "Alectinib 600mg BID",
      "rationale": "EML4-ALK Tier I, VAF 22%, FISH positif",
      "evidence_level": "IA",
      "biomarker": "EML4-ALK fusion",
      "expected_response": "70-80% PFS 2 ans",
      "contraindications": []
    }
  ],
  "clinical_trials": ["NCT03052608 — ALEX trial ALK+"],
  "molecular_profiling_gaps": ["Test BRCA germinal recommandé", "PD-L1 IHC requis"],
  "rcp_recommendation": "Texte de recommandation RCP complète en 5-8 phrases, prête à être lue en réunion",
  "follow_up": ["Biopsie liquidienne J90", "IRM cérébrale J30"],
  "prognosis": "Pronostic estimé avec thérapie optimale",
  "urgent_actions": ["Action urgente 1 à faire dans 48h"],
  "genetic_counseling": true,
  "urgent": false,
  "urgent_reason": ""
}"""

        user_msg = "Synthétise ces données multi-omiques pour le tumeur board:\n\n" + "\n\n".join(context_parts)

        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role":"user","content":user_msg}]
        )
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = _json.loads(raw)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        import logging; logging.error(f"tumor_board error: {e}")
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════
# DASHBOARD PATIENTS
# ════════════════════════════════════════════════════════
@app.route('/dashboard/patients')
def patients_dashboard():
    if not session.get('authenticated'):
        from flask import redirect
        return redirect('/login')
    return render_template('patients_dashboard.html')

@app.route('/dashboard/patient/<patient_id>')
def patient_detail_dashboard(patient_id):
    if not session.get('authenticated'):
        from flask import redirect
        return redirect('/login')
    return render_template('patient_detail.html', patient_id=patient_id)

@app.route('/api/patients/<patient_id>', methods=['GET'])
def api_get_patient(patient_id):
    try:
        from supabase_client import get_supabase
        if not session.get('user_id'):
            return jsonify({"success": False, "error": "Non authentifie"}), 401
        sb = get_supabase()
        res = sb.table('patients').select('*').eq('id', patient_id).execute()
        if not res.data:
            return jsonify({"success": False, "error": "Patient non trouve"})
        analyses = sb.table('analyses').select('*').eq('patient_id', patient_id).order('created_at', desc=True).execute()
        return jsonify({"success": True, "patient": res.data[0], "analyses": analyses.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/patients/<patient_id>', methods=['PUT'])
def api_update_patient(patient_id):
    try:
        from supabase_client import get_supabase
        if not session.get('user_id'):
            return jsonify({"success": False, "error": "Non authentifie"}), 401
        data = request.json or {}
        sb = get_supabase()
        allowed = ['first_name','last_name','cancer_type','stage','notes','sex','date_of_birth']
        update = {k: data[k] for k in allowed if k in data}
        res = sb.table('patients').update(update).eq('id', patient_id).execute()
        return jsonify({"success": True, "patient": res.data[0] if res.data else {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/patients/<patient_id>', methods=['DELETE'])
def api_delete_patient(patient_id):
    try:
        from supabase_client import get_supabase
        if not session.get('user_id'):
            return jsonify({"success": False, "error": "Non authentifie"}), 401
        sb = get_supabase()
        sb.table('analyses').delete().eq('patient_id', patient_id).execute()
        sb.table('patients').delete().eq('id', patient_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════
# PDF CLINIQUE AVANCÉ — avec QR code, en-tête institution
# ════════════════════════════════════════════════════════
@app.route('/generate_clinical_pdf', methods=['POST'])
def generate_clinical_pdf():
    try:
        import io, qrcode
        from datetime import datetime
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
        from reportlab.pdfgen import canvas as rl_canvas

        data = request.json or {}
        patient     = data.get('patient', {})
        analyses    = data.get('analyses', [])
        institution = data.get('institution', 'SenGenoScope — Oncogénomique Clinique')
        physician   = data.get('physician', session.get('user_name', 'Médecin traitant'))
        report_id   = data.get('report_id', f"SGS-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2.5*cm, bottomMargin=2.5*cm)

        # Styles
        teal   = colors.HexColor('#0d9488')
        navy   = colors.HexColor('#1e3a5f')
        gray   = colors.HexColor('#64748b')
        red    = colors.HexColor('#dc2626')
        orange = colors.HexColor('#ea580c')
        light  = colors.HexColor('#f8fafc')

        h1 = ParagraphStyle('h1', fontSize=18, fontName='Helvetica-Bold', textColor=navy, spaceAfter=4)
        h2 = ParagraphStyle('h2', fontSize=13, fontName='Helvetica-Bold', textColor=teal, spaceAfter=6, spaceBefore=12)
        h3 = ParagraphStyle('h3', fontSize=11, fontName='Helvetica-Bold', textColor=navy, spaceAfter=4)
        body = ParagraphStyle('body', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#374151'), spaceAfter=4, leading=14)
        small = ParagraphStyle('small', fontSize=8, fontName='Helvetica', textColor=gray, spaceAfter=2)
        center = ParagraphStyle('center', fontSize=9, fontName='Helvetica', alignment=TA_CENTER, textColor=gray)
        bold_body = ParagraphStyle('bold_body', fontSize=9, fontName='Helvetica-Bold', textColor=navy, spaceAfter=4)

        story = []

        # ── EN-TÊTE ──
        header_data = [[
            Paragraph(f"<b>{institution}</b>", ParagraphStyle('inst', fontSize=11, fontName='Helvetica-Bold', textColor=navy)),
            Paragraph(f"<b>RAPPORT GÉNOMIQUE CLINIQUE</b><br/><font size=8 color='#64748b'>Confidentiel — Usage médical exclusif</font>",
                ParagraphStyle('rtype', fontSize=11, fontName='Helvetica-Bold', textColor=teal, alignment=TA_RIGHT))
        ]]
        header_table = Table(header_data, colWidths=[9*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,0), 1.5, teal),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.4*cm))

        # ── INFOS RAPPORT ──
        now_str = datetime.now().strftime('%d/%m/%Y à %H:%M')
        info_data = [
            ['N° Rapport', report_id, 'Date', now_str],
            ['Médecin', physician, 'Patient', patient.get('patient_code', '—')],
        ]
        info_table = Table(info_data, colWidths=[3*cm, 7*cm, 2.5*cm, 4.5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('TEXTCOLOR', (0,0), (0,-1), gray),
            ('TEXTCOLOR', (2,0), (2,-1), gray),
            ('BACKGROUND', (0,0), (-1,-1), light),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [light, colors.white]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*cm))

        # ── INFOS PATIENT ──
        if patient:
            story.append(Paragraph("Informations patient", h2))
            name = ' '.join(filter(None, [patient.get('first_name',''), patient.get('last_name','')])) or 'Anonyme'
            pat_data = [
                ['Nom', name, 'Sexe', patient.get('sex','—')],
                ['Cancer', patient.get('cancer_type','—'), 'Stade', patient.get('stage','—')],
                ['Code', patient.get('patient_code','—'), 'Notes', (patient.get('notes','—') or '—')[:60]],
            ]
            pat_table = Table(pat_data, colWidths=[2.5*cm, 6.5*cm, 2.5*cm, 5.5*cm])
            pat_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('TEXTCOLOR', (0,0), (0,-1), gray),
                ('TEXTCOLOR', (2,0), (2,-1), gray),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [light, colors.white]),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
            ]))
            story.append(pat_table)
            story.append(Spacer(1, 0.3*cm))

        # ── ANALYSES ──
        import json as _json
        type_labels = {'ngs':'Variants NGS / ACMG','cnv':'CNV — Amplifications & Délétions',
                       'fusions':'Fusions Géniques','signatures':'Signatures Mutationnelles COSMIC','mtb':'Tumeur Board IA — Décision RCP'}
        type_colors = {'ngs':teal,'cnv':colors.HexColor('#7c3aed'),'fusions':colors.HexColor('#2563eb'),
                       'signatures':colors.HexColor('#059669'),'mtb':navy}

        for analysis in analyses:
            atype = analysis.get('analysis_type','ngs')
            label = type_labels.get(atype, atype.upper())
            col   = type_colors.get(atype, teal)
            result = analysis.get('result', {})
            if isinstance(result, str):
                try: result = _json.loads(result)
                except: result = {}

            story.append(HRFlowable(width="100%", thickness=1, color=col))
            story.append(Paragraph(label, h2))

            # Contexte
            if analysis.get('context'):
                story.append(Paragraph(f"<b>Contexte:</b> {analysis['context']}", body))

            # Résumé
            summary = result.get('summary') or result.get('patient_summary') or ''
            if summary:
                story.append(Paragraph(f"<b>Résumé clinique:</b> {summary}", body))

            # Alerte urgente
            if result.get('urgent') and result.get('urgent_reason'):
                urgent_data = [[Paragraph(f"⚠️ ALERTE: {result['urgent_reason']}", ParagraphStyle('urg', fontSize=9, fontName='Helvetica-Bold', textColor=red))]]
                urgent_table = Table(urgent_data, colWidths=[17*cm])
                urgent_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fecaca')),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('LEFTPADDING', (0,0), (-1,-1), 10),
                ]))
                story.append(urgent_table)
                story.append(Spacer(1, 0.2*cm))

            # Variants NGS
            if atype == 'ngs' and result.get('variants'):
                variants = result['variants'][:8]
                v_data = [['Gène', 'Variant', 'Classification', 'VAF', 'Profondeur']]
                for v in variants:
                    acmg = v.get('acmg_classification','—')
                    acmg_col = red if 'Pathog' in acmg else orange if 'Probable' in acmg else gray
                    v_data.append([
                        Paragraph(f"<b>{v.get('gene','—')}</b>", ParagraphStyle('g', fontSize=8, fontName='Helvetica-Bold', textColor=navy)),
                        Paragraph(v.get('hgvsc','—') or '—', ParagraphStyle('hg', fontSize=7, fontName='Helvetica', textColor=gray)),
                        Paragraph(acmg, ParagraphStyle('ac', fontSize=8, fontName='Helvetica-Bold', textColor=acmg_col)),
                        str(v.get('vaf','—')),
                        str(v.get('depth','—'))
                    ])
                v_table = Table(v_data, colWidths=[2.5*cm,5*cm,4*cm,2.5*cm,3*cm])
                v_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), teal),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [light, colors.white]),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                    ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
                ]))
                story.append(v_table)
                story.append(Spacer(1, 0.2*cm))

            # CNV
            if atype == 'cnv' and result.get('cnvs'):
                cnvs = result['cnvs'][:6]
                c_data = [['Gène', 'Chr', 'Type', 'CN', 'Log2', 'Action']]
                for c in cnvs:
                    c_data.append([
                        Paragraph(f"<b>{c.get('gene','—')}</b>", ParagraphStyle('cg', fontSize=8, fontName='Helvetica-Bold', textColor=navy)),
                        c.get('chromosome','—'),
                        Paragraph(c.get('type','—'), ParagraphStyle('ct', fontSize=8, fontName='Helvetica', textColor=red if 'amp' in str(c.get('type','')).lower() else orange)),
                        str(c.get('copy_number','—')),
                        str(c.get('log2_ratio','—')),
                        Paragraph((c.get('action','—') or '—')[:50], ParagraphStyle('ca', fontSize=7, fontName='Helvetica', textColor=teal)),
                    ])
                c_table = Table(c_data, colWidths=[2.5*cm,2.5*cm,3*cm,1.5*cm,1.5*cm,6*cm])
                c_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7c3aed')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [light, colors.white]),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                    ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
                ]))
                story.append(c_table)
                story.append(Spacer(1, 0.2*cm))

            # MTB / RCP
            if atype == 'mtb':
                if result.get('rcp_recommendation'):
                    rcp_data = [[Paragraph(f"<b>RECOMMANDATION RCP:</b><br/>{result['rcp_recommendation']}",
                        ParagraphStyle('rcp', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#166534'), leading=14))]]
                    rcp_table = Table(rcp_data, colWidths=[17*cm])
                    rcp_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
                        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bbf7d0')),
                        ('TOPPADDING', (0,0), (-1,-1), 10),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                        ('LEFTPADDING', (0,0), (-1,-1), 12),
                    ]))
                    story.append(rcp_table)
                    story.append(Spacer(1, 0.2*cm))
                if result.get('therapeutic_priorities'):
                    story.append(Paragraph("Priorités thérapeutiques", h3))
                    for t in result['therapeutic_priorities'][:4]:
                        story.append(Paragraph(f"<b>#{t.get('rank','')} {t.get('therapy','')}</b> — {t.get('rationale','')} [Niveau {t.get('evidence_level','')}]", body))

            # Recommandations
            recs = result.get('recommendations', [])
            if recs:
                story.append(Paragraph("Recommandations", h3))
                for i, r in enumerate(recs[:6], 1):
                    story.append(Paragraph(f"{i}. {r}", body))

            story.append(Spacer(1, 0.3*cm))

        # ── QR CODE ──
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 0.3*cm))

        try:
            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr_data = f"SenGenoScope|{report_id}|{patient.get('patient_code','—')}|{now_str}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color='#0d9488', back_color='white')
            qr_buf = io.BytesIO()
            qr_img.save(qr_buf, format='PNG')
            qr_buf.seek(0)
            qr_rl = RLImage(qr_buf, width=2.5*cm, height=2.5*cm)

            footer_data = [[
                qr_rl,
                Paragraph(
                    f"<b>SenGenoScope v1.0</b> — Plateforme d'Oncogénomique Clinique<br/>"
                    f"Rapport N° {report_id} — Généré le {now_str}<br/>"
                    f"<font color='#dc2626'><b>CONFIDENTIEL — Usage clinique exclusif</b></font><br/>"
                    f"<font size=7 color='#94a3b8'>Ce rapport est généré par IA et doit être validé par un professionnel de santé qualifié</font>",
                    ParagraphStyle('footer', fontSize=8, fontName='Helvetica', textColor=gray, leading=12))
            ]]
            footer_table = Table(footer_data, colWidths=[3*cm, 14*cm])
            footer_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(footer_table)
        except Exception:
            story.append(Paragraph(
                f"SenGenoScope v1.0 — Rapport {report_id} — {now_str} — CONFIDENTIEL",
                center))

        doc.build(story)
        buf.seek(0)
        from flask import send_file
        fname = f"rapport_SGS_{patient.get('patient_code','patient')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=fname)

    except Exception as e:
        import logging; logging.error(f"generate_clinical_pdf error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ════════════════════════════════════════════════════════
# COMPARATEUR THÉRAPEUTIQUE IA
# ════════════════════════════════════════════════════════
@app.route('/compare_therapeutics', methods=['POST'])
def compare_therapeutics():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key','') or data.get('user_api_key','')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY','')
        if not api_key:
            return jsonify({"success": False, "error": "Cle API manquante."})

        genomic_profile = data.get('genomic_profile','').strip()
        cancer_type     = data.get('cancer_type','').strip()
        context         = data.get('context','').strip()

        if not genomic_profile:
            return jsonify({"success": False, "error": "Profil genomique manquant."})

        import anthropic as _anth, json as _json
        system_prompt = """Tu es expert en oncologie de precision et pharmacogenomique clinique.
Compare les options therapeutiques disponibles pour ce profil genomique.
Reponds UNIQUEMENT en JSON valide strict.

Format:
{
  "therapies": [
    {
      "rank": 1,
      "name": "Olaparib (Lynparza)",
      "class": "Inhibiteur PARP",
      "biomarker": "BRCA1 c.5266dupC pathogene",
      "evidence_level": "IA",
      "indication": "Cancer du sein HER2- avec mutation BRCA germinale",
      "response_rate": "60%",
      "pfs_median": "7.0 mois vs 4.2 (HR 0.58)",
      "os_benefit": "Oui — OS superieur vs chimiotherapie",
      "side_effects": ["Nausees", "Anemie", "Fatigue"],
      "contraindications": ["Insuffisance renale severe"],
      "clinical_trial": "NCT01064102 — OlympiAD",
      "guideline": "ESMO 2023 — Recommandation Grade A",
      "availability": "AMM Europe — remboursable",
      "score": 95
    }
  ],
  "comparison_summary": "Resume comparatif en 3-4 phrases",
  "best_option": "Nom de la meilleure option",
  "best_rationale": "Pourquoi cette option est prioritaire",
  "combination_options": ["Option combinaison 1"],
  "resistance_mechanisms": ["Mecanisme de resistance possible"],
  "monitoring": ["Bilan J0: HNF, NFS, creatinine", "IRM J90"],
  "genetic_counseling_needed": true
}"""

        user_msg = f"Profil genomique: {genomic_profile}"
        if cancer_type: user_msg += f"\nType de cancer: {cancer_type}"
        if context: user_msg += f"\nContexte: {context}"

        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role":"user","content":user_msg}]
        )
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = _json.loads(raw)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        import logging; logging.error(f"compare_therapeutics error: {e}")
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════
# SCORE HRD AVANCÉ (LOH + TAI + LST)
# ════════════════════════════════════════════════════════
@app.route('/calculate_hrd', methods=['POST'])
def calculate_hrd():
    try:
        data = request.json or {}
        user_api_key = (request.headers.get('X-User-Api-Key','') or data.get('user_api_key','')).strip()
        api_key = user_api_key or os.environ.get('ANTHROPIC_API_KEY','')
        if not api_key:
            return jsonify({"success": False, "error": "Cle API manquante."})

        cnv_data  = data.get('cnv_data','').strip()
        context   = data.get('context','').strip()

        if not cnv_data:
            return jsonify({"success": False, "error": "Donnees CNV manquantes."})

        import anthropic as _anth, json as _json
        system_prompt = """Tu es expert en instabilite genomique et score HRD (Homologous Recombination Deficiency).
Calcule le score HRD complet depuis les donnees CNV fournies.
Reponds UNIQUEMENT en JSON valide strict.

Format:
{
  "loh_score": 18,
  "tai_score": 12,
  "lst_score": 15,
  "hrd_total": 45,
  "hrd_status": "Positif",
  "hrd_threshold": 42,
  "interpretation": "HRD positif (score 45 > seuil 42) — deficit de reparation homologue probable",
  "brca_like": true,
  "parp_eligibility": "Eligible",
  "parp_drugs": ["Olaparib", "Niraparib", "Rucaparib"],
  "platinum_sensitivity": "Haute",
  "confidence": "Moderee",
  "loh_details": "18 regions LOH detectees (seuil: 15)",
  "tai_details": "12 transitions allele-specifiques (seuil: 11)",
  "lst_details": "15 transitions large-scale (seuil: 10)",
  "genomic_instability": "Elevee",
  "recommendations": [
    "Eligibilite inhibiteurs PARP confirmee (score HRD 45)",
    "Test BRCA germinal complementaire recommande",
    "Chimiotherapie a base de platine en premiere intention"
  ],
  "caveats": "Score calcule par IA depuis donnees CNV — validation bioinformatique recommandee"
}"""

        user_msg = "Calcule le score HRD depuis ces donnees CNV:\n\n" + cnv_data
        if context: user_msg += "\n\nContexte: " + context

        client = _anth.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role":"user","content":user_msg}]
        )
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = _json.loads(raw)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        import logging; logging.error(f"calculate_hrd error: {e}")
        return jsonify({"success": False, "error": str(e)})


# ════════════════════════════════════════════
# PAGES ERREUR + ONBOARDING
# ════════════════════════════════════════════
@app.errorhandler(404)
def error_404(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_500(e):
    return render_template('500.html'), 500

@app.route('/onboarding')
def onboarding():
    if not session.get('authenticated'):
        return redirect('/login')
    return render_template('onboarding.html')

# ══ TRAJECTOIRE DE SOIN — ANALYSES PATIENT ════════════════════════════════════

@app.route('/patients/<int:pid>/analyses', methods=['GET'])
@login_required
def get_patient_analyses(pid):
    uid = session['user_id']
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        # Vérifier accès patient
        cur.execute(f"SELECT id,nom,prenom,diagnostic,numero_dossier,date_naissance,notes,created_at FROM patients WHERE id={ph} AND user_id={ph}", (pid, uid))
        p = cur.fetchone()
        if not p:
            return jsonify({"success": False, "error": "Patient non trouvé"})
        # Récupérer analyses
        cur.execute(f"SELECT id,type_analyse,titre,resume,resultat,classification,created_at FROM patient_analyses WHERE patient_id={ph} AND user_id={ph} ORDER BY created_at ASC", (pid, uid))
        analyses = [{"id":r[0],"type":r[1],"titre":r[2],"resume":r[3],"resultat":r[4],"classification":r[5],"created_at":str(r[6])} for r in cur.fetchall()]
        # Récupérer consultations liées
        cur.execute(f"SELECT id,clinician_name,clinician_specialty,title,updated_at FROM consultations WHERE patient_id={ph} AND user_id={ph} ORDER BY updated_at ASC", (pid, uid))
        consults = [{"id":c[0],"type":"consultation","titre":c[3],"clinician":c[1],"specialty":c[2],"created_at":str(c[4])} for c in cur.fetchall()]
        conn.close()
        return jsonify({
            "success": True,
            "patient": {"id":p[0],"nom":p[1],"prenom":p[2],"diagnostic":p[3],"numero_dossier":p[4],"date_naissance":p[5],"notes":p[6],"created_at":str(p[7])},
            "analyses": analyses,
            "consultations": consults
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/<int:pid>/analyses', methods=['POST'])
@login_required
def save_patient_analyse(pid):
    uid = session['user_id']
    data = request.json or {}
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        cur.execute(f"SELECT id FROM patients WHERE id={ph} AND user_id={ph}", (pid, uid))
        if not cur.fetchone():
            return jsonify({"success": False, "error": "Patient non trouvé"})
        cur.execute(
            f"INSERT INTO patient_analyses (patient_id,user_id,type_analyse,titre,resume,resultat,classification) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
            (pid, uid, data.get('type_analyse','NGS'), data.get('titre',''), data.get('resume',''), data.get('resultat',''), data.get('classification',''))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/<int:pid>/analyses/<int:aid>', methods=['PUT'])
@login_required
def update_patient_analyse(pid, aid):
    uid = session['user_id']
    data = request.json or {}
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        cur.execute(
            f"UPDATE patient_analyses SET type_analyse={ph},titre={ph},resume={ph},classification={ph} WHERE id={ph} AND patient_id={ph} AND user_id={ph}",
            (data.get('type_analyse',''), data.get('titre',''), data.get('resume',''), data.get('classification',''), aid, pid, uid)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/patients/<int:pid>/analyses/<int:aid>', methods=['DELETE'])
@login_required
def delete_patient_analyse(pid, aid):
    uid = session['user_id']
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"
    try:
        cur.execute(f"DELETE FROM patient_analyses WHERE id={ph} AND patient_id={ph} AND user_id={ph}", (aid, pid, uid))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ══ RAPPORT PDF TRAJECTOIRE DE SOIN ══════════════════════════════════════════

@app.route('/patients/<int:pid>/pdf')
@login_required
def generate_trajectory_pdf(pid):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import io
    from datetime import datetime

    uid = session['user_id']
    user_name = session.get('user_name', '')
    user_institution = session.get('user_institution', '')
    conn, _db = get_conn()
    cur = conn.cursor()
    ph = "%s" if _db == "pg" else "?"

    try:
        # Récupérer patient
        cur.execute(f"SELECT id,nom,prenom,date_naissance,numero_dossier,diagnostic,notes,created_at FROM patients WHERE id={ph} AND user_id={ph}", (pid, uid))
        p = cur.fetchone()
        if not p:
            return "Patient non trouvé", 404

        # Récupérer analyses
        cur.execute(f"SELECT type_analyse,titre,resume,classification,created_at FROM patient_analyses WHERE patient_id={ph} AND user_id={ph} ORDER BY created_at ASC", (pid, uid))
        analyses = cur.fetchall()

        # Récupérer consultations
        cur.execute(f"SELECT clinician_name,clinician_specialty,title,updated_at FROM consultations WHERE patient_id={ph} AND user_id={ph} ORDER BY updated_at ASC", (pid, uid))
        consults = cur.fetchall()
        conn.close()

        # Fusionner et trier
        events = []
        for a in analyses:
            events.append({'type': a[0], 'titre': a[1], 'resume': a[2] or '', 'classification': a[3] or '', 'date': str(a[4])[:10], 'cat': 'analyse'})
        for c in consults:
            events.append({'type': 'Consultation', 'titre': c[2] or f'Consultation {c[0]}', 'resume': f'Clinicien: {c[0]} ({c[1]})', 'classification': '', 'date': str(c[3])[:10], 'cat': 'consultation'})
        events.sort(key=lambda x: x['date'])

        # Créer le PDF en mémoire
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()

        # Styles personnalisés
        title_style = ParagraphStyle('Title', parent=styles['Normal'],
            fontSize=20, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d9488'),
            spaceAfter=4, alignment=TA_CENTER)
        subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
            fontSize=11, fontName='Helvetica', textColor=colors.HexColor('#6b7280'),
            spaceAfter=2, alignment=TA_CENTER)
        section_style = ParagraphStyle('Section', parent=styles['Normal'],
            fontSize=13, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d9488'),
            spaceBefore=16, spaceAfter=8, borderPad=4)
        body_style = ParagraphStyle('Body', parent=styles['Normal'],
            fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#1f2937'),
            leading=14, spaceAfter=4)
        small_style = ParagraphStyle('Small', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#6b7280'),
            spaceAfter=2)
        event_title_style = ParagraphStyle('EvTitle', parent=styles['Normal'],
            fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#111827'),
            spaceAfter=3)

        CLASSIF_COLORS = {
            'Pathogène': '#dc2626', 'Probablement pathogène': '#ea580c',
            'VUS': '#ca8a04', 'Probablement bénin': '#16a34a', 'Bénin': '#15803d',
            'Traitement initié': '#0891b2', 'Réponse partielle': '#7c3aed',
            'Réponse complète': '#059669', 'Progression': '#dc2626', 'Stable': '#6b7280'
        }

        story = []

        # ── EN-TÊTE ──────────────────────────────────────────────
        story.append(Paragraph('SenGenoScope', title_style))
        story.append(Paragraph('Plateforme d\'oncogenomique et oncopharmacogenomique clinique', subtitle_style))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#0d9488')))
        story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph('RAPPORT DE TRAJECTOIRE DE SOIN', ParagraphStyle('RTitle',
            parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#111827'), alignment=TA_CENTER, spaceAfter=4)))
        story.append(Paragraph(f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} par {user_name}',
            ParagraphStyle('Gen', parent=styles['Normal'], fontSize=9,
            textColor=colors.HexColor('#9ca3af'), alignment=TA_CENTER, spaceAfter=4)))
        if user_institution:
            story.append(Paragraph(user_institution, ParagraphStyle('Inst', parent=styles['Normal'],
                fontSize=9, textColor=colors.HexColor('#9ca3af'), alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5*cm))

        # ── FICHE PATIENT ──────────────────────────────────────
        story.append(Paragraph('INFORMATIONS PATIENT', section_style))
        patient_data = [
            ['Nom', f"{p[1]} {p[2] or ''}".strip(), 'N° Dossier', p[4] or 'N/A'],
            ['Date de naissance', p[3] or 'N/A', 'Diagnostic', p[5] or 'N/A'],
            ['Suivi depuis', str(p[7])[:10], 'Nb événements', str(len(events))],
        ]
        if p[6]:
            patient_data.append(['Notes', p[6], '', ''])

        pt = Table(patient_data, colWidths=[3.5*cm, 6.5*cm, 3.5*cm, 3.5*cm])
        pt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0fdfa')),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f0fdfa')),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#0d9488')),
            ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#0d9488')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f9fafb')]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(pt)
        story.append(Spacer(1, 0.5*cm))

        # ── RÉSUMÉ STATISTIQUE ─────────────────────────────────
        story.append(Paragraph('RÉSUMÉ', section_style))
        nb_analyses = len(analyses)
        nb_consults = len(consults)
        nb_patho = sum(1 for e in events if e['classification'] in ['Pathogène','Probablement pathogène'])
        jours = 0
        if len(events) > 1:
            try:
                d1 = datetime.strptime(events[0]['date'], '%Y-%m-%d')
                d2 = datetime.strptime(events[-1]['date'], '%Y-%m-%d')
                jours = (d2-d1).days
            except: pass

        stats_data = [['Analyses genomiques', 'Consultations IA', 'Variants patho.', 'Duree suivi'],
                      [str(nb_analyses), str(nb_consults), str(nb_patho), f'{jours} jours']]
        st = Table(stats_data, colWidths=[4.25*cm]*4)
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d9488')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('FONTSIZE', (0,1), (-1,1), 16),
            ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor('#0d9488')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWHEIGHTS', (0,0), (-1,-1), [0.7*cm, 1.2*cm]),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.5*cm))

        # ── TIMELINE ──────────────────────────────────────────
        story.append(Paragraph('CHRONOLOGIE DES EVENEMENTS', section_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 0.2*cm))

        if not events:
            story.append(Paragraph('Aucun événement enregistré.', small_style))
        else:
            for i, ev in enumerate(events):
                classif_color = colors.HexColor(CLASSIF_COLORS.get(ev['classification'], '#6b7280'))
                is_consult = ev['cat'] == 'consultation'
                dot_color = colors.HexColor('#7c3aed') if is_consult else classif_color

                # Ligne de timeline
                row_data = [[
                    Paragraph(f"<b>{ev['date']}</b>", ParagraphStyle('D', parent=styles['Normal'],
                        fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#6b7280'))),
                    Paragraph(f"<b>{ev['type']}</b>", ParagraphStyle('T', parent=styles['Normal'],
                        fontSize=9, fontName='Helvetica-Bold', textColor=dot_color)),
                    Paragraph(ev['classification'] or ('Consultation IA' if is_consult else '—'),
                        ParagraphStyle('C', parent=styles['Normal'], fontSize=9,
                        textColor=classif_color if ev['classification'] else colors.HexColor('#9ca3af'))),
                ]]
                header_t = Table(row_data, colWidths=[3*cm, 4*cm, 6*cm])
                header_t.setStyle(TableStyle([
                    ('PADDING', (0,0), (-1,-1), 2),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LINEBELOW', (0,0), (-1,-1), 0, colors.white),
                ]))
                story.append(header_t)

                story.append(Paragraph(ev['titre'], event_title_style))
                if ev['resume']:
                    story.append(Paragraph(ev['resume'], body_style))

                if i < len(events)-1:
                    story.append(HRFlowable(width='100%', thickness=0.3,
                        color=colors.HexColor('#e5e7eb'), spaceAfter=8))
                story.append(Spacer(1, 0.2*cm))

        # ── PIED DE PAGE ──────────────────────────────────────
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f'Document confidentiel — SenGenoScope v1.0 — Usage clinique exclusif — {datetime.now().strftime("%d/%m/%Y")}',
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8,
            textColor=colors.HexColor('#9ca3af'), alignment=TA_CENTER)))

        doc.build(story)
        buf.seek(0)

        nom_patient = f"{p[1]}_{p[2] or ''}".strip('_').replace(' ', '_')
        from flask import send_file
        return send_file(buf, mimetype='application/pdf',
            as_attachment=True,
            download_name=f"trajectoire_{nom_patient}_{datetime.now().strftime('%Y%m%d')}.pdf")

    except Exception as e:
        import traceback
        return f"Erreur PDF: {str(e)}\n{traceback.format_exc()}", 500

# force redeploy dim. 12 avr. 2026 10:28:05 EDT

# redeploy-1776005080
# redeploy-1776007524
