# src/services/CombinedAnalyzer.py

import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.services.FrameExtractor import FrameExtractor
from src.services.AudioTranscript import TranscriptionThread
from src.config import PROMPT_COMBINED_ANALYSIS, get_api_key, get_model_for_action

class FrameAnalysisThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, num_frames, language, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language

    def run(self):
        try:
            extractor = FrameExtractor(
                video_path=self.video_path,
                num_frames=self.num_frames
            )
            frames = extractor.extract_frames()
            frame_data = extractor.analyze_frames_batch(
                frames,
                self.language
            )
            final_discourse = extractor.generate_video_summary(frame_data, self.language)
            self.finished.emit(final_discourse or "N/A")
        except Exception as e:
            logging.exception("Error in FrameAnalysisThread")
            self.error.emit(str(e))

class CombinedAnalysisThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, frame_summary, audio_transcript, language, parent=None):
        super().__init__(parent)
        self.frame_summary = frame_summary
        self.audio_transcript = audio_transcript
        self.language = language

    def run(self):
        try:
            with open(PROMPT_COMBINED_ANALYSIS, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            prompt = prompt_template.format(
                language=self.language,
                frame_summary=self.frame_summary,
                audio_transcript=self.audio_transcript
            )

            summary = self.generate_summary(prompt)
            self.finished.emit(summary)

        except Exception as e:
            logging.exception("Error in CombinedAnalysisThread")
            self.error.emit(str(e))

    def generate_summary(self, prompt):
        import google.generativeai as genai

        api_key = get_api_key('google')
        if not api_key:
            raise ValueError("Google API Key not found for combined analysis.")

        genai.configure(api_key=api_key)
        model_name = get_model_for_action('summary')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()


class CombinedAnalyzer(QObject):
    analysis_complete = pyqtSignal(str)
    analysis_error = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, video_path, num_frames, language, combined_mode, main_window, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language
        self.combined_mode = combined_mode
        self.main_window = main_window
        self.results = {}

    def start_analysis(self):
        if self.combined_mode:
            self.progress_update.emit("Avvio analisi frame e audio...")
            self.frame_thread = FrameAnalysisThread(self.video_path, self.num_frames, self.language)
            self.frame_thread.finished.connect(lambda summary: self.on_part_finished('frame', summary))
            self.frame_thread.error.connect(self.on_part_error)
            self.frame_thread.start()

            self.audio_thread = TranscriptionThread(self.video_path, main_window=self.main_window)
            self.audio_thread.transcription_complete.connect(lambda transcript, files: self.on_part_finished('audio', transcript, files))
            self.audio_thread.error_occurred.connect(self.on_part_error)
            self.audio_thread.start()
        else:
            self.progress_update.emit("Avvio analisi frame...")
            self.frame_thread = FrameAnalysisThread(self.video_path, self.num_frames, self.language)
            self.frame_thread.finished.connect(self.analysis_complete.emit)
            self.frame_thread.error.connect(self.analysis_error.emit)
            self.frame_thread.start()

    def on_part_finished(self, part, result, files=None):
        self.progress_update.emit(f"Completata analisi: {part}")
        self.results[part] = result
        if 'frame' in self.results and 'audio' in self.results:
            self.combine_results()

    def on_part_error(self, error_message):
        # Stop other threads if one fails? For now, just report error.
        self.analysis_error.emit(error_message)


    def combine_results(self):
        self.progress_update.emit("Combinazione dei risultati di frame e audio...")
        frame_summary = self.results.get('frame', 'Nessun riassunto visuale generato.')
        audio_transcript = self.results.get('audio', 'Nessuna trascrizione audio generata.')

        self.combination_thread = CombinedAnalysisThread(frame_summary, audio_transcript, self.language)
        self.combination_thread.finished.connect(self.analysis_complete.emit)
        self.combination_thread.error.connect(self.analysis_error.emit)
        self.combination_thread.start()
