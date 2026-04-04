"""
pubmed.py — Module PubMed NCBI amélioré pour SenGenoScope v5
- Pas de limite d'articles (configurable jusqu'à 10 000)
- Extraction enrichie : DOI, MeSH, type publication, abstract structuré
- Source officielle : https://www.ncbi.nlm.nih.gov/home/develop/api/
"""

import requests
import xml.etree.ElementTree as ET

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MAX_FETCH_BATCH   = 200  # Limite NCBI par requête


def search_pubmed(query: str, max_results: int = 0, sort: str = "relevance") -> list:
    """
    Recherche PubMed. max_results=0 = tous les résultats (jusqu'à 10000).
    Source: https://www.ncbi.nlm.nih.gov/books/NBK25499/
    """
    # Obtenir le total
    try:
        r = requests.get(PUBMED_SEARCH_URL, params={"db":"pubmed","term":query,"retmax":1,"retmode":"json"}, timeout=12)
        total = int(r.json()["esearchresult"].get("count", 0))
    except Exception:
        total = max_results or 100

    retmax = max_results if max_results > 0 else min(total, 200)  # Cap 200 pour eviter timeout Render
    params = {"db":"pubmed","term":query,"retmax":retmax,"retmode":"json","sort":sort,"usehistory":"y"}
    try:
        r = requests.get(PUBMED_SEARCH_URL, params=params, timeout=20)
        r.raise_for_status()
        return r.json()["esearchresult"].get("idlist", [])
    except Exception:
        return []


def fetch_articles(pmids: list) -> list:
    """Récupère les articles par batch de 200. Extrait toutes métadonnées."""
    if not pmids:
        return []
    articles = []
    for i in range(0, len(pmids), MAX_FETCH_BATCH):
        batch = pmids[i:i+MAX_FETCH_BATCH]
        try:
            r = requests.get(PUBMED_FETCH_URL,
                params={"db":"pubmed","id":",".join(batch),"rettype":"abstract","retmode":"xml"},
                timeout=15)
            r.raise_for_status()
            articles.extend(_parse_xml(r.text))
        except Exception:
            continue
    return articles


def _parse_xml(xml_text: str) -> list:
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for article in root.findall(".//PubmedArticle"):
        try:
            medline = article.find("MedlineCitation")
            art = medline.find("Article") if medline else None
            if not art:
                continue

            pmid_el = medline.find("PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = art.find("ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else ""

            abstract_parts = []
            for ab in art.findall(".//AbstractText"):
                label = ab.get("Label","")
                text = "".join(ab.itertext())
                abstract_parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(abstract_parts)

            authors_list = []
            for author in art.findall(".//Author"):
                ln = author.findtext("LastName","")
                fn = author.findtext("ForeName","")
                if ln: authors_list.append(f"{ln} {fn}".strip())
            authors = ", ".join(authors_list[:6])
            if len(authors_list) > 6: authors += " et al."

            journal_el = art.find("Journal/Title") or art.find("Journal/ISOAbbreviation")
            journal = journal_el.text if journal_el is not None else ""

            year = ""
            for dp in ["Journal/JournalIssue/PubDate/Year","Journal/JournalIssue/PubDate/MedlineDate","ArticleDate/Year"]:
                el = art.find(dp)
                if el is not None and el.text: year = el.text[:4]; break

            doi = ""
            for id_el in article.findall(".//ArticleId"):
                if id_el.get("IdType") == "doi": doi = id_el.text or ""; break

            pub_types = [pt.text for pt in art.findall(".//PublicationType") if pt.text and pt.text != "Journal Article"]
            mesh_terms = [mh.text for mh in medline.findall(".//MeshHeading/DescriptorName") if mh.text][:10] if medline else []
            affil_el = art.find(".//AffiliationInfo/Affiliation")
            affiliation = (affil_el.text or "")[:150] if affil_el is not None else ""

            articles.append({
                "pmid": pmid, "title": title, "abstract": abstract,
                "authors": authors, "journal": journal, "year": year,
                "doi": doi, "doi_url": f"https://doi.org/{doi}" if doi else "",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pub_types": pub_types, "mesh_terms": mesh_terms, "affiliation": affiliation,
                "volume": art.findtext("Journal/JournalIssue/Volume",""),
                "pages": art.findtext("Pagination/MedlinePgn",""),
            })
        except Exception:
            continue
    return articles


def get_article_count(query: str) -> int:
    try:
        r = requests.get(PUBMED_SEARCH_URL, params={"db":"pubmed","term":query,"retmax":0,"retmode":"json"}, timeout=8)
        return int(r.json()["esearchresult"].get("count",0))
    except Exception:
        return 0
