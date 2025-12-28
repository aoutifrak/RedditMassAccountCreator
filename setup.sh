#!/bin/bash
#
# Setup script for Reddit Account Registration
# Installs all dependencies and prepares the environment
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Reddit Account Registration - Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider running as regular user.${NC}"
fi

# Step 1: Update system packages
echo -e "${GREEN}[1/5] Updating system packages...${NC}"
sudo apt-get update

# Step 2: Install system dependencies
echo -e "${GREEN}[2/5] Installing system dependencies...${NC}"
sudo apt-get install -y python3 python3-full python3-pip python3-venv xvfb curl wget

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Step 3: Create virtual environment
echo -e "${GREEN}[3/5] Setting up Python virtual environment...${NC}"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Recreating...${NC}"
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Step 4: Install Python dependencies
echo -e "${GREEN}[4/5] Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Install Playwright Firefox browser
echo -e "${GREEN}Installing Playwright Firefox browser...${NC}"
playwright install --with-deps firefox

# Step 5: Create required directories
echo -e "${GREEN}[5/5] Creating required directories...${NC}"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/user-data-dir"

# Make scripts executable
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/reddit_register.py"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add your proxies to proxy.txt (format: host:port or host:port:user:password)"
echo "2. Run the script with: ./run.sh"
echo "   Or: ./run.sh 3  (to run 3 instances)"
echo ""
echo -e "${YELLOW}Files:${NC}"
echo "  proxy.txt              - Add your proxies here"
echo "  bad_proxy.txt          - Failed proxies (auto-managed)"
echo "  data/registration_success.txt - Registered accounts"
echo "  logs/                  - Instance logs"
echo ""
echo -e "${GREEN}To activate the virtual environment manually:${NC}"
echo "  source venv/bin/activate"
echo ""
