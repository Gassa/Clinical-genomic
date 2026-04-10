#!/usr/bin/env python3
"""
patch_arbre_genealogique.py
Module arbre généalogique interactif pour conseil génétique.
Exécuter depuis SenGenoScope/ :
  python3 patch_arbre_genealogique.py
"""

with open('templates/index.html', 'r') as f:
    html = f.read()

# 1. Bouton sidebar
OLD_BTN = '''    <button class="ni" onclick="showSec('compvar',this)"><span class="ni-i">⚖️</span><span data-fr="Comparateur de variants" data-en="Variant Comparator">Comparateur variants</span></button>'''
NEW_BTN = OLD_BTN + '''
    <button class="ni" onclick="showSec('pedigree',this)"><span class="ni-i">🌳</span><span data-fr="Arbre généalogique" data-en="Family Tree">Arbre généalogique</span></button>'''

if OLD_BTN in html:
    html = html.replace(OLD_BTN, NEW_BTN)
    print("✅ Bouton sidebar ajouté")
else:
    print("❌ Bouton sidebar non trouvé")

# 2. showSec
old_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','compvar','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho','rare']"
new_list = "['search','prs','founder','penetrance','tools','ngs','acmg','risk','glcomp','manchester','compvar','pedigree','bookmarks','about','litimport','ai_chat','ai_upload','ai_pharma','clinicians','morpho','rare']"
if old_list in html:
    html = html.replace(old_list, new_list)
    print("✅ 'pedigree' ajouté dans showSec")
else:
    print("❌ Liste showSec non trouvée")

# 3. Section HTML
PEDIGREE_HTML = '''
  <!-- ══ ARBRE GENEALOGIQUE ════════════════════════════════════════════ -->
  <div id="sec-pedigree" style="display:none">
    <div style="padding:14px 16px;border-bottom:1px solid var(--bd)">
      <div style="font-size:15px;font-weight:700;color:var(--tx);margin-bottom:4px">🌳 Arbre généalogique — Conseil génétique interactif</div>
      <div style="font-size:12px;color:var(--mu)">Ajoutez les membres de la famille, indiquez les atteintes et calculez automatiquement le risque génétique.</div>
    </div>
    <div style="padding:14px">

      <!-- Toolbar -->
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center">
        <select id="pedSyndrome" onchange="pedUpdateSyndrome()"
          style="padding:6px 10px;border-radius:6px;border:1px solid var(--bd);background:var(--s2);color:var(--tx);font-size:12px">
          <option value="brca">BRCA1/2 — Sein / Ovaire</option>
          <option value="lynch">Lynch — Colorectal / Endomètre</option>
          <option value="lifraumeni">Li-Fraumeni — TP53</option>
          <option value="palb2">PALB2 — Cancer du sein</option>
        </select>
        <button class="btn bsm" style="font-size:11px" onclick="pedReset()">🔄 Reset</button>
        <button class="btn bsm bp3" style="font-size:11px" onclick="pedExport()">📄 Export SVG</button>
        <button class="btn bsm" style="font-size:11px;background:var(--s2);color:var(--mu)" onclick="pedToManchester()">🎗️ → Manchester</button>
      </div>

      <!-- Légende -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px;padding:7px 12px;background:var(--s2);border-radius:7px;font-size:11px;color:var(--mu)">
        <span>⭕ Femme non atteinte</span>
        <span>⬜ Homme non atteint</span>
        <span style="color:#dc2626">🔴 Atteint(e)</span>
        <span style="color:#0891b2">🔵 Porteur</span>
        <span style="color:#6b7280">⬛ Décédé</span>
        <span>· Clic = changer statut · Clic droit = supprimer</span>
      </div>

      <!-- Canvas -->
      <div style="background:var(--sf);border:1px solid var(--bd);border-radius:9px;overflow:hidden;margin-bottom:12px;position:relative">
        <svg id="pedCanvas" width="100%" height="500" style="cursor:default;display:block"
             onclick="pedCanvasClick(event)"
             oncontextmenu="pedCanvasRightClick(event);return false">
          <defs>
            <pattern id="pgrid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="var(--bd)" stroke-width="0.3" opacity="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#pgrid)"/>
          <g id="pedLines"></g>
          <g id="pedNodes"></g>
        </svg>
        <div id="pedHint" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;pointer-events:none">
          <div style="font-size:28px">🌳</div>
          <div style="font-size:13px;font-weight:700;color:var(--tx);margin-top:6px">Cliquez pour ajouter un membre</div>
          <div style="font-size:11px;color:var(--mu);margin-top:3px">Utilisez les boutons rapides ci-dessous</div>
        </div>
      </div>

      <!-- Boutons ajout rapide -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:12px">
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Grand-mère P','F',0)"
                data-fr="+ Grand-mère Pat." data-en="+ Paternal Grandma">+ Grand-mère Pat.</button>
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Grand-père P','M',0)"
                data-fr="+ Grand-père Pat." data-en="+ Paternal Grandpa">+ Grand-père Pat.</button>
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Mère','F',1)"
                data-fr="+ Mère" data-en="+ Mother">+ Mère</button>
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Père','M',1)"
                data-fr="+ Père" data-en="+ Father">+ Père</button>
        <button class="btn bsm bp3" onclick="pedQuickAdd('Patient','F',2)"
                data-fr="+ Patiente (cas index)" data-en="+ Patient (index case)">+ Patiente (cas index)</button>
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Frère','M',2)"
                data-fr="+ Frère/Sœur" data-en="+ Sibling">+ Frère/Sœur</button>
        <button class="btn bsm" style="background:var(--s2)" onclick="pedQuickAdd('Enfant','F',3)"
                data-fr="+ Enfant" data-en="+ Child">+ Enfant</button>
        <button class="btn bsm" style="background:var(--s2);color:var(--or)" onclick="pedQuickAddAffected()"
                data-fr="+ Membre ATTEINT" data-en="+ AFFECTED member">+ Membre ATTEINT</button>
      </div>

      <!-- Résultat risque -->
      <div id="pedRiskResult"></div>

      <div style="font-size:11px;color:var(--mu);padding:6px 10px;border-left:2px solid var(--bd);line-height:1.5;margin-top:8px">
        🔒 Données stockées localement dans votre navigateur uniquement — aucune transmission.
      </div>
    </div>
  </div>

'''

OLD_ABOUT = '  <div id="sec-about" style="display:none">'
if OLD_ABOUT in html:
    html = html.replace(OLD_ABOUT, PEDIGREE_HTML + OLD_ABOUT)
    print("✅ Section HTML insérée")
else:
    print("❌ Ancre sec-about non trouvée")

# 4. JavaScript
PED_JS = r'''
// ══ ARBRE GENEALOGIQUE ═══════════════════════════════════════════════════════
let pedMembers = [];
let pedSyndr = 'brca';
const PED_R = 22;
const PED_GEN_Y = {0:70, 1:190, 2:310, 3:420};
const PED_COLS = {
  unaffected:{fill:'transparent',stroke:'currentColor'},
  affected:{fill:'#dc2626',stroke:'#dc2626'},
  carrier:{fill:'transparent',stroke:'currentColor',dot:true},
  deceased:{fill:'#9ca3af',stroke:'#9ca3af'}
};

function pedUpdateSyndrome(){
  pedSyndr = document.getElementById('pedSyndrome').value;
  pedCalcRisk();
}

function pedCanvasClick(e){
  // Clic vide = afficher dialogue ajout simplifié
  const svg = document.getElementById('pedCanvas');
  const rect = svg.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const hit = pedMembers.find(m=>{const dx=m.x-x,dy=m.y-y;return Math.sqrt(dx*dx+dy*dy)<PED_R+6;});
  if(hit){ pedCycleStatus(hit); return; }
  // Clic sur zone vide → détecter génération selon Y
  const gen = y < 130 ? 0 : y < 250 ? 1 : y < 370 ? 2 : 3;
  const name = prompt('Prénom du membre :', '');
  if(name === null) return;
  const sexStr = prompt('Sexe (F/M) :', 'F');
  const sex = sexStr === null ? 'F' : sexStr.toUpperCase() === 'M' ? 'M' : 'F';
  pedAddM(name||'?', sex, gen, 'unaffected', '');
}

function pedQuickAdd(name, sex, gen){
  pedAddM(name, sex, gen, 'unaffected', '');
}

function pedQuickAddAffected(){
  const name = prompt('Prénom du membre atteint :', '');
  if(name === null) return;
  const sexStr = prompt('Sexe (F/M) :', 'F');
  const sex = !sexStr || sexStr.toUpperCase() !== 'M' ? 'F' : 'M';
  const cancer = prompt('Type de cancer et âge (ex: sein 45) :', '');
  const gen = parseInt(prompt('Génération (0=grands-parents, 1=parents, 2=patient, 3=enfants):', '1')||'1');
  pedAddM(name, sex, gen, 'affected', cancer||'');
}

function pedAddM(name, sex, gen, status, age){
  document.getElementById('pedHint').style.display = 'none';
  const sameGen = pedMembers.filter(m=>m.gen===gen);
  const x = Math.min(80 + sameGen.length * 75, 680);
  const y = PED_GEN_Y[gen] || 310;
  pedMembers.push({id:Date.now(), name, sex, gen, status, age, x, y});
  pedRender();
  pedCalcRisk();
}

function pedCycleStatus(m){
  const cycle = ['unaffected','affected','carrier','deceased'];
  m.status = cycle[(cycle.indexOf(m.status)+1)%cycle.length];
  pedRender();
  pedCalcRisk();
}

function pedRender(){
  const lG = document.getElementById('pedLines');
  const nG = document.getElementById('pedNodes');
  lG.innerHTML = ''; nG.innerHTML = '';
  if(!pedMembers.length) return;

  // Lignes entre générations
  const byGen = {};
  pedMembers.forEach(m=>{if(!byGen[m.gen])byGen[m.gen]=[];byGen[m.gen].push(m);});
  const gens = Object.keys(byGen).map(Number).sort();
  gens.forEach(g=>{
    const ms = byGen[g];
    if(ms.length>=2){
      ms.slice(0,-1).forEach((m,i)=>{
        const n=ms[i+1];
        const ln=document.createElementNS('http://www.w3.org/2000/svg','line');
        ln.setAttribute('x1',m.x);ln.setAttribute('y1',m.y);
        ln.setAttribute('x2',n.x);ln.setAttribute('y2',n.y);
        ln.setAttribute('stroke','var(--mu)');ln.setAttribute('stroke-width','1.2');
        ln.setAttribute('stroke-dasharray','5,3');lG.appendChild(ln);
      });
    }
  });
  for(let i=0;i<gens.length-1;i++){
    const pg=byGen[gens[i]],cg=byGen[gens[i+1]];
    if(pg&&cg){
      const pmx=pg.reduce((s,m)=>s+m.x,0)/pg.length;
      const cmx=cg.reduce((s,m)=>s+m.x,0)/cg.length;
      const py=pg[0].y,cy=cg[0].y,my=(py+cy)/2;
      [[pmx,py+PED_R,pmx,my],[pmx,my,cmx,my],[cmx,my,cmx,cy-PED_R]].forEach(([x1,y1,x2,y2])=>{
        const ln=document.createElementNS('http://www.w3.org/2000/svg','line');
        ln.setAttribute('x1',x1);ln.setAttribute('y1',y1);ln.setAttribute('x2',x2);ln.setAttribute('y2',y2);
        ln.setAttribute('stroke','var(--tx)');ln.setAttribute('stroke-width','1.2');lG.appendChild(ln);
      });
    }
  }

  // Noeuds
  pedMembers.forEach(m=>{
    const c=PED_COLS[m.status]||PED_COLS.unaffected;
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    g.setAttribute('cursor','pointer');
    g.setAttribute('transform',`translate(${m.x},${m.y})`);
    g.onclick=e=>{e.stopPropagation();pedCycleStatus(m);};
    g.oncontextmenu=e=>{e.preventDefault();e.stopPropagation();if(confirm('Supprimer '+m.name+' ?')){pedMembers=pedMembers.filter(x=>x.id!==m.id);pedRender();pedCalcRisk();}};

    if(m.sex==='F'){
      const el=document.createElementNS('http://www.w3.org/2000/svg','circle');
      el.setAttribute('cx','0');el.setAttribute('cy','0');el.setAttribute('r',PED_R);
      el.setAttribute('fill',c.fill);el.setAttribute('stroke',c.stroke==='currentColor'?'var(--tx)':c.stroke);el.setAttribute('stroke-width','2');
      g.appendChild(el);
    } else {
      const el=document.createElementNS('http://www.w3.org/2000/svg','rect');
      el.setAttribute('x',-PED_R);el.setAttribute('y',-PED_R);el.setAttribute('width',PED_R*2);el.setAttribute('height',PED_R*2);
      el.setAttribute('fill',c.fill);el.setAttribute('stroke',c.stroke==='currentColor'?'var(--tx)':c.stroke);el.setAttribute('stroke-width','2');
      g.appendChild(el);
    }
    if(m.status==='carrier'){
      const d=document.createElementNS('http://www.w3.org/2000/svg','circle');
      d.setAttribute('cx','0');d.setAttribute('cy','0');d.setAttribute('r','8');d.setAttribute('fill','#0891b2');g.appendChild(d);
    }
    if(m.status==='deceased'){
      const ln=document.createElementNS('http://www.w3.org/2000/svg','line');
      ln.setAttribute('x1',-(PED_R+6));ln.setAttribute('y1',PED_R+6);ln.setAttribute('x2',PED_R+6);ln.setAttribute('y2',-(PED_R+6));
      ln.setAttribute('stroke','var(--tx)');ln.setAttribute('stroke-width','1.5');g.appendChild(ln);
    }
    const t=document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x','0');t.setAttribute('y',PED_R+13);t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','10');t.setAttribute('fill','var(--tx)');t.textContent=m.name;g.appendChild(t);
    if(m.age){
      const ta=document.createElementNS('http://www.w3.org/2000/svg','text');
      ta.setAttribute('x','0');ta.setAttribute('y',PED_R+23);ta.setAttribute('text-anchor','middle');
      ta.setAttribute('font-size','9');ta.setAttribute('fill','#dc2626');ta.textContent=m.age;g.appendChild(ta);
    }
    nG.appendChild(g);
  });
}

function pedCalcRisk(){
  const affected=pedMembers.filter(m=>m.status==='affected');
  const res=document.getElementById('pedRiskResult');
  if(!affected.length){res.innerHTML='';return;}
  let score=0,details=[];
  affected.forEach(m=>{
    const age=parseInt(m.age)||50;
    const info=(m.age||'').toLowerCase();
    if(pedSyndr==='brca'||pedSyndr==='palb2'){
      if(info.includes('sein')||info.includes('breast')){
        const pts=age<40?6:age<50?4:age<60?3:2;
        score+=pts;details.push(`${m.name} sein ${age}ans (+${pts})`);
      }
      if(info.includes('ovaire')||info.includes('ovary')){score+=5;details.push(`${m.name} ovaire (+5)`);}
      if(m.sex==='M'&&(info.includes('sein')||info.includes('breast'))){score+=6;details.push(`${m.name} homme (+6)`);}
      if(info.includes('pancréas')||info.includes('pancreas')){score+=2;details.push(`${m.name} pancréas (+2)`);}
    } else if(pedSyndr==='lynch'){
      if(info.includes('colon')||info.includes('rectal')||info.includes('colorectal')){
        const pts=age<50?5:3;score+=pts;details.push(`${m.name} colorectal (+${pts})`);
      }
      if(info.includes('endomètre')||info.includes('endometr')){score+=4;details.push(`${m.name} endomètre (+4)`);}
    } else if(pedSyndr==='lifraumeni'){
      const pts=m.gen===2?8:5;score+=pts;details.push(`${m.name} Li-Fraumeni (+${pts})`);
    }
  });
  const lvl=score>=15?'very_high':score>=10?'high':score>=5?'moderate':'low';
  const cols={very_high:'#dc2626',high:'#d97706',moderate:'#0891b2',low:'#16a34a'};
  const bgs={very_high:'#fef2f2',high:'#fffbeb',moderate:'#e0f2fe',low:'#f0fdf4'};
  const lbls={very_high:'Très élevé — Test génétique fortement recommandé',high:'Élevé — Test génétique recommandé (Manchester ≥10)',moderate:'Modéré — Consultation oncogénétique conseillée',low:'Faible — Surveillance standard'};
  res.innerHTML=`<div style="background:${bgs[lvl]};border:1.5px solid ${cols[lvl]};border-radius:9px;padding:12px 14px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
      <div style="text-align:center"><div style="font-size:30px;font-weight:800;color:${cols[lvl]}">${score}</div><div style="font-size:10px;color:var(--mu)">Score</div></div>
      <div><div style="font-size:13px;font-weight:700;color:${cols[lvl]}">${lbls[lvl]}</div>
      <div style="font-size:11px;color:var(--mu);margin-top:2px">${affected.length} membre(s) atteint(s) · ${pedMembers.length} au total</div></div>
    </div>
    ${details.length?`<div style="font-size:11px;color:var(--mu)">${details.join(' · ')}</div>`:''}
  </div>`;
}

function pedReset(){pedMembers=[];pedRender();document.getElementById('pedRiskResult').innerHTML='';document.getElementById('pedHint').style.display='block';}

function pedExport(){
  const svg=document.getElementById('pedCanvas');
  const s=new XMLSerializer().serializeToString(svg);
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{type:'image/svg+xml'}));
  a.download='arbre_genealogique_'+Date.now()+'.svg';a.click();
}

function pedToManchester(){
  showSec('manchester',document.querySelector('[onclick*="manchester"]'));
  pedMembers.filter(m=>m.status==='affected').forEach(m=>{
    const age=parseInt(m.age)||0;const info=(m.age||'').toLowerCase();
    const bump=id=>{const el=document.getElementById(id);if(el)el.value=Math.min((parseInt(el.value)||0)+1,5);};
    if(info.includes('sein')||info.includes('breast')){
      if(age<40)bump('m_breast_under40');else if(age<50)bump('m_breast_40_49');else if(age<60)bump('m_breast_50_59');else bump('m_breast_60_plus');
    }
    if(info.includes('ovaire')||info.includes('ovary'))bump('m_ovary_any_age');
  });
}

function pedCanvasRightClick(e){
  const svg=document.getElementById('pedCanvas');const rect=svg.getBoundingClientRect();
  const x=e.clientX-rect.left,y=e.clientY-rect.top;
  const hit=pedMembers.find(m=>{const dx=m.x-x,dy=m.y-y;return Math.sqrt(dx*dx+dy*dy)<PED_R+6;});
  if(hit&&confirm('Supprimer "'+hit.name+'" ?')){pedMembers=pedMembers.filter(m=>m.id!==hit.id);pedRender();pedCalcRisk();}
}
// ══ FIN ARBRE ════════════════════════════════════════════════════════════════
'''

last_script = html.rfind('</script>')
if last_script > 0:
    html = html[:last_script] + PED_JS + html[last_script:]
    print("✅ JavaScript inséré")

# initRareTumors + pedigree dans showSec
old_init = "  if(name==='rare')initRareTumors();"
new_init = "  if(name==='rare')initRareTumors();\n  if(name==='pedigree'){if(pedMembers.length)pedRender();}"
if old_init in html:
    html = html.replace(old_init, new_init)
    print("✅ init pedigree dans showSec")

# Compteur 19 → 20
html = html.replace(
    'data-fr="🧪 19 modules" data-en="🧪 19 modules">🧪 19 modules',
    'data-fr="🧪 20 modules" data-en="🧪 20 modules">🧪 20 modules'
)
print("✅ Compteur : 19 → 20 modules")

with open('templates/index.html', 'w') as f:
    f.write(html)

print("\n" + "="*55)
print("COMMANDES SUIVANTES :")
print("  git add templates/index.html")
print('  git commit -m "feat: arbre généalogique interactif + calcul risque + export SVG"')
print("  git push origin main")
