#!/usr/bin/env python3
"""
patch_manchester_ui.py
Ajoute l'interface Manchester/Tyrer-Cuzick dans index.html.
Le backend existe déjà dans advanced_modules.py + app.py.

Exécuter depuis SenGenoScope/ :
  python3 patch_manchester_ui.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Bouton sidebar (après Comparaison guidelines)
# ─────────────────────────────────────────────────────────────
OLD_BTN = '''    <button class="ni" onclick="showSec('glcomp',this)"><span class="ni-i">📋</span><span data-fr="Comparaison guidelines" data-en="Guidelines Comparison">Comparaison guidelines</span></button>'''

NEW_BTN = OLD_BTN + '''
    <button class="ni" onclick="showSec('manchester',this)"><span class="ni-i">🎗️</span><span data-fr="Score Manchester / Tyrer-Cuzick" data-en="Manchester / Tyrer-Cuzick Score">Score Manchester / TC</span></button>'''

if OLD_BTN in html:
    html = html.replace(OLD_BTN, NEW_BTN)
    print("✅ Bouton sidebar ajouté")
else:
    print("❌ Bouton sidebar non trouvé")

# ─────────────────────────────────────────────────────────────
# 2. Ajouter 'manchester' dans showSec
# ─────────────────────────────────────────────────────────────
OLD_SHOWSEC = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"
NEW_SHOWSEC = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"

if OLD_SHOWSEC in html:
    html = html.replace(OLD_SHOWSEC, NEW_SHOWSEC)
    print("✅ 'manchester' ajouté dans showSec")
else:
    print("❌ Liste showSec non trouvée")

# ─────────────────────────────────────────────────────────────
# 3. Section HTML complète
# ─────────────────────────────────────────────────────────────
MANCHESTER_SECTION = '''
  <!-- ══ MANCHESTER / TYRER-CUZICK ════════════════════════════════════════ -->
  <div id="sec-manchester" style="display:none">
    <div style="padding:14px 16px;border-bottom:1px solid var(--bd)">
      <div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px"
           data-fr="🎗️ Score Manchester &amp; Tyrer-Cuzick — Risque BRCA &amp; Cancer du sein"
           data-en="🎗️ Manchester Score &amp; Tyrer-Cuzick — BRCA &amp; Breast Cancer Risk">
        🎗️ Score Manchester &amp; Tyrer-Cuzick — Risque BRCA &amp; Cancer du sein
      </div>
      <div style="font-size:12px;color:var(--mu);line-height:1.6">
        <span data-fr="Manchester Score (Evans 2004) : indique si un test génétique BRCA est recommandé. Tyrer-Cuzick : risque cumulatif à 10 ans et au cours de la vie."
              data-en="Manchester Score (Evans 2004): indicates whether BRCA genetic testing is recommended. Tyrer-Cuzick: 10-year and lifetime cumulative risk.">
          Manchester Score (Evans 2004) : indique si un test génétique BRCA est recommandé. Tyrer-Cuzick : risque cumulatif à 10 ans et au cours de la vie.
        </span>
      </div>
    </div>

    <div style="padding:14px">
      <!-- Onglets -->
      <div style="display:flex;gap:8px;margin-bottom:16px">
        <button class="btn bp3" id="tab-manchester-btn" onclick="switchManchTab('manchester',this)"
                data-fr="🏆 Score de Manchester" data-en="🏆 Manchester Score">🏆 Score de Manchester</button>
        <button class="btn" style="background:var(--s2);color:var(--mu)" id="tab-tyrer-btn"
                onclick="switchManchTab('tyrer',this)"
                data-fr="📊 Tyrer-Cuzick (IBIS)" data-en="📊 Tyrer-Cuzick (IBIS)">📊 Tyrer-Cuzick (IBIS)</button>
      </div>

      <!-- ── MANCHESTER ── -->
      <div id="manch-panel-manchester">
        <div style="font-size:13px;color:var(--mu);background:var(--s2);padding:10px 13px;border-radius:7px;margin-bottom:14px;line-height:1.7"
             data-fr="Indiquez le nombre de membres de la famille (1er et 2ème degré) atteints pour chaque critère. Score ≥10 → test BRCA recommandé."
             data-en="Enter the number of family members (1st and 2nd degree) affected for each criterion. Score ≥10 → BRCA testing recommended.">
          Indiquez le nombre de membres de la famille (1er et 2ème degré) atteints pour chaque critère. Score ≥10 → test BRCA recommandé.
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin-bottom:14px">

          <div style="background:var(--s2);border-radius:9px;padding:12px;border:1px solid var(--bd)">
            <div style="font-size:12px;font-weight:700;color:var(--pr);margin-bottom:8px"
                 data-fr="🎀 Cancer du sein" data-en="🎀 Breast Cancer">🎀 Cancer du sein</div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="< 40 ans (6 pts)" data-en="< 40 years (6 pts)">&lt; 40 ans (6 pts)</label>
              <input type="number" id="m_breast_under40" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="40-49 ans (4 pts)" data-en="40-49 years (4 pts)">40-49 ans (4 pts)</label>
              <input type="number" id="m_breast_40_49" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="50-59 ans (3 pts)" data-en="50-59 years (3 pts)">50-59 ans (3 pts)</label>
              <input type="number" id="m_breast_50_59" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="≥ 60 ans (2 pts)" data-en="≥ 60 years (2 pts)">≥ 60 ans (2 pts)</label>
              <input type="number" id="m_breast_60_plus" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="Bilatéral (8 pts)" data-en="Bilateral (8 pts)">Bilatéral (8 pts)</label>
              <input type="number" id="m_breast_bilateral" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <label style="font-size:11px;color:var(--tx)" data-fr="Homme (8 pts)" data-en="Male (8 pts)">Homme (8 pts)</label>
              <input type="number" id="m_breast_male" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
          </div>

          <div style="background:var(--s2);border-radius:9px;padding:12px;border:1px solid var(--bd)">
            <div style="font-size:12px;font-weight:700;color:var(--pu);margin-bottom:8px"
                 data-fr="🔵 Autres cancers" data-en="🔵 Other cancers">🔵 Autres cancers</div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="Ovaire tout âge (5 pts)" data-en="Ovary any age (5 pts)">Ovaire tout âge (5 pts)</label>
              <input type="number" id="m_ovary_any_age" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="Pancréas familial (2 pts)" data-en="Family pancreas (2 pts)">Pancréas familial (2 pts)</label>
              <input type="number" id="m_pancreas_any" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:var(--tx)" data-fr="Prostate < 60 ans (2 pts)" data-en="Prostate < 60 years (2 pts)">Prostate &lt; 60 ans (2 pts)</label>
              <input type="number" id="m_prostate_under60" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <label style="font-size:11px;color:var(--tx)" data-fr="Triple négatif < 40 ans (4 pts)" data-en="Triple negative < 40y (4 pts)">Triple négatif &lt;40 ans (4 pts)</label>
              <input type="number" id="m_triple_negative_under40" min="0" max="5" value="0"
                     style="width:60px;padding:4px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px;text-align:center">
            </div>
          </div>
        </div>

        <button class="btn bp3" style="width:100%" onclick="calcManchester()"
                data-fr="🧮 Calculer le score de Manchester" data-en="🧮 Calculate Manchester Score">
          🧮 Calculer le score de Manchester
        </button>
        <div id="manchResult" style="margin-top:14px"></div>
      </div>

      <!-- ── TYRER-CUZICK ── -->
      <div id="manch-panel-tyrer" style="display:none">
        <div style="font-size:13px;color:var(--mu);background:var(--s2);padding:10px 13px;border-radius:7px;margin-bottom:14px;line-height:1.7"
             data-fr="Estimation du risque cumulatif à 10 ans et au cours de la vie (modèle IBIS simplifié). Pour le calcul officiel complet, utiliser l'outil IBIS."
             data-en="Estimation of 10-year and lifetime cumulative risk (simplified IBIS model). For full official calculation, use the IBIS tool.">
          Estimation du risque cumulatif à 10 ans et au cours de la vie (modèle IBIS simplifié).
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin-bottom:14px">

          <div style="background:var(--s2);border-radius:9px;padding:12px;border:1px solid var(--bd)">
            <div style="font-size:12px;font-weight:700;color:var(--pr);margin-bottom:8px"
                 data-fr="👤 Données personnelles" data-en="👤 Personal data">👤 Données personnelles</div>

            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="Âge actuel" data-en="Current age">Âge actuel</label>
              <input type="number" id="tc_age" min="20" max="80" value="45"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="IMC (kg/m²)" data-en="BMI (kg/m²)">IMC (kg/m²)</label>
              <input type="number" id="tc_bmi" min="15" max="50" value="25" step="0.1"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="Âge ménarche" data-en="Age at menarche">Âge ménarche</label>
              <input type="number" id="tc_menarche" min="8" max="18" value="12"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="Âge ménopause (laisser vide si non ménopausée)"
                     data-en="Age at menopause (leave blank if premenopausal)">
                Âge ménopause (vide si non ménopausée)
              </label>
              <input type="number" id="tc_menopause" min="35" max="65" placeholder="—"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
          </div>

          <div style="background:var(--s2);border-radius:9px;padding:12px;border:1px solid var(--bd)">
            <div style="font-size:12px;font-weight:700;color:var(--pu);margin-bottom:8px"
                 data-fr="🧬 Antécédents &amp; Facteurs de risque"
                 data-en="🧬 History &amp; Risk factors">🧬 Antécédents &amp; Facteurs de risque</div>

            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="Cancers du sein 1er degré (mère, sœur, fille)"
                     data-en="1st degree breast cancers (mother, sister, daughter)">
                Cancers sein 1er degré
              </label>
              <input type="number" id="tc_1st" min="0" max="5" value="0"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div style="margin-bottom:8px">
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                     data-fr="Cancers du sein 2ème degré" data-en="2nd degree breast cancers">
                Cancers sein 2ème degré
              </label>
              <input type="number" id="tc_2nd" min="0" max="5" value="0"
                     style="width:100%;padding:6px 10px;border-radius:5px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>

            <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px">
              <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--tx);cursor:pointer">
                <input type="checkbox" id="tc_brca1" style="width:14px;height:14px">
                <span data-fr="Mutation BRCA1 familiale" data-en="Family BRCA1 mutation">Mutation BRCA1 familiale</span>
              </label>
              <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--tx);cursor:pointer">
                <input type="checkbox" id="tc_brca2" style="width:14px;height:14px">
                <span data-fr="Mutation BRCA2 familiale" data-en="Family BRCA2 mutation">Mutation BRCA2 familiale</span>
              </label>
              <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--tx);cursor:pointer">
                <input type="checkbox" id="tc_nulliparous" style="width:14px;height:14px">
                <span data-fr="Nullipare (aucune grossesse)" data-en="Nulliparous (no pregnancies)">Nullipare</span>
              </label>
              <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--tx);cursor:pointer">
                <input type="checkbox" id="tc_hrt" style="width:14px;height:14px">
                <span data-fr="Traitement hormonal substitutif (THS)" data-en="Hormone replacement therapy (HRT)">THS</span>
              </label>
              <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--tx);cursor:pointer">
                <input type="checkbox" id="tc_atyp" style="width:14px;height:14px">
                <span data-fr="Hyperplasie atypique (biopsie)" data-en="Atypical hyperplasia (biopsy)">Hyperplasie atypique</span>
              </label>
            </div>
          </div>
        </div>

        <button class="btn bp3" style="width:100%" onclick="calcTyrerCuzick()"
                data-fr="📊 Calculer le risque Tyrer-Cuzick" data-en="📊 Calculate Tyrer-Cuzick Risk">
          📊 Calculer le risque Tyrer-Cuzick
        </button>
        <div id="tyrerResult" style="margin-top:14px"></div>
      </div>

      <!-- Référence -->
      <div style="margin-top:14px;font-size:11px;color:var(--mu);padding:8px 10px;border-left:2px solid var(--bd);line-height:1.5">
        📚 Evans DGR et al. JNCI 2004;96:370 (PMID 14996858) · Tyrer J et al. Stat Methods Med Res 2004;13:395 (PMID 15622009)<br>
        🔒 Outil d'aide à la décision — Validation clinique requise · Dr. Moustapha Gassama · SenGenoScope
      </div>
    </div>
  </div>

'''

# Insérer avant sec-about
OLD_ABOUT = '  <div id="sec-about" style="display:none">'
if OLD_ABOUT in html:
    html = html.replace(OLD_ABOUT, MANCHESTER_SECTION + OLD_ABOUT)
    print("✅ Section Manchester/TC insérée")
else:
    print("❌ Ancre sec-about non trouvée")

# ─────────────────────────────────────────────────────────────
# 4. JavaScript
# ─────────────────────────────────────────────────────────────
MANCHESTER_JS = '''
// ══ MANCHESTER / TYRER-CUZICK ════════════════════════════════════════════════
function switchManchTab(tab, btn) {
  ['manchester','tyrer'].forEach(t => {
    document.getElementById('manch-panel-' + t).style.display = t === tab ? 'block' : 'none';
  });
  document.querySelectorAll('#sec-manchester .btn').forEach(b => {
    if(b.id === 'tab-manchester-btn' || b.id === 'tab-tyrer-btn') {
      b.classList.remove('bp3');
      b.style.background = 'var(--s2)';
      b.style.color = 'var(--mu)';
    }
  });
  btn.classList.add('bp3');
  btn.style.background = '';
  btn.style.color = '';
}

async function calcManchester() {
  const family = {
    breast_under40:         parseInt(document.getElementById('m_breast_under40').value)||0,
    breast_40_49:           parseInt(document.getElementById('m_breast_40_49').value)||0,
    breast_50_59:           parseInt(document.getElementById('m_breast_50_59').value)||0,
    breast_60_plus:         parseInt(document.getElementById('m_breast_60_plus').value)||0,
    breast_bilateral:       parseInt(document.getElementById('m_breast_bilateral').value)||0,
    breast_male:            parseInt(document.getElementById('m_breast_male').value)||0,
    ovary_any_age:          parseInt(document.getElementById('m_ovary_any_age').value)||0,
    pancreas_any:           parseInt(document.getElementById('m_pancreas_any').value)||0,
    prostate_under60:       parseInt(document.getElementById('m_prostate_under60').value)||0,
    triple_negative_under40:parseInt(document.getElementById('m_triple_negative_under40').value)||0,
  };

  const res = document.getElementById('manchResult');
  res.innerHTML = '<div style="color:var(--mu);font-size:13px">⏳ Calcul en cours…</div>';

  try {
    const r = await fetch('/manchester', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({family})
    });
    const d = await r.json();

    const colMap = {very_high:'#dc2626', high:'#d97706', moderate:'#0891b2', low:'#16a34a'};
    const bgMap  = {very_high:'#fef2f2', high:'#fffbeb', moderate:'#e0f2fe', low:'#f0fdf4'};
    const col = colMap[d.level] || '#0891b2';
    const bg  = bgMap[d.level]  || '#e0f2fe';

    let detailRows = (d.details||[]).map(det =>
      `<tr>
        <td style="padding:5px 8px;font-size:12px">${det.criterion}</td>
        <td style="padding:5px 8px;font-size:12px;text-align:center">${det.count}</td>
        <td style="padding:5px 8px;font-size:12px;text-align:center;font-weight:700;color:${col}">+${det.points}</td>
      </tr>`
    ).join('');

    res.innerHTML = `
      <div style="background:${bg};border:1.5px solid ${col};border-radius:9px;padding:14px;margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px">
          <div style="text-align:center">
            <div style="font-size:42px;font-weight:800;color:${col}">${d.score}</div>
            <div style="font-size:11px;color:var(--mu)">Score total</div>
          </div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:700;color:${col};margin-bottom:4px">${d.probability}</div>
            <div style="font-size:12px;color:var(--tx);line-height:1.5">${d.recommendation}</div>
          </div>
          <div style="text-align:center;background:${col};color:#fff;border-radius:7px;padding:6px 12px">
            <div style="font-size:10px;font-weight:700">${d.threshold_test ? '✅ TEST' : '⬜ TEST'}</div>
            <div style="font-size:9px">RECOMMANDÉ</div>
          </div>
        </div>
        ${detailRows ? `
        <div style="border-top:1px solid ${col}40;padding-top:10px">
          <div style="font-size:11px;color:var(--mu);margin-bottom:6px">Détail des critères :</div>
          <table style="width:100%;border-collapse:collapse">
            <thead><tr>
              <th style="padding:4px 8px;font-size:11px;color:var(--mu);text-align:left">Critère</th>
              <th style="padding:4px 8px;font-size:11px;color:var(--mu)">Nb</th>
              <th style="padding:4px 8px;font-size:11px;color:var(--mu)">Points</th>
            </tr></thead>
            <tbody>${detailRows}</tbody>
          </table>
        </div>` : ''}
      </div>
      <div style="font-size:11px;color:var(--mu)">📚 ${d.reference}</div>`;

  } catch(e) {
    document.getElementById('manchResult').innerHTML =
      `<div style="color:var(--dg);font-size:13px">❌ Erreur : ${e.message}</div>`;
  }
}

async function calcTyrerCuzick() {
  const data = {
    age:                    parseInt(document.getElementById('tc_age').value)||45,
    bmi:                    parseFloat(document.getElementById('tc_bmi').value)||25,
    age_menarche:           parseInt(document.getElementById('tc_menarche').value)||12,
    age_menopause:          document.getElementById('tc_menopause').value ? parseInt(document.getElementById('tc_menopause').value) : null,
    breast_cancer_1st_degree: parseInt(document.getElementById('tc_1st').value)||0,
    breast_cancer_2nd_degree: parseInt(document.getElementById('tc_2nd').value)||0,
    family_brca1:           document.getElementById('tc_brca1').checked,
    family_brca2:           document.getElementById('tc_brca2').checked,
    nulliparous:            document.getElementById('tc_nulliparous').checked,
    hrt_use:                document.getElementById('tc_hrt').checked,
    atypical_hyperplasia:   document.getElementById('tc_atyp').checked,
  };

  const res = document.getElementById('tyrerResult');
  res.innerHTML = '<div style="color:var(--mu);font-size:13px">⏳ Calcul en cours…</div>';

  try {
    const r = await fetch('/tyrer_cuzick', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    const d = await r.json();

    const risk = d.estimated_risk_10y_percent;
    const col = risk >= 8 ? '#dc2626' : risk >= 5 ? '#d97706' : risk >= 3 ? '#0891b2' : '#16a34a';
    const bg  = risk >= 8 ? '#fef2f2' : risk >= 5 ? '#fffbeb' : risk >= 3 ? '#e0f2fe' : '#f0fdf4';

    const factorsHtml = (d.factors||[]).map(f =>
      `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--bd);font-size:12px">
        <span>${f.factor}</span>
        <span style="font-weight:700;color:${col}">${f.effect}</span>
      </div>`
    ).join('') || '<div style="font-size:12px;color:var(--mu)">Aucun facteur de risque supplémentaire</div>';

    res.innerHTML = `
      <div style="background:${bg};border:1.5px solid ${col};border-radius:9px;padding:14px;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px;text-align:center">
          <div style="background:rgba(255,255,255,.7);border-radius:7px;padding:10px">
            <div style="font-size:28px;font-weight:800;color:${col}">${risk}%</div>
            <div style="font-size:10px;color:var(--mu)">Risque à 10 ans</div>
          </div>
          <div style="background:rgba(255,255,255,.7);border-radius:7px;padding:10px">
            <div style="font-size:28px;font-weight:800;color:${col}">${d.estimated_lifetime_risk_percent}%</div>
            <div style="font-size:10px;color:var(--mu)">Risque vie entière</div>
          </div>
          <div style="background:rgba(255,255,255,.7);border-radius:7px;padding:10px">
            <div style="font-size:28px;font-weight:800;color:var(--mu)">${d.population_lifetime_risk}</div>
            <div style="font-size:10px;color:var(--mu)">Population générale</div>
          </div>
        </div>
        <div style="font-size:14px;font-weight:700;color:${col};margin-bottom:6px">${d.risk_level}</div>
        <div style="font-size:12px;color:var(--tx);line-height:1.5;margin-bottom:12px">${d.recommendation}</div>
        <div style="font-size:11px;font-weight:700;color:var(--mu);margin-bottom:6px">Facteurs modificateurs (×${d.multiplier}) :</div>
        ${factorsHtml}
      </div>
      <div style="font-size:11px;color:var(--mu);line-height:1.5">
        ⚠️ ${d.note}<br>📚 ${d.reference}
      </div>`;

  } catch(e) {
    document.getElementById('tyrerResult').innerHTML =
      `<div style="color:var(--dg);font-size:13px">❌ Erreur : ${e.message}</div>`;
  }
}
// ══ FIN MANCHESTER ════════════════════════════════════════════════════════════
'''

last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + MANCHESTER_JS + html[last_script:]
    print("✅ JavaScript Manchester/TC inséré")
else:
    print("❌ </script> final non trouvé")

# ─────────────────────────────────────────────────────────────
# 5. Mettre à jour le compteur modules (16 → 17)
# ─────────────────────────────────────────────────────────────
html = html.replace(
    'data-fr="🧪 16 modules" data-en="🧪 16 modules">🧪 16 modules',
    'data-fr="🧪 17 modules" data-en="🧪 17 modules">🧪 17 modules'
)
print("✅ Compteur modules : 16 → 17")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: interface Manchester Score + Tyrer-Cuzick intégrée"')
print("  git push origin main")
