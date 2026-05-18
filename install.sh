#!/bin/bash
# AutoRun v3 Installer
# Run with: sudo bash install.sh

set -e

AUTORUN_USER="${SUDO_USER:-$(whoami)}"
DB_DIR="/var/lib/autorun"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

if [ "$EUID" -ne 0 ]; then
  error "Please run as root: sudo bash install.sh"
fi

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║   AutoRun v3  —  Installer       ║"
echo "  ╚══════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Installing from: $SCRIPT_DIR"
info "Running as user: $AUTORUN_USER"

# ── System dependencies ───────────────────────────────────────────────────────
info "Checking system dependencies..."
apt-get update -q

for pkg in python3 python3-pip python3-venv git curl; do
  if ! dpkg -l "$pkg" &>/dev/null; then
    info "Installing $pkg..."
    apt-get install -y -q "$pkg"
  fi
done

NODE_MAJOR=0
if command -v node &>/dev/null; then
  NODE_MAJOR=$(node --version | sed 's/v//' | cut -d. -f1)
fi
if [ "$NODE_MAJOR" -lt 18 ]; then
  info "Installing Node.js LTS..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - > /dev/null
  apt-get install -y -q nodejs
fi
success "Node $(node --version) / npm $(npm --version)"

# ── Python virtualenv ─────────────────────────────────────────────────────────
info "Setting up Python environment..."
VENV="$SCRIPT_DIR/backend/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/backend/requirements.txt"
success "Python dependencies installed"

# ── Build React frontend ──────────────────────────────────────────────────────
info "Building React frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run build
success "Frontend built → frontend/dist/"
cd "$SCRIPT_DIR"

# ── Database directory ────────────────────────────────────────────────────────
info "Creating database directory..."
mkdir -p "$DB_DIR"
chown "$AUTORUN_USER:$AUTORUN_USER" "$DB_DIR"
chmod 750 "$DB_DIR"
success "Database directory: $DB_DIR"

# ── First admin user ──────────────────────────────────────────────────────────
echo ""
echo "  Create your AutoRun admin account"
echo "  ──────────────────────────────────"
read -rp "  Username: " ADMIN_USER
while true; do
  read -rsp "  Password: " ADMIN_PASS
  echo ""
  read -rsp "  Confirm:  " ADMIN_PASS2
  echo ""
  if [ "$ADMIN_PASS" = "$ADMIN_PASS2" ]; then break
  else warn "Passwords do not match, try again."; fi
done

AUTORUN_DB_DIR="$DB_DIR" "$VENV/bin/python3" - <<PYEOF
import sys
sys.path.insert(0, '$SCRIPT_DIR/backend')
from database import init_db, create_first_user
init_db()
try:
    create_first_user('$ADMIN_USER', '$ADMIN_PASS')
    print('  User created.')
except ValueError as e:
    print(f'  Note: {e}')
PYEOF
success "Admin user '$ADMIN_USER' ready"

# ── Sudoers ───────────────────────────────────────────────────────────────────
info "Configuring sudoers for systemctl..."
cat > /etc/sudoers.d/autorun <<EOF
# AutoRun — systemctl permissions (no password)
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl start autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl enable autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl disable autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/tee /etc/systemd/system/autorun-*
$AUTORUN_USER ALL=(ALL) NOPASSWD: /bin/rm /etc/systemd/system/autorun-*
EOF
chmod 440 /etc/sudoers.d/autorun
success "Sudoers configured"

# ── Systemd service ───────────────────────────────────────────────────────────
info "Installing systemd service..."
cat > /etc/systemd/system/autorun.service <<EOF
[Unit]
Description=AutoRun v3 — Service Manager Dashboard
After=network.target

[Service]
Type=simple
User=$AUTORUN_USER
WorkingDirectory=$SCRIPT_DIR/backend
ExecStart=$VENV/bin/python3 $SCRIPT_DIR/backend/autorun.py
Environment="AUTORUN_DB_DIR=$DB_DIR"
Environment="AUTORUN_USER=$AUTORUN_USER"
Environment="AUTORUN_PORT=80"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable autorun
systemctl restart autorun
success "autorun service installed and started"

echo ""
echo -e "  ${GREEN}Installation complete!${NC}"
echo ""
echo "  Dashboard → http://localhost"
echo "  Logs      → journalctl -u autorun -f"
echo "  Stop      → sudo systemctl stop autorun"
echo ""
