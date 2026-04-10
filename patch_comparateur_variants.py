#!/usr/bin/env python3
"""
patch_comparateur_variants.py
Ajoute l'interface de comparaison de variants côte à côte dans index.html.
Le backend /compare_variants existe déjà dans app.py + advanced_modules.py.

Exécuter depuis SenGenoScope/ :
  python3 patch_comparateur_variants.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Bouton sidebar
# ─────────────────────────────────────────────────────────────
OLD_BTN = '''    <button class="ni" onclick="showSec('manchester',this)"><span class="ni-i">🎗️</span><span data-fr="Score Manchester / Tyrer-Cuzick" data-en="Manchester / Tyrer-Cuzick Score">Score Manchester / TC</span></button>'''

NEW_BTN = OLD_BTN + '''
    <button class="ni" onclick="showSec('compvar',this)"><span class="ni-i">⚖️</span><span data-fr="Comparateur de variants" data-en="Variant Comparator">Comparateur variants</span></button>'''

if OLD_BTN in html:
    html = html.replace(OLD_BTN, NEW_BTN)
    print("✅ Bouton sidebar ajouté")
else:
    print("❌ Bouton sidebar non trouvé")

# ─────────────────────────────────────────────────────────────
# 2. Ajouter 'compvar' dans showSec
# ─────────────────────────────────────────────────────────────
old_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"
new_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','compvar','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho']"

if old_list in html:
    html = html.replace(old_list, new_list)
    print("✅ 'compvar' ajouté dans showSec")
else:
    print("❌ Liste showSec non trouvée")

# ─────────────────────────────────────────────────────────────
# 3. Section HTML
# ─────────────────────────────────────────────────────────────
COMPVAR_SECTION = '''
  <!-- ══ COMPARATEUR DE VARIANTS ══════════════════════════════════════════ -->
  <div id="sec-compvar" style="display:none">
    <div style="padding:14px 16px;border-bottom:1px solid var(--bd)">
      <div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px"
           data-fr="⚖️ Comparateur de variants — Analyse côte à côte"
           data-en="⚖️ Variant Comparator — Side-by-side analysis">
        ⚖️ Comparateur de variants — Analyse côte à côte
      </div>
      <div style="font-size:12px;color:var(--mu)"
           data-fr="Comparez deux variants selon leurs scores in silico (PolyPhen-2, SIFT, CADD) et leur classification ACMG."
           data-en="Compare two variants by their in silico scores (PolyPhen-2, SIFT, CADD) and ACMG classification.">
        Comparez deux variants selon leurs scores in silico (PolyPhen-2, SIFT, CADD) et leur classification ACMG.
      </div>
    </div>

    <div style="padding:14px">
      <!-- Grille côte à côte -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px">

        <!-- Variant 1 -->
        <div style="background:var(--s2);border-radius:9px;padding:14px;border:2px solid var(--pr)">
          <div style="font-size:13px;font-weight:700;color:var(--pr);margin-bottom:10px">
            🧬 <span data-fr="Variant 1" data-en="Variant 1">Variant 1</span>
          </div>

          <div style="margin-bottom:8px">
            <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                   data-fr="HGVS / Nom du variant" data-en="HGVS / Variant name">HGVS / Nom</label>
            <input type="text" id="cv1_hgvs" placeholder="ex: BRCA1 c.5266dupC"
                   style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
          </div>
          <div style="margin-bottom:8px">
            <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                   data-fr="Classification ACMG" data-en="ACMG Classification">Classification ACMG</label>
            <select id="cv1_acmg"
                    style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:12px">
              <option value="">— Sélectionner —</option>
              <option value="Pathogène">Pathogène</option>
              <option value="Probablement Pathogène">Probablement Pathogène</option>
              <option value="VUS">VUS (Signification incertaine)</option>
              <option value="Probablement Bénin">Probablement Bénin</option>
              <option value="Bénin">Bénin</option>
            </select>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">PolyPhen-2 (0-1)</label>
              <input type="number" id="cv1_polyphen" min="0" max="1" step="0.01" placeholder="0.00-1.00"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">SIFT (0-1)</label>
              <input type="number" id="cv1_sift" min="0" max="1" step="0.001" placeholder="0.000-1.000"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">CADD phred</label>
              <input type="number" id="cv1_cadd" min="0" max="60" step="0.1" placeholder="0-60"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">Gène</label>
              <input type="text" id="cv1_gene" placeholder="BRCA1"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
          </div>
        </div>

        <!-- Variant 2 -->
        <div style="background:var(--s2);border-radius:9px;padding:14px;border:2px solid var(--tl)">
          <div style="font-size:13px;font-weight:700;color:var(--tl);margin-bottom:10px">
            🧬 <span data-fr="Variant 2" data-en="Variant 2">Variant 2</span>
          </div>

          <div style="margin-bottom:8px">
            <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                   data-fr="HGVS / Nom du variant" data-en="HGVS / Variant name">HGVS / Nom</label>
            <input type="text" id="cv2_hgvs" placeholder="ex: BRCA2 c.9976A>T"
                   style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
          </div>
          <div style="margin-bottom:8px">
            <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px"
                   data-fr="Classification ACMG" data-en="ACMG Classification">Classification ACMG</label>
            <select id="cv2_acmg"
                    style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:12px">
              <option value="">— Sélectionner —</option>
              <option value="Pathogène">Pathogène</option>
              <option value="Probablement Pathogène">Probablement Pathogène</option>
              <option value="VUS">VUS (Signification incertaine)</option>
              <option value="Probablement Bénin">Probablement Bénin</option>
              <option value="Bénin">Bénin</option>
            </select>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">PolyPhen-2 (0-1)</label>
              <input type="number" id="cv2_polyphen" min="0" max="1" step="0.01" placeholder="0.00-1.00"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">SIFT (0-1)</label>
              <input type="number" id="cv2_sift" min="0" max="1" step="0.001" placeholder="0.000-1.000"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">CADD phred</label>
              <input type="number" id="cv2_cadd" min="0" max="60" step="0.1" placeholder="0-60"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
            <div>
              <label style="font-size:11px;color:var(--mu);display:block;margin-bottom:2px">Gène</label>
              <input type="text" id="cv2_gene" placeholder="BRCA2"
                     style="width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:12px">
            </div>
          </div>
        </div>
      </div>

      <!-- Exemples rapides -->
      <div style="margin-bottom:12px">
        <div style="font-size:11px;color:var(--mu);margin-bottom:6px"
             data-fr="Exemples rapides :" data-en="Quick examples:">Exemples rapides :</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn bsm" style="font-size:11px;background:var(--s2)"
                  onclick="cvExample('BRCA1 c.5266dupC','Pathogène',0.998,0.001,35,'BRCA1','BRCA2 c.9976A>T','VUS',0.42,0.18,12,'BRCA2')">
            BRCA1 vs BRCA2
          </button>
          <button class="btn bsm" style="font-size:11px;background:var(--s2)"
                  onclick="cvExample('TP53 R175H','Pathogène',0.999,0.001,45,'TP53','TP53 R248W','Pathogène',0.997,0.002,42,'TP53')">
            TP53 R175H vs R248W
          </button>
          <button class="btn bsm" style="font-size:11px;background:var(--s2)"
                  onclick="cvExample('EGFR L858R','Pathogène',0.985,0.001,38,'EGFR','EGFR T790M','Probablement Pathogène',0.76,0.05,28,'EGFR')">
            EGFR L858R vs T790M
          </button>
        </div>
      </div>

      <button class="btn bp3" style="width:100%" onclick="compareVariants()"
              data-fr="⚖️ Comparer les deux variants" data-en="⚖️ Compare both variants">
        ⚖️ Comparer les deux variants
      </button>

      <div id="compvarResult" style="margin-top:14px"></div>

      <div style="margin-top:12px;font-size:11px;color:var(--mu);padding:8px 10px;border-left:2px solid var(--bd);line-height:1.5"
           data-fr="📚 Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868) · Les scores PolyPhen-2, SIFT et CADD sont des prédicteurs in silico. La classification ACMG finale requiert l'intégration des données cliniques."
           data-en="📚 Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868) · PolyPhen-2, SIFT and CADD scores are in silico predictors. Final ACMG classification requires clinical data integration.">
        📚 Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868) · Scores in silico uniquement — validation clinique requise.
      </div>
    </div>
  </div>

'''

OLD_ABOUT = '  <div id="sec-about" style="display:none">'
if OLD_ABOUT in html:
    html = html.replace(OLD_ABOUT, COMPVAR_SECTION + OLD_ABOUT)
    print("✅ Section comparateur insérée")
else:
    print("❌ Ancre sec-about non trouvée")

# ─────────────────────────────────────────────────────────────
# 4. JavaScript
# ─────────────────────────────────────────────────────────────
COMPVAR_JS = '''
// ══ COMPARATEUR DE VARIANTS ══════════════════════════════════════════════════
function cvExample(h1, acmg1, pp1, sift1, cadd1, g1, h2, acmg2, pp2, sift2, cadd2, g2) {
  document.getElementById('cv1_hgvs').value = h1;
  document.getElementById('cv1_acmg').value = acmg1;
  document.getElementById('cv1_polyphen').value = pp1;
  document.getElementById('cv1_sift').value = sift1;
  document.getElementById('cv1_cadd').value = cadd1;
  document.getElementById('cv1_gene').value = g1;
  document.getElementById('cv2_hgvs').value = h2;
  document.getElementById('cv2_acmg').value = acmg2;
  document.getElementById('cv2_polyphen').value = pp2;
  document.getElementById('cv2_sift').value = sift2;
  document.getElementById('cv2_cadd').value = cadd2;
  document.getElementById('cv2_gene').value = g2;
}

function cvGetVal(id) {
  const v = document.getElementById(id).value;
  return v === '' ? undefined : isNaN(v) ? v : parseFloat(v);
}

async function compareVariants() {
  const v1 = {
    hgvs: document.getElementById('cv1_hgvs').value || 'Variant 1',
    gene: document.getElementById('cv1_gene').value || '',
    acmg_classification: document.getElementById('cv1_acmg').value || '',
    polyphen_score: cvGetVal('cv1_polyphen'),
    sift_score: cvGetVal('cv1_sift'),
    cadd_phred: cvGetVal('cv1_cadd'),
  };
  const v2 = {
    hgvs: document.getElementById('cv2_hgvs').value || 'Variant 2',
    gene: document.getElementById('cv2_gene').value || '',
    acmg_classification: document.getElementById('cv2_acmg').value || '',
    polyphen_score: cvGetVal('cv2_polyphen'),
    sift_score: cvGetVal('cv2_sift'),
    cadd_phred: cvGetVal('cv2_cadd'),
  };

  if (!v1.hgvs && !v2.hgvs) return;

  const res = document.getElementById('compvarResult');
  res.innerHTML = '<div style="color:var(--mu);font-size:13px">⏳ Comparaison en cours…</div>';

  try {
    const r = await fetch('/compare_variants', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({variant1: v1, variant2: v2})
    });
    const d = await r.json();
    if (d.error) { res.innerHTML = `<div style="color:var(--dg)">${d.error}</div>`; return; }

    const v1r = d.variant1;
    const v2r = d.variant2;
    const winner = d.more_pathogenic;

    const acmgCol = {
      'Pathogène': '#dc2626',
      'Probablement Pathogène': '#d97706',
      'VUS': '#0891b2',
      'Probablement Bénin': '#16a34a',
      'Bénin': '#6b7280',
    };

    function scoreBar(score, maxScore=13) {
      const pct = Math.min(100, Math.round(score / maxScore * 100));
      const col = pct >= 70 ? '#dc2626' : pct >= 40 ? '#d97706' : '#16a34a';
      return `<div style="background:var(--bd);border-radius:4px;height:8px;overflow:hidden;margin-top:4px">
        <div style="width:${pct}%;height:100%;background:${col};border-radius:4px;transition:width .5s"></div>
      </div>`;
    }

    function varCard(v, label, borderCol, isWinner) {
      const acmg = v.acmg_classification || '—';
      const col = acmgCol[acmg] || 'var(--mu)';
      return `
        <div style="background:var(--s2);border-radius:9px;padding:14px;border:2px solid ${borderCol};position:relative">
          ${isWinner ? '<div style="position:absolute;top:-10px;right:10px;background:#d97706;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:5px">⚠️ PLUS PATHOGÈNE</div>' : ''}
          <div style="font-size:13px;font-weight:700;color:${borderCol};margin-bottom:10px">${label}</div>
          <div style="font-size:14px;font-weight:700;color:var(--tx);margin-bottom:6px">${v.hgvs}</div>
          ${v.gene ? `<div style="font-size:11px;color:var(--mu);margin-bottom:8px">Gène : <b>${v.gene}</b></div>` : ''}

          <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:11px;color:var(--mu)">Classification ACMG</span>
              <span style="font-size:12px;font-weight:700;color:${col}">${acmg}</span>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:8px">
            <div style="text-align:center;background:var(--bg);border-radius:6px;padding:6px">
              <div style="font-size:16px;font-weight:700;color:var(--tx)">${v.polyphen_score != null ? v.polyphen_score.toFixed(3) : '—'}</div>
              <div style="font-size:9px;color:var(--mu)">PolyPhen-2</div>
            </div>
            <div style="text-align:center;background:var(--bg);border-radius:6px;padding:6px">
              <div style="font-size:16px;font-weight:700;color:var(--tx)">${v.sift_score != null ? v.sift_score.toFixed(3) : '—'}</div>
              <div style="font-size:9px;color:var(--mu)">SIFT</div>
            </div>
            <div style="text-align:center;background:var(--bg);border-radius:6px;padding:6px">
              <div style="font-size:16px;font-weight:700;color:var(--tx)">${v.cadd_phred != null ? v.cadd_phred : '—'}</div>
              <div style="font-size:9px;color:var(--mu)">CADD phred</div>
            </div>
          </div>

          <div>
            <div style="display:flex;justify-content:space-between;font-size:11px">
              <span style="color:var(--mu)">Score composite</span>
              <span style="font-weight:700;color:var(--tx)">${v.composite_score} / 13</span>
            </div>
            ${scoreBar(v.composite_score)}
          </div>
        </div>`;
    }

    const v1Winner = winner === 'Variant 1';
    const v2Winner = winner === 'Variant 2';

    res.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        ${varCard(v1r, '🧬 Variant 1', 'var(--pr)', v1Winner)}
        ${varCard(v2r, '🧬 Variant 2', 'var(--tl)', v2Winner)}
      </div>

      <div style="background:var(--s2);border-radius:9px;padding:14px;border:1px solid var(--bd);margin-bottom:10px">
        <div style="font-size:13px;font-weight:700;color:var(--tx);margin-bottom:6px">🔬 Conclusion comparative</div>
        <div style="font-size:13px;color:var(--tx);line-height:1.6">${d.conclusion}</div>
      </div>

      <div style="font-size:11px;color:var(--mu);background:var(--s2);padding:8px 12px;border-radius:7px;border-left:3px solid var(--wn)">
        ${d.disclaimer}
      </div>`;

  } catch(e) {
    res.innerHTML = `<div style="color:var(--dg);font-size:13px">❌ Erreur : ${e.message}</div>`;
  }
}
// ══ FIN COMPARATEUR ══════════════════════════════════════════════════════════
'''

last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + COMPVAR_JS + html[last_script:]
    print("✅ JavaScript comparateur inséré")

# ─────────────────────────────────────────────────────────────
# 5. Compteur 17 → 18
# ─────────────────────────────────────────────────────────────
html = html.replace(
    'data-fr="🧪 17 modules" data-en="🧪 17 modules">🧪 17 modules',
    'data-fr="🧪 18 modules" data-en="🧪 18 modules">🧪 18 modules'
)
print("✅ Compteur modules : 17 → 18")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: comparateur de variants côte à côte"')
print("  git push origin main")
