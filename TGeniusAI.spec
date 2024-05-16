# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['src/TGeniusAI.py'],
             pathex=['.'],
             binaries=[],
             datas=[('res', 'res')],  # Assicurati di includere tutte le risorse necessarie
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
               name='TGeniusAI')
