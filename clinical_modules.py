"""
clinical_modules.py — Modules cliniques avancés pour SenGenoScope v4
- Score polygénique (PRS) pour cancers courants
- Interpréteur NGS (variant calling simplifié)
- Conseil génétique structuré + arbre généalogique
- Mutations fondatrices (populations africaines, Ashkénaze, etc.)
- Comparaison guidelines (ACMG vs ENIGMA vs InSiGHT)
- Pénétrance et expression variable
- Interprétation rapports NGS en langage clinique
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SCORE POLYGÉNIQUE (PRS)
# ═══════════════════════════════════════════════════════════════════════════════

PRS_CANCERS = {
    "breast": {
        "name": "Cancer du sein",
        "icon": "🎗️",
        "population_risk": 12.0,
        "snps": [
            {"rsid": "rs2981582", "gene": "FGFR2", "or": 1.26, "description": "Variant FGFR2 — risque sein +26%"},
            {"rsid": "rs3803662", "gene": "TOX3", "or": 1.20, "description": "Variant TOX3/TNRC9"},
            {"rsid": "rs13281615", "gene": "8q24", "or": 1.14, "description": "Locus 8q24"},
            {"rsid": "rs889312", "gene": "MAP3K1", "or": 1.13, "description": "Variant MAP3K1"},
            {"rsid": "rs3817198", "gene": "LSP1", "or": 1.07, "description": "Variant LSP1"},
            {"rsid": "rs10941679", "gene": "5p12", "or": 1.19, "description": "Locus 5p12"},
            {"rsid": "rs4973768", "gene": "SLC4A7", "or": 1.11, "description": "Variant SLC4A7"},
            {"rsid": "rs6504950", "gene": "STXBP4", "or": 1.08, "description": "Variant STXBP4"},
        ],
        "reference": "Michailidou et al., Nature 2017 / BCAC"
    },
    "colorectal": {
        "name": "Cancer colorectal",
        "icon": "🔵",
        "population_risk": 4.4,
        "snps": [
            {"rsid": "rs6983267", "gene": "8q24", "or": 1.27, "description": "Locus 8q24 — oncogène MYC"},
            {"rsid": "rs10505477", "gene": "8q24", "or": 1.19, "description": "Locus 8q24 (2)"},
            {"rsid": "rs4939827", "gene": "SMAD7", "or": 1.21, "description": "Variant SMAD7 — voie TGF-β"},
            {"rsid": "rs3802842", "gene": "11q23", "or": 1.11, "description": "Locus 11q23"},
            {"rsid": "rs16892766", "gene": "8q23.3", "or": 1.25, "description": "Locus 8q23.3"},
            {"rsid": "rs9929218", "gene": "CDH1", "or": 1.10, "description": "Variant CDH1"},
            {"rsid": "rs10795668", "gene": "10p14", "or": 1.12, "description": "Locus 10p14"},
        ],
        "reference": "Huyghe et al., Nature Genetics 2019 / GECCO"
    },
    "prostate": {
        "name": "Cancer de la prostate",
        "icon": "🔷",
        "population_risk": 11.0,
        "snps": [
            {"rsid": "rs1447295", "gene": "8q24", "or": 1.43, "description": "Locus 8q24 — risque prostate +43%"},
            {"rsid": "rs6983267", "gene": "8q24", "or": 1.26, "description": "Locus 8q24 (2)"},
            {"rsid": "rs16901979", "gene": "8q24", "or": 1.79, "description": "Locus 8q24 (3)"},
            {"rsid": "rs10993994", "gene": "MSMB", "or": 1.25, "description": "Variant MSMB"},
            {"rsid": "rs4430796", "gene": "HNF1B", "or": 1.19, "description": "Variant HNF1B"},
            {"rsid": "rs2735839", "gene": "KLK3", "or": 0.83, "description": "Variant KLK3 — effet protecteur"},
        ],
        "reference": "Schumacher et al., Nature Genetics 2018"
    },
    "ovarian": {
        "name": "Cancer de l'ovaire",
        "icon": "🩷",
        "population_risk": 1.2,
        "snps": [
            {"rsid": "rs2072590", "gene": "2q31", "or": 1.16, "description": "Locus 2q31"},
            {"rsid": "rs3814113", "gene": "9p22.2", "or": 1.22, "description": "Locus 9p22.2"},
            {"rsid": "rs9303542", "gene": "SKAP1", "or": 1.11, "description": "Variant SKAP1"},
            {"rsid": "rs4691139", "gene": "5p15.33", "or": 1.09, "description": "Locus 5p15.33"},
        ],
        "reference": "Phelan et al., Nature Genetics 2017 / OCAC"
    },
    "lung": {
        "name": "Cancer du poumon",
        "icon": "🫁",
        "population_risk": 6.0,
        "snps": [
            {"rsid": "rs2736100", "gene": "TERT", "or": 1.22, "description": "Variant TERT — télomérase"},
            {"rsid": "rs402710", "gene": "TERT", "or": 1.12, "description": "Variant TERT (2)"},
            {"rsid": "rs31489", "gene": "CHRNA5", "or": 1.31, "description": "Variant CHRNA5 — récepteur nicotinique"},
            {"rsid": "rs16969968", "gene": "CHRNA5", "or": 1.28, "description": "Variant CHRNA5 (2)"},
            {"rsid": "rs7626795", "gene": "3q28", "or": 1.15, "description": "Locus 3q28"},
        ],
        "reference": "McKay et al., Nature Genetics 2017 / ILCCO"
    }
}


def calculate_prs(cancer_type: str, risk_alleles: dict) -> dict:
    """Calcule le score polygénique pour un type de cancer."""
    if cancer_type not in PRS_CANCERS:
        return {"error": f"Cancer '{cancer_type}' non reconnu"}
    
    cancer = PRS_CANCERS[cancer_type]
    total_log_or = 0.0
    snp_contributions = []
    
    for snp in cancer["snps"]:
        rsid = snp["rsid"]
        dosage = risk_alleles.get(rsid, 0)  # 0, 1, ou 2 allèles à risque
        log_or = (snp["or"] - 1) * dosage if snp["or"] > 1 else (1 - snp["or"]) * dosage * -1
        total_log_or += log_or
        snp_contributions.append({
            "rsid": rsid,
            "gene": snp["gene"],
            "or": snp["or"],
            "dosage": dosage,
            "description": snp["description"],
            "contribution": round(log_or, 3)
        })
    
    # Calcul du risque absolu basé sur le risque populationnel
    multiplier = max(0.1, 1 + total_log_or)
    absolute_risk = min(95.0, cancer["population_risk"] * multiplier)
    percentile = min(99, max(1, int(50 + total_log_or * 15)))
    
    if percentile >= 80:
        risk_category = "Élevé"
        recommendation = "Dépistage intensifié recommandé. Consultation oncogénétique."
    elif percentile >= 60:
        risk_category = "Modérément élevé"
        recommendation = "Suivi standard + vigilance accrue. Réévaluation annuelle."
    elif percentile >= 40:
        risk_category = "Moyen"
        recommendation = "Suivi standard de dépistage populationnel."
    else:
        risk_category = "Faible"
        recommendation = "Risque polygénique faible. Dépistage standard."
    
    return {
        "cancer": cancer["name"],
        "icon": cancer["icon"],
        "absolute_risk_percent": round(absolute_risk, 1),
        "population_risk_percent": cancer["population_risk"],
        "risk_multiplier": round(multiplier, 2),
        "percentile": percentile,
        "risk_category": risk_category,
        "recommendation": recommendation,
        "snp_contributions": snp_contributions,
        "reference": cancer["reference"],
        "snps_available": cancer["snps"]
    }


def get_prs_cancers():
    return [{"id": k, "name": v["name"], "icon": v["icon"], "snp_count": len(v["snps"])} for k, v in PRS_CANCERS.items()]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MUTATIONS FONDATRICES PAR POPULATION
# ═══════════════════════════════════════════════════════════════════════════════

FOUNDER_MUTATIONS = {
    "Ashkénaze (Juifs d'Europe de l'Est)": {
        "flag": "🇮🇱",
        "prevalence": "1/40 porteurs",
        "mutations": [
            {"gene": "BRCA1", "variant": "c.5266dupC (5382insC)", "frequency": "1/100", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA1", "variant": "c.68_69delAG (185delAG)", "frequency": "1/100", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA2", "variant": "c.5946delT (6174delT)", "frequency": "1/100", "cancer": "Sein/Ovaire/Pancréas", "classification": "Pathogène"},
            {"gene": "APC", "variant": "c.3920T>A (I1307K)", "frequency": "6%", "cancer": "Colorectal", "classification": "Risque augmenté"},
            {"gene": "MLH1", "variant": "Variants Lynch", "frequency": "Rare", "cancer": "Colorectal", "classification": "Pathogène"},
        ]
    },
    "Afrique de l'Ouest (Sénégal, Mali, Guinée…)": {
        "flag": "🌍",
        "prevalence": "Variable",
        "mutations": [
            {"gene": "BRCA1", "variant": "c.798_799delTT", "frequency": "Émergent", "cancer": "Sein", "classification": "Pathogène"},
            {"gene": "BRCA2", "variant": "c.7480C>T", "frequency": "Émergent", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "TP53", "variant": "c.817C>T (R273C)", "frequency": "Documenté", "cancer": "Multiples", "classification": "Pathogène"},
            {"gene": "BRCA1", "variant": "c.5266dupC", "frequency": "Documenté", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "PALB2", "variant": "Variants PALB2", "frequency": "Sous-étudié", "cancer": "Sein", "classification": "Pathogène probable"},
            {"gene": "RAD51C", "variant": "Variants RAD51C", "frequency": "Sous-étudié", "cancer": "Ovaire", "classification": "Pathogène probable"},
        ],
        "note": "⚠️ Données limitées — populations africaines sous-représentées dans les études génomiques mondiales. Recherche en cours (AWI-Gen, H3Africa)."
    },
    "Afrique du Sud (Xhosa, Zulu)": {
        "flag": "🇿🇦",
        "prevalence": "Étudiée",
        "mutations": [
            {"gene": "BRCA1", "variant": "c.2641G>T", "frequency": "Documenté Xhosa", "cancer": "Sein", "classification": "Pathogène"},
            {"gene": "BRCA2", "variant": "c.7934delC", "frequency": "Documenté", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA1", "variant": "c.1374dupA", "frequency": "Documenté", "cancer": "Sein", "classification": "Pathogène"},
            {"gene": "TP53", "variant": "c.215C>G (R72P)", "frequency": "Polymorphisme fréquent", "cancer": "Modulation risque", "classification": "VUS/Polymorphisme"},
        ]
    },
    "Islandaise / Nordique": {
        "flag": "🇮🇸",
        "prevalence": "0.6% porteurs BRCA2",
        "mutations": [
            {"gene": "BRCA2", "variant": "c.771_775del5 (999del5)", "frequency": "0.6%", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA1", "variant": "c.4964delA", "frequency": "Rare", "cancer": "Sein", "classification": "Pathogène"},
        ]
    },
    "Française / Québécoise": {
        "flag": "🇨🇦🇫🇷",
        "prevalence": "Effets fondateurs",
        "mutations": [
            {"gene": "BRCA1", "variant": "c.5266dupC", "frequency": "Commun", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA2", "variant": "c.3396delA", "frequency": "Documenté Québec", "cancer": "Sein", "classification": "Pathogène"},
            {"gene": "MLH1", "variant": "c.1731+3A>T (splice)", "frequency": "Documenté", "cancer": "Lynch/Colorectal", "classification": "Pathogène"},
            {"gene": "MUTYH", "variant": "p.Y179C + p.G396D", "frequency": "Documenté Europe", "cancer": "Polypose/Colorectal", "classification": "Pathogène"},
        ]
    },
    "Hispanique / Latino-américaine": {
        "flag": "🌎",
        "prevalence": "Variable",
        "mutations": [
            {"gene": "BRCA1", "variant": "c.185delAG", "frequency": "Documenté", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "BRCA2", "variant": "c.3922G>T (E1308X)", "frequency": "Mexique", "cancer": "Sein", "classification": "Pathogène"},
            {"gene": "BRCA1", "variant": "c.3331_3334delCAAG", "frequency": "Documenté", "cancer": "Sein/Ovaire", "classification": "Pathogène"},
            {"gene": "MLH1", "variant": "c.1732-2A>G", "frequency": "Documenté", "cancer": "Lynch", "classification": "Pathogène"},
        ]
    },
}


def get_founder_mutations(population: str = None) -> dict:
    if population and population in FOUNDER_MUTATIONS:
        return {population: FOUNDER_MUTATIONS[population]}
    return FOUNDER_MUTATIONS


def get_populations() -> list:
    return list(FOUNDER_MUTATIONS.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 3. COMPARAISON GUIDELINES
# ═══════════════════════════════════════════════════════════════════════════════

GUIDELINES_COMPARISON = {
    "BRCA1/BRCA2": {
        "gene": "BRCA1/BRCA2",
        "organizations": {
            "ACMG": {
                "classification_criteria": "5 classes: Pathogène/Prob. Pathogène/VUS/Prob. Bénin/Bénin",
                "testing_indication": "Histoire familiale, cancer sein <50 ans, cancer ovaire tout âge, triple négatif <60 ans",
                "vus_management": "Ne pas utiliser pour guider décisions cliniques. Reclassification progressive.",
                "surveillance_carriers": "IRM annuelle + mammographie dès 25 ans (BRCA1), 30 ans (BRCA2)",
                "url": "https://www.acmg.net"
            },
            "ENIGMA": {
                "classification_criteria": "Comité expert BRCA — 5 classes basées sur multiples lignes de preuves",
                "testing_indication": "Spécifique BRCA — score familial ≥10% ou cas index cancer sein/ovaire",
                "vus_management": "Études fonctionnelles spécifiques BRCA. Reclassification par consensus international.",
                "surveillance_carriers": "Recommandations nationales variables selon pays",
                "url": "https://enigmaconsortium.org"
            },
            "NCCN": {
                "classification_criteria": "Pathogène / Variante likelypathogenic / VUS / Bénin",
                "testing_indication": "Critères détaillés v3.2024 — score familial, âge, ethnie (Ashkénaze)",
                "vus_management": "Gestion basée sur histoire familiale. Ne pas modifier surveillance.",
                "surveillance_carriers": "IRM + mammographie dès 25-30 ans. Chirurgie préventive discutée.",
                "url": "https://www.nccn.org"
            }
        }
    },
    "MLH1/MSH2/MSH6/PMS2": {
        "gene": "Gènes Lynch (MMR)",
        "organizations": {
            "ACMG": {
                "classification_criteria": "5 classes standard — critères généraux",
                "testing_indication": "MSI-H tumeur, critères Amsterdam II, Bethesda révisés, cancer colorectal <50 ans",
                "vus_management": "Analyse ségrégation familiale. Tests fonctionnels MMR.",
                "surveillance_carriers": "Coloscopie tous 1-2 ans dès 25 ans",
                "url": "https://www.acmg.net"
            },
            "InSiGHT": {
                "classification_criteria": "Critères spécifiques Lynch — 5 classes avec pondération MSI/IHC/fonctionnel",
                "testing_indication": "Expert panel Lynch international — MSI/IHC obligatoire avant test germinal",
                "vus_management": "Système de scoring dédié Lynch — intégration données tumorales indispensable",
                "surveillance_carriers": "Coloscopie annuelle. Gynécologie (MSH2/MLH1). Urologie (MSH2).",
                "url": "https://www.insight-group.org"
            },
            "NCCN": {
                "classification_criteria": "Pathogène / LP / VUS selon contexte tumoral",
                "testing_indication": "Test universel tumeurs colorectales recommandé v2.2024",
                "vus_management": "Test tumeur MSI/IHC prioritaire pour reclassification",
                "surveillance_carriers": "Coloscopie 1-2 ans. Hystérectomie/annexectomie discutée femmes >35-40 ans.",
                "url": "https://www.nccn.org"
            }
        }
    },
    "TP53": {
        "gene": "TP53 (Li-Fraumeni)",
        "organizations": {
            "ACMG": {
                "classification_criteria": "5 classes standard — attention aux faux positifs somatiques",
                "testing_indication": "Critères Chompret 2015: sarcome <46 ans + parent cancer <56 ans, ou ≥2 cancers LFS",
                "vus_management": "Prudence — TP53 très muté somatiquement. Confirmer germinal.",
                "surveillance_carriers": "Protocole MDACC/Toronto: IRM corps entier annuelle, mammographie, dermatologie",
                "url": "https://www.acmg.net"
            },
            "NCCN": {
                "classification_criteria": "Pathogène / LP / VUS — distinction germinal vs somatique critique",
                "testing_indication": "Critères Chompret + carcinome corticosurrénalien, médulloblastome, carcinome choroïdien",
                "vus_management": "Test somatique tumeur pour distinguer germinal/somatique avant conclusion",
                "surveillance_carriers": "IRM corps entier annuelle + mammographie + endoscopie digestive",
                "url": "https://www.nccn.org"
            }
        }
    },
    "APC": {
        "gene": "APC (FAP / Polypose)",
        "organizations": {
            "ACMG": {
                "classification_criteria": "5 classes — attention variant I1307K (Ashkénaze) = risque modéré",
                "testing_indication": ">10 polypes adénomateux synchrones, polypose familiale confirmée",
                "vus_management": "Études fonctionnelles domaine SAMP/ARM. Coloscopie chez apparentés.",
                "surveillance_carriers": "Coloscopie annuelle dès 10-15 ans. Chirurgie prophylactique discutée.",
                "url": "https://www.acmg.net"
            },
            "NCCN": {
                "classification_criteria": "Pathogène / Attenuée (AFAP) / VUS",
                "testing_indication": "≥20 polypes, ou ≥10 + histoire familiale, ou desmoïde/ostéome/CHRPE",
                "vus_management": "Surveillance endoscopique renforcée. Coloscopie si doute familial.",
                "surveillance_carriers": "FAP: coloscopie annuelle + duodénoscopie. Prophylaxie AINS (celecoxib).",
                "url": "https://www.nccn.org"
            }
        }
    }
}


def get_guidelines_comparison(gene_group: str = None) -> dict:
    if gene_group and gene_group in GUIDELINES_COMPARISON:
        return {gene_group: GUIDELINES_COMPARISON[gene_group]}
    return GUIDELINES_COMPARISON


def get_gene_groups() -> list:
    return list(GUIDELINES_COMPARISON.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PÉNÉTRANCE ET EXPRESSION VARIABLE
# ═══════════════════════════════════════════════════════════════════════════════

PENETRANCE_DATA = {
    "BRCA1": {
        "gene": "BRCA1",
        "inheritance": "Autosomique dominant",
        "penetrance_type": "Incomplète, âge-dépendante",
        "lifetime_risks": {
            "Sein (lifetime)": {"risk": "55-72%", "population": "12%", "source": "Kuchenbaecker 2017"},
            "Ovaire (lifetime)": {"risk": "44%", "population": "1.2%", "source": "Kuchenbaecker 2017"},
            "Pancréas": {"risk": "1-3%", "population": "0.3%", "source": "NCCN"},
            "Col utérin": {"risk": "Légèrement augmenté", "population": "Standard", "source": "NCCN"},
        },
        "age_specific": [
            {"age": 30, "breast_risk": "3.2%", "ovarian_risk": "0.4%"},
            {"age": 40, "breast_risk": "11.4%", "ovarian_risk": "3.4%"},
            {"age": 50, "breast_risk": "24.0%", "ovarian_risk": "11.2%"},
            {"age": 60, "breast_risk": "38.8%", "ovarian_risk": "21.8%"},
            {"age": 70, "breast_risk": "55.0%", "ovarian_risk": "35.0%"},
            {"age": 80, "breast_risk": "72.0%", "ovarian_risk": "44.0%"},
        ],
        "modifiers": [
            "Antécédents familiaux étendus → augmentation du risque",
            "Contraceptifs oraux (≥5 ans) → réduction risque ovaire -50%",
            "Parité → légère réduction risque sein, augmentation risque ovaire",
            "Tabac → risque légèrement augmenté",
            "IMC élevé → risque sein post-ménopausique augmenté",
        ],
        "expressivity": "Variable — même variant peut donner cancer à 35 ans dans une famille, 70 ans dans une autre"
    },
    "BRCA2": {
        "gene": "BRCA2",
        "inheritance": "Autosomique dominant",
        "penetrance_type": "Incomplète, généralement plus tardive que BRCA1",
        "lifetime_risks": {
            "Sein (lifetime)": {"risk": "45-69%", "population": "12%", "source": "Kuchenbaecker 2017"},
            "Ovaire (lifetime)": {"risk": "17%", "population": "1.2%", "source": "Kuchenbaecker 2017"},
            "Sein masculin": {"risk": "8%", "population": "0.1%", "source": "NCCN"},
            "Pancréas": {"risk": "3-7%", "population": "0.3%", "source": "NCCN"},
            "Mélanome": {"risk": "Augmenté 2-3x", "population": "Standard", "source": "NCCN"},
            "Prostate": {"risk": "20-25% (avant 65 ans)", "population": "Standard", "source": "NCCN"},
        },
        "age_specific": [
            {"age": 30, "breast_risk": "2.1%", "ovarian_risk": "0.1%"},
            {"age": 40, "breast_risk": "8.0%", "ovarian_risk": "0.8%"},
            {"age": 50, "breast_risk": "18.5%", "ovarian_risk": "3.4%"},
            {"age": 60, "breast_risk": "32.0%", "ovarian_risk": "7.5%"},
            {"age": 70, "breast_risk": "45.0%", "ovarian_risk": "12.0%"},
            {"age": 80, "breast_risk": "69.0%", "ovarian_risk": "17.0%"},
        ],
        "modifiers": [
            "Localisation variant: Ovarian Cancer Cluster Region (OCCR) = risque ovaire accru",
            "Contraceptifs oraux → réduction risque ovaire",
            "Salpingo-oophorectomie prophylactique → réduction risque sein 50%",
        ],
        "expressivity": "Variable — risque ovaire plus faible que BRCA1 mais significatif"
    },
    "MLH1": {
        "gene": "MLH1",
        "inheritance": "Autosomique dominant",
        "penetrance_type": "Élevée mais variable",
        "lifetime_risks": {
            "Colorectal": {"risk": "40-80%", "population": "4.4%", "source": "Moller 2018"},
            "Endomètre": {"risk": "25-60%", "population": "2.7%", "source": "Moller 2018"},
            "Ovaire": {"risk": "10-15%", "population": "1.2%", "source": "NCCN"},
            "Gastrique": {"risk": "6-13%", "population": "0.8%", "source": "NCCN"},
            "Voies urinaires": {"risk": "8-28%", "population": "Standard", "source": "NCCN"},
        },
        "age_specific": [
            {"age": 40, "crc_risk": "10-15%"},
            {"age": 50, "crc_risk": "20-40%"},
            {"age": 70, "crc_risk": "40-80%"},
        ],
        "modifiers": [
            "Aspirine régulière → réduction significative risque colorectal (CAPP2 study)",
            "Tabac → augmente risque colorectal Lynch",
            "IMC élevé → augmente risque endomètre",
        ],
        "expressivity": "Pénétrance très variable selon le variant spécifique de MLH1"
    },
    "TP53": {
        "gene": "TP53 (Li-Fraumeni)",
        "inheritance": "Autosomique dominant",
        "penetrance_type": "Très élevée (~90% lifetime)",
        "lifetime_risks": {
            "Cancer (tous types)": {"risk": "~90%", "population": "40%", "source": "Bougeard 2015"},
            "Sein": {"risk": "54% (avant 70 ans)", "population": "12%", "source": "Bougeard 2015"},
            "Sarcome": {"risk": "22%", "population": "<1%", "source": "Bougeard 2015"},
            "SNC": {"risk": "6%", "population": "<1%", "source": "Bougeard 2015"},
            "Leucémie/MDS": {"risk": "4%", "population": "<1%", "source": "Bougeard 2015"},
            "Corticosurrénale": {"risk": "3%", "population": "<0.1%", "source": "Bougeard 2015"},
        },
        "age_specific": [
            {"age": 20, "cancer_risk": "12%"},
            {"age": 30, "cancer_risk": "35%"},
            {"age": 40, "cancer_risk": "56%"},
            {"age": 50, "cancer_risk": "73%"},
            {"age": 60, "cancer_risk": "83%"},
            {"age": 70, "cancer_risk": "~90%"},
        ],
        "modifiers": [
            "Polymorphisme R72P (c.215C>G) — modifie légèrement l'apoptose",
            "Domaine de liaison ADN (codons 248, 273, 175) — variants chauds plus sévères",
            "Exposition aux rayonnements ionisants — à éviter absolument (risque secondaire)",
        ],
        "expressivity": "Très variable — cancers pédiatriques possibles, spectre très large"
    },
}


def get_penetrance_data(gene: str = None) -> dict:
    if gene and gene.upper() in PENETRANCE_DATA:
        return PENETRANCE_DATA[gene.upper()]
    return PENETRANCE_DATA


def get_penetrance_genes() -> list:
    return list(PENETRANCE_DATA.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INTERPRÉTEUR NGS EN LANGAGE CLINIQUE
# ═══════════════════════════════════════════════════════════════════════════════

CONSEQUENCE_EXPLANATIONS = {
    "stop_gained": {
        "technical": "stop_gained / nonsense",
        "clinical_fr": "Variant non-sens : création prématurée d'un codon stop",
        "clinical_en": "Nonsense variant: premature stop codon created",
        "impact": "Élevé",
        "acmg_hint": "PVS1 applicable si perte de fonction est mécanisme pathogène",
        "color": "red"
    },
    "frameshift_variant": {
        "technical": "frameshift_variant",
        "clinical_fr": "Variant frameshift : décalage du cadre de lecture → protéine tronquée",
        "clinical_en": "Frameshift variant: reading frame shift → truncated protein",
        "impact": "Élevé",
        "acmg_hint": "PVS1 applicable — perte de fonction quasi-certaine",
        "color": "red"
    },
    "splice_donor_variant": {
        "technical": "splice_donor_variant",
        "clinical_fr": "Variant site donneur d'épissage : altération probable du transcrit ARN",
        "clinical_en": "Splice donor variant: probable RNA transcript alteration",
        "impact": "Élevé",
        "acmg_hint": "PVS1 applicable si épissage confirmé par ARN",
        "color": "red"
    },
    "splice_acceptor_variant": {
        "technical": "splice_acceptor_variant",
        "clinical_fr": "Variant site accepteur d'épissage : altération probable du transcrit ARN",
        "clinical_en": "Splice acceptor variant: probable RNA transcript alteration",
        "impact": "Élevé",
        "acmg_hint": "PVS1 applicable si épissage confirmé par ARN",
        "color": "red"
    },
    "missense_variant": {
        "technical": "missense_variant",
        "clinical_fr": "Variant faux-sens : substitution d'un acide aminé par un autre",
        "clinical_en": "Missense variant: one amino acid substituted for another",
        "impact": "Modéré",
        "acmg_hint": "Évaluer PolyPhen/SIFT/CADD. Critères PM1, PM2, PP2, PP3 applicables.",
        "color": "orange"
    },
    "synonymous_variant": {
        "technical": "synonymous_variant",
        "clinical_fr": "Variant synonyme : même acide aminé — vérifier impact sur épissage",
        "clinical_en": "Synonymous variant: same amino acid — check splicing impact",
        "impact": "Faible",
        "acmg_hint": "Généralement BP7 (bénin). Vérifier prédicteurs d'épissage (SpliceAI).",
        "color": "green"
    },
    "inframe_insertion": {
        "technical": "inframe_insertion",
        "clinical_fr": "Insertion en phase : ajout d'acide(s) aminé(s) sans décalage du cadre",
        "clinical_en": "In-frame insertion: amino acid(s) added without frameshift",
        "impact": "Modéré",
        "acmg_hint": "PM4 applicable. Évaluer impact sur domaine fonctionnel.",
        "color": "orange"
    },
    "inframe_deletion": {
        "technical": "inframe_deletion",
        "clinical_fr": "Délétion en phase : suppression d'acide(s) aminé(s) sans décalage du cadre",
        "clinical_en": "In-frame deletion: amino acid(s) removed without frameshift",
        "impact": "Modéré",
        "acmg_hint": "PM4 applicable. Évaluer impact sur domaine fonctionnel.",
        "color": "orange"
    },
    "3_prime_UTR_variant": {
        "technical": "3_prime_UTR_variant",
        "clinical_fr": "Variant région 3'UTR : impact possible sur stabilité ARNm ou régulation",
        "clinical_en": "3'UTR variant: possible impact on mRNA stability or regulation",
        "impact": "Faible à modéré",
        "acmg_hint": "Généralement bénin sauf si site miRNA démontré.",
        "color": "green"
    },
    "5_prime_UTR_variant": {
        "technical": "5_prime_UTR_variant",
        "clinical_fr": "Variant région 5'UTR : impact possible sur initiation traduction",
        "clinical_en": "5'UTR variant: possible impact on translation initiation",
        "impact": "Faible à modéré",
        "acmg_hint": "Vérifier si création codon ATG aberrant ou destruction Kozak.",
        "color": "yellow"
    },
    "intron_variant": {
        "technical": "intron_variant",
        "clinical_fr": "Variant intronique profond : impact faible sauf si proche du site d'épissage",
        "clinical_en": "Deep intronic variant: low impact unless near splice site",
        "impact": "Faible",
        "acmg_hint": "BP7 applicable. Vérifier distance au site d'épissage (<10bp = évaluer).",
        "color": "green"
    },
}


def interpret_ngs_variant(consequence: str, gene: str, hgvsc: str = "", hgvsp: str = "",
                          af_gnomad: float = None, acmg_classification: str = "") -> dict:
    """Interprète un variant NGS en langage clinique clair."""
    
    consequence_clean = consequence.lower().replace(" ", "_")
    explanation = CONSEQUENCE_EXPLANATIONS.get(consequence_clean, {
        "technical": consequence,
        "clinical_fr": f"Variant de type '{consequence}' — évaluation spécialisée requise",
        "clinical_en": f"Variant type '{consequence}' — specialist evaluation required",
        "impact": "À évaluer",
        "acmg_hint": "Classification selon contexte clinique et familial",
        "color": "gray"
    })
    
    # Fréquence population
    freq_interpretation = ""
    if af_gnomad is not None:
        if af_gnomad > 0.05:
            freq_interpretation = f"⚠️ Variant fréquent en population générale (AF={af_gnomad:.4f}) → argument fort pour bénignité (BA1/BS1)"
        elif af_gnomad > 0.01:
            freq_interpretation = f"Variant peu fréquent (AF={af_gnomad:.4f}) → BS1 possible selon prévalence maladie"
        elif af_gnomad > 0:
            freq_interpretation = f"Variant rare en population générale (AF={af_gnomad:.6f}) → PM2 applicable"
        else:
            freq_interpretation = "Variant absent de gnomAD → PM2 fort (variant rare)"
    
    # Résumé clinique
    clinical_summary = f"""
Ce variant {gene} ({hgvsc or 'position non précisée'}) est un variant de type **{explanation['clinical_fr']}**.

**Impact fonctionnel prédit :** {explanation['impact']}

**Notation HGVS :** {hgvsp or 'Protéine non affectée ou non précisée'}

{freq_interpretation}

**Orientation ACMG :** {explanation['acmg_hint']}
    """.strip()
    
    return {
        "gene": gene,
        "consequence": consequence,
        "explanation": explanation,
        "hgvsc": hgvsc,
        "hgvsp": hgvsp,
        "af_gnomad": af_gnomad,
        "frequency_interpretation": freq_interpretation,
        "clinical_summary": clinical_summary,
        "acmg_classification": acmg_classification,
    }


def parse_ngs_report(text: str) -> list:
    """Parse un rapport NGS brut et extrait les variants."""
    import re
    variants = []
    
    # Patterns courants dans les rapports NGS
    # Format: GENE c.XXX p.XXX consequence classification
    patterns = [
        r'([A-Z][A-Z0-9]+)\s+(c\.[^\s]+)\s+(p\.[^\s]+)',
        r'([A-Z][A-Z0-9]+)\s+(c\.[^\s]+)',
        r'(chr\w+):(\d+)\s*([ATCG]+)\s*>\s*([ATCG]+)',
    ]
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    variants.append({
                        "raw_line": line,
                        "gene": groups[0] if not groups[0].startswith('chr') else "",
                        "hgvsc": groups[1] if len(groups) > 1 else "",
                        "hgvsp": groups[2] if len(groups) > 2 else "",
                        "parsed": True
                    })
                    break
        else:
            if len(line) > 5:
                variants.append({"raw_line": line, "parsed": False})
    
    return variants[:20]
