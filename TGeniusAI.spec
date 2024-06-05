# -*- mode: python ; coding: utf-8 -*-

import shutil
import os

block_cipher = None

a = Analysis(['src/TGeniusAI.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                 ('res', 'res'),  # Assicurati di includere tutte le risorse necessarie
                 ('Readme.txt', '.'),  # Aggiungi Readme.txt nella cartella TGeniusAI
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
             noarchive=True)  # Modifica qui

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher,
          noarchive=True)  # E anche qui

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='TGeniusAI',
          debug=False,
          strip=False,
          upx=True,
          console=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name='TGeniusAI',
               strip=False,
               upx=True,
               console=True)

# Script personalizzato per spostare i file un livello sopra
def move_files_up():
    dist_dir = os.path.join(os.getcwd(), 'dist', 'TGeniusAI')
    files_to_move = ['Readme.txt', 'install.bat']
    for file_name in files_to_move:
        src_path = os.path.join(dist_dir, file_name)
        dest_path = os.path.join(dist_dir, '..', file_name)
        if os.path.exists(src_path):
            shutil.move(src_path, dest_path)

move_files_up()
