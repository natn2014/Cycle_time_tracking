#!/bin/bash
# Installation script for Cycle Time Tracker on Raspberry Pi 5
# Usage: chmod +x install.sh && ./install.sh

set -e

echo "=========================================="
echo "Cycle Time Tracker - Installation Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
    echo "Continuing anyway..."
fi

# Get installation directory
INSTALL_DIR="${1:-.}"
APP_USER="${2:-$USER}"

echo -e "${BLUE}Installation directory: $INSTALL_DIR${NC}"
echo -e "${BLUE}Application user: $APP_USER${NC}"
echo ""

# Step 1: Update system packages
echo -e "${BLUE}[1/6] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install system dependencies
echo -e "${BLUE}[2/6] Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libjasper1 \
    libharfbuzz0b \
    libwebp6 \
    libtiff5 \
    libopenjp2-7 \
    libatlas-base-dev \
    libagg2 \
    libcairo2 \
    libharfbuzz0b \
    libwebp6

echo -e "${GREEN}✓ System dependencies installed${NC}"

# Step 3: Create Python virtual environment (optional but recommended)
echo -e "${BLUE}[3/6] Setting up Python environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists, skipping...${NC}"
fi

# Activate venv
source "$INSTALL_DIR/venv/bin/activate"

# Step 4: Install Python dependencies
echo -e "${BLUE}[4/6] Installing Python dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r "$INSTALL_DIR/requirements.txt"
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Step 5: Create systemd service
echo -e "${BLUE}[5/6] Creating systemd service...${NC}"

SERVICE_FILE="/etc/systemd/system/cycle-tracker.service"
SCRIPT_DIR="$(cd "$INSTALL_DIR" && pwd)"

# Create service file
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Cycle Time Tracker
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd service created${NC}"

# Step 6: Display next steps
echo -e "${BLUE}[6/6] Installation complete!${NC}"
echo ""
echo -e "${GREEN}========== NEXT STEPS ==========${NC}"
echo ""
echo "1. Enable auto-start on boot:"
echo "   ${YELLOW}sudo systemctl enable cycle-tracker${NC}"
echo ""
echo "2. Start the service now:"
echo "   ${YELLOW}sudo systemctl start cycle-tracker${NC}"
echo ""
echo "3. Check service status:"
echo "   ${YELLOW}sudo systemctl status cycle-tracker${NC}"
echo ""
echo "4. View live logs:"
echo "   ${YELLOW}journalctl -u cycle-tracker -f${NC}"
echo ""
echo "5. Stop the service:"
echo "   ${YELLOW}sudo systemctl stop cycle-tracker${NC}"
echo ""
echo "6. Restart the service:"
echo "   ${YELLOW}sudo systemctl restart cycle-tracker${NC}"
echo ""
echo -e "${GREEN}==============================${NC}"
echo ""
echo "Configuration file: $INSTALL_DIR/config.yaml"
echo "Service file: $SERVICE_FILE"
echo "Data directory: $INSTALL_DIR"
echo ""
