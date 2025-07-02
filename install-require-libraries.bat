@echo off
chcp 65001 > nul
call pip install -r requirements.txt
echo.
echo Instalacja zakończona. Naciśnij dowolny klawisz, aby kontynuować...
pause > nul