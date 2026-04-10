#!/usr/bin/env python3
"""
patch_mobile_responsive.py
Ajoute une interface mobile complète :
- Sidebar hamburger menu sur mobile
- Topbar adaptée mobile
- Grilles responsives
- Boutons et inputs adaptés au touch
- Navigation mobile fluide

Exécuter depuis SenGenoScope/ :
  python3 patch_mobile_responsive.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────
# 1. Remplacer la règle @media existante par un CSS mobile complet
# ─────────────────────────────────────────────────────────────
OLD_MEDIA = '@media(max-width:768px){.sb{display:none;}.ct{padding:10px;}}'

NEW_MEDIA = '''@media(max-width:768px){
  /* ── Layout principal ── */
  .shell{flex-direction:column;}
  .sb{
    position:fixed;top:0;left:-280px;width:280px;height:100vh;
    z-index:1000;transition:left .25s ease;overflow-y:auto;
    box-shadow:4px 0 20px rgba(0,0,0,.3);
  }
  .sb.open{left:0;}
  .ct{padding:8px;margin-left:0!important;}
  .topbar{padding:8px 12px;flex-wrap:nowrap;gap:4px;}
  .tt{font-size:11px!important;flex:1;}
  .tr2{gap:4px;flex-wrap:nowrap;}
  .tr2 .bg2{font-size:9px!important;padding:2px 5px!important;}
  #apiKeyBtn{font-size:9px!important;padding:4px 6px!important;}

  /* ── Overlay sidebar ── */
  .sb-overlay{
    display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;
    background:rgba(0,0,0,.5);z-index:999;
  }
  .sb-overlay.active{display:block;}

  /* ── Bouton hamburger ── */
  .hamburger{
    display:flex!important;flex-direction:column;gap:4px;cursor:pointer;
    padding:6px;border-radius:6px;background:var(--s2);border:1px solid var(--bd);
    flex-shrink:0;
  }
  .hamburger span{
    display:block;width:18px;height:2px;background:var(--tx);
    border-radius:1px;transition:all .2s;
  }

  /* ── Grilles adaptées ── */
  .prs-grid,[class*="grid"]{grid-template-columns:1fr!important;}
  .or2{flex-direction:column;gap:6px;}
  .tg{grid-template-columns:1fr!important;}

  /* ── Cards et sections ── */
  .card{border-radius:8px;margin-bottom:8px;}
  .ch{padding:10px 12px!important;flex-wrap:wrap;gap:6px;}

  /* ── Topbar switcher FR/EN ── */
  #topbar-btn-fr,#topbar-btn-en{font-size:9px!important;padding:3px 6px!important;}

  /* ── Comparateur variants ── */
  #sec-compvar .card > div[style*="grid-template-columns:1fr 1fr"],
  div[style*="grid-template-columns:1fr 1fr"]{
    grid-template-columns:1fr!important;
  }

  /* ── Manchester grille ── */
  #sec-manchester div[style*="grid-template-columns:repeat"]{
    grid-template-columns:1fr!important;
  }

  /* ── Résultats ── */
  .rg{grid-template-columns:repeat(2,1fr)!important;}

  /* ── Inputs et boutons ── */
  input,select,textarea{font-size:16px!important;} /* évite zoom iOS */
  .btn{min-height:38px;}

  /* ── Morpho preview ── */
  #morphoPreview{flex-direction:column!important;}
  #morphoImgBox{width:100%!important;max-width:100%!important;}

  /* ── Cliniciens ── */
  #clinicianCards{grid-template-columns:1fr!important;}
}

/* ── Hamburger caché sur desktop ── */
.hamburger{display:none;}

@media(max-width:480px){
  .tt{display:none;}
  .tr2 .bg2:not(#topbar-btn-fr):not(#topbar-btn-en){display:none;}
  .topbar{padding:6px 8px;}
}'''

if OLD_MEDIA in html:
    html = html.replace(OLD_MEDIA, NEW_MEDIA)
    print("✅ CSS mobile complet ajouté")
else:
    print("❌ @media non trouvé — vérifier")

# ─────────────────────────────────────────────────────────────
# 2. Ajouter le bouton hamburger dans la topbar
# ─────────────────────────────────────────────────────────────
OLD_TOPBAR = '  <div class="topbar">\n    <div class="tt">'
NEW_TOPBAR = '''  <!-- Overlay sidebar mobile -->
  <div class="sb-overlay" id="sbOverlay" onclick="closeSidebar()"></div>

  <div class="topbar">
    <button class="hamburger" id="hamburgerBtn" onclick="toggleSidebar()" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <div class="tt">'''

if OLD_TOPBAR in html:
    html = html.replace(OLD_TOPBAR, NEW_TOPBAR)
    print("✅ Bouton hamburger ajouté dans topbar")
else:
    print("❌ Topbar non trouvée")

# ─────────────────────────────────────────────────────────────
# 3. Ajouter bouton fermeture en haut de la sidebar
# ─────────────────────────────────────────────────────────────
OLD_SIDEBAR_TOP = '  <div class="lg2"><div class="li">🧬</div>'
NEW_SIDEBAR_TOP = '''  <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px 0;min-height:0" class="sb-close-row">
    <button onclick="closeSidebar()" style="display:none;background:none;border:none;cursor:pointer;font-size:20px;color:var(--mu);padding:4px" id="sidebarCloseBtn">✕</button>
  </div>
  <div class="lg2"><div class="li">🧬</div>'''

if OLD_SIDEBAR_TOP in html:
    html = html.replace(OLD_SIDEBAR_TOP, NEW_SIDEBAR_TOP)
    print("✅ Bouton fermeture sidebar ajouté")
else:
    print("❌ Sidebar top non trouvé")

# ─────────────────────────────────────────────────────────────
# 4. JavaScript hamburger
# ─────────────────────────────────────────────────────────────
MOBILE_JS = '''
// ══ MOBILE — SIDEBAR HAMBURGER ═══════════════════════════════════════════════
function toggleSidebar() {
  const sb = document.querySelector('.sb');
  const overlay = document.getElementById('sbOverlay');
  const closeBtn = document.getElementById('sidebarCloseBtn');
  if (sb.classList.contains('open')) {
    closeSidebar();
  } else {
    sb.classList.add('open');
    overlay.classList.add('active');
    if (closeBtn) closeBtn.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }
}

function closeSidebar() {
  const sb = document.querySelector('.sb');
  const overlay = document.getElementById('sbOverlay');
  const closeBtn = document.getElementById('sidebarCloseBtn');
  sb.classList.remove('open');
  overlay.classList.remove('active');
  if (closeBtn) closeBtn.style.display = 'none';
  document.body.style.overflow = '';
}

// Fermer sidebar quand on clique sur un item de nav
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.ni').forEach(btn => {
    btn.addEventListener('click', function() {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
});

// Swipe gauche pour fermer sidebar
(function() {
  let startX = 0;
  document.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, {passive:true});
  document.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - startX;
    if (dx < -60 && document.querySelector('.sb').classList.contains('open')) closeSidebar();
  }, {passive:true});
})();
// ══ FIN MOBILE ═══════════════════════════════════════════════════════════════
'''

last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + MOBILE_JS + html[last_script:]
    print("✅ JavaScript mobile inséré")

with open('templates/index.html', 'w') as f:
    f.write(html)

# Vérifications
with open('templates/index.html', 'r') as f:
    final = f.read()

checks = {
    'CSS @media complet': '@media(max-width:768px)' in final,
    'CSS @media 480px': '@media(max-width:480px)' in final,
    'Hamburger button': 'hamburgerBtn' in final,
    'Overlay sidebar': 'sbOverlay' in final,
    'toggleSidebar JS': 'toggleSidebar' in final,
    'Swipe gesture': 'touchstart' in final,
    'closeSidebar JS': 'closeSidebar' in final,
}
print("\nVÉRIFICATIONS :")
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: interface mobile responsive + hamburger menu + swipe"')
print("  git push origin main")
