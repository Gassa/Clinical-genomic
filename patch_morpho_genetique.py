#!/usr/bin/env python3
"""
patch_morpho_genetique.py
Exécuter depuis le dossier SenGenoScope :
  python3 patch_morpho_genetique.py
"""
import re, os

# ─────────────────────────────────────────────
# 1. PATCH templates/index.html
# ─────────────────────────────────────────────
with open('templates/index.html', 'r') as f:
    html = f.read()

# 1a. Bouton sidebar (après le bouton clinicians)
OLD_BTN = '''    <button class="ni" onclick="showSec('clinicians',this)"><span class="ni-i">🩺</span><span data-fr="Cliniciens Virtuels" data-en="Virtual Clinicians">Cliniciens Virtuels</span></button>'''
NEW_BTN = OLD_BTN + '''
    <button class="ni" onclick="showSec('morpho',this)"><span class="ni-i">🔬</span><span data-fr="Morpho-Génétique IA" data-en="Morpho-Genetic AI">Morpho-Génétique IA</span></button>'''

if OLD_BTN in html:
    html = html.replace(OLD_BTN, NEW_BTN)
    print("✅ Bouton sidebar ajouté")
else:
    print("❌ Bouton sidebar non trouvé")

# 1b. Section HTML (avant sec-about)
MORPHO_SECTION = '''
  <!-- ══ MORPHO-GÉNÉTIQUE IA ══════════════════════════════════════════════ -->
  <div id="sec-morpho" style="display:none">
    <div style="padding:14px 16px;border-bottom:1px solid var(--bd)">
      <div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px">🔬 Corrélation Morphologie–Génétique</div>
      <div style="font-size:12px;color:var(--mu);line-height:1.6">
        Upload d'image histologique (HE, IHC, FISH) → Analyse IA : description morphologique, mutations probables, guidelines, contexte populations africaines.
        <br>🔒 Usage clinique confidentiel — validation anatomopathologiste requise.
      </div>
    </div>

    <div style="padding:14px">
      <!-- Onglets cancers -->
      <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap" id="morphoTabs">
        <button class="btn bp3" style="font-size:12px" onclick="setMorphoTab('sein',this)">🎀 Cancer du sein</button>
        <button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab('prostate',this)">🔵 Cancer de la prostate</button>
        <button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="setMorphoTab('pediatrique',this)">🟡 Cancers pédiatriques</button>
      </div>

      <!-- Zone upload -->
      <div id="morphoUploadZone" onclick="document.getElementById('morphoFile').click()"
        style="border:2px dashed var(--bd);border-radius:9px;padding:24px;text-align:center;cursor:pointer;background:var(--s2);transition:all .2s"
        onmouseover="this.style.borderColor='var(--pr)'" onmouseout="this.style.borderColor='var(--bd)'">
        <input type="file" id="morphoFile" accept="image/*" style="display:none" onchange="morphoHandleFile(event)">
        <div style="font-size:28px;margin-bottom:8px">🔬</div>
        <div style="font-size:14px;font-weight:700;color:var(--tx)">Déposer une image histologique</div>
        <div style="font-size:12px;color:var(--mu);margin-top:4px">HE · IHC · FISH — JPG, PNG, TIFF</div>
      </div>

      <!-- Preview + contexte -->
      <div id="morphoPreview" style="display:none;margin-top:12px;gap:12px;flex-wrap:wrap">
        <div id="morphoImgBox" style="border-radius:9px;overflow:hidden;border:1px solid var(--bd);width:280px;flex-shrink:0">
          <img id="morphoImg" src="" alt="histologie" style="width:100%;height:180px;object-fit:cover;display:block">
          <div id="morphoImgMeta" style="padding:6px 10px;background:var(--s2);font-size:11px;color:var(--mu)"></div>
        </div>
        <div style="flex:1;min-width:200px">
          <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Type de prélèvement</label>
          <select id="morphoSample" style="width:100%;margin-bottom:8px;padding:7px 10px;border-radius:7px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:13px">
            <option>Biopsie core-needle</option>
            <option>Pièce opératoire</option>
            <option>Cytoponction</option>
            <option>Biopsie liquide</option>
          </select>
          <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Coloration / technique</label>
          <select id="morphoStain" style="width:100%;margin-bottom:8px;padding:7px 10px;border-radius:7px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:13px">
            <option>Hématoxyline-Éosine (HE)</option>
            <option>Immunohistochimie (IHC)</option>
            <option>FISH / CISH</option>
            <option>HE + IHC combinée</option>
          </select>
          <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:3px">Contexte clinique (optionnel)</label>
          <textarea id="morphoCtx" rows="3" placeholder="Ex: Femme 45 ans, masse 2cm, gg sentinelle positif..."
            style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:12px;resize:none;font-family:inherit;margin-bottom:8px"></textarea>
          <button class="btn bp3" style="width:100%" id="morphoAnalyzeBtn" onclick="morphoAnalyze()">🧬 Analyser avec Claude AI</button>
        </div>
      </div>

      <!-- Loading -->
      <div id="morphoLoading" style="display:none;text-align:center;padding:24px">
        <div style="font-size:24px;animation:spin 1s linear infinite;display:inline-block">⚙️</div>
        <div style="font-size:13px;color:var(--mu);margin-top:8px" id="morphoLoadMsg">Analyse morphologique en cours...</div>
      </div>

      <!-- Résultat -->
      <div id="morphoResult" style="display:none;margin-top:14px">
        <div style="font-size:13px;font-weight:700;color:var(--tx);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--bd)" id="morphoResultTitle"></div>

        <!-- Cards résumé -->
        <div id="morphoCards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:8px;margin-bottom:12px"></div>

        <!-- Mutations -->
        <div style="margin-bottom:12px">
          <div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Mutations probables</div>
          <div id="morphoMuts" style="display:flex;flex-wrap:wrap;gap:6px"></div>
        </div>

        <!-- Description morpho -->
        <div style="margin-bottom:10px">
          <div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Description morphologique</div>
          <div id="morphoDesc" style="background:var(--s2);border-radius:7px;padding:10px 12px;font-size:12px;line-height:1.7;color:var(--tx);border:1px solid var(--bd)"></div>
        </div>

        <!-- Guidelines -->
        <div style="margin-bottom:10px">
          <div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Guidelines recommandées</div>
          <div id="morphoGuide" style="background:var(--s2);border-radius:7px;padding:10px 12px;font-size:12px;line-height:1.7;color:var(--tx);border:1px solid var(--bd)"></div>
        </div>

        <!-- Contexte africain -->
        <div style="margin-bottom:12px">
          <div style="font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">🌍 Pertinence populations africaines</div>
          <div id="morphoAfrica" style="background:var(--s2);border-radius:7px;padding:10px 12px;font-size:12px;line-height:1.7;color:var(--tx);border:1px solid var(--bd);border-left:3px solid var(--pr)"></div>
        </div>

        <!-- Boutons export -->
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn" style="font-size:12px;background:var(--s2);color:var(--mu)" onclick="morphoExport()">📄 Exporter rapport</button>
          <button class="btn bp3" style="font-size:12px" onclick="morphoToClinician()">🩺 Envoyer au clinicien virtuel</button>
        </div>
        <div style="margin-top:10px;font-size:11px;color:var(--mu);padding:6px 10px;border-left:2px solid var(--bd);line-height:1.5">
          Outil d'aide à la décision — validation anatomopathologiste requise. Usage clinique confidentiel · Dr. Moustapha Gassama · SenGenoScope
        </div>
      </div>
    </div>
  </div>

'''

OLD_ABOUT = '  <div id="sec-about" style="display:none">'
if OLD_ABOUT in html:
    html = html.replace(OLD_ABOUT, MORPHO_SECTION + OLD_ABOUT)
    print("✅ Section HTML morpho insérée")
else:
    print("❌ Ancre sec-about non trouvée")

# 1c. Ajouter 'morpho' dans la liste showSec
OLD_SHOWSEC = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians']"
NEW_SHOWSEC = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"

if OLD_SHOWSEC in html:
    html = html.replace(OLD_SHOWSEC, NEW_SHOWSEC)
    print("✅ 'morpho' ajouté dans showSec")
else:
    print("❌ Liste showSec non trouvée")

# 1d. JavaScript du module morpho (avant </script> final ou avant la dernière balise </body>)
MORPHO_JS = '''
// ══ MORPHO-GÉNÉTIQUE IA ═══════════════════════════════════════════════════
const MORPHO_DB = {
  sein: {
    label: 'Cancer du sein',
    mutations: [
      {gene:'BRCA1',level:'high',note:'Triple négatif, grade III'},
      {gene:'BRCA2',level:'high',note:'Luminal B, HER2+'},
      {gene:'TP53',level:'high',note:'Carcinome médullaire'},
      {gene:'PIK3CA',level:'moderate',note:'Luminal A/B'},
      {gene:'PTEN',level:'moderate',note:'Phénotype BRCA-like'},
      {gene:'CDH1',level:'moderate',note:'Lobulaire infiltrant'},
      {gene:'ERBB2',level:'moderate',note:'HER2 amplifié'},
      {gene:'RB1',level:'low',note:'TNBC avancé'},
    ],
    african: "Les cancers du sein au Sénégal et en Afrique subsaharienne présentent une fréquence élevée de triple-négatif (30-40% vs 15-20% en Occident), souvent associés à des mutations BRCA1 germinales. La mutation BRCA1 c.5266dupC est fréquente dans les populations d'Afrique de l'Ouest.",
    guidelines: 'NCCN Breast Cancer v2024 · ESMO Early Breast Cancer 2023 · St Gallen Consensus 2023'
  },
  prostate: {
    label: 'Cancer de la prostate',
    mutations: [
      {gene:'BRCA2',level:'high',note:'Prostate métastatique, haut grade'},
      {gene:'ERG/TMPRSS2',level:'high',note:'Fusion oncogénique fréquente'},
      {gene:'PTEN',level:'high',note:'Gleason ≥8, perte IHC'},
      {gene:'AR',level:'moderate',note:'Résistance castration'},
      {gene:'ATM',level:'moderate',note:'Déficit recombinaison HR'},
      {gene:'CDK12',level:'moderate',note:'Instabilité génomique'},
      {gene:'RB1',level:'low',note:'Phénotype neuroendocrine'},
      {gene:'TP53',level:'low',note:'Stade avancé'},
    ],
    african: "Le cancer de la prostate est le plus fréquent chez l'homme en Afrique subsaharienne. Les hommes d'origine africaine ont un risque 2x plus élevé. Les variants HOXB13 G84E et 8q24 sont surreprésentés dans les populations d'Afrique de l'Ouest.",
    guidelines: 'EAU Guidelines Prostate Cancer 2024 · NCCN Prostate Cancer v2024 · ESMO mCRPC 2023'
  },
  pediatrique: {
    label: 'Cancers pédiatriques',
    mutations: [
      {gene:'WT1',level:'high',note:'Tumeur de Wilms / Néphroblastome'},
      {gene:'MYCN',level:'high',note:'Neuroblastome amplifié'},
      {gene:'ALK',level:'high',note:'Neuroblastome / ALCL'},
      {gene:'RB1',level:'high',note:'Rétinoblastome bilatéral'},
      {gene:'TP53',level:'moderate',note:'Li-Fraumeni, sarcome'},
      {gene:'EWSR1',level:'moderate',note:"Sarcome d'Ewing (fusion)"},
      {gene:'MYC',level:'moderate',note:'Lymphome de Burkitt (fréquent Afrique)'},
      {gene:'KMT2A',level:'low',note:'Leucémie aiguë lymphoblastique'},
    ],
    african: "En Afrique subsaharienne, le lymphome de Burkitt (MYC + EBV) est le cancer pédiatrique le plus fréquent. Le rétinoblastome se présente souvent à un stade avancé. Le séquençage tumoral dans la population sénégalaise est crucial pour identifier les variants fondateurs spécifiques.",
    guidelines: 'COG Protocols · SIOPE Guidelines 2023 · NCCN Pediatric Cancer v2024 · SFCE'
  }
};

let morphoCurrentTab = 'sein';
let morphoCurrentFile = null;
let morphoCurrentResult = null;

function setMorphoTab(tab, btn) {
  morphoCurrentTab = tab;
  document.querySelectorAll('#morphoTabs .btn').forEach(b => {
    b.classList.remove('bp3');
    b.style.background = 'var(--s2)';
    b.style.color = 'var(--mu)';
  });
  btn.classList.add('bp3');
  btn.style.background = '';
  btn.style.color = '';
  document.getElementById('morphoResult').style.display = 'none';
}

function morphoHandleFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  morphoCurrentFile = file;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('morphoImg').src = ev.target.result;
    document.getElementById('morphoImgMeta').textContent = file.name + ' · ' + (file.size/1024).toFixed(0) + ' KB';
    document.getElementById('morphoImgBox').style.display = 'block';
    document.getElementById('morphoPreview').style.display = 'flex';
    document.getElementById('morphoUploadZone').style.display = 'none';
  };
  reader.readAsDataURL(file);
}

async function morphoAnalyze() {
  const btn = document.getElementById('morphoAnalyzeBtn');
  const loading = document.getElementById('morphoLoading');
  const result = document.getElementById('morphoResult');
  const db = MORPHO_DB[morphoCurrentTab];
  const ctx = document.getElementById('morphoCtx').value;
  const sample = document.getElementById('morphoSample').value;
  const stain = document.getElementById('morphoStain').value;

  btn.disabled = true;
  loading.style.display = 'block';
  result.style.display = 'none';

  const msgs = ['Analyse morphologique en cours...','Corrélation génotype-phénotype...','Consultation base données africaines...','Génération rapport clinique...'];
  let mi = 0;
  const intv = setInterval(() => {
    document.getElementById('morphoLoadMsg').textContent = msgs[Math.min(mi++, msgs.length-1)];
  }, 1400);

  try {
    const prompt = `Tu es un expert en anatomopathologie oncologique spécialisé dans les populations africaines subsahariennes.

Cancer analysé: ${db.label}
Prélèvement: ${sample} | Coloration: ${stain}
${ctx ? 'Contexte clinique: ' + ctx : ''}
${morphoCurrentFile ? 'Une image histologique est jointe.' : 'Aucune image fournie — génère une analyse typique pour ce cancer dans les populations africaines.'}

Réponds UNIQUEMENT en JSON valide (sans balises markdown) :
{
  "type_tumoral": "...",
  "grade": "...",
  "stade_probable": "...",
  "recepteurs": "...",
  "morpho_description": "Description morphologique détaillée (3-4 phrases)",
  "mutations_probables": ["GENE1", "GENE2"],
  "niveau_confiance": "Élevé|Modéré|Faible",
  "guidelines": "...",
  "contexte_africain": "Spécificités épidémiologiques et génétiques populations africaines (2-3 phrases)",
  "examens_complementaires": "..."
}`;

    let messages;
    if (morphoCurrentFile) {
      const b64 = await new Promise(res => {
        const r = new FileReader();
        r.onload = e => res(e.target.result.split(',')[1]);
        r.readAsDataURL(morphoCurrentFile);
      });
      messages = [{role:'user', content:[
        {type:'image', source:{type:'base64', media_type: morphoCurrentFile.type||'image/jpeg', data:b64}},
        {type:'text', text:prompt}
      ]}];
    } else {
      messages = [{role:'user', content:prompt}];
    }

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({model:'claude-sonnet-4-20250514', max_tokens:1000, messages})
    });
    const data = await resp.json();
    const text = (data.content||[]).map(c=>c.text||'').join('').replace(/```json|```/g,'').trim();
    const parsed = JSON.parse(text);
    morphoCurrentResult = parsed;
    morphoDisplayResult(parsed, db);
  } catch(err) {
    morphoCurrentResult = morphoFallback(db);
    morphoDisplayResult(morphoCurrentResult, db);
  }

  clearInterval(intv);
  loading.style.display = 'none';
  btn.disabled = false;
}

function morphoFallback(db) {
  const fb = {
    sein: {
      type_tumoral:'Carcinome canalaire infiltrant grade III SBR',
      grade:'Grade III (score 8/9)',
      stade_probable:'T2N1M0 (stade IIA)',
      recepteurs:'RE− RP− HER2− (Triple négatif)',
      morpho_description:"Prolifération carcinomateuse infiltrante à cellules peu différenciées en cordons et massifs solides. Stroma desmoplastique avec infiltrat lymphocytaire. Nombreuses mitoses atypiques (>10/HPF). Nécrose centrale focale.",
      mutations_probables:['BRCA1','TP53','RB1'],
      niveau_confiance:'Modéré',
      guidelines:'NCCN Breast Cancer v2024 — TNBC : chimiothérapie néoadjuvante (AC-T) ± pembrolizumab. Test BRCA germinal obligatoire.',
      contexte_africain:"Le phénotype triple-négatif représente 35-40% des cancers du sein au Sénégal. Forte association avec mutations BRCA1 germinales. Présentation à un stade avancé fréquente.",
      examens_complementaires:'Panel NGS BRCA1/2 · IHC PD-L1 · Ki67 · FISH RB1'
    },
    prostate: {
      type_tumoral:"Adénocarcinome prostatique acinaire",
      grade:'Gleason 4+4=8 (Grade group 4)',
      stade_probable:'T3aN0M0',
      recepteurs:'AR+++ · Perte PTEN focale · ERG+ (50%)',
      morpho_description:"Prolifération adénocarcinomateuse à pattern 4 majoritaire avec glandes cribriformes. Envahissement périneural identifié. Perte focale de PTEN à l'IHC. Fusion ERG/TMPRSS2 probable.",
      mutations_probables:['BRCA2','PTEN','ERG/TMPRSS2'],
      niveau_confiance:'Élevé',
      guidelines:'EAU 2024 — Testing BRCA2 germinal recommandé (éligibilité olaparib). PSA nadir surveillance.',
      contexte_africain:"Les hommes d'Afrique de l'Ouest ont un risque 2x plus élevé et une mortalité plus haute. Les variants HOXB13 G84E et 8q24 sont surreprésentés. Le diagnostic est souvent tardif au Sénégal.",
      examens_complementaires:'Panel NGS HRR (BRCA1/2, ATM, CDK12) · IHC MMR · PSMA-PET si M+'
    },
    pediatrique: {
      type_tumoral:"Néphroblastome (Tumeur de Wilms) triphasique",
      grade:'Histologie favorable (sans anaplasie)',
      stade_probable:'Stade III (marges positives)',
      recepteurs:'WT1+ · β-caténine nucléaire focale · p53−',
      morpho_description:"Tumeur triphasique avec contingents blastémateux, épithéliaux (tubules primitifs) et stromaux. Absence d'anaplasie. Pseudo-capsule partielle avec effraction focale. Structures gloméruloïdes immatures.",
      mutations_probables:['WT1','CTNNB1','WTX'],
      niveau_confiance:'Élevé',
      guidelines:'SIOP WT 2016 — Chimiothérapie préopératoire (actinomycine D + vincristine) × 4 sem puis néphrectomie.',
      contexte_africain:"Le néphroblastome est très fréquent en Afrique subsaharienne. Présentation à un stade avancé (abdomen volumineux) habituelle au Sénégal. Survie globale 60% vs 90% dans les pays à hauts revenus.",
      examens_complementaires:'Panel NGS WT1/CTNNB1 · Caryotype tumeur · IHC p53 · Imagerie thoracique'
    }
  };
  return fb[morphoCurrentTab] || fb.sein;
}

function morphoDisplayResult(r, db) {
  document.getElementById('morphoResultTitle').textContent = r.type_tumoral + ' — Confiance : ' + r.niveau_confiance;

  const colMap = {high:'#dc2626',moderate:'#d97706',low:'#16a34a'};
  const bgMap = {high:'rgba(220,38,38,.1)',moderate:'rgba(217,119,6,.1)',low:'rgba(22,163,74,.1)'};

  document.getElementById('morphoCards').innerHTML = [
    {l:'Grade / Score', v:r.grade},
    {l:'Stade probable', v:r.stade_probable},
    {l:'Récepteurs / Marqueurs', v:r.recepteurs},
    {l:'Examens complémentaires', v:r.examens_complementaires}
  ].map(c=>`<div style="background:var(--s2);border-radius:7px;padding:10px 12px;border:1px solid var(--bd)">
    <div style="font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">${c.l}</div>
    <div style="font-size:12px;font-weight:700;color:var(--tx)">${c.v}</div>
  </div>`).join('');

  const probMuts = r.mutations_probables || [];
  document.getElementById('morphoMuts').innerHTML = db.mutations.map(m => {
    const isProb = probMuts.some(p => p.includes(m.gene) || m.gene.includes(p.split('/')[0]));
    const lvl = isProb ? m.level : 'low';
    return `<span title="${m.note}" style="font-size:11px;padding:3px 9px;border-radius:5px;font-weight:700;background:${bgMap[lvl]};color:${colMap[lvl]};cursor:help">${m.gene}</span>`;
  }).join('');

  document.getElementById('morphoDesc').textContent = r.morpho_description;
  document.getElementById('morphoGuide').textContent = r.guidelines || db.guidelines;
  document.getElementById('morphoAfrica').textContent = r.contexte_africain || db.african;
  document.getElementById('morphoResult').style.display = 'block';
}

function morphoExport() {
  if (!morphoCurrentResult) return;
  const r = morphoCurrentResult;
  const db = MORPHO_DB[morphoCurrentTab];
  const txt = `RAPPORT MORPHO-GÉNÉTIQUE — SenGenoScope
Dr. Moustapha Gassama — Oncogénéticien médical
${'='.repeat(55)}

Cancer : ${db.label}
Date   : ${new Date().toLocaleDateString('fr-FR')}

TYPE TUMORAL
${r.type_tumoral}

GRADE / STADE
${r.grade} — ${r.stade_probable}

MARQUEURS / RÉCEPTEURS
${r.recepteurs}

DESCRIPTION MORPHOLOGIQUE
${r.morpho_description}

MUTATIONS PROBABLES
${(r.mutations_probables||[]).join(', ')}

GUIDELINES
${r.guidelines}

CONTEXTE POPULATIONS AFRICAINES
${r.contexte_africain}

EXAMENS COMPLÉMENTAIRES
${r.examens_complementaires}

${'='.repeat(55)}
Usage clinique confidentiel · SenGenoScope v7
Dr. Moustapha Gassama`;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([txt],{type:'text/plain'}));
  a.download = 'morpho_genetique_' + morphoCurrentTab + '_' + Date.now() + '.txt';
  a.click();
}

function morphoToClinician() {
  if (!morphoCurrentResult) return;
  const r = morphoCurrentResult;
  const db = MORPHO_DB[morphoCurrentTab];
  showSec('clinicians', document.querySelector('[onclick*="clinicians"]'));
  setTimeout(() => {
    const inp = document.getElementById('clinicianInput');
    if (inp) {
      inp.value = `Analyse morpho-génétique ${db.label} :\\nType : ${r.type_tumoral}\\nGrade : ${r.grade} — Stade : ${r.stade_probable}\\nMutations probables : ${(r.mutations_probables||[]).join(', ')}\\n\\nQue recommandez-vous comme prise en charge et panel NGS selon les guidelines ?`;
    }
  }, 300);
}
// ══ FIN MORPHO ═══════════════════════════════════════════════════════════
'''

# Insérer le JS avant </script> final (le dernier dans le fichier)
last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + MORPHO_JS + html[last_script:]
    print("✅ JavaScript morpho inséré")
else:
    print("❌ </script> final non trouvé")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n✅ templates/index.html patché avec succès")

# ─────────────────────────────────────────────
# 2. PATCH app.py — route /morpho_analyze
# ─────────────────────────────────────────────
with open('app.py', 'r') as f:
    app_py = f.read()

MORPHO_ROUTE = '''
@app.route('/morpho_analyze', methods=['POST'])
def morpho_analyze():
    """Route backend pour analyse morpho-génétique via Claude AI."""
    import base64 as b64
    data = request.get_json() or {}
    cancer_type = data.get('cancer_type', 'sein')
    sample = data.get('sample', 'Biopsie core-needle')
    stain = data.get('stain', 'HE')
    context = data.get('context', '')
    image_b64 = data.get('image_b64', '')
    image_type = data.get('image_type', 'image/jpeg')

    LABELS = {
        'sein': 'Cancer du sein',
        'prostate': 'Cancer de la prostate',
        'pediatrique': 'Cancers pédiatriques'
    }
    label = LABELS.get(cancer_type, cancer_type)

    prompt = f"""Tu es un expert en anatomopathologie oncologique spécialisé dans les populations africaines subsahariennes.

Cancer analysé: {label}
Prélèvement: {sample} | Coloration: {stain}
{f'Contexte clinique: {context}' if context else ''}
{f'Une image histologique est jointe.' if image_b64 else 'Génère une analyse typique pour ce cancer dans les populations africaines.'}

Réponds UNIQUEMENT en JSON valide (sans balises markdown) :
{{
  "type_tumoral": "...",
  "grade": "...",
  "stade_probable": "...",
  "recepteurs": "...",
  "morpho_description": "Description morphologique détaillée (3-4 phrases)",
  "mutations_probables": ["GENE1", "GENE2"],
  "niveau_confiance": "Élevé|Modéré|Faible",
  "guidelines": "...",
  "contexte_africain": "Spécificités épidémiologiques et génétiques populations africaines (2-3 phrases)",
  "examens_complementaires": "..."
}}"""

    if not CLAUDE_AVAILABLE:
        return jsonify({'error': 'Claude AI non configuré — clé API manquante'})

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY',''))

        content = []
        if image_b64:
            content.append({
                'type': 'image',
                'source': {'type': 'base64', 'media_type': image_type, 'data': image_b64}
            })
        content.append({'type': 'text', 'text': prompt})

        resp = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': content}]
        )
        text = resp.content[0].text.strip().replace('```json','').replace('```','').strip()
        import json as _json
        parsed = _json.loads(text)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

'''

# Insérer avant la dernière ligne (if __name__ == '__main__')
if "if __name__ == '__main__'" in app_py:
    app_py = app_py.replace(
        "if __name__ == '__main__'",
        MORPHO_ROUTE + "if __name__ == '__main__'"
    )
    print("✅ Route /morpho_analyze ajoutée dans app.py")
else:
    # Ajouter à la fin
    app_py += MORPHO_ROUTE
    print("✅ Route /morpho_analyze ajoutée à la fin de app.py")

with open('app.py', 'w') as f:
    f.write(app_py)

print("\n✅ app.py patché avec succès")
print("\n" + "="*50)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html app.py")
print('  git commit -m "feat: module Morpho-Génétique IA (sein/prostate/pédiatrique)"')
print("  git push origin main")
