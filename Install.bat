@echo off
SETLOCAL

REM Specifica il percorso del file TGeniusAI.exe
set TARGET_PATH=%~dp0TGeniusAI\TGeniusAI.exe

REM Specifica il percorso della cartella in cui vuoi creare il collegamento
set SHORTCUT_PATH=%~dp0

REM Nome del collegamento
set SHORTCUT_NAME=TGeniusAI.lnk

REM Percorso completo del collegamento
set SHORTCUT=%SHORTCUT_PATH%%SHORTCUT_NAME%

REM Creazione del file VBScript temporaneo per creare il collegamento
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\crea_collegamento.vbs"
echo sLinkFile = "%SHORTCUT%" >> "%TEMP%\crea_collegamento.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\crea_collegamento.vbs"
echo oLink.TargetPath = "%TARGET_PATH%" >> "%TEMP%\crea_collegamento.vbs"
echo oLink.Save >> "%TEMP%\crea_collegamento.vbs"

REM Esecuzione del file VBScript
cscript /nologo "%TEMP%\crea_collegamento.vbs"

REM Eliminazione del file VBScript temporaneo
del "%TEMP%\crea_collegamento.vbs"

echo Collegamento creato in %SHORTCUT_PATH%
ENDLOCAL
pause
