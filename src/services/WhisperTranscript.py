import os
import json
import datetime
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
import logging
from moviepy.editor import AudioFileClip
import concurrent.futures

# Import for Whisper
import whisper
import torch
from urllib.error import URLError
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
        self.transcribe_future = None
        self.executor = None

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

                    models_dir = "models"
                    if not os.path.exists(models_dir):
                        os.makedirs(models_dir)

                    cls._whisper_model = whisper.load_model(model_name, device=device, download_root=models_dir)
                    cls._model_name = model_name
                    load_end_time = time.time()
                    logging.info(f"Whisper model '{model_name}' loaded successfully on {device} in {load_end_time - load_start_time:.2f} seconds.")

                    if device == 'cuda':
                        logging.info(f"VRAM Usage:\n{torch.cuda.memory_summary(device=device, abbreviated=False)}")

                except URLError as e:
                    error_msg = f"Network error downloading Whisper model '{model_name}'. Check your internet connection, firewall, or proxy settings. Details: {e}"
                    logging.error(error_msg)
                    cls._whisper_model = None
                    cls._model_name = None
                    raise Exception(error_msg) from e
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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        try:
            if not self._is_running: return
            # --- Audio Extraction ---
            self.progress.emit(5, "Estrazione e standardizzazione audio...")
            input_clip = AudioFileClip(self.media_path)
            if self.start_time is not None and self.end_time is not None:
                input_clip = input_clip.subclip(self.start_time, self.end_time)
            standard_wav_path = self.main_window.get_temp_filepath(suffix=".wav")
            input_clip.write_audiofile(standard_wav_path, codec='pcm_s16le', fps=16000, logger=None)
            self.progress.emit(10, "Audio pronto per la trascrizione.")

            if not self._is_running: return
            original_path = os.environ.get("PATH", "")
            ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
            os.environ["PATH"] = ffmpeg_dir + pathsep + original_path

            model = self.load_model(self.model_name, self.use_gpu, self.progress)
            if not model:
                self.error.emit("Failed to load Whisper model.")
                return

            # --- Transcription in a separate thread ---
            self.progress.emit(25, "Trascrizione in corso con Whisper...")
            language_code = self.main_window.languageComboBox.currentData()
            self.transcribe_future = self.executor.submit(
                model.transcribe,
                standard_wav_path,
                language=language_code if language_code != 'auto' else None,
                fp16=self.use_gpu and torch.cuda.is_available(),
                verbose=False
            )

            # Wait for the future to complete, periodically checking the running flag
            while self._is_running and not self.transcribe_future.done():
                time.sleep(0.2) # Check for cancellation every 200ms

            if not self._is_running:
                logging.info("Transcription cancelled by user during execution.")
                # The future continues in the background, but we exit the thread.
                return

            result = self.transcribe_future.result() # Get result if done
            logging.info(f"Whisper transcription completed. Detected language: {result.get('language')}")

            if not self._is_running: return
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

                if last_end_time > 0:
                    pause_duration = start_segment - last_end_time
                    if pause_duration > 1.0:
                        transcription += f'<p><break time="{pause_duration:.1f}s" /></p>'

                start_seconds_with_offset = int(start_segment + offset_seconds)
                start_mins, start_secs = divmod(start_seconds_with_offset, 60)
                timestamp = f"[{start_mins:02d}:{start_secs:02d}]"

                if text:
                    transcription += f"<p>{timestamp}</p><p>{text}</p>"

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
            if self._is_running: # Only emit error if not cancelled
                import traceback
                logging.error(f"Errore nella trascrizione Whisper: {e}\n{traceback.format_exc()}")
                self.error.emit(f"Si è verificato un errore imprevisto: {e}")
        finally:
            # --- Cleanup ---
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=True)
            if 'original_path' in locals():
                os.environ["PATH"] = original_path
            if input_clip:
                input_clip.close()
            if standard_wav_path and os.path.exists(standard_wav_path):
                try:
                    os.remove(standard_wav_path)
                except OSError as e:
                    logging.warning(f"Could not remove temporary audio file {standard_wav_path}: {e}")
            overall_end_time = time.time()
            logging.info(f"WhisperTranscriptionThread finished in {overall_end_time - overall_start_time:.2f} seconds.")

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
        """
        Stops the QThread from processing further.
        Note: This will not interrupt the underlying Whisper `transcribe` call if it
        is already running, as it's a blocking operation in a separate thread.
        The worker thread will run to completion, but its result will be discarded.
        """
        logging.info("Stopping WhisperTranscriptionThread.")
        self._is_running = False
