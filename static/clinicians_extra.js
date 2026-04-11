
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
            + '<div style="display:flex;gap:4px">'+ '<button onclick="event.stopPropagation();showPatientDossier(' + p.id + ',&quot;' + p.nom + ' ' + p.prenom + '&quot;)" style="padding:3px 8px;border-radius:6px;border:0.5px solid #0d9488;background:transparent;font-size:11px;cursor:pointer;color:#0d9488">📋</button>'+ '<button onclick="event.stopPropagation();deletePatient(' + p.id + ',this.closest(&quot;[onclick]&quot;))" style="padding:3px 8px;border-radius:6px;border:0.5px solid var(--bd);background:transparent;font-size:11px;cursor:pointer;color:var(--mu)">✕</button></div></div>'
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

// ══ VUE DOSSIER PATIENT COMPLET ══════════════════════════════

async function showPatientDossier(patientId, patientName) {
  const modal = document.getElementById('patientModal');
  if (modal) modal.remove();

  // Afficher loading
  const m = document.createElement('div');
  m.id = 'dossierModal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:var(--bg);border-radius:14px;width:100%;max-width:720px;max-height:90vh;display:flex;flex-direction:column;border:0.5px solid var(--bd);overflow:hidden">'
    + '<div style="padding:16px 20px;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;background:var(--s2)">'
    + '<div style="font-size:15px;font-weight:600">📋 Dossier — ' + patientName + '</div>'
    + '<button onclick="document.getElementById(\'dossierModal\').remove()" style="background:none;border:none;font-size:22px;cursor:pointer;color:var(--mu)">×</button></div>'
    + '<div style="padding:30px;text-align:center;color:var(--mu)">Chargement...</div></div>';
  document.body.appendChild(m);

  try {
    const r = await fetch('/patients/' + patientId);
    const d = await r.json();
    if (!d.success) throw new Error(d.error);
    const p = d.patient;
    const consults = d.consultations || [];

    const CC = {
      oncogenetics:'#0d9488', oncologist:'#7c3aed', pathologist:'#b45309',
      geneticist:'#c2410c', generalist:'#16a34a', internist:'#0284c7',
      hematologist:'#dc2626', radiologist:'#4338ca', gynecologist:'#db2777',
      pediatric_oncologist:'#d97706', rcp_coordinator:'#0891b2'
    };

    const consultRows = consults.length
      ? consults.map(c => {
          const col = CC[c.clinician_id] || '#888';
          const dt = new Date(c.updated_at).toLocaleDateString('fr-FR', {day:'2-digit', month:'short', year:'numeric'});
          return '<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;border:0.5px solid var(--bd);margin-bottom:6px;background:var(--s2);cursor:pointer" onclick="loadConsultation(' + c.id + ');document.getElementById(&quot;dossierModal&quot;).remove()">'
            + '<div style="width:36px;height:36px;border-radius:50%;background:' + col + ';display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:600;flex-shrink:0;text-align:center;line-height:1.2">' + (c.clinician_name || '?').split(' ').pop().slice(0,3).toUpperCase() + '</div>'
            + '<div style="flex:1;min-width:0">'
            + '<div style="font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + (c.title || 'Consultation sans titre') + '</div>'
            + '<div style="font-size:11px;color:var(--mu)">' + c.clinician_name + ' · ' + dt + '</div></div>'
            + '<div style="font-size:11px;color:var(--mu);flex-shrink:0">Voir →</div></div>';
        }).join('')
      : '<div style="text-align:center;padding:20px;color:var(--mu);font-size:13px">Aucune consultation associée à ce patient</div>';

    const infos = [
      p.date_naissance ? '🎂 ' + p.date_naissance : null,
      p.numero_dossier ? '📁 N° ' + p.numero_dossier : null,
      p.diagnostic ? '🩺 ' + p.diagnostic : null,
    ].filter(Boolean).join('&nbsp;&nbsp;·&nbsp;&nbsp;');

    m.innerHTML = '<div style="background:var(--bg);border-radius:14px;width:100%;max-width:720px;max-height:90vh;display:flex;flex-direction:column;border:0.5px solid var(--bd);overflow:hidden">'
      // Header
      + '<div style="padding:16px 20px;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;background:var(--s2)">'
      + '<div style="font-size:15px;font-weight:600">📋 Dossier patient</div>'
      + '<div style="display:flex;gap:8px">'
      + '<button onclick="exportPatientPDF(' + p.id + ',&quot;' + p.nom + ' ' + p.prenom + '&quot;)" style="padding:6px 12px;border-radius:7px;border:1px solid var(--bd);background:var(--sf);font-size:12px;cursor:pointer">📄 Exporter PDF</button>'
      + '<button onclick="document.getElementById(&quot;dossierModal&quot;).remove()" style="background:none;border:none;font-size:22px;cursor:pointer;color:var(--mu)">×</button></div></div>'
      // Patient info card
      + '<div style="padding:16px 20px;border-bottom:1px solid var(--bd)">'
      + '<div style="display:flex;align-items:center;gap:14px">'
      + '<div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#0d9488,#0891b2);display:flex;align-items:center;justify-content:center;color:white;font-size:20px;font-weight:700;flex-shrink:0">' + p.nom[0].toUpperCase() + '</div>'
      + '<div>'
      + '<div style="font-size:18px;font-weight:700">' + p.nom + ' ' + p.prenom + '</div>'
      + '<div style="font-size:12px;color:var(--mu);margin-top:3px">' + (infos || 'Aucune information complémentaire') + '</div>'
      + '</div></div>'
      + (p.notes ? '<div style="margin-top:12px;padding:10px 12px;background:var(--s2);border-radius:8px;border-left:3px solid #0891b2;font-size:12px;color:var(--mu)">' + p.notes + '</div>' : '')
      // Edit button
      + '<div style="margin-top:10px;display:flex;gap:8px">'
      + '<button onclick="editPatient(' + p.id + ')" style="padding:5px 12px;border-radius:7px;border:1px solid var(--bd);background:var(--sf);font-size:11px;cursor:pointer">✏️ Modifier</button>'
      + '<button onclick="selectPatient(' + p.id + ',&quot;' + p.nom + ' ' + p.prenom + '&quot;)" style="padding:5px 12px;border-radius:7px;border:none;background:#0d9488;color:white;font-size:11px;cursor:pointer">👤 Consulter avec ce patient</button>'
      + '</div></div>'
      // Consultations
      + '<div style="padding:16px 20px;flex:1;overflow-y:auto">'
      + '<div style="font-size:13px;font-weight:600;margin-bottom:12px">Consultations (' + consults.length + ')</div>'
      + consultRows
      + '</div></div>';

  } catch(e) {
    m.innerHTML = '<div style="background:var(--bg);border-radius:14px;padding:40px;text-align:center;color:var(--mu)">Erreur: ' + e.message + '</div>';
  }
}

async function exportPatientPDF(patientId, patientName) {
  try {
    const r = await fetch('/patients/' + patientId);
    const d = await r.json();
    if (!d.success) throw new Error(d.error);
    // Générer PDF simple via export consultation PDF pour chaque consultation
    alert('Export PDF dossier complet — ' + d.consultations.length + ' consultation(s)\n(Fonctionnalité en développement)');
  } catch(e) { alert('Erreur: ' + e.message); }
}

function editPatient(pid) {
  alert('Modification patient — fonctionnalité à venir');
}
