import os
from PyQt6.QtCore import QThread, pyqtSignal
import pycountry
import speech_recognition as sr
import tempfile
import logging
from moviepy.editor import AudioFileClip, VideoFileClip
import sys
# Configura il logging
logging.basicConfig(filename='transcription_log.txt', level=logging.DEBUG, format='[%(asctime)s - %(levelname)s] - %(message)s')
# Reindirizza stdout e stderr a os.devnull per ignorare l'output
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')


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
                    logging.debug("Checkpoint: Stopping transcription")  # Checkpoint
                    self.transcription_complete.emit(transcription, [])  # Emit current transcription
                    return

                logging.debug(f"Checkpoint: Transcribing chunk {index + 1}/{total_chunks}")  # Checkpoint
                text, start_time, _ = self.transcribeAudioChunk(chunk, start_time)
                start_mins, start_secs = divmod(start_time // 1000, 60)
                current_time_in_seconds = (start_mins * 60) + start_secs

                if last_timestamp is None or (current_time_in_seconds - last_timestamp >= 30):
                    transcription += f"[{start_mins:02d}:{start_secs:02d}] {text}\n\n"
                    last_timestamp = current_time_in_seconds
                else:
                    transcription += f"{text}\n\n"

                self.partial_text = transcription  # Update partial transcription

                # Calculate the progress percentage
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

    def splitAudio(self, audio_input, length=60000):
        logging.debug("Checkpoint: Inside splitAudio")  # Checkpoint
        audio = AudioFileClip(audio_input)
        if audio.duration <= 0:
            raise ValueError("La durata dell'audio è non valida o negativa.")
        chunks = [(audio.subclip(i / 1000, min(i + length, audio.duration * 1000) / 1000), i) for i in range(0, int(audio.duration * 1000), length)]
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

        # Salva il chunk audio in un file temporaneo
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
                if temp_audio_file is None:
                    raise Exception("Failed to create temporary file")
                audio_chunk.write_audiofile(temp_audio_file.name, codec='pcm_s16le')
                temp_audio_file_path = temp_audio_file.name
            logging.debug(f"Checkpoint: Temporary audio file created at {temp_audio_file_path}")  # Checkpoint
        except Exception as e:
            logging.debug(f"Checkpoint: Error creating temporary audio file - {e}")  # Checkpoint
            return f"[Errore: {e}]", start_time, None

        try:
            with sr.AudioFile(temp_audio_file_path) as source:
                logging.debug("Checkpoint: Audio file loaded into recognizer")  # Checkpoint
                audio_data = recognizer.record(source)
                language_video = self.parent().languageComboBox.currentData()  # Ottiene il codice lingua dalla comboBox
                logging.debug(f"Checkpoint: Language video obtained from combo box - {language_video}")  # Checkpoint
                locale = self.get_locale_from_language(language_video)
                logging.debug(f"Checkpoint: Locale for recognition - {locale}")  # Checkpoint
                text = recognizer.recognize_google(audio_data, language=locale)
                logging.debug(f"Checkpoint: Successfully recognized text - {text}")  # Checkpoint
            return text, start_time, language_video
        except sr.UnknownValueError:
            logging.debug("Checkpoint: Speech recognition could not understand audio")  # Checkpoint
            return "[Incomprensibile]", start_time, language_video
        except sr.RequestError as e:
            logging.debug(f"Checkpoint: API request error - {e}")  # Checkpoint
            return f"[Errore: {e}]", start_time, language_video
        except Exception as e:
            logging.debug(f"Checkpoint: General error during transcription - {e}")  # Checkpoint
            return f"[Errore: {e}]", start_time, language_video
        finally:
            if os.path.exists(temp_audio_file_path):
                try:
                    os.remove(temp_audio_file_path)  # Elimina il file temporaneo
                    logging.debug(f"Checkpoint: Temporary audio file {temp_audio_file_path} removed")  # Checkpoint
                except Exception as e:
                    logging.debug(f"Checkpoint: Error removing temporary audio file - {e}")  # Checkpoint
