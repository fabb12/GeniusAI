import os
import shutil
import logging
import datetime
import torch
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLabel,
    QLineEdit, QCheckBox, QPushButton, QMessageBox
)
from src.services.DownloadVideo import DownloadThread
from src.config import FFMPEG_PATH_DOWNLOAD
from src.services import utils
from src.services.WhisperTranscript import WhisperTranscriptionThread


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

        # Riga 2: Checkbox per i commenti
        self.comments_checkbox = QCheckBox("Scarica anche i commenti del video")
        self.comments_checkbox.setChecked(False)
        grid_layout.addWidget(self.comments_checkbox, 2, 1)

        # Riga 3: Trascrizione Automatica
        self.transcribe_checkbox = QCheckBox("Avvia trascrizione dopo il download")
        self.transcribe_checkbox.setChecked(True)
        grid_layout.addWidget(self.transcribe_checkbox, 3, 1)

        # Riga 4: Pulsante di download
        download_btn = QPushButton("Scarica")
        download_btn.clicked.connect(self.handleDownload)
        grid_layout.addWidget(download_btn, 4, 1)

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
        download_comments = self.comments_checkbox.isChecked()

        thread = DownloadThread(url, download_video, FFMPEG_PATH_DOWNLOAD, parent_window=self.parent_window, download_comments=download_comments)

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
        temp_file_path, video_title, video_language, upload_date, video_id = result
        self.parent_window.show_status_message(f"Download completato: {video_title}")
        self.parent_window.video_download_language = video_language
        logging.debug(video_language)

        if not self.parent_window.current_project_path:
            self.parent_window.show_status_message("Nessun progetto attivo. Creane o aprine uno per aggiungere il video.", error=True)
            return

        clips_dir = os.path.join(self.parent_window.current_project_path, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        permanent_file_path = ""
        try:
            # Get the file extension from the temporary file
            _, file_extension = os.path.splitext(temp_file_path)

            # Construct the initial desired path
            base_filename = f"{video_title}{file_extension}"
            initial_path = os.path.join(clips_dir, base_filename)

            # Generate a unique path, ensuring the filename is sanitized and unique
            permanent_file_path = utils.generate_unique_filename(initial_path)

            # Move the downloaded file to the clips directory with the new name
            shutil.move(temp_file_path, permanent_file_path)

            # Define temp_dir before using it
            temp_dir = os.path.dirname(temp_file_path)

            # Move the comments file if it exists
            if video_id:
                temp_comments_path = os.path.join(temp_dir, f"comments_{video_id}.json")
                if os.path.exists(temp_comments_path):
                    permanent_comments_path = os.path.join(clips_dir, f"comments_{video_id}.json")
                    shutil.move(temp_comments_path, permanent_comments_path)

            # Clean up the temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            # Add the new clip to the project
            self.parent_window.project_manager.add_clip_to_project_from_path(
                self.parent_window.projectDock.gnai_path, permanent_file_path, status="online"
            )

            # Load the new video into the input player
            self.parent_window.loadVideo(permanent_file_path, video_title)

            # Refresh the project dock to show the new clip
            self.parent_window.load_project(self.parent_window.projectDock.gnai_path)

            if upload_date:
                try:
                    video_date = datetime.datetime.strptime(upload_date, '%Y%m%d').isoformat()
                    self.parent_window._update_json_file(permanent_file_path, {"video_date": video_date})
                except (ValueError, TypeError) as e:
                    logging.warning(f"Non è stato possibile analizzare o salvare la data di caricamento: {upload_date}. Errore: {e}")

        except Exception as e:
            self.parent_window.show_status_message(f"Errore durante lo spostamento del file scaricato: {e}", error=True)
            logging.error(f"Failed to move downloaded file: {e}")
            return # Non procedere con la trascrizione se il file non è stato gestito correttamente

        # Avvia la trascrizione se richiesto
        if self.transcribe_checkbox.isChecked() and permanent_file_path:
            self.parent_window.show_status_message("Avvio trascrizione automatica (Whisper)...")
            settings = QSettings("Genius", "GeniusAI")
            model_name = settings.value("whisper/model", "base")
            use_gpu = settings.value("whisper/use_gpu", torch.cuda.is_available(), type=bool)

            transcription_thread = WhisperTranscriptionThread(
                media_path=permanent_file_path,
                main_window=self.parent_window,
                model_name=model_name,
                use_gpu=use_gpu
            )
            self.parent_window.start_task(
                transcription_thread,
                self.parent_window.onTranscriptionComplete,
                self.parent_window.onTranscriptionError,
                self.parent_window.update_status_progress
            )

    def onDownloadError(self, error_message):
        self.parent_window.show_status_message(f"Errore di download: {error_message}", error=True)