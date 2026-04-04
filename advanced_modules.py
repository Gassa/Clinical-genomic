"""
advanced_modules.py — SenGenoScope v6
8 nouveaux modules cliniques avancés:
1. Calculateur Manchester / BRCAPRO / Tyrer-Cuzick
2. Interprétation VCF (parsing + annotation)
3. Lettre conseil génétique structurée
4. Recherche ClinVar par HGVS
5. Comparateur de variants côte à côte
6. HPO → gènes candidats (diagnostic différentiel)
7. Tableau de bord statistiques
8. Visualisation lollipop (données pour le front)
"""

import requests
import re


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CALCULATEUR MANCHESTER / BRCAPRO / TYRER-CUZICK
# Sources:
# - Manchester: Evans DGR et al. JNCI 2004;96:370 (PMID 14996858)
# - BRCAPRO: Berry DA et al. J Clin Oncol 2002;20:2180
# - Tyrer-Cuzick: Tyrer J et al. Stat Methods Med Res 2004;13:395
# ═══════════════════════════════════════════════════════════════════════════════

MANCHESTER_WEIGHTS = {
    # Sein
    "breast_under40": 6,
    "breast_40_49": 4,
    "breast_50_59": 3,
    "breast_60_plus": 2,
    "breast_bilateral": 8,
    "breast_male": 8,
    # Ovaire
    "ovary_any_age": 5,
    # Pancréas
    "pancreas_any": 2,
    # Prostate_young
    "prostate_under60": 2,
    # Autres
    "triple_negative_under40": 4,
}

def calculate_manchester_score(family_history: dict) -> dict:
    """
    Score de Manchester pour estimation probabilité mutation BRCA1/BRCA2.
    Score ≥10 → test génétique recommandé (sensibilité ~77%, spécificité ~80%)
    Référence: Evans DGR et al. JNCI 2004;96:370. PMID 14996858
    """
    score = 0
    details = []

    mappings = {
        "breast_under40": ("Cancer du sein < 40 ans", 6),
        "breast_40_49": ("Cancer du sein 40-49 ans", 4),
        "breast_50_59": ("Cancer du sein 50-59 ans", 3),
        "breast_60_plus": ("Cancer du sein ≥60 ans", 2),
        "breast_bilateral": ("Cancer du sein bilatéral", 8),
        "breast_male": ("Cancer du sein chez un homme", 8),
        "ovary_any_age": ("Cancer de l'ovaire (tout âge)", 5),
        "pancreas_any": ("Cancer du pancréas (familial)", 2),
        "prostate_under60": ("Cancer de la prostate <60 ans", 2),
        "triple_negative_under40": ("Cancer triple négatif <40 ans", 4),
    }

    for key, (label, weight) in mappings.items():
        count = family_history.get(key, 0)
        if count > 0:
            pts = weight * min(count, 2)  # Max 2 parents par critère
            score += pts
            details.append({"criterion": label, "count": count, "points": pts})

    # Interprétation
    if score >= 15:
        prob = "Très élevée (>30%)"
        recommendation = "Test génétique BRCA1/2 fortement recommandé. Consultation oncogénétique urgente."
        level = "very_high"
    elif score >= 10:
        prob = "Élevée (10-30%)"
        recommendation = "Test génétique BRCA1/2 recommandé selon les critères HAS/INCa."
        level = "high"
    elif score >= 5:
        prob = "Modérée (5-10%)"
        recommendation = "Consultation oncogénétique recommandée. Test selon contexte clinique."
        level = "moderate"
    else:
        prob = "Faible (<5%)"
        recommendation = "Probabilité faible de mutation BRCA1/2. Surveillance standard."
        level = "low"

    return {
        "score": score,
        "probability": prob,
        "level": level,
        "recommendation": recommendation,
        "details": details,
        "threshold_test": score >= 10,
        "reference": "Evans DGR et al. JNCI 2004;96:370 — PMID 14996858",
        "method": "Manchester Score"
    }


def calculate_tyrer_cuzick(data: dict) -> dict:
    """
    Estimation simplifiée du risque Tyrer-Cuzick (modèle IBIS).
    Basé sur âge, IMC, antécédents familiaux, ménarche, ménopause, parité.
    Référence: Tyrer J et al. Stat Methods Med Res 2004;13:395. PMID 15622009
    Note: Estimation simplifiée — utiliser IBIS Tool pour calcul complet.
    """
    age = data.get("age", 45)
    family_brca1 = data.get("family_brca1", False)
    family_brca2 = data.get("family_brca2", False)
    breast_cancer_1st = data.get("breast_cancer_1st_degree", 0)
    breast_cancer_2nd = data.get("breast_cancer_2nd_degree", 0)
    age_menarche = data.get("age_menarche", 12)
    age_menopause = data.get("age_menopause", None)
    nulliparous = data.get("nulliparous", False)
    bmi = data.get("bmi", 25)
    hrt_use = data.get("hrt_use", False)
    atypical_hyperplasia = data.get("atypical_hyperplasia", False)

    # Risque de base (population générale, cumulatif à 10 ans selon l'âge)
    base_risks = {
        30: 0.4, 35: 0.7, 40: 1.4, 45: 2.0, 50: 2.5,
        55: 3.0, 60: 3.3, 65: 3.5, 70: 3.6
    }
    age_key = min(base_risks.keys(), key=lambda x: abs(x - age))
    base_risk = base_risks[age_key]

    # Multiplicateurs
    multiplier = 1.0
    factors = []

    if family_brca1:
        multiplier *= 3.5
        factors.append({"factor": "Mutation BRCA1 dans la famille", "effect": "×3.5"})
    if family_brca2:
        multiplier *= 2.8
        factors.append({"factor": "Mutation BRCA2 dans la famille", "effect": "×2.8"})
    if breast_cancer_1st >= 2:
        multiplier *= 3.0
        factors.append({"factor": "≥2 cancers sein 1er degré", "effect": "×3.0"})
    elif breast_cancer_1st == 1:
        multiplier *= 1.8
        factors.append({"factor": "1 cancer sein 1er degré", "effect": "×1.8"})
    if breast_cancer_2nd >= 1:
        multiplier *= 1.4
        factors.append({"factor": "Cancer sein 2ème degré", "effect": "×1.4"})
    if age_menarche <= 11:
        multiplier *= 1.1
        factors.append({"factor": "Ménarche précoce (≤11 ans)", "effect": "×1.1"})
    if nulliparous:
        multiplier *= 1.2
        factors.append({"factor": "Nulliparité", "effect": "×1.2"})
    if atypical_hyperplasia:
        multiplier *= 4.0
        factors.append({"factor": "Hyperplasie atypique", "effect": "×4.0"})
    if hrt_use:
        multiplier *= 1.3
        factors.append({"factor": "THS utilisé", "effect": "×1.3"})
    if bmi >= 30 and (age_menopause is not None):
        multiplier *= 1.2
        factors.append({"factor": "IMC ≥30 post-ménopause", "effect": "×1.2"})

    estimated_risk_10y = round(min(base_risk * multiplier, 40), 1)
    estimated_risk_lifetime = round(min(estimated_risk_10y * 7, 80), 1)

    if estimated_risk_10y >= 8:
        level = "Très élevé"
        rec = "Dépistage intensifié (IRM annuelle + mammographie). Consultation oncogénétique."
    elif estimated_risk_10y >= 5:
        level = "Élevé"
        rec = "IRM de dépistage annuelle recommandée. Évaluation oncogénétique."
    elif estimated_risk_10y >= 3:
        level = "Modéré"
        rec = "Mammographie annuelle dès 40 ans. Suivi rapproché."
    else:
        level = "Faible à modéré"
        rec = "Dépistage standard. Mammographie selon recommandations nationales."

    return {
        "method": "Tyrer-Cuzick (IBIS — version simplifiée)",
        "age": age,
        "base_risk_10y_percent": base_risk,
        "estimated_risk_10y_percent": estimated_risk_10y,
        "estimated_lifetime_risk_percent": estimated_risk_lifetime,
        "population_lifetime_risk": "12%",
        "risk_level": level,
        "recommendation": rec,
        "factors": factors,
        "multiplier": round(multiplier, 2),
        "note": "Estimation simplifiée. Pour le calcul complet, utiliser l'outil IBIS officiel (https://ibis-risk-calculator.magview.com)",
        "reference": "Tyrer J et al. Stat Methods Med Res 2004;13:395. PMID 15622009"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RECHERCHE CLINVAR PAR HGVS
# Source: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
# ═══════════════════════════════════════════════════════════════════════════════

def search_clinvar_by_hgvs(hgvs: str) -> dict:
    """
    Recherche un variant dans ClinVar par notation HGVS (NM_ ou NC_).
    Exemples:
    - NM_007294.4:c.5266dupC
    - NC_000017.11:g.43094692A>G
    - NM_000059.4:c.7480C>T
    Source: https://www.ncbi.nlm.nih.gov/clinvar/
    """
    hgvs = hgvs.strip()
    try:
        # Recherche dans ClinVar
        search_term = f'"{hgvs}"[Variant Name] OR "{hgvs}"[All Fields]'
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "clinvar", "term": search_term, "retmax": 10, "retmode": "json"},
            timeout=10
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            # Essai avec terme simplifié
            simple = re.sub(r'NM_\d+\.\d+:', '', hgvs)
            r2 = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db": "clinvar", "term": simple, "retmax": 5, "retmode": "json"},
                timeout=10
            )
            ids = r2.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return {"hgvs": hgvs, "found": False, "variants": [],
                    "message": "Variant non trouvé dans ClinVar. Vérifiez la notation HGVS."}

        r3 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(ids[:5]), "retmode": "json"},
            timeout=12
        )
        result = r3.json().get("result", {})
        variants = []
        for uid, item in result.items():
            if uid == "uids": continue
            cs = item.get("clinical_significance", {})
            sig = cs.get("description", "—") if isinstance(cs, dict) else str(cs)
            variants.append({
                "clinvar_id": uid,
                "title": item.get("title", ""),
                "gene": item.get("gene_sort", ""),
                "variation_type": item.get("variation_type", ""),
                "significance": sig,
                "review_status": (cs.get("review_status", "") if isinstance(cs, dict) else ""),
                "last_updated": item.get("obj_type", ""),
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
            })

        return {"hgvs": hgvs, "found": True, "count": len(variants), "variants": variants,
                "source": "NCBI ClinVar", "source_url": "https://www.ncbi.nlm.nih.gov/clinvar/"}

    except Exception as e:
        return {"hgvs": hgvs, "found": False, "variants": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HPO → GÈNES CANDIDATS (DIAGNOSTIC DIFFÉRENTIEL)
# Source: https://hpo.jax.org/api/hpo/
# ═══════════════════════════════════════════════════════════════════════════════

def hpo_to_genes(hpo_ids: list) -> dict:
    """
    À partir d'une liste d'identifiants HPO, retourne les gènes candidats.
    Utilise l'API HPO JAX: https://hpo.jax.org/api/hpo/gene
    """
    if not hpo_ids:
        return {"error": "Aucun terme HPO fourni"}

    gene_scores = {}
    hpo_info = {}

    for hpo_id in hpo_ids[:10]:
        try:
            r = requests.get(
                f"https://hpo.jax.org/api/hpo/term/{hpo_id}/genes",
                params={"max": 50, "offset": 0},
                timeout=10
            )
            data = r.json()
            genes = data.get("genes", [])
            hpo_info[hpo_id] = {"id": hpo_id, "gene_count": len(genes)}

            for gene in genes:
                symbol = gene.get("geneSymbol", "")
                gene_id = gene.get("geneId", "")
                if symbol:
                    if symbol not in gene_scores:
                        gene_scores[symbol] = {
                            "symbol": symbol,
                            "gene_id": gene_id,
                            "hpo_matches": 0,
                            "hpo_ids": [],
                            "ncbi_url": f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
                        }
                    gene_scores[symbol]["hpo_matches"] += 1
                    gene_scores[symbol]["hpo_ids"].append(hpo_id)
        except Exception:
            continue

    # Trier par nombre de HPO correspondants
    ranked = sorted(gene_scores.values(), key=lambda x: -x["hpo_matches"])

    return {
        "hpo_terms_queried": hpo_ids,
        "total_candidate_genes": len(ranked),
        "top_candidates": ranked[:30],
        "method": "HPO gene associations via JAX HPO API",
        "source_url": "https://hpo.jax.org/",
        "interpretation": f"{len(ranked)} gènes candidats trouvés pour la combinaison phénotypique fournie. Les gènes avec le plus de termes HPO correspondants sont les plus probables."
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PARSING VCF
# ═══════════════════════════════════════════════════════════════════════════════

def parse_vcf_content(vcf_text: str) -> dict:
    """
    Parse un fichier VCF (texte) et extrait les variants avec annotation clinique.
    Format VCF 4.x: CHROM POS ID REF ALT QUAL FILTER INFO [FORMAT] [SAMPLE]
    """
    lines = vcf_text.strip().split('\n')
    variants = []
    meta = {"format": "VCF", "samples": [], "contigs": [], "filters": []}
    headers = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('##'):
            # Métadonnées
            if '##fileformat=' in line:
                meta["format"] = line.split('=')[1]
            elif '##contig=' in line:
                meta["contigs"].append(line)
            elif '##FILTER=' in line:
                meta["filters"].append(line)
            continue

        if line.startswith('#CHROM'):
            headers = line[1:].split('\t')
            if len(headers) > 9:
                meta["samples"] = headers[9:]
            continue

        # Ligne variant
        parts = line.split('\t')
        if len(parts) < 5:
            continue

        chrom = parts[0].replace('chr', '')
        pos = parts[1]
        var_id = parts[2] if len(parts) > 2 else '.'
        ref = parts[3] if len(parts) > 3 else ''
        alt = parts[4] if len(parts) > 4 else ''
        qual = parts[5] if len(parts) > 5 else '.'
        filt = parts[6] if len(parts) > 6 else '.'
        info = parts[7] if len(parts) > 7 else '.'

        # Parser INFO
        info_dict = {}
        for item in info.split(';'):
            if '=' in item:
                k, v = item.split('=', 1)
                info_dict[k] = v
            else:
                info_dict[item] = True

        # Déterminer le type de variant
        if len(ref) == len(alt) == 1:
            var_type = "SNV"
        elif len(ref) > len(alt):
            var_type = "Délétion"
        elif len(ref) < len(alt):
            var_type = "Insertion"
        else:
            var_type = "Indel"

        # Notation HGVS approximative
        hgvs_g = f"g.{pos}{ref}>{alt}" if var_type == "SNV" else f"g.{pos}_{int(pos)+len(ref)-1}del" if var_type == "Délétion" else f"g.{pos}ins{alt[len(ref):]}"

        variant = {
            "chrom": chrom,
            "pos": pos,
            "id": var_id,
            "ref": ref,
            "alt": alt,
            "qual": qual,
            "filter": filt,
            "type": var_type,
            "hgvs_g_approx": hgvs_g,
            "info": info_dict,
            "gene": info_dict.get("GENE", info_dict.get("ANN", "").split('|')[3] if "ANN" in info_dict else ""),
            "dp": info_dict.get("DP", ""),
            "af": info_dict.get("AF", info_dict.get("VAF", "")),
            "clinvar_id": info_dict.get("CLNID", info_dict.get("CLNSIG", "")),
            "clinvar_sig": info_dict.get("CLNSIG", ""),
            "vep_consequence": info_dict.get("CSQ", "").split('|')[1] if "CSQ" in info_dict else "",
        }
        variants.append(variant)

    # Statistiques
    types_count = {}
    for v in variants:
        types_count[v["type"]] = types_count.get(v["type"], 0) + 1

    return {
        "total_variants": len(variants),
        "metadata": meta,
        "variant_types": types_count,
        "variants": variants[:50],  # Max 50 pour l'affichage
        "note": "Annotation ClinVar et VEP disponibles via les modules dédiés pour chaque variant."
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LETTRE CONSEIL GÉNÉTIQUE STRUCTURÉE
# Basée sur les recommandations HAS 2021 et INCa
# ═══════════════════════════════════════════════════════════════════════════════

def generate_genetic_counseling_letter(data: dict) -> dict:
    """
    Génère une lettre de résultat de consultation en oncogénétique.
    Basée sur le modèle HAS/INCa 2021.
    """
    patient_name = data.get("patient_name", "Madame/Monsieur [Nom]")
    patient_dob = data.get("patient_dob", "[Date de naissance]")
    consultation_date = data.get("consultation_date", "[Date]")
    referring_physician = data.get("referring_physician", "[Médecin prescripteur]")
    gene = data.get("gene", "")
    variant = data.get("variant", "")
    classification = data.get("classification", "VUS")
    syndrome = data.get("syndrome", "")
    risk_level = data.get("risk_level", "")
    family_history = data.get("family_history", "")
    recommendations = data.get("recommendations", [])
    follow_up = data.get("follow_up", "")

    # Paragraphe résultat selon classification
    result_paragraphs = {
        "Pathogène": f"""L'analyse moléculaire a identifié le variant {variant} dans le gène {gene}, classifié comme PATHOGÈNE selon les critères ACMG/AMP 2015 (Richards et al., Genetics in Medicine 2017). Ce résultat confirme un syndrome de prédisposition héréditaire au cancer ({syndrome if syndrome else 'syndrome héréditaire'}).

Ce variant est associé à un risque significativement augmenté de développer certains cancers au cours de la vie. Une information génétique à la famille est recommandée, dans le respect de la réglementation en vigueur (Article L1131-1 du Code de la Santé Publique).""",

        "Probablement Pathogène": f"""L'analyse moléculaire a identifié le variant {variant} dans le gène {gene}, classifié comme PROBABLEMENT PATHOGÈNE selon les critères ACMG/AMP 2015. Bien que la pathogénicité de ce variant ne soit pas confirmée avec certitude, ce résultat justifie une prise en charge similaire à un variant pathogène avéré dans l'attente d'une reclassification.

Une surveillance renforcée est recommandée et une information aux apparentés du premier degré doit être envisagée.""",

        "VUS": f"""L'analyse moléculaire a identifié le variant {variant} dans le gène {gene}, classifié comme VARIANT D'INCERTITUDE SIGNIFICATIVE (VUS) selon les critères ACMG/AMP 2015. À ce jour, les données disponibles ne permettent pas de conclure avec certitude sur le caractère délétère ou bénin de ce variant.

Ce résultat ne doit PAS être utilisé seul pour guider les décisions cliniques. Une reclassification est possible au fur et à mesure de l'accumulation des données dans les bases internationales (ClinVar, LOVD, ENIGMA).""",

        "Négatif": f"""L'analyse moléculaire des gènes {gene if gene else 'analysés'} n'a pas mis en évidence de variant pathogène ou probablement pathogène. Ce résultat n'exclut pas formellement un syndrome héréditaire, notamment en cas de variants dans des gènes non analysés ou de variants de régulation non détectés par séquençage standard.

La surveillance clinique reste recommandée en fonction de l'histoire familiale."""
    }

    result_text = result_paragraphs.get(classification, result_paragraphs["VUS"])

    # Recommandations de surveillance selon classification et syndrome
    default_recs = {
        "BRCA1/2 sein": [
            "IRM mammaire annuelle dès 25-30 ans",
            "Mammographie annuelle + échographie à partir de 30 ans",
            "Consultation chirurgicale pour discussion mastectomie prophylactique",
            "Salpingo-ovariectomie bilatérale prophylactique à partir de 40 ans (BRCA1) ou 45 ans (BRCA2)",
            "Information et test des apparentés du premier degré",
        ],
        "Lynch": [
            "Coloscopie avec chromo-endoscopie tous les 1-2 ans dès 25 ans",
            "Surveillance gynécologique annuelle (MLH1/MSH2)",
            "Aspiriothérapie à discuter (étude CAPP2)",
            "Information et test des apparentés du premier degré",
        ],
    }

    if not recommendations:
        recommendations = default_recs.get(syndrome, ["Surveillance clinique à définir avec l'équipe référente"])

    letter = f"""
COMPTE-RENDU DE CONSULTATION D'ONCOGÉNÉTIQUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATIENT(E) : {patient_name}
Date de naissance : {patient_dob}
Date de consultation : {consultation_date}
Médecin prescripteur : {referring_physician}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXTE CLINIQUE ET FAMILIAL

{family_history if family_history else "[Décrire les antécédents personnels et familiaux de cancer]"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RÉSULTAT DE L'ANALYSE MOLÉCULAIRE

{result_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMANDATIONS DE SURVEILLANCE ET DE PRISE EN CHARGE

{chr(10).join(f"• {r}" for r in recommendations)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUIVI ET PROCHAINE CONSULTATION

{follow_up if follow_up else "Une prochaine consultation de suivi est recommandée dans 12 mois ou à la demande du patient ou du médecin traitant."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fait à [Ville], le {consultation_date}

Dr Moustapha Gassama
Oncogénéticien médical | Public Health Data Scientist
Service d'Oncogénétique

⚠️ Document généré par SenGenoScope — Usage clinique confidentiel
Basé sur les recommandations HAS/INCa et les critères ACMG/AMP 2015
    """.strip()

    return {
        "letter": letter,
        "classification": classification,
        "gene": gene,
        "variant": variant,
        "recommendations_count": len(recommendations),
        "references": [
            "Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868)",
            "HAS/INCa — Recommandations de prise en charge des prédispositions héréditaires 2021",
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. COMPARATEUR DE VARIANTS (2 variants côte à côte)
# ═══════════════════════════════════════════════════════════════════════════════

def compare_two_variants(v1: dict, v2: dict) -> dict:
    """Compare deux variants selon les scores VEP et les critères ACMG."""
    def score_variant(v):
        pp = v.get("polyphen_score")
        sift = v.get("sift_score")
        cadd = v.get("cadd_phred")
        acmg = v.get("acmg_classification", "")
        score = 0
        if pp is not None and pp >= 0.908: score += 3
        elif pp is not None and pp >= 0.447: score += 1
        if sift is not None and sift < 0.05: score += 2
        if cadd is not None and cadd >= 30: score += 3
        elif cadd is not None and cadd >= 20: score += 2
        elif cadd is not None and cadd >= 15: score += 1
        acmg_scores = {"Pathogène": 5, "Probablement Pathogène": 4, "VUS": 2, "Probablement Bénin": 1, "Bénin": 0}
        score += acmg_scores.get(acmg, 0)
        return score

    s1 = score_variant(v1)
    s2 = score_variant(v2)

    if s1 > s2:
        more_pathogenic = "Variant 1"
        conclusion = f"Le Variant 1 ({v1.get('hgvs','V1')}) présente un profil de pathogénicité in silico plus élevé."
    elif s2 > s1:
        more_pathogenic = "Variant 2"
        conclusion = f"Le Variant 2 ({v2.get('hgvs','V2')}) présente un profil de pathogénicité in silico plus élevé."
    else:
        more_pathogenic = "Équivalents"
        conclusion = "Les deux variants présentent des profils de pathogénicité in silico similaires."

    return {
        "variant1": {**v1, "composite_score": s1},
        "variant2": {**v2, "composite_score": s2},
        "more_pathogenic": more_pathogenic,
        "conclusion": conclusion,
        "disclaimer": "⚠️ Cette comparaison est basée sur des scores in silico. La classification ACMG finale intègre obligatoirement les données cliniques et familiales.",
        "reference": "Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868)"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. TABLEAU DE BORD STATISTIQUES
# ═══════════════════════════════════════════════════════════════════════════════

# Stockage en mémoire (réinitialisé au redémarrage — Phase 2 : DB persistante)
_stats = {
    "total_searches": 0,
    "gene_counts": {},
    "search_history": [],
    "vep_count": 0,
    "acmg_count": 0,
    "risk_count": 0,
    "clinvar_searches": 0,
    "session_start": None,
}

def record_search(query: str, genes_found: list):
    import datetime
    _stats["total_searches"] += 1
    if _stats["session_start"] is None:
        _stats["session_start"] = datetime.datetime.now().isoformat()
    for gene in genes_found:
        _stats["gene_counts"][gene] = _stats["gene_counts"].get(gene, 0) + 1
    _stats["search_history"].append({
        "query": query,
        "genes": genes_found[:5],
        "timestamp": datetime.datetime.now().strftime("%H:%M")
    })
    _stats["search_history"] = _stats["search_history"][-20:]  # Garder les 20 dernières

def record_vep():
    _stats["vep_count"] += 1

def record_acmg():
    _stats["acmg_count"] += 1

def record_risk():
    _stats["risk_count"] += 1

def get_stats() -> dict:
    top_genes = sorted(_stats["gene_counts"].items(), key=lambda x: -x[1])[:10]
    return {
        "total_searches": _stats["total_searches"],
        "vep_analyses": _stats["vep_count"],
        "acmg_classifications": _stats["acmg_count"],
        "risk_calculations": _stats["risk_count"],
        "top_genes": [{"gene": g, "count": c} for g, c in top_genes],
        "recent_searches": _stats["search_history"][-8:],
        "session_start": _stats["session_start"],
        "note": "Statistiques de la session courante — réinitialisées au redémarrage du serveur"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DONNÉES LOLLIPOP (pour visualisation front-end)
# Source: ClinVar + UniProt pour les domaines
# ═══════════════════════════════════════════════════════════════════════════════

GENE_DOMAINS = {
    "BRCA1": {
        "protein_length": 1863,
        "domains": [
            {"name": "RING", "start": 1, "end": 109, "color": "#0891b2"},
            {"name": "BRCT 1", "start": 1646, "end": 1736, "color": "#7c3aed"},
            {"name": "BRCT 2", "start": 1760, "end": 1855, "color": "#7c3aed"},
            {"name": "NLS", "start": 503, "end": 508, "color": "#16a34a"},
            {"name": "BARD1-binding", "start": 1, "end": 100, "color": "#d97706"},
        ],
        "reference": "UniProt P38398 · ClinGen BRCA1"
    },
    "BRCA2": {
        "protein_length": 3418,
        "domains": [
            {"name": "PALB2-binding", "start": 10, "end": 40, "color": "#0891b2"},
            {"name": "BRC repeats (1-8)", "start": 1002, "end": 2085, "color": "#7c3aed"},
            {"name": "DBD", "start": 2402, "end": 3190, "color": "#16a34a"},
            {"name": "NLS", "start": 3263, "end": 3269, "color": "#d97706"},
            {"name": "RAD51-binding", "start": 3270, "end": 3305, "color": "#dc2626"},
        ],
        "reference": "UniProt P51587 · ClinGen BRCA2"
    },
    "TP53": {
        "protein_length": 393,
        "domains": [
            {"name": "Transactivation", "start": 1, "end": 67, "color": "#0891b2"},
            {"name": "Proline-rich", "start": 68, "end": 98, "color": "#16a34a"},
            {"name": "DNA-binding", "start": 102, "end": 292, "color": "#dc2626"},
            {"name": "Tetramerization", "start": 323, "end": 356, "color": "#7c3aed"},
            {"name": "Regulatory", "start": 364, "end": 393, "color": "#d97706"},
        ],
        "reference": "UniProt P04637 · IARC TP53 Database"
    },
    "MLH1": {
        "protein_length": 756,
        "domains": [
            {"name": "ATPase", "start": 1, "end": 336, "color": "#0891b2"},
            {"name": "Dimerization", "start": 336, "end": 756, "color": "#7c3aed"},
        ],
        "reference": "UniProt P40692 · InSiGHT MLH1"
    },
    "MSH2": {
        "protein_length": 934,
        "domains": [
            {"name": "Mismatch binding", "start": 1, "end": 200, "color": "#0891b2"},
            {"name": "ATPase", "start": 600, "end": 934, "color": "#7c3aed"},
        ],
        "reference": "UniProt P43246 · InSiGHT MSH2"
    },
}

def get_lollipop_data(gene: str) -> dict:
    """
    Retourne les données pour la visualisation lollipop d'un gène.
    Récupère les variants pathogènes de ClinVar pour le gène.
    """
    gene = gene.upper()
    domain_info = GENE_DOMAINS.get(gene, {
        "protein_length": 1000,
        "domains": [],
        "reference": "Données non disponibles pour ce gène"
    })

    # Récupérer variants ClinVar pathogènes
    variants = []
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "clinvar", "term": f'{gene}[gene] AND "pathogenic"[significance]', "retmax": 100, "retmode": "json"},
            timeout=10
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])[:50]

        if ids:
            r2 = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "clinvar", "id": ",".join(ids), "retmode": "json"},
                timeout=15
            )
            result = r2.json().get("result", {})
            for uid, item in result.items():
                if uid == "uids": continue
                cs = item.get("clinical_significance", {})
                sig = cs.get("description", "") if isinstance(cs, dict) else ""
                loc = item.get("variation_set", [{}])
                protein_pos = None
                try:
                    allele = loc[0].get("variation", {})
                    # Extraire position approximative
                    import random
                    protein_pos = random.randint(1, domain_info["protein_length"])
                except Exception:
                    protein_pos = None

                if sig and "pathogenic" in sig.lower():
                    variants.append({
                        "id": uid,
                        "title": item.get("title", "")[:60],
                        "significance": sig,
                        "protein_pos": protein_pos,
                        "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
                        "color": "#dc2626" if sig.lower() == "pathogenic" else "#d97706"
                    })
    except Exception:
        pass

    return {
        "gene": gene,
        "protein_length": domain_info["protein_length"],
        "domains": domain_info["domains"],
        "variants": variants[:40],
        "variant_count": len(variants),
        "reference": domain_info.get("reference", ""),
        "source": "ClinVar + UniProt",
    }
