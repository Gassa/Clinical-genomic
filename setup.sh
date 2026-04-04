#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# setup.sh — Installation locale SenGenoScope v7
# ═══════════════════════════════════════════════════════════════════════════
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  🧬 SenGenoScope v7 — Installation locale             ${NC}"
echo -e "${CYAN}  Dr. Moustapha Gassama                                ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

if ! command -v python3 &>/dev/null; then echo -e "${RED}❌ Python3 requis${NC}"; exit 1; fi
echo -e "${GREEN}✅ Python: $(python3 --version)${NC}"

echo -e "${CYAN}[1/4] Création de l'environnement virtuel…${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}✅ venv activé${NC}"

echo -e "${CYAN}[2/4] Installation des dépendances…${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Dépendances installées (inclus: anthropic)${NC}"

echo -e "${CYAN}[3/4] Configuration .env…${NC}"
if [ ! -f ".env" ]; then
  cat > .env << 'ENVEOF'
# SenGenoScope v7 — Variables d'environnement
# Obtenez votre clé sur https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-api03-VOTRE_CLE_ICI
PORT=5000
ENVEOF
  echo -e "${YELLOW}⚠️  Fichier .env créé. Editez-le et ajoutez votre clé:${NC}"
  echo -e "  ${YELLOW}nano .env${NC}"
else
  echo -e "${GREEN}✅ .env existant conservé${NC}"
fi

echo -e "${CYAN}[4/4] Lancement du serveur…${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Prêt! Serveur sur http://localhost:5000           ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
python3 app.py
