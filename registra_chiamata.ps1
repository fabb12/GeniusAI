# Script v2: Legge le impostazioni da un file config.json

# --- Caricamento Configurazione ---
$script_path = $PSScriptRoot
$config_file = Join-Path $script_path "config.json"

# Impostazioni predefinite (in caso il file non esista o manchino delle chiavi)
$default_config = @{
    percorso_output = "$env:USERPROFILE\\Desktop"
    nome_file_output = "registrazione_default.mkv"
    parole_chiave_microfono = @("Bluetooth", "Headset", "Cuffie", "Microfono")
    nome_stereo_mix = "Stereo Mix|Missaggio stereo" # Cerca entrambi i nomi
}

if (Test-Path $config_file) {
    Write-Host "✅ Trovato file di configurazione: $config_file"
    try {
        $config = Get-Content $config_file -Raw | ConvertFrom-Json
        # Unisci le configurazioni, dando priorità a quelle del file
        $final_config = $default_config.Clone()
        $config.psobject.Properties | ForEach-Object { $final_config[$_.Name] = $_.Value }
    } catch {
        Write-Warning "⚠️ Errore nella lettura del file config.json. Uso le impostazioni predefinite."
        $final_config = $default_config
    }
} else {
    Write-Host "ℹ️ Nessun file config.json trovato. Uso le impostazioni predefinite."
    $final_config = $default_config
}

# Espandi le variabili d'ambiente nel percorso (es. %USERPROFILE%)
$output_path = [System.Environment]::ExpandEnvironmentVariables($final_config.percorso_output)
if (-not (Test-Path $output_path)) {
    Write-Host "La cartella di output non esiste, la creo: $output_path"
    New-Item -ItemType Directory -Force -Path $output_path | Out-Null
}
$output_file = Join-Path $output_path $final_config.nome_file_output
# --- Fine Configurazione ---


Write-Host "Cerco i dispositivi audio con le impostazioni fornite..."

try {
    $device_list = ffmpeg -list_devices true -f dshow -i dummy 2>&1
} catch {
    Write-Error "Errore nell'esecuzione di ffmpeg. Assicurati che sia installato e nel PATH."
    exit
}

# Cerca "Stereo Mix" usando il nome dalla configurazione
$stereo_mix_pattern = '"(.*?(' + ($final_config.nome_stereo_mix -join '|') + ').*?)"'
$stereo_mix_device = $device_list | Select-String -Pattern $stereo_mix_pattern | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1

# Cerca il microfono usando le parole chiave dalla configurazione
$mic_keywords_pattern = $final_config.parole_chiave_microfono -join '|'
$mic_pattern = '"(.*?((Microphone)|(Microfono)).*?(' + $mic_keywords_pattern + ').*?)"'
$microphone_device = $device_list | Select-String -Pattern $mic_pattern -AllMatches | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1

# Se non trova un microfono specifico, cerca il primo microfono generico
if (-not $microphone_device) {
    Write-Host "Nessun microfono specifico trovato con le parole chiave, cerco un microfono generico..."
    $mic_generic_pattern = '"(.*?((Microphone)|(Microfono)).*?)"'
    $microphone_device = $device_list | Select-String -Pattern $mic_generic_pattern | Where-Object { $_ -notmatch $final_config.nome_stereo_mix } | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1
}


# Controlli finali
if (-not $stereo_mix_device) {
    Write-Error "Dispositivo Stereo Mix non trovato con il nome '$($final_config.nome_stereo_mix)'. Controlla il nome nel file config.json e nelle impostazioni audio di Windows."
    exit
}
if (-not $microphone_device) {
    Write-Error "Nessun microfono trovato. Controlla che sia connesso."
    exit
}


Write-Host "✅ Dispositivo di sistema trovato: $stereo_mix_device"
Write-Host "✅ Microfono trovato: $microphone_device"
Write-Host "---"
Write-Host "▶️ Avvio della registrazione... Premi 'q' nella finestra di ffmpeg per terminare."

$ffmpeg_args = @(
    "-f", "dshow",
    "-i", "audio=$microphone_device",
    "-f", "dshow",
    "-i", "audio=$stereo_mix_device",
    "-filter_complex", "[0:a][1:a]amerge=inputs=2[a]",
    "-ac", "2",
    "-y",
    "$output_file"
)

try {
    Start-Process -FilePath "ffmpeg" -ArgumentList $ffmpeg_args -Wait
    Write-Host "✅ Registrazione terminata e salvata in: $output_file"
} catch {
    Write-Error "Impossibile avviare la registrazione con ffmpeg."
}
