import os
import whisper
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLabel, QMessageBox, QProgressBar
from PyQt6.QtCore import QThread, pyqtSignal, Qt

class ModelDownloaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model_name, cache_dir):
        super().__init__()
        self.model_name = model_name
        self.cache_dir = cache_dir

    def run(self):
        try:
            whisper._download(whisper._MODELS[self.model_name], self.cache_dir, self.progress.emit)
            self.finished.emit(self.model_name)
        except Exception as e:
            self.error.emit(str(e))

class ModelManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Modelli Whisper")
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout(self)

        self.listWidget = QListWidget()
        self.layout.addWidget(self.listWidget)

        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        self.layout.addWidget(self.progressBar)

        self.buttonLayout = QHBoxLayout()
        self.downloadButton = QPushButton("Download Selezionato")
        self.deleteButton = QPushButton("Elimina Selezionato")
        self.buttonLayout.addWidget(self.downloadButton)
        self.buttonLayout.addWidget(self.deleteButton)
        self.layout.addLayout(self.buttonLayout)

        self.downloadButton.clicked.connect(self.download_model)
        self.deleteButton.clicked.connect(self.delete_model)

        self.populate_models()

    def get_cache_dir(self):
        """Returns the application's cache directory for Whisper models."""
        models_dir = "models"
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
        return models_dir

    def populate_models(self):
        self.listWidget.clear()
        cache_dir = self.get_cache_dir()
        for model_name in whisper.available_models():
            item = QListWidgetItem(model_name)
            is_downloaded = os.path.exists(os.path.join(cache_dir, f"{model_name}.pt"))
            item.setText(f"{model_name} {'(scaricato)' if is_downloaded else ''}")
            item.setData(Qt.ItemDataRole.UserRole, is_downloaded)
            self.listWidget.addItem(item)

    def download_model(self):
        selected_item = self.listWidget.currentItem()
        if not selected_item:
            return

        model_name = selected_item.text().split(' ')[0]
        is_downloaded = selected_item.data(Qt.ItemDataRole.UserRole)

        if is_downloaded:
            QMessageBox.information(self, "Modello già scaricato", "Il modello selezionato è già stato scaricato.")
            return

        self.downloadButton.setEnabled(False)
        self.deleteButton.setEnabled(False)
        self.progressBar.setVisible(True)

        self.downloader = ModelDownloaderThread(model_name, self.get_cache_dir())
        self.downloader.progress.connect(self.progressBar.setValue)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.on_download_error)
        self.downloader.start()

    def on_download_finished(self, model_name):
        self.progressBar.setVisible(False)
        self.downloadButton.setEnabled(True)
        self.deleteButton.setEnabled(True)
        QMessageBox.information(self, "Download completato", f"Il modello '{model_name}' è stato scaricato con successo.")
        self.populate_models()

    def on_download_error(self, error_message):
        self.progressBar.setVisible(False)
        self.downloadButton.setEnabled(True)
        self.deleteButton.setEnabled(True)
        QMessageBox.critical(self, "Errore di download", f"Errore durante il download del modello: {error_message}")

    def delete_model(self):
        selected_item = self.listWidget.currentItem()
        if not selected_item:
            return

        model_name = selected_item.text().split(' ')[0]
        is_downloaded = selected_item.data(Qt.ItemDataRole.UserRole)

        if not is_downloaded:
            QMessageBox.information(self, "Modello non presente", "Il modello selezionato non è presente sul disco.")
            return

        reply = QMessageBox.question(self, "Conferma eliminazione", f"Sei sicuro di voler eliminare il modello '{model_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                model_path = os.path.join(self.get_cache_dir(), f"{model_name}.pt")
                os.remove(model_path)
                QMessageBox.information(self, "Eliminazione completata", f"Il modello '{model_name}' è stato eliminato.")
                self.populate_models()
            except Exception as e:
                QMessageBox.critical(self, "Errore di eliminazione", f"Errore durante l'eliminazione del modello: {e}")
