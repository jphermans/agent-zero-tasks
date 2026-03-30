#!/bin/bash
# E-Ink Dashboard - Raspberry Pi Setup Script
# Run this on a fresh Raspberry Pi OS installation
# Usage: chmod +x install.sh && ./install.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
SERVICE_NAME="eink-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Check running on Raspberry Pi
info "Checking system..."
if [ ! -f /proc/device-tree/model ]; then
    warn "Not running on a Raspberry Pi - some hardware features will be unavailable"
    warn "Continuing in simulation-compatible mode..."
fi

# Update system
info "Updating system packages..."
sudo apt-get update -qq

# Install system dependencies
info "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-pil \
    fonts-dejavu-core \
    libopenjp2-7 \
    libtiff5 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    i2c-tools \
    spi-tools \
    git

# Enable SPI interface (needed for Inky display)
info "Enabling SPI interface..."
if command -v raspi-config &> /dev/null; then
    sudo raspi-config nonint do_spi 0 2>/dev/null || warn "Could not enable SPI via raspi-config"
    info "SPI interface enabled"
else
    warn "raspi-config not found - make sure SPI is enabled manually"
fi

# Create virtual environment
info "Creating Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

# Install Python dependencies
info "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install core requirements
pip install Pillow>=10.0.0 PyYAML>=6.0 requests>=2.31.0

# Try installing hardware libraries
info "Installing Raspberry Pi hardware libraries..."
pip install inky>=1.4.0 gpiozero>=2.0 2>/dev/null || warn "Hardware libraries not installed (OK for development)"

# Optional: Google Calendar
read -p "Install Google Calendar support? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    info "Google Calendar libraries installed"
fi

# Create config from example if not exists
if [ ! -f "${PROJECT_DIR}/config.yaml" ]; then
    cp "${PROJECT_DIR}/config.example.yaml" "${PROJECT_DIR}/config.yaml"
    info "Created config.yaml from template - please edit with your API keys"
else
    info "config.yaml already exists, keeping it"
fi

# Create cache directory
mkdir -p "${PROJECT_DIR}/cache"

# Create sample tasks if not exists
if [ ! -f "${PROJECT_DIR}/tasks.json" ]; then
    cat > "${PROJECT_DIR}/tasks.json" << 'TASKS'
[
    {"text": "Set up e-ink dashboard", "done": true, "priority": "high"},
    {"text": "Configure weather API key", "done": false, "priority": "high"},
    {"text": "Add Google Calendar credentials", "done": false, "priority": "medium"},
    {"text": "Set up IMAP email access", "done": false, "priority": "medium"},
    {"text": "Connect Home Assistant", "done": false, "priority": "low"},
    {"text": "Customize dashboard layout", "done": false, "priority": "low"}
]
TASKS
    info "Created sample tasks.json"
fi

# Test run
info "Testing dashboard in render-once mode..."
cd "${PROJECT_DIR}"
python main.py -s -r --log-level INFO && info "Test render successful!" || warn "Test render had issues (check output above)"

# Ask about systemd service
read -p "Install as systemd service (auto-start on boot)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > /tmp/${SERVICE_NAME}.service << SVC
[Unit]
Description=E-Ink Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${PROJECT_DIR}
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/main.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC
    sudo mv /tmp/${SERVICE_NAME}.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    info "Systemd service installed and enabled"
    info "Start with: sudo systemctl start ${SERVICE_NAME}"
    info "Logs with: journalctl -u ${SERVICE_NAME} -f"
fi

echo ""
info "==================================="
info "Setup Complete!"
info "==================================="
echo ""
echo "Next steps:"
echo "  1. Edit config.yaml with your API keys"
echo "  2. Run: python main.py -s        (simulation mode)"
echo "  3. Run: python main.py            (on Pi with display)"
echo "  4. Run: python main.py -k         (kiosk mode)"
echo ""
echo "Button controls:"
echo "  A = Previous view"
echo "  B = Next view"
echo "  C = Force refresh"
echo "  D = Toggle kiosk mode"
echo ""
