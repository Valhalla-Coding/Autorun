#!/bin/bash
# AutoRun v2 Installation Script
# This script sets up AutoRun as a systemd service on Linux

set -e  # Exit on error

echo "======================================"
echo "  AutoRun v2 Installation"
echo "======================================"
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Don't run this script as root"
    echo "Run as regular user, will prompt for sudo when needed"
    exit 1
fi

# Get current user and directory
CURRENT_USER=$(whoami)
INSTALL_DIR=$(pwd)

echo "Installation Details:"
echo "  User: $CURRENT_USER"
echo "  Directory: $INSTALL_DIR"
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3 and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Python: $PYTHON_VERSION"
echo

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages || {
    echo "WARNING: pip install failed, trying with --user flag as fallback"
    pip3 install --user -r requirements.txt --break-system-packages
}
echo "✓ Dependencies installed"
echo

# Create sudoers rules
echo "Setting up sudo permissions..."
echo "This allows AutoRun to manage systemd services without password prompts"

sudo tee /etc/sudoers.d/autorun > /dev/null <<EOF
# AutoRun v2 sudoers configuration
# Allows AutoRun to manage systemd services
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl daemon-reload
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-enabled *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl show *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/systemd/system/autorun-*.service
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/systemd/system/autorun-*.service
EOF

sudo chmod 440 /etc/sudoers.d/autorun
echo "✓ Sudoers configuration created"
echo

# Create AutoRun systemd service
echo "Creating AutoRun systemd service..."

sudo tee /etc/systemd/system/autorun.service > /dev/null <<EOF
[Unit]
Description=AutoRun v2 Service Manager
Documentation=https://github.com/Valhalla-Coding/autorun
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/autorun.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security settings
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Systemd service file created"
echo

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✓ Systemd reloaded"
echo

# Enable and start AutoRun
echo "Enabling and starting AutoRun..."
sudo systemctl enable autorun
sudo systemctl start autorun
echo "✓ AutoRun service started"
echo

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet autorun; then
    echo "======================================"
    echo "  Installation Complete!"
    echo "======================================"
    echo
    echo "AutoRun v2 is now running!"
    echo
    echo "Dashboard: http://localhost"
    echo
    echo "Useful commands:"
    echo "  Status:  sudo systemctl status autorun"
    echo "  Logs:    sudo journalctl -u autorun -f"
    echo "  Stop:    sudo systemctl stop autorun"
    echo "  Restart: sudo systemctl restart autorun"
    echo
else
    echo "======================================"
    echo "  Installation Warning"
    echo "======================================"
    echo
    echo "AutoRun service was created but failed to start."
    echo "Check logs with: sudo journalctl -u autorun -xe"
    echo
    exit 1
fi
