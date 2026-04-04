#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# deploy.sh — SenGenoScope v7 — Déploiement GitHub + Render
# Usage: ./deploy.sh "message de commit"
# ═══════════════════════════════════════════════════════════════════════════
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

REPO="https://github.com/Gassa/Clinical-genomic.git"
BRANCH="main"
MSG="${1:-SenGenoScope v7 — Oncogénomique + Oncopharmacogénomique + Claude AI — $(date '+%Y-%m-%d %H:%M')}"

echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  🧬 SenGenoScope v7 — Déploiement GitHub             ${NC}"
echo -e "${CYAN}  Plateforme d'Oncogénomique & Oncopharmacogénomique  ${NC}"
echo -e "${CYAN}  Dr. Moustapha Gassama                               ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

command -v git &>/dev/null || { echo -e "${RED}❌ Git non installé${NC}"; exit 1; }

if [ ! -d ".git" ]; then
  echo -e "${YELLOW}Initialisation du dépôt Git…${NC}"
  git init
  git remote add origin "$REPO"
fi

git remote set-url origin "$REPO" 2>/dev/null || git remote add origin "$REPO"

# Protéger .env
grep -qxF '.env' .gitignore 2>/dev/null || echo ".env" >> .gitignore

git checkout -B "$BRANCH" 2>/dev/null || true
git add -A

if git diff --cached --quiet 2>/dev/null; then
  echo -e "${YELLOW}Aucun changement à committer${NC}"
else
  git commit -m "$MSG"
fi

echo -e "${CYAN}Push vers GitHub…${NC}"
git push -u origin "$BRANCH" --force 2>&1

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Déployé sur GitHub!                  ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo -e "  GitHub : ${CYAN}${REPO}${NC}"
echo -e "  Site   : ${CYAN}https://clinical-genomic.onrender.com${NC}"
echo ""
echo -e "${YELLOW}  ⚡ ÉTAPES SUIVANTES — Render:${NC}"
echo -e "  1. https://dashboard.render.com"
echo -e "  2. Votre service → Environment"
echo -e "  3. Ajoutez : ANTHROPIC_API_KEY = sk-ant-api03-..."
echo -e "  4. Save Changes → Render redéploie automatiquement (~2 min)"
echo ""
