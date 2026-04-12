
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
      + '<button onclick="exportPatientPDFFull(' + p.id + ',&quot;' + p.nom + ' ' + p.prenom + '&quot;)" style="padding:6px 12px;border-radius:7px;border:1px solid var(--bd);background:var(--sf);font-size:12px;cursor:pointer">📄 Exporter PDF</button>'
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
      + '<button onclick="editPatientForm(' + p.id + ')" style="padding:5px 12px;border-radius:7px;border:1px solid var(--bd);background:var(--sf);font-size:11px;cursor:pointer">✏️ Modifier</button>'
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

// ══ MODIFICATION PATIENT ══════════════════════════════════════

async function editPatientForm(pid) {
  try {
    const r = await fetch('/patients/' + pid);
    const d = await r.json();
    if (!d.success) throw new Error(d.error);
    const p = d.patient;
    const existing = document.getElementById('dossierModal');
    if (existing) existing.remove();
    const m = document.createElement('div');
    m.id = 'editPatientModal';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    m.innerHTML = '<div style="background:var(--bg);border-radius:14px;width:100%;max-width:480px;border:0.5px solid var(--bd);overflow:hidden">'
      + '<div style="padding:14px 20px;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;background:var(--s2)">'
      + '<div style="font-size:14px;font-weight:600">✏️ Modifier le patient</div>'
      + '<button onclick="document.getElementById(\'editPatientModal\').remove()" style="background:none;border:none;font-size:20px;cursor:pointer">×</button></div>'
      + '<div style="padding:20px;display:flex;flex-direction:column;gap:10px">'
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">Nom *</label><input id="epNom" value="' + (p.nom||'') + '" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px"></div>'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">Prénom</label><input id="epPrenom" value="' + (p.prenom||'') + '" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px"></div>'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">N° dossier</label><input id="epDossier" value="' + (p.numero_dossier||'') + '" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px"></div>'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">Date naissance</label><input id="epDob" type="date" value="' + (p.date_naissance||'') + '" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px"></div>'
      + '</div>'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">Diagnostic principal</label><input id="epDiag" value="' + (p.diagnostic||'') + '" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px"></div>'
      + '<div><label style="font-size:11px;color:var(--mu);font-weight:500">Notes cliniques</label><textarea id="epNotes" rows="3" style="width:100%;padding:7px 10px;border:1px solid var(--bd);border-radius:7px;background:var(--sf);color:var(--tx);font-size:13px;box-sizing:border-box;margin-top:3px;resize:vertical">' + (p.notes||'') + '</textarea></div>'
      + '<button onclick="savePatientEdit(' + pid + ')" style="padding:10px;border-radius:8px;border:none;background:#0d9488;color:white;font-size:13px;font-weight:500;cursor:pointer">💾 Sauvegarder</button>'
      + '</div></div>';
    document.body.appendChild(m);
  } catch(e) { alert('Erreur: ' + e.message); }
}

async function savePatientEdit(pid) {
  const data = {
    nom: (document.getElementById('epNom')||{value:''}).value.trim(),
    prenom: (document.getElementById('epPrenom')||{value:''}).value,
    date_naissance: (document.getElementById('epDob')||{value:''}).value,
    numero_dossier: (document.getElementById('epDossier')||{value:''}).value,
    diagnostic: (document.getElementById('epDiag')||{value:''}).value,
    notes: (document.getElementById('epNotes')||{value:''}).value,
  };
  if (!data.nom) { alert('Le nom est requis'); return; }
  try {
    const r = await fetch('/patients/' + pid, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const res = await r.json();
    if (!res.success) throw new Error(res.error);
    const m = document.getElementById('editPatientModal');
    if (m) m.remove();
    // Rafraîchir le badge si actif
    if (currentPatient && currentPatient.id === pid) {
      const badge = document.getElementById('activePatientBadge');
      if (badge) badge.querySelector('span').textContent = data.nom + ' ' + data.prenom;
    }
    alert('Patient mis à jour');
  } catch(e) { alert('Erreur: ' + e.message); }
}

// ══ EXPORT PDF DOSSIER COMPLET ══════════════════════════════

async function exportPatientPDFFull(patientId, patientName) {
  try {
    const btn = event.target;
    btn.textContent = '...';
    btn.disabled = true;
    const r = await fetch('/patients/' + patientId + '/export_pdf');
    if (!r.ok) { const e = await r.json(); throw new Error(e.error || 'Erreur'); }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dossier_' + (patientName||'patient').replace(/\s/g,'_') + '.pdf';
    a.click();
    URL.revokeObjectURL(url);
    btn.textContent = '📄 Exporter PDF';
    btn.disabled = false;
  } catch(e) {
    alert('Erreur export: ' + e.message);
    if (event.target) { event.target.textContent = '📄 Exporter PDF'; event.target.disabled = false; }
  }
}

function filterClinicians() {
  var inp = document.getElementById('clinicianSearch');
  var q = inp ? inp.value.toLowerCase() : '';
  var all = window._allClinicians || [];
  var grid = document.getElementById('clinicianCards');
  if (!grid) return;
  if (!all.length && q) { setTimeout(filterClinicians, 500); return; }
  if (!q) { if (all.length) renderClinicianCards(all); return; }
  var f = all.filter(function(c) {
    return c.name.toLowerCase().includes(q)
      || (c.specialty || '').toLowerCase().includes(q)
      || (c.description || '').toLowerCase().includes(q)
      || (c.id || '').toLowerCase().includes(q);
  });
  if (!f.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--mu)">Aucun résultat pour « ' + q + ' »</div>';
    return;
  }
  renderClinicianCards(f);
}

function clearClinicianFilter() {
  var s = document.getElementById('clinicianSearch');
  if (s) s.value = '';
  filterClinicians();
}

// ══ RETRY AUTO COLD START ══════════════════════════════════════
(function() {
  var originalFetch = window.fetch;
  var retryToast = null;

  function showRetryToast(seconds, onRetry) {
    if (retryToast) retryToast.remove();
    retryToast = document.createElement('div');
    retryToast.id = 'retryToast';
    retryToast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#0f172a;color:white;border-radius:12px;padding:14px 20px;z-index:99999;display:flex;align-items:center;gap:14px;box-shadow:0 8px 32px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);min-width:300px';
    var counter = seconds;
    retryToast.innerHTML = '<div style="width:36px;height:36px;border-radius:50%;border:3px solid rgba(255,255,255,0.2);border-top-color:#0d9488;animation:spin 1s linear infinite;flex-shrink:0"></div>'
      + '<div style="flex:1"><div style="font-size:13px;font-weight:500;margin-bottom:2px">Serveur en cours de démarrage...</div>'
      + '<div style="font-size:12px;color:rgba(255,255,255,0.6)" id="retryCountdown">Reconnexion dans ' + counter + 's</div></div>'
      + '<button onclick="document.getElementById(\'retryToast\').remove()" style="background:rgba(255,255,255,0.1);border:none;color:white;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:11px">X</button>';
    if (!document.getElementById('retrySpinStyle')) {
      var st = document.createElement('style');
      st.id = 'retrySpinStyle';
      st.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
      document.head.appendChild(st);
    }
    document.body.appendChild(retryToast);
    var interval = setInterval(function() {
      counter--;
      var cd = document.getElementById('retryCountdown');
      if (cd) cd.textContent = counter > 0 ? 'Reconnexion dans ' + counter + 's' : 'Connexion...';
      if (counter <= 0) {
        clearInterval(interval);
        if (retryToast) { retryToast.remove(); retryToast = null; }
        onRetry();
      }
    }, 1000);
  }

  window.fetch = function(url, options) {
    return originalFetch(url, options).then(function(response) {
      if (retryToast) { retryToast.remove(); retryToast = null; }
      return response;
    }).catch(function(err) {
      var isNetworkError = err.name === 'TypeError' || err.name === 'NetworkError' || err.message === 'Failed to fetch';
      var isApiCall = typeof url === 'string' && (url.startsWith('/') || url.includes('clinical-genomic'));
      if (isNetworkError && isApiCall) {
        return new Promise(function(resolve, reject) {
          showRetryToast(35, function() {
            originalFetch(url, options).then(function(r) {
              resolve(r);
            }).catch(function(e) {
              reject(e);
            });
          });
        });
      }
      throw err;
    });
  };
})();

// ══ ANALYSE NGS IA ══════════════════════════════════════════
var _lastNGSResult = null;

async function analyzeNGSAI() {
  var text = (document.getElementById('ngsAIInput') || {value:''}).value.trim();
  var context = (document.getElementById('ngsContext') || {value:''}).value.trim();
  if (!text) { alert('Collez un rapport NGS dans la zone de texte'); return; }
  var resDiv = document.getElementById('ngsAIResult');
  if (!resDiv) return;
  resDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--mu)"><div style="display:inline-block;width:24px;height:24px;border:3px solid var(--bd);border-top-color:#0d9488;border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:8px;font-size:13px">Analyse IA en cours...</div></div>';

  try {
    var userKey = localStorage.getItem('sgs_api_key') || '';
    var r = await fetch('/interpret_ngs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-User-Api-Key': userKey},
      body: JSON.stringify({text: text, context: context, user_api_key: userKey})
    });
    var d = await r.json();
    if (!d.success) throw new Error(d.error);
    _lastNGSResult = d.result;
    renderNGSResult(d.result);
    var btn = document.getElementById('ngsExportBtn');
    if (btn) btn.style.display = 'inline-block';
  } catch(e) {
    resDiv.innerHTML = '<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px;font-size:13px">Erreur: ' + e.message + '</div>';
  }
}

function renderNGSResult(res) {
  var resDiv = document.getElementById('ngsAIResult');
  if (!resDiv || !res) return;

  var ACMG_COL = {
    'Pathogene':'#dc2626', 'Probablement pathogene':'#f97316',
    'VUS':'#f59e0b', 'Probablement benin':'#84cc16', 'Benin':'#22c55e',
    'Pathogène':'#dc2626', 'Probablement pathogène':'#f97316',
    'Probablement bénin':'#84cc16'
  };

  var html = '<div style="display:flex;flex-direction:column;gap:12px">';

  if (res.urgent) {
    html += '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;color:#dc2626;font-weight:500;font-size:13px">⚠️ ALERTE URGENTE: ' + (res.urgent_reason || '') + '</div>';
  }

  if (res.summary) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px;font-size:13px;line-height:1.6"><strong>Résumé clinique:</strong> ' + res.summary + '</div>';
  }

  var variants = res.variants || [];
  if (variants.length) {
    html += '<div><div style="font-size:12px;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Variants (' + variants.length + ')</div>';
    variants.forEach(function(v) {
      var acmg = v.acmg_class || 'VUS';
      var col = ACMG_COL[acmg] || '#f59e0b';
      html += '<div style="border:1px solid var(--bd);border-radius:8px;padding:12px;margin-bottom:8px;border-left:4px solid ' + col + '">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">';
      html += '<div><span style="font-size:15px;font-weight:700;color:var(--tx)">' + (v.gene || '') + '</span>';
      html += '<span style="font-size:12px;color:var(--mu);margin-left:8px">' + (v.variant || '') + '</span></div>';
      html += '<span style="font-size:11px;font-weight:600;padding:3px 8px;border-radius:99px;background:' + col + '20;color:' + col + '">' + acmg + '</span></div>';
      html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;color:var(--mu);margin-bottom:8px">';
      if (v.zygosity) html += '<span>Zygosité: <strong style="color:var(--tx)">' + v.zygosity + '</strong></span>';
      if (v.vaf) html += '<span>VAF: <strong style="color:var(--tx)">' + v.vaf + '</strong></span>';
      if (v.depth) html += '<span>Profondeur: <strong style="color:var(--tx)">' + v.depth + '</strong></span>';
      html += '</div>';
      if (v.acmg_criteria && v.acmg_criteria.length) {
        html += '<div style="margin-bottom:6px">' + v.acmg_criteria.map(function(c) {
          return '<span style="font-size:11px;background:var(--s2);padding:2px 6px;border-radius:4px;margin-right:4px">' + c + '</span>';
        }).join('') + '</div>';
      }
      if (v.clinical_significance) html += '<div style="font-size:12px;color:var(--mu);margin-bottom:4px">' + v.clinical_significance + '</div>';
      if (v.action) html += '<div style="font-size:12px;font-weight:500;color:#0d9488;padding:6px 10px;background:#E1F5EE;border-radius:6px">→ ' + v.action + '</div>';
      html += '</div>';
    });
    html += '</div>';
  }

  var tmb = res.tmb; var msi = res.msi;
  if (tmb || msi) {
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">';
    if (tmb) html += '<div style="background:var(--s2);border-radius:8px;padding:10px"><div style="font-size:11px;color:var(--mu);font-weight:500;margin-bottom:2px">TMB</div><div style="font-size:18px;font-weight:700">' + (tmb.value || '-') + '</div><div style="font-size:12px;color:var(--mu)">' + (tmb.interpretation || '') + '</div></div>';
    if (msi) html += '<div style="background:var(--s2);border-radius:8px;padding:10px"><div style="font-size:11px;color:var(--mu);font-weight:500;margin-bottom:2px">MSI</div><div style="font-size:18px;font-weight:700">' + (msi.status || '-') + '</div><div style="font-size:12px;color:var(--mu)">' + (msi.interpretation || '') + '</div></div>';
    html += '</div>';
  }

  var recs = res.recommendations || [];
  if (recs.length) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px"><div style="font-size:12px;font-weight:600;margin-bottom:8px">Recommandations</div>';
    recs.forEach(function(r, i) {
      html += '<div style="font-size:13px;padding:4px 0;border-bottom:.5px solid var(--bd)">' + (i+1) + '. ' + r + '</div>';
    });
    html += '</div>';
  }

  html += '</div>';
  resDiv.innerHTML = html;
}

async function exportNGSPDF() {
  if (!_lastNGSResult) { alert('Analysez d abord un rapport NGS'); return; }
  var btn = document.getElementById('ngsExportBtn');
  if (btn) { btn.textContent = '...'; btn.disabled = true; }
  try {
    var r = await fetch('/ngs_to_pdf', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({result: _lastNGSResult})
    });
    if (!r.ok) throw new Error('Erreur PDF');
    var blob = await r.blob();
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'rapport_ngs.pdf'; a.click();
    URL.revokeObjectURL(url);
  } catch(e) { alert('Erreur: ' + e.message); }
  finally { if (btn) { btn.textContent = 'PDF'; btn.disabled = false; } }
}


// ══ CNV ANALYZER ══
var _lastCNVResult = null;
async function analyzeCNVAI() {
  var text=(document.getElementById('cnvAIInput')||{}).value||'';
  var context=(document.getElementById('cnvContext')||{}).value||'';
  var resDiv=document.getElementById('cnvAIResult');
  if(!resDiv)return;
  if(!text.trim()){resDiv.innerHTML='<div style="color:#dc2626;padding:10px;background:#fef2f2;border-radius:8px">Collez des donnees CNV.</div>';return;}
  resDiv.innerHTML='<div style="text-align:center;padding:20px"><div style="display:inline-block;width:24px;height:24px;border:3px solid var(--bd);border-top-color:#7c3aed;border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:8px;font-size:13px;color:var(--mu)">Analyse CNV...</div></div>';
  try {
    var userKey=localStorage.getItem('sgs_api_key')||'';
    var r=await fetch('/analyze_cnv',{method:'POST',headers:{'Content-Type':'application/json','X-User-Api-Key':userKey},body:JSON.stringify({text:text,context:context,user_api_key:userKey})});
    var d=await r.json();
    if(!d.success)throw new Error(d.error);
    _lastCNVResult=d.result;
    renderCNVResult(d.result);
  } catch(e){resDiv.innerHTML='<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px">Erreur: '+e.message+'</div>';}
}
function renderCNVResult(res){
  var resDiv=document.getElementById('cnvAIResult');
  if(!resDiv||!res)return;
  var html='<div style="display:flex;flex-direction:column;gap:12px">';
  if(res.urgent)html+='<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;color:#dc2626;font-size:13px;font-weight:500">⚠️ '+res.urgent_reason+'</div>';
  var cnvs=res.cnvs||[];
  var amps=cnvs.filter(function(c){return c.type==='amplification';}).length;
  var dels=cnvs.filter(function(c){return c.type&&c.type.includes('delet');}).length;
  html+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#7c3aed">'+cnvs.length+'</div><div style="font-size:11px;color:var(--mu)">CNV detectes</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#dc2626">'+amps+'</div><div style="font-size:11px;color:var(--mu)">Amplifications</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#ea580c">'+dels+'</div><div style="font-size:11px;color:var(--mu)">Deletions</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:13px;font-weight:700;color:#0d9488">'+(res.genome_instability||'-')+'</div><div style="font-size:11px;color:var(--mu)">Instabilite</div></div>';
  html+='</div>';
  if(res.summary)html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b>Resume: </b>'+res.summary+'</div>';
  cnvs.forEach(function(c){
    var color=c.type==='amplification'?'#dc2626':c.type&&c.type.includes('delet')?'#ea580c':'#0d9488';
    html+='<div style="border:1px solid var(--bd);border-left:4px solid '+color+';border-radius:8px;padding:12px">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
    html+='<b style="font-size:15px">'+c.gene+'</b><span style="font-size:11px;color:var(--mu)">'+c.chromosome+'</span>';
    html+='<div style="display:flex;gap:6px"><span style="font-size:12px;background:var(--s2);padding:2px 8px;border-radius:12px">CN: <b>'+(c.copy_number||'-')+'</b></span>';
    html+='<span style="font-size:11px;background:'+color+'22;color:'+color+';padding:3px 8px;border-radius:10px;font-weight:600">'+c.type+'</span></div></div>';
    if(c.log2_ratio!=null)html+='<div style="font-size:12px;color:var(--mu);margin-bottom:4px">Log2: <b>'+c.log2_ratio+'</b>'+(c.size_mb?' · '+c.size_mb+' Mb':'')+'</div>';
    if(c.clinical_significance)html+='<div style="font-size:12px;margin-bottom:6px">'+c.clinical_significance+'</div>';
    if(c.therapeutic_targets&&c.therapeutic_targets.length){html+='<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">';c.therapeutic_targets.forEach(function(t){html+='<span style="font-size:11px;background:#0d948822;color:#0d9488;padding:2px 8px;border-radius:10px">💊 '+t+'</span>';});html+='</div>';}
    if(c.action)html+='<div style="font-size:12px;background:#0d948811;border-radius:6px;padding:8px;color:#0d9488">→ '+c.action+'</div>';
    html+='</div>';
  });
  if(res.recommendations&&res.recommendations.length){html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b style="font-size:12px">Recommandations</b><br>';res.recommendations.forEach(function(r,i){html+='<div style="font-size:13px;padding:4px 0;border-bottom:.5px solid var(--bd)">'+(i+1)+'. '+r+'</div>';});html+='</div>';}
  html+='</div>';resDiv.innerHTML=html;
}
function handleCNVUpload(input){var f=input.files[0];if(!f)return;var rd=new FileReader();rd.onload=function(e){var t=document.getElementById('cnvAIInput');if(t)t.value=e.target.result;};rd.readAsText(f);}

// ══ FUSIONS GÉNIQUES ══
var _lastFusionResult = null;
async function analyzeFusionsAI() {
  var text=(document.getElementById('fusionAIInput')||{}).value||'';
  var context=(document.getElementById('fusionContext')||{}).value||'';
  var resDiv=document.getElementById('fusionAIResult');
  if(!resDiv)return;
  if(!text.trim()){resDiv.innerHTML='<div style="color:#dc2626;padding:10px;background:#fef2f2;border-radius:8px">Collez des donnees de fusions.</div>';return;}
  resDiv.innerHTML='<div style="text-align:center;padding:20px"><div style="display:inline-block;width:24px;height:24px;border:3px solid var(--bd);border-top-color:#2563eb;border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:8px;font-size:13px;color:var(--mu)">Analyse fusions...</div></div>';
  try {
    var userKey=localStorage.getItem('sgs_api_key')||'';
    var r=await fetch('/analyze_fusions',{method:'POST',headers:{'Content-Type':'application/json','X-User-Api-Key':userKey},body:JSON.stringify({text:text,context:context,user_api_key:userKey})});
    var d=await r.json();
    if(!d.success)throw new Error(d.error);
    _lastFusionResult=d.result;renderFusionResult(d.result);
  } catch(e){resDiv.innerHTML='<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px">Erreur: '+e.message+'</div>';}
}
function renderFusionResult(res){
  var resDiv=document.getElementById('fusionAIResult');
  if(!resDiv||!res)return;
  var html='<div style="display:flex;flex-direction:column;gap:12px">';
  if(res.urgent)html+='<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;color:#dc2626;font-size:13px;font-weight:500">⚠️ '+res.urgent_reason+'</div>';
  html+='<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#2563eb">'+(res.total_fusions||0)+'</div><div style="font-size:11px;color:var(--mu)">Fusions</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#dc2626">'+(res.oncogenic_fusions||0)+'</div><div style="font-size:11px;color:var(--mu)">Oncogeniques</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:22px;font-weight:700;color:#0d9488">'+(res.actionable_fusions||0)+'</div><div style="font-size:11px;color:var(--mu)">Actionnables</div></div>';
  html+='</div>';
  if(res.summary)html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b>Resume: </b>'+res.summary+'</div>';
  var fusions=res.fusions||[];
  fusions.forEach(function(f){
    var tierColor=f.tier==='Tier I'?'#dc2626':f.tier==='Tier II'?'#ea580c':f.tier==='Tier III'?'#f59e0b':'#6b7280';
    html+='<div style="border:1px solid var(--bd);border-left:4px solid '+tierColor+';border-radius:8px;padding:12px">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
    html+='<b style="font-size:16px;color:'+tierColor+'">'+(f.name||(f.gene5+'-'+f.gene3))+'</b>';
    html+='<div style="display:flex;gap:6px">';
    if(f.tier)html+='<span style="font-size:11px;background:'+tierColor+'22;color:'+tierColor+';padding:3px 8px;border-radius:10px;font-weight:600">'+f.tier+'</span>';
    if(f.oncogenic)html+='<span style="font-size:11px;background:#dc262622;color:#dc2626;padding:3px 8px;border-radius:10px">Oncogenique</span>';
    html+='</div></div>';
    if(f.breakpoint5||f.breakpoint3)html+='<div style="font-size:12px;color:var(--mu);font-family:monospace;margin-bottom:6px">'+(f.gene5||'')+' ['+f.breakpoint5+'] :: '+(f.gene3||'')+' ['+f.breakpoint3+']</div>';
    if(f.allele_frequency)html+='<div style="font-size:12px;color:var(--mu);margin-bottom:4px">AF: <b>'+f.allele_frequency+'</b>'+(f.read_support?' · Reads: <b>'+f.read_support+'</b>':'')+'</div>';
    if(f.therapeutic_targets&&f.therapeutic_targets.length){html+='<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">';f.therapeutic_targets.forEach(function(t){html+='<span style="font-size:11px;background:#2563eb22;color:#2563eb;padding:2px 8px;border-radius:10px">💊 '+t+'</span>';});html+='</div>';}
    if(f.resistance_mechanisms&&f.resistance_mechanisms.length)html+='<div style="font-size:11px;color:#f59e0b;background:#fef3c7;border-radius:6px;padding:6px;margin-bottom:6px">⚠️ Resistances: '+f.resistance_mechanisms.join(', ')+'</div>';
    if(f.action)html+='<div style="font-size:12px;background:#2563eb11;border-radius:6px;padding:8px;color:#2563eb">→ '+f.action+'</div>';
    html+='</div>';
  });
  if(res.recommendations&&res.recommendations.length){html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b style="font-size:12px">Recommandations</b><br>';res.recommendations.forEach(function(r,i){html+='<div style="font-size:13px;padding:4px 0;border-bottom:.5px solid var(--bd)">'+(i+1)+'. '+r+'</div>';});html+='</div>';}
  html+='</div>';resDiv.innerHTML=html;
}
function handleFusionUpload(input){var f=input.files[0];if(!f)return;var rd=new FileReader();rd.onload=function(e){var t=document.getElementById('fusionAIInput');if(t)t.value=e.target.result;};rd.readAsText(f);}

// ══ SIGNATURES MUTATIONNELLES ══
var _lastSigResult = null;
async function analyzeSignaturesAI() {
  var text=(document.getElementById('sigAIInput')||{}).value||'';
  var context=(document.getElementById('sigContext')||{}).value||'';
  var resDiv=document.getElementById('sigAIResult');
  if(!resDiv)return;
  if(!text.trim()){resDiv.innerHTML='<div style="color:#dc2626;padding:10px;background:#fef2f2;border-radius:8px">Collez des donnees de signatures.</div>';return;}
  resDiv.innerHTML='<div style="text-align:center;padding:20px"><div style="display:inline-block;width:24px;height:24px;border:3px solid var(--bd);border-top-color:#059669;border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:8px;font-size:13px;color:var(--mu)">Analyse signatures...</div></div>';
  try {
    var userKey=localStorage.getItem('sgs_api_key')||'';
    var r=await fetch('/analyze_signatures',{method:'POST',headers:{'Content-Type':'application/json','X-User-Api-Key':userKey},body:JSON.stringify({text:text,context:context,user_api_key:userKey})});
    var d=await r.json();
    if(!d.success)throw new Error(d.error);
    _lastSigResult=d.result;renderSigResult(d.result);
  } catch(e){resDiv.innerHTML='<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px">Erreur: '+e.message+'</div>';}
}
function renderSigResult(res){
  var resDiv=document.getElementById('sigAIResult');
  if(!resDiv||!res)return;
  var colors=['#059669','#2563eb','#7c3aed','#dc2626','#ea580c','#f59e0b','#0d9488'];
  var html='<div style="display:flex;flex-direction:column;gap:12px">';
  if(res.urgent)html+='<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;color:#dc2626;font-size:13px;font-weight:500">⚠️ '+res.urgent_reason+'</div>';
  html+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:15px;font-weight:700;color:#059669">'+(res.dominant_signature||'-')+'</div><div style="font-size:11px;color:var(--mu)">Dominante</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:13px;font-weight:700;color:#7c3aed">'+(res.tmb||'-')+'</div><div style="font-size:11px;color:var(--mu)">TMB</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:14px;font-weight:700;color:#dc2626">'+(res.hrd_status||'-')+'</div><div style="font-size:11px;color:var(--mu)">HRD</div></div>';
  html+='<div style="background:var(--s2);border-radius:8px;padding:10px;text-align:center"><div style="font-size:14px;font-weight:700;color:#0d9488">'+(res.msi_predicted||'-')+'</div><div style="font-size:11px;color:var(--mu)">MSI</div></div>';
  html+='</div>';
  if(res.summary)html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b>Resume: </b>'+res.summary+'</div>';
  if(res.immunotherapy_prediction||res.parp_inhibitor_prediction){
    html+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">';
    if(res.immunotherapy_prediction)html+='<div style="background:#2563eb11;border:1px solid #2563eb33;border-radius:8px;padding:10px"><div style="font-size:11px;font-weight:600;color:#2563eb;margin-bottom:4px">🧬 Immunotherapie</div><div style="font-size:12px">'+res.immunotherapy_prediction+'</div></div>';
    if(res.parp_inhibitor_prediction)html+='<div style="background:#05996911;border:1px solid #05996933;border-radius:8px;padding:10px"><div style="font-size:11px;font-weight:600;color:#059669;margin-bottom:4px">💊 Inh. PARP</div><div style="font-size:12px">'+res.parp_inhibitor_prediction+'</div></div>';
    html+='</div>';
  }
  var sigs=res.signatures||[];
  sigs.forEach(function(s,idx){
    var col=colors[idx%colors.length];var pct=s.contribution||0;
    html+='<div style="border:1px solid var(--bd);border-radius:8px;padding:12px">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
    html+='<div><span style="font-weight:700;font-size:15px;color:'+col+'">'+s.id+'</span><span style="font-size:12px;color:var(--mu);margin-left:8px">'+s.name+'</span></div>';
    html+='<b style="color:'+col+'">'+pct+'%</b></div>';
    html+='<div style="background:var(--bd);border-radius:4px;height:6px;margin-bottom:8px"><div style="background:'+col+';width:'+Math.min(pct,100)+'%;height:100%;border-radius:4px"></div></div>';
    if(s.etiology)html+='<div style="font-size:12px;margin-bottom:4px">'+s.etiology+'</div>';
    if(s.clinical_implications)html+='<div style="font-size:12px;color:var(--mu);font-style:italic;margin-bottom:6px">'+s.clinical_implications+'</div>';
    if(s.therapeutic_targets&&s.therapeutic_targets.length){html+='<div style="display:flex;flex-wrap:wrap;gap:4px">';s.therapeutic_targets.forEach(function(t){html+='<span style="font-size:11px;background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:10px">💊 '+t+'</span>';});html+='</div>';}
    html+='</div>';
  });
  if(res.recommendations&&res.recommendations.length){html+='<div style="background:var(--s2);border-radius:8px;padding:12px"><b style="font-size:12px">Recommandations</b><br>';res.recommendations.forEach(function(r,i){html+='<div style="font-size:13px;padding:4px 0;border-bottom:.5px solid var(--bd)">'+(i+1)+'. '+r+'</div>';});html+='</div>';}
  html+='</div>';resDiv.innerHTML=html;
}
function handleSigUpload(input){var f=input.files[0];if(!f)return;var rd=new FileReader();rd.onload=function(e){var t=document.getElementById('sigAIInput');if(t)t.value=e.target.result;};rd.readAsText(f);}


// ══ TUMEUR BOARD IA (MTB) ══
var _lastMTBResult = null;

async function analyzeTumorBoard() {
  var resDiv = document.getElementById('mtbResult');
  if (!resDiv) return;

  var patientInfo = (document.getElementById('mtbPatient')||{}).value||'';
  var ngsResult   = window._lastNGSResult   || null;
  var cnvResult   = window._lastCNVResult   || null;
  var fusionResult= window._lastFusionResult|| null;
  var sigResult   = window._lastSigResult   || null;

  if (!ngsResult && !cnvResult && !fusionResult && !sigResult) {
    resDiv.innerHTML='<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px;font-size:13px">Analysez au moins un module (NGS, CNV, Fusions ou Signatures) avant de lancer le Tumeur Board.</div>';
    return;
  }

  resDiv.innerHTML='<div style="text-align:center;padding:30px"><div style="display:inline-block;width:28px;height:28px;border:3px solid var(--bd);border-top-color:#7c3aed;border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:12px;font-size:13px;color:var(--mu)">Synthese multi-omique en cours — Claude Sonnet analyse toutes les donnees...</div></div>';

  try {
    var userKey = localStorage.getItem('sgs_api_key')||'';
    var r = await fetch('/tumor_board', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-User-Api-Key':userKey},
      body: JSON.stringify({
        patient_info:  patientInfo,
        ngs_result:    ngsResult,
        cnv_result:    cnvResult,
        fusion_result: fusionResult,
        sig_result:    sigResult,
        user_api_key:  userKey
      })
    });
    var d = await r.json();
    if (!d.success) throw new Error(d.error);
    _lastMTBResult = d.result;
    renderMTBResult(d.result);
  } catch(e) {
    resDiv.innerHTML='<div style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px;font-size:13px">Erreur: '+e.message+'</div>';
  }
}

function renderMTBResult(res) {
  var resDiv = document.getElementById('mtbResult');
  if (!resDiv||!res) return;
  var html = '<div style="display:flex;flex-direction:column;gap:14px">';

  if (res.urgent) html += '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;color:#dc2626;font-size:13px;font-weight:500">⚠️ URGENT: '+res.urgent_reason+'</div>';

  // En-tête RCP
  html += '<div style="background:linear-gradient(135deg,#1e3a5f,#0d9488);border-radius:12px;padding:16px;color:white">';
  html += '<div style="font-size:11px;opacity:.8;letter-spacing:.05em;margin-bottom:4px">SYNTHESE TUMEUR BOARD — DECISION RCP</div>';
  html += '<div style="font-size:14px;line-height:1.6">'+res.patient_summary+'</div>';
  html += '<div style="margin-top:10px;display:flex;gap:8px"><span style="font-size:11px;background:rgba(255,255,255,.2);padding:3px 10px;border-radius:10px">Complexite: '+res.genomic_complexity+'</span></div>';
  html += '</div>';

  // Findings clés
  if (res.key_findings&&res.key_findings.length) {
    html += '<div style="border:1px solid var(--bd);border-radius:10px;padding:14px">';
    html += '<div style="font-size:12px;font-weight:600;margin-bottom:10px;color:var(--mu)">FINDINGS CLES</div>';
    res.key_findings.forEach(function(f){
      var uc = f.urgency==='haute'?'#dc2626':f.urgency==='modérée'?'#f59e0b':'#0d9488';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;padding:8px 0;border-bottom:.5px solid var(--bd)">';
      html += '<div><div style="font-size:13px;font-weight:500">'+f.finding+'</div><div style="font-size:12px;color:var(--mu)">'+f.significance+'</div></div>';
      html += '<span style="font-size:11px;background:'+uc+'22;color:'+uc+';padding:2px 8px;border-radius:8px;white-space:nowrap;margin-left:8px">'+f.urgency+'</span>';
      html += '</div>';
    });
    html += '</div>';
  }

  // Priorités thérapeutiques
  if (res.therapeutic_priorities&&res.therapeutic_priorities.length) {
    html += '<div style="font-size:12px;font-weight:600;color:var(--mu);letter-spacing:.05em">PRIORITES THERAPEUTIQUES</div>';
    res.therapeutic_priorities.forEach(function(t){
      var rank = t.rank||1;
      var rankColor = rank===1?'#dc2626':rank===2?'#ea580c':'#f59e0b';
      html += '<div style="border:1px solid var(--bd);border-left:4px solid '+rankColor+';border-radius:8px;padding:12px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
      html += '<div style="display:flex;align-items:center;gap:8px">';
      html += '<span style="font-size:18px;font-weight:700;color:'+rankColor+'">#'+rank+'</span>';
      html += '<span style="font-size:14px;font-weight:600">'+t.therapy+'</span></div>';
      html += '<span style="font-size:11px;background:#0d948822;color:#0d9488;padding:2px 8px;border-radius:8px">'+t.evidence_level+'</span>';
      html += '</div>';
      html += '<div style="font-size:12px;color:var(--mu);margin-bottom:4px">Biomarqueur: <b>'+t.biomarker+'</b></div>';
      html += '<div style="font-size:12px;margin-bottom:6px">'+t.rationale+'</div>';
      if (t.expected_response) html += '<div style="font-size:12px;color:#0d9488;background:#0d948811;border-radius:6px;padding:6px">Reponse attendue: '+t.expected_response+'</div>';
      html += '</div>';
    });
  }

  // Recommandation RCP
  if (res.rcp_recommendation) {
    html += '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px">';
    html += '<div style="font-size:12px;font-weight:600;color:#16a34a;margin-bottom:8px">RECOMMANDATION RCP OFFICIELLE</div>';
    html += '<div style="font-size:13px;line-height:1.7;color:#166534">'+res.rcp_recommendation+'</div>';
    html += '</div>';
  }

  // Essais cliniques
  if (res.clinical_trials&&res.clinical_trials.length) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px">';
    html += '<div style="font-size:12px;font-weight:600;margin-bottom:8px">Essais cliniques eligibles</div>';
    res.clinical_trials.forEach(function(t){ html += '<div style="font-size:12px;padding:3px 0">• '+t+'</div>'; });
    html += '</div>';
  }

  // Actions urgentes
  if (res.urgent_actions&&res.urgent_actions.length) {
    html += '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px">';
    html += '<div style="font-size:12px;font-weight:600;color:#dc2626;margin-bottom:8px">Actions urgentes (48h)</div>';
    res.urgent_actions.forEach(function(a){ html += '<div style="font-size:12px;padding:3px 0;color:#991b1b">→ '+a+'</div>'; });
    html += '</div>';
  }

  // Suivi + Lacunes
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">';
  if (res.follow_up&&res.follow_up.length) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px"><div style="font-size:12px;font-weight:600;margin-bottom:6px">Plan de suivi</div>';
    res.follow_up.forEach(function(f){ html += '<div style="font-size:12px;padding:2px 0">• '+f+'</div>'; });
    html += '</div>';
  }
  if (res.molecular_profiling_gaps&&res.molecular_profiling_gaps.length) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px"><div style="font-size:12px;font-weight:600;margin-bottom:6px">Examens complementaires</div>';
    res.molecular_profiling_gaps.forEach(function(g){ html += '<div style="font-size:12px;padding:2px 0">• '+g+'</div>'; });
    html += '</div>';
  }
  html += '</div>';

  if (res.prognosis) {
    html += '<div style="background:var(--s2);border-radius:8px;padding:12px"><span style="font-weight:500;font-size:13px">Pronostic: </span><span style="font-size:13px">'+res.prognosis+'</span></div>';
  }

  html += '</div>';
  resDiv.innerHTML = html;
}
