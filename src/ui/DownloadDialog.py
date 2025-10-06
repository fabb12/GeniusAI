import os
import shutil
import logging
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLabel,
    QLineEdit, QCheckBox, QPushButton, QMessageBox
)
from src.services.DownloadVideo import DownloadThread
from src.config import FFMPEG_PATH_DOWNLOAD

class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Importa da URL")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        downloadGroup = QGroupBox("Download da URL (YouTube, ecc.)")
        grid_layout = QGridLayout(downloadGroup)

        # Riga 0: URL Input
        url_label = QLabel("URL:")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Incolla qui l'URL del video...")
        grid_layout.addWidget(url_label, 0, 0)
        grid_layout.addWidget(self.url_edit, 0, 1)

        # Riga 1: Opzioni
        self.video_checkbox = QCheckBox("Scarica file video (altrimenti solo audio)")
        self.video_checkbox.setChecked(True)
        grid_layout.addWidget(self.video_checkbox, 1, 1)

        # Riga 2: Pulsante di download
        download_btn = QPushButton("Scarica")
        download_btn.clicked.connect(self.handleDownload)
        grid_layout.addWidget(download_btn, 2, 1)

        # Imposta lo stretch per la colonna 1 per farla espandere
        grid_layout.setColumnStretch(1, 1)

        main_layout.addWidget(downloadGroup)
        self.setLayout(main_layout)

    def handleDownload(self):
        url = self.url_edit.text()
        if not url:
            self.parent_window.show_status_message("Inserisci un URL valido.", error=True)
            return

        download_video = self.video_checkbox.isChecked()

        thread = DownloadThread(url, download_video, FFMPEG_PATH_DOWNLOAD, parent_window=self.parent_window)

        if hasattr(thread, 'stream_url_found'):
            thread.stream_url_found.connect(self.onStreamUrlFound)

        self.parent_window.start_task(
            thread,
            self.onDownloadFinished,
            self.onDownloadError,
            self.parent_window.update_status_progress
        )
        self.accept() # Chiude il dialogo dopo aver avviato il task

    def onStreamUrlFound(self, stream_url):
        """Gestisce l'URL di streaming trovato"""
        logging.debug(f"URL di streaming trovato: {stream_url}")

    def onDownloadFinished(self, result):
        temp_file_path, video_title, video_language, upload_date = result
        self.parent_window.show_status_message(f"Download completato: {video_title}")
        self.parent_window.video_download_language = video_language
        logging.debug(video_language)

        # Se un progetto è attivo, salva nella cartella 'downloads' del progetto,
        # altrimenti nella cartella 'downloads' principale.
        if self.parent_window.current_project_path:
            downloads_dir = os.path.join(self.parent_window.current_project_path, "downloads")
        else:
            downloads_dir = os.path.join(os.getcwd(), "downloads")

        os.makedirs(downloads_dir, exist_ok=True)

        try:
            file_name = os.path.basename(temp_file_path)
            permanent_file_path = os.path.join(downloads_dir, file_name)
            shutil.move(temp_file_path, permanent_file_path)

            temp_dir = os.path.dirname(temp_file_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            self.parent_window.loadVideo(permanent_file_path, video_title)

            if upload_date:
                try:
                    video_date = datetime.datetime.strptime(upload_date, '%Y%m%d').isoformat()
                    self.parent_window._update_json_file(permanent_file_path, {"video_date": video_date})
                except (ValueError, TypeError) as e:
                    logging.warning(f"Non è stato possibile analizzare o salvare la data di caricamento: {upload_date}. Errore: {e}")

        except Exception as e:
            self.parent_window.show_status_message(f"Errore durante lo spostamento del file scaricato: {e}", error=True)
            logging.error(f"Failed to move downloaded file: {e}")

    def onDownloadError(self, error_message):
        self.parent_window.show_status_message(f"Errore di download: {error_message}", error=True)