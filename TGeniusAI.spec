# -*- mode: python ; coding: utf-8 -*-

import shutil
import os
import re
import zipfile

block_cipher = None

a = Analysis(
    ['src/TGeniusAI.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('res', 'res'),  # Includi la cartella delle risorse
        ('Readme.md', '.'),  # Aggiungi Readme.md nella cartella TGeniusAI
        ('install.bat', '.'),  # Aggiungi install.bat nella cartella TGeniusAI
        ('ffmpeg.exe', '.')  # Aggiungi ffmpeg.exe nella cartella TGeniusAI
    ],
    hiddenimports=[
        'cv2', 'moviepy', 'numpy', 'pydub', 'PyQt6.QtCore',
        'PyQt6.QtGui', 'PyQt6.QtWidgets'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
    noarchive=True
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TGeniusAI',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='res/eye.ico'  # Specifica il percorso dell'icona
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='TGeniusAI',
    strip=False,
    upx=True,
    console=True
)

# Script personalizzato per spostare i file nella cartella corretta e creare un file ZIP
def move_files_up_and_create_zip():
    dist_dir = os.path.join(os.getcwd(), 'dist', 'TGeniusAI')
    release_dir = os.path.join(os.getcwd(), 'Release')

    # Crea la cartella Release se non esiste
    os.makedirs(release_dir, exist_ok=True)

    files_to_move = ['Readme.md', 'install.bat', 'ffmpeg.exe']
    folders_to_move = ['res']

    for file_name in files_to_move:
        src_path = os.path.join(dist_dir, file_name)
        dest_path = os.path.join(release_dir, file_name)
        if os.path.exists(src_path):
            shutil.move(src_path, dest_path)

    for folder_name in folders_to_move:
        src_path = os.path.join(dist_dir, folder_name)
        dest_path = os.path.join(release_dir, folder_name)
        if os.path.exists(src_path):
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.move(src_path, dest_path)

    # Estrai la versione del software dal codice principale
    version_pattern = re.compile(r'self\.version_major = (\d+).*self\.version_minor = (\d+).*self\.version_patch = (\d+)', re.DOTALL)
    with open('src/TGeniusAI.py', 'r') as f:
        content = f.read()
    match = version_pattern.search(content)
    if match:
        version = f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"
    else:
        version = "v0.0.0"

    # Crea un file ZIP contenente tutti i file nella cartella Release
    zip_file_path = os.path.join(release_dir, f"TGeniusAI_{version}.zip")
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                if file != os.path.basename(zip_file_path):  # Evita di aggiungere il file ZIP a se stesso
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, release_dir)
                    zipf.write(file_path, arcname)

move_files_up_and_create_zip()
