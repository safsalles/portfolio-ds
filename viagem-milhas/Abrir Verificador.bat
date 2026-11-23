@echo off
title Verificador de voos
cd /d "%~dp0"
echo Abrindo o Verificador de voos...
echo Nao feche esta janela enquanto estiver usando. Para encerrar, feche-a.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\app.ps1"
echo.
echo O Verificador foi encerrado. Se apareceu algum erro acima, copie o texto e me mande.
pause
