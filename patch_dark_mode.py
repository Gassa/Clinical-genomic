#!/usr/bin/env python3
"""
patch_dark_mode.py
Ajoute le toggle mode sombre/clair :
- Variables CSS dark mode complètes
- Bouton toggle dans la topbar
- Préférence sauvegardée dans localStorage
- Respect du prefers-color-scheme système

Exécuter depuis SenGenoScope/ :
  python3 patch_dark_mode.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Ajouter les variables CSS dark mode après :root
# ─────────────────────────────────────────────────────────────
OLD_ROOT = ''':root{
  --bg:#f0f4f8;--sf:#fff;--s2:#f7f9fb;--bd:#dde3ea;
  --pr:#0c6e9c;--prd:#085880;--prl:#dff0f8;
  --tl:#0d9488;--tll:#ccfbf1;--pu:#7c3aed;--pul:#ede9fe;
  --or:#c2410c;--orl:#ffedd5;--dg:#dc2626;--sc:#16a34a;--wn:#d97706;
  --tx:#0f1c2e;--mu:#5a6a7a;
  --mono:'DM Mono',monospace;--sans:'DM Sans',sans-serif;
  --r:10px;--sh:0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);
}'''

NEW_ROOT = ''':root{
  --bg:#f0f4f8;--sf:#fff;--s2:#f7f9fb;--bd:#dde3ea;
  --pr:#0c6e9c;--prd:#085880;--prl:#dff0f8;
  --tl:#0d9488;--tll:#ccfbf1;--pu:#7c3aed;--pul:#ede9fe;
  --or:#c2410c;--orl:#ffedd5;--dg:#dc2626;--sc:#16a34a;--wn:#d97706;
  --tx:#0f1c2e;--mu:#5a6a7a;
  --mono:'DM Mono',monospace;--sans:'DM Sans',sans-serif;
  --r:10px;--sh:0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);
}
[data-theme="dark"]{
  --bg:#0d1117;--sf:#161b22;--s2:#1c2128;--bd:#30363d;
  --pr:#38bdf8;--prd:#0ea5e9;--prl:#0c2d3f;
  --tl:#2dd4bf;--tll:#0d2f2b;--pu:#a78bfa;--pul:#1e1535;
  --or:#fb923c;--orl:#2d1a0e;--dg:#f87171;--sc:#4ade80;--wn:#fbbf24;
  --tx:#e6edf3;--mu:#8b949e;
  --sh:0 1px 3px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.2);
}
@media(prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0d1117;--sf:#161b22;--s2:#1c2128;--bd:#30363d;
    --pr:#38bdf8;--prd:#0ea5e9;--prl:#0c2d3f;
    --tl:#2dd4bf;--tll:#0d2f2b;--pu:#a78bfa;--pul:#1e1535;
    --or:#fb923c;--orl:#2d1a0e;--dg:#f87171;--sc:#4ade80;--wn:#fbbf24;
    --tx:#e6edf3;--mu:#8b949e;
    --sh:0 1px 3px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.2);
  }
}'''

if OLD_ROOT in html:
    html = html.replace(OLD_ROOT, NEW_ROOT)
    print("✅ Variables CSS dark mode ajoutées")
else:
    print("❌ :root non trouvé")

# ─────────────────────────────────────────────────────────────
# 2. Ajouter le bouton toggle dans la topbar (avant les boutons FR/EN)
# ─────────────────────────────────────────────────────────────
OLD_TOPBAR_LANG = '''      <div style="display:flex;gap:4px;margin-left:6px;border-left:1px solid var(--bd);padding-left:8px">
        <button id="topbar-btn-fr" onclick="setLang('fr')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--pr);color:#fff;font-size:11px;font-weight:700;cursor:pointer">🇫🇷 FR</button>
        <button id="topbar-btn-en" onclick="setLang('en')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--mu);font-size:11px;font-weight:700;cursor:pointer">🇬🇧 EN</button>
      </div>'''

NEW_TOPBAR_LANG = '''      <button id="themeToggleBtn" onclick="toggleTheme()"
        style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:13px;cursor:pointer;margin-left:6px"
        title="Toggle dark/light mode">🌙</button>
      <div style="display:flex;gap:4px;margin-left:6px;border-left:1px solid var(--bd);padding-left:8px">
        <button id="topbar-btn-fr" onclick="setLang('fr')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--pr);color:#fff;font-size:11px;font-weight:700;cursor:pointer">🇫🇷 FR</button>
        <button id="topbar-btn-en" onclick="setLang('en')" style="padding:4px 9px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--mu);font-size:11px;font-weight:700;cursor:pointer">🇬🇧 EN</button>
      </div>'''

if OLD_TOPBAR_LANG in html:
    html = html.replace(OLD_TOPBAR_LANG, NEW_TOPBAR_LANG)
    print("✅ Bouton toggle dark/light ajouté dans topbar")
else:
    print("❌ Topbar lang non trouvée")

# ─────────────────────────────────────────────────────────────
# 3. JavaScript toggle theme
# ─────────────────────────────────────────────────────────────
THEME_JS = '''
// ══ THEME DARK / LIGHT ═══════════════════════════════════════════════════════
(function initTheme() {
  const saved = localStorage.getItem('sgs_theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = saved === 'dark' || (!saved && prefersDark);
  if (isDark) {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
  }
  updateThemeBtn(isDark);
})();

function updateThemeBtn(isDark) {
  const btn = document.getElementById('themeToggleBtn');
  if (btn) btn.textContent = isDark ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const isDark = current !== 'dark';
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  localStorage.setItem('sgs_theme', isDark ? 'dark' : 'light');
  updateThemeBtn(isDark);
}
// ══ FIN THEME ════════════════════════════════════════════════════════════════
'''

# Insérer au tout début du script principal (avant les autres fonctions)
old_script_start = 'let _pendingCalls'
if old_script_start in html:
    html = html.replace(old_script_start, THEME_JS + 'let _pendingCalls', 1)
    print("✅ JavaScript theme inséré")
else:
    last_script = html.rfind('</script>')
    html = html[:last_script] + THEME_JS + html[last_script:]
    print("✅ JavaScript theme inséré (fallback)")

# ─────────────────────────────────────────────────────────────
# 4. Transition douce sur body pour le changement de thème
# ─────────────────────────────────────────────────────────────
old_body = 'body{background:var(--bg);color:var(--tx);font-family:var(--sans);font-size:15px;line-height:1.6;}'
new_body = 'body{background:var(--bg);color:var(--tx);font-family:var(--sans);font-size:15px;line-height:1.6;transition:background .2s,color .2s;}'

if old_body in html:
    html = html.replace(old_body, new_body)
    print("✅ Transition douce ajoutée sur body")

with open('templates/index.html', 'w') as f:
    f.write(html)

# Vérifications
with open('templates/index.html', 'r') as f:
    final = f.read()

checks = {
    'Variables dark mode': '[data-theme="dark"]' in final,
    'prefers-color-scheme': 'prefers-color-scheme' in final,
    'Bouton toggle topbar': 'themeToggleBtn' in final,
    'toggleTheme JS': 'function toggleTheme' in final,
    'initTheme auto': 'initTheme' in final,
    'localStorage theme': "sgs_theme" in final,
    'Transition body': 'transition:background' in final,
}
print("\nVÉRIFICATIONS :")
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: mode sombre/clair toggle + respect prefers-color-scheme"')
print("  git push origin main")
