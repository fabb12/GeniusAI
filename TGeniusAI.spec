# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['TGeniusAI.py'],
             pathex=['.'],
             binaries=[('./ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin')],
             datas=[('res', 'res'), ('./ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin')],  # Include ffmpeg e risorse
             hiddenimports=[
                 'cv2', 'moviepy', 'numpy', 'pydub', 'PyQt6.QtCore',
                 'PyQt6.QtGui', 'PyQt6.QtWidgets'  # Aggiungi altre librerie nascoste come necessario
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PyQt5'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='TGeniusAI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,  # Modifica a seconda se desideri una finestra di console o no
          onefile=False)  # Crea una directory di distribuzione invece di un file unico

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='TGeniusAI')
