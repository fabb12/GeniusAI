import os
import random
import sys
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import Qt


def resource_path(relative_path):
    """
    Determina il percorso corretto per le risorse, che funziona sia in modalità sviluppo
    che quando l'applicazione è eseguita tramite PyInstaller.
    """
    try:
        # Se l'app è in esecuzione come bundle PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Altrimenti, durante lo sviluppo
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SplashScreen(QSplashScreen):
    def __init__(self, image_folder):
        super().__init__()

        # Seleziona un'immagine casuale dalla cartella
        pixmap = self.get_random_image(image_folder)
        self.setPixmap(pixmap)

    def get_random_image(self, folder_path):
        """
        Seleziona casualmente un'immagine da una cartella.
        """
        try:
            # Verifica se la cartella esiste
            if not os.path.exists(folder_path):
                # Prova a usare resource_path
                folder_path = resource_path(folder_path)

            # Se la cartella ancora non esiste, utilizzare un'immagine di default
            if not os.path.exists(folder_path):
                default_image = resource_path("res/eye.png")
                if os.path.exists(default_image):
                    return QPixmap(default_image)
                raise FileNotFoundError(f"Cartella immagini non trovata: {folder_path}")

            # Ottieni tutti i file nella cartella
            all_files = os.listdir(folder_path)
            images = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

            if not images:
                # Se non ci sono immagini, usa un'immagine predefinita
                default_image = resource_path("res/eye.png")
                if os.path.exists(default_image):
                    return QPixmap(default_image)
                raise FileNotFoundError("Nessuna immagine trovata nella cartella.")

            # Seleziona un file casuale
            random_image = random.choice(images)

            # Costruisci il percorso completo dell'immagine
            image_path = os.path.join(folder_path, random_image)

            # Carica l'immagine come QPixmap
            return QPixmap(image_path)

        except Exception as e:
            print(f"Errore nel caricamento dell'immagine splash: {e}")
            # Fallback a un'immagine predefinita in caso di errore
            try:
                default_image = resource_path("res/eye.png")
                if os.path.exists(default_image):
                    return QPixmap(default_image)
            except:
                pass
            return QPixmap()  # Pixmap vuoto come ultima risorsa

    def showMessage(self, message):
        """
        Mostra un messaggio nella splash screen, centrato, con colore bianco.
        """
        super().showMessage(message, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                            color=Qt.GlobalColor.white)