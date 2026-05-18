#!/bin/bash
# AutoRun v3 — Quick restart helper
# Run with: sudo bash restart.sh
# Pulls latest code, rebuilds frontend, reinstalls Python deps, restarts service.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

if [ "$EUID" -ne 0 ]; then
  error "Please run as root: sudo bash restart.sh"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/backend/venv"

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║   AutoRun v3  —  Restart         ║"
echo "  ╚══════════════════════════════════╝"
echo ""

info "Stopping AutoRun service..."
systemctl stop autorun || true

# ── Git pull ──────────────────────────────────────────────────────────────────
info "Pulling latest code from git..."
cd "$SCRIPT_DIR"
git pull
success "Code updated"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Updating Python dependencies..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/backend/requirements.txt"
success "Python dependencies up to date"

# ── Rebuild frontend ──────────────────────────────────────────────────────────
info "Rebuilding React frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run build
success "Frontend rebuilt → frontend/dist/"
cd "$SCRIPT_DIR"

# ── Reload systemd + restart ──────────────────────────────────────────────────
info "Restarting AutoRun service..."
systemctl daemon-reload
systemctl restart autorun
success "AutoRun service restarted"

echo ""
echo -e "  ${GREEN}Done!${NC}"
echo ""
echo "  Dashboard → http://localhost:8080"
echo "  Logs      → journalctl -u autorun -f"
echo ""
