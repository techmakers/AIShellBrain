#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to install a package
install_package() {
    echo -e "${GREEN}Installing $1...${NC}"
    sudo apt-get install -y $1
}

# Function to install a pip package
install_pip_package() {
    echo -e "${GREEN}Installing $1 via pip...${NC}"
    pip3 install $1
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

# List of pip dependencies
dependencies=("requests" "prompt_toolkit" "openai")

# Check and install pip dependencies
for dep in "${dependencies[@]}"
do
    if ! pip3 show $dep &> /dev/null
    then
        echo -e "${RED}$dep not found. Installing...${NC}"
        install_pip_package $dep
    fi
done

# Run the Python script
echo -e "${GREEN}Starting shellbrain.py...${NC}"
python3 shellbrain.py -y
