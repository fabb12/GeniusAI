import os
import random
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import Qt


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
        # Ottieni tutti i file nella cartella
        images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if not images:
            raise FileNotFoundError("Nessuna immagine trovata nella cartella.")

        # Seleziona un file casuale
        random_image = random.choice(images)

        # Costruisci il percorso completo dell'immagine
        image_path = os.path.join(folder_path, random_image)

        # Carica l'immagine come QPixmap
        return QPixmap(image_path)

    def showMessage(self, message):
        """
        Mostra un messaggio nella splash screen, centrato, con colore bianco.
        """
        super().showMessage(message, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                            color=Qt.GlobalColor.white)
