#!/bin/bash
# Minimal installation script for Cycle Time Tracker on Raspberry Pi 5
# Use this if install.sh fails due to missing packages
# Usage: chmod +x install_minimal.sh && ./install_minimal.sh

set -e

echo "=========================================="
echo "Cycle Time Tracker - Minimal Installation"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get installation directory
INSTALL_DIR="${1:-.}"
APP_USER="${2:-$USER}"

echo -e "${BLUE}Installation directory: $INSTALL_DIR${NC}"
echo -e "${BLUE}Application user: $APP_USER${NC}"
echo ""

# Step 1: Update system
echo -e "${BLUE}[1/4] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install ONLY essential packages
echo -e "${BLUE}[2/4] Installing essential Python + OpenCV...${NC}"
echo "Installing: python3-pip, python3-opencv, python3-venv"
sudo apt-get install -y python3-pip python3-opencv python3-venv

# If python3-opencv fails, try just pip install opencv-python
if ! python3 -c "import cv2" 2>/dev/null; then
    echo -e "${YELLOW}python3-opencv not available, will use pip instead${NC}"
fi

echo -e "${GREEN}✓ Python environment ready${NC}"

# Step 3: Setup Python environment
echo -e "${BLUE}[3/4] Setting up Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

source "$INSTALL_DIR/venv/bin/activate"

# Step 4: Install Python dependencies
echo -e "${BLUE}[4/4] Installing Python dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r "$INSTALL_DIR/requirements.txt"

echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""
echo -e "${GREEN}========== INSTALLATION COMPLETE ==========${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Test the installation:"
echo "   ${YELLOW}cd $INSTALL_DIR && source venv/bin/activate && python main.py${NC}"
echo "   (Press Q to quit)"
echo ""
echo "2. (Optional) Set up systemd auto-start:"
echo "   ${YELLOW}sudo cp $INSTALL_DIR/cycle-tracker.service /etc/systemd/system/${NC}"
echo "   ${YELLOW}sudo systemctl daemon-reload${NC}"
echo "   ${YELLOW}sudo systemctl enable cycle-tracker${NC}"
echo "   ${YELLOW}sudo systemctl start cycle-tracker${NC}"
echo ""
echo "3. View logs:"
echo "   ${YELLOW}journalctl -u cycle-tracker -f${NC}"
echo ""
