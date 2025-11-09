from PyInstaller.utils.hooks import collect_all

# Estrae tutti i sottomoduli, i file di dati e i file binari da torch
datas, binaries, hiddenimports = collect_all('torch')
