"""
app.py — SenGenoScope v1.0
Flask backend complet — sans clé API Claude requise
"""
from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for
import os, secrets
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
from pdf_report import generate_pdf_report
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
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
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


def log_login(user_id, name, email, ip):
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
    return hashlib.sha256(pwd.encode()).hexdigest()

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
    return row

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
            result = analyze_uploaded_file(filename, b64_content, "pdf_b64", question)
        else:
            # Fichier texte
            try:
                content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content = file_content.decode('latin-1', errors='replace')

            result = analyze_uploaded_file(filename, content, ext, question)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ── Chat médical Claude AI ────────────────────────────────────────────────────
@app.route("/ai/chat", methods=["POST"])
def ai_chat():
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

    result = clinical_chat(_chat_history, message, context)

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

    result = synthesize_pubmed_results(
        query=_last_result.get("query", ""),
        articles=_last_result.get("articles", []),
        genes=list(_last_result.get("gene_data", {}).get("frequency", {}).keys())
    )
    return jsonify(result)

# ── Rapport clinique ACMG par Claude AI ──────────────────────────────────────
@app.route("/ai/clinical_report", methods=["POST"])
def ai_clinical_report():
    """Génère un rapport clinique ACMG structuré par Claude AI."""
    data = request.get_json()
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
    gene = data.get("gene", "").strip()
    variant = data.get("variant", "").strip()
    drug = data.get("drug", "").strip()
    if not gene:
        return jsonify({"error": "Gène requis"}), 400
    result = pharmacogenomics_analysis(gene, variant, drug)
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

@app.route("/clinicians", methods=["GET"])
def get_clinicians():
    try:
        from virtual_clinicians import get_all_clinicians
        data = get_all_clinicians()
        if not isinstance(data, list):
            return jsonify([]), 200
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clinicians/test", methods=["GET"])
def test_clinicians():
    try:
        from virtual_clinicians import get_all_clinicians, CLINICIANS
        return jsonify({"ok": True, "count": len(CLINICIANS), "ids": [c["id"] for c in CLINICIANS]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/clinicians/chat", methods=["POST"])
def clinician_chat():
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


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
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': content}]
        )
        text = resp.content[0].text.strip().replace('```json','').replace('```','').strip()
        import json as _json
        parsed = _json.loads(text)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

