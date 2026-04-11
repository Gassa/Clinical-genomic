"""
app.py — SenGenoScope v1.0
Flask backend complet — sans clé API Claude requise
"""
import logging
from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for

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

