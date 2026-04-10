#!/usr/bin/env python3
"""
patch_tumeurs_rares.py
Module tumeurs rares : sarcomes, tumeurs neuroendocrines, GIST,
tumeurs desmoïdes, rhabdomyosarcomes — avec mutations, guidelines et
spécificités populations africaines.

Exécuter depuis SenGenoScope/ :
  python3 patch_tumeurs_rares.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Bouton sidebar (après Morpho-Génétique IA)
# ─────────────────────────────────────────────────────────────
OLD_BTN = '''    <button class="ni" onclick="showSec('morpho',this)"><span class="ni-i">🔬</span><span data-fr="Morpho-Génétique IA" data-en="Morpho-Genetic AI">Morpho-Génétique IA</span></button>'''

NEW_BTN = OLD_BTN + '''
    <button class="ni" onclick="showSec('rare',this)"><span class="ni-i">🧩</span><span data-fr="Tumeurs rares" data-en="Rare Tumors">Tumeurs rares</span></button>'''

if OLD_BTN in html:
    html = html.replace(OLD_BTN, NEW_BTN)
    print("✅ Bouton sidebar ajouté")
else:
    print("❌ Bouton sidebar non trouvé")

# ─────────────────────────────────────────────────────────────
# 2. Ajouter 'rare' dans showSec
# ─────────────────────────────────────────────────────────────
old_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','compvar','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"
new_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','compvar','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho','rare']"

if old_list in html:
    html = html.replace(old_list, new_list)
    print("✅ 'rare' ajouté dans showSec")
else:
    print("❌ Liste showSec non trouvée")

# ─────────────────────────────────────────────────────────────
# 3. Section HTML
# ─────────────────────────────────────────────────────────────
RARE_SECTION = '''
  <!-- ══ TUMEURS RARES ════════════════════════════════════════════════════ -->
  <div id="sec-rare" style="display:none">
    <div style="padding:14px 16px;border-bottom:1px solid var(--bd)">
      <div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px"
           data-fr="🧩 Tumeurs rares — Sarcomes, TNE &amp; Tumeurs spéciales"
           data-en="🧩 Rare Tumors — Sarcomas, NETs &amp; Special Tumors">
        🧩 Tumeurs rares — Sarcomes, TNE &amp; Tumeurs spéciales
      </div>
      <div style="font-size:12px;color:var(--mu)"
           data-fr="Référentiel génomique des tumeurs rares avec mutations drivers, guidelines ESMO/NCCN et pertinence pour les populations africaines."
           data-en="Genomic reference for rare tumors with driver mutations, ESMO/NCCN guidelines and relevance for African populations.">
        Référentiel génomique des tumeurs rares avec mutations drivers, guidelines ESMO/NCCN et pertinence pour les populations africaines.
      </div>
    </div>

    <div style="padding:14px">
      <!-- Filtres par catégorie -->
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px" id="rareCatBtns">
        <button class="btn bp3" onclick="filterRare('all',this)" data-fr="Toutes" data-en="All">Toutes</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" onclick="filterRare('sarcome',this)" data-fr="🦴 Sarcomes" data-en="🦴 Sarcomas">🦴 Sarcomes</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" onclick="filterRare('tne',this)" data-fr="🔵 TNE" data-en="🔵 NETs">🔵 TNE</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" onclick="filterRare('gist',this)" data-fr="⚡ GIST" data-en="⚡ GIST">⚡ GIST</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" onclick="filterRare('pediatrique',this)" data-fr="🟡 Pédiatrique" data-en="🟡 Pediatric">🟡 Pédiatrique</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" onclick="filterRare('afrique',this)" data-fr="🌍 Spécifique Afrique" data-en="🌍 Africa-specific">🌍 Spécifique Afrique</button>
      </div>

      <!-- Barre de recherche -->
      <div style="margin-bottom:14px;position:relative">
        <input type="text" id="rareSearch" placeholder="Rechercher une tumeur, gène ou mutation..."
               oninput="searchRare(this.value)"
               style="width:100%;padding:9px 12px 9px 36px;border-radius:7px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:13px">
        <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--mu);font-size:14px">🔍</span>
      </div>

      <!-- Grille des tumeurs -->
      <div id="rareTumorGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px"></div>
    </div>
  </div>

'''

OLD_ABOUT = '  <div id="sec-about" style="display:none">'
if OLD_ABOUT in html:
    html = html.replace(OLD_ABOUT, RARE_SECTION + OLD_ABOUT)
    print("✅ Section tumeurs rares insérée")
else:
    print("❌ Ancre sec-about non trouvée")

# ─────────────────────────────────────────────────────────────
# 4. JavaScript
# ─────────────────────────────────────────────────────────────
RARE_JS = r'''
// ══ TUMEURS RARES ════════════════════════════════════════════════════════════
const RARE_DB = [
  // ── SARCOMES ──────────────────────────────────────────────
  {
    id:'ewing', cat:'sarcome',
    name:'Sarcome d\'Ewing', emoji:'🦴',
    gene:'EWSR1-FLI1', fusion:'t(11;22)(q24;q12)',
    mutations:['EWSR1-FLI1 (85%)','EWSR1-ERG (10%)','CDKN2A del'],
    incidence:'3/million/an', age:'Adolescents, jeunes adultes',
    guidelines:'ESMO 2023 · COG AEWS1031',
    treatment:'VDC/IE alternés · Radiothérapie · Chirurgie',
    african:'Rare mais sous-diagnostiqué en Afrique subsaharienne. Diagnostic histologique + FISH EWSR1 indispensable. Accès limité à la chimiothérapie intensive.',
    color:'#0891b2', links:[
      {name:'ESMO Ewing', url:'https://www.esmo.org/guidelines/bone-sarcomas'},
      {name:'ClinVar EWSR1', url:'https://www.ncbi.nlm.nih.gov/clinvar/?term=EWSR1'},
    ]
  },
  {
    id:'gist_main', cat:'gist',
    name:'GIST (Tumeur stromale gastro-intestinale)', emoji:'⚡',
    gene:'KIT / PDGFRA',
    mutations:['KIT exon 11 (70%)','KIT exon 9 (10%)','PDGFRA D842V (8%)','NF1/SDH-déficient (5%)'],
    incidence:'10-15/million/an', age:'Adultes > 50 ans',
    guidelines:'ESMO GIST 2023 · NCCN Soft Tissue Sarcoma v2024',
    treatment:'Imatinib (1ère ligne) · Sunitinib (2ème) · Ripretinib (4ème)',
    african:'KIT exon 11 mutations similaires aux populations occidentales. PDGFRA D842V résistant à l\'imatinib — avapritinib recommandé. Accès imatinib générique possible en Afrique.',
    color:'#7c3aed', links:[
      {name:'ESMO GIST', url:'https://www.esmo.org/guidelines/gastrointestinal-cancers/gastrointestinal-stromal-tumours-gist'},
    ]
  },
  {
    id:'osteo', cat:'sarcome',
    name:'Ostéosarcome', emoji:'🦴',
    gene:'TP53 / RB1',
    mutations:['TP53 (50%)','RB1 (40%)','DLG2 (17%)','ATRX (15%)','CDKN2A del'],
    incidence:'3-5/million/an', age:'Adolescents (pic 10-20 ans)',
    guidelines:'ESMO Bone Sarcomas 2023 · NCCN Bone Cancer v2024',
    treatment:'MAP (MTX+ADR+DDP) · Chirurgie conservatrice · IFO',
    african:'2ème cancer osseux le plus fréquent en Afrique subsaharienne. Présentation souvent tardive (stade métastatique). Mutations TP53 germinales → syndrome Li-Fraumeni à rechercher.',
    color:'#c2410c', links:[
      {name:'ESMO Bone', url:'https://www.esmo.org/guidelines/bone-sarcomas'},
    ]
  },
  {
    id:'lms', cat:'sarcome',
    name:'Léiomyosarcome', emoji:'💪',
    gene:'TP53 / RB1 / PTEN',
    mutations:['TP53 (30-40%)','RB1 (40%)','PTEN (20%)','ATRX (20%)'],
    incidence:'2-3/million/an', age:'Adultes 50-70 ans',
    guidelines:'ESMO Soft Tissue Sarcoma 2023',
    treatment:'Doxorubicine ± ifosfamide · Gemcitabine-docétaxel · Trabectédine',
    african:'Localisation utérine fréquente chez la femme africaine. Association possible avec EBV dans formes immunodéprimées (VIH+). Diagnostic différentiel avec fibrome utérin crucial.',
    color:'#dc2626', links:[]
  },
  {
    id:'rms', cat:'pediatrique',
    name:'Rhabdomyosarcome', emoji:'🟡',
    gene:'PAX3-FOXO1 / PAX7-FOXO1',
    mutations:['PAX3-FOXO1 t(2;13) alvéolaire','PAX7-FOXO1 t(1;13)','RAS (embryonnaire)','MYOD1 (spindle cell)'],
    incidence:'4-7/million < 20 ans', age:'Enfants < 10 ans (pic)',
    guidelines:'COG ARST Protocols · ESMO Pediatric 2023 · SIOPE',
    treatment:'VAC (VCR+ActD+CPM) · Radiothérapie · Chirurgie',
    african:'Sous-diagnostic fréquent. Forme alvéolaire (PAX-FOXO1) de mauvais pronostic. Accès aux protocoles COG limité — SIOPE recommandé pour LMIC.',
    color:'#d97706', links:[
      {name:'SIOPE RMS', url:'https://www.siope.eu/'},
    ]
  },
  // ── TNE ───────────────────────────────────────────────────
  {
    id:'tne_pancreas', cat:'tne',
    name:'TNE Pancréatique (pNET)', emoji:'🔵',
    gene:'MEN1 / DAXX / ATRX',
    mutations:['MEN1 (44%)','DAXX (25%)','ATRX (18%)','mTOR pathway (15%)'],
    incidence:'1-2/million/an', age:'Adultes 40-60 ans',
    guidelines:'ENETS 2023 · ESMO pNET 2023 · NCCN NET v2024',
    treatment:'Somatostatine analogues · Everolimus · Sunitinib · PRRT (Lu-177)',
    african:'MEN1 germinal à rechercher (NEM1). Ki-67 indispensable pour grading OMS 2022. Accès aux analogues somatostatine limité en Afrique.',
    color:'#0d9488', links:[
      {name:'ENETS Guidelines', url:'https://www.enets.org/guidelines.html'},
    ]
  },
  {
    id:'tne_pulmonaire', cat:'tne',
    name:'TNE Pulmonaire (Carcinoïde)', emoji:'🫁',
    gene:'MEN1 / CDKN1B',
    mutations:['MEN1 (35%)','CDKN1B (8%)','EIF1AX','TP53 (LCNEC)'],
    incidence:'2/million/an', age:'Adultes 45-55 ans',
    guidelines:'ENETS 2023 · ESMO Lung NET 2022',
    treatment:'Chirurgie (typique/atypique) · SSA · Chimiothérapie (LCNEC)',
    african:'Carcinoïde typique de bon pronostic. LCNEC de mauvais pronostic similaire au CPPC. Tabagisme moins corrélé qu\'en Occident.',
    color:'#0891b2', links:[]
  },
  // ── GIST variantes ────────────────────────────────────────
  {
    id:'gist_sdh', cat:'gist',
    name:'GIST SDH-déficient', emoji:'⚡',
    gene:'SDHA/B/C/D',
    mutations:['SDHA (65%)','SDHB (30%)','SDHC/D (5%)'],
    incidence:'Rare (< 5% des GIST)', age:'Jeunes adultes, enfants',
    guidelines:'ESMO GIST 2023 — traitement spécifique',
    treatment:'Sunitinib · Regorafenib (résistance imatinib)',
    african:'Syndrome de Carney-Stratakis (GIST + paragangliome + SDHA germinal). Testing germinal SDH recommandé. Triade de Carney (GIST + chondrome + paragangliome).',
    color:'#7c3aed', links:[]
  },
  // ── SPÉCIFIQUES AFRIQUE ───────────────────────────────────
  {
    id:'burkitt', cat:'afrique',
    name:'Lymphome de Burkitt (Endémique)', emoji:'🌍',
    gene:'MYC',
    mutations:['t(8;14)(q24;q32) MYC-IGH (80%)','t(2;8) MYC-IGK (15%)','TP53 (30%)','EBV+ (100% forme endémique)'],
    incidence:'Endémique Afrique équatoriale', age:'Enfants 4-7 ans (pic)',
    guidelines:'ESMO DLBCL 2023 · Protocoles LMB/CODOX-M · SIOPE',
    treatment:'CODOX-M/IVAC · CHOP-R si ressources limitées · Rituximab',
    african:'Cancer pédiatrique le plus fréquent en Afrique équatoriale (belt). EBV + malaria = cofacteurs. Mâchoire et abdomen = sites prédominants. Survie 90% si traitement précoce.',
    color:'#16a34a', links:[
      {name:'SIOPE Burkitt', url:'https://www.siope.eu/'},
      {name:'PubMed Burkitt Africa', url:'https://pubmed.ncbi.nlm.nih.gov/?term=burkitt+lymphoma+africa'},
    ]
  },
  {
    id:'kaposi', cat:'afrique',
    name:'Sarcome de Kaposi (Africain/VIH)', emoji:'🌍',
    gene:'HHV-8 / TP53',
    mutations:['HHV-8 (100%)','VIH-associé dominant','Forme endémique (sans VIH)'],
    incidence:'Endémique Afrique subsaharienne', age:'Tout âge (VIH+), adultes jeunes',
    guidelines:'ESMO Kaposi 2023 · PEPFAR Guidelines',
    treatment:'ARV (HAART) · Liposomal doxorubicine · Paclitaxel · Vincristine',
    african:'1er cancer associé au VIH en Afrique subsaharienne. Forme cutanée + muqueuse + viscérale. Traitement ARV seul peut induire rémission stade I-II. Accès HAART crucial.',
    color:'#dc2626', links:[
      {name:'PubMed Kaposi Africa', url:'https://pubmed.ncbi.nlm.nih.gov/?term=kaposi+sarcoma+africa+HIV'},
    ]
  },
  {
    id:'wilms', cat:'pediatrique',
    name:'Tumeur de Wilms (Néphroblastome)', emoji:'🟡',
    gene:'WT1 / CTNNB1 / WTX',
    mutations:['WT1 (10-15%)','CTNNB1 (15%)','WTX (15-20%)','SIX1/2 (18%)','DROSHA/DGCR8 (15%)'],
    incidence:'7-10/million < 15 ans', age:'Enfants 3-4 ans (pic)',
    guidelines:'SIOP WT 2016 · COG · ESMO Pediatric',
    treatment:'Chimiothérapie préopératoire (SIOP) · Néphrectomie · AV ± doxorubicine',
    african:'2ème cancer pédiatrique le plus fréquent en Afrique subsaharienne. Présentation tardive (abdomen volumineux, HTA). Survie 90% (pays HIC) vs 60% (Afrique) → diagnostic précoce crucial.',
    color:'#d97706', links:[
      {name:'SIOP Wilms', url:'https://www.siope.eu/siop-europe-working-groups/renal-tumours/'},
    ]
  },
];

let rareCurrentCat = 'all';

function initRareTumors() {
  renderRareTumors(RARE_DB);
}

function filterRare(cat, btn) {
  rareCurrentCat = cat;
  document.querySelectorAll('#rareCatBtns .btn').forEach(b => {
    b.classList.remove('bp3');
    b.style.background = 'var(--s2)';
    b.style.color = 'var(--mu)';
  });
  btn.classList.add('bp3');
  btn.style.background = '';
  btn.style.color = '';
  const filtered = cat === 'all' ? RARE_DB : RARE_DB.filter(t => t.cat === cat);
  renderRareTumors(filtered);
}

function searchRare(q) {
  const lq = q.toLowerCase();
  const filtered = RARE_DB.filter(t =>
    (rareCurrentCat === 'all' || t.cat === rareCurrentCat) &&
    (t.name.toLowerCase().includes(lq) || t.gene.toLowerCase().includes(lq) ||
     t.mutations.some(m => m.toLowerCase().includes(lq)))
  );
  renderRareTumors(filtered);
}

function renderRareTumors(list) {
  const grid = document.getElementById('rareTumorGrid');
  if (!grid) return;

  if (list.length === 0) {
    grid.innerHTML = '<div style="color:var(--mu);font-size:13px;padding:20px;grid-column:1/-1">Aucune tumeur trouvée.</div>';
    return;
  }

  grid.innerHTML = list.map(t => `
    <div style="background:var(--sf);border:1px solid var(--bd);border-radius:10px;overflow:hidden;border-top:3px solid ${t.color}">
      <div style="padding:12px 14px;border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:10px">
        <span style="font-size:20px">${t.emoji}</span>
        <div style="flex:1">
          <div style="font-size:13px;font-weight:700;color:var(--tx)">${t.name}</div>
          <div style="font-size:11px;color:${t.color};font-weight:600;margin-top:1px">${t.gene}</div>
        </div>
        <span style="font-size:10px;background:var(--s2);color:var(--mu);padding:2px 7px;border-radius:5px;font-weight:600">
          ${t.cat === 'sarcome' ? 'SARCOME' : t.cat === 'tne' ? 'TNE' : t.cat === 'gist' ? 'GIST' : t.cat === 'pediatrique' ? 'PÉDIATRIQUE' : t.cat === 'afrique' ? 'AFRIQUE' : t.cat.toUpperCase()}
        </span>
      </div>

      <div style="padding:10px 14px">
        <!-- Mutations -->
        <div style="font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px">Mutations principales</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px">
          ${t.mutations.map(m => `<span style="font-size:10px;padding:2px 7px;border-radius:4px;background:${t.color}18;color:${t.color};font-weight:600;font-family:var(--mono)">${m}</span>`).join('')}
        </div>

        <!-- Infos -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;font-size:11px">
          <div style="color:var(--mu)">📊 Incidence</div><div style="color:var(--tx)">${t.incidence}</div>
          <div style="color:var(--mu)">👤 Âge</div><div style="color:var(--tx)">${t.age}</div>
          <div style="color:var(--mu)">💊 Traitement</div><div style="color:var(--tx)">${t.treatment}</div>
        </div>

        <!-- Guidelines -->
        <div style="font-size:10px;color:var(--mu);background:var(--s2);padding:5px 8px;border-radius:5px;margin-bottom:8px">
          📋 ${t.guidelines}
        </div>

        <!-- Contexte africain -->
        <div style="font-size:11px;color:var(--tx);background:var(--s2);padding:7px 9px;border-radius:6px;border-left:3px solid #16a34a;line-height:1.5;margin-bottom:8px">
          🌍 ${t.african}
        </div>

        <!-- Liens -->
        ${t.links && t.links.length ? `
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${t.links.map(l => `<a href="${l.url}" target="_blank" style="font-size:11px;color:${t.color};text-decoration:none;padding:3px 8px;border:1px solid ${t.color}40;border-radius:5px">↗ ${l.name}</a>`).join('')}
          <a href="https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(t.name)}" target="_blank"
             style="font-size:11px;color:var(--mu);text-decoration:none;padding:3px 8px;border:1px solid var(--bd);border-radius:5px">
            📚 PubMed
          </a>
        </div>` : `
        <a href="https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(t.name)}" target="_blank"
           style="font-size:11px;color:var(--mu);text-decoration:none;padding:3px 8px;border:1px solid var(--bd);border-radius:5px">
          📚 PubMed
        </a>`}
      </div>
    </div>
  `).join('');
}
// ══ FIN TUMEURS RARES ════════════════════════════════════════════════════════
'''

# Insérer le JS avant </script>
last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + RARE_JS + html[last_script:]
    print("✅ JavaScript tumeurs rares inséré")

# Appeler initRareTumors dans showSec
old_showsec_init = "  if(name==='clinicians')initClinicians();"
new_showsec_init = "  if(name==='clinicians')initClinicians();\n  if(name==='rare')initRareTumors();"
if old_showsec_init in html:
    html = html.replace(old_showsec_init, new_showsec_init)
    print("✅ initRareTumors() appelé dans showSec")

# Compteur 18 → 19
html = html.replace(
    'data-fr="🧪 18 modules" data-en="🧪 18 modules">🧪 18 modules',
    'data-fr="🧪 19 modules" data-en="🧪 19 modules">🧪 19 modules'
)
print("✅ Compteur modules : 18 → 19")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: module tumeurs rares (sarcomes, TNE, GIST, pédiatrique, Afrique)"')
print("  git push origin main")
