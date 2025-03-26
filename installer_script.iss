; Script di Inno Setup per installare GeniusAI senza richiedere privilegi di amministratore
#define MyAppVersion "1.5.7" ; Definisci qui la versione del programma

[Setup]
; Nome del programma che verrà visualizzato nel pannello di controllo
AppName=GeniusAI
; Versione del programma
AppVersion={#MyAppVersion}
; Nome completo con versione
AppVerName=GeniusAI {#MyAppVersion}
; Directory di destinazione (installazione nella cartella AppData locale dell'utente)
DefaultDirName={userappdata}\GeniusAI
; Nome del file di output
OutputBaseFilename=Setup_GeniusAI_v{#MyAppVersion}
; Directory di output per il file di setup
OutputDir=userdocs:Inno Setup Output
; Non richiedere privilegi di amministratore
PrivilegesRequired=lowest
; Icona del programma
SetupIconFile=dist\TGeniusAI\res\eye.ico
; Registrazione automatica del programma nel pannello di controllo
UninstallDisplayIcon={app}\res\eye.ico
; Opzione per chiudere le finestre applicative durante l'installazione
CloseApplications=yes
; Abilita il logging del setup per la risoluzione dei problemi
SetupLogging=yes

[Files]
; File principale dell'applicazione
Source: "dist\TGeniusAI\TGeniusAI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Copia la cartella ffmpeg e tutte le sue sottocartelle
Source: "dist\TGeniusAI\ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copia la cartella dei prompt
Source: "dist\TGeniusAI\prompts\*"; DestDir: "{app}\prompts"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copia la cartella delle icone e risorse
Source: "dist\TGeniusAI\res\*"; DestDir: "{app}\res"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copia eventuali file di configurazione o dati aggiuntivi
Source: "dist\TGeniusAI\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TGeniusAI\KNOW_ISSUES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TGeniusAI\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TGeniusAI\contatti_teams.txt"; DestDir: "{app}"; Flags: ignoreversion

; Includi la cartella _internal con PyQt6 e le librerie necessarie
Source: "dist\TGeniusAI\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Aggiungi il file version_info.txt
Source: "dist\TGeniusAI\version_info.txt"; DestDir: "{app}"; Flags: ignoreversion

; Aggiungi il file .env nella root
Source: "dist\TGeniusAI\.env"; DestDir: "{app}"; Flags: ignoreversion

; Copia il file Python di base (necessario per PyInstaller)
Source: "dist\TGeniusAI\python*.dll"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Crea directory per dati generati dall'applicazione
Name: "{app}\screenrecorder"; Flags: uninsneveruninstall

[Icons]
; Crea un'icona sul desktop per l'eseguibile principale
Name: "{userdesktop}\GeniusAI"; Filename: "{app}\TGeniusAI.exe"; IconFilename: "{app}\res\eye.ico"

; Crea un'icona nel menu Start per l'eseguibile principale
Name: "{group}\GeniusAI"; Filename: "{app}\TGeniusAI.exe"; IconFilename: "{app}\res\eye.ico"

[Run]
; Avvia l'applicazione al termine dell'installazione
Filename: "{app}\TGeniusAI.exe"; Description: "Avvia GeniusAI"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Rimuovi i file generati dall'applicazione durante la disinstallazione
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\dock_settings.json"
Type: filesandordirs; Name: "{app}\console_log.txt"

[Code]
// Funzione per verificare se l'applicazione è in esecuzione prima dell'installazione
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Prova a terminare l'applicazione se è in esecuzione
  Exec('taskkill.exe', '/F /IM TGeniusAI.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True; // Continua con l'installazione
end;