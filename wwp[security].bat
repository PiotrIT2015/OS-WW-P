@echo off
chcp 65001 > nul

rem Użycie py.exe jest bardziej niezawodne w Windows
rem %~dp0 to ścieżka do folderu, w którym znajduje się ten plik .bat
py "%~dp0main.py"

echo.
echo Skrypt zakończył działanie. Naciśnij dowolny klawisz...
pause > nul