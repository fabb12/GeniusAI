# src/services/VideoIntegrator.py

import logging
from PyQt6.QtCore import QThread, pyqtSignal

from src.services.FrameExtractor import FrameExtractor
from src.config import PROMPT_VIDEO_INTEGRATION, get_api_key, get_model_for_action

class VideoIntegrationThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, video_path, num_frames, language, current_summary, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language
        self.current_summary = current_summary

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

            frame_info = "\n".join([f"- {item['description']} (timestamp: {item['timestamp']})" for item in frame_data])

            self.progress.emit(60, "Lettura del prompt di integrazione...")
            with open(PROMPT_VIDEO_INTEGRATION, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            prompt = prompt_template.format(
                language=self.language,
                current_summary=self.current_summary,
                frame_info=frame_info
            )

            self.progress.emit(70, "Generazione del riassunto integrato...")
            integrated_summary = self.generate_integrated_summary(prompt)

            self.progress.emit(100, "Completato.")
            self.finished.emit(integrated_summary)

        except Exception as e:
            logging.exception("Errore in VideoIntegrationThread")
            self.error.emit(str(e))

    def generate_integrated_summary(self, prompt):
        import google.generativeai as genai

        api_key = get_api_key('google')
        if not api_key:
            raise ValueError("Google API Key non trovata per l'integrazione video.")

        genai.configure(api_key=api_key)
        model_name = get_model_for_action('summary')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
