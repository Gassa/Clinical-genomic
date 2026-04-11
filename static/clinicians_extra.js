
// ══ DOSSIERS PATIENTS ══════════════════════════════════════════

let currentPatient = null;

function showPatientSelector() {
  fetch('/patients/list')
    .then(r => r.json())
    .then(d => {
      const list = d.patients || [];
      const m = document.createElement('div');
      m.id = 'patientModal';
      m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
      const rows = list.length
        ? list.map(p =>
            '<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;border:0.5px solid var(--bd);margin-bottom:6px;background:var(--s2);cursor:pointer" onclick="selectPatient(' + p.id + ',&quot;' + p.nom + ' ' + p.prenom + '&quot;)">'
            + '<div style="width:32px;height:32px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;color:white;font-size:13px;font-weight:600;flex-shrink:0">' + p.nom[0].toUpperCase() + '</div>'
            + '<div style="flex:1"><div style="font-size:13px;font-weight:500">' + p.nom + ' ' + p.prenom + '</div>'
            + '<div style="font-size:11px;color:var(--mu)">' + (p.numero_dossier ? 'N° ' + p.numero_dossier + ' · ' : '') + (p.diagnostic || 'Aucun diagnostic') + '</div></div>'
            + '<button onclick="event.stopPropagation();deletePatient(' + p.id + ',this.closest(&quot;[onclick]&quot;))" style="padding:3px 8px;border-radius:6px;border:0.5px solid var(--bd);background:transparent;font-size:11px;cursor:pointer;color:var(--mu)">✕</button></div>'
          ).join('')
        : '<div style="text-align:center;padding:30px;color:var(--mu)">Aucun patient — créez-en un ci-dessous</div>';

      m.innerHTML = '<div style="background:var(--bg);border-radius:14px;width:100%;max-width:540px;max-height:85vh;display:flex;flex-direction:column;gap:0;border:0.5px solid var(--bd);overflow:hidden">'
        + '<div style="padding:16px 20px;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;background:var(--s2)">'
        + '<div style="font-size:15px;font-weight:600">👤 Dossiers patients</div>'
        + '<button onclick="document.getElementById(&quot;patientModal&quot;).remove()" style="background:none;border:none;font-size:20px;cursor:pointer">×</button></div>'
        + '<div style="overflow-y:auto;padding:16px;flex:1">' + rows + '</div>'
        + '<div style="padding:16px;border-top:1px solid var(--bd);background:var(--s2)">'
        + '<div style="font-size:12px;font-weight:500;color:var(--mu);margin-bottom:10px;text-transform:uppercase">Nouveau patient</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">'
        + '<input id="newPatNom" placeholder="Nom *" style="padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px">'
        + '<input id="newPatPrenom" placeholder="Prénom" style="padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px">'
        + '<input id="newPatDossier" placeholder="N° dossier" style="padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px">'
        + '<input id="newPatDob" placeholder="Date naissance" type="date" style="padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px">'
        + '</div>'
        + '<input id="newPatDiag" placeholder="Diagnostic principal" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-bottom:8px">'
        + '<button onclick="createPatient()" style="width:100%;padding:9px;border-radius:8px;border:none;background:#0d9488;color:white;font-size:13px;font-weight:500;cursor:pointer">+ Créer le patient</button>'
        + '</div></div>';
      document.body.appendChild(m);
    })
    .catch(e => alert('Erreur: ' + e.message));
}

function selectPatient(id, name) {
  currentPatient = {id: id, name: name};
  const modal = document.getElementById('patientModal');
  if (modal) modal.remove();
  // Afficher badge patient actif
  let badge = document.getElementById('activePatientBadge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'activePatientBadge';
    badge.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:8px;background:#E1F5EE;border:1px solid #9FE1CB;font-size:12px;font-weight:500;color:#085041;cursor:pointer;margin-bottom:8px';
    badge.onclick = showPatientSelector;
    const zone = document.getElementById('consultationPanel') || document.getElementById('clinicianMessages');
    if (zone && zone.parentNode) zone.parentNode.insertBefore(badge, zone);
  }
  badge.innerHTML = '👤 <span>' + name + '</span> <span style="opacity:.5;font-size:10px">· changer</span>';
  // Associer la consultation courante si elle existe
  if (currentConsultationId) {
    fetch('/patients/attach', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({consultation_id: currentConsultationId, patient_id: id})
    }).catch(() => {});
  }
}

async function createPatient() {
  const nom = (document.getElementById('newPatNom') || {value:''}).value.trim();
  if (!nom) { alert('Le nom est requis'); return; }
  const data = {
    nom: nom,
    prenom: (document.getElementById('newPatPrenom') || {value:''}).value,
    date_naissance: (document.getElementById('newPatDob') || {value:''}).value,
    numero_dossier: (document.getElementById('newPatDossier') || {value:''}).value,
    diagnostic: (document.getElementById('newPatDiag') || {value:''}).value,
  };
  try {
    const r = await fetch('/patients/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const res = await r.json();
    if (!res.success) throw new Error(res.error);
    selectPatient(res.id, nom + ' ' + data.prenom);
  } catch(e) { alert('Erreur: ' + e.message); }
}

async function deletePatient(id, el) {
  if (!confirm('Supprimer ce patient et dissocier ses consultations ?')) return;
  await fetch('/patients/' + id, {method: 'DELETE'});
  if (el) el.remove();
}
