import os
import re
import subprocess
import sys
from collections import defaultdict


def find_imports_in_file(file_path):
    """Trova tutti gli import in un singolo file Python."""
    imports = set()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # Cattura import diretti (import x)
            match = re.match(r'^\s*import\s+([\w\d_]+)', line)
            if match:
                imports.add(match.group(1))
            # Cattura import con from (from x import y)
            match = re.match(r'^\s*from\s+([\w\d_.]+)', line)
            if match:
                root_module = match.group(1).split('.')[0]
                imports.add(root_module)
    return imports


def find_imports_in_project(root_dir):
    """Scansiona ricorsivamente tutti i file .py e raccoglie gli import."""
    all_imports = set()
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = find_imports_in_file(file_path)
                all_imports.update(imports)
    return all_imports


def get_installed_packages():
    """Ottiene un dizionario di pacchetti installati e relative versioni."""
    installed = {}
    result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if '==' in line:
            package, version = line.split('==')
            installed[package] = version
    return installed


def map_common_aliases(imports):
    """Mappa gli alias comuni ai pacchetti ufficiali di pip."""
    alias_map = {
        'cv2': 'opencv-python',
        'np': 'numpy',
        'PIL': 'pillow',
        'bs4': 'beautifulsoup4',
        'sklearn': 'scikit-learn',
        'yaml': 'pyyaml',
        'CustomSlider': 'CustomSlider',  # Se personalizzato, puoi ignorare
    }
    return {alias_map.get(imp, imp) for imp in imports}


def generate_requirements_file(imports, installed_packages, output_file='requirements.txt'):
    """Genera il file requirements.txt basato sugli import trovati."""
    with open(output_file, 'w') as req_file:
        for imp in sorted(imports):
            if imp in installed_packages:
                req_file.write(f"{imp}=={installed_packages[imp]}\n")
            else:
                print(f"⚠️ Avviso: '{imp}' non trovato nei pacchetti installati. Saltato.")


if __name__ == '__main__':
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"🔍 Scansione dei file Python nella cartella: {project_dir}")

    # Trova tutti gli import nei file Python
    imports = find_imports_in_project(project_dir)
    imports = map_common_aliases(imports)
    print(f"✅ Trovati {len(imports)} moduli importati.")

    # Ottieni pacchetti installati
    installed_packages = get_installed_packages()
    print(f"✅ Rilevati {len(installed_packages)} pacchetti installati.")

    # Genera requirements.txt
    generate_requirements_file(imports, installed_packages)
    print("✅ File requirements.txt generato con successo!")
