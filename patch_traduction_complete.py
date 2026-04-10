#!/usr/bin/env python3
"""
patch_traduction_complete.py
Traduction complète FR/EN de toutes les sections de SenGenoScope.
Exécuter depuis SenGenoScope/ :
  python3 patch_traduction_complete.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

fixes = 0

def tr(old, fr_txt, en_txt, tag='span'):
    """Remplace old par <tag data-fr="..." data-en="...">old</tag>"""
    global html, fixes
    new = f'<{tag} data-fr="{fr_txt}" data-en="{en_txt}">{old}</{tag}>'
    if old in html:
        html = html.replace(old, new)
        fixes += 1
        return True
    return False

def rep(old, new):
    """Remplacement direct."""
    global html, fixes
    if old in html:
        html = html.replace(old, new)
        fixes += 1
        return True
    return False

# ══ META TITLE ══════════════════════════════════════════════════════════════
rep(
    "<title>SenGenoScope — Plateforme d'Oncogénomique et Oncopharmacogénomique Clinique</title>",
    "<title id='page-title'>SenGenoScope — Plateforme d'Oncogénomique et Oncopharmacogénomique Clinique</title>"
)

# ══ SIDEBAR — Sous-titre logo ════════════════════════════════════════════════
# Déjà fait via data-fr/data-en dans .ls

# ══ SECTION PRS ══════════════════════════════════════════════════════════════
rep(
    '<span class="ct2">📊 Calculateur de Score Polygénique (PRS) — Risque de cancer basé sur les SNPs GWAS</span>',
    '<span class="ct2" data-fr="📊 Calculateur de Score Polygénique (PRS) — Risque de cancer basé sur les SNPs GWAS" data-en="📊 Polygenic Risk Score (PRS) Calculator — Cancer risk based on GWAS SNPs">📊 Calculateur de Score Polygénique (PRS) — Risque de cancer basé sur les SNPs GWAS</span>'
)

# ══ SECTION VEP ══════════════════════════════════════════════════════════════
rep(
    '<span class="ct2">🎯 Prédiction d\'impact — Ensembl VEP · PolyPhen-2 · SIFT · CADD</span>',
    '<span class="ct2" data-fr="🎯 Prédiction d\'impact — Ensembl VEP · PolyPhen-2 · SIFT · CADD" data-en="🎯 Impact prediction — Ensembl VEP · PolyPhen-2 · SIFT · CADD">🎯 Prédiction d\'impact — Ensembl VEP · PolyPhen-2 · SIFT · CADD</span>'
)
rep(
    '<div style="font-size:12px;font-weight:700;color:var(--pr);margin-bottom:7px">🔗 Pré-remplir depuis une base de données en ligne</div>',
    '<div style="font-size:12px;font-weight:700;color:var(--pr);margin-bottom:7px" data-fr="🔗 Pré-remplir depuis une base de données en ligne" data-en="🔗 Pre-fill from an online database">🔗 Pré-remplir depuis une base de données en ligne</div>'
)

# ══ SECTION NGS ══════════════════════════════════════════════════════════════
rep(
    '<div style="font-size:12px;font-weight:700;color:#16a34a;margin-bottom:6px">🔍 Auto-remplir depuis ClinVar / littérature</div>',
    '<div style="font-size:12px;font-weight:700;color:#16a34a;margin-bottom:6px" data-fr="🔍 Auto-remplir depuis ClinVar / littérature" data-en="🔍 Auto-fill from ClinVar / literature">🔍 Auto-remplir depuis ClinVar / littérature</div>'
)

# ══ SECTION PENETRANCE — select ═══════════════════════════════════════════════
rep(
    '<option value="">— Sélectionner un gène —</option>',
    '<option value="" data-fr="— Sélectionner un gène —" data-en="— Select a gene —">— Sélectionner un gène —</option>'
)
rep(
    '<option value="">— Sélectionner un syndrome —</option>',
    '<option value="" data-fr="— Sélectionner un syndrome —" data-en="— Select a syndrome —">— Sélectionner un syndrome —</option>'
)

# ══ SECTION RISK ══════════════════════════════════════════════════════════════
rep(
    '>Vérification…<',
    ' data-fr="Vérification…" data-en="Checking…">Vérification…<'
)
rep(
    '>Données en temps réel<',
    ' data-fr="Données en temps réel" data-en="Real-time data">Données en temps réel<'
)

# ══ SECTION AI CHAT ══════════════════════════════════════════════════════════
rep(
    '>Exemples : interprétation ACMG, variant BRCA1, thérapie ciblée EGFR…<',
    ' data-fr="Exemples : interprétation ACMG, variant BRCA1, thérapie ciblée EGFR…" data-en="Examples: ACMG interpretation, BRCA1 variant, EGFR targeted therapy…">Exemples : interprétation ACMG, variant BRCA1, thérapie ciblée EGFR…<'
)

# ══ SECTION AI PHARMA ════════════════════════════════════════════════════════
rep(
    '>🤖 Analyser avec Claude AI<',
    ' data-fr="🤖 Analyser avec Claude AI" data-en="🤖 Analyze with Claude AI">🤖 Analyser avec Claude AI<'
)
rep(
    '>Accès rapide :<',
    ' data-fr="Accès rapide :" data-en="Quick access:">Accès rapide :<'
)
rep(
    '>💊 Analyser avec Claude AI<',
    ' data-fr="💊 Analyser avec Claude AI" data-en="💊 Analyze with Claude AI">💊 Analyser avec Claude AI<'
)

# ══ SECTION CLINICIENS ═══════════════════════════════════════════════════════
rep(
    '>🩺 Cliniciens Virtuels en Oncologie — Basés sur les bases de données internationales<',
    ' data-fr="🩺 Cliniciens Virtuels en Oncologie — Basés sur les bases de données internationales" data-en="🩺 Virtual Clinicians in Oncology — Based on international databases">🩺 Cliniciens Virtuels en Oncologie — Basés sur les bases de données internationales<'
)
rep(
    '>avant de répondre.<',
    ' data-fr="avant de répondre." data-en="before responding.">avant de répondre.<'
)
rep(
    '>BRCA1 pathogène<',
    ' data-fr="BRCA1 pathogène" data-en="BRCA1 pathogenic">BRCA1 pathogène<'
)
rep(
    '>EGFR muté CBNPC<',
    ' data-fr="EGFR muté CBNPC" data-en="EGFR mutated NSCLC">EGFR muté CBNPC<'
)
rep(
    '>📚 Sources consultées pour cette réponse :<',
    ' data-fr="📚 Sources consultées pour cette réponse :" data-en="📚 Sources consulted for this response:">📚 Sources consultées pour cette réponse :<'
)

# ══ SECTION ABOUT ════════════════════════════════════════════════════════════
rep(
    '>Dr. Moustapha Gassama — Oncogénéticien médical · Public Health Data Scientist<',
    ' data-fr="Dr. Moustapha Gassama — Oncogénéticien médical · Public Health Data Scientist" data-en="Dr. Moustapha Gassama — Medical Oncogeneticist · Public Health Data Scientist">Dr. Moustapha Gassama — Oncogénéticien médical · Public Health Data Scientist<'
)

# Cartes version/phase
rep(
    '>✅ Score polygénique PRS (5 cancers)<',
    ' data-fr="✅ Score polygénique PRS (5 cancers)" data-en="✅ Polygenic Risk Score PRS (5 cancers)">✅ Score polygénique PRS (5 cancers)<'
)
rep(
    '>✅ Pénétrance par âge (BRCA/Lynch/TP53)<',
    ' data-fr="✅ Pénétrance par âge (BRCA/Lynch/TP53)" data-en="✅ Penetrance by age (BRCA/Lynch/TP53)">✅ Pénétrance par âge (BRCA/Lynch/TP53)<'
)
rep(
    '>✅ Interpréteur NGS en langage clinique<',
    ' data-fr="✅ Interpréteur NGS en langage clinique" data-en="✅ NGS Interpreter in clinical language">✅ Interpréteur NGS en langage clinique<'
)
rep(
    '>Claude AI intégré<',
    ' data-fr="Claude AI intégré" data-en="Integrated Claude AI">Claude AI intégré<'
)
rep(
    '>✅ Chat IA oncogénomique spécialisé<',
    ' data-fr="✅ Chat IA oncogénomique spécialisé" data-en="✅ Specialized oncogenomics AI chat">✅ Chat IA oncogénomique spécialisé<'
)
rep(
    '>✅ Pharmacogénomique IA (CPIC/DPWG/FDA)<',
    ' data-fr="✅ Pharmacogénomique IA (CPIC/DPWG/FDA)" data-en="✅ AI Pharmacogenomics (CPIC/DPWG/FDA)">✅ Pharmacogénomique IA (CPIC/DPWG/FDA)<'
)
rep(
    '>✅ Rapport ACMG structuré par IA<',
    ' data-fr="✅ Rapport ACMG structuré par IA" data-en="✅ AI-structured ACMG report">✅ Rapport ACMG structuré par IA<'
)
rep(
    '>✅ Synthèse PubMed intelligente<',
    ' data-fr="✅ Synthèse PubMed intelligente" data-en="✅ Intelligent PubMed synthesis">✅ Synthèse PubMed intelligente<'
)
rep(
    '>✅ Thérapies ciblées par gène/variant<',
    ' data-fr="✅ Thérapies ciblées par gène/variant" data-en="✅ Targeted therapies by gene/variant">✅ Thérapies ciblées par gène/variant<'
)
rep(
    '>🔜 Dossiers patients sécurisés<',
    ' data-fr="🔜 Dossiers patients sécurisés" data-en="🔜 Secure patient records">🔜 Dossiers patients sécurisés<'
)
rep(
    '>IA & Interopérabilité<',
    ' data-fr="IA & Interopérabilité" data-en="AI & Interoperability">IA & Interopérabilité<'
)
rep(
    '>🚀 Prédiction VUS → Pathogène (ML)<',
    ' data-fr="🚀 Prédiction VUS → Pathogène (ML)" data-en="🚀 VUS → Pathogenic prediction (ML)">🚀 Prédiction VUS → Pathogène (ML)<'
)
rep(
    '>🚀 Analyses de cohortes africaines<',
    ' data-fr="🚀 Analyses de cohortes africaines" data-en="🚀 African cohort analyses">🚀 Analyses de cohortes africaines<'
)
rep(
    '>🚀 API FHIR pour DMP/EHR<',
    ' data-fr="🚀 API FHIR pour DMP/EHR" data-en="🚀 FHIR API for EHR/DMP">🚀 API FHIR pour DMP/EHR<'
)
rep(
    '>🚀 GWAS Catalog PRS temps réel<',
    ' data-fr="🚀 GWAS Catalog PRS temps réel" data-en="🚀 Real-time GWAS Catalog PRS">🚀 GWAS Catalog PRS temps réel<'
)

# ══ FOOTER MORPHO ════════════════════════════════════════════════════════════
rep(
    'Usage clinique confidentiel · SenGenoScope',
    '<span data-fr="Usage clinique confidentiel · SenGenoScope" data-en="Confidential clinical use · SenGenoScope">Usage clinique confidentiel · SenGenoScope</span>'
)

# ══ TOPBAR — synchroniser lang au chargement ════════════════════════════════
# Mettre à jour les boutons topbar selon la langue sauvegardée
old_setlang_init = 'setLang(lang);'
new_setlang_init = '''setLang(lang);
// Init boutons topbar selon langue sauvegardée
(function(){
  const l = localStorage.getItem('sgs_lang') || 'fr';
  const tbFr = document.getElementById('topbar-btn-fr');
  const tbEn = document.getElementById('topbar-btn-en');
  if(tbFr){ tbFr.style.background = l==='fr' ? 'var(--pr)' : 'var(--s2)'; tbFr.style.color = l==='fr' ? '#fff' : 'var(--mu)'; }
  if(tbEn){ tbEn.style.background = l==='en' ? 'var(--pr)' : 'var(--s2)'; tbEn.style.color = l==='en' ? '#fff' : 'var(--mu)'; }
})();'''

rep(old_setlang_init, new_setlang_init)

with open('templates/index.html', 'w') as f:
    f.write(html)

print(f"✅ {fixes} remplacements effectués")
print("✅ templates/index.html patché avec succès")
print()
print("="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: traduction complète FR/EN toutes sections"')
print("  git push origin main")
