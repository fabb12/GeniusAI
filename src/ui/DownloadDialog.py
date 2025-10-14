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

        if not self.parent_window.current_project_path:
            self.parent_window.show_status_message("Nessun progetto attivo. Il file scaricato non sarà aggiunto al progetto.", error=True)
            # Carica il video nel player per un uso temporaneo
            self.parent_window.loadVideo(temp_file_path, video_title)
            return

        clips_dir = os.path.join(self.parent_window.current_project_path, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        try:
            file_name = os.path.basename(temp_file_path)
            permanent_file_path = os.path.join(clips_dir, file_name)
            shutil.move(temp_file_path, permanent_file_path)

            temp_dir = os.path.dirname(temp_file_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            # Aggiungi la clip al progetto usando il ProjectManager
            success, message = self.parent_window.project_manager.add_clip_to_project_from_path(
                self.parent_window.projectDock.gnai_path,
                permanent_file_path,
                status="online" # Imposta lo stato come online
            )
            if success:
                self.parent_window.show_status_message(f"Clip '{file_name}' aggiunta al progetto.")
                # Ricarica il progetto per aggiornare la UI
                self.parent_window.load_project(self.parent_window.projectDock.gnai_path)
                # Carica il nuovo video nel player
                self.parent_window.loadVideo(permanent_file_path, video_title)

                # Aggiorna la data di creazione se disponibile
                if upload_date:
                    try:
                        video_date = datetime.datetime.strptime(upload_date, '%Y%m%d').isoformat()
                        self.parent_window._update_json_file(permanent_file_path, {"video_date": video_date})
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Non è stato possibile analizzare o salvare la data di caricamento: {upload_date}. Errore: {e}")
            else:
                 self.parent_window.show_status_message(f"Errore nell'aggiungere la clip al progetto: {message}", error=True)


        except Exception as e:
            self.parent_window.show_status_message(f"Errore durante lo spostamento e l'integrazione del file scaricato: {e}", error=True)
            logging.error(f"Failed to move and integrate downloaded file: {e}")

    def onDownloadError(self, error_message):
        self.parent_window.show_status_message(f"Errore di download: {error_message}", error=True)