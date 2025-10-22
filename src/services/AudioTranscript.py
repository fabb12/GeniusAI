import os
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import pycountry
import speech_recognition as sr
import tempfile
import logging
from moviepy.editor import AudioFileClip
from pydub import AudioSegment
from pydub.silence import detect_nonsilent


class TranscriptionThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, media_path, parent=None, start_time=None, end_time=None, main_window=None):
        super().__init__(parent)
        self.media_path = media_path
        self.main_window = main_window if main_window else parent
        self._is_running = True
        self.partial_text = ""
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        standard_wav_path = None
        input_clip = None
        try:
            self.progress.emit(5, "Estrazione e standardizzazione audio...")

            input_clip = AudioFileClip(self.media_path)

            if self.start_time is not None and self.end_time is not None:
                self.progress.emit(6, f"Estrazione audio da {self.start_time:.2f}s a {self.end_time:.2f}s...")
                input_clip = input_clip.subclip(self.start_time, self.end_time)

            standard_wav_path = self.main_window.get_temp_filepath(suffix=".wav")
            input_clip.write_audiofile(standard_wav_path, codec='pcm_s16le', logger=None)
            self.progress.emit(10, "Audio pronto per l'analisi del silenzio.")

            sound = AudioSegment.from_wav(standard_wav_path)
            self.progress.emit(15, "Rilevamento delle parti non silenziose...")

            nonsilent_chunks = detect_nonsilent(sound, min_silence_len=1000, silence_thresh=-40)
            if not nonsilent_chunks:
                self.error.emit("Nessuna parte non silenziosa trovata. L'audio potrebbe essere completamente silenzioso.")
                return

            self.progress.emit(20, f"Trovati {len(nonsilent_chunks)} segmenti audio da trascrivere.")
            language_video = self.main_window.languageComboBox.currentData()
            transcription = ""
            last_end_ms = 0
            offset_ms = int(self.start_time * 1000) if self.start_time is not None else 0

            total_chunks = len(nonsilent_chunks)
            for i, (start_ms, end_ms) in enumerate(nonsilent_chunks):
                if not self._is_running:
                    self.save_transcription_to_json(transcription, language_video)
                    return

                if start_ms > last_end_ms:
                    pause_start_s = (last_end_ms + offset_ms) / 1000
                    pause_end_s = (start_ms + offset_ms) / 1000
                    transcription += f"[PAUSA] [{self.format_time(pause_start_s)}] - [{self.format_time(pause_end_s)}]\n\n"

                chunk_audio_clip = AudioFileClip(standard_wav_path).subclip(start_ms / 1000, end_ms / 1000)
                text, _, _ = self.transcribeAudioChunk(chunk_audio_clip, start_ms + offset_ms)

                start_s = (start_ms + offset_ms) / 1000
                end_s = (end_ms + offset_ms) / 1000
                timestamp = f"[{self.format_time(start_s)}] - [{self.format_time(end_s)}]"
                transcription += f"{timestamp}\n{text}\n\n"

                last_end_ms = end_ms
                self.partial_text = transcription
                progress_percentage = int(((i + 1) / total_chunks) * 80) + 20
                self.progress.emit(progress_percentage, f"Trascrizione {i + 1}/{total_chunks}")
                chunk_audio_clip.close()

            duration_ms = len(sound)
            if last_end_ms < duration_ms:
                pause_start_s = (last_end_ms + offset_ms) / 1000
                pause_end_s = (duration_ms + offset_ms) / 1000
                transcription += f"[PAUSA] [{self.format_time(pause_start_s)}] - [{self.format_time(pause_end_s)}]\n\n"

            json_path = self.save_transcription_to_json(transcription, language_video)
            self.completed.emit((json_path, []))

        except Exception as e:
            self.error.emit(str(e))
            logging.error(f"Errore nella trascrizione: {e}", exc_info=True)
        finally:
            if input_clip:
                input_clip.close()
            if standard_wav_path and os.path.exists(standard_wav_path):
                os.remove(standard_wav_path)

    def format_time(self, seconds):
        """Formatta i secondi in HH:MM:SS."""
        td = datetime.timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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

    def get_partial_transcription(self):
        return self.partial_text

    def get_locale_from_language(self, language_code):
        try:
            language = pycountry.languages.get(alpha_2=language_code)
            locale = {'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'it': 'it-IT', 'de': 'de-DE'}.get(language.alpha_2, f"{language.alpha_2}-{language.alpha_2.upper()}")
            return locale
        except Exception:
            return language_code

    def transcribeAudioChunk(self, audio_chunk, start_time):
        recognizer = sr.Recognizer()
        temp_audio_file_path = None
        try:
            temp_audio_file_path = self.main_window.get_temp_filepath(suffix=".wav")
            audio_chunk.write_audiofile(temp_audio_file_path, codec='pcm_s16le', logger=None)

            with sr.AudioFile(temp_audio_file_path) as source:
                audio_data = recognizer.record(source)

            language_video = self.main_window.languageComboBox.currentData()
            locale = self.get_locale_from_language(language_video)
            text = recognizer.recognize_google(audio_data, language=locale)
            return text, start_time, language_video
        except sr.UnknownValueError:
            return "[Incomprensibile]", start_time, None
        except sr.RequestError as e:
            return f"[Errore: {e}]", start_time, None
        except Exception as e:
            return f"[Errore: {e}]", start_time, None
        finally:
            if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                os.remove(temp_audio_file_path)