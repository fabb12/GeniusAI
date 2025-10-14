import os
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import pycountry
import speech_recognition as sr
import tempfile
import logging
from moviepy.editor import AudioFileClip


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
        audio_clip_for_chunking = None
        try:
            self.progress.emit(5, "Estrazione e standardizzazione audio...")

            input_clip = AudioFileClip(self.media_path)

            # Se sono specificati start_time e end_time, taglia la clip
            if self.start_time is not None and self.end_time is not None:
                self.progress.emit(6, f"Estrazione audio da {self.start_time:.2f}s a {self.end_time:.2f}s...")
                input_clip = input_clip.subclip(self.start_time, self.end_time)

            # Standardizza in un file WAV temporaneo
            standard_wav_path = self.main_window.get_temp_filepath(suffix=".wav")
            input_clip.write_audiofile(standard_wav_path, codec='pcm_s16le', logger=None)
            input_clip.close()
            self.progress.emit(10, "Audio pronto per la trascrizione.")

            # Step 2: Process the standardized WAV file.
            audio_clip_for_chunking = AudioFileClip(standard_wav_path)
            duration = audio_clip_for_chunking.duration
            if duration <= 0:
                raise ValueError("La durata dell'audio è non valida o negativa.")

            language_video = self.main_window.languageComboBox.currentData()
            transcription = ""

            # Unified chunking logic for all audio lengths
            length = 30000  # 30 seconds
            # Calcola l'offset iniziale basato sul tempo di inizio della trascrizione parziale
            offset_ms = int(self.start_time * 1000) if self.start_time is not None else 0

            chunks = [
                (audio_clip_for_chunking.subclip(start / 1000, min((start + length) / 1000, duration)), start + offset_ms)
                for start in range(0, int(duration * 1000), length)
            ]

            total_chunks = len(chunks)

            for index, (chunk, start_time_ms) in enumerate(chunks):
                if not self._is_running:
                    self.save_transcription_to_json(transcription, language_video)
                    return

                text, _, _ = self.transcribeAudioChunk(chunk, start_time_ms)

                # Calcola i timestamp di inizio e fine
                start_seconds = start_time_ms // 1000
                end_seconds = start_seconds + int(chunk.duration)
                start_mins, start_secs = divmod(start_seconds, 60)
                end_mins, end_secs = divmod(end_seconds, 60)

                # Formatta il timestamp come [MM:SS] - [MM:SS]
                timestamp = f"[{start_mins:02d}:{start_secs:02d}] - [{end_mins:02d}:{end_secs:02d}]"
                transcription += f'{timestamp}\n"{text}"\n\n'

                self.partial_text = transcription
                progress_percentage = int(((index + 1) / total_chunks) * 100)
                self.progress.emit(progress_percentage, f"Trascrizione {index + 1}/{total_chunks}")

            json_path = self.save_transcription_to_json(transcription, language_video)
            self.completed.emit((json_path, []))

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if input_clip:
                input_clip.close()
            if audio_clip_for_chunking:
                audio_clip_for_chunking.close()
            if standard_wav_path and os.path.exists(standard_wav_path):
                os.remove(standard_wav_path)

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