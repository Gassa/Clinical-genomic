#!/bin/bash
set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
PROJECT_DIR="$HOME/Downloads/SenGenoScope_v7"
REPO="https://github.com/Gassa/Clinical-genomic.git"
BRANCH="main"
DATE_NOW="$(date '+%Y-%m-%d %H:%M')"
MSG="SenGenoScope v7 - Oncogenomique Oncopharmacogenomique Claude AI - ${DATE_NOW}"

echo ""
echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  SenGenoScope v7 - Deploiement                      ${NC}"
echo -e "${CYAN}  Dr. Moustapha Gassama                               ${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""

cd "$PROJECT_DIR"

echo -e "${CYAN}[1/4] Verification des fichiers...${NC}"
ALL_OK=true
for f in "app.py" "claude_ai.py" "templates/index.html" "requirements.txt" "Procfile" "render.yaml"; do
  if [ -f "$f" ]; then
    echo -e "  ${GREEN}OK $f${NC}"
  else
    echo -e "  ${RED}MANQUANT : $f${NC}"
    ALL_OK=false
  fi
done
if [ "$ALL_OK" = "false" ]; then
  echo -e "${RED}Fichiers manquants. Verifiez le ZIP.${NC}"
  exit 1
fi

echo -e "${CYAN}[2/4] Protection .env...${NC}"
touch .gitignore
grep -qxF '.env' .gitignore || echo ".env" >> .gitignore
echo -e "${GREEN}OK${NC}"

echo -e "${CYAN}[3/4] Configuration Git...${NC}"
if [ ! -d ".git" ]; then
  git init
  echo -e "${YELLOW}  Git initialise${NC}"
fi
git remote set-url origin "$REPO" 2>/dev/null || git remote add origin "$REPO"
git checkout -B "$BRANCH" 2>/dev/null || true
git add -A
if git diff --cached --quiet 2>/dev/null; then
  echo -e "${YELLOW}  Rien a committer${NC}"
else
  git commit -m "$MSG"
  echo -e "${GREEN}  Commit cree${NC}"
fi

echo -e "${CYAN}[4/4] Push vers GitHub...${NC}"
git push -u origin "$BRANCH" --force

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  DEPLOIEMENT TERMINE                                ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "  Site live : ${CYAN}https://clinical-genomic.onrender.com${NC}"
echo ""
echo -e "${YELLOW}  Ajoutez votre cle API sur Render :${NC}"
echo -e "  https://dashboard.render.com -> Environment"
echo -e "  ANTHROPIC_API_KEY = sk-ant-api03-..."
echo ""
