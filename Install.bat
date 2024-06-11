@echo off

REM Ottieni il percorso completo dello script .bat
set SCRIPT_DIR=%~dp0

REM Imposta il percorso di ffmpeg.exe
set FFMPEG_DIR=%SCRIPT_DIR%res\ffmpeg\bin

REM Aggiungi il percorso di ffmpeg.exe alla variabile PATH per l'utente corrente usando PowerShell
powershell -Command "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'User') + ';%FFMPEG_DIR%', 'User')"

REM Verifica che il percorso sia stato aggiunto
echo Verifica che il percorso di ffmpeg.exe sia stato aggiunto al PATH:
powershell -Command "[Environment]::GetEnvironmentVariable('PATH', 'User')" | find "%FFMPEG_DIR%"
if %errorlevel%==0 (
    echo Il percorso e' stato aggiunto con successo.
) else (
    echo Errore: il percorso non e' stato aggiunto.
)

pause
