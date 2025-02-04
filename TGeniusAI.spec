import shutil
import os
import re
import zipfile
import datetime
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

current_dir = os.getcwd()

# Collect all submodules and data files of required packages to avoid missing imports
hiddenimports = (
    collect_submodules('cv2') +
    collect_submodules('moviepy') +
    collect_submodules('numpy') +
    collect_submodules('pydub') +
    collect_submodules('PyQt6') +
    collect_submodules('pycountry') +
    collect_submodules('speech_recognition')
)
datas = (
    collect_data_files('cv2') +
    collect_data_files('moviepy') +
    collect_data_files('numpy') +
    collect_data_files('pydub') +
    collect_data_files('PyQt6') +
    collect_data_files('pycountry') +
    collect_data_files('speech_recognition')
)

# Additional DLLs and plugins for PyQt6
extra_dll_paths = [
    os.path.join(current_dir, 'venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')
]
extra_datas = collect_data_files('PyQt6', subdir='Qt6/plugins')

datas += extra_datas

binaries = []
for dll_path in extra_dll_paths:
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))

a = Analysis(
    ['src/TGeniusAI.py'],
    pathex=['.', os.path.join(current_dir, 'venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')],
    binaries=binaries,
    datas=[
        (os.path.join(current_dir, '.env'), '.'),  # Add venv
        (os.path.join(current_dir, 'src', 'res'), 'res'),  # Include resource folder
        (os.path.join(current_dir, 'README.md'), '.'),  # Add Readme.md
        (os.path.join(current_dir, 'CHANGELOG.md'), '.'),  # Add CHANGELOG.md
        (os.path.join(current_dir, 'KNOW_ISSUES.md'), '.'),  # Add KNOW_ISSUES.md
    ] + datas,
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
    console=False,  # Set console to False to remove console window
    icon=os.path.join('src', 'res', 'eye.ico')  # Specify the icon path in the res folder under src
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

# Custom script to create the version_info.txt file and move files to the correct folder
def create_version_info():
    # Extract version from the source code
    version_pattern = re.compile(r'self\.version_major = (\d+).*self\.version_minor = (\d+).*self\.version_patch = (\d+)', re.DOTALL)
    with open('src/TGeniusAI.py', 'r') as f:
        content = f.read()
    match = version_pattern.search(content)
    if match:
        version = f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"
    else:
        version = "v0.0.0"

    # Get the current date
    build_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the version_info.txt file
    version_info_content = f"Version: {version}\nBuild Date: {build_date}\n"
    version_info_path = os.path.join(current_dir, 'version_info.txt')

    with open(version_info_path, 'w') as version_file:
        version_file.write(version_info_content)

    return version_info_path, version


def move_files_up_and_create_zip():
    internal_dir = os.path.join(current_dir, 'dist', 'TGeniusAI', '_internal')
    release_dir = os.path.join(current_dir, 'dist', 'Release')
    tgeniusai_dir = os.path.join(current_dir, 'dist', 'TGeniusAI')

    # Create the release folder if it doesn't exist
    os.makedirs(release_dir, exist_ok=True)

    # Files to move
    files_to_move = ['README.md', 'KNOW_ISSUES.md', 'CHANGELOG.md']
    folders_to_move = ['res']

    # Move the files
    for file_name in files_to_move:
        src_path = os.path.join(internal_dir, file_name)
        dest_path = os.path.join(tgeniusai_dir, file_name)
        if os.path.exists(src_path):
            shutil.move(src_path, dest_path)

    # Move the folders
    for folder_name in folders_to_move:
        src_path = os.path.join(internal_dir, folder_name)
        dest_path = os.path.join(tgeniusai_dir, folder_name)
        if os.path.exists(src_path):
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.move(src_path, dest_path)

    # Create the version_info.txt file
    version_info_path, version = create_version_info()

    # Move the version_info.txt file to the destination folder
    shutil.move(version_info_path, os.path.join(tgeniusai_dir, 'version_info.txt'))

    # Create a ZIP file with all files in the TGeniusAI folder
    zip_file_path = os.path.join(release_dir, f"TGeniusAI_{version}.zip")
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for root, dirs, files in os.walk(tgeniusai_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tgeniusai_dir)
                zipf.write(file_path, arcname)

# Run the script to move files and create the ZIP
move_files_up_and_create_zip()
