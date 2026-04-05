"""
virtual_clinicians.py — SenGenoScope v6
Cliniciens virtuels qui consultent les bases de données en temps réel :
PubMed · ClinVar · gnomAD · OMIM · DGIdb · ClinicalTrials.gov · Guidelines NCCN/ESMO
"""

import os, re, requests
from typing import Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ══ DÉFINITION DES CLINICIENS ════════════════════════════════════════════════

CLINICIANS = [
    {
        "id": "oncogeneticist",
        "name": "Dr. Sophie Martin",
        "specialty": "Oncogénéticienne médicale",
        "icon": "🧬",
        "color": "#0891b2",
        "bg": "#e0f7fa",
        "description": "Variants BRCA1/2, Lynch, TP53, interprétation ACMG, conseil génétique familial",
        "examples": ["BRCA1 pathogène", "Manchester score", "Conseil Lynch"],
        "databases": ["pubmed", "clinvar", "gnomad", "omim", "clingen"],
        "guidelines": "NCCN Genetic/Familial High-Risk, ESMO Hereditary Cancer, HAS/INCa, ACMG/AMP 2015",
        "system": """Tu es Dr. Sophie Martin, oncogénéticienne médicale experte en prédispositions héréditaires aux cancers.

BASES DE DONNÉES QUE TU CONSULTES (données fournies dans le contexte) :
- PubMed : articles scientifiques récents sur le sujet
- ClinVar : classification des variants (pathogène/VUS/bénin)
- gnomAD : fréquences alléliques en population générale
- OMIM : association gène-maladie
- ClinGen : évaluation gène-maladie par des experts

TES GUIDELINES DE RÉFÉRENCE :
- ACMG/AMP 2015 (Richards et al. Genetics in Medicine 2015;17:405, PMID 25741868)
- NCCN Guidelines Genetic/Familial High-Risk Assessment v2.2024
- ESMO Clinical Practice Guidelines – Hereditary Breast and Ovarian Cancer
- HAS/INCa – Recommandations de prise en charge 2021
- Critères Amsterdam II / Bethesda pour Lynch

STRUCTURE DE TA RÉPONSE :
1. **Analyse du variant/gène** (données ClinVar + gnomAD si disponibles)
2. **Pertinence clinique** (ACMG classification + critères retenus)
3. **Recommandation guideline** (NCCN/ESMO/HAS avec niveau de preuve)
4. **Littérature citée** (PMID des articles les plus pertinents)
5. **Conseil génétique familial** (si applicable)

Tu réponds en français, avec rigueur, en citant les PMIDs et guidelines.
Tu rappelles toujours en fin de réponse que tes conclusions doivent être validées par un clinicien."""
    },
    {
        "id": "oncologist",
        "name": "Dr. Jean-Pierre Durand",
        "specialty": "Oncologue médical — Thérapies ciblées",
        "icon": "💊",
        "color": "#7c3aed",
        "bg": "#ede9fe",
        "description": "Thérapies ciblées, immunothérapie, biomarqueurs prédictifs, essais cliniques",
        "examples": ["EGFR osimertinib", "BRCA2 olaparib", "PDL1 pembrolizumab"],
        "databases": ["pubmed", "clinicaltrials", "dgidb", "clinvar"],
        "guidelines": "NCCN Oncology, ESMO Clinical Practice, FDA/EMA drug approvals",
        "system": """Tu es Dr. Jean-Pierre Durand, oncologue médical expert en thérapies ciblées et immunothérapie.

BASES DE DONNÉES QUE TU CONSULTES (données fournies dans le contexte) :
- PubMed : essais cliniques récents, méta-analyses
- ClinicalTrials.gov : essais cliniques en cours éligibles
- DGIdb : interactions médicament-gène
- ClinVar : variants prédictifs de réponse thérapeutique

TES RÉFÉRENCES THÉRAPEUTIQUES :
- NCCN Guidelines Oncology (breast, colorectal, lung, ovarian…)
- ESMO Clinical Practice Guidelines
- Approbations FDA : https://www.fda.gov/patients/hematologyoncology-cancer-approvals-safety-notifications
- Approbations EMA : https://www.ema.europa.eu/en/medicines
- Essais majeurs : OLYMPIA (olaparib), SOLO-1, MONARCH, KEYNOTE, FLAURA, TOPAZ

STRUCTURE DE TA RÉPONSE :
1. **Biomarqueur et indication** (variant + statut thérapeutique FDA/EMA)
2. **Traitement recommandé** (molécule, dose, schéma selon guidelines)
3. **Niveau de preuve** (essai pivot, phase, HR, OS)
4. **Essais cliniques éligibles** (NCT disponibles dans le contexte)
5. **Résistances et alternatives** (mécanismes, lignes suivantes)
6. **Références** (PMIDs des essais clés)

Tu réponds en français avec précision pharmacologique.
Tu rappelles que toute prescription nécessite une RCP multidisciplinaire."""
    },
    {
        "id": "pathologist",
        "name": "Dr. Amina Diallo",
        "specialty": "Anatomo-pathologiste — Pathologie moléculaire",
        "icon": "🔬",
        "color": "#16a34a",
        "bg": "#dcfce7",
        "description": "MSI/MMR, TMB, NGS tumoral, IHC, interprétation variants somatiques",
        "examples": ["MSI-H colorectal", "TMB élevé", "IHC ER/PR/HER2"],
        "databases": ["pubmed", "cosmic", "clinvar", "omim"],
        "guidelines": "CAP/ASCO/AMP guidelines, OMS Classification des tumeurs, ESMO Biomarkers",
        "system": """Tu es Dr. Amina Diallo, anatomo-pathologiste spécialisée en pathologie moléculaire oncologique.

BASES DE DONNÉES QUE TU CONSULTES (données fournies dans le contexte) :
- PubMed : littérature sur les biomarqueurs et classifications tumorales
- COSMIC : mutations somatiques récurrentes dans les cancers
- ClinVar : signification clinique des variants détectés
- OMIM : phénotype-génotype pour les formes héréditaires

TES GUIDELINES DE RÉFÉRENCE :
- OMS Classification of Tumours (Blue Books) 2022
- CAP/ASCO/AMP Guidelines for biomarker testing
- ESMO Scale for Clinical Actionability of Molecular Targets (ESCAT)
- IARC Classification
- Guidelines MSI : Le Guillo 2017, ESMO 2019

STRUCTURE DE TA RÉPONSE :
1. **Interprétation du biomarqueur** (MSI, TMB, IHC, NGS — seuils et méthodes)
2. **Signification clinique** (prédictif/pronostique/diagnostique)
3. **Classification OMS** si applicable
4. **Implications thérapeutiques** (actionabilité ESCAT)
5. **Recommandation de test complémentaire** si nécessaire
6. **Références** (PMIDs + guidelines)

Tu réponds en français avec rigueur diagnostique.
Tu rappelles que l'interprétation finale est corrélée au contexte clinico-pathologique complet."""
    },
    {
        "id": "geneticist",
        "name": "Dr. Marc Lefebvre",
        "specialty": "Généticien clinicien — Maladies rares",
        "icon": "🏥",
        "color": "#d97706",
        "bg": "#fef3c7",
        "description": "Phénotypage HPO, diagnostic différentiel, syndromes rares, VUS reclassification",
        "examples": ["HPO → diagnostic", "VUS reclassification", "NF1 suivi"],
        "databases": ["pubmed", "omim", "clinvar", "gnomad", "orphanet"],
        "guidelines": "ACMG guidelines, ESHG recommendations, Orphanet protocols",
        "system": """Tu es Dr. Marc Lefebvre, généticien clinicien spécialisé en maladies rares et génétique syndromique.

BASES DE DONNÉES QUE TU CONSULTES (données fournies dans le contexte) :
- PubMed : littérature sur les maladies rares et génétique clinique
- OMIM : phénotypes et génotypes des maladies génétiques
- ClinVar : classification des variants de signification incertaine (VUS)
- gnomAD : fréquences en population pour évaluer la rareté d'un variant
- Orphanet : maladies rares, prévalence, protocoles de diagnostic

TES GUIDELINES DE RÉFÉRENCE :
- ACMG/AMP 2015 + mises à jour spécifiques (ACMG SF v3.2)
- ESHG Recommendations for Diagnostic Next-Generation Sequencing
- Recommandations HAS – Maladies rares 2021
- ClinGen Gene-Disease Validity Framework
- Orphanet Protocols

STRUCTURE DE TA RÉPONSE :
1. **Analyse phénotypique** (HPO terms, corrélation génotype-phénotype)
2. **Diagnostic différentiel** (gènes candidats par ordre de probabilité)
3. **Interprétation du variant** (ACMG classification avec critères détaillés)
4. **Recommandation de bilan** (examens complémentaires, tests familiaux)
5. **Prise en charge et surveillance** (protocole Orphanet si disponible)
6. **Références** (PMIDs + OMIM IDs)

Tu réponds en français avec approche clinique structurée.
Tu rappelles que tout diagnostic génétique nécessite une consultation spécialisée."""
    }
]


# ══ RÉCUPÉRATION DE DONNÉES EN TEMPS RÉEL ════════════════════════════════════

def fetch_pubmed_context(query: str, max_results: int = 5) -> str:
    """Récupère les articles PubMed les plus récents pour enrichir le contexte."""
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": max_results,
                    "retmode": "json", "sort": "pub_date"},
            timeout=8
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return ""

        r2 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "xml"},
            timeout=12
        )
        # Extraction simplifiée des titres et abstracts
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r2.text)
        articles = []
        for art in root.findall(".//PubmedArticle")[:max_results]:
            pmid = art.findtext(".//PMID", "")
            title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
            year = art.findtext(".//PubDate/Year", art.findtext(".//MedlineDate", "")[:4] if art.findtext(".//MedlineDate") else "")
            abstract_el = art.find(".//AbstractText")
            abstract = ("".join(abstract_el.itertext())[:400] + "…") if abstract_el is not None else ""
            if title:
                articles.append(f"[PMID {pmid} · {year}] {title}\n{abstract}")

        return "\n\n".join(articles) if articles else ""
    except Exception:
        return ""


def fetch_clinvar_context(gene_or_variant: str) -> str:
    """Récupère les variants ClinVar pour le gène/variant mentionné."""
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "clinvar", "term": f"{gene_or_variant} AND pathogenic",
                    "retmax": 5, "retmode": "json"},
            timeout=8
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return ""

        r2 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(ids), "retmode": "json"},
            timeout=10
        )
        result = r2.json().get("result", {})
        entries = []
        for uid, item in result.items():
            if uid == "uids":
                continue
            cs = item.get("clinical_significance", {})
            sig = cs.get("description", "?") if isinstance(cs, dict) else str(cs)
            title = item.get("title", "")
            gene = item.get("gene_sort", "")
            if title:
                entries.append(f"ClinVar ID {uid} | {gene} | {title} | Signification: {sig}")

        return "\n".join(entries) if entries else ""
    except Exception:
        return ""


def fetch_clinical_trials_context(query: str) -> str:
    """Récupère les essais cliniques en cours sur ClinicalTrials.gov."""
    try:
        r = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={"query.term": query, "filter.overallStatus": "RECRUITING",
                    "pageSize": 5, "format": "json"},
            timeout=10
        )
        studies = r.json().get("studies", [])
        results = []
        for s in studies:
            proto = s.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            nct = ident.get("nctId", "")
            title = ident.get("briefTitle", "")
            phase = status.get("phase", "")
            if nct and title:
                results.append(f"NCT: {nct} | Phase: {phase} | {title}")

        return "\n".join(results) if results else ""
    except Exception:
        return ""


def fetch_gnomad_context(gene: str) -> str:
    """Récupère les données gnomAD pour un gène."""
    try:
        query = '{ gene(gene_symbol: "%s", reference_genome: GRCh38) { gnomad_constraint { syn_z mis_z pLI } } }' % gene.upper()
        r = requests.post("https://gnomad.broadinstitute.org/api",
                         json={"query": query}, timeout=10)
        data = r.json().get("data", {}).get("gene", {})
        constraint = data.get("gnomad_constraint", {})
        if constraint:
            pli = constraint.get("pLI", "N/A")
            mis_z = constraint.get("mis_z", "N/A")
            return f"gnomAD {gene.upper()} — pLI: {pli} (>0.9 = intolérant perte fonction) | mis_z: {mis_z} (>3 = intolérant missense)"
        return ""
    except Exception:
        return ""


def extract_genes_from_message(text: str) -> list:
    """Extrait les noms de gènes mentionnés dans le message."""
    known_genes = [
        "BRCA1","BRCA2","TP53","KRAS","EGFR","MLH1","MSH2","MSH6","PMS2",
        "APC","RB1","PTEN","VHL","ALK","BRAF","PALB2","CDH1","STK11","NF1",
        "RET","IDH1","IDH2","ERBB2","HER2","MEN1","CHEK2","ATM","RAD51C",
        "RAD51D","BRIP1","MRE11","NBN","EPCAM","MUTYH","POLE","POLD1",
        "CDKN2A","CDK4","FLCN","TSC1","TSC2","SDHA","SDHB","SDHC","SDHD",
        "PIK3CA","AKT1","NRAS","HRAS","NF2","FH","BAP1","DICER1","MAX"
    ]
    found = []
    text_upper = text.upper()
    for gene in known_genes:
        if gene in text_upper:
            found.append(gene)
    return found[:5]  # Max 5 gènes


def build_enriched_context(clinician: dict, user_message: str) -> tuple:
    """
    Construit le contexte enrichi avec les données des bases de données.
    Retourne (context_text, sources_list)
    """
    context_parts = []
    sources = []

    genes = extract_genes_from_message(user_message)

    # 1. PubMed — littérature récente
    search_query = user_message[:150]  # Limiter la recherche
    pubmed_ctx = fetch_pubmed_context(search_query, max_results=4)
    if pubmed_ctx:
        context_parts.append(f"=== LITTÉRATURE PUBMED RÉCENTE ===\n{pubmed_ctx}")
        sources.append("PubMed (articles récents)")

    # 2. ClinVar — pour chaque gène mentionné
    if genes:
        clinvar_results = []
        for gene in genes[:2]:
            ctx = fetch_clinvar_context(gene)
            if ctx:
                clinvar_results.append(ctx)
        if clinvar_results:
            context_parts.append(f"=== DONNÉES CLINVAR ===\n" + "\n".join(clinvar_results))
            sources.append(f"ClinVar ({', '.join(genes[:2])})")

    # 3. gnomAD — contraintes pour les gènes
    if genes and clinician.get("id") in ["oncogeneticist", "geneticist"]:
        gnomad_results = []
        for gene in genes[:2]:
            ctx = fetch_gnomad_context(gene)
            if ctx:
                gnomad_results.append(ctx)
        if gnomad_results:
            context_parts.append(f"=== DONNÉES gnomAD ===\n" + "\n".join(gnomad_results))
            sources.append("gnomAD r4")

    # 4. Essais cliniques — pour les oncologues et oncogénéticiens
    if clinician.get("id") in ["oncologist", "oncogeneticist"]:
        trial_query = " ".join(genes[:2]) + " cancer" if genes else user_message[:80]
        trials_ctx = fetch_clinical_trials_context(trial_query)
        if trials_ctx:
            context_parts.append(f"=== ESSAIS CLINIQUES EN COURS (ClinicalTrials.gov) ===\n{trials_ctx}")
            sources.append("ClinicalTrials.gov (essais en recrutement)")

    # 5. Guidelines intégrées au système
    sources.append(f"Guidelines: {clinician.get('guidelines', 'NCCN/ESMO/HAS')}")

    return "\n\n".join(context_parts), sources


# ══ API PUBLIQUE ═════════════════════════════════════════════════════════════

def get_all_clinicians() -> list:
    """Retourne la liste des cliniciens (sans system prompt)."""
    return [{k: v for k, v in c.items() if k != "system"} for c in CLINICIANS]


def get_clinician_response(clinician_id: str, messages: list, api_key: str = None) -> dict:
    """
    Obtient une réponse enrichie du clinicien virtuel.
    Consulte PubMed, ClinVar, gnomAD, ClinicalTrials avant de répondre.
    """
    clinician = next((c for c in CLINICIANS if c["id"] == clinician_id), None)
    if not clinician:
        return {"success": False, "error": f"Clinicien '{clinician_id}' introuvable"}

    if not ANTHROPIC_AVAILABLE:
        return {"success": False, "error": "Module 'anthropic' non installé. Ajoutez-le dans requirements.txt"}

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {
            "success": False,
            "error": "Clé API Anthropic manquante. Configurez ANTHROPIC_API_KEY dans Render → Environment."
        }

    # Construire le contexte enrichi à partir du dernier message utilisateur
    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )

    enriched_context, sources_consulted = build_enriched_context(clinician, last_user_msg)

    # Construire le system prompt enrichi
    system_prompt = clinician["system"]
    if enriched_context:
        system_prompt += f"""

══════════════════════════════════════════════════════════
DONNÉES CONSULTÉES EN TEMPS RÉEL POUR CETTE QUESTION :
══════════════════════════════════════════════════════════

{enriched_context}

══════════════════════════════════════════════════════════
Utilise ces données réelles pour enrichir et citer ta réponse.
Cite les PMIDs, NCT et données ClinVar dans ta réponse.
"""

    try:
        client = anthropic.Anthropic(api_key=key)

        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

        if not api_messages:
            return {"success": False, "error": "Aucun message utilisateur fourni"}

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=api_messages
        )

        return {
            "success": True,
            "response": response.content[0].text if response.content else "",
            "clinician": clinician["name"],
            "specialty": clinician["specialty"],
            "sources_consulted": sources_consulted,
            "model": "claude-sonnet-4-20250514"
        }

    except anthropic.AuthenticationError:
        return {"success": False, "error": "Clé API invalide. Vérifiez ANTHROPIC_API_KEY dans Render → Environment."}
    except anthropic.RateLimitError:
        return {"success": False, "error": "Limite API atteinte. Réessayez dans quelques secondes."}
    except Exception as e:
        return {"success": False, "error": f"Erreur API: {str(e)}"}
