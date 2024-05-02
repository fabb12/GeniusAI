# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['TGeniusAI.py'],
             pathex=['.'],
             binaries=[('C:/ffmpeg/bin/ffmpeg.exe', '.')],  # Aggiunge ffmpeg all'eseguibile
             datas=[('res', 'res')],  # Copia la cartella 'res' interamente nella root dell'eseguibile
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
           cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          exclude_binaries=True,
          name='TGeniusAI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )  # Cambia console=False se non vuoi una finestra console
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='TGeniusAI')
