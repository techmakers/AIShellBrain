#!/bin/bash

# Colori per l'output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funzione per installare un pacchetto
install_package() {
    echo -e "${GREEN}Installazione di $1...${NC}"
    sudo apt-get install -y $1
}

# Funzione per installare un pacchetto pip
install_pip_package() {
    echo -e "${GREEN}Installazione di $1 via pip...${NC}"
    pip3 install $1
}

# Verifica se Python 3 è installato
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}Python 3 non trovato. Installazione in corso...${NC}"
    install_package python3
fi

# Verifica se pip è installato
if ! command -v pip3 &> /dev/null
then
    echo -e "${RED}pip3 non trovato. Installazione in corso...${NC}"
    install_package python3-pip
fi

# Lista delle dipendenze pip
dependencies=("requests" "prompt_toolkit" "openai")

# Verifica e installa le dipendenze pip
for dep in "${dependencies[@]}"
do
    if ! pip3 show $dep &> /dev/null
    then
        echo -e "${RED}$dep non trovato. Installazione in corso...${NC}"
        install_pip_package $dep
    fi
done

# Esegui lo script Python
echo -e "${GREEN}Avvio di shell.py...${NC}"
python3 shell.py --keep
