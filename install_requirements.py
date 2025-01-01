import subprocess

# Leggi i pacchetti dal file requirements.txt
with open('requirements.txt', 'r') as file:
    lines = file.readlines()

# Installa ogni pacchetto individualmente
for line in lines:
    package = line.strip()
    if package and not package.startswith('#'):
        print(f"\n📦 Installing {package}...")
        try:
            subprocess.run(['pip', 'install', package], check=True)
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to install {package}. Skipping to the next package.")
