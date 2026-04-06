# 🧬 SenGenoScope — Plateforme d'Oncogénomique et Oncopharmacogénomique Clinique

**Dr. Moustapha Gassama** — Oncogénéticien médical | Public Health Data Scientist

🌐 Site : https://clinical-genomic.onrender.com
📁 GitHub : https://github.com/Gassa/Clinical-genomic

---

## 🆕 Nouveautés v1.0

| Module | Description |
|--------|-------------|
| 🧬 Renommage | Plateforme d'Oncogénomique ET Oncopharmacogénomique Clinique |
| 🤖 Chat IA | Assistant oncogénomique spécialisé (Claude Sonnet) |
| 📁 Upload IA | Analyse VCF/CSV/FASTA par Claude AI + interprétation ACMG |
| 💊 Pharma IA | Oncopharmacogénomique : gène → médicaments, CPIC/DPWG/FDA |
| 👤 Identité | Dr. Moustapha Gassama affiché dans footer et rapports |
| 🔗 Cowork | Bouton Claude Cowork intégré dans la sidebar |

---

## 🚀 DÉPLOIEMENT — 3 étapes

### Étape 1 — Pousser sur GitHub

```bash
# Sur votre Mac / Linux, dans le dossier du projet :
chmod +x deploy.sh
./deploy.sh "SenGenoScope — Oncopharmacogénomique"

# OU manuellement :
git init
git remote add origin https://github.com/Gassa/Clinical-genomic.git
git add -A
git commit -m "SenGenoScope"
git push -u origin main --force
```

### Étape 2 — Configurer la clé API Claude sur Render

1. Aller sur **https://dashboard.render.com**
2. Cliquer sur votre service **clinical-genomic**
3. Menu gauche → **Environment**
4. **Add Environment Variable**
   - Key : `ANTHROPIC_API_KEY`
   - Value : `sk-ant-api03-...` (depuis https://console.anthropic.com)
5. **Save Changes** → Render redéploie automatiquement (~2 min)

### Étape 3 — Vérifier

Aller sur https://clinical-genomic.onrender.com
→ Sidebar : **Intelligence Artificielle → Chat IA Clinique**
→ Badge vert **✅ Claude AI connecté** = tout fonctionne !

---

## 📁 Structure du projet

```
Clinical-genomic/
├── app.py                  # Backend Flask — 50+ routes API
├── claude_ai.py            # 🆕 Claude AI (chat, upload, pharma, rapport)
├── advanced_modules.py     # Manchester, VCF parser, lettres génétiques
├── clinical_modules.py     # PRS, NGS, pénétrance, guidelines
├── genomic_tools.py        # VEP Ensembl, ACMG, séquences
├── databases.py            # ClinVar, OMIM, COSMIC, ClinGen
├── pubmed.py               # PubMed NCBI (sans limite d'articles)
├── gene_extractor.py       # Extraction de gènes depuis abstracts
├── pdf_report.py           # Export PDF clinique
├── requirements.txt        # Dépendances (inclus: anthropic==0.40.0)
├── Procfile                # gunicorn pour Render
├── render.yaml             # Config Render
├── deploy.sh               # 🆕 Script déploiement GitHub
├── setup.sh                # Installation locale
└── templates/
    └── index.html          # 🆕 Interface v1.0 — 16 modules
```

---

## ⚠️ Sécurité

- Le fichier `.env` ne doit **JAMAIS** être pushé sur GitHub
- La clé `ANTHROPIC_API_KEY` se configure **uniquement** sur Render
- Sans la clé, l'app fonctionne mais les modules IA affichent une erreur
- Usage clinique confidentiel — Dr. Moustapha Gassama

---

## 🔧 Installation locale

```bash
chmod +x setup.sh
./setup.sh
```

Puis éditez `.env` pour ajouter votre `ANTHROPIC_API_KEY`.
# rebuilt sam.  4 avr. 2026 20:58:46 EDT
rebuild
