# src/services/VideoIntegrator.py

import logging
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from bs4 import BeautifulSoup

from src.services.FrameExtractor import FrameExtractor
from src.services.ProcessTextAI import ProcessTextAI

class VideoIntegrationThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, video_path, num_frames, language, current_summary_html, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language
        self.current_summary_html = current_summary_html

    def run(self):
        try:
            self.progress.emit(10, "Estrazione frame dal video...")
            extractor = FrameExtractor(
                video_path=self.video_path,
                num_frames=self.num_frames
            )
            frames = extractor.extract_frames()
            if not frames:
                self.error.emit("Impossibile estrarre i frame dal video.")
                return

            self.progress.emit(30, "Analisi dei frame in corso...")
            frame_data = extractor.analyze_frames_batch(frames, self.language)
            if not frame_data:
                self.error.emit("L'analisi dei frame non ha prodotto risultati.")
                return

            # Formatta le informazioni dei frame per il prompt
            frame_info_str = "\n".join([
                f"- {item['description']} [{item['timestamp']}]"
                for item in frame_data
            ])

            # Estrai il testo puro dal riassunto HTML per l'analisi
            soup = BeautifulSoup(self.current_summary_html, 'html.parser')
            current_summary_text = soup.get_text()

            # Prepara le variabili per il prompt
            prompt_vars = {
                "current_summary": current_summary_text,
                "frame_info": frame_info_str
            }

            self.progress.emit(70, "Integrazione AI nel riassunto...")

            # Crea e avvia il thread di elaborazione AI
            self.ai_thread = ProcessTextAI(
                mode="video_integration",
                language=self.language,
                prompt_vars=prompt_vars
            )

            # Connetti i segnali
            self.ai_thread.completed.connect(self.on_ai_completed)
            self.ai_thread.error.connect(self.on_ai_error)

            # Esegui il thread in modo sincrono per mantenere la logica sequenziale
            self.ai_thread.run()

        except Exception as e:
            logging.exception("Errore in VideoIntegrationThread")
            self.error.emit(str(e))

    def on_ai_completed(self, integrated_summary_html):
        """Chiamato quando l'AI completa l'integrazione."""
        self.progress.emit(100, "Completato.")
        self.completed.emit(integrated_summary_html)

    def on_ai_error(self, error_message):
        """Chiamato se l'AI restituisce un errore."""
        self.error.emit(f"Errore durante l'integrazione AI: {error_message}")
