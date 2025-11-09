# pyinstaller.hook.py
import os
import sys

# Questo hook viene eseguito all'avvio dell'eseguibile creato da PyInstaller.
# Il suo scopo è aggiungere la directory contenente le librerie DLL di PyTorch
# al PATH di sistema, risolvendo l'errore `OSError: [WinError 1114]` su Windows.

print("Esecuzione del runtime hook per PyTorch...")

try:
    # Controlla se l'applicazione sta girando come eseguibile PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # sys._MEIPASS è il percorso della cartella temporanea in cui PyInstaller
        # estrae tutti i file dell'applicazione.
        # Le librerie di PyTorch si trovano in una sottocartella 'torch\lib'.
        torch_lib_path = os.path.join(sys._MEIPASS, 'torch', 'lib')

        # Aggiungi questa directory al PATH di sistema se non è già presente.
        # È importante preporla per darle priorità.
        if os.path.isdir(torch_lib_path):
            if torch_lib_path not in os.environ['PATH']:
                print(f"Aggiunta della directory delle librerie PyTorch al PATH: {torch_lib_path}")
                os.environ['PATH'] = torch_lib_path + os.pathsep + os.environ['PATH']
            else:
                print(f"Il percorso delle librerie PyTorch è già nel PATH: {torch_lib_path}")
        else:
            print(f"ATTENZIONE: La directory delle librerie PyTorch non è stata trovata in: {torch_lib_path}")

    else:
        # Se non siamo in un ambiente PyInstaller, non fare nulla.
        print("Non in un ambiente PyInstaller, hook non necessario.")

except Exception as e:
    # Stampa un errore se qualcosa va storto, per facilitare il debug.
    print(f"ERRORE nel runtime hook di PyTorch: {e}")
    # Scrivi l'errore su un file per il debug in caso di crash immediato
    with open("hook_error.log", "w") as f:
        f.write(f"ERRORE nel runtime hook di PyTorch: {e}\n")
        f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Non definito')}\n")
        f.write(f"os.environ['PATH']: {os.environ.get('PATH', 'Non definito')}\n")

print("Runtime hook per PyTorch completato.")
