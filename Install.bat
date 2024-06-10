@echo off
setlocal

:: Ottieni la directory corrente
set "currentDir=%~dp0"
set "currentDir=%currentDir:~0,-1%"

:: Percorso della cartella superiore
set "parentDir=%currentDir%\.."
set "parentDir=%parentDir:~0,-1%"

:: Percorso della cartella TGeniusAI
set "tgFolder=%currentDir%\TGeniusAI"

:: Imposta il percorso dell'eseguibile
set "exePath=%tgFolder%\TGeniusAI.exe"

:: Nome del collegamento
set "shortcutName=TGeniusAI.lnk"

:: Percorso completo del collegamento nella cartella TGeniusAI
set "tgShortcutPath=%tgFolder%\%shortcutName%"

:: Percorso completo del collegamento nella cartella superiore
set "parentShortcutPath=%parentDir%\%shortcutName%"

:: Crea il collegamento nella cartella TGeniusAI utilizzando PowerShell
powershell -command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%tgShortcutPath%'); $s.TargetPath = '%exePath%'; $s.WorkingDirectory = '%tgFolder%'; $s.Save()"

:: Sposta il collegamento nella cartella superiore
move "%tgShortcutPath%" "%parentShortcutPath%"

echo Collegamento creato e spostato con successo: %parentShortcutPath%

endlocal
pause
