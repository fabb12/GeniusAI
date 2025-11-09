# pyinstaller.hook.py
import os
import sys

# Questo hook viene eseguito all'avvio dell'eseguibile creato da PyInstaller.
# Il suo scopo è aggiungere le directory necessarie (in particolare per PyTorch)
# al percorso di ricerca delle DLL di sistema, risolvendo l'errore `OSError: [WinError 1114]`.

print("Esecuzione del runtime hook di PyInstaller...")

try:
    # Controlla se l'applicazione sta girando come eseguibile PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_dir = sys._MEIPASS
        print(f"Ambiente PyInstaller rilevato. Directory _MEIPASS: {meipass_dir}")

        # Definisci i percorsi da aggiungere alla ricerca delle DLL
        # 1. La directory principale dell'app (_MEIPASS) per le DLL generiche.
        # 2. La directory specifica '_internal/torch/lib' per le dipendenze di PyTorch.
        torch_lib_path = os.path.join(meipass_dir, '_internal', 'torch', 'lib')
        paths_to_add = [meipass_dir]

        if os.path.isdir(torch_lib_path):
            print(f"Trovata la directory delle librerie PyTorch: {torch_lib_path}")
            paths_to_add.append(torch_lib_path)
        else:
            print(f"ATTENZIONE: La directory delle librerie PyTorch non è stata trovata in: {torch_lib_path}")

        # Aggiungi i percorsi di ricerca delle DLL
        for path in paths_to_add:
            # Metodo 1: Moderno e preferito (Python 3.8+ su Windows)
            if hasattr(os, 'add_dll_directory'):
                print(f"Aggiunta '{path}' con os.add_dll_directory()...")
                try:
                    os.add_dll_directory(path)
                    print("  -> Successo.")
                except Exception as e:
                    print(f"  -> ERRORE durante l'uso di os.add_dll_directory(): {e}")

            # Metodo 2: Fallback / Tradizionale (modifica della variabile d'ambiente PATH)
            print(f"Aggiunta '{path}' alla variabile d'ambiente PATH...")
            if path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
                print(f"  -> Successo. Nuovo PATH (inizio): {os.environ['PATH'][:500]}...")
            else:
                print("  -> Percorso già presente nel PATH.")

    else:
        # Se non siamo in un ambiente PyInstaller, non fare nulla.
        print("Non in un ambiente PyInstaller, hook non necessario.")

except Exception as e:
    # Stampa un errore se qualcosa va storto, per facilitare il debug.
    print(f"ERRORE CRITICO nel runtime hook di PyInstaller: {e}")
    # Scrivi l'errore su un file per il debug in caso di crash immediato
    log_file = "hook_error.log"
    print(f"Scrittura dell'errore su '{log_file}'...")
    with open(log_file, "a") as f:
        f.write(f"ERRORE nel runtime hook: {e}\n")
        f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Non definito')}\n")
        f.write(f"os.environ['PATH']: {os.environ.get('PATH', 'Non definito')}\n")

print("Runtime hook di PyInstaller completato.")
