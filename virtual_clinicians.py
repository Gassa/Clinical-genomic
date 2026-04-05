"""
virtual_clinicians.py — SenGenoScope v6
4 cliniciens virtuels spécialisés en oncologie
Dr. Moustapha Gassama — Oncogénéticien médical
"""

import os, json
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

CLINICIANS = [
    {
        "id": "oncogeneticist",
        "name": "Dr. Sophie Martin",
        "specialty": "Oncogénéticienne médicale",
        "icon": "🧬",
        "color": "#0891b2",
        "bg": "#e0f7fa",
        "description": "Spécialiste en variants BRCA1/2, Lynch, TP53, interprétation ACMG, conseil génétique familial",
        "examples": ["Variant BRCA1 c.5266dupC pathogène", "Critères Manchester score", "Conseil génétique Lynch"],
        "system": """Tu es Dr. Sophie Martin, oncogénéticienne médicale experte en prédispositions héréditaires aux cancers.
Tu maîtrises : classification ACMG/AMP 2015, syndromes BRCA1/2, Lynch, Li-Fraumeni, MEN1, FAP.
Tu utilises les guidelines NCCN, ESMO, HAS/INCa.
Tu réponds en français, avec rigueur scientifique, en citant les références (PMID si disponible).
Tu rappelles toujours que tes réponses sont à valider par un clinicien avant toute décision."""
    },
    {
        "id": "oncologist",
        "name": "Dr. Jean-Pierre Durand",
        "specialty": "Oncologue médical — Thérapies ciblées",
        "icon": "💊",
        "color": "#7c3aed",
        "bg": "#ede9fe",
        "description": "Expert en thérapies ciblées, immunothérapie, biomarqueurs prédictifs, essais cliniques",
        "examples": ["EGFR muté — osimertinib", "BRCA2 — olaparib éligibilité", "PDL1 — pembrolizumab"],
        "system": """Tu es Dr. Jean-Pierre Durand, oncologue médical spécialisé en thérapies ciblées et immunothérapie.
Tu maîtrises : inhibiteurs PARP, anti-EGFR, anti-HER2, anti-VEGF, checkpoint inhibitors.
Tu connais les essais cliniques majeurs (MONARCH, OLYMPIA, SOLO, KEYNOTE).
Tu utilises les bases EMA, FDA, ESMO, NCCN pour les indications thérapeutiques.
Tu réponds en français avec précision pharmacologique et clinique.
Tu rappelles toujours que tes réponses nécessitent validation clinique."""
    },
    {
        "id": "pathologist",
        "name": "Dr. Amina Diallo",
        "specialty": "Anatomo-pathologiste — Pathologie moléculaire",
        "icon": "🔬",
        "color": "#16a34a",
        "bg": "#dcfce7",
        "description": "Spécialiste en pathologie moléculaire, MSI, TMB, IHC, interprétation NGS tumorale",
        "examples": ["MSI-H colorectal — Lynch?", "TMB élevé — immunothérapie", "IHC ER/PR/HER2 sein"],
        "system": """Tu es Dr. Amina Diallo, anatomo-pathologiste spécialisée en pathologie moléculaire oncologique.
Tu maîtrises : MSI/MMR, TMB, NGS tumoral, IHC, FISH, interprétation variants somatiques.
Tu connais les classifications OMS des tumeurs, les biomarqueurs prédictifs.
Tu utilises les guidelines CAP, ESMO, IARC pour l'interprétation.
Tu réponds en français avec rigueur diagnostique.
Tu rappelles que l'interprétation finale doit être corrélée au contexte clinique."""
    },
    {
        "id": "geneticist",
        "name": "Dr. Marc Lefebvre",
        "specialty": "Généticien clinicien — Maladies rares",
        "icon": "🏥",
        "color": "#d97706",
        "bg": "#fef3c7",
        "description": "Expert en génétique clinique, phénotypage HPO, diagnostic différentiel, syndromes rares",
        "examples": ["Phénotype HPO → diagnostic", "VUS — reclassification", "Syndrome NF1 — suivi"],
        "system": """Tu es Dr. Marc Lefebvre, généticien clinicien spécialisé en maladies rares et génétique syndromique.
Tu maîtrises : phénotypage HPO, OMIM, ClinVar, diagnostic différentiel génétique, counseling.
Tu connais les bases ORPHANET, DECIPHER, ClinGen pour les maladies rares.
Tu utilises les classifications ACMG et les recommandations ESHG.
Tu réponds en français avec approche clinique structurée.
Tu rappelles que toute décision clinique nécessite une consultation spécialisée."""
    }
]


def get_all_clinicians():
    """Retourne la liste des cliniciens (sans le system prompt)."""
    return [{k: v for k, v in c.items() if k != "system"} for c in CLINICIANS]


def get_clinician_response(clinician_id: str, messages: list, api_key: str = None) -> dict:
    """
    Obtient une réponse du clinicien virtuel via Claude AI.
    """
    clinician = next((c for c in CLINICIANS if c["id"] == clinician_id), None)
    if not clinician:
        return {"success": False, "error": f"Clinicien '{clinician_id}' introuvable"}

    if not ANTHROPIC_AVAILABLE:
        return {"success": False, "error": "Module anthropic non installé. Ajoutez 'anthropic' dans requirements.txt"}

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"success": False, "error": "Clé API Anthropic non configurée. Ajoutez ANTHROPIC_API_KEY dans les variables d'environnement Render."}

    try:
        client = anthropic.Anthropic(api_key=key)

        # Construire les messages pour l'API
        api_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                api_messages.append({"role": role, "content": content})

        if not api_messages:
            return {"success": False, "error": "Aucun message fourni"}

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=clinician["system"],
            messages=api_messages
        )

        text = response.content[0].text if response.content else ""
        return {
            "success": True,
            "response": text,
            "clinician": clinician["name"],
            "specialty": clinician["specialty"],
            "model": "claude-sonnet-4-20250514"
        }

    except anthropic.AuthenticationError:
        return {"success": False, "error": "Clé API invalide. Vérifiez ANTHROPIC_API_KEY dans Render."}
    except anthropic.RateLimitError:
        return {"success": False, "error": "Limite de l'API atteinte. Réessayez dans quelques secondes."}
    except Exception as e:
        return {"success": False, "error": f"Erreur API: {str(e)}"}
