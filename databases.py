import requests

# ── ClinVar ──────────────────────────────────────────────────────────────────

CLINVAR_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
CLINVAR_FETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def search_clinvar(query: str, max_results: int = 10) -> list:
    """Recherche des variants dans ClinVar."""
    try:
        params = {"db": "clinvar", "term": query, "retmax": max_results, "retmode": "json"}
        r = requests.get(CLINVAR_SEARCH, params=params, timeout=10)
        r.raise_for_status()
        ids = r.json()["esearchresult"]["idlist"]
        if not ids:
            return []

        params2 = {"db": "clinvar", "id": ",".join(ids), "retmode": "json"}
        r2 = requests.get(CLINVAR_FETCH, params=params2, timeout=10)
        r2.raise_for_status()
        data = r2.json()

        results = []
        for uid in ids:
            item = data.get("result", {}).get(uid, {})
            if not item or uid == "uids":
                continue
            title = item.get("title", "")
            clinical_sig = item.get("clinical_significance", {})
            if isinstance(clinical_sig, dict):
                sig = clinical_sig.get("description", "Non spécifié")
            else:
                sig = str(clinical_sig)
            gene_sort = item.get("gene_sort", "")
            results.append({
                "id": uid,
                "title": title,
                "significance": sig,
                "gene": gene_sort,
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


# ── OMIM ─────────────────────────────────────────────────────────────────────

def search_omim(query: str) -> list:
    """Génère des liens OMIM pertinents (recherche directe via URL)."""
    encoded = requests.utils.quote(query)
    return [{
        "name": f"Rechercher « {query} » dans OMIM",
        "url": f"https://omim.org/search?search={encoded}",
        "description": "Base de données des maladies génétiques héréditaires"
    }, {
        "name": f"Gènes liés à « {query} » dans OMIM",
        "url": f"https://omim.org/search?search={encoded}&filter=gene",
        "description": "Entrées de type gène uniquement"
    }]


# ── COSMIC ────────────────────────────────────────────────────────────────────

def search_cosmic(gene: str) -> list:
    """Génère des liens COSMIC pour un gène."""
    encoded = requests.utils.quote(gene.upper())
    return [{
        "name": f"Mutations somatiques de {gene.upper()} dans COSMIC",
        "url": f"https://cancer.sanger.ac.uk/cosmic/gene/analysis?ln={encoded}",
        "description": "Catalogue des mutations somatiques dans le cancer"
    }, {
        "name": f"Census du gène {gene.upper()}",
        "url": f"https://cancer.sanger.ac.uk/census",
        "description": "Liste des gènes cancéreux confirmés (Cancer Gene Census)"
    }]


# ── ClinGen ───────────────────────────────────────────────────────────────────

def search_clingen(gene: str) -> list:
    """Génère des liens ClinGen pour un gène."""
    encoded = requests.utils.quote(gene.upper())
    return [{
        "name": f"Curations ClinGen pour {gene.upper()}",
        "url": f"https://search.clinicalgenome.org/kb/genes?search={encoded}",
        "description": "Évidence clinique et classification des gènes"
    }]


# ── Guidelines cliniques ──────────────────────────────────────────────────────

GUIDELINES = [
    {
        "name": "ACMG — Interprétation des variants de séquence",
        "url": "https://www.acmg.net/ACMG/Medical-Genetics-Practice-Resources/Practice-Guidelines.aspx",
        "org": "ACMG"
    },
    {
        "name": "ACMG — Standards for variant interpretation (2015)",
        "url": "https://pubmed.ncbi.nlm.nih.gov/25741868/",
        "org": "ACMG / PubMed"
    },
    {
        "name": "GeneReviews — Maladies génétiques (NCBI)",
        "url": "https://www.ncbi.nlm.nih.gov/books/NBK1116/",
        "org": "NCBI"
    },
    {
        "name": "HGMD — Human Gene Mutation Database",
        "url": "https://www.hgmd.cf.ac.uk/",
        "org": "Cardiff University"
    },
    {
        "name": "LOVD — Leiden Open Variation Database",
        "url": "https://www.lovd.nl/",
        "org": "LOVD"
    },
    {
        "name": "ClinicalTrials.gov — Essais en génétique du cancer",
        "url": "https://clinicaltrials.gov/search?cond=cancer+genetics",
        "org": "NIH"
    },
    {
        "name": "Orphanet — Maladies rares et génétiques",
        "url": "https://www.orpha.net/",
        "org": "Orphanet"
    },
    {
        "name": "gnomAD — Fréquences alléliques populationnelles",
        "url": "https://gnomad.broadinstitute.org/",
        "org": "Broad Institute"
    },
]


def get_guidelines():
    return GUIDELINES
