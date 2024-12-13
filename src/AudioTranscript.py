import os
from PyQt6.QtCore import QThread, pyqtSignal
import pycountry
import speech_recognition as sr
import tempfile
import logging
from moviepy.editor import AudioFileClip, VideoFileClip
import sys


class TranscriptionThread(QThread):
    update_progress = pyqtSignal(int, str)  # Signal for updating progress with an index and message
    transcription_complete = pyqtSignal(str, list)  # Signal when transcription is complete, including temporary files to clean
    error_occurred = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self._is_running = True  # Flag to control the running state of the thread
        self.partial_text = ""  # Initialize partial_text to store partial transcriptions

    def run(self):
        audio_file = None
        try:
            logging.debug("Checkpoint: Start transcription")  # Checkpoint
            if os.path.splitext(self.media_path)[1].lower() in ['.wav', '.mp3', '.flac', '.aac']:
                logging.debug(f"Checkpoint: Detected audio file format {os.path.splitext(self.media_path)[1].lower()}")  # Checkpoint
                audio_file = self.media_path
            else:
                logging.debug("Checkpoint: Converting video to audio")  # Checkpoint
                audio_file = self.convertVideoToAudio(self.media_path)
                if not audio_file or not os.path.exists(audio_file):
                    raise Exception("La conversione del video in audio è fallita.")

            logging.debug("Checkpoint: Splitting audio")  # Checkpoint
            chunks = self.splitAudio(audio_file)
            total_chunks = len(chunks)  # Total number of chunks for percentage calculation
            transcription = ""
            last_timestamp = None

            for index, (chunk, start_time) in enumerate(chunks):
                if not self._is_running:  # Check if the thread should stop
                    self.transcription_complete.emit(transcription, [])  # Emit current transcription
                    return

                logging.debug(f"Checkpoint: Transcribing chunk {index + 1}/{total_chunks}")  # Checkpoint
                text, start_time, _ = self.transcribeAudioChunk(chunk, start_time)

                # Calcola il timecode corrente
                current_time_seconds = start_time // 1000
                start_mins, start_secs = divmod(current_time_seconds, 60)

                # Aggiungi il timecode e la trascrizione
                transcription += f"[{start_mins:02d}:{start_secs:02d}]\n"
                transcription += f"{text}\n\n"

                self.partial_text = transcription  # Update partial transcription

                # Calcola la percentuale di progresso
                progress_percentage = int(((index + 1) / total_chunks) * 100)
                self.update_progress.emit(progress_percentage, f"Trascrizione {index + 1}/{total_chunks}")

            logging.debug("Checkpoint: Transcription complete")  # Checkpoint
            self.transcription_complete.emit(transcription, [])  # Emit completion with no temp files to clean
        except Exception as e:
            logging.debug(f"Checkpoint: Error occurred - {str(e)}")  # Checkpoint
            self.error_occurred.emit(str(e))
        finally:
            if audio_file and not audio_file.endswith(self.media_path):  # Elimina il file temporaneo solo se è stato creato da convertVideoToAudio
                if os.path.exists(audio_file):
                    os.remove(audio_file)

    def stop(self):
        self._is_running = False

    def get_partial_transcription(self):
        return self.partial_text  # Return the partial transcription text

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

    def splitAudio(self, audio_input, length=30000):  # 30 secondi in millisecondi
        logging.debug("Checkpoint: Inside splitAudio")  # Checkpoint
        audio = AudioFileClip(audio_input)

        if audio.duration <= 0:
            raise ValueError("La durata dell'audio è non valida o negativa.")

        # Dividi l'audio in blocchi di lunghezza fissa
        chunks = [
            (audio.subclip(start / 1000, min((start + length) / 1000, audio.duration)), start)
            for start in range(0, int(audio.duration * 1000), length)
        ]
        return chunks

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
