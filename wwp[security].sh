#!/bin/bash

# Ten skrypt uruchamia główny plik Pythona.

# Odpowiednik '@echo off' nie jest potrzebny; to domyślne zachowanie w skryptach bash.
# Odpowiednik 'chcp 65001' (ustawienie kodowania UTF-8) również zazwyczaj nie jest konieczny,
# ponieważ nowoczesne systemy Linux i macOS domyślnie używają UTF-8.

# Użycie python3 jest standardem w nowoczesnych systemach uniksowych.
# $(dirname "$0") to ścieżka do folderu, w którym znajduje się ten plik .sh
python3 "$(dirname "$0")/main.py"

echo
echo "Skrypt zakończył działanie. Naciśnij dowolny klawisz, aby zamknąć..."
read -n 1 -s -r