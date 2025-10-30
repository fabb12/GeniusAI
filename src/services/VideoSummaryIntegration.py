# File: src/services/VideoSummaryIntegration.py
import logging
import re
import base64
import cv2
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

            # Step 2: Extract and analyze significant frames
            self.progress.emit(30, "Estrazione e analisi dei frame video significativi...")
            frame_info, frame_dict = self._extract_and_analyze_frames()
            if not frame_info:
                # If frame extraction fails, we can still proceed with the text summary
                logging.warning("Estrazione frame fallita o nessun frame significativo trovato. Procedo con il riassunto testuale.")
                self.completed.emit(convert_markdown_to_html(text_summary))
                return

            # Step 3: Integrate text summary with frame info
            self.progress.emit(60, "Integrazione del riassunto con le informazioni visive...")
            integrated_html = self._integrate_summary_with_frames(text_summary, frame_info)
            if not integrated_html:
                self.error.emit("L'integrazione del riassunto con i frame è fallita.")
                return

            # Step 4: Embed frame images into the final HTML
            self.progress.emit(80, "Incorporamento delle immagini nel riassunto finale...")
            final_html = self._embed_images_into_html(integrated_html, frame_dict)
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
        # We run this directly as it's a blocking call within our thread
        result, _, _ = summarizer._process_text_with_selected_model()
        return result

    def _extract_and_analyze_frames(self):
        """Extracts significant frames and gets their AI descriptions."""
        extractor = FrameExtractor(
            video_path=self.video_path,
            num_frames=20, # This is a placeholder, as extract_significant_frames is used
            language=self.language
        )

        # Use significant frames extraction
        extracted_frames = extractor.extract_significant_frames()
        if not extracted_frames:
            return None, None

        analyzed_data = extractor.analyze_frames_batch(extracted_frames, self.language)
        if not analyzed_data:
            return None, None

        # Create a string representation for the prompt
        frame_info_str = "\n".join(
            [f"- Timecode {item['timestamp']}: {item['description']}" for item in analyzed_data]
        )

        # Create a dictionary mapping timestamps (in seconds) to base64 image data
        frame_dict = {
            int(parse_timestamp_to_seconds(item['timestamp'])): next(
                (frame['data'] for frame in extracted_frames if abs(frame['timestamp'] - parse_timestamp_to_seconds(item['timestamp'])) < 0.1),
                None
            )
            for item in analyzed_data
        }

        return frame_info_str, frame_dict


    def _integrate_summary_with_frames(self, text_summary, frame_info):
        """Calls the AI to merge the text summary and frame descriptions."""
        prompt_vars = {
            'current_summary': convert_markdown_to_html(text_summary), # The prompt expects HTML
            'frame_info': frame_info
        }
        integrator = ProcessTextAI(
            mode="video_integration",
            language=self.language,
            prompt_vars=prompt_vars
        )
        result, _, _ = integrator._process_text_with_selected_model()
        return result

    def _embed_images_into_html(self, html_content, frame_dict):
        """Parses HTML, finds timestamps, and inserts corresponding base64 images."""

        # Regex to find timestamps like [MM:SS] or [HH:MM:SS]
        timestamp_regex = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')

        def replacer(match):
            timestamp_str = match.group(1)
            seconds = parse_timestamp_to_seconds(timestamp_str)

            # Find the closest matching frame in our dictionary
            closest_second = min(frame_dict.keys(), key=lambda k: abs(k - seconds))

            # Allow a small tolerance (e.g., 2 seconds) to find a match
            if abs(closest_second - seconds) <= 2:
                b64_image = frame_dict.get(closest_second)
                if b64_image:
                    img_tag = f'<br><img src="data:image/jpeg;base64,{b64_image}" alt="Frame at {timestamp_str}" style="max-width: 90%; height: auto; display: block; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 5px; border: 1px solid #ccc; border-radius: 5px;"><br>'
                    # Return the original timestamp plus the image tag
                    return f"{match.group(0)}{img_tag}"

            # If no close frame is found, return the original timestamp unmodified
            return match.group(0)

        # Substitute all found timestamps in the HTML content
        final_html = timestamp_regex.sub(replacer, html_content)
        return final_html
