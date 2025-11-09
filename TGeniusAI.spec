# -*- mode: python ; coding: utf-8 -*-
import shutil
import os
import re
import zipfile
import datetime
import sys
import platform
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

current_dir = os.getcwd()

# --- INIZIO CODICE PER PLAYWRIGHT ---
# def find_playwright_browsers():
#     """Trova il percorso della cartella dei browser Playwright."""
#     system = platform.system()
#     if system == 'Windows':
#         base_path = os.getenv('LOCALAPPDATA')
#     elif system == 'Darwin':
#         base_path = os.path.expanduser('~/Library/Caches')
#     else:
#         base_path = os.path.expanduser('~/.cache')

#     if not base_path:
#         raise EnvironmentError("Impossibile determinare la cartella cache/appdata dell'utente.")

#     browser_path = os.path.join(base_path, 'ms-playwright')

#     if not os.path.exists(browser_path):
#         raise FileNotFoundError(
#             f"Cartella browser Playwright non trovata in '{browser_path}'. "
#             "Assicurati di aver eseguito 'playwright install' prima di compilare."
#         )
#     print(f"Trovata cartella browser Playwright in: {browser_path}")
#     return browser_path

# try:
#     playwright_browser_dir = find_playwright_browsers()
#     playwright_datas = [(playwright_browser_dir, 'ms-playwright')]
#     print("Inclusione dati Playwright configurata.")
# except (FileNotFoundError, EnvironmentError) as e:
#     print(f"ERRORE: {e}")
#     print("Il build continuerà senza i browser Playwright, ma l'Agent Browser non funzionerà.")
playwright_datas = []

# --- FINE CODICE PER PLAYWRIGHT ---


# Collect all submodules and data files of required packages
hiddenimports = (
    collect_submodules('cv2') +
    collect_submodules('moviepy') +
    collect_submodules('numpy') +
    collect_submodules('pydub') +
    collect_submodules('PyQt6') +
    collect_submodules('pycountry') +
    collect_submodules('speech_recognition') +
    collect_submodules('pydantic') +
    collect_submodules('whisper') +
    collect_submodules('torch') +
    collect_submodules('torchvision') +
    collect_submodules('torchaudio') +
    # collect_submodules('playwright') +
    # collect_submodules('browser_use') +
    # ['playwright.sync_api', 'playwright.async_api'] +
    # Internal project modules
    ['src.ui', 'src.ui.CustomDock', 'src.ui.CustomSlider', 'src.ui.CustVideoWidget',
     'src.ui.CustomTextEdit', 'src.ui.ScreenButton', 'src.ui.SplashScreen', 'src.ui.VideoOverlay', 'src.ui.CropOverlay',
     'src.services', 'src.managers', 'src.recorder', 'src.config']
)

datas = (
    collect_data_files('cv2') +
    collect_data_files('moviepy') +
    collect_data_files('numpy') +
    collect_data_files('pydub') +
    collect_data_files('PyQt6') +
    collect_data_files('pycountry') +
    collect_data_files('speech_recognition') +
    collect_data_files('whisper') +
    collect_data_files('torch') +
    collect_data_files('torchvision') +
    collect_data_files('torchaudio')
)

# Additional DLLs and plugins for PyQt6
extra_dll_paths = [
    os.path.join(current_dir, 'venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')
]
extra_datas = collect_data_files('PyQt6', subdir='Qt6/plugins')

datas += extra_datas

# Explicitly add project modules
datas += [
    (os.path.join(current_dir, 'src', 'ui'), 'src/ui'),
    (os.path.join(current_dir, 'src', 'services'), 'src/services'),
    (os.path.join(current_dir, 'src', 'managers'), 'src/managers'),
    (os.path.join(current_dir, 'src', 'recorder'), 'src/recorder'),
    (os.path.join(current_dir, 'src', 'config.py'), 'src')
]

binaries = []
for dll_path in extra_dll_paths:
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))

# ====================================================================================
# === INIZIO CORREZIONE PER ERRORE SQLITE3 ===
# Aggiunge esplicitamente la DLL di SQLite3 dall'ambiente Python in uso
# per evitare conflitti con versioni di sistema obsolete che causano l'errore
# "ImportError: DLL load failed while importing _sqlite3".
sqlite_dll_path = os.path.join(sys.prefix, 'DLLs', 'sqlite3.dll')
if os.path.exists(sqlite_dll_path):
    print(f"Inclusione esplicita di: {sqlite_dll_path}")
    binaries.append((sqlite_dll_path, '.'))
else:
    print("ATTENZIONE: Non è stato possibile trovare sqlite3.dll. L'eseguibile potrebbe non funzionare.")
# === FINE CORREZIONE PER ERRORE SQLITE3 ===
# ====================================================================================


# Resource files
resource_files = [
    (os.path.join(current_dir, '.env'), '.'),
    (os.path.join(current_dir, 'README.md'), '.'),
    (os.path.join(current_dir, 'CHANGELOG.md'), '.'),
    (os.path.join(current_dir, 'KNOW_ISSUES.md'), '.'),
    (os.path.join(current_dir, 'src', 'prompts'), 'prompts'),
    (os.path.join(current_dir, 'src', 'res'), 'res'),
    (os.path.join(current_dir, 'src', 'res', 'splash_images'), 'res/splash_images'),
    (os.path.join(current_dir, 'src', 'res', 'music'), 'res/music'),
    (os.path.join(current_dir, 'src', 'res', 'eye.ico'), 'res'),
    (os.path.join(current_dir, 'src', 'res', 'eye.png'), 'res'),
    (os.path.join(current_dir, 'src', 'res', 'watermark.png'), 'res'),
    (os.path.join(current_dir, 'src', 'res', '*.png'), 'res'),
    (os.path.join(current_dir, 'src', 'contatti_teams.txt'), '.'),
]

a = Analysis(
    ['src/TGeniusAI.py'],
    pathex=[
        '.',
        'src',
        os.path.join(current_dir, 'venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')
    ],
    binaries=binaries,
    datas=resource_files + datas + playwright_datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6.Qt3DAnimation',
        'PyQt6.Qt3DCore',
        'PyQt6.Qt3DExtras',
        'PyQt6.Qt3DInput',
        'PyQt6.Qt3DLogic',
        'PyQt6.Qt3DRender',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineQuick',
        'PyQt6.QtQuick3D',
        'PyQt6.QtSql',
        'PyQt6.QtNetworkAuth',
        'PyQt6.QtWebSockets',
        'PyQt6.QtScxml',
        'PyQt6.QtTest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
    noarchive=False
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
    icon=os.path.join('src', 'res', 'eye.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='TGeniusAI',
    strip=False,
    upx=True,
    console=False
)


# ============================================================
# DEFINIZIONI DELLE FUNZIONI AUSILIARIE (DEVONO STARE QUI)
# ============================================================

def create_version_info():
    """Crea il file version_info.txt e restituisce il percorso e la versione."""
    # Extract version from the source code
    version_pattern = re.compile(r"self\.setWindowTitle\(f\"GeniusAI - (v[\d\.]+).*Build Date: (.*?)\"\)")
    try:
        with open('src/TGeniusAI.py', 'r', encoding='utf-8') as f:
            content = f.read()
        match = version_pattern.search(content)
        if match:
            version = match.group(1)
        else:
            print("Warning: Version pattern not found in TGeniusAI.py. Using fallback.")
            version = "v0.0.0"
    except Exception as e:
        print(f"Error extracting version: {e}")
        version = "v0.0.0"

    # Get the current date for build date
    build_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the version_info.txt file content
    version_info_content = f"Version: {version}\nBuild Date: {build_date}\n"
    version_info_path = os.path.join(current_dir, 'version_info.txt') # Create in project root

    with open(version_info_path, 'w') as version_file:
        version_file.write(version_info_content)

    return version_info_path, version

def post_build_steps():
    """Esegue tutti i passaggi post-build per organizzare il pacchetto di distribuzione."""
    dist_dir = os.path.join(current_dir, 'dist')
    tgeniusai_dir = os.path.join(dist_dir, 'TGeniusAI')
    internal_dir = os.path.join(tgeniusai_dir, '_internal') # Default location for collected datas

    # Create version info file and get path/version
    version_info_path, version = create_version_info()

    # Ensure the main distribution directory exists
    os.makedirs(tgeniusai_dir, exist_ok=True)

    # Move version_info.txt to the root of the distribution
    if os.path.exists(version_info_path):
        target_path = os.path.join(tgeniusai_dir, 'version_info.txt')
        try:
            shutil.copy2(version_info_path, target_path) # Copy first
            print(f"Version info copied to: {target_path}")
            os.remove(version_info_path) # Then remove original
        except Exception as e:
            print(f"Error copying/removing version info: {e}")
    else:
        print("Warning: version_info.txt was not found after creation attempt.")

    # Explicitly copy the ffmpeg directory
    src_ffmpeg_path = os.path.join(current_dir, 'src', 'ffmpeg')
    dest_ffmpeg_path = os.path.join(tgeniusai_dir, 'ffmpeg')

    if os.path.exists(src_ffmpeg_path):
        print(f"Copying ffmpeg directory from {src_ffmpeg_path} to {dest_ffmpeg_path}")
        if os.path.exists(dest_ffmpeg_path):
            shutil.rmtree(dest_ffmpeg_path) # Remove destination if it exists
        try:
            shutil.copytree(src_ffmpeg_path, dest_ffmpeg_path)
            print(f"Successfully copied ffmpeg directory")
        except Exception as e:
             print(f"ERROR copying ffmpeg directory: {e}")
    else:
        print(f"WARNING: Source ffmpeg directory not found at {src_ffmpeg_path}")

    # Move data collected by PyInstaller from _internal to the correct locations
    # List of items expected in _internal that need moving/copying
    items_to_handle = {
        'res': 'res',
        'prompts': 'prompts',
        # 'ms-playwright': 'ms-playwright', # Playwright browsers
        # 'browser_use': 'browser_use',    # Data files from browser_use lib
        # Add other collected data subdirs here if necessary
        '.env': '.',
        'README.md': '.',
        'CHANGELOG.md': '.',
        'KNOW_ISSUES.md': '.',
        'contatti_teams.txt': '.'
    }

    if os.path.exists(internal_dir):
        print(f"Processing items in {internal_dir}...")
        for item_name, target_subdir in items_to_handle.items():
            internal_item_path = os.path.join(internal_dir, item_name)
            target_path = os.path.join(tgeniusai_dir, target_subdir)

            if os.path.exists(internal_item_path):
                try:
                    # Ensure target directory exists if it's a subdir
                    if target_subdir != '.':
                         os.makedirs(target_path, exist_ok=True)

                    # Decide target based on whether it's root or subdir
                    final_target_path = os.path.join(tgeniusai_dir, target_subdir) if target_subdir != '.' else tgeniusai_dir
                    # If target_subdir is '.', the final path is just the root dir
                    # If moving a file to root, the target needs to be the filename in the root
                    if target_subdir == '.' and not os.path.isdir(internal_item_path):
                        final_target_path = os.path.join(tgeniusai_dir, item_name)
                    # If moving a directory to root, the target is the root dir
                    elif target_subdir == '.' and os.path.isdir(internal_item_path):
                         final_target_path = os.path.join(tgeniusai_dir, item_name) # Put dir inside root
                    # If moving to a subdir
                    elif target_subdir != '.':
                        final_target_path = os.path.join(tgeniusai_dir, target_subdir)
                        # If it's a dir going into a subdir, append its name
                        if os.path.isdir(internal_item_path) and item_name != target_subdir:
                            final_target_path = os.path.join(final_target_path, item_name)


                    print(f"  Moving '{item_name}' to '{final_target_path}'")

                    # If the destination path exists, remove it to prevent `shutil.move`
                    # from moving the source *inside* the destination directory.
                    if os.path.exists(final_target_path):
                        print(f"  Target '{final_target_path}' already exists. Removing it to ensure a clean move.")
                        if os.path.isdir(final_target_path):
                            shutil.rmtree(final_target_path)
                        else:
                            os.remove(final_target_path)

                    shutil.move(internal_item_path, final_target_path)

                except Exception as e:
                    print(f"  ERROR moving '{item_name}': {e}")
            #else:
            #    print(f"  Item '{item_name}' not found in {internal_dir}")

        # Attempt to remove _internal if empty after processing
        try:
            if not os.listdir(internal_dir):
                print(f"Removing empty directory: {internal_dir}")
                os.rmdir(internal_dir)
            else:
                 print(f"Warning: Directory not empty, contains unexpected files: {internal_dir}")
                 print(f"  Contents: {os.listdir(internal_dir)}")
        except Exception as e:
            print(f"Could not remove directory {internal_dir}: {e}")
    else:
         print(f"Directory {internal_dir} not found. Skipping post-build moves from it.")


    print("Post-build steps completed successfully")

    # Verifica integrità dell'installazione
    print("\n===== INSTALLATION INTEGRITY CHECK =====")
    expected_items = ['ffmpeg', 'res', 'prompts',  # Dirs
                      'version_info.txt', '.env', 'README.md', 'CHANGELOG.md', # Files
                      'KNOW_ISSUES.md', 'contatti_teams.txt', 'TGeniusAI.exe']
    missing_items = []
    for item in expected_items:
        check_path = os.path.join(tgeniusai_dir, item)
        if os.path.exists(check_path):
            print(f"✓ {item} exists")
            if item == 'ms-playwright' and os.path.isdir(check_path):
                 try:
                    total_size = sum(os.path.getsize(os.path.join(root, name)) for root, dirs, files in os.walk(check_path) for name in files)
                    print(f"  - Playwright browsers size: {total_size / (1024*1024):.2f} MB")
                 except Exception as e:
                      print(f"  - Error calculating size for {item}: {e}")
        else:
            print(f"✗ {item} MISSING")
            missing_items.append(item)

    if missing_items:
         print(f"\nWARNING: Some critical items are missing: {', '.join(missing_items)}")
    else:
         print("\nIntegrity check passed.")


# ============================================================
# CHIAMATA ALLA FUNZIONE POST-BUILD (DEVE STARE ALLA FINE)
# ============================================================
post_build_steps()