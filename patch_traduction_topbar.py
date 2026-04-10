#!/usr/bin/env python3
"""
patch_traduction_topbar.py
- Ajoute switcher FR/EN dans la topbar (barre du haut)
- Ajoute data-fr/data-en au module Morpho-Génétique
- Met à jour le compteur de modules (15 → 16)

Exécuter depuis SenGenoScope/ :
  python3 patch_traduction_topbar.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Ajouter switcher FR/EN dans la topbar (à droite)
# ─────────────────────────────────────────────────────────────
OLD_TOPBAR_END = '''      <button class="btn bsm" id="apiKeyBtn" onclick="openApiSettings()" style="background:rgba(124,58,237,.15);color:#a78bfa;border:1px solid rgba(124,58,237,.3);font-size:11px" title="Configurer votre clé API Claude">⚙️ <span data-fr="Clé API" data-en="API Key">Clé API</span></button>
    </div>
  </div>'''

NEW_TOPBAR_END = '''      <button class="btn bsm" id="apiKeyBtn" onclick="openApiSettings()" style="background:rgba(124,58,237,.15);color:#a78bfa;border:1px solid rgba(124,58,237,.3);font-size:11px" title="Configurer votre clé API Claude">⚙️ <span data-fr="Clé API" data-en="API Key">Clé API</span></button>
      <div style="display:flex;gap:4px;margin-left:6px;border-left:1px solid var(--bd);padding-left:8px">
        <button id="topbar-btn-fr" onclick="setLang('fr')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--pr);color:#fff;font-size:11px;font-weight:700;cursor:pointer">🇫🇷 FR</button>
        <button id="topbar-btn-en" onclick="setLang('en')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--mu);font-size:11px;font-weight:700;cursor:pointer">🇬🇧 EN</button>
      </div>
    </div>
  </div>'''

if OLD_TOPBAR_END in html:
    html = html.replace(OLD_TOPBAR_END, NEW_TOPBAR_END)
    print("✅ Switcher FR/EN ajouté dans la topbar")
else:
    print("❌ Topbar non trouvée — vérifier manuellement")

# ─────────────────────────────────────────────────────────────
# 2. Mettre à jour setLang() pour synchroniser les deux switchers
# ─────────────────────────────────────────────────────────────
OLD_SETLANG = '''  document.getElementById('btn-fr').classList.toggle('active',l==='fr');
  document.getElementById('btn-en').classList.toggle('active',l==='en');'''

NEW_SETLANG = '''  document.getElementById('btn-fr').classList.toggle('active',l==='fr');
  document.getElementById('btn-en').classList.toggle('active',l==='en');
  // Synchroniser les boutons de la topbar
  const tbFr = document.getElementById('topbar-btn-fr');
  const tbEn = document.getElementById('topbar-btn-en');
  if(tbFr){ tbFr.style.background = l==='fr' ? 'var(--pr)' : 'var(--s2)'; tbFr.style.color = l==='fr' ? '#fff' : 'var(--mu)'; }
  if(tbEn){ tbEn.style.background = l==='en' ? 'var(--pr)' : 'var(--s2)'; tbEn.style.color = l==='en' ? '#fff' : 'var(--mu)'; }'''

if OLD_SETLANG in html:
    html = html.replace(OLD_SETLANG, NEW_SETLANG)
    print("✅ setLang() mis à jour pour synchroniser topbar + sidebar")
else:
    print("❌ setLang() non trouvé")

# ─────────────────────────────────────────────────────────────
# 3. Ajouter data-fr/data-en au module Morpho-Génétique
# ─────────────────────────────────────────────────────────────

# Titre section
html = html.replace(
    '<div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px">🔬 Corrélation Morphologie–Génétique</div>',
    '<div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px" data-fr="🔬 Corrélation Morphologie–Génétique" data-en="🔬 Morphology–Genetics Correlation">🔬 Corrélation Morphologie–Génétique</div>'
)

# Sous-titre
html = html.replace(
    "Upload d'image histologique (HE, IHC, FISH) → Analyse IA : description morphologique, mutations probables, guidelines, contexte populations africaines.",
    '<span data-fr="Upload d\'image histologique (HE, IHC, FISH) → Analyse IA : description morphologique, mutations probables, guidelines, contexte populations africaines." data-en="Upload histological image (HE, IHC, FISH) → AI analysis: morphological description, probable mutations, guidelines, African population context.">Upload d\'image histologique (HE, IHC, FISH) → Analyse IA : description morphologique, mutations probables, guidelines, contexte populations africaines.</span>'
)

# Avertissement sécurité
html = html.replace(
    '🔒 Usage clinique confidentiel — validation anatomopathologiste requise.',
    '<span data-fr="🔒 Usage clinique confidentiel — validation anatomopathologiste requise." data-en="🔒 Confidential clinical use — pathologist validation required.">🔒 Usage clinique confidentiel — validation anatomopathologiste requise.</span>'
)

# Onglets cancers
html = html.replace(
    '<button class="btn bp3" style="font-size:12px" onclick="setMorphoTab(\'sein\',this)">🎀 Cancer du sein</button>',
    '<button class="btn bp3" style="font-size:12px" onclick="setMorphoTab(\'sein\',this)" data-fr="🎀 Cancer du sein" data-en="🎀 Breast Cancer">🎀 Cancer du sein</button>'
)
html = html.replace(
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab(\'prostate\',this)">🔵 Cancer de la prostate</button>',
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab(\'prostate\',this)" data-fr="🔵 Cancer de la prostate" data-en="🔵 Prostate Cancer">🔵 Cancer de la prostate</button>'
)
html = html.replace(
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab(\'pediatrique\',this)">🟡 Cancers pédiatriques</button>',
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab(\'pediatrique\',this)" data-fr="🟡 Cancers pédiatriques" data-en="🟡 Pediatric Cancers">🟡 Cancers pédiatriques</button>'
)

# Zone upload
html = html.replace(
    '<div style="font-size:14px;font-weight:700;color:var(--tx)">Déposer une image histologique</div>',
    '<div style="font-size:14px;font-weight:700;color:var(--tx)" data-fr="Déposer une image histologique" data-en="Drop a histological image">Déposer une image histologique</div>'
)
html = html.replace(
    '<div style="font-size:12px;color:var(--mu);margin-top:4px">HE · IHC · FISH — JPG, PNG, TIFF</div>',
    '<div style="font-size:12px;color:var(--mu);margin-top:4px" data-fr="HE · IHC · FISH — JPG, PNG, TIFF" data-en="HE · IHC · FISH — JPG, PNG, TIFF">HE · IHC · FISH — JPG, PNG, TIFF</div>'
)

# Labels contexte
html = html.replace(
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Type de prélèvement</label>',
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px" data-fr="Type de prélèvement" data-en="Sample type">Type de prélèvement</label>'
)
html = html.replace(
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Coloration / technique</label>',
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px" data-fr="Coloration / technique" data-en="Staining / technique">Coloration / technique</label>'
)
html = html.replace(
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Contexte clinique (optionnel)</label>',
    '<label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px" data-fr="Contexte clinique (optionnel)" data-en="Clinical context (optional)">Contexte clinique (optionnel)</label>'
)

# Placeholder textarea
html = html.replace(
    'placeholder="Ex: Femme 45 ans, masse 2cm, gg sentinelle positif..."',
    'placeholder="Ex: Femme 45 ans, masse 2cm, gg sentinelle positif..." data-ph-fr="Ex: Femme 45 ans, masse 2cm, gg sentinelle positif..." data-ph-en="Ex: 45-year-old woman, 2cm mass, sentinel node positive..."'
)

# Bouton analyser
html = html.replace(
    '<button class="btn bp3" style="width:100%" id="morphoAnalyzeBtn" onclick="morphoAnalyze()">🧬 Analyser avec Claude AI</button>',
    '<button class="btn bp3" style="width:100%" id="morphoAnalyzeBtn" onclick="morphoAnalyze()" data-fr="🧬 Analyser avec Claude AI" data-en="🧬 Analyze with Claude AI">🧬 Analyser avec Claude AI</button>'
)

# Titres sections résultat
html = html.replace(
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Mutations probables</div>',
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px" data-fr="Mutations probables" data-en="Probable mutations">Mutations probables</div>'
)
html = html.replace(
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Description morphologique</div>',
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px" data-fr="Description morphologique" data-en="Morphological description">Description morphologique</div>'
)
html = html.replace(
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Guidelines recommandées</div>',
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px" data-fr="Guidelines recommandées" data-en="Recommended guidelines">Guidelines recommandées</div>'
)
html = html.replace(
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">🌍 Pertinence populations africaines</div>',
    '<div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px" data-fr="🌍 Pertinence populations africaines" data-en="🌍 African populations relevance">🌍 Pertinence populations africaines</div>'
)

# Boutons export
html = html.replace(
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="morphoExport()">📄 Exporter rapport</button>',
    '<button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="morphoExport()" data-fr="📄 Exporter rapport" data-en="📄 Export report">📄 Exporter rapport</button>'
)
html = html.replace(
    '<button class="btn bp3" style="font-size:12px" onclick="morphoToClinician()">🩺 Envoyer au clinicien virtuel</button>',
    '<button class="btn bp3" style="font-size:12px" onclick="morphoToClinician()" data-fr="🩺 Envoyer au clinicien virtuel" data-en="🩺 Send to virtual clinician">🩺 Envoyer au clinicien virtuel</button>'
)

# Bouton sidebar morpho
html = html.replace(
    '<button class="ni" onclick="showSec(\'morpho\',this)"><span class="ni-i">🔬</span><span data-fr="Morpho-Génétique IA" data-en="Virtual Clinicians">Morpho-Génétique IA</span></button>',
    '<button class="ni" onclick="showSec(\'morpho\',this)"><span class="ni-i">🔬</span><span data-fr="Morpho-Génétique IA" data-en="Morpho-Genetic AI">Morpho-Génétique IA</span></button>'
)

print("✅ data-fr/data-en ajoutés au module Morpho-Génétique")

# ─────────────────────────────────────────────────────────────
# 4. Mettre à jour le compteur de modules (15 → 16)
# ─────────────────────────────────────────────────────────────
html = html.replace(
    'data-fr="🧪 15 modules" data-en="🧪 15 modules">🧪 15 modules',
    'data-fr="🧪 16 modules" data-en="🧪 16 modules">🧪 16 modules'
)
print("✅ Compteur modules : 15 → 16")

# ─────────────────────────────────────────────────────────────
# 5. Ajouter data-ph-fr/data-ph-en pour les placeholders
#    dans setLang() si pas encore présent
# ─────────────────────────────────────────────────────────────
if 'data-ph-fr' not in html:
    OLD_SETLANG2 = "  document.querySelectorAll('[data-fr]').forEach(el=>{"
    NEW_SETLANG2 = """  // Translate placeholders data-ph-fr / data-ph-en
  document.querySelectorAll('[data-ph-fr]').forEach(el=>{
    const ph = l==='en' ? el.getAttribute('data-ph-en') : el.getAttribute('data-ph-fr');
    if(ph) el.placeholder = ph;
  });

  document.querySelectorAll('[data-fr]').forEach(el=>{"""
    html = html.replace(OLD_SETLANG2, NEW_SETLANG2)
    print("✅ Traduction placeholders data-ph-fr/data-ph-en ajoutée dans setLang()")
else:
    print("✅ Traduction placeholders déjà présente")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n✅ templates/index.html patché avec succès")
print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: switcher FR/EN topbar + traduction module Morpho + 16 modules"')
print("  git push origin main")
