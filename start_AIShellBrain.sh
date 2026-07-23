#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Function to install a package
install_package() {
    echo -e "${GREEN}Installing $1...${NC}"
    sudo apt-get install -y "$1"
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}Python 3 not found. Installing...${NC}"
    install_package python3
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo -e "${RED}pip3 not found. Installing...${NC}"
    install_package python3-pip
fi

# Install Python dependencies from requirements.txt
echo -e "${GREEN}Installing dependencies from requirements.txt...${NC}"
pip3 install -r requirements.txt

# Create .env from the example on first run
if [ ! -f .env ] && [ -f .env.example ]; then
    echo -e "${GREEN}Creating .env from .env.example. Edit it to set your provider/API key.${NC}"
    cp .env.example .env
fi

# Run ShellBrain
echo -e "${GREEN}Starting ShellBrain...${NC}"
python3 shellbrain.py "$@"
