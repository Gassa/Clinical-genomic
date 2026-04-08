"""
claude_ai.py — SenGenoScope v1.0
IA avec accès aux bases de données scientifiques en temps réel
Dr. Moustapha Gassama — Oncogénéticien médical | Public Health Data Scientist
"""

import os, json, re, requests
from typing import Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

SYSTEM_GENOMICS = """Tu es SenGenoScope AI — assistant expert en oncogénomique et oncopharmacogénomique clinique.

Tu travailles en collaboration avec Dr. Moustapha Gassama, oncogénéticien médical et Public Health Data Scientist, Sénégal.

PLATEFORME : 🧬 Plateforme d'Oncogénomique et Oncopharmacogénomique Clinique — SenGenoScope v1.0

TON EXPERTISE :
• Interprétation ACMG/AMP 2015 (Pathogène/LP/VUS/LB/Bénin) avec critères explicités
• Oncogénétique héréditaire (BRCA1/2, Lynch, Li-Fraumeni, Cowden, FAP, MEN, CDH1, PALB2…)
• Oncopharmacogénomique : pharmacogénétique des chimiothérapies, thérapies ciblées
• Bioinformatique : VCF, NGS, gnomAD r4, ClinVar, OMIM, COSMIC, Ensembl VEP
• Médecine de précision oncologique (EGFR, ALK, BRAF, HER2, KRAS, PIK3CA…)
• Épidémiologie génétique africaine/sénégalaise, populations sous-représentées
• Guidelines : NCCN, ENIGMA, InSiGHT, ACMG, INCa, HAS, CPIC, DPWG, FDA

ACCÈS AUX DONNÉES EN TEMPS RÉEL :
Quand tu as des données PubMed, ClinVar ou gnomAD fournies dans le contexte, utilise-les pour enrichir ta réponse avec des citations précises (PMIDs, IDs ClinVar).

PRINCIPES :
• Réponses fondées sur les données probantes avec PMIDs quand disponibles
• Classification ACMG rigoureuse avec critères détaillés
• Mentionner les limites cliniques et recommander consultation spécialisée
• Répondre en français sauf si l'utilisateur écrit en anglais
• Rapport à valider par un médecin généticien qualifié

FORMAT :
• Sections claires (## titres), tableaux pour variants multiples
• Niveaux d'évidence (fort/modéré/faible)
• Recommandations cliniques pratiques avec PMIDs
"""


def _no_api_error():
    return {"success": False, "error": "Module anthropic non installé.", "fix": "pip install anthropic"}


def get_client(user_api_key: str = ''):
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic non installé")
    api_key = user_api_key.strip() if user_api_key and user_api_key.strip() else os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non configurée")
    return anthropic.Anthropic(api_key=api_key)


def check_api_status() -> dict:
    if not ANTHROPIC_AVAILABLE:
        return {"configured": False, "error": "Module anthropic non installé"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"configured": False, "error": "ANTHROPIC_API_KEY non définie", "fix": "Configurer sur Render Dashboard → Environment"}
    if not api_key.startswith("sk-ant-"):
        return {"configured": False, "error": "Format de clé invalide"}
    return {"configured": True, "model": "claude-haiku-4-5-20251001", "key_prefix": api_key[:16] + "..."}


# ── Fetch live data from scientific databases ─────────────────────────────────

def _fetch_pubmed_abstracts(query: str, max_results: int = 5) -> list:
    """Fetch recent PubMed abstracts for enriching AI responses."""
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db":"pubmed","term":query,"retmax":max_results,"retmode":"json","sort":"relevance"}, timeout=8)
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db":"pubmed","id":",".join(ids),"rettype":"abstract","retmode":"xml"}, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r2.text)
        results = []
        for art in root.findall(".//PubmedArticle")[:max_results]:
            try:
                pmid = art.findtext(".//PMID","")
                title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
                abstract = " ".join("".join(ab.itertext()) for ab in art.findall(".//AbstractText"))[:500]
                year = art.findtext(".//PubDate/Year","")
                journal = art.findtext(".//Journal/ISOAbbreviation","")
                results.append({"pmid": pmid, "title": title, "abstract": abstract, "year": year, "journal": journal})
            except: continue
        return results
    except: return []


def _fetch_clinvar_variants(gene: str, max_results: int = 5) -> list:
    """Fetch ClinVar variants for a gene."""
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db":"clinvar","term":f"{gene}[gene] AND pathogenic","retmax":max_results,"retmode":"json"}, timeout=8)
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db":"clinvar","id":",".join(ids),"retmode":"json"}, timeout=8)
        result = r2.json().get("result",{})
        variants = []
        for uid in ids[:max_results]:
            item = result.get(uid,{})
            if not item or uid == "uids": continue
            cs = item.get("clinical_significance",{})
            sig = cs.get("description","") if isinstance(cs,dict) else str(cs)
            variants.append({
                "id": uid, "title": item.get("title",""), "gene": gene.upper(),
                "significance": sig, "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"
            })
        return variants
    except: return []


def _extract_gene_from_message(message: str) -> str:
    """Extract gene name from user message."""
    known_genes = ["BRCA1","BRCA2","TP53","MLH1","MSH2","MSH6","PMS2","APC","PTEN","VHL",
                   "NF1","RET","MEN1","STK11","CDH1","PALB2","CHEK2","ATM","EGFR","KRAS",
                   "BRAF","ALK","ERBB2","MET","PIK3CA","NRAS","IDH1","IDH2","FLT3","NPM1"]
    msg_upper = message.upper()
    for gene in known_genes:
        if gene in msg_upper:
            return gene
    return ""


# ── Main AI functions ─────────────────────────────────────────────────────────

def clinical_chat(messages_history: list, user_message: str, context: dict = None, user_api_key: str = '') -> dict:
    """Chat with real-time scientific database enrichment."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)

        # Extract gene from message for live data fetching
        gene = _extract_gene_from_message(user_message)
        live_data_context = ""

        # Fetch live PubMed data
        pubmed_articles = _fetch_pubmed_abstracts(user_message[:100], max_results=3)
        if pubmed_articles:
            live_data_context += "\n\n📚 DONNÉES PUBMED EN TEMPS RÉEL :\n"
            for a in pubmed_articles:
                live_data_context += f"• PMID {a['pmid']} ({a['year']}, {a['journal']}): {a['title']}\n  {a['abstract'][:200]}…\n"

        # Fetch ClinVar data if gene identified
        if gene:
            clinvar_variants = _fetch_clinvar_variants(gene, max_results=3)
            if clinvar_variants:
                live_data_context += f"\n\n🧬 VARIANTS CLINVAR EN TEMPS RÉEL pour {gene}:\n"
                for v in clinvar_variants:
                    live_data_context += f"• {v['title']} — {v['significance']} (ClinVar ID: {v['id']})\n"

        # Session context
        session_ctx = ""
        if context:
            if context.get("last_query"):
                session_ctx += f"\nDernière recherche PubMed: {context['last_query']}"
            if context.get("genes_found"):
                session_ctx += f"\nGènes identifiés: {', '.join(context['genes_found'][:10])}"

        system = SYSTEM_GENOMICS
        if live_data_context:
            system += f"\n\n{live_data_context}"
        if session_ctx:
            system += f"\n\nCONTEXTE SESSION:\n{session_ctx}"

        formatted = [{"role": m["role"], "content": m["content"]} for m in messages_history[-10:]]
        formatted.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=system,
            messages=formatted
        )
        return {
            "success": True,
            "response": response.content[0].text,
            "tokens": response.usage.output_tokens,
            "live_pubmed": len(pubmed_articles),
            "live_clinvar": len(clinvar_variants) if gene else 0,
            "gene_detected": gene
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_uploaded_file(filename: str, content: str, file_type: str, user_question: str = "", user_api_key: str = "") -> dict:
    """AI analysis of genomic file with live database enrichment."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)

        # Extract genes from file content for live data
        known_genes = ["BRCA1","BRCA2","TP53","MLH1","MSH2","EGFR","KRAS","BRAF","ALK","PTEN"]
        detected_genes = [g for g in known_genes if g in content.upper()][:3]

        live_context = ""
        if detected_genes:
            for gene in detected_genes[:2]:
                cv = _fetch_clinvar_variants(gene, 2)
                if cv:
                    live_context += f"\n🧬 ClinVar {gene}: " + "; ".join(f"{v['title']} ({v['significance']})" for v in cv) + "\n"

        if file_type == "vcf":
            prompt = f"""Analyse ce fichier VCF génomique (SenGenoScope — Dr. Moustapha Gassama):
FICHIER: {filename}
```{content[:8000]}```
{"QUESTION: " + user_question if user_question else ""}
{live_context}

## 1. Résumé du fichier
## 2. Variants prioritaires — Classification ACMG 2015
## 3. Interprétation clinique oncogénomique
## 4. Corrélations ClinVar/gnomAD (utilise les données ci-dessus)
## 5. Pharmacogénomique — thérapies ciblées applicables
## 6. Recommandations cliniques avec PMIDs
"""
        else:
            prompt = f"""Analyse ce fichier génomique:
FICHIER: {filename}
```{content[:7000]}```
{"QUESTION: " + user_question if user_question else ""}
{live_context}

## 1. Type de données
## 2. Variants/gènes identifiés
## 3. Classification ACMG
## 4. Corrélations bases de données
## 5. Recommandations cliniques
"""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=4000, system=SYSTEM_GENOMICS,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "success": True, "filename": filename, "file_type": file_type,
            "analysis": response.content[0].text,
            "tokens_used": response.usage.output_tokens, "model": response.model,
            "genes_detected": detected_genes
        }
    except Exception as e:
        return {"success": False, "error": str(e), "filename": filename}


def synthesize_pubmed_results(query: str, articles: list, genes: list, user_api_key: str = "") -> dict:
    """Intelligent PubMed synthesis with live data."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)
        articles_summary = "\n".join([
            f"- PMID {a.get('pmid','')}: {a.get('title','')} ({a.get('journal','')}, {a.get('year','')})"
            for a in articles[:15]
        ])
        prompt = f"""Synthèse de littérature oncogénomique pour: "{query}"
GÈNES: {', '.join(genes[:15]) if genes else 'Aucun'}
ARTICLES ({len(articles)} total):
{articles_summary}

## 1. Résumé exécutif
## 2. Gènes et variants clés
## 3. Implications cliniques oncogénomiques
## 4. Pharmacogénomique et thérapies ciblées
## 5. Guidelines applicables (PMIDs)
## 6. Lacunes dans la littérature
## 7. Recommandations pratiques
"""
        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=3000, system=SYSTEM_GENOMICS,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"success": True, "synthesis": response.content[0].text,
                "articles_analyzed": len(articles), "genes_covered": genes[:15]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_clinical_report(variant_data: dict, patient_context: str = "", user_api_key: str = "") -> dict:
    """Generate structured ACMG clinical report."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)

        # Fetch live ClinVar data for the variant's gene
        gene = variant_data.get("gene","")
        live_context = ""
        if gene:
            cv = _fetch_clinvar_variants(gene, 3)
            if cv:
                live_context = f"\nDonnées ClinVar temps réel pour {gene}:\n" + \
                    "\n".join(f"• {v['title']} — {v['significance']}" for v in cv)

        prompt = f"""Génère un rapport clinique ACMG/AMP 2015:
VARIANT: {json.dumps(variant_data, indent=2, ensure_ascii=False)}
{"CONTEXTE: " + patient_context if patient_context else ""}
{live_context}

### 1. IDENTIFICATION (HGVS, gène, GRCh38)
### 2. CLASSIFICATION ACMG (critères + justification)
### 3. DONNÉES FONCTIONNELLES
### 4. DONNÉES POPULATIONNELLES (gnomAD r4)
### 5. DONNÉES CLINIQUES (OMIM, pénétrance)
### 6. PHARMACOGÉNOMIQUE (thérapies ciblées)
### 7. RECOMMANDATIONS CLINIQUES
### 8. RÉFÉRENCES (PMIDs)
### 9. LIMITATIONS

*SenGenoScope v1.0 — Dr. Moustapha Gassama — À valider par un médecin généticien*
"""
        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=4000, system=SYSTEM_GENOMICS,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"success": True, "report": response.content[0].text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def interpret_vcf_variant(chrom: str, pos: str, ref: str, alt: str,
                           gene: str = "", existing_data: dict = None) -> dict:
    """ACMG interpretation with live ClinVar data."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)
        context = ""
        if existing_data:
            if existing_data.get("polyphen_score") is not None:
                context += f"\nPolyPhen-2: {existing_data['polyphen_score']} ({existing_data.get('polyphen_prediction','')})"
            if existing_data.get("sift_score") is not None:
                context += f"\nSIFT: {existing_data['sift_score']}"
            if existing_data.get("cadd_phred") is not None:
                context += f"\nCADD Phred: {existing_data['cadd_phred']}"

        # Live ClinVar data
        if gene:
            cv = _fetch_clinvar_variants(gene, 2)
            if cv:
                context += f"\nClinVar {gene}: " + "; ".join(f"{v['title']} ({v['significance']})" for v in cv)

        prompt = f"""Classification ACMG rapide — JSON uniquement:
Variant: chr{chrom}:{pos} {ref}>{alt}
Gène: {gene or 'inconnu'} · Assembly: GRCh38
{context}

JSON:
{{
  "acmg_classification": "Pathogène|Probablement Pathogène|VUS|Probablement Bénin|Bénin",
  "acmg_criteria": ["critère 1"],
  "clinical_significance": "2-3 phrases",
  "targeted_therapy": "thérapie ou N/A",
  "key_evidence": ["évidence 1"],
  "recommendations": "recommandation",
  "confidence": "haute|modérée|faible",
  "pmids_relevant": []
}}"""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=800, system=SYSTEM_GENOMICS,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["success"] = True
            return result
        return {"success": True, "acmg_classification": "VUS", "clinical_significance": text[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def pharmacogenomics_analysis(gene: str, variant: str = "", drug: str = "", user_api_key: str = "") -> dict:
    """Clinical pharmacogenomics analysis with live data."""
    if not ANTHROPIC_AVAILABLE:
        return _no_api_error()
    try:
        client = get_client(user_api_key) if user_api_key else get_client(user_api_key)

        # Fetch live PubMed data for pharmacogenomics
        query = f"{gene} pharmacogenomics {drug}" if drug else f"{gene} pharmacogenomics targeted therapy"
        pubmed_data = _fetch_pubmed_abstracts(query, 3)
        live_ctx = ""
        if pubmed_data:
            live_ctx = "\n📚 Littérature récente:\n" + "\n".join(
                f"• PMID {a['pmid']} ({a['year']}): {a['title']}" for a in pubmed_data
            )

        prompt = f"""Analyse pharmacogénomique clinique:
Gène: {gene}
{"Variant: " + variant if variant else ""}
{"Médicament: " + drug if drug else ""}
{live_ctx}

## 1. Profil pharmacogénomique de {gene}
## 2. Médicaments concernés (chimiothérapies, thérapies ciblées)
## 3. Implications cliniques (dosage, efficacité, toxicité)
## 4. Guidelines (CPIC, DPWG, FDA biomarkers)
## 5. Recommandations pratiques avec PMIDs
"""
        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=2500, system=SYSTEM_GENOMICS,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "success": True, "gene": gene,
            "analysis": response.content[0].text,
            "tokens": response.usage.output_tokens,
            "pubmed_sources": len(pubmed_data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
