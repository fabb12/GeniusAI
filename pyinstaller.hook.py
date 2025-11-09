# pyinstaller.hook.py
import os
import sys

# Questo hook viene eseguito all'avvio dell'eseguibile creato da PyInstaller.
# Il suo scopo è aggiungere la directory contenente le librerie DLL di PyTorch
# al percorso di ricerca delle DLL di sistema, risolvendo l'errore `OSError: [WinError 1114]`.

print("Esecuzione del runtime hook robusto per PyTorch...")

try:
    # Controlla se l'applicazione sta girando come eseguibile PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print(f"Ambiente PyInstaller rilevato. _MEIPASS: {sys._MEIPASS}")

        # sys._MEIPASS è il percorso della cartella temporanea in cui PyInstaller
        # estrae tutti i file dell'applicazione.
        # Le librerie di PyTorch si trovano in una sottocartella 'torch\lib'.
        torch_lib_path = os.path.join(sys._MEIPASS, 'torch', 'lib')

        if os.path.isdir(torch_lib_path):
            print(f"Trovata la directory delle librerie PyTorch: {torch_lib_path}")

            # Metodo 1: Moderno e preferito (Python 3.8+ su Windows)
            # Utilizza os.add_dll_directory() per aggiungere il percorso di ricerca delle DLL.
            if hasattr(os, 'add_dll_directory'):
                print(f"Tentativo di aggiungere il percorso con os.add_dll_directory()...")
                try:
                    os.add_dll_directory(torch_lib_path)
                    print(f"Percorso aggiunto con successo a os.add_dll_directory().")
                except Exception as e:
                    print(f"ERRORE durante l'uso di os.add_dll_directory(): {e}")

            # Metodo 2: Fallback / Tradizionale
            # Modifica la variabile d'ambiente PATH.
            print("Tentativo di aggiungere il percorso alla variabile d'ambiente PATH...")
            if torch_lib_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = torch_lib_path + os.pathsep + os.environ.get('PATH', '')
                print(f"Percorso aggiunto al PATH. Nuovo PATH (inizio): {os.environ['PATH'][:300]}...")
            else:
                print("Il percorso delle librerie PyTorch era già nel PATH.")

        else:
            print(f"ATTENZIONE: La directory delle librerie PyTorch non è stata trovata in: {torch_lib_path}")

    else:
        # Se non siamo in un ambiente PyInstaller, non fare nulla.
        print("Non in un ambiente PyInstaller, hook non necessario.")

except Exception as e:
    # Stampa un errore se qualcosa va storto, per facilitare il debug.
    print(f"ERRORE CRITICO nel runtime hook di PyTorch: {e}")
    # Scrivi l'errore su un file per il debug in caso di crash immediato
    with open("hook_error.log", "a") as f:
        f.write(f"ERRORE nel runtime hook di PyTorch: {e}\n")
        f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Non definito')}\n")
        f.write(f"os.environ['PATH']: {os.environ.get('PATH', 'Non definito')}\n")

print("Runtime hook robusto per PyTorch completato.")
