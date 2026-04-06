from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io

DARK_BLUE  = colors.HexColor("#0d2137")
TEAL       = colors.HexColor("#0891b2")
LIGHT_GRAY = colors.HexColor("#f1f5f9")
MID_GRAY   = colors.HexColor("#94a3b8")
RED_ACCENT = colors.HexColor("#dc2626")
GREEN      = colors.HexColor("#16a34a")


def generate_pdf_report(query: str, articles: list, gene_data: dict, clinvar_results: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", fontSize=20, textColor=DARK_BLUE,
                                 fontName="Helvetica-Bold", spaceAfter=4,
                                 alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("Sub", fontSize=11, textColor=TEAL,
                                    fontName="Helvetica", spaceAfter=2,
                                    alignment=TA_CENTER)
    author_style = ParagraphStyle("Author", fontSize=10, textColor=MID_GRAY,
                                  fontName="Helvetica-Oblique", spaceAfter=16,
                                  alignment=TA_CENTER)
    h2_style = ParagraphStyle("H2", fontSize=13, textColor=DARK_BLUE,
                               fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", fontSize=9, textColor=colors.black,
                                fontName="Helvetica", spaceAfter=4, leading=14)
    small_style = ParagraphStyle("Small", fontSize=8, textColor=MID_GRAY,
                                 fontName="Helvetica-Oblique", spaceAfter=2)

    story = []
    now = datetime.now().strftime("%d %B %Y à %H:%M")

    # En-tête
    story.append(Paragraph("SenGenoScope", title_style))
    story.append(Paragraph("Rapport d'analyse génomique clinique", subtitle_style))
    story.append(Paragraph(f"Dr. Moustapha Gassama  ·  {now}", author_style))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=12))

    # Résumé
    story.append(Paragraph("Résumé de la recherche", h2_style))
    freq = gene_data.get("frequency", {})
    top_genes = list(freq.keys())[:5]
    summary_data = [
        ["Requête", query],
        ["Articles analysés", str(len(articles))],
        ["Gènes identifiés", str(len(freq))],
        ["Top gènes", ", ".join(top_genes) if top_genes else "Aucun"],
        ["Variants ClinVar", str(len([c for c in clinvar_results if "error" not in c]))],
    ]
    t = Table(summary_data, colWidths=[5*cm, 12*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Gènes
    if freq:
        story.append(Paragraph("Gènes identifiés (triés par fréquence)", h2_style))
        gene_rows = [["Rang", "Gène", "Articles", "Sources"]]
        sources = gene_data.get("sources", {})
        for i, (gene, count) in enumerate(list(freq.items())[:20], 1):
            srcs = sources.get(gene, [])
            src_text = "; ".join([s.get("journal", "") or f"PMID {s['pmid']}" for s in srcs[:2]])
            gene_rows.append([str(i), gene, str(count), src_text])
        gt = Table(gene_rows, colWidths=[1.5*cm, 3*cm, 2*cm, 10.5*cm])
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ]))
        story.append(gt)
        story.append(Spacer(1, 0.5*cm))

    # ClinVar
    valid_cv = [c for c in clinvar_results if "error" not in c and c.get("title")]
    if valid_cv:
        story.append(Paragraph("Variants ClinVar associés", h2_style))
        for v in valid_cv[:10]:
            sig = v.get("significance", "")
            if "pathogenic" in sig.lower() or "pathogène" in sig.lower():
                sig_color = RED_ACCENT
            elif "benign" in sig.lower() or "bénin" in sig.lower():
                sig_color = GREEN
            else:
                sig_color = TEAL
            story.append(Paragraph(
                f'<font color="#{sig_color.hexval()[2:]}"><b>{v.get("gene","")}</b></font> — {v.get("title","")}',
                body_style
            ))
            story.append(Paragraph(f'Signification clinique : {sig}  |  {v.get("url","")}', small_style))
        story.append(Spacer(1, 0.4*cm))

    # Articles
    if articles:
        story.append(Paragraph("Articles PubMed analysés", h2_style))
        for art in articles[:15]:
            story.append(Paragraph(f'<b>{art.get("title","")}</b>', body_style))
            story.append(Paragraph(
                f'{art.get("authors","")} · {art.get("journal","")} ({art.get("year","")}) · PMID {art.get("pmid","")}',
                small_style
            ))
        story.append(Spacer(1, 0.4*cm))

    # Pied de page
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceBefore=12))
    story.append(Paragraph(
        "Rapport généré par SenGenoScope · Dr. Moustapha Gassama · Usage clinique confidentiel",
        ParagraphStyle("Footer", fontSize=7, textColor=MID_GRAY,
                       fontName="Helvetica-Oblique", alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
