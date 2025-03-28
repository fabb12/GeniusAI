import shutil
import os
import re
import zipfile
import datetime
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

current_dir = os.getcwd()

# Collect all submodules and data files of required packages
hiddenimports = (
    collect_submodules('cv2') +
    collect_submodules('moviepy') +
    collect_submodules('numpy') +
    collect_submodules('pydub') +
    collect_submodules('PyQt6') +
    collect_submodules('pycountry') +
    collect_submodules('speech_recognition') +
    # Add explicit imports for pydantic and browser-use relevant modules
    collect_submodules('pydantic') +
    collect_submodules('browser_use') +
    # Additional explicit imports to fix Pydantic issues
    ['pydantic.deprecated.decorator', 'langchain_anthropic', 'langchain_openai'] +
    # Internal project modules
    ['src.ui', 'src.ui.CustomDock', 'src.ui.CustomSlider', 'src.ui.CustVideoWidget',
     'src.ui.CustumTextEdit', 'src.ui.ScreenButton', 'src.ui.SplashScreen', 'src.ui.VideoOverlay', 'src.ui.CropOverlay',
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
    # Add data files for pydantic and browser-use
    collect_data_files('pydantic') +
    collect_data_files('browser_use')
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

# Resource files - lista ridotta senza ffmpeg per evitare duplicazioni
resource_files = [
    # Environment file
    (os.path.join(current_dir, '.env'), '.'),

    # Documentation files
    (os.path.join(current_dir, 'README.md'), '.'),
    (os.path.join(current_dir, 'CHANGELOG.md'), '.'),
    (os.path.join(current_dir, 'KNOW_ISSUES.md'), '.'),

    # Cartella prompts - posizionata a livello root
    (os.path.join(current_dir, 'src', 'prompts'), 'prompts'),

    # Main resource directories - keep these at the top level
    (os.path.join(current_dir, 'src', 'res'), 'res'),

    # Explicitly include subdirectories
    (os.path.join(current_dir, 'src', 'res', 'splash_images'), 'res/splash_images'),
    (os.path.join(current_dir, 'src', 'res', 'music'), 'res/music'),

    # Ensure important icons are included
    (os.path.join(current_dir, 'src', 'res', 'eye.ico'), 'res'),
    (os.path.join(current_dir, 'src', 'res', 'eye.png'), 'res'),
    (os.path.join(current_dir, 'src', 'res', 'watermark.png'), 'res'),

    # Assicurarsi che tutti i file .png nella cartella res vengano inclusi
    (os.path.join(current_dir, 'src', 'res', '*.png'), 'res'),

    # Add contatti_teams.txt
    (os.path.join(current_dir, 'src', 'contatti_teams.txt'), '.'),
]

# Create copies of any missing pydantic modules
try:
    # Find the site-packages directory
    site_packages_dir = os.path.join(current_dir, 'venv', 'Lib', 'site-packages')

    # Paths to pydantic directories
    pydantic_dir = os.path.join(site_packages_dir, 'pydantic')
    deprecated_dir = os.path.join(pydantic_dir, 'deprecated')

    # Create the deprecated directory if it doesn't exist
    if not os.path.exists(deprecated_dir):
        os.makedirs(deprecated_dir, exist_ok=True)
        print(f"Created directory: {deprecated_dir}")

    # Create an __init__.py in the deprecated directory
    init_file = os.path.join(deprecated_dir, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("# Auto-generated for compatibility\n")
        print(f"Created file: {init_file}")

    # Create a minimal decorator.py file
    decorator_file = os.path.join(deprecated_dir, 'decorator.py')
    if not os.path.exists(decorator_file):
        with open(decorator_file, 'w') as f:
            f.write("# Auto-generated for compatibility with newer pydantic versions\n\n")
            f.write("class ValidatedFunction:\n")
            f.write("    def __init__(self, *args, **kwargs):\n")
            f.write("        pass\n\n")
            f.write("def validate_arguments(func):\n")
            f.write("    return func\n")
        print(f"Created file: {decorator_file}")

    # Add these files to datas
    datas.append((deprecated_dir, 'pydantic/deprecated'))
except Exception as e:
    print(f"Warning: Could not create pydantic compatibility files: {e}")

a = Analysis(
    ['src/TGeniusAI.py'],
    pathex=[
        '.',
        'src',
        os.path.join(current_dir, 'venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin'),
        # Add site-packages to the path to ensure all modules are found
        os.path.join(current_dir, 'venv', 'Lib', 'site-packages')
    ],
    binaries=binaries,
    datas=resource_files + datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5'],
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
    console=False,  # Impostato a False per nascondere la console nell'app finale
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
    console=False  # Impostato a False per nascondere la console nell'app finale
)

# Create version_info.txt file
def create_version_info():
    # Extract version from the source code
    version_pattern = re.compile(r'self\.version_major = (\d+).*self\.version_minor = (\d+).*self\.version_patch = (\d+)', re.DOTALL)
    try:
        with open('src/TGeniusAI.py', 'r', encoding='utf-8') as f:
            content = f.read()
        match = version_pattern.search(content)
        if match:
            version = f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"
        else:
            version = "v0.0.0"
    except Exception as e:
        print(f"Error extracting version: {e}")
        version = "v0.0.0"

    # Get the current date
    build_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the version_info.txt file
    version_info_content = f"Version: {version}\nBuild Date: {build_date}\n"
    version_info_path = os.path.join(current_dir, 'version_info.txt')

    with open(version_info_path, 'w') as version_file:
        version_file.write(version_info_content)

    return version_info_path, version


def post_build_steps():
    """Performs all post-build steps to organize the distribution package"""
    dist_dir = os.path.join(current_dir, 'dist')
    tgeniusai_dir = os.path.join(dist_dir, 'TGeniusAI')
    internal_dir = os.path.join(tgeniusai_dir, '_internal')

    # Create version info file
    version_info_path, version = create_version_info()

    # Move version_info.txt to the root of the distribution
    if os.path.exists(version_info_path):
        target_path = os.path.join(tgeniusai_dir, 'version_info.txt')
        try:
            shutil.copy2(version_info_path, target_path)
            print(f"Version info copied to: {target_path}")
        except Exception as e:
            print(f"Error copying version info: {e}")

    # Copiamo esplicitamente la cartella ffmpeg
    src_ffmpeg_path = os.path.join(current_dir, 'src', 'ffmpeg')
    dest_ffmpeg_path = os.path.join(tgeniusai_dir, 'ffmpeg')

    if os.path.exists(src_ffmpeg_path):
        print(f"Copying ffmpeg directory from {src_ffmpeg_path} to {dest_ffmpeg_path}")

        # Rimuovi la destinazione se esiste già
        if os.path.exists(dest_ffmpeg_path):
            shutil.rmtree(dest_ffmpeg_path)

        # Copia l'intera cartella ffmpeg con tutti i binari
        shutil.copytree(src_ffmpeg_path, dest_ffmpeg_path)
        print(f"Successfully copied ffmpeg directory")
    else:
        print(f"WARNING: Source ffmpeg directory not found at {src_ffmpeg_path}")

    # Make sure resource directories are properly structured
    critical_dirs = [
        'res',
        'res/splash_images',
        'res/music',
        'prompts'
    ]

    for dir_path in critical_dirs:
        internal_source = os.path.join(internal_dir, dir_path)
        target_path = os.path.join(tgeniusai_dir, dir_path)

        # Create target directory if it doesn't exist
        os.makedirs(target_path, exist_ok=True)

        # If resources exist in _internal, copy them to the right place
        if os.path.exists(internal_source):
            try:
                for item in os.listdir(internal_source):
                    s = os.path.join(internal_source, item)
                    d = os.path.join(target_path, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                print(f"Copied resources from {internal_source} to {target_path}")
            except Exception as e:
                print(f"Error copying {dir_path}: {e}")

    # Move documentation files and contatti_teams.txt up to the root level
    files_to_move = ['README.md', 'CHANGELOG.md', 'KNOW_ISSUES.md', 'contatti_teams.txt']
    for file_name in files_to_move:
        src_path = os.path.join(internal_dir, file_name)
        dest_path = os.path.join(tgeniusai_dir, file_name)
        if os.path.exists(src_path):
            try:
                shutil.copy2(src_path, dest_path)
                print(f"Copied {file_name} to root directory")
            except Exception as e:
                print(f"Error copying {file_name}: {e}")

    print("Post-build steps completed successfully")

    # Verifica integrità dell'installazione
    print("\n===== INSTALLATION INTEGRITY CHECK =====")
    all_critical_dirs = critical_dirs + ['ffmpeg', 'ffmpeg/bin']
    for dir_path in all_critical_dirs:
        check_path = os.path.join(tgeniusai_dir, dir_path)
        if os.path.exists(check_path):
            print(f"✓ {dir_path} exists")
            if os.path.isdir(check_path):
                items = os.listdir(check_path)
                print(f"  - Contains {len(items)} items")
        else:
            print(f"✗ {dir_path} MISSING")

    # Verifica ffmpeg binaries
    ffmpeg_binaries = ['ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe']
    ffmpeg_bin_dir = os.path.join(tgeniusai_dir, 'ffmpeg', 'bin')

    for binary in ffmpeg_binaries:
        binary_path = os.path.join(ffmpeg_bin_dir, binary)
        if os.path.exists(binary_path):
            print(f"✓ {binary} exists - {os.path.getsize(binary_path)/1024/1024:.2f} MB")
        else:
            print(f"✗ {binary} MISSING")


# Run post-build steps
post_build_steps()