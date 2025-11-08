from PyQt6.QtWidgets import QMainWindow

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QSettings
import torch
from src.services.ProcessTextAI import ProcessTextAI
from src.services.MeetingSummarizer import MeetingSummarizer
from src.services.AudioTranscript import TranscriptionThread
from src.services.WhisperTranscript import WhisperTranscriptionThread


class ActionManager:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window

    def setup_connections(self):
        # Qui collegheremo i segnali dei widget alle funzioni di questo manager
        self.main_window.transcribeButton.clicked.connect(self.transcribeVideo)
        self.main_window.summarizeAction.triggered.connect(self.processTextWithAI)
        self.main_window.summarizeMeetingAction.triggered.connect(self.summarizeMeeting)


    def transcribeVideo(self):
        if not self.main_window.videoPathLineEdit:
            self.main_window.show_status_message("Nessun video selezionato.", error=True)
            return

        if self.main_window.onlineModeCheckbox.isChecked():
            # Use the original TranscriptionThread for online mode
            if self.main_window.videoSlider.bookmarks:
                self.main_window.bookmark_manager.transcribe_all_bookmarks()
            else:
                self.main_window.show_status_message("Avvio trascrizione online (Google)...")
                thread = TranscriptionThread(
                    media_path=self.main_window.videoPathLineEdit,
                    main_window=self.main_window,
                    start_time=None,
                    end_time=None
                )
                self.main_window.start_task(thread, self.main_window.onTranscriptionComplete, self.main_window.onTranscriptionError, self.main_window.update_status_progress)
        else:
            # Use the new WhisperTranscriptionThread for offline mode
            if self.main_window.videoSlider.bookmarks:
                # TODO: Update bookmark_manager to support Whisper options
                self.main_window.bookmark_manager.transcribe_all_bookmarks()
            else:
                self.main_window.show_status_message("Avvio trascrizione offline (Whisper)...")
                settings = QSettings("Genius", "GeniusAI")
                model_name = settings.value("whisper/model", "base")
                use_gpu = settings.value("whisper/use_gpu", torch.cuda.is_available(), type=bool)

                thread = WhisperTranscriptionThread(
                    media_path=self.main_window.videoPathLineEdit,
                    main_window=self.main_window,
                    start_time=None,
                    end_time=None,
                    model_name=model_name,
                    use_gpu=use_gpu
                )
                self.main_window.start_task(thread, self.main_window.onTranscriptionComplete, self.main_window.onTranscriptionError, self.main_window.update_status_progress)


    def summarizeMeeting(self):
        current_text = self.main_window.singleTranscriptionTextArea.toPlainText()
        if not current_text.strip():
            self.main_window.show_status_message("Inserisci la trascrizione della riunione da riassumere.", error=True)
            return

        self.main_window.original_text = current_text
        self.main_window.active_summary_type = 'meeting'
        self.main_window.summaryTabWidget.setCurrentIndex(1)


        thread = MeetingSummarizer(
            current_text,
            self.main_window.languageComboBox.currentText()
        )
        self.main_window.start_task(thread, self.main_window.onProcessComplete, self.main_window.onProcessError, self.main_window.update_status_progress)

    def processTextWithAI(self):
        current_text = self.main_window.singleTranscriptionTextArea.toPlainText()
        if not current_text.strip():
            self.main_window.show_status_message("Inserisci del testo da riassumere.", error=True)
            return

        self.main_window.original_text = current_text
        self.main_window.active_summary_type = 'detailed'
        self.main_window.summaryTabWidget.setCurrentIndex(0)

        thread = ProcessTextAI(
            mode="summary",
            language=self.main_window.languageComboBox.currentText(),
            prompt_vars={'text': current_text}
        )
        self.main_window.start_task(thread, self.main_window.onProcessComplete, self.main_window.onProcessError, self.main_window.update_status_progress)
