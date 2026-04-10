from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
from datetime import datetime
import io

# ── Palette SenGenoScope ────────────────────────────────────
DARK_BLUE   = colors.HexColor("#0d2137")
TEAL        = colors.HexColor("#0891b2")
TEAL_LIGHT  = colors.HexColor("#e0f2fe")
PURPLE      = colors.HexColor("#7c3aed")
PURPLE_LIGHT= colors.HexColor("#ede9fe")
LIGHT_GRAY  = colors.HexColor("#f1f5f9")
MID_GRAY    = colors.HexColor("#94a3b8")
DARK_GRAY   = colors.HexColor("#475569")
RED_ACCENT  = colors.HexColor("#dc2626")
RED_LIGHT   = colors.HexColor("#fef2f2")
GREEN       = colors.HexColor("#16a34a")
GREEN_LIGHT = colors.HexColor("#f0fdf4")
ORANGE      = colors.HexColor("#c2410c")
WHITE       = colors.white


class SGSDocTemplate(BaseDocTemplate):
    """Template avec en-tête et pied de page sur chaque page."""

    def __init__(self, buffer, query="", **kwargs):
        self.query = query
        BaseDocTemplate.__init__(self, buffer, **kwargs)
        frame = Frame(
            self.leftMargin, self.bottomMargin,
            self.width, self.height - 1.5*cm,
            id="main"
        )
        template = PageTemplate(id="sgs", frames=frame, onPage=self._draw_page)
        self.addPageTemplates([template])

    def _draw_page(self, c, doc):
        c.saveState()
        w, h = A4

        # Bande en-tête
        c.setFillColor(DARK_BLUE)
        c.rect(0, h - 1.8*cm, w, 1.8*cm, fill=1, stroke=0)

        # Logo textuel
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1.8*cm, h - 1.2*cm, "SenGenoScope")

        # Sous-titre en-tête
        c.setFillColor(TEAL)
        c.setFont("Helvetica", 8)
        c.drawString(1.8*cm, h - 1.55*cm, "Clinical Oncogenomics & Oncopharmacogenomics Platform")

        # Date à droite
        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica", 8)
        date_str = datetime.now().strftime("%d/%m/%Y")
        c.drawRightString(w - 1.8*cm, h - 1.2*cm, date_str)

        # Numéro de page
        c.setFont("Helvetica", 7)
        c.drawRightString(w - 1.8*cm, h - 1.55*cm, f"Page {doc.page}")

        # Ligne de séparation
        c.setStrokeColor(TEAL)
        c.setLineWidth(1.5)
        c.line(0, h - 1.8*cm, w, h - 1.8*cm)

        # Pied de page
        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.line(1.8*cm, 1.5*cm, w - 1.8*cm, 1.5*cm)

        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica-Oblique", 6.5)
        footer = "Rapport généré par SenGenoScope · Dr. Moustapha Gassama · Oncogénéticien médical · Usage clinique confidentiel"
        c.drawCentredString(w/2, 1.0*cm, footer)

        # Filigrane CONFIDENTIEL (léger)
        c.saveState()
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.setFont("Helvetica-Bold", 52)
        c.translate(w/2, h/2)
        c.rotate(35)
        c.drawCentredString(0, 0, "CONFIDENTIEL")
        c.restoreState()

        c.restoreState()


def _style(name, **kwargs):
    base = {
        "fontName": "Helvetica",
        "fontSize": 9,
        "textColor": colors.black,
        "spaceAfter": 4,
        "leading": 13,
    }
    base.update(kwargs)
    return ParagraphStyle(name, **base)


def generate_pdf_report(query: str, articles: list, gene_data: dict, clinvar_results: list) -> bytes:
    buffer = io.BytesIO()

    doc = SGSDocTemplate(
        buffer,
        query=query,
        pagesize=A4,
        leftMargin=1.8*cm,
        rightMargin=1.8*cm,
        topMargin=2.4*cm,
        bottomMargin=2.2*cm
    )

    # ── Styles ──────────────────────────────────────────────
    title_s   = _style("T", fontSize=18, textColor=DARK_BLUE, fontName="Helvetica-Bold",
                        spaceAfter=3, alignment=TA_CENTER)
    sub_s     = _style("S", fontSize=11, textColor=TEAL, spaceAfter=2, alignment=TA_CENTER)
    author_s  = _style("A", fontSize=9, textColor=DARK_GRAY, spaceAfter=14,
                        alignment=TA_CENTER, fontName="Helvetica-Oblique")
    h2_s      = _style("H2", fontSize=12, textColor=DARK_BLUE, fontName="Helvetica-Bold",
                        spaceBefore=12, spaceAfter=6)
    h3_s      = _style("H3", fontSize=10, textColor=TEAL, fontName="Helvetica-Bold",
                        spaceBefore=8, spaceAfter=4)
    body_s    = _style("B", fontSize=9, spaceAfter=4, leading=14)
    small_s   = _style("Sm", fontSize=7.5, textColor=DARK_GRAY,
                        fontName="Helvetica-Oblique", spaceAfter=2)
    justify_s = _style("J", fontSize=9, spaceAfter=4, leading=14, alignment=TA_JUSTIFY)
    badge_s   = _style("Bg", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold",
                        alignment=TA_CENTER, spaceAfter=0)

    story = []
    now = datetime.now().strftime("%d %B %Y à %H:%M")

    # ── Page de titre ────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("Rapport d'Analyse Génomique Clinique", title_s))
    story.append(Paragraph("Oncogénomique &amp; Oncopharmacogénomique", sub_s))
    story.append(Paragraph(
        f"Dr. Moustapha Gassama — Oncogénéticien médical · Public Health Data Scientist<br/>"
        f"Généré le {now}",
        author_s
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=10))

    # Requête en bandeau
    req_table = Table(
        [[Paragraph(f"<b>Requête analysée :</b> {query}", body_s)]],
        colWidths=[doc.width]
    )
    req_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), TEAL_LIGHT),
        ("ROUNDEDCORNERS", [6,6,6,6]),
        ("PADDING", (0,0), (-1,-1), 8),
        ("BOX", (0,0), (-1,-1), 0.5, TEAL),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Résumé statistique ───────────────────────────────────
    story.append(Paragraph("Résumé de l'analyse", h2_s))
    freq = gene_data.get("frequency", {})
    top_genes = list(freq.keys())[:5]
    valid_cv = [c for c in clinvar_results if "error" not in c and c.get("title")]

    # Cartes statistiques
    stats = [
        ("📄 Articles PubMed", str(len(articles)), TEAL_LIGHT, TEAL),
        ("🧬 Gènes identifiés", str(len(freq)), PURPLE_LIGHT, PURPLE),
        ("⚠️ Variants ClinVar", str(len(valid_cv)), RED_LIGHT, RED_ACCENT),
        ("🏆 Top gène", top_genes[0] if top_genes else "—", GREEN_LIGHT, GREEN),
    ]
    stat_cells = []
    for label, val, bg, fg in stats:
        cell_content = [
            Paragraph(f'<font color="#{fg.hexval()[2:]}"><b>{val}</b></font>',
                     _style("SV", fontSize=18, fontName="Helvetica-Bold",
                            alignment=TA_CENTER, textColor=fg)),
            Paragraph(label, _style("SL", fontSize=7.5, alignment=TA_CENTER,
                                    textColor=DARK_GRAY)),
        ]
        stat_cells.append(cell_content)

    stat_table = Table([stat_cells], colWidths=[doc.width/4]*4)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), TEAL_LIGHT),
        ("BACKGROUND", (1,0), (1,-1), PURPLE_LIGHT),
        ("BACKGROUND", (2,0), (2,-1), RED_LIGHT),
        ("BACKGROUND", (3,0), (3,-1), GREEN_LIGHT),
        ("PADDING", (0,0), (-1,-1), 10),
        ("BOX", (0,0), (-1,-1), 0.3, MID_GRAY),
        ("INNERGRID", (0,0), (-1,-1), 0.3, MID_GRAY),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(stat_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Gènes ────────────────────────────────────────────────
    if freq:
        story.append(Paragraph("Gènes identifiés (triés par fréquence)", h2_s))
        gene_rows = [[
            Paragraph("<b>Rang</b>", body_s),
            Paragraph("<b>Gène</b>", body_s),
            Paragraph("<b>Mentions</b>", body_s),
            Paragraph("<b>Sources principales</b>", body_s),
        ]]
        sources = gene_data.get("sources", {})
        for i, (gene, count) in enumerate(list(freq.items())[:20], 1):
            srcs = sources.get(gene, [])
            src_text = "; ".join([s.get("journal","") or f"PMID {s['pmid']}" for s in srcs[:2]])
            bg = LIGHT_GRAY if i % 2 == 0 else WHITE
            gene_rows.append([
                Paragraph(str(i), small_s),
                Paragraph(f"<b>{gene}</b>", body_s),
                Paragraph(str(count), body_s),
                Paragraph(src_text or "—", small_s),
            ])
        gt = Table(gene_rows, colWidths=[1.5*cm, 3*cm, 2.2*cm, doc.width-6.7*cm])
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK_BLUE),
            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0,0), (-1,-1), 0.3, MID_GRAY),
            ("PADDING", (0,0), (-1,-1), 5),
            ("ALIGN", (2,0), (2,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(gt)
        story.append(Spacer(1, 0.5*cm))

    # ── ClinVar ──────────────────────────────────────────────
    if valid_cv:
        story.append(Paragraph("Variants ClinVar associés", h2_s))
        for v in valid_cv[:12]:
            sig = v.get("significance", "")
            if "pathogenic" in sig.lower() or "pathogène" in sig.lower():
                box_color = RED_LIGHT
                sig_color = RED_ACCENT
                badge = "PATHOGÈNE"
            elif "benign" in sig.lower() or "bénin" in sig.lower():
                box_color = GREEN_LIGHT
                sig_color = GREEN
                badge = "BÉNIN"
            else:
                box_color = TEAL_LIGHT
                sig_color = TEAL
                badge = "INCERTAIN"

            row = [[
                Paragraph(
                    f'<font color="#{sig_color.hexval()[2:]}"><b>{v.get("gene","")}</b></font> — {v.get("title","")}',
                    body_s
                ),
                Paragraph(
                    f'<font color="#{sig_color.hexval()[2:]}"><b>{badge}</b></font>',
                    _style("Badge", fontSize=7, fontName="Helvetica-Bold",
                           textColor=sig_color, alignment=TA_CENTER)
                ),
            ]]
            cv_table = Table(row, colWidths=[doc.width - 2.5*cm, 2.5*cm])
            cv_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), box_color),
                ("PADDING", (0,0), (-1,-1), 6),
                ("BOX", (0,0), (-1,-1), 0.3, sig_color),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))
            story.append(cv_table)
            story.append(Paragraph(
                f'Signification : {sig}  |  {v.get("url","")}',
                small_s
            ))
            story.append(Spacer(1, 0.2*cm))
        story.append(Spacer(1, 0.3*cm))

    # ── Articles PubMed ──────────────────────────────────────
    if articles:
        story.append(Paragraph("Articles PubMed analysés", h2_s))
        for i, art in enumerate(articles[:15], 1):
            story.append(KeepTogether([
                Paragraph(f'<b>{i}. {art.get("title","")}</b>', body_s),
                Paragraph(
                    f'{art.get("authors","")} · <i>{art.get("journal","")}</i> '
                    f'({art.get("year","")}) · PMID {art.get("pmid","")}',
                    small_s
                ),
                Spacer(1, 0.15*cm),
            ]))

    # ── Contexte populations africaines ─────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("🌍 Contexte — Populations africaines", h2_s))
    africa_text = (
        "SenGenoScope intègre les données H3Africa et gnomAD v4 pour les populations africaines "
        "afin de fournir une analyse génomique adaptée aux patients africains et sénégalais. "
        "Les fréquences alléliques africaines peuvent différer significativement des populations "
        "européennes — il est essentiel de les prendre en compte dans l'interprétation clinique "
        "des variants. Les mutations fondatrices spécifiques aux populations d'Afrique de l'Ouest "
        "(ex: BRCA1 c.5266dupC, variants HOXB13, 8q24) sont documentées dans cette plateforme."
    )
    story.append(Paragraph(africa_text, justify_s))
    story.append(Spacer(1, 0.3*cm))

    # ── Avertissement ────────────────────────────────────────
    disclaimer_table = Table(
        [[Paragraph(
            "<b>⚠️ Avertissement</b> — Ce rapport est un outil d'aide à la décision clinique. "
            "Toute conclusion diagnostique ou thérapeutique doit être validée par un médecin "
            "qualifié. Les données proviennent de PubMed, ClinVar, OMIM, gnomAD et COSMIC. "
            "Usage clinique confidentiel — Dr. Moustapha Gassama, Oncogénéticien médical.",
            _style("Disc", fontSize=8, textColor=DARK_GRAY, leading=12, alignment=TA_JUSTIFY)
        )]],
        colWidths=[doc.width]
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GRAY),
        ("PADDING", (0,0), (-1,-1), 8),
        ("BOX", (0,0), (-1,-1), 0.5, MID_GRAY),
    ]))
    story.append(disclaimer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


CLINICIAN_COLORS = {
    "oncogenetics":colors.HexColor("#0d9488"),"oncologist":colors.HexColor("#7c3aed"),
    "pathologist":colors.HexColor("#b45309"),"geneticist":colors.HexColor("#c2410c"),
    "generalist":colors.HexColor("#16a34a"),"internist":colors.HexColor("#0284c7"),
    "hematologist":colors.HexColor("#dc2626"),"radiologist":colors.HexColor("#4338ca"),
    "gynecologist":colors.HexColor("#db2777"),"pediatric_oncologist":colors.HexColor("#d97706"),
    "pain_specialist":colors.HexColor("#7c3aed"),"rcp_coordinator":colors.HexColor("#0891b2"),
}

def generate_clinician_pdf(clinician_id,clinician_name,clinician_specialty,messages,patient_context=""):
    buffer=io.BytesIO(); accent=CLINICIAN_COLORS.get(clinician_id,TEAL)
    class CDoc(BaseDocTemplate):
        def __init__(self,buf,**kw):
            BaseDocTemplate.__init__(self,buf,**kw)
            frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height-1.5*cm,id="main")
            self.addPageTemplates([PageTemplate(id="c",frames=frame,onPage=self._draw)])
        def _draw(self,c,doc):
            c.saveState(); w,h=A4
            c.setFillColor(DARK_BLUE); c.rect(0,h-1.8*cm,w,1.8*cm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",13)
            c.drawString(1.8*cm,h-1.2*cm,"SenGenoScope — Consultation Virtuelle")
            c.setFillColor(accent); c.setFont("Helvetica",8)
            c.drawString(1.8*cm,h-1.55*cm,clinician_name+" - "+clinician_specialty)
            c.setFillColor(MID_GRAY); c.setFont("Helvetica",8)
            c.drawRightString(w-1.8*cm,h-1.2*cm,datetime.now().strftime("%d/%m/%Y %H:%M"))
            c.setFont("Helvetica",7); c.drawRightString(w-1.8*cm,h-1.55*cm,f"Page {doc.page}")
            c.setStrokeColor(accent); c.setLineWidth(2); c.line(0,h-1.8*cm,w,h-1.8*cm)
            c.setStrokeColor(LIGHT_GRAY); c.setLineWidth(0.5); c.line(1.8*cm,1.5*cm,w-1.8*cm,1.5*cm)
            c.setFillColor(MID_GRAY); c.setFont("Helvetica-Oblique",6.5)
            c.drawCentredString(w/2,1.0*cm,"SenGenoScope - Dr. Moustapha Gassama - Usage clinique confidentiel")
            c.saveState(); c.setFillColor(colors.HexColor("#e2e8f0")); c.setFont("Helvetica-Bold",52)
            c.translate(w/2,h/2); c.rotate(35); c.drawCentredString(0,0,"CONFIDENTIEL"); c.restoreState()
            c.restoreState()
    doc=CDoc(buffer,pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=2.5*cm,bottomMargin=2.5*cm)
    W=A4[0]-3.6*cm; story=[]
    story.append(Paragraph("Compte-rendu de Consultation Virtuelle",_style("T",fontSize=16,fontName="Helvetica-Bold",textColor=DARK_BLUE,spaceAfter=4)))
    story.append(Spacer(1,0.3*cm))
    info=[["Clinicien",clinician_name],["Specialite",clinician_specialty],["Date",datetime.now().strftime("%d/%m/%Y")],["Plateforme","SenGenoScope"]]
    if patient_context: info.append(["Contexte",patient_context[:200]])
    t=Table([[Paragraph(f"<b>{k}</b>",_style("K",fontSize=9,textColor=DARK_GRAY)),Paragraph(v,_style("V",fontSize=9))] for k,v in info],colWidths=[3.5*cm,W-3.5*cm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),LIGHT_GRAY),("BOX",(0,0),(-1,-1),0.5,MID_GRAY),("INNERGRID",(0,0),(-1,-1),0.3,LIGHT_GRAY),("PADDING",(0,0),(-1,-1),6)]))
    story.append(t); story.append(Spacer(1,0.5*cm))
    story.append(HRFlowable(width="100%",thickness=1.5,color=accent,spaceAfter=10))
    story.append(Paragraph("Echanges de la consultation",_style("S",fontSize=12,fontName="Helvetica-Bold",textColor=DARK_BLUE,spaceAfter=8)))
    for i,msg in enumerate(messages):
        role=msg.get("role",""); content=msg.get("content","").strip()
        if not content: continue
        bg=colors.HexColor("#eff6ff") if role=="user" else colors.HexColor("#f0fdf4")
        label="Vous" if role=="user" else clinician_name
        lc=colors.HexColor("#1d4ed8") if role=="user" else accent
        disp=content if len(content)<=2000 else content[:2000]+"..."
        bd=[[Paragraph(f"<b>{label}</b>",_style(f"L{i}",fontSize=8,textColor=lc,spaceAfter=3)),""],
            [Paragraph(disp.replace("\n","<br/>"),_style(f"M{i}",fontSize=9,textColor=DARK_GRAY,leading=13)),""]]
        bt=Table(bd,colWidths=[W,0])
        bt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("BOX",(0,0),(-1,-1),0.5,MID_GRAY),("PADDING",(0,0),(-1,-1),8)]))
        story.append(KeepTogether(bt)); story.append(Spacer(1,0.25*cm))
    story.append(Spacer(1,0.5*cm))
    story.append(Paragraph("Avertissement: Resume IA, a valider par un medecin qualifie.",_style("D",fontSize=8,textColor=DARK_GRAY,leading=12,alignment=TA_JUSTIFY)))
    doc.build(story); buffer.seek(0); return buffer.read()
