#!/bin/bash

# Ustawienie kodowania na UTF-8 (w bashu zwykle domyślne)
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Instalacja pakietów z requirements.txt
pip install -r requirements.txt

# Komunikat końcowy
echo
echo "Instalacja zakończona. Naciśnij Enter, aby kontynuować..."
read
