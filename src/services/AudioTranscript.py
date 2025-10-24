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
            self.progress.emit(10, "Audio pronto per la trascrizione.")

            audio_segment = AudioSegment.from_wav(standard_wav_path)

            language_video = self.main_window.languageComboBox.currentData()
            transcription = ""

            offset_ms = int(self.start_time * 1000) if self.start_time is not None else 0

            # Rileva i segmenti di non-silenzio
            nonsilent_chunks = detect_nonsilent(
                audio_segment,
                min_silence_len=700,
                silence_thresh=audio_segment.dBFS - 16,
                seek_step=1
            )

            if not nonsilent_chunks:
                self.error.emit("Nessun parlato rilevato nel file audio.")
                return

            total_chunks = len(nonsilent_chunks)
            last_end_time = 0

            for index, chunk_range in enumerate(nonsilent_chunks):
                if not self._is_running:
                    self.save_transcription_to_json(transcription, language_video)
                    return

                start_chunk, end_chunk = chunk_range

                # Calcola la pausa dall'ultimo segmento
                if last_end_time > 0:
                    pause_duration = (start_chunk - last_end_time) / 1000.0
                    if pause_duration > 1.0: # Pausa significativa
                        pause_start_seconds = (last_end_time + offset_ms) // 1000
                        pause_start_mins, pause_start_secs = divmod(pause_start_seconds, 60)
                        timestamp = f"[{pause_start_mins:02d}:{pause_start_secs:02d}]"
                        transcription += f'{timestamp}\n\n<break time="{pause_duration:.1f}s" />\n\n'

                chunk = audio_segment[start_chunk:end_chunk]
                text, _, _ = self.transcribeAudioChunk(chunk, start_chunk + offset_ms)

                start_seconds = (start_chunk + offset_ms) // 1000
                start_mins, start_secs = divmod(start_seconds, 60)
                timestamp = f"[{start_mins:02d}:{start_secs:02d}]"

                if text:
                    transcription += f"{timestamp}\n\n{text}\n\n"

                last_end_time = end_chunk

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
            audio_chunk.export(temp_audio_file_path, format="wav")

            with sr.AudioFile(temp_audio_file_path) as source:
                audio_data = recognizer.record(source)

            language_video = self.main_window.languageComboBox.currentData()
            locale = self.get_locale_from_language(language_video)
            text = recognizer.recognize_google(audio_data, language=locale)
            return text, start_time, language_video
        except sr.UnknownValueError:
            return None, start_time, None
        except sr.RequestError as e:
            return f"[Errore: {e}]", start_time, None
        except Exception as e:
            return f"[Errore: {e}]", start_time, None
        finally:
            if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                os.remove(temp_audio_file_path)