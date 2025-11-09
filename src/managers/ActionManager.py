import logging
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from src.services.WhisperTranscript import WhisperTranscriptionThread
from src.services.ProcessTextAI import ProcessTextAI
from src.services.MeetingSummarizer import MeetingSummarizer

class ActionManager:
    def __init__(self, main_window, ui_manager, player_manager):
        """
        Inizializza l'ActionManager.

        :param main_window: L'istanza della finestra principale (VideoAudioManager).
        :param ui_manager: L'istanza di UIManager.
        :param player_manager: L'istanza di PlayerManager.
        """
        self.main_window = main_window
        self.ui_manager = ui_manager
        self.player_manager = player_manager

    def transcribe_video(self):
        """
        Avvia la trascrizione del video attualmente caricato nel player di input.
        """
        video_path = self.main_window.videoPathLineEdit
        if not video_path:
            self.main_window.show_status_message("Errore: Nessun video caricato.", error=True)
            return

        settings = self.main_window.settings
        use_whisper = settings.value("transcription/use_whisper", True, type=bool)
        model_name = settings.value("transcription/whisper_model", "medium")
        use_gpu = settings.value("transcription/use_gpu", True, type=bool)
        language_code = self.ui_manager.languageComboBox.currentData()

        if use_whisper:
            self.main_window.show_status_message(f"Avvio trascrizione con Whisper (modello: {model_name})...")
            thread = WhisperTranscriptionThread(video_path, model_name, use_gpu, language_code)
            self.main_window.start_task(
                thread,
                on_complete=self.on_whisper_transcription_complete,
                on_error=lambda e: self.main_window.show_status_message(f"Errore Whisper: {e}", error=True),
                on_progress=self.main_window.update_status_progress
            )
        else:
            # Qui andrebbe la logica per la trascrizione non-Whisper, se esiste
            self.main_window.show_status_message("Errore: La trascrizione standard non è implementata.", error=True)


    def on_whisper_transcription_complete(self, result):
        """
        Gestisce il completamento della trascrizione Whisper.
        'result' è un dizionario con 'raw_text' e 'markdown_text'.
        """
        self.main_window.transcription_original = result.get('markdown_text', '')
        # Aggiorna la UI con il testo formattato (markdown)
        self.ui_manager.singleTranscriptionTextArea.setMarkdown(self.main_window.transcription_original)
        self.main_window.show_status_message("Trascrizione completata con successo.")
        self.main_window.autosave_transcription()

        # Abilita il toggle per la visualizzazione dopo la prima trascrizione
        self.ui_manager.transcriptionViewToggle.setEnabled(True)
        self.ui_manager.transcriptionViewToggle.setChecked(True) # Mostra la versione con stili

    def process_text_with_ai(self):
        """
        Avvia il processo di riepilogo dettagliato del testo della trascrizione.
        """
        transcription_text = self.ui_manager.singleTranscriptionTextArea.toPlainText()
        if not transcription_text:
            self.main_window.show_status_message("La trascrizione è vuota. Impossibile riassumere.", error=True)
            return

        self.main_window.active_summary_type = 'detailed'
        thread = ProcessTextAI(text=transcription_text, mode='summary')
        self.main_window.start_task(
            thread,
            on_complete=self.on_ai_process_complete,
            on_error=lambda e: self.main_window.show_status_message(f"Errore AI: {e}", error=True),
            on_progress=self.main_window.update_status_progress
        )

    def summarize_meeting(self):
        """
        Avvia il processo di riepilogo in stile "verbale di riunione".
        """
        transcription_text = self.ui_manager.singleTranscriptionTextArea.toPlainText()
        if not transcription_text:
            self.main_window.show_status_message("La trascrizione è vuota. Impossibile riassumere.", error=True)
            return

        self.main_window.active_summary_type = 'meeting'
        thread = MeetingSummarizer(text=transcription_text)
        self.main_window.start_task(
            thread,
            on_complete=self.on_ai_process_complete,
            on_error=lambda e: self.main_window.show_status_message(f"Errore AI: {e}", error=True),
            on_progress=self.main_window.update_status_progress
        )

    def on_ai_process_complete(self, summary_text):
        """
        Gestisce il completamento di un'attività AI (es. riepilogo) e aggiorna la UI.
        """
        if self.main_window.active_summary_type:
            # Salva il riassunto nel modello dati (testo grezzo/markdown)
            self.main_window.summaries[self.main_window.active_summary_type] = summary_text

            # Aggiorna la vista del riassunto, che gestirà la conversione in HTML
            self.main_window._update_summary_view()

            self.main_window.show_status_message(f"Riepilogo '{self.main_window.active_summary_type}' generato con successo.")

            # Passa alla tab del riassunto per mostrare il risultato
            self.ui_manager.transcriptionTabWidget.setCurrentIndex(1)

            # Seleziona la tab specifica per il tipo di riassunto generato
            if 'detailed' in self.main_window.active_summary_type:
                self.ui_manager.summaryTabWidget.setCurrentWidget(self.ui_manager.detailedSummaryTab)
            elif 'meeting' in self.main_window.active_summary_type:
                self.ui_manager.summaryTabWidget.setCurrentWidget(self.ui_manager.meetingSummaryTab)
        else:
            logging.warning("on_ai_process_complete chiamato senza un active_summary_type impostato.")
