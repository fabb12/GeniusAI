import os
import json
import datetime
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
import logging
from moviepy.editor import AudioFileClip

# Import for Whisper
import whisper
import torch
from src.config import FFMPEG_PATH
from os import pathsep

class WhisperTranscriptionThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(tuple)
    error = pyqtSignal(str)

    # Class-level cache for the Whisper model to avoid reloading
    _whisper_model = None
    _model_name = None
    _model_lock = threading.Lock()

    def __init__(self, media_path, parent=None, start_time=None, end_time=None, main_window=None, model_name="base", use_gpu=True):
        super().__init__(parent)
        self.media_path = media_path
        self.main_window = main_window if main_window else parent
        self._is_running = True
        self.start_time = start_time
        self.end_time = end_time
        self.model_name = model_name
        self.use_gpu = use_gpu

    @classmethod
    def load_model(cls, model_name='base', use_gpu=True, progress_signal=None):
        with cls._model_lock:
            if cls._whisper_model is None or cls._model_name != model_name:
                try:
                    load_start_time = time.time()
                    logging.info(f"Loading Whisper model: {model_name}")
                    if progress_signal:
                        progress_signal.emit(16, f"Downloading model '{model_name}'...")

                    device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
                    logging.info(f"Using device: {device} for Whisper model.")

                    cls._whisper_model = whisper.load_model(model_name, device=device)
                    cls._model_name = model_name
                    load_end_time = time.time()
                    logging.info(f"Whisper model '{model_name}' loaded successfully on {device} in {load_end_time - load_start_time:.2f} seconds.")

                    if device == 'cuda':
                        logging.info(f"VRAM Usage:\n{torch.cuda.memory_summary(device=device, abbreviated=False)}")

                except Exception as e:
                    logging.error(f"Failed to load Whisper model: {e}")
                    cls._whisper_model = None
                    cls._model_name = None
                    raise e
        return cls._whisper_model

    def run(self):
        overall_start_time = time.time()
        standard_wav_path = None
        input_clip = None
        try:
            # --- Audio Extraction ---
            audio_extraction_start_time = time.time()
            self.progress.emit(5, "Estrazione e standardizzazione audio...")
            input_clip = AudioFileClip(self.media_path)

            if self.start_time is not None and self.end_time is not None:
                self.progress.emit(6, f"Estrazione audio da {self.start_time:.2f}s a {self.end_time:.2f}s...")
                input_clip = input_clip.subclip(self.start_time, self.end_time)

            standard_wav_path = self.main_window.get_temp_filepath(suffix=".wav")
            input_clip.write_audiofile(standard_wav_path, codec='pcm_s16le', fps=16000, logger=None)
            audio_extraction_end_time = time.time()
            logging.info(f"Audio extracted in {audio_extraction_end_time - audio_extraction_start_time:.2f} seconds.")
            self.progress.emit(10, "Audio pronto per la trascrizione.")

            # --- Environment Setup for FFmpeg ---
            original_path = os.environ["PATH"]
            ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
            os.environ["PATH"] = ffmpeg_dir + pathsep + original_path

            # --- Model Loading ---
            model = self.load_model(self.model_name, self.use_gpu, self.progress)

            # --- Transcription ---
            transcription_start_time = time.time()
            self.progress.emit(25, "Trascrizione in corso con Whisper...")
            language_code = self.main_window.languageComboBox.currentData()

            result = model.transcribe(
                standard_wav_path,
                language=language_code if language_code != 'auto' else None,
                fp16=self.use_gpu and torch.cuda.is_available(),
                verbose=False # Set to True for debugging Whisper's internal progress
            )
            transcription_end_time = time.time()
            logging.info(f"Whisper transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds.")
            logging.info(f"Detected language: {result.get('language')}")

            # --- Formatting Output ---
            transcription = ""
            last_end_time = 0.0
            offset_seconds = self.start_time if self.start_time is not None else 0.0

            total_segments = len(result['segments'])
            for i, segment in enumerate(result['segments']):
                if not self._is_running:
                    self.save_transcription_to_json(transcription, result.get('language', language_code))
                    return

                start_segment = segment['start']
                end_segment = segment['end']
                text = segment['text'].strip()
                avg_logprob = segment.get('avg_logprob', -1.0)
                no_speech_prob = segment.get('no_speech_prob', 0.0)

                confidence_threshold = -0.5  # Adjust this threshold as needed

                # Annotate text with confidence if below threshold or if no_speech_prob is high
                if avg_logprob < confidence_threshold or no_speech_prob > 0.6:
                    confidence_percent = round((1 + avg_logprob) * 100, 1) if avg_logprob != -1.0 else 0
                    text += f" (Confidence: {confidence_percent}%)"

                # Calculate and insert break tags for silences > 1s
                if last_end_time > 0:
                    pause_duration = start_segment - last_end_time
                    if pause_duration > 1.0:
                        pause_start_seconds = int(last_end_time + offset_seconds)
                        pause_mins, pause_secs = divmod(pause_start_seconds, 60)
                        timestamp = f"[{pause_mins:02d}:{pause_secs:02d}]"
                        transcription += f'{timestamp}\n\n<break time="{pause_duration:.1f}s" />\n\n'

                # Format the timestamp for the current segment
                start_seconds_with_offset = int(start_segment + offset_seconds)
                start_mins, start_secs = divmod(start_seconds_with_offset, 60)
                timestamp = f"[{start_mins:02d}:{start_secs:02d}]"

                if text:
                    transcription += f"{timestamp}\n\n{text}\n\n"

                last_end_time = end_segment

                progress_percentage = 30 + int(((i + 1) / total_segments) * 65)
                self.progress.emit(progress_percentage, f"Elaborazione segmento {i + 1}/{total_segments}")

            self.progress.emit(100, "Trascrizione completata.")
            json_path = self.save_transcription_to_json(transcription, result.get('language', language_code))
            self.completed.emit((json_path, [standard_wav_path]))

        except torch.cuda.OutOfMemoryError:
            error_msg = f"Memoria GPU esaurita con il modello '{self.model_name}'. Prova a usare un modello più piccolo o disabilita l'uso della GPU."
            logging.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            import traceback
            logging.error(f"Errore nella trascrizione Whisper: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Si è verificato un errore imprevisto: {e}")
        finally:
            if 'original_path' in locals():
                os.environ["PATH"] = original_path
            if input_clip:
                input_clip.close()
            if standard_wav_path and os.path.exists(standard_wav_path):
                os.remove(standard_wav_path)
            overall_end_time = time.time()
            logging.info(f"TranscriptionThread finished in {overall_end_time - overall_start_time:.2f} seconds.")

    def save_transcription_to_json(self, transcription, language_code):
        json_path = os.path.splitext(self.media_path)[0] + ".json"
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data['language'] = language_code
        data['transcription_date'] = datetime.datetime.now().isoformat()
        data['transcription_raw'] = transcription
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return json_path

    def stop(self):
        self._is_running = False
