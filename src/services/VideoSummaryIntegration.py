# File: src/services/VideoSummaryIntegration.py
import logging
import re
import base64
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.ProcessTextAI import ProcessTextAI
from src.services.FrameExtractor import FrameExtractor
from src.services.utils import (
    parse_timestamp_to_seconds,
    convert_html_to_markdown,
    convert_markdown_to_html
)

class VideoSummaryIntegrationThread(QThread):
    """
    Orchestrates the creation of a rich video summary by integrating
    a text summary with key video frames.
    """
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, main_window, video_path, transcription_text, language="italiano", parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.video_path = video_path
        self.transcription_text = transcription_text
        self.language = language

    def run(self):
        try:
            # Step 1: Generate the initial text-only summary
            self.progress.emit(10, "Generazione del riassunto testuale...")
            text_summary = self._generate_text_summary()
            if not text_summary:
                self.error.emit("La generazione del riassunto testuale iniziale è fallita.")
                return

            # Step 2: Parse summary to find all timestamps
            self.progress.emit(30, "Analisi dei momenti chiave del riassunto...")
            timestamps = self._extract_timestamps_from_summary(text_summary)
            if not timestamps:
                logging.warning("Nessun timestamp trovato nel riassunto. Procedo con il riassunto testuale.")
                self.completed.emit(convert_markdown_to_html(text_summary))
                return

            # Step 3: Extract frames for the identified timestamps
            self.progress.emit(50, f"Estrazione di {len(timestamps)} frame pertinenti...")
            frame_dict = self._extract_frames_for_timestamps(timestamps)
            if not frame_dict:
                logging.warning("Estrazione frame fallita. Procedo con il riassunto testuale.")
                self.completed.emit(convert_markdown_to_html(text_summary))
                return

            # Step 4: Embed frame images into the final HTML
            self.progress.emit(80, "Incorporamento delle immagini nel riassunto finale...")
            summary_html = convert_markdown_to_html(text_summary)
            final_html = self._embed_images_into_html(summary_html, frame_dict)
            self.progress.emit(100, "Completato.")
            self.completed.emit(final_html)

        except Exception as e:
            logging.exception("Errore imprevisto in VideoSummaryIntegrationThread.")
            self.error.emit(f"Errore: {str(e)}")

    def _generate_text_summary(self):
        """Generates a text-only summary from the transcription."""
        prompt_vars = {'text': convert_html_to_markdown(self.transcription_text)}
        summarizer = ProcessTextAI(
            mode="summary",
            language=self.language,
            prompt_vars=prompt_vars
        )
        result, _, _ = summarizer._process_text_with_selected_model()
        return result

    def _extract_timestamps_from_summary(self, summary_text):
        """Finds all timestamps (e.g., [MM:SS]) in the summary text."""
        timestamp_regex = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')
        matches = timestamp_regex.findall(summary_text)
        # Convert to seconds and remove duplicates
        return sorted(list(set([parse_timestamp_to_seconds(ts) for ts in matches])))

    def _extract_frames_for_timestamps(self, timestamps_in_seconds):
        """Extracts frames at specific timestamps."""
        extractor = FrameExtractor(
            video_path=self.video_path,
            num_frames=0, # Not needed for this method
            language=self.language
        )

        extracted_frames = extractor.extract_frames_at_timestamps(timestamps_in_seconds)
        if not extracted_frames:
            return None

        # Create a dictionary mapping timestamps (in seconds) to base64 image data
        frame_dict = {
            int(frame['timestamp']): frame['data']
            for frame in extracted_frames
        }

        return frame_dict

    def _embed_images_into_html(self, html_content, frame_dict):
        """Parses HTML, finds timestamps, and inserts corresponding base64 images."""

        timestamp_regex = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')

        def replacer(match):
            timestamp_str = match.group(1)
            seconds = parse_timestamp_to_seconds(timestamp_str)

            # Find the closest matching frame in our dictionary
            if seconds in frame_dict:
                b64_image = frame_dict[seconds]
                img_tag = f'<br><img src="data:image/jpeg;base64,{b64_image}" alt="Frame at {timestamp_str}" style="max-width: 90%; height: auto; display: block; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 5px; border: 1px solid #ccc; border-radius: 5px;"><br>'
                return f"{match.group(0)}{img_tag}"

            return match.group(0)

        final_html = timestamp_regex.sub(replacer, html_content)
        return final_html
