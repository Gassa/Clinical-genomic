import re
from collections import Counter

KNOWN_CANCER_GENES = {
    "TP53","BRCA1","BRCA2","RB1","PTEN","APC","VHL","MLH1","MSH2","MSH6",
    "PMS2","NF1","NF2","WT1","MEN1","STK11","CDH1","SMAD4","BMPR1A","EPCAM",
    "TSC1","TSC2","PTCH1","SUFU","BAP1","PALB2","CHEK2","ATM","NBN","RAD51C",
    "RAD51D","BRIP1","CDK4","CDKN2A","CDKN2B","CDKN1A","CDKN1B","RUNX1",
    "CEBPA","GATA2","KRAS","NRAS","HRAS","BRAF","MYC","MYCN","MYCL","EGFR",
    "ERBB2","ERBB3","ERBB4","MET","ALK","RET","ROS1","FGFR1","FGFR2","FGFR3",
    "FGFR4","PDGFRA","PDGFRB","KIT","FLT3","JAK2","JAK1","JAK3","STAT3",
    "STAT5A","STAT5B","PIK3CA","PIK3CB","AKT1","AKT2","AKT3","MTOR","MDM2",
    "MDM4","BCL2","BCL6","CCND1","CCND2","CCND3","CDK6","CDK2","MYB","EZH2",
    "DNMT3A","IDH1","IDH2","NPM1","NOTCH1","NOTCH2","HIF1A","VEGFA","VEGFB",
    "MUTYH","POLE","POLD1","MSH3","RAD50","MRE11","BCR","ABL1","PML","RARA",
    "ETV6","DEK","NUP214","EWS","FLI1","SS18","SSX1","SSX2","DDIT3","FUS",
    "TERT","ARID1A","ARID1B","SMARCA4","SMARCB1","CREBBP","EP300","KMT2A",
    "KMT2C","KMT2D","ASXL1","TET2","SF3B1","SRSF2","U2AF1","STAG2","CTCF",
    "FBXW7","AXIN1","AXIN2","CTNNB1","PTCH2","FOXA1","GATA3","ESR1","AR",
    "PGR","SPOP","FOXA2","HNF1A","KEAP1","NFE2L2","RHOA","RAC1","MAP2K1",
    "MAP2K2","MAP2K4","MAP3K1","MAPK1","MAPK3","RAF1","ARAF","SOX2","SOX9",
    "GNAS","GNA11","GNAQ","DICER1","DROSHA","XPO1","CSF1R","NTRK1","NTRK2",
    "NTRK3","KDR","AURKA","AURKB","PLK1","CHEK1","WEE1","ATR","ATRX","DAXX",
    "MAX","MGA","SDH","SDHA","SDHB","SDHC","SDHD","FH","MAX","FLCN","PRKAR1A",
    "AIP","CDKN1B","RET","TMEM127","MAX","VHL","PHOX2B","ALK","SDHAF2",
}

PATHOGENICITY_KEYWORDS = [
    "pathogenic", "pathogène", "likely pathogenic", "probablement pathogène",
    "variant of uncertain significance", "VUS", "benign", "bénin",
    "likely benign", "probablement bénin", "deleterious", "délétère",
    "loss of function", "gain of function", "frameshift", "nonsense",
    "splice site", "missense", "truncating", "dominant", "recessive",
]

def extract_genes_from_abstracts(articles: list) -> dict:
    all_genes = []
    gene_sources = {}
    for article in articles:
        genes = _find_genes(article["abstract"])
        for gene in genes:
            all_genes.append(gene)
            if gene not in gene_sources:
                gene_sources[gene] = []
            if not any(s["pmid"] == article["pmid"] for s in gene_sources[gene]):
                gene_sources[gene].append({
                    "pmid": article["pmid"],
                    "title": article["title"],
                    "year": article.get("year", ""),
                    "journal": article.get("journal", ""),
                    "url": article.get("url", "")
                })
    frequency = dict(Counter(all_genes).most_common())
    return {"frequency": frequency, "sources": gene_sources}


def _find_genes(text: str) -> list:
    if not text:
        return []
    found = []
    for gene in KNOWN_CANCER_GENES:
        if re.search(r'\b' + re.escape(gene) + r'\b', text, re.IGNORECASE):
            found.append(gene.upper())
    return list(set(found))


def extract_pathogenicity_context(abstract: str) -> list:
    """Extrait les phrases contenant des termes de pathogénicité."""
    sentences = re.split(r'[.!?]', abstract)
    results = []
    for s in sentences:
        s = s.strip()
        if any(kw.lower() in s.lower() for kw in PATHOGENICITY_KEYWORDS) and len(s) > 20:
            results.append(s)
    return results[:3]
