# src/services/OperationalGuideThread.py

import logging
import base64
import re
import json
from PyQt6.QtCore import QThread, pyqtSignal

from src.services.FrameExtractor import FrameExtractor
from src.config import get_model_for_action, PROMPT_OPERATIONAL_GUIDE
import anthropic
import google.generativeai as genai

class OperationalGuideThread(QThread):
    """
    A thread that generates an operational guide from a video by analyzing its frames with a vision AI model.
    """
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, video_path, num_frames, language, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language
        self.extractor = FrameExtractor(video_path=video_path, num_frames=num_frames)
        self.selected_model = get_model_for_action('frame_extractor') # Use the same vision model

    def run(self):
        try:
            self.progress.emit(10, "Estrazione dei fotogrammi dal video...")
            frames = self.extractor.extract_frames()
            if not frames:
                self.error.emit("Impossibile estrarre i fotogrammi dal video.")
                return

            self.progress.emit(30, f"Analisi di {len(frames)} fotogrammi con {self.selected_model}...")

            guide_text = self._generate_guide_with_vision_model(frames)

            if guide_text:
                self.progress.emit(100, "Guida operativa generata con successo.")
                self.completed.emit(guide_text)
            else:
                self.error.emit("L'analisi dei fotogrammi non ha prodotto alcun risultato.")

        except Exception as e:
            logging.exception("Errore durante la generazione della guida operativa.")
            self.error.emit(str(e))

    def _generate_guide_with_vision_model(self, frames):
        """
        Sends frames to the selected vision model and returns the generated guide.
        """
        try:
            with open(PROMPT_OPERATIONAL_GUIDE, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            formatted_prompt = prompt_template.format(language=self.language)
        except Exception as e:
            raise RuntimeError(f"Impossibile leggere o formattare il file prompt della guida operativa: {e}")

        model_name_lower = self.selected_model.lower()

        if "claude" in model_name_lower:
            return self._generate_with_claude(frames, formatted_prompt)
        elif "gemini" in model_name_lower:
            return self._generate_with_gemini(frames, formatted_prompt)
        else:
            raise ValueError(f"Modello non supportato per la generazione di guide operative: {self.selected_model}")

    def _generate_with_claude(self, frames, system_prompt):
        self.extractor._init_anthropic_client()
        if not self.extractor.anthropic_client:
            raise ConnectionError("Client Anthropic non inizializzato.")

        messages = [{"role": "user", "content": []}]
        content_list = messages[0]["content"]

        for idx, frame in enumerate(frames):
            content_list.append({"type": "text", "text": f"Frame {idx + 1}:"})
            content_list.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": frame["data"]}
            })

        self.progress.emit(50, "Invio dei fotogrammi a Claude...")
        response = self.extractor.anthropic_client.messages.create(
            model=self.selected_model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )
        self.progress.emit(90, "Risposta ricevuta da Claude.")
        return response.content[0].text.strip()

    def _generate_with_gemini(self, frames, system_prompt):
        self.extractor._configure_gemini()

        gemini_content = []
        for idx, frame in enumerate(frames):
            gemini_content.append(f"Frame {idx + 1}:")
            try:
                image_bytes = base64.b64decode(frame["data"])
                img_part = {"mime_type": "image/jpeg", "data": image_bytes}
                gemini_content.append(img_part)
            except Exception as e:
                logging.error(f"Errore nella decodifica base64 per Gemini: {e}")
                continue

        # Gemini uses a different way to set the system prompt
        model = genai.GenerativeModel(self.selected_model, system_instruction=system_prompt)

        self.progress.emit(50, "Invio dei fotogrammi a Gemini...")
        response = model.generate_content(gemini_content)
        self.progress.emit(90, "Risposta ricevuta da Gemini.")

        try:
            return response.text
        except ValueError:
            logging.warning(f"Risposta di Gemini bloccata o non valida. Feedback: {response.prompt_feedback}")
            raise Exception(f"Risposta di Gemini bloccata. Causa: {response.prompt_feedback}")