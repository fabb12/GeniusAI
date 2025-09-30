import os
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import pycountry
import speech_recognition as sr
import tempfile
import logging
from moviepy.editor import AudioFileClip, VideoFileClip


class TranscriptionThread(QThread):
    progress = pyqtSignal(int, str)  # Signal for updating progress with an index and message
    completed = pyqtSignal(tuple)  # Signal when transcription is complete, including temporary files to clean
    error = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self._is_running = True
        self.partial_text = ""

    def run(self):
        audio_file = None
        audio_clip = None
        try:
            if os.path.splitext(self.media_path)[1].lower() in ['.wav', '.mp3', '.flac', '.aac']:
                audio_file = self.media_path
            else:
                audio_file = self.convertVideoToAudio(self.media_path)
                if not audio_file or not os.path.exists(audio_file):
                    raise Exception("La conversione del video in audio è fallita.")

            audio_clip = AudioFileClip(audio_file)
            if audio_clip.duration <= 0:
                raise ValueError("La durata dell'audio è non valida o negativa.")

            length = 30000  # 30 secondi in millisecondi
            chunks = [
                (audio_clip.subclip(start / 1000, min((start + length) / 1000, audio_clip.duration)), start)
                for start in range(0, int(audio_clip.duration * 1000), length)
            ]
            total_chunks = len(chunks)
            transcription = ""
            language_video = self.parent().languageComboBox.currentData()

            for index, (chunk, start_time) in enumerate(chunks):
                if not self._is_running:
                    self.save_transcription_to_json(transcription, language_video)
                    return

                text, _, _ = self.transcribeAudioChunk(chunk, start_time)
                current_time_seconds = start_time // 1000
                start_mins, start_secs = divmod(current_time_seconds, 60)
                transcription += f"[{start_mins:02d}:{start_secs:02d}]\n{text}\n\n"
                self.partial_text = transcription
                progress_percentage = int(((index + 1) / total_chunks) * 100)
                self.progress.emit(progress_percentage, f"Trascrizione {index + 1}/{total_chunks}")

            json_path = self.save_transcription_to_json(transcription, language_video)
            self.completed.emit((json_path, []))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if audio_clip:
                audio_clip.close()
            if audio_file and audio_file != self.media_path and os.path.exists(audio_file):
                os.remove(audio_file)

    def save_transcription_to_json(self, transcription, language_code):
        json_path = os.path.splitext(self.media_path)[0] + ".json"

        # Leggi i dati esistenti
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Se il file non esiste o è corrotto, crea un nuovo dizionario
            data = {}

        # Aggiorna i campi
        data['language'] = language_code
        data['transcription_date'] = datetime.datetime.now().isoformat()
        data['transcription_raw'] = transcription

        # Salva i dati aggiornati
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return json_path

    def stop(self):
        self._is_running = False

    def get_partial_transcription(self):
        return self.partial_text

    def convertVideoToAudio(self, video_file, audio_format='wav'):
        """Estrae la traccia audio dal video e la converte in formato WAV mantenendo tutto in memoria."""
        logging.debug("Checkpoint: Inside convertVideoToAudio")  # Checkpoint
        # Carica il clip video usando moviepy
        video = VideoFileClip(video_file)
        audio = video.audio

        # Converti l'audio in formato WAV e salvalo in un file temporaneo
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            audio.write_audiofile(temp_audio_file.name, codec='pcm_s16le')
            temp_audio_file_path = temp_audio_file.name

        # Chiudi i clip per liberare le risorse
        audio.close()
        video.close()

        return temp_audio_file_path

    def get_locale_from_language(self, language_code):
        """Converte un codice di lingua ISO 639-1 in un locale più specifico."""
        logging.debug(f"Checkpoint: Converting language code {language_code} to locale")  # Checkpoint
        try:
            language = pycountry.languages.get(alpha_2=language_code)
            logging.debug(f"Checkpoint: Language object obtained - {language}")  # Checkpoint
            locale = {
                'en': 'en-US',
                'es': 'es-ES',
                'fr': 'fr-FR',
                'it': 'it-IT',
                'de': 'de-DE'
            }.get(language.alpha_2, f"{language.alpha_2}-{language.alpha_2.upper()}")
            logging.debug(f"Checkpoint: Locale determined - {locale}")  # Checkpoint
            return locale
        except Exception as e:
            logging.debug(f"Checkpoint: Exception in get_locale_from_language - {e}")  # Checkpoint
            return language_code  # Ritorna il codice originale se la mappatura fallisce

    def transcribeAudioChunk(self, audio_chunk, start_time):
        logging.debug("Checkpoint: Inside transcribeAudioChunk")  # Checkpoint
        recognizer = sr.Recognizer()

        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
                audio_chunk.write_audiofile(temp_audio_file.name, codec='pcm_s16le')
                temp_audio_file_path = temp_audio_file.name

            with sr.AudioFile(temp_audio_file_path) as source:
                audio_data = recognizer.record(source)
                language_video = self.parent().languageComboBox.currentData()  # Ottiene il codice lingua dalla comboBox
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
            if os.path.exists(temp_audio_file_path):
                os.remove(temp_audio_file_path)