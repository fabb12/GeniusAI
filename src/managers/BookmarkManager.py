import os
import datetime
import logging
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips
from src.services.utils import generate_unique_filename
from src.services.AudioTranscript import TranscriptionThread
import json

class BookmarkCutThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, bookmarks, media_path, is_audio_only, parent=None):
        super().__init__(parent)
        self.bookmarks = bookmarks
        self.media_path = media_path
        self.is_audio_only = is_audio_only
        self.running = True

    def run(self):
        final_media = None
        media_clip = None
        try:
            self.progress.emit(5, "Caricamento media...")
            media_clip = AudioFileClip(self.media_path) if self.is_audio_only else VideoFileClip(self.media_path)

            total_segments = len(self.bookmarks)
            clips = []

            for i, (start_ms, end_ms) in enumerate(sorted(self.bookmarks)):
                if not self.running: return
                progress_percent = 10 + int((i / total_segments) * 50)
                self.progress.emit(progress_percent, f"Estrazione segmento {i+1}/{total_segments}...")

                start_time = start_ms / 1000.0
                end_time = end_ms / 1000.0
                clips.append(media_clip.subclip(start_time, end_time))

            if not clips:
                self.error.emit("Nessun clip valido da tagliare.")
                return

            if not self.running: return
            self.progress.emit(60, "Unione dei segmenti...")
            final_media = concatenate_audioclips(clips) if self.is_audio_only else concatenate_videoclips(clips, method="compose")

            base_name = os.path.splitext(os.path.basename(self.media_path))[0]
            directory = os.path.dirname(self.media_path)
            ext = ".mp3" if self.is_audio_only else ".mp4"
            output_path = generate_unique_filename(os.path.join(directory, f"{base_name}_cut{ext}"))

            if not self.running: return
            self.progress.emit(80, "Salvataggio file finale...")
            if self.is_audio_only:
                final_media.write_audiofile(output_path, logger=None)
            else:
                final_media.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=None)

            if self.running:
                self.progress.emit(100, "Completato.")
                self.completed.emit(output_path)

        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            if media_clip: media_clip.close()
            if final_media:
                if self.is_audio_only:
                    if hasattr(final_media, 'close'): final_media.close()
                else:
                    if hasattr(final_media, 'audio') and final_media.audio: final_media.audio.close()
                    if hasattr(final_media, 'mask') and final_media.mask: final_media.mask.close()
                    if hasattr(final_media, 'close'): final_media.close()
            if final_media:
                if self.is_audio_only:
                    if hasattr(final_media, 'close'): final_media.close()
                else:
                    if hasattr(final_media, 'audio') and final_media.audio: final_media.audio.close()
                    if hasattr(final_media, 'mask') and final_media.mask: final_media.mask.close()
                    if hasattr(final_media, 'close'): final_media.close()

    def stop(self):
        self.running = False

class BookmarkDeleteThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, bookmarks, media_path, is_audio_only, parent=None):
        super().__init__(parent)
        self.bookmarks = bookmarks
        self.media_path = media_path
        self.is_audio_only = is_audio_only
        self.running = True

    def run(self):
        media_clip = None
        try:
            self.progress.emit(5, "Caricamento media...")
            media_clip = AudioFileClip(self.media_path) if self.is_audio_only else VideoFileClip(self.media_path)

            clips_to_keep = []
            last_end_time = 0.0
            total_segments = len(self.bookmarks)

            for i, (start_ms, end_ms) in enumerate(sorted(self.bookmarks)):
                if not self.running: return
                progress_percent = 10 + int((i / total_segments) * 50)
                self.progress.emit(progress_percent, f"Analisi segmento da rimuovere {i+1}/{total_segments}...")

                start_time = start_ms / 1000.0
                end_time = end_ms / 1000.0
                if start_time > last_end_time:
                    clips_to_keep.append(media_clip.subclip(last_end_time, start_time))
                last_end_time = end_time

            if last_end_time < media_clip.duration:
                clips_to_keep.append(media_clip.subclip(last_end_time))

            if not clips_to_keep:
                self.error.emit("L'operazione cancellerebbe l'intero file.")
                return

            if not self.running: return
            self.progress.emit(60, "Unione dei segmenti da conservare...")
            final_media = concatenate_audioclips(clips_to_keep) if self.is_audio_only else concatenate_videoclips(clips_to_keep, method="compose")

            ext = ".mp3" if self.is_audio_only else ".mp4"
            output_path = generate_unique_filename(os.path.join(os.path.dirname(self.media_path), f"modified_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"))

            if not self.running: return
            self.progress.emit(80, "Salvataggio file modificato...")
            if self.is_audio_only:
                final_media.write_audiofile(output_path, logger=None)
            else:
                final_media.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=None)

            if self.running:
                self.progress.emit(100, "Completato.")
                self.completed.emit(output_path)

        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            if media_clip: media_clip.close()

    def stop(self):
        self.running = False

class BookmarkManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.bookmarks_to_transcribe = []
        self.current_bookmark_index = 0
        self.combined_transcription_html = ""

    def transcribe_all_bookmarks(self):
        """
        Initiates the sequential transcription of all bookmarked segments.
        """
        bookmarks = self.main_window.videoSlider.bookmarks
        if not bookmarks:
            self.main_window.show_status_message("Nessun bookmark impostato per la trascrizione.", error=True)
            return

        reply = QMessageBox.question(
            self.main_window,
            "Conferma Trascrizione",
            f"Verranno trascritti i {len(bookmarks)} segmenti video selezionati. Continuare?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self.bookmarks_to_transcribe = sorted(bookmarks)
        self.current_bookmark_index = 0
        self.combined_transcription_html = ""
        self.main_window.transcriptionTextArea.clear()

        self._transcribe_next_segment()

    def _transcribe_next_segment(self):
        """
        Transcribes the next segment in the queue.
        """
        if self.current_bookmark_index >= len(self.bookmarks_to_transcribe):
            self.main_window.show_status_message("Trascrizione di tutti i segmenti completata.")
            # Set the final combined HTML
            self.main_window.transcriptionTextArea.setHtml(self.combined_transcription_html)
            self.main_window.onProcessComplete({
                'transcription_raw': self.combined_transcription_html
            })
            return

        start_ms, end_ms = self.bookmarks_to_transcribe[self.current_bookmark_index]
        start_time_sec = start_ms / 1000.0
        end_time_sec = end_ms / 1000.0

        self.main_window.show_status_message(f"Trascrizione del segmento {self.current_bookmark_index + 1}/{len(self.bookmarks_to_transcribe)}...")

        thread = TranscriptionThread(
            media_path=self.main_window.videoPathLineEdit.text(),
            main_window=self.main_window,
            start_time=start_time_sec,
            end_time=end_time_sec
        )

        # Use the main window's task manager to run the thread
        self.main_window.start_task(
            thread,
            on_complete=self._on_segment_transcribed,
            on_error=self._on_transcription_error,
            on_progress=self._on_transcription_progress
        )

    def _on_segment_transcribed(self, result):
        """
        Callback function for when a single segment transcription is complete.
        """
        json_path, temp_files = result
        segment_html = ""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Get the raw transcription for this segment
            segment_html = data.get('transcription_raw', '')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Errore nel leggere il JSON del segmento: {e}")
            segment_html = f"<p><i>Errore nella trascrizione del segmento {self.current_bookmark_index + 1}.</i></p>"

        # Clean up temporary files for the segment
        self.main_window.cleanupFiles(temp_files)

        # Add a header for the segment
        start_ms, end_ms = self.bookmarks_to_transcribe[self.current_bookmark_index]
        start_time_str = self.main_window.formatTimecode(start_ms)
        end_time_str = self.main_window.formatTimecode(end_ms)
        header = f"<hr><h4>Segmento {self.current_bookmark_index + 1} ({start_time_str} - {end_time_str})</h4>"

        # Append to the combined HTML and update the display
        self.combined_transcription_html += header + segment_html
        self.main_window.transcriptionTextArea.setHtml(self.combined_transcription_html)
        self.main_window.transcriptionTextArea.verticalScrollBar().setValue(self.main_window.transcriptionTextArea.verticalScrollBar().maximum())


        # Move to the next segment
        self.current_bookmark_index += 1
        self._transcribe_next_segment()

    def _on_transcription_progress(self, value, label):
        """
        Updates the progress bar and status for the current segment.
        """
        total_segments = len(self.bookmarks_to_transcribe)
        current_segment_num = self.current_bookmark_index + 1

        # Calculate overall progress
        # Each segment contributes 1/total_segments to the total progress.
        base_progress = int((self.current_bookmark_index / total_segments) * 100)
        segment_progress = int(value / total_segments)
        overall_progress = base_progress + segment_progress

        status_label = f"Segmento {current_segment_num}/{total_segments}: {label}"
        self.main_window.update_status_progress(overall_progress, status_label)

    def _on_transcription_error(self, error_message):
        """
        Handles an error during a segment's transcription.
        """
        logging.error(f"Errore durante la trascrizione del segmento {self.current_bookmark_index + 1}: {error_message}")
        self.main_window.show_status_message(f"Errore nel segmento {self.current_bookmark_index + 1}. Salto al successivo.", error=True)

        header = f"<hr><h4>Segmento {self.current_bookmark_index + 1}</h4>"
        error_html = f"<p><i>Trascrizione fallita: {error_message}</i></p>"
        self.combined_transcription_html += header + error_html
        self.main_window.transcriptionTextArea.setHtml(self.combined_transcription_html)

        # Try to continue with the next segment
        self.current_bookmark_index += 1
        self._transcribe_next_segment()

    def cut_all_bookmarks(self):
        bookmarks = self.main_window.videoSlider.bookmarks
        if not bookmarks:
            self.main_window.show_status_message("Nessun bookmark impostato per il taglio.", error=True)
            return

        media_path = self.main_window.videoPathLineEdit
        if not media_path:
            self.main_window.show_status_message("Nessun file media caricato.", error=True)
            return

        is_audio_only = self.main_window.isAudioOnly(media_path)

        thread = BookmarkCutThread(bookmarks, media_path, is_audio_only, self.main_window)
        self.main_window.start_task(
            thread,
            on_complete=self._on_operation_completed,
            on_error=self._on_operation_error,
            on_progress=self.main_window.update_status_progress
        )

    def delete_all_bookmarks(self):
        bookmarks = self.main_window.videoSlider.bookmarks
        if not bookmarks:
            self.main_window.show_status_message("Nessun bookmark impostato per l'eliminazione.", error=True)
            return

        media_path = self.main_window.videoPathLineEdit
        if not media_path:
            self.main_window.show_status_message("Nessun file media caricato.", error=True)
            return

        is_audio_only = self.main_window.isAudioOnly(media_path)

        thread = BookmarkDeleteThread(bookmarks, media_path, is_audio_only, self.main_window)
        self.main_window.start_task(
            thread,
            on_complete=self._on_operation_completed,
            on_error=self._on_operation_error,
            on_progress=self.main_window.update_status_progress
        )

    def _on_operation_completed(self, output_path):
        self.main_window.show_status_message(f"Operazione completata. File salvato in: {os.path.basename(output_path)}")
        self.main_window.loadVideoOutput(output_path)

    def _on_operation_error(self, error_message):
        self.main_window.show_status_message(f"Errore durante l'operazione: {error_message}", error=True)