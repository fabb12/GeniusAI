import sys
import re
import shutil
import subprocess
import tempfile
import datetime
import time
import logging
import json
import markdown
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Librerie PyQt6
from PyQt6.QtCore import (Qt, QUrl, QEvent, QTimer, QPoint, QTime, QSettings)
from PyQt6.QtGui import (QIcon, QAction, QDesktopServices, QImage, QPixmap, QFont, QColor, QTextCharFormat)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QRadioButton, QLineEdit,
    QHBoxLayout, QGroupBox, QComboBox, QSpinBox, QFileDialog,
    QMessageBox, QSizePolicy, QProgressDialog, QToolBar, QSlider,
    QProgressBar, QTabWidget, QDialog,QTextEdit, QInputDialog, QDoubleSpinBox, QFrame,
    QStatusBar, QListWidget, QListWidgetItem, QMenu
)

# PyQtGraph (docking)
from pyqtgraph.dockarea.DockArea import DockArea
from src.ui.CustomDock import CustomDock
from src.ui.InfoDock import InfoDock

from moviepy.editor import (
    ImageClip, CompositeVideoClip, concatenate_audioclips,
    concatenate_videoclips, VideoFileClip, AudioFileClip, vfx, TextClip
)
from moviepy.audio.AudioClip import CompositeAudioClip
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

import numpy as np
import proglog
import pyaudio
from screeninfo import get_monitors
from bs4 import BeautifulSoup
from num2words import num2words
from langdetect import detect, LangDetectException
import pycountry
from difflib import SequenceMatcher

from src.ui.DownloadDialog import DownloadDialog
from src.services.AudioTranscript import TranscriptionThread
from src.services.AudioGenerationREST import AudioGenerationThread
from src.services.VideoCutting import VideoCuttingThread
from src.recorder.ScreenRecorder import ScreenRecorder
from src.managers.SettingsManager import DockSettingsManager
from src.ui.CustVideoWidget import CropVideoWidget
from src.ui.CustomSlider import CustomSlider
from src.managers.Settings import SettingsDialog
from src.ui.ScreenButton import ScreenButton
from src.ui.CustumTextEdit import CustomTextEdit
from src.services.PptxGeneration import PptxGeneration
from src.ui.PptxDialog import PptxDialog
from src.services.ProcessTextAI import ProcessTextAI
from src.ui.SplashScreen import SplashScreen
from src.services.ShareVideo import VideoSharingManager
from src.ui.MonitorPreview import MonitorPreview
from src.managers.StreamToLogger import setup_logging
from src.services.FrameExtractor import FrameExtractor
from src.services.VideoCropping import CropThread
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from src.ui.CropDialog import CropDialog
from src.ui.CursorOverlay import CursorOverlay
from src.ui.MultiLineInputDialog import MultiLineInputDialog
from src.ui.AddMediaDialog import AddMediaDialog
from src.config import (get_api_key, FFMPEG_PATH, FFMPEG_PATH_DOWNLOAD, VERSION_FILE,
                    MUSIC_DIR, DEFAULT_FRAME_COUNT, DEFAULT_AUDIO_CHANNELS,
                    DEFAULT_STABILITY, DEFAULT_SIMILARITY, DEFAULT_STYLE,
                    DEFAULT_FRAME_RATE, DEFAULT_VOICES, SPLASH_IMAGES_DIR,
                    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, get_resource, WATERMARK_IMAGE, HIGHLIGHT_COLORS)
import os
AudioSegment.converter = FFMPEG_PATH
from src.ui.VideoOverlay import VideoOverlay

from src.services.MeetingSummarizer import MeetingSummarizer
from src.services.CombinedAnalyzer import CombinedAnalyzer
from src.services.VideoIntegrator import VideoIntegrationThread
from src.managers.ProjectManager import ProjectManager
from src.ui.ProjectDock import ProjectDock
from src.services.VideoCompositing import VideoCompositingThread
import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import RGBColor


class ProjectClipsMergeThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, clips_paths, output_path, parent=None):
        super().__init__(parent)
        self.clips_paths = clips_paths
        self.output_path = output_path
        self.running = True

    def run(self):
        try:
            self.progress.emit(10, "Caricamento clip...")
            video_clips = [VideoFileClip(path) for path in self.clips_paths]

            if not self.running:
                return

            target_resolution = video_clips[0].size
            resized_clips = []
            for i, clip in enumerate(video_clips):
                if not self.running: return
                self.progress.emit(20 + int(i / len(video_clips) * 30), f"Controllo clip {i+1}...")
                if clip.size != target_resolution:
                    resized_clips.append(clip.resize(target_resolution))
                else:
                    resized_clips.append(clip)

            self.progress.emit(50, "Unione delle clip...")
            final_clip = concatenate_videoclips(resized_clips, method="compose")

            if not self.running:
                return

            self.progress.emit(80, "Salvataggio video finale...")
            final_clip.write_videofile(self.output_path, codec='libx264', audio_codec='aac')

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(self.output_path)

        except Exception as e:
            if self.running:
                self.error.emit(f"Errore durante l'unione: {e}")
        finally:
            for clip in video_clips:
                clip.close()

    def stop(self):
        self.running = False


class MediaOverlayThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, base_video_path, media_data, output_path, start_time, parent=None):
        super().__init__(parent)
        self.base_video_path = base_video_path
        self.media_data = media_data
        self.output_path = output_path
        self.start_time = start_time
        self.running = True

    def run(self):
        video_clip = None
        overlay_clip = None
        final_clip = None
        try:
            self.progress.emit(10, "Loading base video...")
            if not self.running: return
            video_clip = VideoFileClip(self.base_video_path)

            duration = self.media_data.get('duration', 5)

            media_type = self.media_data.get('type')

            if media_type == 'text':
                self.progress.emit(30, "Creating text overlay...")

                # Create text image with Pillow
                font_path_str = self.media_data['font'].replace('-', ' ')
                font_size = self.media_data.get('fontsize', 12) # Default to 12 if not provided

                try:
                    # Attempt to load the selected font
                    font = ImageFont.truetype(f"{font_path_str}.ttf", font_size)
                except IOError:
                    logging.warning(f"Could not find font: {font_path_str}.ttf. Trying a default font.")
                    try:
                        # Fallback 1: Try a common font like Arial
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except IOError:
                        # Fallback 2: Use the default Pillow font and specify the size
                        logging.warning("Default font 'arial.ttf' not found. Using Pillow's load_default().")
                        # load_default() returns a font object, but we need to ensure the size is correct.
                        # The default font has a fixed size, so we can't pass the size directly.
                        # This is a limitation of the default font. Let's try to get a font with size.
                        try:
                            # This is a bit of a hack, but might work on some systems
                            font = ImageFont.truetype("sans-serif", font_size)
                        except IOError:
                             # Final fallback: Use Pillow's default font. It does not support resizing.
                             font = ImageFont.load_default()


                text = self.media_data['text']

                # Dummy draw to get text size
                dummy_img = Image.new('RGB', (0, 0))
                dummy_draw = ImageDraw.Draw(dummy_img)
                left, top, right, bottom = dummy_draw.textbbox((0,0), text, font=font)
                text_width = right - left
                text_height = bottom - top

                # Create image with a bit of padding
                img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), text, font=font, fill=self.media_data['color'])

                # Convert Pillow image to moviepy clip
                overlay_clip = ImageClip(np.array(img))
            elif media_type == 'image':
                self.progress.emit(30, "Creating image overlay...")
                overlay_clip = (ImageClip(self.media_data['path'])
                                .resize(width=self.media_data['size'][0], height=self.media_data['size'][1]))

            elif media_type == 'gif':
                self.progress.emit(30, "Creating GIF overlay...")
                overlay_clip = (VideoFileClip(self.media_data['path'], has_mask=True, transparent=True)
                                .resize(width=self.media_data['size'][0], height=self.media_data['size'][1]))
                if duration < overlay_clip.duration:
                    overlay_clip = overlay_clip.subclip(0, duration)
                else:
                    overlay_clip = overlay_clip.loop(duration=duration)

            if not overlay_clip:
                raise ValueError("Unsupported media type or error creating overlay.")

            if not self.running: return

            overlay_clip = overlay_clip.set_position(self.media_data['position']).set_duration(duration).set_start(self.start_time)

            self.progress.emit(60, "Compositing video...")
            if not self.running: return

            final_clip = CompositeVideoClip([video_clip, overlay_clip])

            self.progress.emit(80, "Writing final video...")
            if not self.running: return

            final_clip.write_videofile(self.output_path, codec='libx264', audio_codec='aac', temp_audiofile=f'temp-audio.m4a', remove_temp=True)

            if self.running:
                self.progress.emit(100, "Completed.")
                self.completed.emit(self.output_path)

        except Exception as e:
            import traceback
            logging.error(f"Error in MediaOverlayThread: {e}\n{traceback.format_exc()}")
            if self.running:
                self.error.emit(str(e))
        finally:
            if video_clip: video_clip.close()
            if overlay_clip: overlay_clip.close()
            if final_clip: final_clip.close()

    def stop(self):
        self.running = False


class MergeProgressLogger(proglog.ProgressBarLogger):
    def __init__(self, progress_signal_emitter):
        super().__init__()
        self.progress_signal_emitter = progress_signal_emitter
        self.duration = 0

    def bars_callback(self, bar, attr, value, old_value=None):
        super().bars_callback(bar, attr, value, old_value)
        if attr == 'duration':
            self.duration = value
        elif attr == 't' and self.duration > 0:
            percent = int((value / self.duration) * 100)
            # Map rendering progress (0-100%) to the 60-95% range
            progress_value = 60 + int(percent * 0.35)
            self.progress_signal_emitter.emit(progress_value, f"Rendering: {percent}%")

class VideoMergeThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, base_path, merge_path, timecode_str, adapt_resolution, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.merge_path = merge_path
        self.timecode_str = timecode_str
        self.adapt_resolution = adapt_resolution
        self.running = True

    def run(self):
        base_clip = None
        merge_clip = None
        try:
            self.progress.emit(5, "Caricamento video...")
            base_clip = VideoFileClip(self.base_path)
            merge_clip = VideoFileClip(self.merge_path)

            if not self.running: return

            if self.adapt_resolution:
                self.progress.emit(15, "Adattamento risoluzioni...")
                max_width = max(base_clip.w, merge_clip.w)
                max_height = max(base_clip.h, merge_clip.h)
                target_resolution = (max_width, max_height)
                if base_clip.size != target_resolution:
                    base_clip = base_clip.resize(target_resolution)
                if merge_clip.size != target_resolution:
                    merge_clip = merge_clip.resize(target_resolution)

            self.progress.emit(25, "Calcolo timecode...")
            tc_parts = list(map(int, self.timecode_str.split(':')))
            if len(tc_parts) != 3: raise ValueError("Formato timecode non valido.")
            tc_seconds_total = tc_parts[0] * 3600 + tc_parts[1] * 60 + tc_parts[2]

            if tc_seconds_total > base_clip.duration:
                raise ValueError("Il timecode supera la durata del video di base.")

            if not self.running: return

            self.progress.emit(40, "Composizione video...")
            final_clip = concatenate_videoclips([
                base_clip.subclip(0, tc_seconds_total),
                merge_clip,
                base_clip.subclip(tc_seconds_total)
            ], method='compose')

            base_dir = os.path.dirname(self.base_path)
            base_name = os.path.splitext(os.path.basename(self.base_path))[0]
            output_path = os.path.join(base_dir, f"{base_name}_merged_{int(time.time())}.mp4")

            if not self.running: return

            logger = MergeProgressLogger(self.progress)
            final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(output_path)

        except Exception as e:
            if self.running: self.error.emit(str(e))
        finally:
            if base_clip: base_clip.close()
            if merge_clip: merge_clip.close()

    def stop(self):
        self.running = False
        self.progress.emit(0, "Annullamento in corso...")


class BackgroundAudioProgressLogger(proglog.ProgressBarLogger):
    def __init__(self, progress_signal_emitter):
        super().__init__()
        self.progress_signal_emitter = progress_signal_emitter
        self.duration = 0

    def bars_callback(self, bar, attr, value, old_value=None):
        super().bars_callback(bar, attr, value, old_value)
        if attr == 'duration':
            self.duration = value
        elif attr == 't' and self.duration > 0:
            percent = int((value / self.duration) * 100)
            progress_value = 50 + int(percent * 0.45)
            self.progress_signal_emitter.emit(progress_value, f"Rendering video: {percent}%")

class BackgroundAudioThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, audio_path, volume, loop_audio=True, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.audio_path = audio_path
        self.volume = volume
        self.loop_audio = loop_audio
        self.running = True

    def run(self):
        video_clip = None
        background_audio_clip = None
        try:
            self.progress.emit(5, "Caricamento file...")
            video_clip = VideoFileClip(self.video_path)
            background_audio_clip = AudioFileClip(self.audio_path).volumex(self.volume)
            if not self.running: return

            if self.loop_audio and background_audio_clip.duration < video_clip.duration:
                self.progress.emit(20, "Looping audio di sottofondo...")
                background_audio_clip = background_audio_clip.loop(duration=video_clip.duration)
            if not self.running: return

            self.progress.emit(35, "Composizione audio...")
            if video_clip.audio:
                combined_audio = CompositeAudioClip(
                    [video_clip.audio, background_audio_clip.set_duration(video_clip.duration)])
            else:
                combined_audio = background_audio_clip.set_duration(video_clip.duration)
            if not self.running: return

            self.progress.emit(50, "Applicazione audio al video...")
            final_clip = video_clip.set_audio(combined_audio)

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            output_dir = os.path.dirname(self.video_path)
            output_path = os.path.join(output_dir, f"{base_name}_background_audio_{timestamp}.mp4")

            if not self.running: return

            logger = BackgroundAudioProgressLogger(self.progress)
            final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(output_path)

        except Exception as e:
            if self.running: self.error.emit(str(e))
        finally:
            if video_clip: video_clip.close()
            if background_audio_clip: background_audio_clip.close()

    def stop(self):
        self.running = False
        self.progress.emit(0, "Annullamento in corso...")


class AudioProcessingThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, new_audio_path, use_sync, start_time, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.new_audio_path = new_audio_path
        self.use_sync = use_sync
        self.start_time = start_time
        self.running = True

    def run(self):
        try:
            if self.use_sync:
                self.sync_and_apply()
            else:
                self.apply_at_time()
        except Exception as e:
            if self.running:
                self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.terminate()
        self.wait()

    def sync_and_apply(self):
        self.progress.emit(10, "Avvio sincronizzazione...")
        if not self.running: return

        try:
            video_clip = VideoFileClip(self.video_path)
            new_audio_clip = AudioFileClip(self.new_audio_path)

            if not self.running: return

            speed_factor = video_clip.duration / new_audio_clip.duration
            self.progress.emit(30, f"Fattore di velocità calcolato: {speed_factor:.2f}x")

            if not self.running: return

            video_modificato = video_clip.fx(vfx.speedx, speed_factor)
            final_video = video_modificato.set_audio(new_audio_clip)

            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
            output_path = os.path.join(os.path.dirname(self.video_path), f"{base_name}_GeniusAI_{timestamp}.mp4")

            self.progress.emit(70, "Salvataggio video finale...")
            if not self.running: return

            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=video_clip.fps, logger=None)

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(output_path)
        finally:
            if 'video_clip' in locals(): video_clip.close()
            if 'new_audio_clip' in locals(): new_audio_clip.close()


    def apply_at_time(self):
        self.progress.emit(10, "Avvio applicazione audio...")
        if not self.running: return

        try:
            video_clip = VideoFileClip(self.video_path)
            original_audio = video_clip.audio
            new_audio_clip = AudioFileClip(self.new_audio_path)

            if not self.running: return

            if self.start_time > video_clip.duration:
                raise ValueError("Il tempo di inizio supera la durata del video.")

            self.progress.emit(30, "Composizione tracce audio...")

            # Parte 1: Audio originale fino a start_time
            part1 = original_audio.subclip(0, self.start_time)

            # Parte 3: Audio originale dopo il nuovo audio
            end_of_new_audio = self.start_time + new_audio_clip.duration
            part3 = None
            if end_of_new_audio < video_clip.duration:
                part3 = original_audio.subclip(end_of_new_audio)

            # Combina le parti
            final_audio_clips = [part1, new_audio_clip]
            if part3:
                final_audio_clips.append(part3)

            final_audio = concatenate_audioclips(final_audio_clips)

            if not self.running: return

            self.progress.emit(60, "Applicazione audio al video...")
            final_video = video_clip.set_audio(final_audio)

            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
            output_path = os.path.join(os.path.dirname(self.video_path), f"{base_name}_manual_audio_{timestamp}.mp4")

            self.progress.emit(80, "Salvataggio video...")
            if not self.running: return

            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=video_clip.fps, logger=None)

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(output_path)
        finally:
            if 'video_clip' in locals(): video_clip.close()
            if 'original_audio' in locals(): original_audio.close()
            if 'new_audio_clip' in locals(): new_audio_clip.close()


class VideoAudioManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.project_manager = ProjectManager(base_dir="projects")
        self.current_project_path = None

        setup_logging()

        # File di versione
        self.version_file = VERSION_FILE

        # Carica le informazioni di versione dal file esterno
        self.version, self.build_date = self.load_version_info()

        # Imposta il titolo della finestra con la versione e la data di build
        self.setWindowTitle(f"GeniusAI - {self.version} (Build Date: {self.build_date})")

        self.setGeometry(500, 500, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.player = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.playerOutput = QMediaPlayer()
        self.audioOutputOutput = QAudioOutput()
        self.previewPlayer = QMediaPlayer()
        self.previewAudioOutput = QAudioOutput()

        self.player.setAudioOutput(self.audioOutput)
        self.previewPlayer.setAudioOutput(self.previewAudioOutput)
        self.audioOutput.setVolume(1.0)
        self.playerOutput.setAudioOutput(self.audioOutputOutput)
        self.recentFiles = []
        self.loadRecentFiles()
        self.recentProjects = []
        self.loadRecentProjects()
        self.recording_segments = []

        # Blinking recording indicator
        self.recording_indicator = QLabel(self)
        self.recording_indicator.setPixmap(QIcon(get_resource("rec.png")).pixmap(16, 16))
        self.recording_indicator.setVisible(True)
        self.indicator_timer = QTimer(self)
        self.indicator_timer.timeout.connect(self.toggle_recording_indicator)
        self.is_recording = False

        self.reverseTimer = QTimer(self)
        self.reverseTimer.timeout.connect(self.reversePlaybackStep)
        self.reverseTimerOutput = QTimer(self)
        self.reverseTimerOutput.timeout.connect(self.reversePlaybackStepOutput)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.autosave_transcription)

        # Timer per il salvataggio automatico nel file JSON
        self.json_autosave_timer = QTimer(self)
        self.json_autosave_timer.timeout.connect(lambda: self.save_all_tabs_to_json(show_message=False))
        self.json_autosave_timer.start(300000)  # 5 minuti (300,000 ms)

        # Initialize attributes before UI
        self.use_vb_cable = False
        self.audio_device_layout = None
        self.audio_checkbox_container = None
        self.enableWatermark = False
        self.watermarkPath = ""
        self.watermarkSize = 0
        self.watermarkPosition = "Bottom Right"

        # Usa la configurazione dei colori centralizzata da config.py
        self.highlight_colors = HIGHLIGHT_COLORS
        # Imposta un colore di default. Prende il primo nome dalla config se quello salvato non è valido.
        default_color_name = next(iter(self.highlight_colors))
        self.current_highlight_color_name = default_color_name

        self.initUI()

        # Move these initializations to after initUI
        self.videoContainer.resizeEvent = self.videoContainerResizeEvent
        self.setupDockSettingsManager()
        self.bookmarkStart = None
        self.bookmarkEnd = None
        self.currentPosition = 0
        self.videoPathLineEdit = ''
        self.videoPathLineOutputEdit = ''
        self.is_recording = False
        self.video_writer = None
        self.current_video_path = None
        self.current_audio_path = None
        self.updateViewMenu()
        self.videoSharingManager = VideoSharingManager(self)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.load_recording_settings() # This will now correctly update the UI
        self.setDefaultAudioDevice()
        self.original_text = ""
        self.transcription_original = ""
        self.transcription_corrected = ""
        self.summaries = {}
        self.active_summary_type = None
        self.summary_text = ""
        self.summary_generated = ""
        self.summary_generated_integrated = ""
        self.original_audio_ai_html = ""


        # Avvia la registrazione automatica delle chiamate
        #self.teams_call_recorder.start()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.monitor_preview = None
        self.cursor_overlay = CursorOverlay()
        self.current_thread = None
        self.original_status_bar_stylesheet = self.statusBar.styleSheet()

    def show_status_message(self, message, timeout=5000, error=False):
        """Mostra un messaggio nella barra di stato per un tempo limitato."""
        if error:
            self.statusBar.setStyleSheet(self.original_status_bar_stylesheet + "color: red;")
        else:
            self.statusBar.setStyleSheet(self.original_status_bar_stylesheet)

        self.statusLabel.setText(message)

        if timeout > 0:
            # Ripristina il messaggio e lo stile dopo il timeout
            def reset_status():
                # Controlla se il messaggio è ancora quello impostato da questa chiamata
                if self.statusLabel.text() == message:
                    self.statusLabel.setText("Pronto")
                    self.statusBar.setStyleSheet(self.original_status_bar_stylesheet)
            QTimer.singleShot(timeout, reset_status)

    def start_task(self, thread, on_complete, on_error, on_progress):
        """Avvia un thread e gestisce la barra di stato."""
        if self.current_thread and self.current_thread.isRunning():
            self.show_status_message("Un'altra operazione è già in corso.", error=True)
            return

        self.current_thread = thread

        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.cancelButton.setVisible(True)

        # Disconnette eventuali segnali precedenti prima di connetterne di nuovi
        try:
            self.cancelButton.clicked.disconnect()
        except TypeError:
            pass  # Nessuna connessione da rimuovere
        self.cancelButton.clicked.connect(self.cancel_task)

        # Connette i segnali del thread
        thread.progress.connect(on_progress)
        thread.completed.connect(lambda result: self.finish_task(True, result, on_complete))
        thread.error.connect(lambda error: self.finish_task(False, error, on_error))

        thread.start()

    def update_status_progress(self, value, label):
        """Aggiorna la barra di avanzamento e il messaggio di stato."""
        self.progressBar.setValue(value)
        self.statusLabel.setText(label)

    def finish_task(self, success, result_or_error, callback):
        """Gestisce il completamento o l'errore di un'attività."""
        self.progressBar.setVisible(False)
        self.cancelButton.setVisible(False)
        self.current_thread = None
        try:
            self.cancelButton.clicked.disconnect()
        except TypeError:
            pass

        if success:
            self.show_status_message("Operazione completata con successo.", timeout=5000)
        else:
            self.show_status_message(f"Errore: {result_or_error}", error=True, timeout=10000)

        if callback:
            callback(result_or_error)

    def cancel_task(self):
        """Annulla l'attività in corso."""
        if self.current_thread and self.current_thread.isRunning():
            if hasattr(self.current_thread, 'stop'):
                self.current_thread.stop()
            else:
                self.current_thread.terminate() # Fallback

            self.show_status_message("Operazione annullata.", timeout=5000)
            self.finish_task(False, "Annullato dall'utente", None)

    def load_recording_settings(self):
        """Carica le impostazioni per il cursore e il watermark e le salva come attributi dell'istanza."""
        settings = QSettings("Genius", "GeniusAI")

        # Leggi le impostazioni e salvale in variabili "self"

        self.show_red_dot = settings.value("cursor/showRedDot", True, type=bool)
        self.show_yellow_triangle = settings.value("cursor/showYellowTriangle", False, type=bool)
        self.enableWatermark = settings.value("recording/enableWatermark", False, type=bool)
        self.watermarkPath = settings.value("recording/watermarkPath", WATERMARK_IMAGE)
        self.watermarkSize = settings.value("recording/watermarkSize", 10, type=int)
        self.watermarkPosition = settings.value("recording/watermarkPosition", "Bottom Right")
        self.use_vb_cable = settings.value("recording/useVBCable", False, type=bool)

        # Carica il colore di evidenziazione personalizzato
        self.current_highlight_color_name = settings.value("editor/highlightColor", "Giallo")

        # Configura l'aspetto dell'overlay
        self.videoOverlay.set_show_red_dot(self.show_red_dot)
        self.videoOverlay.set_show_yellow_triangle(self.show_yellow_triangle)
        self.videoOverlay.setWatermark(self.enableWatermark, self.watermarkPath, self.watermarkSize, self.watermarkPosition)

        if self.audio_device_layout is not None:
            self.update_audio_device_list()

    def initUI(self):
        """
        Inizializza l'interfaccia utente creando e configurando l'area dei dock,
        impostando i dock principali (video input, video output, trascrizione, editing AI, ecc.)
        e definendo la sezione di trascrizione con QTabWidget e area di testo sempre visibile.
        """
        # Impostazione dell'icona della finestra
        self.setWindowIcon(QIcon(get_resource('eye.png')))

        # Creazione dell'area dei dock
        area = DockArea()
        self.setCentralWidget(area)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setToolTip("Area principale dei dock")

        # ---------------------
        # CREAZIONE DOCK PRINCIPALI (invariati)
        # ---------------------
        self.videoPlayerDock = CustomDock("Video Player Input", closable=True)
        self.videoPlayerDock.setStyleSheet(self.styleSheet())
        self.videoPlayerDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerDock.setToolTip("Dock per la riproduzione video di input")
        area.addDock(self.videoPlayerDock, 'left')

        self.videoPlayerOutput = CustomDock("Video Player Output", closable=True)
        self.videoPlayerOutput.setStyleSheet(self.styleSheet())
        self.videoPlayerOutput.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerOutput.setToolTip("Dock per la riproduzione video di output")
        area.addDock(self.videoPlayerOutput, 'left')

        self.transcriptionDock = CustomDock("Trascrizione e Sintesi Audio", closable=True)
        self.transcriptionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.transcriptionDock.setStyleSheet(self.styleSheet())
        self.transcriptionDock.setToolTip("Dock per la trascrizione e sintesi audio")
        area.addDock(self.transcriptionDock, 'right')

        self.editingDock = CustomDock("Generazione Audio AI", closable=True)
        self.editingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editingDock.setStyleSheet(self.styleSheet())
        self.editingDock.setToolTip("Dock per la generazione audio assistita da AI")
        area.addDock(self.editingDock, 'right')

        self.recordingDock = self.createRecordingDock()
        self.recordingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.recordingDock.setStyleSheet(self.styleSheet())
        self.recordingDock.setToolTip("Dock per la registrazione")
        area.addDock(self.recordingDock, 'right')

        self.audioDock = self.createAudioDock()
        self.audioDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.audioDock.setStyleSheet(self.styleSheet())
        self.audioDock.setToolTip("Dock per la gestione Audio/Video")
        area.addDock(self.audioDock, 'left')

        self.videoEffectsDock = self.createVideoEffectsDock()
        self.videoEffectsDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoEffectsDock.setStyleSheet(self.styleSheet())
        self.videoEffectsDock.setToolTip("Dock per effetti video (PiP, Overlay)")
        area.addDock(self.videoEffectsDock, 'right', self.audioDock)

        self.infoDock = InfoDock()
        self.infoDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.infoDock.setStyleSheet(self.styleSheet())
        area.addDock(self.infoDock, 'right', self.transcriptionDock)

        self.projectDock = ProjectDock()
        self.projectDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.projectDock.setStyleSheet(self.styleSheet())
        area.addDock(self.projectDock, 'right', self.infoDock)
        self.projectDock.clip_selected.connect(self.load_project_clip)
        self.projectDock.open_folder_requested.connect(self.open_project_folder)
        self.projectDock.delete_clip_requested.connect(self.delete_project_clip)
        self.projectDock.project_clips_folder_changed.connect(self.sync_project_clips_folder)
        self.projectDock.open_in_input_player_requested.connect(self.loadVideo)
        self.projectDock.open_in_output_player_requested.connect(self.loadVideoOutput)
        self.projectDock.rename_clip_requested.connect(self.rename_project_clip)
        self.projectDock.relink_clip_requested.connect(self.relink_project_clip)

        self.videoNotesDock = CustomDock("Note Video", closable=True)
        self.videoNotesDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoNotesDock.setStyleSheet(self.styleSheet())
        self.videoNotesDock.setToolTip("Dock per le note video")
        area.addDock(self.videoNotesDock, 'bottom', self.transcriptionDock)
        self.createVideoNotesDock()


        # self.infoExtractionDock = CustomDock("Estrazione Info Video", closable=True)
        # self.infoExtractionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # self.infoExtractionDock.setToolTip("Dock per l'estrazione di informazioni da video")
        # area.addDock(self.infoExtractionDock, 'right')
        # self.createInfoExtractionDock()

        # ---------------------
        # PLAYER INPUT
        # ---------------------
        self.videoContainer = QWidget()
        self.videoContainer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoContainer.setToolTip("Video container for panning and zooming")

        self.videoCropWidget = CropVideoWidget(parent=self.videoContainer)
        self.videoCropWidget.setAcceptDrops(True)
        self.videoCropWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoCropWidget.setToolTip("Area di visualizzazione e ritaglio video input")
        self.player.setVideoOutput(self.videoCropWidget)
        self.videoCropWidget.spacePressed.connect(self.togglePlayPause)

        # Aggiungi un QLabel per l'immagine "Solo audio"
        self.audioOnlyLabel = QLabel(self.videoContainer)
        self.audioOnlyLabel.setPixmap(QPixmap(get_resource("audio_only.png")).scaled(
            self.videoContainer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        self.audioOnlyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audioOnlyLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.audioOnlyLabel.setVisible(False) # Inizialmente nascosto

        self.videoOverlay = VideoOverlay(self, parent=self.videoContainer)
        self.videoOverlay.show()
        self.videoOverlay.raise_()

        self.zoom_level = 1.0
        self.is_panning = False
        self.last_mouse_position = QPoint()

        self.videoOverlay.panned.connect(self.handle_pan)
        self.videoOverlay.zoomed.connect(self.handle_zoom)
        self.videoOverlay.view_reset.connect(self.reset_view)
        self.videoOverlay.installEventFilter(self)

        self.videoSlider = CustomSlider(Qt.Orientation.Horizontal)
        self.videoSlider.setToolTip("Slider per navigare all'interno del video input")

        self.fileNameLabel = QLabel("Nessun video caricato")
        self.fileNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fileNameLabel.setStyleSheet("QLabel { font-weight: bold; }")
        self.fileNameLabel.setToolTip("Nome del file video attualmente caricato nel Player Input")

        self.openFileInputButton = QPushButton('')
        self.openFileInputButton.setIcon(QIcon(get_resource("load.png")))
        self.openFileInputButton.setToolTip("Apri un nuovo video nell'input player")
        self.openFileInputButton.clicked.connect(self.browseVideo)

        self.playButton = QPushButton('')
        self.playButton.setIcon(QIcon(get_resource("play.png")))
        self.playButton.setToolTip("Riproduci/Pausa il video input")
        self.playButton.clicked.connect(self.togglePlayPause)

        self.stopButton = QPushButton('')
        self.stopButton.setIcon(QIcon(get_resource("stop.png")))
        self.stopButton.setToolTip("Ferma la riproduzione del video input")

        self.setStartBookmarkButton = QPushButton('')
        self.setStartBookmarkButton.setIcon(QIcon(get_resource("bookmark_1.png")))
        self.setStartBookmarkButton.setToolTip("Imposta segnalibro di inizio sul video input")

        self.setEndBookmarkButton = QPushButton('')
        self.setEndBookmarkButton.setIcon(QIcon(get_resource("bookmark_2.png")))
        self.setEndBookmarkButton.setToolTip("Imposta segnalibro di fine sul video input")

        self.clearBookmarksButton = QPushButton('')
        self.clearBookmarksButton.setIcon(QIcon(get_resource("reset.png")))
        self.clearBookmarksButton.setToolTip("Cancella tutti i segnalibri")

        self.cutButton = QPushButton('')
        self.cutButton.setIcon(QIcon(get_resource("taglia.png")))
        self.cutButton.setToolTip("Taglia il video tra i segnalibri impostati")

        self.cropButton = QPushButton('')
        self.cropButton.setIcon(QIcon(get_resource("crop.png")))
        self.cropButton.setToolTip("Apre la finestra di dialogo per ritagliare il video")


        self.rewindButton = QPushButton('<< 5s')
        self.rewindButton.setIcon(QIcon(get_resource("rewind.png")))
        self.rewindButton.setToolTip("Riavvolgi il video di 5 secondi")

        self.frameBackwardButton = QPushButton('|<')
        self.frameBackwardButton.setToolTip("Indietro di un frame")

        self.forwardButton = QPushButton('>> 5s')
        self.forwardButton.setIcon(QIcon(get_resource("forward.png")))
        self.forwardButton.setToolTip("Avanza il video di 5 secondi")

        self.frameForwardButton = QPushButton('>|')
        self.frameForwardButton.setToolTip("Avanti di un frame")

        self.deleteButton = QPushButton('')
        self.deleteButton.setIcon(QIcon(get_resource("trash-bin.png")))
        self.deleteButton.setToolTip("Cancella la parte selezionata del video")

        self.transferToOutputButton = QPushButton('')
        self.transferToOutputButton.setIcon(QIcon(get_resource("change.png")))
        self.transferToOutputButton.setToolTip("Sposta il video dall'input all'output")
        self.transferToOutputButton.clicked.connect(
            lambda: self.loadVideoOutput(self.videoPathLineEdit) if self.videoPathLineEdit else None
        )

        self.stopButton.clicked.connect(self.stopVideo)
        self.setStartBookmarkButton.clicked.connect(self.setStartBookmark)
        self.setEndBookmarkButton.clicked.connect(self.setEndBookmark)
        self.clearBookmarksButton.clicked.connect(self.clearBookmarks)
        self.cutButton.clicked.connect(self.cutVideoBetweenBookmarks)
        self.cropButton.clicked.connect(self.open_crop_dialog)
        self.rewindButton.clicked.connect(self.rewind5Seconds)
        self.forwardButton.clicked.connect(self.forward5Seconds)
        self.frameBackwardButton.clicked.connect(self.frameBackward)
        self.frameForwardButton.clicked.connect(self.frameForward)
        self.deleteButton.clicked.connect(self.deleteVideoSegment)

        self.currentTimeLabel = QLabel('00:00')
        self.currentTimeLabel.setToolTip("Mostra il tempo corrente del video input")
        self.totalTimeLabel = QLabel('/ 00:00')
        self.totalTimeLabel.setToolTip("Mostra la durata totale del video input")
        timecodeLayout = QHBoxLayout()
        timecodeLayout.addWidget(self.currentTimeLabel)
        timecodeLayout.addWidget(self.totalTimeLabel)

        # ---------------------
        # PLAYER OUTPUT
        # ---------------------
        self.videoOutputWidget = CropVideoWidget()
        self.videoOutputWidget.setAcceptDrops(True)
        self.videoOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoOutputWidget.setToolTip("Area di visualizzazione e ritaglio video output")
        self.videoOutputWidget.spacePressed.connect(self.togglePlayPauseOutput)

        self.playerOutput.setAudioOutput(self.audioOutputOutput)
        self.playerOutput.setVideoOutput(self.videoOutputWidget)

        self.openFileOutputButton = QPushButton('')
        self.openFileOutputButton.setIcon(QIcon(get_resource("load.png")))
        self.openFileOutputButton.setToolTip("Apri un nuovo video nell'output player")
        self.openFileOutputButton.clicked.connect(self.browseVideoOutput)

        self.playButtonOutput = QPushButton('')
        self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
        self.playButtonOutput.setToolTip("Riproduci/Pausa il video output")
        self.playButtonOutput.clicked.connect(self.togglePlayPauseOutput)

        stopButtonOutput = QPushButton('')
        stopButtonOutput.setIcon(QIcon(get_resource("stop.png")))
        stopButtonOutput.setToolTip("Ferma la riproduzione del video output")

        changeButtonOutput = QPushButton('')
        changeButtonOutput.setIcon(QIcon(get_resource("change.png")))
        changeButtonOutput.setToolTip("Sposta il video output nel Video Player Input")
        changeButtonOutput.clicked.connect(
            lambda: self.loadVideo(self.videoPathLineOutputEdit, os.path.basename(self.videoPathLineOutputEdit))
        )

        syncPositionButton = QPushButton('Sync Position')
        syncPositionButton.setIcon(QIcon(get_resource("sync.png")))
        syncPositionButton.setToolTip('Sincronizza la posizione del video output con quella del video source')
        syncPositionButton.clicked.connect(self.syncOutputWithSourcePosition)

        stopButtonOutput.clicked.connect(lambda: self.playerOutput.stop())

        playbackControlLayoutOutput = QHBoxLayout()
        playbackControlLayoutOutput.addWidget(self.openFileOutputButton)
        playbackControlLayoutOutput.addWidget(self.playButtonOutput)
        playbackControlLayoutOutput.addWidget(stopButtonOutput)
        playbackControlLayoutOutput.addWidget(changeButtonOutput)
        playbackControlLayoutOutput.addWidget(syncPositionButton)

        videoSliderOutput = CustomSlider(Qt.Orientation.Horizontal)
        videoSliderOutput.setRange(0, 1000)  # Range di esempio
        videoSliderOutput.setToolTip("Slider per navigare all'interno del video output")
        videoSliderOutput.sliderMoved.connect(lambda position: self.playerOutput.setPosition(position))

        self.currentTimeLabelOutput = QLabel('00:00')
        self.currentTimeLabelOutput.setToolTip("Mostra il tempo corrente del video output")
        self.totalTimeLabelOutput = QLabel('/ 00:00')
        self.totalTimeLabelOutput.setToolTip("Mostra la durata totale del video output")
        timecodeLayoutOutput = QHBoxLayout()
        timecodeLayoutOutput.addWidget(self.currentTimeLabelOutput)
        timecodeLayoutOutput.addWidget(self.totalTimeLabelOutput)

        self.timecodeEnabled = False

        self.fileNameLabelOutput = QLabel("Nessun video caricato")
        self.fileNameLabelOutput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fileNameLabelOutput.setStyleSheet("QLabel { font-weight: bold; }")
        self.fileNameLabelOutput.setToolTip("Nome del file video attualmente caricato nel Player Output")

        videoOutputLayout = QVBoxLayout()
        videoOutputLayout.addWidget(self.fileNameLabelOutput)
        videoOutputLayout.addWidget(self.videoOutputWidget)
        videoOutputLayout.addLayout(timecodeLayoutOutput)
        videoOutputLayout.addWidget(videoSliderOutput)

        # Speed control for output player
        speedLayoutOutput = QHBoxLayout()
        speedLayoutOutput.addWidget(QLabel("Velocità:"))
        self.speedSpinBoxOutput = QDoubleSpinBox()
        self.speedSpinBoxOutput.setRange(-20.0, 20.0)
        self.speedSpinBoxOutput.setSuffix("x")
        self.speedSpinBoxOutput.setValue(1.0)
        self.speedSpinBoxOutput.setSingleStep(0.1)
        self.speedSpinBoxOutput.valueChanged.connect(self.setPlaybackRateOutput)
        speedLayoutOutput.addWidget(self.speedSpinBoxOutput)
        videoOutputLayout.addLayout(speedLayoutOutput)

        videoOutputLayout.addLayout(playbackControlLayoutOutput)

        self.playerOutput.durationChanged.connect(self.updateDurationOutput)
        self.playerOutput.positionChanged.connect(self.updateTimeCodeOutput)
        self.playerOutput.playbackStateChanged.connect(self.updatePlayButtonIconOutput)

        videoPlayerOutputWidget = QWidget()
        videoPlayerOutputWidget.setLayout(videoOutputLayout)
        videoPlayerOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerOutput.addWidget(videoPlayerOutputWidget)

        self.playerOutput.durationChanged.connect(lambda duration: videoSliderOutput.setRange(0, duration))
        self.playerOutput.positionChanged.connect(lambda position: videoSliderOutput.setValue(position))

        # Pulsante per trascrivere il video
        self.transcribeButton = QPushButton('Trascrivi Video')
        self.transcribeButton.setToolTip("Avvia la trascrizione del video attualmente caricato")
        self.transcribeButton.clicked.connect(self.transcribeVideo)

        # Layout di playback del Player Input
        playbackControlLayout = QHBoxLayout()
        playbackControlLayout.addWidget(self.openFileInputButton)
        playbackControlLayout.addWidget(self.rewindButton)
        playbackControlLayout.addWidget(self.frameBackwardButton)
        playbackControlLayout.addWidget(self.playButton)
        playbackControlLayout.addWidget(self.stopButton)
        playbackControlLayout.addWidget(self.forwardButton)
        playbackControlLayout.addWidget(self.frameForwardButton)
        playbackControlLayout.addWidget(self.setStartBookmarkButton)
        playbackControlLayout.addWidget(self.setEndBookmarkButton)
        playbackControlLayout.addWidget(self.clearBookmarksButton)
        playbackControlLayout.addWidget(self.cutButton)
        playbackControlLayout.addWidget(self.cropButton)
        playbackControlLayout.addWidget(self.deleteButton)
        playbackControlLayout.addWidget(self.transferToOutputButton)

        # Layout principale del Player Input
        videoPlayerLayout = QVBoxLayout()
        videoPlayerLayout.addWidget(self.fileNameLabel)
        videoPlayerLayout.addWidget(self.videoContainer)
        videoPlayerLayout.addLayout(timecodeLayout)

        # Timecode input
        timecode_input_layout = QHBoxLayout()
        self.timecodeInput = QLineEdit()
        self.timecodeInput.setPlaceholderText("HH:MM:SS:ms")
        self.timecodeInput.setToolTip("Vai al timecode")
        timecode_input_layout.addWidget(self.timecodeInput)

        go_button = QPushButton("Go")
        go_button.setToolTip("Vai al timecode specificato")
        go_button.clicked.connect(self.goToTimecode)
        timecode_input_layout.addWidget(go_button)
        videoPlayerLayout.addLayout(timecode_input_layout)

        videoPlayerLayout.addWidget(self.videoSlider)

        # Speed control
        speedLayout = QHBoxLayout()
        speedLayout.addWidget(QLabel("Velocità:"))
        self.speedSpinBox = QDoubleSpinBox()
        self.speedSpinBox.setRange(-20.0, 20.0)
        self.speedSpinBox.setSuffix("x")
        self.speedSpinBox.setValue(1.0)
        self.speedSpinBox.setSingleStep(0.1)
        self.speedSpinBox.valueChanged.connect(self.setPlaybackRateInput)
        speedLayout.addWidget(self.speedSpinBox)
        videoPlayerLayout.addLayout(speedLayout)

        videoPlayerLayout.addLayout(playbackControlLayout)

        # Controlli volume input e velocità
        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(int(self.audioOutput.volume() * 100))
        self.volumeSlider.setToolTip("Regola il volume dell'audio input")
        self.volumeSlider.valueChanged.connect(self.setVolume)

        self.volumeSliderOutput = QSlider(Qt.Orientation.Horizontal)
        self.volumeSliderOutput.setRange(0, 100)
        self.volumeSliderOutput.setValue(int(self.audioOutputOutput.volume() * 100))
        self.volumeSliderOutput.setToolTip("Regola il volume dell'audio output")
        self.volumeSliderOutput.valueChanged.connect(self.setVolumeOutput)

        videoOutputLayout.addWidget(QLabel("Volume"))
        videoOutputLayout.addWidget(self.volumeSliderOutput)

        videoPlayerWidget = QWidget()
        videoPlayerWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        videoPlayerWidget.setLayout(videoPlayerLayout)
        self.videoPlayerDock.addWidget(videoPlayerWidget)

        # =================================================================================
        # DOCK DI TRASCRIZIONE E RIASSUNTO (CON TAB WIDGET)
        # =================================================================================
        self.transcriptionTabWidget = QTabWidget()
        self.transcriptionTabWidget.setToolTip("Gestisci la trascrizione e i riassunti generati.")

        # --- Tab Trascrizione ---
        transcription_tab = QWidget()
        transcription_layout = QVBoxLayout(transcription_tab)

        trans_controls_group = QGroupBox("Controlli Trascrizione")
        main_controls_layout = QVBoxLayout(trans_controls_group)

        # --- Riga 1: Lingua ---
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Seleziona lingua video:"))
        self.languageComboBox = QComboBox()
        self.languageComboBox.addItems(["Italiano", "Inglese", "Francese", "Spagnolo", "Tedesco"])
        self.languageComboBox.setItemData(0, "it")
        self.languageComboBox.setItemData(1, "en")
        self.languageComboBox.setItemData(2, "fr")
        self.languageComboBox.setItemData(3, "es")
        self.languageComboBox.setItemData(4, "de")
        language_layout.addWidget(self.languageComboBox)
        language_layout.addStretch()
        self.transcriptionLanguageLabel = QLabel("Lingua rilevata: N/A")
        language_layout.addWidget(self.transcriptionLanguageLabel)
        main_controls_layout.addLayout(language_layout)

        # --- Riga 2: Gruppi di Controlli Affiancati ---
        groups_layout = QHBoxLayout()

        # --- Gruppo 1: Azioni sui File ---
        file_actions_group = QGroupBox("File")
        file_actions_layout = QHBoxLayout(file_actions_group)

        self.transcribeButton = QPushButton('')
        self.transcribeButton.setIcon(QIcon(get_resource("script.png")))
        self.transcribeButton.setFixedSize(32, 32)
        self.transcribeButton.setToolTip("Trascrivi Video")
        self.transcribeButton.clicked.connect(self.transcribeVideo)
        file_actions_layout.addWidget(self.transcribeButton)

        self.loadButton = QPushButton('')
        self.loadButton.setIcon(QIcon(get_resource("load.png")))
        self.loadButton.setFixedSize(32, 32)
        self.loadButton.setToolTip("Carica Testo")
        self.loadButton.clicked.connect(self.loadText)
        file_actions_layout.addWidget(self.loadButton)

        self.saveTranscriptionButton = QPushButton('')
        self.saveTranscriptionButton.setIcon(QIcon(get_resource("save.png")))
        self.saveTranscriptionButton.setFixedSize(32, 32)
        self.saveTranscriptionButton.setToolTip("Salva Trascrizione nel JSON associato")
        self.saveTranscriptionButton.clicked.connect(self.save_transcription_to_json)
        file_actions_layout.addWidget(self.saveTranscriptionButton)

        self.resetButton = QPushButton('')
        self.resetButton.setIcon(QIcon(get_resource("reset.png")))
        self.resetButton.setFixedSize(32, 32)
        self.resetButton.setToolTip("Pulisci")
        self.resetButton.clicked.connect(lambda: self.transcriptionTextArea.clear())
        file_actions_layout.addWidget(self.resetButton)

        self.fixTranscriptionButton = QPushButton('')
        self.fixTranscriptionButton.setIcon(QIcon(get_resource("text_fix.png")))
        self.fixTranscriptionButton.setFixedSize(32, 32)
        self.fixTranscriptionButton.setToolTip("Correggi Testo Trascrizione")
        self.fixTranscriptionButton.clicked.connect(self.fixTranscriptionWithAI)
        file_actions_layout.addWidget(self.fixTranscriptionButton)

        # Pulsante per incollare nella tab Audio AI
        self.pasteToAudioAIButton = QPushButton('')
        self.pasteToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        self.pasteToAudioAIButton.setFixedSize(32, 32)
        self.pasteToAudioAIButton.setToolTip("Incolla nella tab Audio AI")
        self.pasteToAudioAIButton.clicked.connect(lambda: self.paste_to_audio_ai(self.transcriptionTextArea))
        file_actions_layout.addWidget(self.pasteToAudioAIButton)

        groups_layout.addWidget(file_actions_group)

        # --- Gruppo 2: Strumenti ---
        tools_group = QGroupBox("Strumenti")
        tools_grid_layout = QGridLayout(tools_group)

        self.timecodeCheckbox = QCheckBox("Inserisci timecode audio")
        self.timecodeCheckbox.toggled.connect(self.handleTimecodeToggle)
        tools_grid_layout.addWidget(self.timecodeCheckbox, 0, 0)

        self.syncButton = QPushButton('')
        self.syncButton.setIcon(QIcon(get_resource("sync.png")))
        self.syncButton.setFixedSize(32, 32)
        self.syncButton.setToolTip("Sincronizza Video da Timecode Vicino")
        self.syncButton.clicked.connect(self.sync_video_to_transcription)
        tools_grid_layout.addWidget(self.syncButton, 0, 1)

        self.pauseTimeEdit = QLineEdit()
        self.pauseTimeEdit.setPlaceholderText("Durata pausa (es. 1.0s)")
        tools_grid_layout.addWidget(self.pauseTimeEdit, 1, 0)

        self.insertPauseButton = QPushButton("Inserisci Pausa")
        self.insertPauseButton.clicked.connect(self.insertPause)
        tools_grid_layout.addWidget(self.insertPauseButton, 1, 1)

        self.saveAudioAIButton = QPushButton('')
        self.saveAudioAIButton.setIcon(QIcon(get_resource("save.png")))
        self.saveAudioAIButton.setFixedSize(32, 32)
        self.saveAudioAIButton.setToolTip("Salva Testo Audio AI nel JSON associato")
        self.saveAudioAIButton.clicked.connect(self.save_audio_ai_to_json)
        tools_grid_layout.addWidget(self.saveAudioAIButton, 0, 2) # Aggiunto qui

        # groups_layout.addWidget(tools_group)

        # LA SEGUENTE RIGA È STATA RIMOSSA PER PERMETTERE L'ESPANSIONE
        # groups_layout.addStretch()

        main_controls_layout.addLayout(groups_layout)

        # --- Riga 3: Toggle per la visualizzazione ---
        view_options_layout = QHBoxLayout()
        self.transcriptionViewToggle = QCheckBox("Mostra testo corretto")
        self.transcriptionViewToggle.setToolTip("Attiva/Disattiva la visualizzazione del testo corretto.")
        self.transcriptionViewToggle.setEnabled(False) # Disabilitato di default
        self.transcriptionViewToggle.toggled.connect(self.toggle_transcription_view)
        view_options_layout.addWidget(self.transcriptionViewToggle)
        view_options_layout.addStretch()
        main_controls_layout.addLayout(view_options_layout)

        transcription_layout.addWidget(trans_controls_group)

        #--------------------

        self.transcriptionTextArea = CustomTextEdit(self)
        self.transcriptionTextArea.setPlaceholderText("La trascrizione del video apparirà qui...")
        self.transcriptionTextArea.textChanged.connect(self.handleTextChange)
        self.transcriptionTextArea.timestampDoubleClicked.connect(self.sincronizza_video)
        transcription_layout.addWidget(self.transcriptionTextArea)

        self.transcriptionTabWidget.addTab(transcription_tab, "Trascrizione")

        # --- Tab Audio AI ---
        self.audio_ai_tab = QWidget()
        audio_ai_layout = QVBoxLayout(self.audio_ai_tab)

        # Sposta il gruppo "Strumenti" qui
        audio_ai_layout.addWidget(tools_group)

        self.audioAiTextArea = CustomTextEdit(self)
        self.audioAiTextArea.setPlaceholderText("Incolla qui il testo da usare per la generazione audio o altre funzioni AI...")
        audio_ai_layout.addWidget(self.audioAiTextArea)

        # --- Tab Riassunto ---
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        summary_controls_group = QGroupBox("Controlli Riassunto e AI")
        summary_controls_layout = QVBoxLayout(summary_controls_group)

        # Layout orizzontale per tutti i pulsanti e controlli in linea
        top_controls_layout = QHBoxLayout()

        # Pulsanti Azioni AI
        summarize_button = QPushButton('')
        summarize_button.setIcon(QIcon(get_resource("text_sum.png")))
        summarize_button.setFixedSize(32, 32)
        summarize_button.setToolTip("Riassumi Testo")
        summarize_button.clicked.connect(self.processTextWithAI)
        top_controls_layout.addWidget(summarize_button)

        #fix_text_button = QPushButton('')
        #fix_text_button.setIcon(QIcon(get_resource("text_fix.png")))
        #fix_text_button.setFixedSize(32, 32)
        #fix_text_button.setToolTip("Correggi Testo")
        #fix_text_button.clicked.connect(self.fixTextWithAI)
        #top_controls_layout.addWidget(fix_text_button)

        summarize_meeting_button = QPushButton('')
        summarize_meeting_button.setIcon(QIcon(get_resource("meet_sum.png")))
        summarize_meeting_button.setFixedSize(32, 32)
        summarize_meeting_button.setToolTip("Riassumi Riunione")
        summarize_meeting_button.clicked.connect(self.summarizeMeeting)
        top_controls_layout.addWidget(summarize_meeting_button)

        self.generatePptxActionBtn = QPushButton('')
        self.generatePptxActionBtn.setIcon(QIcon(get_resource("powerpoint.png")))
        self.generatePptxActionBtn.setFixedSize(32, 32)
        self.generatePptxActionBtn.setToolTip("Genera Presentazione")
        self.generatePptxActionBtn.clicked.connect(self.openPptxDialog)
        top_controls_layout.addWidget(self.generatePptxActionBtn)

        self.highlightTextButton = QPushButton('')
        self.highlightTextButton.setIcon(QIcon(get_resource("key.png")))
        self.highlightTextButton.setFixedSize(32, 32)
        self.highlightTextButton.setToolTip("Evidenzia Testo Selezionato")
        self.highlightTextButton.clicked.connect(self.highlight_selected_text)
        top_controls_layout.addWidget(self.highlightTextButton)

        # Pulsante per incollare il riassunto nella tab Audio AI
        self.pasteSummaryToAudioAIButton = QPushButton('')
        self.pasteSummaryToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        self.pasteSummaryToAudioAIButton.setFixedSize(32, 32)
        self.pasteSummaryToAudioAIButton.setToolTip("Incolla riassunto nella tab Audio AI")
        self.pasteSummaryToAudioAIButton.clicked.connect(lambda: self.paste_to_audio_ai(self.summaryTextArea))
        top_controls_layout.addWidget(self.pasteSummaryToAudioAIButton)

        self.saveSummaryButton = QPushButton('')
        self.saveSummaryButton.setIcon(QIcon(get_resource("save.png")))
        self.saveSummaryButton.setFixedSize(32, 32)
        self.saveSummaryButton.setToolTip("Salva Riassunto nel JSON associato")
        self.saveSummaryButton.clicked.connect(self.save_summary_to_json)
        top_controls_layout.addWidget(self.saveSummaryButton)

        # Separatore
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        top_controls_layout.addWidget(separator)

        # Controlli di estrazione
        self.integraInfoButton = QPushButton("")
        self.integraInfoButton.setIcon(QIcon(get_resource("frame_get.png")))
        self.integraInfoButton.setFixedSize(32, 32)
        self.integraInfoButton.setToolTip("Integra info dal video nel riassunto")
        self.integraInfoButton.clicked.connect(self.integraInfoVideo)
        top_controls_layout.addWidget(self.integraInfoButton)

        top_controls_layout.addWidget(QLabel("Frame:"))
        self.estrazioneFrameCountSpin = QSpinBox()
        self.estrazioneFrameCountSpin.setRange(1, 30)
        self.estrazioneFrameCountSpin.setValue(DEFAULT_FRAME_COUNT)
        top_controls_layout.addWidget(self.estrazioneFrameCountSpin)

        top_controls_layout.addStretch()
        summary_controls_layout.addLayout(top_controls_layout)

        # Layout orizzontale per le checkbox
        bottom_controls_layout = QHBoxLayout()
        self.integrazioneToggle = QCheckBox("Visualizza dopo integrazione")
        self.integrazioneToggle.setEnabled(False)
        self.integrazioneToggle.toggled.connect(self.toggleIntegrazioneView)
        bottom_controls_layout.addWidget(self.integrazioneToggle)

        self.toggleSummaryViewButton = QPushButton("Mostra HTML")
        self.toggleSummaryViewButton.setToolTip("Alterna tra la visualizzazione formattata e il codice sorgente HTML")
        self.toggleSummaryViewButton.setCheckable(True)
        self.toggleSummaryViewButton.toggled.connect(self.toggle_summary_view_mode)
        bottom_controls_layout.addWidget(self.toggleSummaryViewButton)
        self.summary_view_is_raw = False # Stato iniziale

        bottom_controls_layout.addStretch()
        summary_controls_layout.addLayout(bottom_controls_layout)

        summary_layout.addWidget(summary_controls_group)

        self.summaryTextArea = CustomTextEdit(self)
        self.summaryTextArea.setPlaceholderText("Il riassunto generato dall'AI apparirà qui...")
        self.summaryTextArea.timestampDoubleClicked.connect(self.sincronizza_video) # Connetti il segnale
        summary_layout.addWidget(self.summaryTextArea)

        self.transcriptionTabWidget.addTab(summary_tab, "Riassunto")
        self.transcriptionTabWidget.addTab(self.audio_ai_tab, "Audio AI")

        self.transcriptionDock.addWidget(self.transcriptionTabWidget)

        # Impostazioni voce per l'editing audio AI
        voiceSettingsWidget = self.setupVoiceSettingsUI()
        voiceSettingsWidget.setToolTip("Impostazioni voce per l'editing audio AI")
        self.editingDock.addWidget(voiceSettingsWidget)

        # Aggiungi la UI per gli audio generati
        generatedAudiosWidget = self.createGeneratedAudiosUI()
        self.editingDock.addWidget(generatedAudiosWidget)

        # Sincronizza i checkbox di allineamento
        self.alignspeed.toggled.connect(self.alignspeed_replacement.setChecked)
        self.alignspeed_replacement.toggled.connect(self.alignspeed.setChecked)

        # Dizionario per la gestione dei dock
        docks = {
            'videoPlayerDock': self.videoPlayerDock,
            'transcriptionDock': self.transcriptionDock,
            'editingDock': self.editingDock,
            'recordingDock': self.recordingDock,
            'audioDock': self.audioDock,
            'videoPlayerOutput': self.videoPlayerOutput,
            'videoEffectsDock': self.videoEffectsDock,
            'infoDock': self.infoDock,
            'projectDock': self.projectDock,
            'videoNotesDock': self.videoNotesDock
        }
        self.dockSettingsManager = DockSettingsManager(self, docks, self)

        # Collegamenti dei segnali del player
        self.player.durationChanged.connect(self.durationChanged)
        self.player.positionChanged.connect(self.positionChanged)
        self.player.playbackStateChanged.connect(self.updatePlayButtonIcon)
        self.videoSlider.sliderMoved.connect(self.setPosition)




        # --- STATUS BAR ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.setStyleSheet("QStatusBar { padding: 1px; } QStatusBar::item { border: none; }")
        self.statusLabel = QLabel("Pronto")
        self.statusLabel.setToolTip("Mostra lo stato corrente dell'applicazione")
        self.statusBar.addWidget(self.statusLabel, 1) # Il secondo argomento è lo stretch factor

        self.progressBar = QProgressBar(self)
        self.progressBar.setToolTip("Mostra il progresso delle operazioni in corso")
        self.progressBar.setMaximumWidth(300)
        self.progressBar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progressBar)

        self.cancelButton = QPushButton("Annulla")
        self.cancelButton.setToolTip("Annulla l'operazione corrente")
        self.cancelButton.setFixedWidth(100)
        self.cancelButton.setVisible(False)
        self.statusBar.addPermanentWidget(self.cancelButton)


        # --- TOOLBAR (Principale) ---
        mainToolbar = QToolBar("Main Toolbar")
        mainToolbar.setToolTip("Barra degli strumenti principale per le azioni")
        self.addToolBar(mainToolbar)

        mainToolbar.addSeparator()

        # Workflow Actions (Azioni AI)
        self.summarizeMeetingAction = QAction(QIcon(get_resource("meet_sum.png")), 'Riassumi Riunione', self)
        self.summarizeMeetingAction.setStatusTip('Crea un riassunto strutturato della trascrizione di una riunione')
        self.summarizeMeetingAction.triggered.connect(self.summarizeMeeting)
        mainToolbar.addAction(self.summarizeMeetingAction)

        self.summarizeAction = QAction(QIcon(get_resource("text_sum.png")), 'Riassumi Testo', self)
        self.summarizeAction.setStatusTip('Genera un riassunto del testo tramite AI')
        self.summarizeAction.triggered.connect(self.processTextWithAI)
        mainToolbar.addAction(self.summarizeAction)

        self.fixTextAction = QAction(QIcon(get_resource("text_fix.png")), 'Correggi Testo', self)
        self.fixTextAction.setStatusTip('Sistema e migliora il testo tramite AI')
        self.fixTextAction.triggered.connect(self.fixTextWithAI)
        mainToolbar.addAction(self.fixTextAction)

        self.generatePptxAction = QAction(QIcon(get_resource("powerpoint.png")), 'Genera Presentazione', self)
        self.generatePptxAction.setStatusTip('Crea una presentazione PowerPoint dal testo')
        self.generatePptxAction.triggered.connect(self.openPptxDialog)
        mainToolbar.addAction(self.generatePptxAction)

        # --- SECONDA TOOLBAR (Workspace e Impostazioni) ---
        workspaceToolbar = QToolBar("Workspace Toolbar")
        workspaceToolbar.setToolTip("Barra degli strumenti per layout e impostazioni")
        self.addToolBar(workspaceToolbar)

        # Workspace Actions (Layouts)


        self.recordingLayoutAction = QAction(QIcon(get_resource("rec.png")), 'Registrazione', self)
        self.recordingLayoutAction.setToolTip("Layout per la registrazione")
        self.recordingLayoutAction.triggered.connect(self.dockSettingsManager.loadRecordingLayout)
        workspaceToolbar.addAction(self.recordingLayoutAction)

        self.comparisonLayoutAction = QAction(QIcon(get_resource("compare.png")), 'Confronto', self)
        self.comparisonLayoutAction.setToolTip("Layout per il confronto")
        self.comparisonLayoutAction.triggered.connect(self.dockSettingsManager.loadComparisonLayout)
        workspaceToolbar.addAction(self.comparisonLayoutAction)

        self.transcriptionLayoutAction = QAction(QIcon(get_resource("script.png")), 'Trascrizione', self)
        self.transcriptionLayoutAction.setToolTip("Layout per la trascrizione")
        self.transcriptionLayoutAction.triggered.connect(self.dockSettingsManager.loadTranscriptionLayout)
        workspaceToolbar.addAction(self.transcriptionLayoutAction)

        self.defaultLayoutAction = QAction(QIcon(get_resource("default.png")), 'Default', self)
        self.defaultLayoutAction.setToolTip("Layout di default")
        self.defaultLayoutAction.triggered.connect(self.dockSettingsManager.loadDefaultLayout)
        workspaceToolbar.addAction(self.defaultLayoutAction)
        workspaceToolbar.addSeparator()

        serviceToolbar = QToolBar("Rec Toolbar")
        serviceToolbar.setToolTip("Barra servizio")
        self.addToolBar(serviceToolbar)

        # Aggiungi l'indicatore di registrazione lampeggiante
        #serviceToolbar.addWidget(self.recording_indicator)

        # Azione di condivisione
        shareAction = QAction(QIcon(get_resource("share.png")), "Condividi Video", self)
        shareAction.setToolTip("Condividi il video attualmente caricato")
        shareAction.triggered.connect(self.onShareButtonClicked)
        serviceToolbar.addAction(shareAction)

        # Azione Impostazioni
        settingsAction = QAction(QIcon(get_resource("gear.png")), "Impostazioni", self)
        settingsAction.setToolTip("Apri le impostazioni dell'applicazione")
        settingsAction.triggered.connect(self.showSettingsDialog)
        serviceToolbar.addAction(settingsAction)

        serviceToolbar.addSeparator()
        # Configurazione della menu bar (questa parte rimane invariata)
        self.setupMenuBar()

        # Applica il tema scuro, se disponibile
        if hasattr(self, 'applyDarkMode'):
            self.applyDarkMode()

        # Applica lo stile a tutti i dock
        self.applyStyleToAllDocks()

        # Applica le impostazioni del font
        self.apply_and_save_font_settings()

        # Connetti i segnali per il cambio di font
        self.transcriptionTextArea.fontSizeChanged.connect(self.apply_and_save_font_settings)
        self.summaryTextArea.fontSizeChanged.connect(self.apply_and_save_font_settings)

    def apply_and_save_font_settings(self, size=None):
        """
        Applica le impostazioni del font (famiglia e dimensione) alle aree di testo
        e salva la dimensione se viene modificata.
        """
        settings = QSettings("Genius", "GeniusAI")

        font_family = settings.value("editor/fontFamily", "Arial")

        if size is None:
            font_size = settings.value("editor/fontSize", 14, type=int)
        else:
            font_size = size
            settings.setValue("editor/fontSize", font_size)

        font = QFont(font_family, font_size)

        self.transcriptionTextArea.setFont(font)
        self.summaryTextArea.setFont(font)
        if hasattr(self, 'audioAiTextArea'):
            self.audioAiTextArea.setFont(font)

    def videoContainerResizeEvent(self, event):
        # When the container is resized, resize both the video widget and the overlay
        if self.zoom_level == 1.0:
            self.videoCropWidget.setGeometry(self.videoContainer.rect())
            self.videoOverlay.setGeometry(self.videoContainer.rect())
            self.audioOnlyLabel.setGeometry(self.videoContainer.rect())
            self.audioOnlyLabel.setPixmap(QPixmap(get_resource("audio_only.png")).scaled(
                self.videoContainer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        QWidget.resizeEvent(self.videoContainer, event)

    def videoCropWidgetResizeEvent(self, event):
        # The overlay is now a sibling of the video widget, so we don't need to resize it here.
        # Just call the original resize event.
        CropVideoWidget.resizeEvent(self.videoCropWidget, event)

    def handle_pan(self, delta):
        new_pos = self.videoCropWidget.pos() + delta
        self.videoCropWidget.move(new_pos)

    def handle_zoom(self, delta, mouse_pos):
        old_zoom_level = self.zoom_level
        if delta > 0:
            self.zoom_level *= 1.1
        elif delta < 0:
            self.zoom_level *= 0.9

        original_size = self.videoContainer.size()
        new_width = int(original_size.width() * self.zoom_level)
        new_height = int(original_size.height() * self.zoom_level)
        self.videoCropWidget.resize(new_width, new_height)

        scale_change = self.zoom_level / old_zoom_level
        new_x = mouse_pos.x() * scale_change - mouse_pos.x()
        new_y = mouse_pos.y() * scale_change - mouse_pos.y()
        current_pos = self.videoCropWidget.pos()
        new_pos = QPoint(current_pos.x() - int(new_x), current_pos.y() - int(new_y))
        self.videoCropWidget.move(new_pos)

    def reset_view(self):
        self.zoom_level = 1.0
        self.videoCropWidget.setGeometry(self.videoContainer.rect())

    def createWorkflow(self):
        # Implementazione per creare un nuovo workflow
        print("Funzione createWorkflow da implementare")
        # Qui puoi mostrare un dialogo per creare un nuovo workflow

    def loadWorkflow(self):
        # Implementazione per caricare un workflow esistente
        print("Funzione loadWorkflow da implementare")
        # Qui puoi mostrare un dialogo per selezionare e caricare un workflow esistente

    def configureAgent(self):
        """
        Configura l'agent AI mostrando il dialogo di configurazione
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.showConfigDialog()

    def runAgent(self):
        """
        Esegue l'agent AI con la configurazione corrente
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.runAgent()

    def showMediaInfo(self):
        # Implementazione per mostrare informazioni sul media
        print("Funzione showMediaInfo da implementare")
        # Qui puoi mostrare un dialog con le informazioni sul media corrente
    def onExtractFramesClicked(self):
        if not self.videoPathLineEdit:
            QMessageBox.warning(self, "Attenzione", "Nessun video caricato.")
            return

        self.infoExtractionResultArea.setPlainText("Analisi in corso...")

        self.analyzer = CombinedAnalyzer(
            video_path=self.videoPathLineEdit,
            num_frames=self.infoFrameCountSpin.value(),
            language=self.languageInput.currentText(),
            combined_mode=self.combinedAnalysisCheckbox.isChecked(),
            parent_for_transcription=self
        )
        self.analyzer.analysis_complete.connect(self.onAnalysisComplete)
        self.analyzer.analysis_error.connect(self.onAnalysisError)
        self.analyzer.progress_update.connect(self.onAnalysisProgress)
        self.analyzer.start_analysis()

    def onAnalysisComplete(self, summary):
        self.infoExtractionResultArea.setPlainText(summary)
        self.show_status_message("Analisi completata con successo.")

    def onAnalysisError(self, error_message):
        self.infoExtractionResultArea.setPlainText(f"Errore durante l'analisi:\n{error_message}")
        QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante l'analisi:\n{error_message}")

    def onAnalysisProgress(self, message):
        self.infoExtractionResultArea.append(message)

    def toggle_transcription_view(self, checked):
        """
        Alterna la visualizzazione nella casella di testo della trascrizione
        tra la versione originale e quella corretta.
        """
        if checked:
            # Mostra il testo corretto, se disponibile
            if self.transcription_corrected:
                self.transcriptionTextArea.setPlainText(self.transcription_corrected)
        else:
            # Mostra il testo originale con formattazione
            self.transcriptionTextArea.setHtml(self.transcription_original)

    def integraInfoVideo(self):
        if not self.videoPathLineEdit:
            self.show_status_message("Nessun video caricato.", error=True)
            return

        if not self.summary_generated or not self.summary_generated.strip():
            self.show_status_message("È necessario generare un riassunto standard prima di poterlo integrare.", error=True)
            return

        # Passa l'HTML del riassunto direttamente al thread
        thread = VideoIntegrationThread(
            video_path=self.videoPathLineEdit,
            num_frames=self.estrazioneFrameCountSpin.value(),
            language=self.languageComboBox.currentText(),
            current_summary_html=self.summary_generated, # Passa l'HTML
            parent=self
        )
        self.start_task(thread, self.onIntegrazioneComplete, self.onIntegrazioneError, self.update_status_progress)

    def onIntegrazioneComplete(self, summary):
        self.summary_generated_integrated = summary
        self.summaries['integrative_summary'] = summary
        self.summary_text = self.summary_generated_integrated
        self.update_summary_view()
        self.integrazioneToggle.setEnabled(True)
        self.integrazioneToggle.setChecked(True)
        self.show_status_message("Integrazione delle informazioni dal video completata.")
        update_data = {
            "summary_generated_integrated": summary,
            "summary_date": datetime.datetime.now().isoformat()
        }
        self._update_json_file(self.videoPathLineEdit, update_data)

    def onIntegrazioneError(self, error_message):
        self.show_status_message(f"Errore durante l'integrazione: {error_message}", error=True)
        self.integrazioneToggle.setEnabled(False)

    def toggleIntegrazioneView(self, checked):
        """
        Alterna la visualizzazione nell'area del riassunto tra il riassunto standard
        e quello integrato con le informazioni del video.
        """
        if checked:
            self.summary_text = self.summary_generated_integrated
        else:
            self.summary_text = self.summary_generated

        self.update_summary_view()

    def toggle_recording_indicator(self):
        """Toggles the visibility of the recording indicator to make it blink."""
        if self.is_recording:
            self.recording_indicator.setVisible(not self.recording_indicator.isVisible())
        else:
            self.recording_indicator.setVisible(False)
            if self.indicator_timer.isActive():
                self.indicator_timer.stop()

    def onShareButtonClicked(self):
        # Usa il percorso del video nel dock Video Player Output
        video_path = self.videoPathLineOutputEdit
        self.videoSharingManager.shareVideo(video_path)
    def load_version_info(self):
        """
        Carica le informazioni di versione e data dal file di versione.
        """
        version = "Sconosciuta"
        build_date = "Sconosciuta"

        # Verifica se il file esiste
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if "Version" in line:
                        version = line.split(":")[1].strip()  # Estrai la versione
                    elif "Build Date" in line:
                        build_date = line.split(":")[1].strip()  # Estrai la data di build
        else:
            print(f"File {self.version_file} non trovato.")

        return version, build_date

    def setPlaybackRateInput(self, rate):
        if rate == 0:
            rate = 1
            self.speedSpinBox.setValue(1)

        if rate > 0:
            self.reverseTimer.stop()
            self.player.setPlaybackRate(float(rate))
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self.player.play()
        else:  # rate < 0
            self.player.pause()
            self.player.setPlaybackRate(1.0)
            interval = int(1000 / (self.get_current_fps() * abs(rate)))
            if interval <= 0:
                interval = 20
            self.reverseTimer.start(interval)

    def reversePlaybackStep(self):
        current_pos = self.player.position()
        step = 1000 / self.get_current_fps()
        new_pos = current_pos - step
        if new_pos < 0:
            new_pos = 0
            self.reverseTimer.stop()
            self.playButton.setIcon(QIcon(get_resource("play.png")))
        self.player.setPosition(int(new_pos))

    def setPlaybackRateOutput(self, rate):
        if rate == 0:
            rate = 1
            self.speedSpinBoxOutput.setValue(1)

        if rate > 0:
            self.reverseTimerOutput.stop()
            self.playerOutput.setPlaybackRate(float(rate))
            if self.playerOutput.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self.playerOutput.play()
        else:  # rate < 0
            self.playerOutput.pause()
            self.playerOutput.setPlaybackRate(1.0)
            interval = int(1000 / (self.get_current_fps_output() * abs(rate)))
            if interval <= 0:
                interval = 20
            self.reverseTimerOutput.start(interval)

    def reversePlaybackStepOutput(self):
        current_pos = self.playerOutput.position()
        step = 1000 / self.get_current_fps_output()
        new_pos = current_pos - step
        if new_pos < 0:
            new_pos = 0
            self.reverseTimerOutput.stop()
            self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
        self.playerOutput.setPosition(int(new_pos))

    def get_current_fps_output(self):
        if not self.videoPathLineOutputEdit:
            return 30
        try:
            return VideoFileClip(self.videoPathLineOutputEdit).fps
        except Exception as e:
            print(f"Error getting FPS for output: {e}")
            return 30  # default fps

    def togglePlayPauseOutput(self):
        rate = self.speedSpinBoxOutput.value()
        if rate < 0:
            if self.reverseTimerOutput.isActive():
                self.reverseTimerOutput.stop()
                self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
            else:
                interval = int(1000 / (self.get_current_fps_output() * abs(rate)))
                if interval <= 0: interval = 20
                self.reverseTimerOutput.start(interval)
                self.playButtonOutput.setIcon(QIcon(get_resource("pausa.png")))
        else:
            if self.playerOutput.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.playerOutput.pause()
                self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
            else:
                self.playerOutput.play()
                self.playButtonOutput.setIcon(QIcon(get_resource("pausa.png")))

    def togglePlayPause(self):
        rate = self.speedSpinBox.value()
        if rate < 0:
            if self.reverseTimer.isActive():
                self.reverseTimer.stop()
                self.playButton.setIcon(QIcon(get_resource("play.png")))
            else:
                interval = int(1000 / (self.get_current_fps() * abs(rate)))
                if interval <= 0: interval = 20
                self.reverseTimer.start(interval)
                self.playButton.setIcon(QIcon(get_resource("pausa.png")))
        else:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.playButton.setIcon(QIcon(get_resource("play.png")))  # Cambia l'icona in Play
            else:
                self.player.play()
                self.playButton.setIcon(QIcon(get_resource("pausa.png")))  # Cambia l'icona in Pausa

    def syncOutputWithSourcePosition(self):
        source_position = self.player.position()
        self.playerOutput.setPosition(source_position)
        self.playVideo()
        self.playerOutput.play()

    def summarizeMeeting(self):
        current_text = self.transcriptionTextArea.toPlainText()
        if not current_text.strip():
            self.show_status_message("Inserisci la trascrizione della riunione da riassumere.", error=True)
            return

        self.original_text = current_text
        self.current_summary_type = 'meeting'

        thread = MeetingSummarizer(
            current_text,
            self.languageComboBox.currentText()
        )
        self.start_task(thread, self.onProcessComplete, self.onProcessError, self.update_status_progress)

    def processTextWithAI(self):
        current_text = self.transcriptionTextArea.toPlainText()
        if not current_text.strip():
            self.show_status_message("Inserisci del testo da riassumere.", error=True)
            return

        self.original_text = current_text
        self.current_summary_type = 'text'

        thread = ProcessTextAI(
            mode="summary",
            language=self.languageComboBox.currentText(),
            prompt_vars={'text': current_text}
        )
        self.start_task(thread, self.onProcessComplete, self.onProcessError, self.update_status_progress)

    def paste_to_audio_ai(self, source_text_edit):
        """
        Copia il testo dall'area di testo sorgente all'area di testo della tab Audio AI.
        """
        text_to_paste = source_text_edit.toPlainText()
        self.audioAiTextArea.setPlainText(text_to_paste)
        self.transcriptionTabWidget.setCurrentWidget(self.audio_ai_tab)
        self.show_status_message("Testo incollato nella tab Audio AI.")

    def fixTranscriptionWithAI(self):
        """
        Avvia il processo di correzione del testo nella tab di trascrizione.
        """
        current_text = self.transcriptionTextArea.toPlainText()
        if not current_text.strip():
            self.show_status_message("La trascrizione è vuota. Non c'è nulla da correggere.", error=True)
            return

        # Salva la trascrizione corrente come originale, se non è già stato fatto
        if not self.transcription_original:
            self.transcription_original = current_text

        self.current_summary_type = 'transcription_fix' # Tipo specifico per questa azione

        thread = ProcessTextAI(
            mode="fix",
            language=self.languageComboBox.currentText(),
            prompt_vars={'text': current_text}
        )
        self.start_task(thread, self.onProcessComplete, self.onProcessError, self.update_status_progress)

    def fixTextWithAI(self):
        current_text = self.transcriptionTextArea.toPlainText()
        if not current_text.strip():
            self.show_status_message("Inserisci del testo da correggere.", error=True)
            return

        self.original_text = current_text
        self.current_summary_type = 'fix' # Assumendo che questo sia un tipo valido

        thread = ProcessTextAI(
            mode="fix",
            language=self.languageComboBox.currentText(),
            prompt_vars={'text': current_text}
        )
        self.start_task(thread, self.onProcessComplete, self.onProcessError, self.update_status_progress)

    def summarizeYouTube(self):
        url, ok = QInputDialog.getText(self, 'Riassunto YouTube', 'Inserisci l\'URL del video di YouTube:')
        if ok and url:
            thread = DownloadThread(url, download_video=False, ffmpeg_path=FFMPEG_PATH_DOWNLOAD)
            self.start_task(thread, self.onYouTubeDownloadFinished, self.onProcessError, self.update_status_progress)

    def onYouTubeDownloadFinished(self, result):
        audio_path, _, _, _ = result
        thread = TranscriptionThread(audio_path, self)
        self.start_task(thread, self.onYouTubeTranscriptionFinished, self.onProcessError, self.update_status_progress)

    def onYouTubeTranscriptionFinished(self, result):
        transcript, temp_files = result
        self.cleanupFiles(temp_files) # Pulisce i file temporanei della trascrizione

        thread = ProcessTextAI(
            mode="youtube_summary",
            language=self.languageComboBox.currentText(),
            prompt_vars={'text': transcript}
        )
        # Il callback onProcessComplete gestirà già il risultato
        self.start_task(thread, self.onProcessComplete, self.onProcessError, self.update_status_progress)

    def _sync_transcription_state_from_ui(self):
        """Sincronizza le variabili di stato della trascrizione con il contenuto della UI."""
        if self.transcriptionViewToggle.isEnabled() and self.transcriptionViewToggle.isChecked():
            self.transcription_corrected = self.transcriptionTextArea.toPlainText()
        else:
            self.transcription_original = self.transcriptionTextArea.toHtml()

    def _sync_summary_state_from_ui(self):
        """
        Sincronizza le variabili di stato del riassunto con il contenuto della UI,
        tenendo conto della modalità di visualizzazione (grezza o formattata).
        """
        if self.summary_view_is_raw:
            # Se siamo in modalità HTML grezzo, il testo semplice è la nostra fonte di verità
            current_html = self.summaryTextArea.toPlainText()
        else:
            # Altrimenti, prendiamo l'HTML renderizzato
            current_html = self.summaryTextArea.toHtml()

        if self.integrazioneToggle.isEnabled() and self.integrazioneToggle.isChecked():
            self.summary_generated_integrated = current_html
        else:
            self.summary_generated = current_html
        self.summary_text = current_html # Aggiorna anche la variabile di visualizzazione

    def save_transcription_to_json(self):
        """
        Salva solo il contenuto della scheda Trascrizione nel file JSON.
        """
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            self.show_status_message("Salvataggio fallito: nessun video sorgente caricato.", error=True)
            return

        self._sync_transcription_state_from_ui()

        update_data = {
            "transcription_original": self.transcription_original,
            "transcription_corrected": self.transcription_corrected,
            "last_save_date": datetime.datetime.now().isoformat()
        }
        self._update_json_file(self.videoPathLineEdit, update_data)
        self.show_status_message("Trascrizione salvata nel file JSON.", timeout=3000)

    def save_summary_to_json(self):
        """
        Salva solo il contenuto della scheda Riassunto nel file JSON.
        """
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            self.show_status_message("Salvataggio fallito: nessun video sorgente caricato.", error=True)
            return

        self._sync_summary_state_from_ui()

        update_data = {
            "summary_generated": self.summary_generated,
            "summary_generated_integrated": self.summary_generated_integrated,
            "last_save_date": datetime.datetime.now().isoformat()
        }
        self._update_json_file(self.videoPathLineEdit, update_data)
        self.show_status_message("Riassunto salvato nel file JSON.", timeout=3000)

    def save_audio_ai_to_json(self):
        """
        Salva solo il testo della scheda Audio AI nel file JSON.
        """
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            self.show_status_message("Salvataggio fallito: nessun video sorgente caricato.", error=True)
            return

        update_data = {
            "audio_ai_text": self.audioAiTextArea.toPlainText(),
            "last_save_date": datetime.datetime.now().isoformat()
        }
        self._update_json_file(self.videoPathLineEdit, update_data)
        self.show_status_message("Testo Audio AI salvato nel file JSON.", timeout=3000)

    def save_all_tabs_to_json(self, show_message=True):
        """
        Salva i contenuti di tutte le schede rilevanti (Trascrizione, Riassunto, Audio AI)
        nel file JSON associato al video corrente. Legge i dati direttamente dai widget UI
        per garantire che le modifiche più recenti vengano salvate.
        """
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            if show_message:
                self.show_status_message("Salvataggio fallito: nessun video sorgente caricato.", error=True)
            return

        logging.info(f"Salvataggio di tutti i contenuti nel JSON per {self.videoPathLineEdit}...")

        # 1. Sincronizza lo stato interno con la UI utilizzando i metodi helper
        self._sync_transcription_state_from_ui()
        self._sync_summary_state_from_ui()

        # 2. Salva lo stato aggiornato
        update_data = {
            "transcription_original": self.transcription_original,
            "transcription_corrected": self.transcription_corrected,
            "summary_generated": self.summary_generated,
            "summary_generated_integrated": self.summary_generated_integrated,
            "audio_ai_text": self.audioAiTextArea.toPlainText(),
            "last_save_date": datetime.datetime.now().isoformat()
        }

        # La funzione _update_json_file gestirà la lettura, l'aggiornamento e la scrittura.
        self._update_json_file(self.videoPathLineEdit, update_data)

        if show_message:
            self.show_status_message("Tutte le modifiche sono state salvate nel file JSON.", timeout=3000)

    def _update_json_file(self, video_path, update_dict):
        """
        Helper function to update specific fields in a video's JSON file.
        """
        if not video_path or not os.path.exists(video_path):
            logging.warning("Aggiornamento JSON saltato: nessun video sorgente caricato.")
            return

        json_path = os.path.splitext(video_path)[0] + ".json"

        try:
            # Leggi i dati esistenti
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Impossibile leggere il file JSON {json_path} per l'aggiornamento: {e}. L'operazione verrà annullata.")
            return

        # Aggiorna i campi
        data.update(update_dict)
        # Assicura che anche le trascrizioni siano sempre aggiornate
        if self.transcription_original:
            data["transcription_original"] = self.transcription_original
        if self.transcription_corrected:
            data["transcription_corrected"] = self.transcription_corrected

        # Salva i dati aggiornati
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info(f"File JSON {json_path} aggiornato con successo.")
            # Aggiorna il dock informativo
            self.infoDock.update_info(data)
        except Exception as e:
            logging.error(f"Errore durante il salvataggio del file JSON aggiornato: {e}")

    def handleTimecodeToggle(self, checked):
        # Applica la logica solo all'area di testo dell'Audio AI
        self.timecodeEnabled = checked
        text_area = self.audioAiTextArea # Target solo l'area AI

        text_area.setReadOnly(checked)
        if checked:
            # Salva l'HTML corrente e applica i timecode
            original_html = text_area.toHtml()
            # Salva l'originale in un attributo dinamico per evitare conflitti
            setattr(self, f"original_html_for_{text_area.objectName()}", original_html)
            updated_html = self.calculateAndDisplayTimeCodeAtEndOfSentences(original_html)
            text_area.setHtml(updated_html)
        else:
            # Ripristina l'HTML originale
            original_html = getattr(self, f"original_html_for_{text_area.objectName()}", "")
            if original_html:
                text_area.setHtml(original_html)


    def updateProgressDialog(self, value, label):
        if not self.progressDialog.wasCanceled():
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(label)

    def onProcessComplete(self, result):
        if isinstance(result, dict):
            self.transcriptionTextArea.setPlainText(result.get('transcription_raw', ''))
            return

        if hasattr(self, 'current_summary_type') and self.current_summary_type:
            if self.current_summary_type == 'transcription_fix':
                self.transcription_corrected = result
                self.transcriptionTextArea.setPlainText(result)
                self.show_status_message("Correzione del testo completata.")
                # Abilita il toggle per mostrare/nascondere la correzione
                self.transcriptionViewToggle.setEnabled(True)
                self.transcriptionViewToggle.setChecked(True)
            else:
                # Converti il risultato Markdown in HTML prima di memorizzarlo e visualizzarlo
                html_summary = markdown.markdown(result)
                self.summaries[self.current_summary_type] = html_summary
                self.active_summary_type = self.current_summary_type

                self.summary_generated = html_summary
                self.summary_text = html_summary
                self.update_summary_view()

                self.integrazioneToggle.setChecked(False)
                self.transcriptionTabWidget.setCurrentIndex(1)

                update_data = {
                    "summary_generated": html_summary,
                    "summary_date": datetime.datetime.now().isoformat()
                }
                self._update_json_file(self.videoPathLineEdit, update_data)

            self.current_summary_type = None

    def update_summary_view(self):
        """
        Aggiorna la visualizzazione dell'area di testo del riassunto con il contenuto HTML,
        applicando una colorazione azzurra ai timecode.
        """
        if not hasattr(self, 'summary_text'):
            return

        html_content = self.summary_text

        # Pattern robusto per trovare vari formati di timecode come [00:01:15.3] o [01:15]
        timestamp_pattern = re.compile(r'(\[\d{2}:\d{2}:\d{2}(?:\.\d)?\]|\[\d{2}:\d{2}(?:\.\d)?\]|\[\d+:\d+:\d+(\.\d)?\])')

        # Funzione per sostituire il timecode con la versione stilizzata
        def style_match(match):
            return f"<font color='#ADD8E6'>{match.group(1)}</font>"

        # Prima rimuoviamo eventuali tag di stile preesistenti per evitare doppioni,
        # poi applichiamo quello nuovo.
        # Questo passaggio è importante se la funzione viene chiamata più volte sullo stesso testo.
        temp_html = re.sub(r"<font color='#ADD8E6'>(.*?)</font>", r'\1', html_content if html_content else "")
        styled_html = timestamp_pattern.sub(style_match, temp_html)

        # Imposta l'HTML finale nell'area di testo
        self.summaryTextArea.blockSignals(True)
        self.summaryTextArea.setHtml(styled_html)
        self.summaryTextArea.blockSignals(False)

    def onProcessError(self, error_message):
        # This is now a generic error handler for AI text processes.
        # The main error display is handled by finish_task.
        self.show_status_message(f"Errore processo AI: {error_message}", error=True)

    def highlight_selected_text(self):
        """Applies or removes the selected highlight color from the text."""
        cursor = self.summaryTextArea.textCursor()
        if not cursor.hasSelection():
            return

        # Safely get the color info. If the configured color is invalid,
        # fall back to the first color in the dictionary.
        default_color_name = next(iter(self.highlight_colors))
        color_info = self.highlight_colors.get(self.current_highlight_color_name, self.highlight_colors[default_color_name])
        if self.current_highlight_color_name not in self.highlight_colors:
            logging.warning(f"Invalid highlight color '{self.current_highlight_color_name}' found in settings. Falling back to '{default_color_name}'.")
            self.current_highlight_color_name = default_color_name

        highlight_color = color_info["qcolor"]

        # Determine if we are applying or removing the highlight
        current_format = cursor.charFormat()
        new_format = QTextCharFormat()

        if current_format.background().color() == highlight_color:
            # If the current background is the highlight color, remove it (make it transparent)
            new_format.setBackground(QColor(Qt.GlobalColor.transparent))
        else:
            # Otherwise, apply the highlight color
            new_format.setBackground(highlight_color)

        cursor.mergeCharFormat(new_format)

    def toggle_summary_view_mode(self, checked):
        """
        Alterna la visualizzazione dell'editor del riassunto tra testo formattato e sorgente HTML.
        """
        self.summary_view_is_raw = checked
        self.summaryTextArea.blockSignals(True) # Blocca i segnali per evitare loop

        if checked:
            # Passa alla visualizzazione HTML grezzo
            current_html = self.summaryTextArea.toHtml()
            self.summaryTextArea.setPlainText(current_html)
            self.toggleSummaryViewButton.setText("Mostra Testo")
        else:
            # Passa alla visualizzazione formattata
            raw_html = self.summaryTextArea.toPlainText()
            self.summaryTextArea.setHtml(raw_html)
            self.toggleSummaryViewButton.setText("Mostra HTML")

        self.summaryTextArea.blockSignals(False) # Riattiva i segnali

    def openPptxDialog(self):
        """Apre il dialogo per la generazione della presentazione PowerPoint."""
        current_text = self.transcriptionTextArea.toPlainText()
        if not current_text.strip():
            self.show_status_message("Il campo della trascrizione è vuoto. Inserisci del testo prima di generare una presentazione.", error=True)
            return

        dialog = PptxDialog(self, transcription_text=current_text)
        dialog.exec()

    def showSettingsDialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.load_recording_settings()
            self.apply_and_save_font_settings()

    def set_default_dock_layout(self):

        # Set default visibility
        self.videoPlayerOutput.setVisible(True)
        self.recordingDock.setVisible(True)

        # Set other docks as invisible
        self.videoPlayerDock.setVisible(False)
        self.audioDock.setVisible(False)
        self.transcriptionDock.setVisible(False)
        self.editingDock.setVisible(False)

    def openRootFolder(self):
        root_folder_path = os.path.dirname(os.path.abspath(__file__))
        QDesktopServices.openUrl(QUrl.fromLocalFile(root_folder_path))

    def deleteVideoSegment(self):
        if not self.videoSlider.bookmarks:
            self.show_status_message("Per favore, imposta almeno un bookmark prima di eliminare.", error=True)
            return

        media_path = self.videoPathLineEdit
        if not media_path:
            self.show_status_message("Per favore, seleziona un file prima di eliminarne una parte.", error=True)
            return

        is_audio_only = self.isAudioOnly(media_path)

        try:
            if is_audio_only:
                media_clip = AudioFileClip(media_path)
            else:
                media_clip = VideoFileClip(media_path)

            clips_to_keep = []
            last_end_time = 0.0
            for start_ms, end_ms in sorted(self.videoSlider.bookmarks):
                start_time = start_ms / 1000.0
                end_time = end_ms / 1000.0
                if start_time > last_end_time:
                    clips_to_keep.append(media_clip.subclip(last_end_time, start_time))
                last_end_time = end_time

            if last_end_time < media_clip.duration:
                clips_to_keep.append(media_clip.subclip(last_end_time))

            if not clips_to_keep:
                self.show_status_message("Nessuna parte del video da conservare. L'operazione cancellerebbe l'intero file.", error=True)
                return

            if is_audio_only:
                final_media = concatenate_audioclips(clips_to_keep)
                ext = ".mp3"
            else:
                final_media = concatenate_videoclips(clips_to_keep)
                ext = ".mp4"

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            output_dir = os.path.dirname(media_path)
            output_name = f"modified_{timestamp}{ext}"
            output_path = os.path.join(output_dir, output_name)

            if is_audio_only:
                final_media.write_audiofile(output_path)
            else:
                final_media.write_videofile(output_path, codec='libx264', audio_codec='aac')

            self.show_status_message(f"Parti del file eliminate. File salvato.")
            self.loadVideoOutput(output_path)

        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'eliminazione", str(e))
        finally:
            if 'media_clip' in locals():
                media_clip.close()
    def insertPause(self):
        cursor = self.audioAiTextArea.textCursor()
        pause_time = self.pauseTimeEdit.text().strip()

        if not re.match(r'^\d+(\.\d+)?s$', pause_time):
            self.show_status_message("Inserisci un formato valido per la pausa (es. 1.0s)", error=True)
            return

        pause_tag = f'<break time="{pause_time}" />'
        cursor.insertText(f' {pause_tag} ')
        self.audioAiTextArea.setTextCursor(cursor)

    def rewind5Seconds(self):
        current_position = self.player.position()
        new_position = max(0, current_position - 5000)
        self.player.setPosition(new_position)

    def forward5Seconds(self):
        current_position = self.player.position()
        new_position = current_position + 5000
        self.player.setPosition(new_position)

    def frameBackward(self):
        self.get_previous_frame()

    def frameForward(self):
        self.get_next_frame()

    def goToTimecode(self):
        timecode_text = self.timecodeInput.text()
        try:
            parts = timecode_text.split(':')
            if len(parts) != 4:
                raise ValueError("Invalid timecode format")

            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            milliseconds = int(parts[3])

            total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            self.player.setPosition(total_milliseconds)
        except (ValueError, IndexError):
            self.show_status_message("Formato timecode non valido. Usa HH:MM:SS:ms.", error=True)

    def releaseSourceVideo(self):
        self.player.stop()
        time.sleep(.01)
        self.currentTimeLabel.setText('00:00')
        self.totalTimeLabel.setText('00:00')
        self.player.setSource(QUrl())
        self.videoPathLineEdit = ''
        self.fileNameLabel.setText("Nessun video caricato")
        self.videoNotesListWidget.clear()
    def releaseOutputVideo(self):
        self.playerOutput.stop()
        time.sleep(.01)
        self.currentTimeLabelOutput.setText('00:00')
        self.totalTimeLabelOutput.setText('00:00')
        self.playerOutput.setSource(QUrl())
        self.videoPathLineOutputEdit = ''
        self.fileNameLabelOutput.setText("Nessun video caricato")

    def get_nearest_timecode(self):
        cursor_position = self.audioAiTextArea.textCursor().position()
        text = self.audioAiTextArea.toPlainText()

        # Regex per trovare [MM:SS.d] o [MM:SS]
        timecode_pattern = re.compile(r'\[(\d{2}):(\d{2}(?:\.\d)?)\]')
        matches = list(timecode_pattern.finditer(text))

        if not matches:
            logging.debug("Nessun timecode trovato nella trascrizione.")
            return None

        nearest_match = None
        min_distance = float('inf')

        for match in matches:
            start, end = match.span()
            distance = abs(cursor_position - start)
            if distance < min_distance:
                min_distance = distance
                nearest_match = match

        if nearest_match:
            try:
                time_str = nearest_match.group(1)
                if '.' in time_str:
                    minutes, seconds = map(float, time_str.split(':'))
                else:
                    minutes, seconds = map(int, time_str.split(':'))

                total_seconds = minutes * 60 + seconds
                logging.debug(f"Timecode più vicino: {total_seconds} secondi")
                return total_seconds
            except ValueError as e:
                logging.error(f"Errore durante la conversione del timecode in secondi: {e}")
                return None

        logging.debug("Nessun timecode valido trovato.")
        return None

    def sync_video_to_transcription(self):
        timecode_seconds = self.get_nearest_timecode()

        if timecode_seconds is not None:
            try:
                self.player.setPosition(timecode_seconds * 1000)
                logging.info(f"Video sincronizzato al timecode: {timecode_seconds} secondi")
            except Exception as e:
                logging.error(f"Errore durante la sincronizzazione del video: {e}")
                QMessageBox.critical(self, "Errore", "Impossibile sincronizzare il video.")
        else:
            self.show_status_message("Nessun timecode trovato nella trascrizione.", error=True)

    def sincronizza_video(self, seconds):
        """
        Sincronizza il video al timestamp specificato in secondi.
        """
        if self.player:
            self.player.setPosition(int(seconds * 1000))

    def setStartBookmark(self):
        self.videoSlider.setPendingBookmarkStart(self.player.position())

    def setEndBookmark(self):
        if self.videoSlider.pending_bookmark_start is not None:
            start_pos = self.videoSlider.pending_bookmark_start
            end_pos = self.player.position()
            self.videoSlider.addBookmark(start_pos, end_pos)
        else:
            self.show_status_message("Imposta prima un segnalibro di inizio.", error=True)

    def clearBookmarks(self):
        self.videoSlider.resetBookmarks()

    def cutVideoBetweenBookmarks(self):
        if not self.videoSlider.bookmarks:
            self.show_status_message("Per favore, imposta almeno un bookmark prima di tagliare.", error=True)
            return

        media_path = self.videoPathLineEdit
        if not media_path:
            self.show_status_message("Per favore, seleziona un file prima di tagliarlo.", error=True)
            return

        is_audio_only = self.isAudioOnly(media_path)

        clips = []
        final_media = None
        try:
            if is_audio_only:
                media_clip = AudioFileClip(media_path)
            else:
                media_clip = VideoFileClip(media_path)

            for start_ms, end_ms in self.videoSlider.bookmarks:
                start_time = start_ms / 1000.0
                end_time = end_ms / 1000.0
                clips.append(media_clip.subclip(start_time, end_time))

            if not clips:
                self.show_status_message("Nessun clip valido da tagliare.", error=True)
                return

            if is_audio_only:
                final_media = concatenate_audioclips(clips)
            else:
                final_media = concatenate_videoclips(clips)

            base_name = os.path.splitext(os.path.basename(media_path))[0]
            directory = os.path.dirname(media_path)
            ext = ".mp3" if is_audio_only else ".mp4"
            output_path = os.path.join(directory, f"{base_name}_cut{ext}")

            if is_audio_only:
                final_media.write_audiofile(output_path)
            else:
                final_media.write_videofile(output_path, codec='libx264', audio_codec='aac')

            self.show_status_message(f"File tagliato salvato in: {os.path.basename(output_path)}")
            self.loadVideoOutput(output_path)

        except Exception as e:
            QMessageBox.critical(self, "Errore durante il taglio", str(e))
            return
        finally:
            if 'media_clip' in locals():
                media_clip.close()
            if final_media:
                if is_audio_only:
                    final_media.close()
                else: # Video
                    if hasattr(final_media, 'audio') and final_media.audio:
                        final_media.audio.close()
                    if hasattr(final_media, 'mask') and final_media.mask:
                        final_media.mask.close()


    def setVolume(self, value):
        self.audioOutput.setVolume(value / 100.0)

    def setVolumeOutput(self, value):
        self.audioOutputOutput.setVolume(value / 100.0)

    def updateTimeCodeOutput(self, position):
        # Aggiorna il timecode corrente del video output
        total_seconds = position // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = position % 1000
        self.currentTimeLabelOutput.setText(f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}')

    def updateDurationOutput(self, duration):
        # Aggiorna la durata totale del video output
        total_seconds = duration // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = duration % 1000
        self.totalTimeLabelOutput.setText(f' / {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}')

    def open_crop_dialog(self):
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            self.show_status_message("Carica un video prima di ritagliarlo.", error=True)
            return

        self.player.pause()

        frame_pixmap = self.get_frame_at(self.player.position())
        if not frame_pixmap:
            QMessageBox.critical(self, "Errore", "Impossibile estrarre il frame dal video.")
            return

        dialog = CropDialog(frame_pixmap, self)
        if dialog.exec():
            crop_rect = dialog.get_crop_rect()
            self.perform_crop(crop_rect)

    def get_frame_at(self, position_ms):
        try:
            position_sec = position_ms / 1000.0
            video_clip = VideoFileClip(self.videoPathLineEdit)

            if not (0 <= position_sec <= video_clip.duration):
                return None

            frame = video_clip.get_frame(position_sec)

            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()

            pixmap = QPixmap.fromImage(q_image)
            # Scale pixmap to half size for the dialog
            return pixmap.scaled(pixmap.width() // 2, pixmap.height() // 2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        except Exception as e:
            print(f"Error getting frame at {position_ms}ms: {e}")
            return None

    def get_frame_at(self, position_ms):
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            return None
        try:
            position_sec = position_ms / 1000.0
            video_clip = VideoFileClip(self.videoPathLineEdit)

            # Ensure the position is within the video duration
            if not (0 <= position_sec <= video_clip.duration):
                video_clip.close()
                return None

            frame = video_clip.get_frame(position_sec)
            video_clip.close()

            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(q_image)

            return pixmap
        except Exception as e:
            logging.error(f"Error getting frame at {position_ms}ms: {e}")
            return None

    def get_current_fps(self):
        try:
            return VideoFileClip(self.videoPathLineEdit).fps
        except Exception as e:
            print(f"Error getting FPS: {e}")
            return 0

    def get_next_frame(self):
        fps = self.get_current_fps()
        if fps > 0:
            current_pos = self.player.position()
            new_pos = current_pos + (1000 / fps)
            self.player.setPosition(int(new_pos))

    def get_previous_frame(self):
        fps = self.get_current_fps()
        if fps > 0:
            current_pos = self.player.position()
            new_pos = current_pos - (1000 / fps)
            self.player.setPosition(int(new_pos))

    def perform_crop(self, crop_rect):
        if self.current_thread and self.current_thread.isRunning():
            self.show_status_message("Un'altra operazione è già in corso.", error=True)
            return

        self.statusLabel.setText("Ritaglio del video in corso...")
        self.progressBar.setVisible(True)
        self.cancelButton.setVisible(True)

        thread = CropThread(self.videoPathLineEdit, crop_rect, self.current_project_path, self)
        self.current_thread = thread

        thread.progress.connect(self.progressBar.setValue)
        thread.completed.connect(self.on_crop_completed)
        thread.error.connect(self.on_crop_error)

        try:
            self.cancelButton.clicked.disconnect()
        except TypeError:
            pass
        self.cancelButton.clicked.connect(self.cancel_task)

        thread.start()

    def on_crop_completed(self, output_path):
        self.progressBar.setVisible(False)
        self.cancelButton.setVisible(False)
        self.current_thread = None
        self.show_status_message(f"Video ritagliato e salvato in {os.path.basename(output_path)}")
        self.loadVideoOutput(output_path)

    def on_crop_error(self, error_message):
        self.progressBar.setVisible(False)
        self.cancelButton.setVisible(False)
        self.current_thread = None
        QMessageBox.critical(self, "Errore durante il ritaglio", error_message)

    def applyStyleToAllDocks(self):
        style = self.getDarkStyle()
        self.videoPlayerDock.setStyleSheet(style)
        self.transcriptionDock.setStyleSheet(style)
        self.editingDock.setStyleSheet(style)
        self.recordingDock.setStyleSheet(style)
        self.audioDock.setStyleSheet(style)
        self.videoPlayerOutput.setStyleSheet(style)
        self.videoEffectsDock.setStyleSheet(style)
        self.infoDock.setStyleSheet(style)
        self.videoNotesDock.setStyleSheet(style)

    def createVideoNotesDock(self):
        """Crea il dock per le note video."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.videoNotesListWidget = QListWidget()
        self.videoNotesListWidget.setToolTip("Elenco delle note del video. Doppio click per andare al timecode.")
        self.videoNotesListWidget.itemDoubleClicked.connect(self.seek_to_note_timecode)
        layout.addWidget(self.videoNotesListWidget)

        buttons_layout = QHBoxLayout()
        self.editNoteButton = QPushButton("Modifica Nota")
        self.editNoteButton.setToolTip("Modifica la nota selezionata.")
        self.editNoteButton.clicked.connect(self.edit_video_note)
        buttons_layout.addWidget(self.editNoteButton)

        self.deleteNoteButton = QPushButton("Cancella Nota")
        self.deleteNoteButton.setToolTip("Cancella la nota selezionata.")
        self.deleteNoteButton.clicked.connect(self.delete_video_note)
        buttons_layout.addWidget(self.deleteNoteButton)

        layout.addLayout(buttons_layout)
        self.videoNotesDock.addWidget(widget)

    def getDarkStyle(self):
        return """
        QWidget {
            background-color: #2b2b2b;
            color: #dcdcdc;
        }
        QPushButton {
            background-color: #555555;
            border: 1px solid #666666;
            border-radius: 2px;
            padding: 5px;
            color: #ffffff;
        }
        QPushButton:hover {
            background-color: #666666;
        }
        QPushButton:pressed {
            background-color: #777777;
        }
        QLabel {
            color: #cccccc;
        }
        QLineEdit {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 2px;
            padding: 5px;
            color: #ffffff;
        }
        """

    def setupVoiceSettingsUI(self):
        voiceSettingsGroup = QGroupBox("Impostazioni Voce")
        layout = QVBoxLayout()

        # QComboBox per la selezione della voce con opzione per inserire custom ID
        self.voiceSelectionComboBox = QComboBox()
        self.voiceSelectionComboBox.setEditable(True)
        for name, voice_id in DEFAULT_VOICES.items():
            self.voiceSelectionComboBox.addItem(name, voice_id)

        layout.addWidget(self.voiceSelectionComboBox)

        # Campo di input per ID voce
        self.voiceIdInput = QLineEdit()
        self.voiceIdInput.setPlaceholderText("ID Voce")
        layout.addWidget(self.voiceIdInput)

        # Pulsante per aggiungere la voce personalizzata
        self.addVoiceButton = QPushButton('Aggiungi Voce Personalizzata')
        self.addVoiceButton.clicked.connect(self.addCustomVoice)
        layout.addWidget(self.addVoiceButton)

        # Radio buttons per la selezione del genere vocale

        # Slider per la stabilità
        stabilityLabel = QLabel("Stabilità:")
        self.stabilitySlider = QSlider(Qt.Orientation.Horizontal)
        self.stabilitySlider.setMinimum(0)
        self.stabilitySlider.setMaximum(100)
        self.stabilitySlider.setValue(DEFAULT_STABILITY)
        self.stabilitySlider.setToolTip(
            "Regola l'emozione e la coerenza. Minore per più emozione, maggiore per coerenza.")
        self.stabilityValueLabel = QLabel("50%")  # Visualizza il valore corrente
        self.stabilitySlider.valueChanged.connect(lambda value: self.stabilityValueLabel.setText(f"{value}%"))
        layout.addWidget(stabilityLabel)
        layout.addWidget(self.stabilitySlider)
        layout.addWidget(self.stabilityValueLabel)

        # Slider per la similarità
        similarityLabel = QLabel("Similarità:")
        self.similaritySlider = QSlider(Qt.Orientation.Horizontal)
        self.similaritySlider.setMinimum(0)
        self.similaritySlider.setMaximum(100)
        self.similaritySlider.setValue(DEFAULT_SIMILARITY)
        self.similaritySlider.setToolTip(
            "Determina quanto la voce AI si avvicina all'originale. Alti valori possono includere artefatti.")
        self.similarityValueLabel = QLabel("80%")  # Visualizza il valore corrente
        self.similaritySlider.valueChanged.connect(lambda value: self.similarityValueLabel.setText(f"{value}%"))
        layout.addWidget(similarityLabel)
        layout.addWidget(self.similaritySlider)
        layout.addWidget(self.similarityValueLabel)

        # Slider per l'esagerazione dello stile
        styleLabel = QLabel("Esagerazione Stile:")
        self.styleSlider = QSlider(Qt.Orientation.Horizontal)
        self.styleSlider.setMinimum(0)
        self.styleSlider.setMaximum(10)
        self.styleSlider.setValue(DEFAULT_STYLE)
        self.styleSlider.setToolTip("Amplifica lo stile del parlante originale. Impostare a 0 per maggiore stabilità.")
        self.styleValueLabel = QLabel("0")  # Visualizza il valore corrente
        self.styleSlider.valueChanged.connect(lambda value: self.styleValueLabel.setText(f"{value}"))
        layout.addWidget(styleLabel)
        layout.addWidget(self.styleSlider)
        layout.addWidget(self.styleValueLabel)

        # Checkbox per l'uso di speaker boost
        self.speakerBoostCheckBox = QCheckBox("Usa Speaker Boost")
        self.speakerBoostCheckBox.setChecked(True)
        self.speakerBoostCheckBox.setToolTip(
            "Potenzia la somiglianza col parlante originale a costo di maggiori risorse.")
        layout.addWidget(self.speakerBoostCheckBox)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Sincronizzazione labiale
        self.useWav2LipCheckbox = QCheckBox("Sincronizzazione labiale")
        layout.addWidget(self.useWav2LipCheckbox)
        self.useWav2LipCheckbox.setVisible(False)

        # Pulsanti per le diverse funzionalità
        self.generateAudioButton = QPushButton('Genera e Applica Audio con AI')
        self.generateAudioButton.clicked.connect(self.generateAudioWithElevenLabs)

        self.alignspeed = QCheckBox("Allinea velocità video con audio")
        self.alignspeed.setChecked(True)
        layout.addWidget(self.alignspeed)
        layout.addWidget(self.generateAudioButton)

        voiceSettingsGroup.setLayout(layout)
        return voiceSettingsGroup

    def createGeneratedAudiosUI(self):
        """
        Crea il QGroupBox per la gestione degli audio generati.
        """
        generatedAudiosGroup = QGroupBox("Audio Generati per questo Video")
        layout = QVBoxLayout()

        self.generatedAudiosListWidget = QListWidget()
        self.generatedAudiosListWidget.setToolTip("Lista degli audio generati per il video corrente.")
        self.generatedAudiosListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.generatedAudiosListWidget.customContextMenuRequested.connect(self.show_audio_context_menu)
        layout.addWidget(self.generatedAudiosListWidget)

        buttons_layout = QHBoxLayout()
        applyButton = QPushButton("Applica Selezionato")
        applyButton.setToolTip("Applica l'audio selezionato al video.")
        applyButton.clicked.connect(self.apply_selected_audio)
        buttons_layout.addWidget(applyButton)

        deleteButton = QPushButton("Elimina Selezionato")
        deleteButton.setToolTip("Elimina l'audio selezionato (il file verrà cancellato).")
        deleteButton.clicked.connect(self.delete_selected_audio)
        buttons_layout.addWidget(deleteButton)

        layout.addLayout(buttons_layout)
        generatedAudiosGroup.setLayout(layout)
        return generatedAudiosGroup

    def show_audio_context_menu(self, position):
        """
        Mostra il menu contestuale per gli elementi della lista di audio generati.
        """
        item = self.generatedAudiosListWidget.itemAt(position)
        if item:
            context_menu = QMenu(self)
            preview_action = context_menu.addAction("Ascolta anteprima")
            action = context_menu.exec(self.generatedAudiosListWidget.mapToGlobal(position))

            if action == preview_action:
                self.play_preview_audio(item)

    def play_preview_audio(self, item):
        """
        Riproduce l'anteprima dell'audio selezionato.
        """
        audio_path = item.data(Qt.ItemDataRole.UserRole)
        if audio_path and os.path.exists(audio_path):
            self.previewPlayer.setSource(QUrl.fromLocalFile(audio_path))
            self.previewPlayer.play()
            self.show_status_message(f"Riproduzione anteprima: {os.path.basename(audio_path)}")
        else:
            self.show_status_message("File anteprima non trovato.", error=True)

    def addCustomVoice(self):
        custom_name = self.voiceSelectionComboBox.currentText().strip()
        voice_id = self.voiceIdInput.text().strip()
        if custom_name and voice_id:
            self.voiceSelectionComboBox.addItem(custom_name, voice_id)
            self.voiceSelectionComboBox.setCurrentText(custom_name)
            self.voiceIdInput.clear()
            self.show_status_message(f"Voce personalizzata '{custom_name}' aggiunta.")
        else:
            self.show_status_message("Entrambi i campi 'Nome Voce' e 'ID Voce' sono necessari.", error=True)


    def applyFreezeFramePause(self):
        video_path = self.videoPathLineEdit
        if not video_path or not os.path.exists(video_path):
            self.show_status_message("Carica un video prima di applicare una pausa.", error=True)
            return

        try:
            pause_duration = int(self.pauseVideoDurationLineEdit.text())
            start_time = self.player.position() / 1000.0

            video_clip = VideoFileClip(video_path)
            freeze_frame = video_clip.get_frame(start_time)
            freeze_clip = ImageClip(freeze_frame).set_duration(pause_duration).set_fps(video_clip.fps)

            original_video_part1 = video_clip.subclip(0, start_time)
            original_video_part2 = video_clip.subclip(start_time)

            final_video = concatenate_videoclips([original_video_part1, freeze_clip, original_video_part2])

            if video_clip.audio:
                final_video.audio = video_clip.audio

            output_path = self.get_temp_filepath(suffix='.mp4')
            final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

            self.show_status_message("Pausa video applicata con successo.")
            self.loadVideoOutput(output_path)
        except ValueError:
            self.show_status_message("La durata della pausa deve essere un numero intero.", error=True)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante l'applicazione della pausa: {e}")
        finally:
            if 'video_clip' in locals():
                video_clip.close()
            if 'final_video' in locals():
                if hasattr(final_video, 'audio') and final_video.audio:
                    final_video.audio.close()

    def createAudioDock(self):
        dock = CustomDock("Gestione Audio e Video", closable=True)

        # Creazione del QTabWidget
        tab_widget = QTabWidget()

        # Primo tab: Aggiungi/Pausa
        add_pause_tab = QWidget()
        add_pause_layout = QVBoxLayout(add_pause_tab)

        audioPauseGroup = self.createAudioPauseGroup()
        videoPauseGroup = self.createVideoPauseGroup()

        add_pause_layout.addWidget(audioPauseGroup)
        add_pause_layout.addWidget(videoPauseGroup)
        tab_widget.addTab(add_pause_tab, "Aggiungi/Pausa")

        # Secondo tab: Selezione Audio
        audio_selection_tab = QWidget()
        audio_selection_layout = QVBoxLayout(audio_selection_tab)

        audioReplacementGroup = self.createAudioReplacementGroup()
        backgroundAudioGroup = self.createBackgroundAudioGroup()

        audio_selection_layout.addWidget(audioReplacementGroup)
        audio_selection_layout.addWidget(backgroundAudioGroup)
        tab_widget.addTab(audio_selection_tab, "Selezione Audio")

        # Terzo tab: Unisci Video
        video_merge_tab = QWidget()
        video_merge_layout = QVBoxLayout(video_merge_tab)

        mergeGroup = QGroupBox("Opzioni di Unione Video")
        grid_layout = QGridLayout(mergeGroup)
        grid_layout.setSpacing(10)

        self.mergeVideoPathLineEdit = QLineEdit()
        self.mergeVideoPathLineEdit.setReadOnly(True)
        self.mergeVideoPathLineEdit.setPlaceholderText("Seleziona il video da aggiungere...")
        browseMergeVideoButton = QPushButton('Sfoglia...')
        browseMergeVideoButton.clicked.connect(self.browseMergeVideo)

        grid_layout.addWidget(QLabel("Video da unire:"), 0, 0)
        grid_layout.addWidget(self.mergeVideoPathLineEdit, 0, 1, 1, 2)
        grid_layout.addWidget(browseMergeVideoButton, 0, 3)

        resolution_group = QGroupBox("Gestione Risoluzione")
        resolution_layout = QVBoxLayout(resolution_group)
        self.adaptResolutionRadio = QRadioButton("Adatta le risoluzioni")
        self.adaptResolutionRadio.setChecked(True)
        self.maintainResolutionRadio = QRadioButton("Mantieni le risoluzioni originali")
        resolution_layout.addWidget(self.adaptResolutionRadio)
        resolution_layout.addWidget(self.maintainResolutionRadio)
        grid_layout.addWidget(resolution_group, 1, 0, 1, 4)

        mergeButton = QPushButton('Unisci Video')
        mergeButton.setStyleSheet("padding: 10px; font-weight: bold;")
        mergeButton.clicked.connect(self.mergeVideo)
        grid_layout.addWidget(mergeButton, 2, 0, 1, 4)

        video_merge_layout.addWidget(mergeGroup)
        video_merge_tab.setLayout(video_merge_layout)
        tab_widget.addTab(video_merge_tab, "Unisci Video")

        # Aggiunta del QTabWidget al dock
        dock.addWidget(tab_widget)

        return dock

    def createAudioReplacementGroup(self):
        audioReplacementGroup = QGroupBox("Sostituzione audio principale")
        layout = QVBoxLayout()

        # Layout orizzontale per la selezione del file
        file_layout = QHBoxLayout()
        self.audioPathLineEdit = QLineEdit()
        self.audioPathLineEdit.setReadOnly(True)
        browseAudioButton = QPushButton('Scegli Audio Principale')
        browseAudioButton.clicked.connect(self.browseAudio)
        file_layout.addWidget(self.audioPathLineEdit)
        file_layout.addWidget(browseAudioButton)
        layout.addLayout(file_layout)

        applyAudioButton = QPushButton('Applica Audio Principale')
        applyAudioButton.clicked.connect(self.handle_apply_main_audio)

        self.alignspeed_replacement = QCheckBox("Allinea velocità video con audio")
        self.alignspeed_replacement.setChecked(True)
        layout.addWidget(self.alignspeed_replacement)
        layout.addWidget(applyAudioButton)

        audioReplacementGroup.setLayout(layout)
        return audioReplacementGroup

    def createAudioPauseGroup(self):
        audioPauseGroup = QGroupBox("Aggiungi pausa")
        layout = QVBoxLayout()

        # Layout orizzontale per la durata della pausa
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Durata Pausa (s):")
        self.pauseAudioDurationLineEdit = QLineEdit()
        self.pauseAudioDurationLineEdit.setPlaceholderText("Durata Pausa (secondi)")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.pauseAudioDurationLineEdit)
        layout.addLayout(duration_layout)

        applyPauseButton = QPushButton('Applica Pausa Audio')
        applyPauseButton.clicked.connect(self.applyAudioWithPauses)
        layout.addWidget(applyPauseButton)

        audioPauseGroup.setLayout(layout)
        return audioPauseGroup

    def createVideoPauseGroup(self):
        videoPauseGroup = QGroupBox("Applica pausa video")
        layout = QVBoxLayout()

        # Layout orizzontale per la durata della pausa
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Durata Pausa (s):")
        self.pauseVideoDurationLineEdit = QLineEdit()
        self.pauseVideoDurationLineEdit.setPlaceholderText("Durata Pausa (secondi)")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.pauseVideoDurationLineEdit)
        layout.addLayout(duration_layout)

        applyVideoPauseButton = QPushButton('Applica Pausa Video')
        applyVideoPauseButton.clicked.connect(self.applyFreezeFramePause)
        layout.addWidget(applyVideoPauseButton)

        videoPauseGroup.setLayout(layout)
        return videoPauseGroup

    def createBackgroundAudioGroup(self):
        backgroundAudioGroup = QGroupBox("Gestione Audio di Sottofondo")
        layout = QVBoxLayout()

        # Layout orizzontale per la selezione del file
        file_layout = QHBoxLayout()
        self.backgroundAudioPathLineEdit = QLineEdit()
        self.backgroundAudioPathLineEdit.setReadOnly(True)
        browseBackgroundAudioButton = QPushButton('Scegli Sottofondo')
        browseBackgroundAudioButton.clicked.connect(self.browseBackgroundAudio)
        file_layout.addWidget(self.backgroundAudioPathLineEdit)
        file_layout.addWidget(browseBackgroundAudioButton)
        layout.addLayout(file_layout)

        # Layout orizzontale per il volume
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume Sottofondo:")
        self.volumeSliderBack = QSlider(Qt.Orientation.Horizontal)
        self.volumeSliderBack.setRange(0, 1000)
        self.volumeSliderBack.setValue(6)
        self.volumeLabelBack = QLabel(f"{self.volumeSliderBack.value() / 1000:.3f}")
        self.volumeSliderBack.valueChanged.connect(self.adjustBackgroundVolume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volumeSliderBack)
        volume_layout.addWidget(self.volumeLabelBack)
        layout.addLayout(volume_layout)

        self.loopBackgroundAudioCheckBox = QCheckBox("Loop Sottofondo se più corto del video")
        self.loopBackgroundAudioCheckBox.setChecked(True)
        layout.addWidget(self.loopBackgroundAudioCheckBox)

        applyBackgroundButton = QPushButton('Applica Sottofondo al Video')
        applyBackgroundButton.clicked.connect(self.applyBackgroundAudioToVideo)
        layout.addWidget(applyBackgroundButton)

        backgroundAudioGroup.setLayout(layout)
        return backgroundAudioGroup

    def adjustBackgroundVolume(self):
        slider_value = self.volumeSliderBack.value()
        normalized_volume = np.exp(slider_value / 1000 * np.log(2)) - 1
        self.volumeLabelBack.setText(f"Volume Sottofondo: {normalized_volume:.3f}")
    def setTimecodePauseFromSlider(self):
        current_position = self.player.position()
        self.timecodePauseLineEdit.setText(self.formatTimecode(current_position))
    def setTimecodeVideoFromSlider(self):
        current_position = self.player.position()
        self.timecodeVideoPauseLineEdit.setText(self.formatTimecode(current_position))

    def createVideoEffectsDock(self):
        """Crea e restituisce il dock per gli effetti video (PiP e Overlay)."""
        dock = CustomDock("Effetti Video", closable=True)

        tab_widget = QTabWidget()

        # --- Tab Picture-in-Picture (PiP) ---
        pip_tab = QWidget()
        pip_layout = QVBoxLayout(pip_tab)
        pip_group = QGroupBox("Aggiungi Video Picture-in-Picture (PiP)")
        pip_group_layout = QVBoxLayout(pip_group)

        # File selection
        pip_file_layout = QHBoxLayout()
        self.pipVideoPathLineEdit = QLineEdit()
        self.pipVideoPathLineEdit.setReadOnly(True)
        self.pipVideoPathLineEdit.setPlaceholderText("Seleziona il video per il PiP...")
        browsePipVideoButton = QPushButton("Sfoglia...")
        browsePipVideoButton.clicked.connect(self.browsePipVideo)
        pip_file_layout.addWidget(self.pipVideoPathLineEdit)
        pip_file_layout.addWidget(browsePipVideoButton)
        pip_group_layout.addLayout(pip_file_layout)

        # Position and Size
        pip_options_layout = QHBoxLayout()
        pip_group_layout.addWidget(QLabel("Posizione e Dimensione:"))
        self.pipPositionComboBox = QComboBox()
        self.pipPositionComboBox.addItems(["Top Right", "Top Left", "Bottom Right", "Bottom Left", "Center"])
        pip_options_layout.addWidget(self.pipPositionComboBox)

        self.pipSizeSpinBox = QSpinBox()
        self.pipSizeSpinBox.setRange(5, 75)
        self.pipSizeSpinBox.setValue(25)
        self.pipSizeSpinBox.setSuffix("%")
        pip_options_layout.addWidget(self.pipSizeSpinBox)
        pip_group_layout.addLayout(pip_options_layout)

        applyPipButton = QPushButton("Applica Effetto PiP")
        applyPipButton.clicked.connect(self.apply_pip_effect)
        pip_group_layout.addWidget(applyPipButton)

        pip_layout.addWidget(pip_group)
        pip_layout.addStretch()
        tab_widget.addTab(pip_tab, "Video PiP")

        # --- Tab Image Overlay ---
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        image_group = QGroupBox("Aggiungi Immagine in Sovraimpressione")
        image_group_layout = QVBoxLayout(image_group)

        # File selection
        image_file_layout = QHBoxLayout()
        self.imageOverlayPathLineEdit = QLineEdit()
        self.imageOverlayPathLineEdit.setReadOnly(True)
        self.imageOverlayPathLineEdit.setPlaceholderText("Seleziona l'immagine da sovrapporre...")
        browseImageOverlayButton = QPushButton("Sfoglia...")
        browseImageOverlayButton.clicked.connect(self.browseImageOverlay)
        image_file_layout.addWidget(self.imageOverlayPathLineEdit)
        image_file_layout.addWidget(browseImageOverlayButton)
        image_group_layout.addLayout(image_file_layout)

        # Position and Size
        image_options_layout = QHBoxLayout()
        image_group_layout.addWidget(QLabel("Posizione e Dimensione:"))
        self.imagePositionComboBox = QComboBox()
        self.imagePositionComboBox.addItems(["Top Right", "Top Left", "Bottom Right", "Bottom Left", "Center"])
        image_options_layout.addWidget(self.imagePositionComboBox)

        self.imageSizeSpinBox = QSpinBox()
        self.imageSizeSpinBox.setRange(5, 100)
        self.imageSizeSpinBox.setValue(20)
        self.imageSizeSpinBox.setSuffix("%")
        image_options_layout.addWidget(self.imageSizeSpinBox)
        image_group_layout.addLayout(image_options_layout)

        applyImageButton = QPushButton("Applica Immagine Overlay")
        applyImageButton.clicked.connect(self.apply_image_overlay_effect)
        image_group_layout.addWidget(applyImageButton)

        image_layout.addWidget(image_group)
        image_layout.addStretch()
        tab_widget.addTab(image_tab, "Immagine Overlay")

        dock.addWidget(tab_widget)
        return dock

    def browsePipVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video per PiP", "", "Video Files (*.mp4 *.mov *.avi)")
        if fileName:
            self.pipVideoPathLineEdit.setText(fileName)

    def browseImageOverlay(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Immagine Overlay", "", "Image Files (*.png *.jpg *.jpeg)")
        if fileName:
            self.imageOverlayPathLineEdit.setText(fileName)

    def apply_pip_effect(self):
        base_video_path = self.videoPathLineEdit
        overlay_video_path = self.pipVideoPathLineEdit.text()

        if not base_video_path or not os.path.exists(base_video_path):
            self.show_status_message("Carica un video nel player di input prima di applicare un effetto.", error=True)
            return
        if not overlay_video_path or not os.path.exists(overlay_video_path):
            self.show_status_message("Seleziona un video per l'effetto Picture-in-Picture.", error=True)
            return

        position = self.pipPositionComboBox.currentText()
        size = self.pipSizeSpinBox.value()
        start_time = self.player.position() / 1000.0

        self.run_compositing_thread('video', base_video_path, overlay_video_path, position, size, start_time)

    def apply_image_overlay_effect(self):
        base_video_path = self.videoPathLineEdit
        overlay_image_path = self.imageOverlayPathLineEdit.text()

        if not base_video_path or not os.path.exists(base_video_path):
            self.show_status_message("Carica un video nel player di input prima di applicare un effetto.", error=True)
            return
        if not overlay_image_path or not os.path.exists(overlay_image_path):
            self.show_status_message("Seleziona un'immagine per l'effetto overlay.", error=True)
            return

        position = self.imagePositionComboBox.currentText()
        size = self.imageSizeSpinBox.value()
        start_time = self.player.position() / 1000.0

        self.run_compositing_thread('image', base_video_path, overlay_image_path, position, size, start_time)

    def run_compositing_thread(self, overlay_type, base_path, overlay_path, position, size, start_time):
        thread = VideoCompositingThread(
            base_video_path=base_path,
            overlay_path=overlay_path,
            overlay_type=overlay_type,
            position=position,
            size=size,
            start_time=start_time,
            parent=self
        )
        self.start_task(thread, self.on_compositing_completed, self.on_compositing_error, self.update_status_progress)

    def on_compositing_completed(self, output_path):
        self.show_status_message(f"Effetto video applicato con successo. File salvato.")
        self.loadVideoOutput(output_path)

    def on_compositing_error(self, error_message):
        self.show_status_message(f"Errore durante l'applicazione dell'effetto: {error_message}", error=True)

    def formatTimecode(self, position_ms):
        hours, remainder = divmod(position_ms // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def mergeVideo(self):
        base_video_path = self.videoPathLineEdit
        merge_video_path = self.mergeVideoPathLineEdit.text()

        if not base_video_path or not os.path.exists(base_video_path):
            self.show_status_message("Carica il video principale prima di unirne un altro.", error=True)
            return
        if not merge_video_path or not os.path.exists(merge_video_path):
            self.show_status_message("Seleziona un video da unire.", error=True)
            return

        position_ms = self.player.position()
        timecode = self.formatTimecode(position_ms)

        thread = VideoMergeThread(
            base_path=base_video_path,
            merge_path=merge_video_path,
            timecode_str=timecode,
            adapt_resolution=self.adaptResolutionRadio.isChecked(),
            parent=self
        )
        self.start_task(thread, self.onMergeCompleted, self.onMergeError, self.update_status_progress)

    def onMergeCompleted(self, output_path):
        self.show_status_message(f"Video unito e salvato in {os.path.basename(output_path)}")
        self.loadVideoOutput(output_path)

    def onMergeError(self, error_message):
        self.show_status_message(f"Si è verificato un errore durante l'unione: {error_message}", error=True)

    def browseMergeVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video da Unire", "",
                                                  "Video Files (*.mp4 *.mov *.avi)")
        if fileName:
            self.mergeVideoPathLineEdit.setText(fileName)

    def browseBackgroundAudio(self):
        default_dir = MUSIC_DIR
        if not os.path.exists(default_dir):
            self.show_status_message("La cartella di default per la musica non esiste.", error=True)
            default_dir = "" # Fallback to default directory

        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio di Sottofondo", default_dir, "Audio Files (*.mp3 *.wav)")
        if fileName:
            self.backgroundAudioPathLineEdit.setText(fileName)
            self.show_status_message(f"Selezionato audio di sottofondo: {os.path.basename(fileName)}")

    def setupDockSettingsManager(self):
        settings_file = './dock_settings.json'
        if os.path.exists(settings_file):
            self.dockSettingsManager.load_settings(settings_file)
        else:
            self.set_default_dock_layout()
        self.resetViewMenu()

    def closeEvent(self, event):
        # Salva tutte le modifiche correnti prima di chiudere
        self.save_all_tabs_to_json(show_message=False)

        self.dockSettingsManager.save_settings()
        if hasattr(self, 'monitor_preview') and self.monitor_preview:
            self.monitor_preview.close()

        # Pulizia dei file temporanei
        logging.info("Pulizia dei file temporanei...")
        for segment_path in self.recording_segments:
            try:
                if os.path.exists(segment_path):
                    os.remove(segment_path)
                    logging.info(f"Rimosso file temporaneo: {segment_path}")
            except Exception as e:
                logging.error(f"Impossibile rimuovere il file temporaneo {segment_path}: {e}")

        try:
            segments_file = "segments.txt"
            if os.path.exists(segments_file):
                os.remove(segments_file)
                logging.info(f"Rimosso file: {segments_file}")
        except Exception as e:
            logging.error(f"Impossibile rimuovere il file {segments_file}: {e}")

        event.accept()

    def selectDefaultScreen(self):
        if self.screen_buttons:
            self.selectScreen(0)

    def selectScreen(self, screen_index):
        if self.is_recording:
            if screen_index != self.selected_screen_index:
                if hasattr(self, 'recorder_thread') and self.recorder_thread is not None:
                    self.recorder_thread.stop()
                    self.recorder_thread.wait()
                self.selected_screen_index = screen_index
                for i, button in enumerate(self.screen_buttons):
                    button.set_selected(i == screen_index)
                self._startRecordingSegment()
        else:
            self.selected_screen_index = screen_index
            for i, button in enumerate(self.screen_buttons):
                button.set_selected(i == screen_index)
            if hasattr(self, 'monitor_preview') and self.monitor_preview:
                self.monitor_preview.close()
            monitors = get_monitors()
            if screen_index < len(monitors):
                monitor = monitors[screen_index]
                self.monitor_preview = MonitorPreview(monitor)
                self.monitor_preview.show()
                self.selectedMonitorLabel.setText(f"Monitor: Schermo {screen_index + 1} ({monitor.width}x{monitor.height})")


    def browseFolderLocation(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella")
        if folder:
            self.folderPathLineEdit.setText(folder)
    def openFolder(self):
        folder_path = self.folderPathLineEdit.text() or "screenrecorder"
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def setDefaultAudioDevice(self):
        """Imposta il primo dispositivo audio come predefinito se disponibile."""
        if self.audio_buttons:
            self.audio_buttons[0].setChecked(True)

    def applyBackgroundAudioToVideo(self):
        video_path = self.videoPathLineEdit
        background_audio_path = self.backgroundAudioPathLineEdit.text()
        slider_value = self.volumeSliderBack.value()
        background_volume = np.exp(slider_value / 1000 * np.log(2)) - 1

        if not video_path or not os.path.exists(video_path):
            self.show_status_message("Carica un video prima di applicare l'audio di sottofondo.", error=True)
            return
        if not background_audio_path or not os.path.exists(background_audio_path):
            self.show_status_message("Seleziona un file audio di sottofondo valido.", error=True)
            return

        thread = BackgroundAudioThread(
            video_path=video_path,
            audio_path=background_audio_path,
            volume=background_volume,
            loop_audio=self.loopBackgroundAudioCheckBox.isChecked(),
            parent=self
        )
        self.start_task(thread, self.onBackgroundAudioCompleted, self.onBackgroundAudioError, self.update_status_progress)

    def onBackgroundAudioCompleted(self, output_path):
        self.show_status_message("Audio di sottofondo applicato con successo.")
        self.loadVideoOutput(output_path)

    def onBackgroundAudioError(self, error_message):
        self.show_status_message(f"Errore durante l'applicazione dell'audio di sottofondo: {error_message}", error=True)

    def applyAudioWithPauses(self):
        video_path = self.videoPathLineEdit
        pause_duration_str = self.pauseAudioDurationLineEdit.text()

        if not video_path or not os.path.exists(video_path):
            self.show_status_message("Carica un video prima di applicare una pausa audio.", error=True)
            return

        if not pause_duration_str:
            self.show_status_message("Inserisci una durata per la pausa.", error=True)
            return

        try:
            pause_duration = float(pause_duration_str)
            start_time = self.player.position() / 1000.0

            video_clip = VideoFileClip(video_path)

            # Create a silent audio clip for the pause
            pause_audio = AudioSegment.silent(duration=pause_duration * 1000)
            temp_pause_path = self.get_temp_filepath(suffix=".mp3")
            pause_audio.export(temp_pause_path, format="mp3")
            pause_clip = AudioFileClip(temp_pause_path)

            # Concatenate audio clips
            original_audio = video_clip.audio
            part1 = original_audio.subclip(0, start_time)
            part2 = original_audio.subclip(start_time)
            final_audio = concatenate_audioclips([part1, pause_clip, part2])

            # Set the new audio to the video
            video_clip.audio = final_audio

            # Save the result
            output_path = self.get_temp_filepath(suffix=".mp4")
            video_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')

            self.loadVideoOutput(output_path)
            self.show_status_message("Pausa audio applicata con successo.")

        except ValueError:
            self.show_status_message("La durata della pausa non è un numero valido.", error=True)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante l'applicazione della pausa audio: {e}")
        finally:
            if 'video_clip' in locals():
                video_clip.close()
            if 'pause_clip' in locals():
                pause_clip.close()
            if 'final_audio' in locals():
                final_audio.close()
            if 'temp_pause_path' in locals() and os.path.exists(temp_pause_path):
                os.remove(temp_pause_path)

    def updateTimecodeRec(self):
        if self.recordingTime is not None:
            self.recordingTime = self.recordingTime.addSecs(1)
            self.timecodeLabel.setText(self.recordingTime.toString("hh:mm:ss"))


    def selectAudioDevice(self):
        selected_audio = None
        device_index = None
        for index, button in enumerate(self.audio_buttons):
            if button.isChecked():
                selected_audio = button.text()
                device_index = index
                break
        self.audio_input = selected_audio  # Update the audio input name
        if selected_audio:
            self.selectedAudioLabel.setText(f"Audio: {selected_audio}")
            if device_index is not None and self.test_audio_device(device_index):
                self.audioTestResultLabel.setText(f"Test Audio: Periferica OK")
            else:
                self.audioTestResultLabel.setText(f"Test Audio: Periferica KO")
        else:
            self.selectedAudioLabel.setText("Audio: N/A")

    def test_audio_device(self, device_index):
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, input_device_index=device_index)
            data = stream.read(1024)
            stream.close()
            if np.frombuffer(data, dtype=np.int16).any():
                return True
            return False
        except Exception as e:
            return False
        finally:
            p.terminate()

    def print_audio_devices(self):
        p = pyaudio.PyAudio()
        num_devices = p.get_device_count()

        # 1. Get all potential device names
        potential_devices = []
        for i in range(num_devices):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0 and self.test_audio_device(i):
                try:
                    device_name = device_info.get('name').decode('utf-8')
                except (UnicodeDecodeError, AttributeError):
                    device_name = device_info.get('name')

                is_standard_device = 'microphone' in device_name.lower() or 'stereo mix' in device_name.lower()
                is_vb_cable = ('cable' in device_name.lower() or 'voicemeeter' in device_name.lower()) and self.use_vb_cable

                if is_standard_device or is_vb_cable:
                    potential_devices.append(device_name)

        # 2. Filter out shorter, partial names (likely truncated)
        filtered_devices = []
        for name in potential_devices:
            is_partial = False
            for other_name in potential_devices:
                if name != other_name and name in other_name:
                    is_partial = True
                    break
            if not is_partial:
                filtered_devices.append(name)

        # 3. Remove exact duplicates and return
        p.terminate()
        return list(dict.fromkeys(filtered_devices)) # dict.fromkeys preserves order and removes duplicates

    def update_audio_device_list(self):
        """Clears and rebuilds the audio device list in the UI based on current settings."""
        if self.audio_device_layout is None:
            logging.warning("audio_device_layout is not initialized.")
            return

        # Clear existing widgets from the checkbox layout
        while self.audio_device_layout.count():
            child = self.audio_device_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Re-populate the checkbox layout
        self.audio_buttons = []
        audio_devices = self.print_audio_devices()
        if audio_devices:
            for device in audio_devices:
                check_box = QCheckBox(device)
                self.audio_device_layout.addWidget(check_box)
                self.audio_buttons.append(check_box)
        else:
            logging.debug("No input audio devices found.")
            no_device_label = QLabel("Nessun dispositivo audio trovato.")
            self.audio_device_layout.addWidget(no_device_label)

        self.setDefaultAudioDevice()

    def createRecordingDock(self):
        dock =CustomDock("Registrazione", closable=True)
        self.rec_timer = QTimer()
        self.rec_timer.timeout.connect(self.updateTimecodeRec)

        # Group Box for Info
        infoGroup = QGroupBox("Info")
        infoLayout = QGridLayout(infoGroup) # Changed to QGridLayout

        self.timecodeLabel = QLabel('00:00:00')
        self.timecodeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timecodeLabel.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
                font-size: 28pt;
                font-weight: bold;
                color: #00FF00;
                background-color: #000000;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        infoLayout.addWidget(self.timecodeLabel, 0, 0, 1, 2) # Span 2 columns

        # --- Static Info Labels ---
        self.recordingStatusLabel = QLabel("Stato: Pronto")
        infoLayout.addWidget(self.recordingStatusLabel, 1, 0, 1, 2)

        self.selectedMonitorLabel = QLabel("Monitor: N/A")
        infoLayout.addWidget(self.selectedMonitorLabel, 2, 0, 1, 2)

        self.outputFileLabel = QLabel("File: N/A")
        infoLayout.addWidget(self.outputFileLabel, 3, 0, 1, 2)

        # --- Dynamic Stats Labels (in a new row) ---
        self.fpsLabel = QLabel("FPS: N/A")
        infoLayout.addWidget(self.fpsLabel, 4, 0)

        self.fileSizeLabel = QLabel("Dimensione: N/A")
        infoLayout.addWidget(self.fileSizeLabel, 4, 1)

        self.bitrateLabel = QLabel("Bitrate: N/A")
        infoLayout.addWidget(self.bitrateLabel, 5, 0)

        self.audioTestResultLabel = QLabel("Test Audio: N/A")
        infoLayout.addWidget(self.audioTestResultLabel, 5, 1)

        # Apply a consistent style to info labels
        label_style = "font-size: 9pt; color: #cccccc;"
        self.recordingStatusLabel.setStyleSheet(label_style)
        self.selectedMonitorLabel.setStyleSheet(label_style)
        self.outputFileLabel.setStyleSheet(label_style)
        self.fpsLabel.setStyleSheet(label_style)
        self.fileSizeLabel.setStyleSheet(label_style)
        self.bitrateLabel.setStyleSheet(label_style)
        self.audioTestResultLabel.setStyleSheet(label_style)

        # Main Layout for Recording Management
        recordingLayout = QVBoxLayout()

        # Screen selection grid
        screensGroupBox = QGroupBox("Seleziona Schermo")
        screensLayout = QGridLayout(screensGroupBox)

        self.screen_buttons = []
        monitors = get_monitors()
        for i, monitor in enumerate(monitors):
            resolution = f"{monitor.width}x{monitor.height}"
            screen_button = ScreenButton(
                screen_number=i + 1,
                resolution=resolution,
                is_primary=monitor.is_primary
            )
            screen_button.clicked.connect(self.selectScreen)
            screensLayout.addWidget(screen_button, i // 3, i % 3)
            self.screen_buttons.append(screen_button)

        recordingLayout.addWidget(screensGroupBox)

        # Audio selection group box
        audioGroupBox = QGroupBox("Seleziona Audio")
        mainAudioLayout = QVBoxLayout(audioGroupBox)
        mainAudioLayout.addWidget(self.audioTestResultLabel)

        # Container for checkboxes
        self.audio_checkbox_container = QWidget()
        self.audio_device_layout = QVBoxLayout(self.audio_checkbox_container)
        mainAudioLayout.addWidget(self.audio_checkbox_container)

        self.update_audio_device_list()
        recordingLayout.addWidget(audioGroupBox)

        saveOptionsGroup = QGroupBox("Opzioni di Salvataggio")
        saveOptionsLayout = QVBoxLayout(saveOptionsGroup)

        self.folderPathLineEdit = QLineEdit()
        self.folderPathLineEdit.setPlaceholderText("Inserisci il percorso della cartella di destinazione")

        self.saveVideoOnlyCheckBox = QCheckBox("Registra solo video")
        self.saveAudioOnlyCheckBox = QCheckBox("Registra solo audio")

        self.saveVideoOnlyCheckBox.toggled.connect(
            lambda checked: self.saveAudioOnlyCheckBox.setEnabled(not checked)
        )
        self.saveAudioOnlyCheckBox.toggled.connect(
            lambda checked: self.saveVideoOnlyCheckBox.setEnabled(not checked)
        )

        saveOptionsLayout.addWidget(self.saveVideoOnlyCheckBox)
        saveOptionsLayout.addWidget(self.saveAudioOnlyCheckBox)
        saveOptionsLayout.addWidget(QLabel("Percorso File:"))

        saveOptionsLayout.addWidget(self.folderPathLineEdit)

        buttonsLayout = QHBoxLayout()
        browseButton = QPushButton('Sfoglia')
        browseButton.clicked.connect(self.browseFolderLocation)
        buttonsLayout.addWidget(browseButton)

        open_folder_button = QPushButton('Apri Cartella')
        open_folder_button.clicked.connect(self.openFolder)
        buttonsLayout.addWidget(open_folder_button)

        self.recordingNameLineEdit = QLineEdit()
        self.recordingNameLineEdit.setPlaceholderText("Inserisci il nome della registrazione")
        saveOptionsLayout.addLayout(buttonsLayout)

        saveOptionsLayout.addWidget(QLabel("Nome della Registrazione:"))
        saveOptionsLayout.addWidget(self.recordingNameLineEdit)

        recordingLayout.addWidget(saveOptionsGroup)

        # Aggiungi la checkbox per abilitare la registrazione automatica delle chiamate di Teams
        self.autoRecordTeamsCheckBox = QCheckBox("Abilita registrazione automatica per Teams")
        # recordingLayout.addWidget(self.autoRecordTeamsCheckBox)

        self.startRecordingButton = QPushButton("")
        self.startRecordingButton.setIcon(QIcon(get_resource("rec.png")))
        self.startRecordingButton.setToolTip("Inizia la registrazione")

        self.stopRecordingButton = QPushButton("")
        self.stopRecordingButton.setIcon(QIcon(get_resource("stop.png")))
        self.stopRecordingButton.setToolTip("Ferma la registrazione")

        self.pauseRecordingButton = QPushButton("")
        self.pauseRecordingButton.setIcon(QIcon(get_resource("pausa_play.png")))
        self.pauseRecordingButton.setToolTip("Pausa/Riprendi la registrazione")
        self.pauseRecordingButton.setEnabled(False)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.startRecordingButton)
        buttonLayout.addWidget(self.stopRecordingButton)
        buttonLayout.addWidget(self.pauseRecordingButton)

        self.startRecordingButton.clicked.connect(self.startScreenRecording)
        self.stopRecordingButton.clicked.connect(self.stopScreenRecording)
        self.pauseRecordingButton.clicked.connect(self.togglePauseResumeRecording)

        recordingLayout.addLayout(buttonLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infoGroup)
        mainLayout.addLayout(recordingLayout)

        widget = QWidget()
        widget.setLayout(mainLayout)

        dock.addWidget(widget)

        self.selectDefaultScreen()
        return dock

    def startScreenRecording(self):
        if self.show_red_dot:
            self.cursor_overlay.show()
        self.is_recording = True
        self.indicator_timer.start(500)  # Blink every 500ms

        self.startRecordingButton.setEnabled(False)
        self.pauseRecordingButton.setEnabled(True)
        self.stopRecordingButton.setEnabled(True)
        self.recording_segments.clear()  # Pulisce i segmenti precedenti
        self.is_paused = False

        self.recordingTime = QTime(0, 0, 0)
        self.rec_timer.start(1000)
        self._startRecordingSegment()

    def _startRecordingSegment(self):
        if hasattr(self, 'monitor_preview') and self.monitor_preview:
            self.monitor_preview.close()
            self.monitor_preview = None

        selected_audio_devices = []
        for button in self.audio_buttons:
            if button.isChecked():
                selected_audio_devices.append(button.text())

        folder_path = self.folderPathLineEdit.text().strip()
        save_video_only = self.saveVideoOnlyCheckBox.isChecked()
        save_audio_only = self.saveAudioOnlyCheckBox.isChecked()
        self.timecodeLabel.setStyleSheet("""
            QLabel {
                font-family: "Courier New", Courier, monospace;
                font-size: 24pt;
                font-weight: bold;
                color: red;
                background-color: #000000;
                border: 2px solid #880000;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        monitor_index = self.selected_screen_index if self.selected_screen_index is not None else 0

        recording_name = self.recordingNameLineEdit.text().strip()
        if not recording_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            recording_name = f"recording_{timestamp}"

        # --- MODIFICA PER INTEGRAZIONE PROGETTO ---
        # Se un progetto è attivo, salva le clip nella sua cartella 'clips'
        if self.current_project_path:
            output_folder = os.path.join(self.current_project_path, "clips")
        else:
            # Altrimenti, usa la cartella specificata o quella di default
            if folder_path:
                output_folder = folder_path
            else:
                output_folder = os.path.join(os.getcwd(), 'screenrecorder')

        os.makedirs(output_folder, exist_ok=True)
        # --- FINE MODIFICA ---

        file_extension = ".mp3" if save_audio_only else ".mp4"
        segment_file_path = os.path.join(output_folder, f"{recording_name}{file_extension}")

        # BUG: The original code used an undefined 'default_folder' variable.
        # This has been corrected to use 'output_folder'.
        while os.path.exists(segment_file_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            segment_file_path = os.path.join(output_folder, f"{recording_name}_{timestamp}{file_extension}")

        ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'
        if not os.path.exists(ffmpeg_path):
            QMessageBox.critical(self, "Errore",
                                 "L'eseguibile ffmpeg.exe non è stato trovato. Assicurati che sia presente nella directory.")
            self.startRecordingButton.setEnabled(True)
            return

        if not save_video_only and not selected_audio_devices:
            QMessageBox.critical(self, "Errore",
                                 "Nessun dispositivo audio selezionato. Seleziona un dispositivo audio o abilita l'opzione 'Salva solo il video'.")
            self.startRecordingButton.setEnabled(True)
            return

        bluetooth_mode = self._is_bluetooth_mode_active()

        self.recorder_thread = ScreenRecorder(
            output_path=segment_file_path,
            ffmpeg_path=ffmpeg_path,
            monitor_index=monitor_index,
            audio_inputs=selected_audio_devices if not save_video_only else [],
            record_video=not save_audio_only,
            audio_channels=DEFAULT_AUDIO_CHANNELS if not save_video_only else 0,
            frames=DEFAULT_FRAME_RATE,
            use_watermark=self.enableWatermark,
            watermark_path=self.watermarkPath,
            watermark_size=self.watermarkSize,
            watermark_position=self.watermarkPosition,
            bluetooth_mode=bluetooth_mode,
            audio_volume=4.0
        )

        self.recorder_thread.error_signal.connect(self.showError)
        self.recorder_thread.stats_updated.connect(self.updateRecordingStats)
        self.recorder_thread.start()

        self.recording_segments.append(segment_file_path)
        self.current_video_path = segment_file_path
        self.outputFileLabel.setText(f"File: {segment_file_path}")
        self.recordingStatusLabel.setText(f'Stato: Registrazione iniziata di Schermo {monitor_index + 1}')

    def togglePauseResumeRecording(self):
        if self.is_paused:
            self.resumeScreenRecording()
        else:
            self.pauseScreenRecording()

    def pauseScreenRecording(self):
        if hasattr(self, 'recorder_thread') and self.recorder_thread is not None:
            self.recorder_thread.stop()
            self.recorder_thread.wait()  # Ensure the thread has finished
            self.rec_timer.stop()
            self.recordingStatusLabel.setText('Stato: Registrazione in pausa')
            self.is_paused = True

    def resumeScreenRecording(self):
        self._startRecordingSegment()
        self.rec_timer.start(1000)
        self.recordingStatusLabel.setText('Stato: Registrazione ripresa')

        self.is_paused = False

    def stopScreenRecording(self):
        if self.cursor_overlay.isVisible():
            self.cursor_overlay.hide()
        self.is_recording = False
        self.indicator_timer.stop()
        self.recording_indicator.setVisible(False)

        self.pauseRecordingButton.setEnabled(False)
        self.startRecordingButton.setEnabled(True)
        self.pauseRecordingButton.setEnabled(False)
        self.stopRecordingButton.setEnabled(False)
        self.rec_timer.stop()
        if hasattr(self, 'recorder_thread') and self.recorder_thread is not None:
            self.timecodeLabel.setStyleSheet("""
                QLabel {
                    font-family: "Courier New", Courier, monospace;
                    font-size: 24pt;
                    font-weight: bold;
                    color: #00FF00;
                    background-color: #000000;
                    border: 2px solid #444444;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            self.recorder_thread.stop()
            self.recorder_thread.wait()  # Ensure the thread has finished

        if hasattr(self, 'current_video_path'):
            self._mergeSegments()

        if hasattr(self, 'monitor_preview') and self.monitor_preview:
            self.monitor_preview.close()
            self.monitor_preview = None

        self.recordingStatusLabel.setText("Stato: Registrazione Terminata e video salvato.")
        self.timecodeLabel.setText('00:00:00')
        self.outputFileLabel.setText("File: N/A")
        self.fpsLabel.setText("FPS: N/A")
        self.fileSizeLabel.setText("Dimensione: N/A")
        self.bitrateLabel.setText("Bitrate: N/A")

    import datetime

    def _mergeSegments(self):
        if not self.recording_segments:
            return

        first_segment = self.recording_segments[0]
        output_path = ""

        if len(self.recording_segments) > 1:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            base_name = os.path.splitext(os.path.basename(first_segment))[0]
            if '_' in base_name:
                base_name = base_name.rsplit('_', 1)[0]

            output_dir = os.path.dirname(first_segment)
            file_extension = os.path.splitext(first_segment)[1]
            output_path = os.path.join(output_dir, f"{base_name}_final_{timestamp}{file_extension}")

            ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'

            if self.current_project_path:
                temp_dir = os.path.join(self.current_project_path, "temp")
                os.makedirs(temp_dir, exist_ok=True)
                segments_file = os.path.join(temp_dir, "segments.txt")
            else:
                segments_file = "segments.txt"

            try:
                with open(segments_file, "w") as file:
                    for segment in self.recording_segments:
                        file.write(f"file '{os.path.abspath(segment)}'\n")

                merge_command = [ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', segments_file, '-c', 'copy', output_path]
                subprocess.run(merge_command, check=True)

                # Pulizia dei segmenti temporanei
                for segment in self.recording_segments:
                    if os.path.exists(segment):
                        os.remove(segment)
            finally:
                if os.path.exists(segments_file):
                    os.remove(segments_file)
        else:
            output_path = self.recording_segments[0]

        if not output_path or not os.path.exists(output_path):
            self.show_status_message("Errore nel salvataggio della registrazione.", error=True)
            return

        self.show_status_message(f"Registrazione salvata: {os.path.basename(output_path)}")
        self.loadVideoOutput(output_path)

        # --- INTEGRAZIONE PROGETTO ---
        if self.current_project_path and self.projectDock.gnai_path:
            clip_filename = os.path.basename(output_path)
            metadata_filename = os.path.splitext(clip_filename)[0] + ".json"

            # Raccogli i metadati aggiuntivi
            try:
                clip_info = VideoFileClip(output_path)
                duration = clip_info.duration
                clip_info.close()
                size = os.path.getsize(output_path)
                creation_date = datetime.datetime.fromtimestamp(os.path.getctime(output_path)).isoformat()
            except Exception as e:
                logging.error(f"Impossibile estrarre i metadati per {output_path}: {e}")
                duration, size, creation_date = 0, 0, datetime.datetime.now().isoformat()

            self.project_manager.add_clip_to_project(
                self.projectDock.gnai_path,
                clip_filename,
                metadata_filename,
                duration,
                size,
                creation_date
            )

            # Ricarica i dati del progetto per aggiornare la UI
            self.load_project(self.projectDock.gnai_path)
            self.show_status_message(f"Clip '{clip_filename}' aggiunta al progetto.")

    def _is_bluetooth_mode_active(self):
        """Checks if any of the selected audio devices is a Bluetooth headset."""
        bluetooth_keywords = ['headset', 'hands-free', 'cuffie', 'bluetooth', 'cable', 'vb-audio']

        selected_audio_devices = []
        for button in self.audio_buttons:
            if button.isChecked():
                selected_audio_devices.append(button.text())

        for device in selected_audio_devices:
            if any(keyword in device.lower() for keyword in bluetooth_keywords):
                return True

        return False

    def showError(self, message):
        logging.error("Error recording thread:",message)
        #QMessageBox.critical(self, "Errore", message)

    def updateRecordingStats(self, stats):
        """Aggiorna le etichette delle statistiche di registrazione."""
        self.fpsLabel.setText(f"FPS: {stats.get('fps', 'N/A')}")

        # Format file size
        size_kb = float(stats.get('size', 0))
        if size_kb > 1024:
            size_mb = size_kb / 1024
            self.fileSizeLabel.setText(f"Dimensione: {size_mb:.2f} MB")
        else:
            self.fileSizeLabel.setText(f"Dimensione: {size_kb} KB")

        self.bitrateLabel.setText(f"Bitrate: {stats.get('bitrate', 'N/A')} kbit/s")

    def saveText(self):
        path, selected_filter = QFileDialog.getSaveFileName(self, "Salva file", "", "JSON files (*.json);;Text files (*.txt)")
        if not path:
            return

        try:
            file_ext = os.path.splitext(path)[1].lower()

            if "(*.txt)" in selected_filter or file_ext == ".txt":
                if file_ext != ".txt": path += ".txt"

                # Salva il contenuto della scheda attualmente attiva
                current_tab_index = self.transcriptionTabWidget.currentIndex()
                if current_tab_index == 0: # Scheda Trascrizione
                    text_to_save = self.transcriptionTextArea.toPlainText()
                else: # Scheda Riassunto
                    text_to_save = self.summaryTextArea.toPlainText()

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text_to_save)
                logging.info(f"File di testo salvato: {path}")

            else: # Default a JSON
                if file_ext != ".json": path += ".json"

                metadata = {
                    "transcription_original": self.transcription_original,
                    "transcription_corrected": self.transcription_corrected,
                    "riassunto_generato": self.summaryTextArea.toPlainText(),
                    "transcription_date": datetime.datetime.now().isoformat(),
                    "language": self.languageComboBox.currentData()
                }

                if self.videoPathLineEdit and os.path.exists(self.videoPathLineEdit):
                    try:
                        video_clip = VideoFileClip(self.videoPathLineEdit)
                        metadata["video_path"] = self.videoPathLineEdit
                        metadata["duration"] = video_clip.duration
                    except Exception as e:
                        logging.warning(f"Impossibile leggere i metadati del video: {e}")

                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
                logging.info(f"File JSON salvato: {path}")

        except Exception as e:
            logging.error(f"Errore durante il salvataggio del file: {e}")
            QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare il file:\n{e}")

    def exportSummaryToWord(self):
        """
        Esporta il contenuto del riassunto (con formattazione) in un documento Word.
        """
        summary_html = self.summaryTextArea.toHtml()
        if not self.summaryTextArea.document().toPlainText().strip():
            self.show_status_message("Il riassunto è vuoto. Non c'è nulla da esportare.", error=True)
            return

        path, _ = QFileDialog.getSaveFileName(self, "Esporta Riassunto", "", "Word Document (*.docx)")
        if not path:
            return

        if not path.endswith('.docx'):
            path += '.docx'

        try:
            document = docx.Document()
            soup = BeautifulSoup(summary_html, 'html.parser')

            for element in soup.body.contents:
                if element.name == 'p':
                    p = document.add_paragraph()
                    self._add_html_to_doc(element, p)

            document.save(path)
            self.show_status_message(f"Riassunto esportato con successo in: {os.path.basename(path)}")
        except Exception as e:
            self.show_status_message(f"Impossibile esportare il riassunto: {e}", error=True)
            logging.error(f"Errore durante l'esportazione in Word: {e}")

    def _add_html_to_doc(self, element, paragraph):
        """
        Funzione di supporto ricorsiva per analizzare l'HTML e aggiungerlo al documento Word,
        preservando la formattazione come grassetto, corsivo, colore del testo e colore di sfondo.
        """
        for child in element.children:
            if isinstance(child, str):
                run = paragraph.add_run(child)
                parent = element
                # Applica stili ereditati dai tag genitori (es. <b>, <i>, <font>, <span>)
                while parent and parent.name != 'body':
                    if parent.name in ['b', 'strong']:
                        run.bold = True
                    if parent.name in ['i', 'em']:
                        run.italic = True
                    # Gestisce il colore del testo (es. per i timecode)
                    if parent.name == 'font' and 'color' in parent.attrs:
                        color_str = parent['color'].lstrip('#')
                        if len(color_str) == 6: # Formato esadecimale RRGGBB
                            run.font.color.rgb = RGBColor.from_string(color_str)
                    # Gestisce il colore di sfondo (evidenziazione)
                    if parent.name == 'span' and 'style' in parent.attrs:
                        style = parent['style'].replace(" ", "")
                        if 'background-color:' in style:
                            # Cerca il colore corrispondente nella configurazione
                            for color_name, color_data in self.highlight_colors.items():
                                if f"background-color:{color_data['hex']}" in style:
                                    run.font.highlight_color = color_data['docx']
                                    break
                    parent = parent.parent
            elif child.name:
                # Se il figlio è un tag, continua la ricorsione
                self._add_html_to_doc(child, paragraph)

    def loadText(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carica file", "", "JSON files (*.json);;Text files (*.txt);;All files (*.*)")
        if path:
            # Se è un json, lo gestiamo con la nuova logica
            if path.endswith('.json'):
                # We need a video path to associate with the json.
                # For now, let's assume the json has a 'video_path' key.
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    video_path = data.get("video_path")
                    if video_path and os.path.exists(video_path):
                        self.loadVideo(video_path)
                    else:
                        QMessageBox.warning(self, "Attenzione", "Il file video associato a questo JSON non è stato trovato.")
                except Exception as e:
                    QMessageBox.critical(self, "Errore", f"Impossibile caricare il file JSON: {e}")
            # Se è un txt, lo carichiamo solo nell'area di testo
            else:
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        text_loaded = file.read()
                    self.transcriptionTextArea.setPlainText(text_loaded)
                    logging.debug("File di testo caricato correttamente!")
                except Exception as e:
                    logging.error(f"Errore durante il caricamento del file di testo: {e}")

    def openDownloadDialog(self):
        """Apre il dialogo per importare video da URL."""
        dialog = DownloadDialog(self)
        dialog.exec()

    def import_videos_to_project(self):
        """
        Apre un dialogo per selezionare file video e li importa nel progetto corrente.
        I video vengono copiati nella cartella 'clips' del progetto.
        """
        if not self.current_project_path or not self.projectDock.gnai_path:
            self.show_status_message("Nessun progetto attivo. Apri o crea un progetto prima di importare i video.", error=True)
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importa Video nel Progetto",
            "", # Default directory
            "Video Files (*.mp4 *.mov *.avi *.mkv)"
        )

        if not file_paths:
            return # User cancelled

        clips_dir = os.path.join(self.current_project_path, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        imported_count = 0
        for src_path in file_paths:
            try:
                clip_filename = os.path.basename(src_path)
                dest_path = os.path.join(clips_dir, clip_filename)

                # Evita di sovrascrivere file esistenti
                if os.path.exists(dest_path):
                    logging.warning(f"Il file '{clip_filename}' esiste già nella cartella delle clip. Importazione saltata.")
                    continue

                # Copia il file
                shutil.copy2(src_path, dest_path)

                # Estrai i metadati e aggiungi al progetto
                metadata_filename = os.path.splitext(clip_filename)[0] + ".json"

                clip_info = VideoFileClip(dest_path)
                duration = clip_info.duration
                clip_info.close()

                size = os.path.getsize(dest_path)
                creation_date = datetime.datetime.fromtimestamp(os.path.getctime(dest_path)).isoformat()

                self.project_manager.add_clip_to_project(
                    self.projectDock.gnai_path,
                    clip_filename,
                    metadata_filename,
                    duration,
                    size,
                    creation_date
                )
                imported_count += 1

            except Exception as e:
                logging.error(f"Errore durante l'importazione del file {src_path}: {e}")
                self.show_status_message(f"Errore durante l'importazione di {os.path.basename(src_path)}.", error=True)

        if imported_count > 0:
            self.show_status_message(f"Importati {imported_count} video con successo.")
            # Ricarica il progetto per aggiornare la vista
            self.load_project(self.projectDock.gnai_path)

    def isAudioOnly(self, file_path):
        """Check if the file is likely audio-only based on the extension."""
        audio_extensions = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in audio_extensions

    def sourceSetter(self, url):
        self.player.setSource(QUrl.fromLocalFile(url))
        self.player.play()
        self.player.pause()

    def sourceSetterOutput(self, url):
        self.playerOutput.setSource(QUrl.fromLocalFile(url))
        self.playerOutput.play()
        self.playerOutput.pause()

    def _manage_video_json(self, video_path):
        """
        Crea o carica il file JSON associato a un video.
        """
        json_path = os.path.splitext(video_path)[0] + ".json"

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logging.info(f"File JSON esistente caricato per {video_path}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Errore nel caricamento del file JSON {json_path}: {e}. Verrà creato un nuovo file.")
                data = self._create_new_json_data(video_path)
        else:
            logging.info(f"Nessun file JSON trovato per {video_path}. Creazione di un nuovo file.")
            data = self._create_new_json_data(video_path)

        # Pulisci la lista di audio generati, rimuovendo i file che non esistono più
        if 'generated_audios' in data:
            valid_audios = [audio for audio in data['generated_audios'] if os.path.exists(audio)]
            if len(valid_audios) != len(data['generated_audios']):
                data['generated_audios'] = valid_audios
                # Riscrivi il file solo se sono state fatte modifiche
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

        # Scrivi sempre per assicurarti che il formato sia corretto e aggiornato
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self._update_ui_from_json_data(data)
        return data

    def _create_new_json_data(self, video_path):
        """
        Crea la struttura dati di default per un nuovo file JSON.
        """
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()
            # Get video creation time
            creation_time = os.path.getctime(video_path)
            video_date = datetime.datetime.fromtimestamp(creation_time).isoformat()
        except Exception as e:
            logging.error(f"Impossibile leggere i metadati del video {video_path}: {e}")
            duration = 0
            video_date = datetime.datetime.now().isoformat()

        return {
            "video_path": video_path,
            "duration": duration,
            "language": "N/A",
            "video_date": video_date,
            "transcription_date": None,
            "transcription_raw": "", # Mantenuto per retrocompatibilità
            "transcription_original": "",
            "transcription_corrected": "",
            "summary_generated": "",
            "summary_generated_integrated": "",
            "summary_date": None,
            "generated_audios": [],
            "video_notes": []
        }

    def apply_selected_audio(self):
        """
        Applica l'audio selezionato dalla lista degli audio generati.
        """
        selected_items = self.generatedAudiosListWidget.selectedItems()
        if not selected_items:
            self.show_status_message("Nessun audio selezionato dalla lista.", error=True)
            return

        audio_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not os.path.exists(audio_path):
            self.show_status_message("Il file audio selezionato non esiste più.", error=True)
            # Rimuovi l'elemento dalla lista e dal JSON
            self._manage_video_json(self.videoPathLineEdit) # Questo ricaricherà e pulirà
            return

        self.show_status_message(f"Applicazione di {os.path.basename(audio_path)}...")
        self.apply_generated_audio(audio_path)

    def delete_selected_audio(self):
        """
        Elimina l'audio selezionato dalla lista, dal disco e dal file JSON.
        """
        selected_items = self.generatedAudiosListWidget.selectedItems()
        if not selected_items:
            self.show_status_message("Nessun audio selezionato da eliminare.", error=True)
            return

        item = selected_items[0]
        audio_path = item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Conferma Eliminazione",
            f"Sei sicuro di voler eliminare definitivamente il file audio?\n\n{os.path.basename(audio_path)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Rimuovi il file dal disco
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    self.show_status_message(f"File {os.path.basename(audio_path)} eliminato.")

                # 2. Rimuovi dal file JSON
                json_path = os.path.splitext(self.videoPathLineEdit)[0] + ".json"
                if os.path.exists(json_path):
                    with open(json_path, 'r+', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'generated_audios' in data and audio_path in data['generated_audios']:
                            data['generated_audios'].remove(audio_path)
                            f.seek(0)
                            json.dump(data, f, ensure_ascii=False, indent=4)
                            f.truncate()
                        # Aggiorna l'UI con i dati modificati
                        self._update_ui_from_json_data(data)

            except Exception as e:
                self.show_status_message(f"Errore durante l'eliminazione: {e}", error=True)
                logging.error(f"Errore durante l'eliminazione del file audio {audio_path}: {e}")


    def loadVideo(self, video_path, video_title = 'Video Track'):
        """Load and play video or audio, updating UI based on file type."""
        self.player.stop()
        self.reset_view()
        self.speedSpinBox.setValue(1.0)
        self.videoSlider.resetBookmarks()

        if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.sourceSetter(video_path))

        self.videoPathLineEdit = video_path

        is_audio_only = self.isAudioOnly(video_path)
        self.cropButton.setEnabled(not is_audio_only)

        if is_audio_only:
            self.fileNameLabel.setText(f"{video_title} - Traccia solo audio")
            self.videoCropWidget.setVisible(False)
            self.audioOnlyLabel.setVisible(True)
        else:
            self.fileNameLabel.setText(os.path.basename(video_path))
            self.videoCropWidget.setVisible(True)
            self.audioOnlyLabel.setVisible(False)

        self.updateRecentFiles(video_path)

        # Gestisce il file JSON (crea o carica) e aggiorna l'InfoDock
        self._manage_video_json(video_path)

    def loadVideoOutput(self, video_path):

        self.playerOutput.stop()
        self.speedSpinBoxOutput.setValue(1.0)

        if self.playerOutput.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.sourceSetterOutput(video_path))

        self.fileNameLabelOutput.setText(os.path.basename(video_path))  # Aggiorna il nome del file sulla label
        self.videoPathLineOutputEdit = video_path
        logging.debug(f"Loaded video output: {video_path}")


    def updateTimeCode(self, position):
        # Calcola ore, minuti e secondi dalla posizione, che è in millisecondi
        total_seconds = position // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = position % 1000
        timecode_str = f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}'
        # Aggiorna l'etichetta con il nuovo time code
        self.currentTimeLabel.setText(timecode_str)
        if not self.timecodeInput.hasFocus():
            self.timecodeInput.setText(timecode_str)

    def updateDuration(self, duration):
        # Calcola ore, minuti e secondi dalla durata, che è in millisecondi
        total_seconds = duration // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = duration % 1000
        # Aggiorna l'etichetta con la durata totale
        self.totalTimeLabel.setText(f' / {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}')

    def setupMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')

        openProjectAction = QAction('&Open Project...', self)
        openProjectAction.setStatusTip('Open a .gnai project file')
        openProjectAction.triggered.connect(self.open_project)
        fileMenu.addAction(openProjectAction)

        newProjectAction = QAction('&New Project...', self)
        newProjectAction.setStatusTip('Create a new project')
        newProjectAction.triggered.connect(self.create_new_project)
        fileMenu.addAction(newProjectAction)

        saveProjectAction = QAction('&Save Project', self)
        saveProjectAction.setShortcut('Ctrl+S')
        saveProjectAction.setStatusTip('Save the current project')
        saveProjectAction.triggered.connect(self.save_project)
        fileMenu.addAction(saveProjectAction)

        fileMenu.addSeparator()

        openAction = QAction('&Open Video/Audio', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open video')
        openAction.triggered.connect(self.browseVideo)

        openActionOutput = QAction('&Open as Output Video', self)
        openAction.setShortcut('Ctrl+I')
        openActionOutput.setStatusTip('Open Video Output')
        openActionOutput.triggered.connect(self.browseVideoOutput)

        fileMenu.addAction(openAction)
        fileMenu.addAction(openActionOutput)

        # New Save As action
        saveAsAction = QAction('&Save Video Output As...', self)
        saveAsAction.setShortcut('Ctrl+S')
        saveAsAction.setStatusTip('Save the current video from Video Player Output')
        saveAsAction.triggered.connect(self.saveVideoAs)
        fileMenu.addAction(saveAsAction)

        # Action to open root folder
        openRootFolderAction = QAction('&Open Root Folder', self)
        openRootFolderAction.setShortcut('Ctrl+R')
        openRootFolderAction.setStatusTip('Open the root folder of the software')
        openRootFolderAction.triggered.connect(self.openRootFolder)
        fileMenu.addAction(openRootFolderAction)

        fileMenu.addSeparator()

        releaseSourceAction = QAction(QIcon(get_resource("reset.png")), "Unload Video Source", self)
        releaseSourceAction.triggered.connect(self.releaseSourceVideo)
        fileMenu.addAction(releaseSourceAction)

        releaseOutputAction = QAction(QIcon(get_resource("reset.png")), "Unload Video Output", self)
        releaseOutputAction.triggered.connect(self.releaseOutputVideo)
        fileMenu.addAction(releaseOutputAction)

        fileMenu.addSeparator()

        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        fileMenu.addSeparator()
        self.recentMenu = fileMenu.addMenu("Recenti")  # Aggiunge il menu dei file recenti
        self.updateRecentFilesMenu()

        self.recentProjectsMenu = fileMenu.addMenu("Progetti Recenti")
        self.updateRecentProjectsMenu()


        # Creazione del menu Import
        importMenu = menuBar.addMenu('&Import')
        importUrlAction = QAction('Importa da URL...', self)
        importUrlAction.setStatusTip('Importa video o audio da un URL (es. YouTube)')
        importUrlAction.triggered.connect(self.openDownloadDialog)
        importMenu.addAction(importUrlAction)

        importVideoAction = QAction('Importa Video nel Progetto...', self)
        importVideoAction.setStatusTip('Importa file video locali nel progetto corrente')
        importVideoAction.triggered.connect(self.import_videos_to_project)
        importMenu.addAction(importVideoAction)

        # Creazione del menu View per la gestione della visibilità dei docks
        viewMenu = menuBar.addMenu('&View')

        # Creazione del menu Effetti (Rimosso)
        # effectsMenu = menuBar.addMenu('&Effetti')
        # self.setupEffectsMenuActions(effectsMenu)

        # Creazione del menu Workspace per i layout preimpostati
        workspaceMenu = menuBar.addMenu('&Workspace')
        workspaceMenu.addAction(self.defaultLayoutAction)
        workspaceMenu.addAction(self.recordingLayoutAction)
        workspaceMenu.addAction(self.comparisonLayoutAction)
        workspaceMenu.addAction(self.transcriptionLayoutAction)


        # Aggiunta del menu Workflows
        workflowsMenu = menuBar.addMenu('&Workflows')
        workflowsMenu.addAction(self.summarizeMeetingAction)
        workflowsMenu.addAction(self.summarizeAction)
        workflowsMenu.addAction(self.fixTextAction)
        workflowsMenu.addAction(self.generatePptxAction)
        # workflowsMenu.addAction(self.extractInfoAction)

        # Creazione del menu Export
        exportMenu = menuBar.addMenu('&Export')
        exportWordAction = QAction('Esporta riassunto in Word', self)
        exportWordAction.triggered.connect(self.exportSummaryToWord)
        exportMenu.addAction(exportWordAction)

        # Creazione del menu Insert
        insertMenu = menuBar.addMenu('&Insert')
        addMediaAction = QAction('Add Media/Text...', self)
        addMediaAction.setStatusTip('Aggiungi testo o immagini al video')
        addMediaAction.triggered.connect(self.openAddMediaDialog)
        insertMenu.addAction(addMediaAction)

        """
        agentAIsMenu = menuBar.addMenu('&Agent AIs')

        # Opzioni esistenti
        runAgentAction = QAction('&Esegui Agent', self)
        runAgentAction.setStatusTip('Esegui agent AI sul media corrente')
        runAgentAction.triggered.connect(self.runAgent)
        agentAIsMenu.addAction(runAgentAction)

        # Nuova opzione per la creazione della guida e lancio dell'agente
        agentAIsMenu.addSeparator()  # Aggiungi un separatore per chiarezza
        createGuideAction = QAction('&Crea Guida Operativa', self)
        createGuideAction.setStatusTip('Crea una guida operativa dai frame estratti')
        createGuideAction.triggered.connect(self.createGuideAndRunAgent)
        agentAIsMenu.addAction(createGuideAction)
        """
        viewMenu.aboutToShow.connect(self.updateViewMenu)  # Aggiunta di questo segnale
        self.setupViewMenuActions(viewMenu)

        # Creazione del menu About
        aboutMenu = menuBar.addMenu('&About')
        # Aggiunta di azioni al menu About
        aboutAction = QAction('&About', self)
        aboutAction.setStatusTip('About the application')
        aboutAction.triggered.connect(self.about)
        aboutMenu.addAction(aboutAction)

    def setupEffectsMenuActions(self, effectsMenu):
        addPipAction = QAction('Aggiungi Video Picture-in-Picture', self)
        addPipAction.setStatusTip('Apre il pannello per aggiungere un video in PiP')
        addPipAction.triggered.connect(lambda: self.showEffectsDock(0))
        effectsMenu.addAction(addPipAction)

        addImageOverlayAction = QAction('Aggiungi Immagine Overlay', self)
        addImageOverlayAction.setStatusTip("Apre il pannello per aggiungere un'immagine in sovraimpressione")
        addImageOverlayAction.triggered.connect(lambda: self.showEffectsDock(1))
        effectsMenu.addAction(addImageOverlayAction)

    def showEffectsDock(self, tab_index=0):
        """Mostra il dock degli effetti e seleziona il tab specificato."""
        if not self.videoEffectsDock.isVisible():
            self.videoEffectsDock.show()
        self.videoEffectsDock.raise_()

        # Accedi al QTabWidget, che è il primo (e unico) widget nel dock
        widgets_in_dock = self.videoEffectsDock.widgets()
        if widgets_in_dock:
            tab_widget = widgets_in_dock[0]
            if isinstance(tab_widget, QTabWidget):
                tab_widget.setCurrentIndex(tab_index)

    def saveVideoAs(self):
        if not self.videoPathLineOutputEdit:
            self.show_status_message("Nessun video caricato nel Video Player Output.", error=True)
            return

        from ui.VideoSaveOptionsDialog import VideoSaveOptionsDialog
        from services.VideoSaver import VideoSaver

        options_dialog = VideoSaveOptionsDialog(self.videoPathLineOutputEdit, self)
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        save_options = options_dialog.getOptions()

        default_dir = ""
        if self.current_project_path:
            default_dir = os.path.join(self.current_project_path, "clips")

        source_for_name = self.videoPathLineEdit if self.videoPathLineEdit else self.videoPathLineOutputEdit
        base_name, ext = os.path.splitext(os.path.basename(source_for_name))
        if base_name.startswith("tmp_"):
            base_name = "processed_clip"
        default_filename = f"{base_name}_output{ext}"

        default_path = os.path.join(default_dir, default_filename) if default_dir else default_filename

        file_filter = "Video Files (*.mp4 *.mov *.avi)"
        fileName, _ = QFileDialog.getSaveFileName(self, "Salva Video con Nome", default_path, file_filter)

        if not fileName:
            return

        is_project_save = False
        if self.current_project_path:
            clips_dir = os.path.join(self.current_project_path, "clips")
            if os.path.normpath(os.path.dirname(fileName)) == os.path.normpath(clips_dir):
                is_project_save = True

        video_saver = VideoSaver(self)
        thread = video_saver.save_video(self.videoPathLineOutputEdit, fileName, save_options)

        if thread:
            self.start_task(thread, lambda path: self.onSaveCompleted(path, is_project_save=is_project_save), self.onSaveError, self.update_status_progress)

    def onSaveCompleted(self, output_path, is_project_save=False):
        self.show_status_message(f"Video salvato con successo in: {os.path.basename(output_path)}")

        if is_project_save and self.current_project_path:
            clip_filename = os.path.basename(output_path)
            metadata_filename = os.path.splitext(clip_filename)[0] + ".json"
            try:
                clip_info = VideoFileClip(output_path)
                duration = clip_info.duration
                clip_info.close()
                size = os.path.getsize(output_path)
                creation_date = datetime.datetime.fromtimestamp(os.path.getctime(output_path)).isoformat()

                self.project_manager.add_clip_to_project(
                    self.projectDock.gnai_path,
                    clip_filename,
                    metadata_filename,
                    duration,
                    size,
                    creation_date
                )
                self.load_project(self.projectDock.gnai_path) # Ricarica per aggiornare la UI
                self.show_status_message(f"Clip '{clip_filename}' aggiunta al progetto.")
            except Exception as e:
                logging.error(f"Impossibile aggiungere la clip salvata al progetto: {e}")
                self.show_status_message("Errore nell'aggiungere la clip al progetto.", error=True)

    def onSaveError(self, error_message):
        self.show_status_message(f"Errore durante il salvataggio del video: {error_message}", error=True)

    def setupViewMenuActions(self, viewMenu):
        # Azione per il Video Player Dock
        self.actionToggleVideoPlayerDock = QAction('Mostra/Nascondi Video Player Input', self, checkable=True)
        self.actionToggleVideoPlayerDock.setChecked(self.videoPlayerDock.isVisible())
        self.actionToggleVideoPlayerDock.triggered.connect(
            lambda: self.toggleDockVisibilityAndUpdateMenu(self.videoPlayerDock,
                                                           self.actionToggleVideoPlayerDock.isChecked()))

        # Azioni simili per gli altri docks...
        self.actionToggleVideoPlayerDockOutput = self.createToggleAction(self.videoPlayerOutput,
                                                                         'Mostra/Nascondi Video Player Output')
        self.actionToggleTranscriptionDock = self.createToggleAction(self.transcriptionDock,
                                                                     'Mostra/Nascondi Trascrizione')
        self.actionToggleEditingDock = self.createToggleAction(self.editingDock, 'Mostra/Nascondi Generazione Audio AI')
        self.actionToggleRecordingDock = self.createToggleAction(self.recordingDock, 'Mostra/Nascondi Registrazione')
        self.actionToggleAudioDock = self.createToggleAction(self.audioDock, 'Mostra/Nascondi Gestione Audio/Video')
        self.actionToggleVideoEffectsDock = self.createToggleAction(self.videoEffectsDock, 'Mostra/Nascondi Effetti Video')
        self.actionToggleInfoDock = self.createToggleAction(self.infoDock, 'Mostra/Nascondi Info Video')
        self.actionToggleProjectDock = self.createToggleAction(self.projectDock, 'Mostra/Nascondi Projects')
        self.actionToggleVideoNotesDock = self.createToggleAction(self.videoNotesDock, 'Mostra/Nascondi Note Video')

        # Aggiungi tutte le azioni al menu 'View'
        viewMenu.addAction(self.actionToggleVideoPlayerDock)
        viewMenu.addAction(self.actionToggleVideoPlayerDockOutput)
        viewMenu.addAction(self.actionToggleTranscriptionDock)
        viewMenu.addAction(self.actionToggleEditingDock)
        viewMenu.addAction(self.actionToggleRecordingDock)
        viewMenu.addAction(self.actionToggleAudioDock)
        viewMenu.addAction(self.actionToggleVideoEffectsDock)
        viewMenu.addAction(self.actionToggleInfoDock)
        viewMenu.addAction(self.actionToggleProjectDock)
        viewMenu.addAction(self.actionToggleVideoNotesDock)



        # Aggiungi azioni per mostrare/nascondere tutti i docks
        showAllDocksAction = QAction('Mostra tutti i Docks', self)
        hideAllDocksAction = QAction('Nascondi tutti i Docks', self)

        showAllDocksAction.triggered.connect(self.showAllDocks)
        hideAllDocksAction.triggered.connect(self.hideAllDocks)

        viewMenu.addSeparator()  # Aggiunge un separatore per chiarezza
        viewMenu.addAction(showAllDocksAction)
        viewMenu.addAction(hideAllDocksAction)


        # Azione per salvare il layout dei docks
        saveLayoutAction = QAction('Salva Layout dei Docks', self)
        saveLayoutAction.triggered.connect(self.saveDockLayout)
        viewMenu.addSeparator()  # Aggiunge un separatore per chiarezza
        viewMenu.addAction(saveLayoutAction)

        # Aggiorna lo stato iniziale del menu
        self.updateViewMenu()

    def saveDockLayout(self):
        if hasattr(self, 'dockSettingsManager'):
            self.dockSettingsManager.save_settings()
            self.show_status_message("Layout dei docks salvato correttamente.")
        else:
            self.show_status_message("Gestore delle impostazioni dei dock non trovato.", error=True)

    def showAllDocks(self):
        # Imposta tutti i docks visibili
        self.videoPlayerDock.setVisible(True)
        self.videoPlayerOutput.setVisible(True)
        self.audioDock.setVisible(True)
        self.transcriptionDock.setVisible(True)
        self.editingDock.setVisible(True)
        self.recordingDock.setVisible(True)
        self.videoEffectsDock.setVisible(True)
        self.updateViewMenu()  # Aggiorna lo stato dei menu

    def hideAllDocks(self):
        # Nasconde tutti i docks
        self.videoPlayerDock.setVisible(False)
        self.videoPlayerOutput.setVisible(False)
        self.audioDock.setVisible(False)
        self.transcriptionDock.setVisible(False)
        self.editingDock.setVisible(False)
        self.recordingDock.setVisible(False)
        self.videoEffectsDock.setVisible(False)
        self.updateViewMenu()  # Aggiorna lo stato dei menu
    def createToggleAction(self, dock, menuText):
        action = QAction(menuText, self, checkable=True)
        action.setChecked(dock.isVisible())
        action.triggered.connect(lambda checked: self.toggleDockVisibilityAndUpdateMenu(dock, checked))
        return action

    def toggleDockVisibilityAndUpdateMenu(self, dock, visible):
        if visible:
            dock.showDock()
        else:
            dock.hideDock()

        self.updateViewMenu()

    def resetViewMenu(self):

        self.actionToggleVideoPlayerDock.setChecked(True)
        self.actionToggleVideoPlayerDockOutput.setChecked(True)
        self.actionToggleAudioDock.setChecked(True)
        self.actionToggleTranscriptionDock.setChecked(True)
        self.actionToggleEditingDock.setChecked(True)
        self.actionToggleRecordingDock.setChecked(True)
        self.actionToggleVideoEffectsDock.setChecked(True)
        self.actionToggleProjectDock.setChecked(True)
        self.actionToggleInfoDock.setChecked(True)

    def updateViewMenu(self):

        # Aggiorna lo stato dei menu checkable basato sulla visibilità dei dock
        self.actionToggleVideoPlayerDock.setChecked(self.videoPlayerDock.isVisible())
        self.actionToggleVideoPlayerDockOutput.setChecked(self.videoPlayerOutput.isVisible())
        self.actionToggleAudioDock.setChecked(self.audioDock.isVisible())
        self.actionToggleTranscriptionDock.setChecked(self.transcriptionDock.isVisible())
        self.actionToggleEditingDock.setChecked(self.editingDock.isVisible())
        self.actionToggleRecordingDock.setChecked(self.recordingDock.isVisible())
        self.actionToggleVideoEffectsDock.setChecked(self.videoEffectsDock.isVisible())
        self.actionToggleInfoDock.setChecked(self.infoDock.isVisible())
        self.actionToggleProjectDock.setChecked(self.projectDock.isVisible())
        self.actionToggleVideoNotesDock.setChecked(self.videoNotesDock.isVisible())

    def about(self):
        QMessageBox.about(self, "TGeniusAI",
                          f"""<b>Genius AI</b> version: {self.version}<br>
                          AI-based video and audio management application.<br>
                          <br>
                          Autore: FFA <br>""")

    def onTranscriptionError(self, error_message):
        # Il metodo finish_task mostra già l'errore, quindi non è necessario fare altro qui
        # a meno che non ci sia una logica specifica da eseguire in caso di errore.
        pass


    def handleTextChange(self):
        if self.transcriptionTextArea.signalsBlocked():
            return

        # Avvia il timer di salvataggio automatico
        self.autosave_timer.start(2500)  # 2.5 secondi

        # Quando l'utente modifica il testo, questo diventa il nuovo "original_text"
        # e qualsiasi riassunto precedente viene invalidato.
        self.summaries = {}
        self.active_summary_type = None

        self.original_text = self.transcriptionTextArea.toPlainText()

        # La logica del timecode e del rilevamento lingua rimane
        # Usa il testo semplice per il rilevamento della lingua per evitare problemi con l'HTML
        plain_text = self.transcriptionTextArea.toPlainText()
        if plain_text.strip():
            # La logica del timecode è stata rimossa da qui perché deve essere
            # gestita esclusivamente dal toggle nella tab "Audio AI" e non
            # deve attivarsi a ogni modifica della trascrizione.
            self.detectAndUpdateLanguage(plain_text)

    def autosave_transcription(self):
        """
        Salva automaticamente la trascrizione nel file JSON associato al video.
        """
        if not self.videoPathLineEdit:
            logging.debug("Salvataggio automatico saltato: nessun video caricato.")
            return

        logging.info("Salvataggio automatico della trascrizione...")
        current_text = self.transcriptionTextArea.toPlainText()
        update_data = {
            "transcription_raw": current_text,
            "transcription_date": datetime.datetime.now().isoformat()
        }
        self._update_json_file(self.videoPathLineEdit, update_data)

    def calculateAndDisplayTimeCodeAtEndOfSentences(self, html_text):
        WPM = 150
        words_per_second = WPM / 60
        cumulative_time = 0.0

        soup = BeautifulSoup(html_text, 'html.parser')

        # Rimuove i timestamp esistenti per evitare duplicazioni.
        # Cerca il tag <font> specifico e lo elimina.
        for ts_tag in soup.find_all('font', color='#ADD8E6'):
            # Rimuove anche lo spazio vuoto che segue il timestamp, se presente
            next_sibling = ts_tag.next_sibling
            if next_sibling and isinstance(next_sibling, str) and next_sibling.startswith(' '):
                next_sibling.replace_with(next_sibling.lstrip())
            ts_tag.decompose()

        new_body = BeautifulSoup('<body></body>', 'html.parser').body

        # Process paragraphs or the whole body if no paragraphs exist
        elements_to_process = soup.find_all('p') if soup.find('p') else [soup.body]

        for element in elements_to_process:
            if not element: continue

            current_sentence_nodes = []
            # Make a copy to iterate over as we will be modifying the tree
            for node in list(element.contents):
                # Detach the node from its original parent to be moved later
                node.extract()
                current_sentence_nodes.append(node)

                # Check if the sentence is complete
                # A sentence is complete if the node is a string that ends with sentence punctuation
                if isinstance(node, str) and re.search(r'[.!?]\s*$', node):
                    # Process the collected sentence
                    sentence_html = ''.join(str(n) for n in current_sentence_nodes)
                    sentence_text = BeautifulSoup(sentence_html, 'html.parser').get_text()
                    words = re.findall(r'\b\w+\b', sentence_text)

                    if words:
                        time_for_sentence = len(words) / words_per_second
                        cumulative_time += time_for_sentence

                        # Correctly calculate hours, minutes, and seconds
                        hours = int(cumulative_time // 3600)
                        minutes = int((cumulative_time % 3600) // 60)
                        seconds = cumulative_time % 60

                        # Create new paragraph for the sentence
                        new_p = soup.new_tag('p')

                        # Create and add timestamp with HH:MM:SS.d format using <font> tag for better compatibility
                        timestamp_font_str = f"<font color='#ADD8E6'>[{hours:02d}:{minutes:02d}:{seconds:04.1f}]</font> "
                        timestamp_node = BeautifulSoup(timestamp_font_str, 'html.parser').font
                        new_p.append(timestamp_node)

                        # Add sentence content
                        for snode in current_sentence_nodes:
                            new_p.append(snode)

                        new_body.append(new_p)

                    # Reset for the next sentence
                    current_sentence_nodes = []

            # Handle any remaining nodes that didn't form a complete sentence
            if current_sentence_nodes:
                sentence_html = ''.join(str(n) for n in current_sentence_nodes)
                sentence_text = BeautifulSoup(sentence_html, 'html.parser').get_text()
                words = re.findall(r'\b\w+\b', sentence_text)

                if words:
                    time_for_sentence = len(words) / words_per_second
                    cumulative_time += time_for_sentence

                    # Correctly calculate hours, minutes, and seconds
                    hours = int(cumulative_time // 3600)
                    minutes = int((cumulative_time % 3600) // 60)
                    seconds = cumulative_time % 60

                    new_p = soup.new_tag('p')
                    # Create and add timestamp with HH:MM:SS.d format using <font> tag
                    timestamp_font_str = f"<font color='#ADD8E6'>[{hours:02d}:{minutes:02d}:{seconds:04.1f}]</font> "
                    timestamp_node = BeautifulSoup(timestamp_font_str, 'html.parser').font
                    new_p.append(timestamp_node)
                    for snode in current_sentence_nodes:
                        new_p.append(snode)
                    new_body.append(new_p)

        return new_body.decode_contents()

    def _style_existing_timestamps(self, text_edit):
        """
        Applica uno stile coerente ai timestamp esistenti in un QTextEdit.
        Cerca i timestamp nel formato [HH:MM:SS.d] e li colora.
        """
        # Pattern per trovare timestamp come [00:00:02.4] o [00:00]
        timestamp_pattern = re.compile(r'(\[\d{2}:\d{2}:\d{2}(?:\.\d)?\]|\[\d{2}:\d{2}(?:\.\d)?\]|\[\d+:\d+:\d+(\.\d)?\])')

        current_html = text_edit.toHtml()

        # Sostituisce ogni timestamp trovato con la versione stilizzata
        def style_match(match):
            return f"<font color='#ADD8E6'>{match.group(1)}</font>"

        # Per evitare di stilizzare più volte, prima rimuoviamo i tag <font> esistenti
        current_html = re.sub(r"<font color='#ADD8E6'>(.*?)</font>", r'\1', current_html)

        # Riapplichiamo lo stile
        new_html = timestamp_pattern.sub(style_match, current_html)

        if new_html != current_html:
            # Salva la posizione del cursore
            cursor = text_edit.textCursor()
            cursor_pos = cursor.position()
            # Applica il nuovo HTML
            text_edit.setHtml(new_html)
            # Ripristina la posizione del cursore
            cursor.setPosition(cursor_pos)


    def detectAndUpdateLanguage(self, text):
        try:
            detected_language_code = detect(text)
            language = pycountry.languages.get(alpha_2=detected_language_code)
            if language:
                detected_language = language.name
                self.updateLanguageComboBox(detected_language_code, detected_language)
                self.updateTranscriptionLanguageDisplay(detected_language)
            else:
                self.updateTranscriptionLanguageDisplay("Lingua non supportata")
        except LangDetectException:
            self.updateTranscriptionLanguageDisplay("Non rilevabile")

    def updateLanguageComboBox(self, language_code, language_name):
        index = self.languageComboBox.findData(language_code)
        if index == -1:
            self.languageComboBox.addItem(language_name, language_code)
            index = self.languageComboBox.count() - 1
        self.languageComboBox.setCurrentIndex(index)

    def updateTranscriptionLanguageDisplay(self, language):
        self.transcriptionLanguageLabel.setText(f"Lingua rilevata: {language}")

    def transcribeVideo(self):
        if not self.videoPathLineEdit:
            self.show_status_message("Nessun video selezionato.", error=True)
            return

        thread = TranscriptionThread(self.videoPathLineEdit, self)
        self.start_task(thread, self.onTranscriptionComplete, self.onTranscriptionError, self.update_status_progress)

    def onTranscriptionComplete(self, result):
        json_path, temp_files = result
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Carica il testo e poi applica lo stile
            self.transcriptionTextArea.setPlainText(data.get('transcription_raw', ''))
            self._style_existing_timestamps(self.transcriptionTextArea)
            self.onProcessComplete(data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.show_status_message(f"Errore nel caricare la trascrizione: {e}", error=True)
            logging.error(f"Failed to load transcription JSON {json_path}: {e}")

        self.cleanupFiles(temp_files)
        self.show_status_message("Trascrizione completata.")

    def onTranscriptionError(self, error_message):
        # Il metodo finish_task mostra già l'errore, quindi non è necessario fare altro qui
        # a meno che non ci sia una logica specifica da eseguire in caso di errore.
        pass

    def _update_ui_from_json_data(self, data):
        """
        Aggiorna l'interfaccia utente con i dati dal file JSON.
        """
        # Carica le trascrizioni, gestendo la retrocompatibilità
        self.transcription_original = data.get('transcription_original', data.get('transcription_raw', ''))
        self.transcription_corrected = data.get('transcription_corrected', '')

        # Decide quale testo mostrare e imposta lo stato del toggle
        if self.transcription_corrected:
            self.transcriptionTextArea.setPlainText(self.transcription_corrected)
            self.transcriptionViewToggle.setEnabled(True)
            self.transcriptionViewToggle.setChecked(True)
        else:
            # Carica l'HTML per preservare la formattazione
            self.transcriptionTextArea.setHtml(self.transcription_original)
            self._style_existing_timestamps(self.transcriptionTextArea) # Applica stile
            self.transcriptionViewToggle.setEnabled(False)
            self.transcriptionViewToggle.setChecked(False)

        # Carica entrambi i tipi di riassunto
        self.summary_generated = data.get('summary_generated', '')
        self.summary_generated_integrated = data.get('summary_generated_integrated', '')

        # Decide quale riassunto mostrare e imposta lo stato del toggle
        if self.summary_generated_integrated:
            self.summary_text = self.summary_generated_integrated
            self.integrazioneToggle.setEnabled(True)
            self.integrazioneToggle.setChecked(True)
        else:
            self.summary_text = self.summary_generated
            self.integrazioneToggle.setEnabled(False)
            self.integrazioneToggle.setChecked(False)

        self.update_summary_view()

        # Imposta la lingua nella combobox
        language_code = data.get("language")
        if language_code:
            index = self.languageComboBox.findData(language_code)
            if index != -1:
                self.languageComboBox.setCurrentIndex(index)

        # Aggiorna il dock informativo
        self.infoDock.update_info(data)

        # Carica le note video
        self.load_video_notes_from_json(data)

        # Aggiorna la lista degli audio generati
        self.generatedAudiosListWidget.clear()
        if 'generated_audios' in data and data['generated_audios']:
            for audio_path in data['generated_audios']:
                # Mostra solo il nome del file per leggibilità
                item_text = os.path.basename(audio_path)
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.ItemDataRole.UserRole, audio_path) # Salva il percorso completo
                self.generatedAudiosListWidget.addItem(list_item)
        logging.debug("UI aggiornata con i dati JSON!")

    def cleanupFiles(self, file_paths):
        """Safely removes temporary files used during transcription."""
        for path in file_paths:
            self.removeFileSafe(path)

    def removeFileSafe(self, file_path, attempts=5, delay=0.5):
        """Attempt to safely remove a file with retries and delays."""
        for _ in range(attempts):
            try:
                os.remove(file_path)
                logging.debug(f"File {file_path} successfully removed.")
                break
            except PermissionError:
                logging.debug(f"Warning: File {file_path} is currently in use. Retrying...")
                time.sleep(delay)
            except FileNotFoundError:
                logging.debug(f"The file {file_path} does not exist or has already been removed.")
                break
            except Exception as e:
                logging.debug(f"Unexpected error while removing {file_path}: {e}")
    def handleErrors(self, progress_dialog):
        def error(message):
            QMessageBox.critical(self, "Errore nella Trascrizione",
                                 f"Errore durante la trascrizione del video: {message}")
            progress_dialog.cancel()

        return error

    def generateAudioWithElevenLabs(self):
        api_key = get_api_key('elevenlabs')
        if not api_key:
            self.show_status_message("Per favore, imposta l'API Key di ElevenLabs nelle impostazioni.", error=True)
            return

        def convert_numbers_to_words(text):
            text = re.sub(r'(\d+)\.', r'\1 .', text)
            new_text = []
            for word in text.split():
                if word.isdigit():
                    new_word = num2words(word, lang='it')
                    new_text.append(new_word)
                else:
                    new_text.append(word)
            return ' '.join(new_text)

        transcriptionText = self.audioAiTextArea.toPlainText()
        if not transcriptionText.strip():
            self.show_status_message("Inserisci il testo nella tab 'Audio AI' prima di generare l'audio.", error=True)
            return
        transcriptionText = convert_numbers_to_words(transcriptionText)

        voice_id = self.voiceSelectionComboBox.currentData()
        model_id = "eleven_multilingual_v1"

        voice_settings = {
            'stability': self.stabilitySlider.value() / 100.0,
            'similarity_boost': self.similaritySlider.value() / 100.0,
            'style': self.styleSlider.value() / 10.0,
            'use_speaker_boost': self.speakerBoostCheckBox.isChecked()
        }

        base_name = os.path.splitext(os.path.basename(self.videoPathLineEdit))[0] if self.videoPathLineEdit else "generated_audio"
        save_dir = os.path.dirname(self.videoPathLineEdit) if self.videoPathLineEdit else "."
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        audio_save_path = os.path.join(save_dir, f"{base_name}_generated_{timestamp}.mp3")

        thread = AudioGenerationThread(transcriptionText, voice_id, model_id, voice_settings, api_key, audio_save_path, self)
        self.start_task(thread, self.onAudioGenerationCompleted, self.onAudioGenerationError, self.update_status_progress)

    def runWav2Lip(self, video_path, audio_path, output_path):
        command = [
            'python', './Wav2Lip-master/inference.py',
            '--checkpoint_path', './Wav2Lip-master/checkpoints',  # Sostituisci con il percorso al tuo checkpoint
            '--face', video_path,
            '--audio', audio_path,
            '--outfile', output_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Errore nell'esecuzione di Wav2Lip: {result.stderr}")

    def createGuideAndRunAgent(self):
        """
        Crea una guida operativa dai frame estratti e esegue l'agent browser
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.create_guide_agent()

    def onAudioGenerationCompleted(self, audio_path):
        """
        Called when the AI audio generation is complete.
        This function now decides whether to sync the audio or apply it at a specific time.
        """
        # Aggiungi il nuovo audio al file JSON del video
        json_path = os.path.splitext(self.videoPathLineEdit)[0] + ".json"
        if os.path.exists(json_path):
            with open(json_path, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                if 'generated_audios' not in data:
                    data['generated_audios'] = []
                data['generated_audios'].append(audio_path)
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.truncate()
            # Aggiorna l'UI
            self._update_ui_from_json_data(data)

        self.apply_generated_audio(
            new_audio_path=audio_path
        )

    def onAudioGenerationError(self, error_message):
        self.show_status_message(f"Errore durante la generazione dell'audio: {error_message}", error=True)

    def _parse_time(self, time_str):
        """Parses a time string HH:MM:SS.ms into seconds."""
        try:
            parts = time_str.split(':')
            if len(parts) != 3:
                raise ValueError("Invalid time format. Expected HH:MM:SS.ms")

            h = int(parts[0])
            m = int(parts[1])

            s_ms_part = parts[2].split('.')
            s = int(s_ms_part[0])
            ms = int(s_ms_part[1]) if len(s_ms_part) > 1 else 0

            return h * 3600 + m * 60 + s + ms / 1000.0
        except (ValueError, IndexError) as e:
            self.show_status_message(f"Formato ora non valido: {time_str}. Usare HH:MM:SS.ms.", error=True)
            return None

    def apply_generated_audio(self, new_audio_path):
        video_path = self.videoPathLineEdit
        if not video_path or not os.path.exists(video_path):
            self.show_status_message("Nessun video caricato per applicare l'audio.", error=True)
            return

        start_time_sec = self.player.position() / 1000.0

        thread = AudioProcessingThread(
            video_path,
            new_audio_path,
            self.alignspeed.isChecked(), # use_sync is now controlled by the checkbox
            start_time_sec,
            parent=self
        )
        self.start_task(thread, self.onAudioProcessingCompleted, self.onAudioProcessingError, self.update_status_progress)

    def onAudioProcessingCompleted(self, output_path):
        self.show_status_message("Audio applicato al video con successo.")
        self.loadVideoOutput(output_path)

    def onAudioProcessingError(self, error_message):
        self.show_status_message(f"Errore durante l'applicazione dell'audio: {error_message}", error=True)

    def handle_apply_main_audio(self):
        """Handles the 'Applica Audio Principale' button click."""
        video_path = self.videoPathLineEdit
        new_audio_path = self.audioPathLineEdit.text()

        if not video_path or not os.path.exists(video_path):
            self.show_status_message("Nessun video caricato.", error=True)
            return

        if not new_audio_path or not os.path.exists(new_audio_path):
            self.show_status_message("Nessun file audio selezionato.", error=True)
            return

        start_time_sec = self.player.position() / 1000.0

        thread = AudioProcessingThread(
            video_path,
            new_audio_path,
            self.alignspeed_replacement.isChecked(), # use_sync is now controlled by the checkbox
            start_time_sec,
            parent=self
        )
        self.start_task(thread, self.onAudioProcessingCompleted, self.onAudioProcessingError, self.update_status_progress)

    def browseAudio(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio", "", "Audio Files (*.mp3 *.wav)")
        if fileName:
            self.audioPathLineEdit.setText(fileName)

    def extractAudioFromVideo(self, video_path):
        # Estrai l'audio dal video e salvalo temporaneamente
        temp_audio_path = self.get_temp_filepath(suffix='.mp3')
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(temp_audio_path)
        return temp_audio_path

    def applyNewAudioToVideo(self, video_path_line_edit, new_audio_path, align_audio_video):
        video_path = video_path_line_edit

        # Migliorata la validazione degli input
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Attenzione", "Il file video selezionato non esiste.")
            return

        if not new_audio_path or not os.path.exists(new_audio_path):
            QMessageBox.warning(self, "Attenzione", "Il file audio selezionato non esiste.")
            return

        # Verifica la dimensione dei file
        video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        audio_size_mb = os.path.getsize(new_audio_path) / (1024 * 1024)

        # Avvisa l'utente se i file sono molto grandi
        if video_size_mb > 500 or audio_size_mb > 100:
            reply = QMessageBox.question(
                self, "File di grandi dimensioni",
                f"Stai elaborando file di grandi dimensioni (Video: {video_size_mb:.1f} MB, Audio: {audio_size_mb:.1f} MB).\n"
                "L'elaborazione potrebbe richiedere molto tempo. Continuare?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Crea un percorso di output unico con timestamp per evitare sovrascritture
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.dirname(video_path)
        output_path = os.path.join(output_dir, f"{base_name}_audio_{timestamp}.mp4")

        # Creiamo un dialog personalizzato che sostituisce QProgressDialog
        class CustomProgressDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Processo Audio-Video")
                self.setModal(True)
                self.setMinimumWidth(400)

                layout = QVBoxLayout(self)

                # Label per il messaggio di stato
                self.statusLabel = QLabel("Preparazione processo...")
                layout.addWidget(self.statusLabel)

                # Barra di progresso
                self.progressBar = QProgressBar()
                self.progressBar.setRange(0, 100)
                self.progressBar.setValue(0)
                layout.addWidget(self.progressBar)

                # Log dettagliato
                self.logDialog = QDialog(self)
                self.logDialog.setWindowTitle("Log Dettagliato")
                self.logDialog.setMinimumSize(600, 400)
                logLayout = QVBoxLayout(self.logDialog)
                self.logTextEdit = QTextEdit()
                self.logTextEdit.setReadOnly(True)
                logLayout.addWidget(self.logTextEdit)

                # Pulsanti
                buttonLayout = QHBoxLayout()

                # Pulsante per mostrare log
                self.logButton = QPushButton("Mostra Log")
                self.logButton.clicked.connect(self.logDialog.show)
                buttonLayout.addWidget(self.logButton)

                # Pulsante per annullare
                self.cancelButton = QPushButton("Annulla")
                self.cancelButton.clicked.connect(self.reject)
                buttonLayout.addWidget(self.cancelButton)

                layout.addLayout(buttonLayout)

            def setValue(self, value):
                self.progressBar.setValue(value)

            def setLabelText(self, text):
                self.statusLabel.setText(text)

            def addLogMessage(self, message):
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                self.logTextEdit.append(f"[{timestamp}] {message}")

                # Auto-scroll al fondo
                cursor = self.logTextEdit.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.logTextEdit.setTextCursor(cursor)

            def wasCanceled(self):
                return self.result() == QDialog.DialogCode.Rejected

        # Crea un thread per l'elaborazione in background
        class AudioVideoThread(QThread):
            progress = pyqtSignal(int, str)
            completed = pyqtSignal(str)
            error = pyqtSignal(str)
            detailed_log = pyqtSignal(str)

            def __init__(self, video_path, audio_path, output_path, align_speed, parent_window, chunk_size=10):
                super().__init__()
                self.video_path = video_path
                self.audio_path = audio_path
                self.output_path = output_path
                self.align_speed = align_speed
                self.parent_window = parent_window
                self.running = True
                self.chunk_size = chunk_size  # In secondi, per elaborazione a pezzi

                # Per statistiche
                self.start_time = None
                self.video_info = None
                self.audio_info = None

            def log(self, message):
                self.detailed_log.emit(message)
                logging.debug(message)

            def get_media_info(self, file_path):
                """Ottiene informazioni dettagliate sul file media"""
                try:
                    import json
                    # Usa ffprobe per ottenere informazioni sul file
                    ffprobe_cmd = [
                        'ffmpeg/bin/ffprobe',
                        '-v', 'error',
                        '-show_format',
                        '-show_streams',
                        '-print_format', 'json',
                        file_path
                    ]
                    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        return json.loads(result.stdout)
                    return None
                except Exception as e:
                    self.log(f"Errore nell'ottenere informazioni sul file: {e}")
                    return None

            def run(self):
                self.start_time = time.time()
                self.log(f"Inizio elaborazione - {time.strftime('%H:%M:%S')}")

                # Raccogli informazioni sui file
                self.video_info = self.get_media_info(self.video_path)
                self.audio_info = self.get_media_info(self.audio_path)

                if self.video_info:
                    self.log(f"Formato video: {self.video_info.get('format', {}).get('format_name', 'sconosciuto')}")
                    self.log(
                        f"Durata video: {self.video_info.get('format', {}).get('duration', 'sconosciuta')} secondi")
                    self.log(f"Bitrate video: {self.video_info.get('format', {}).get('bit_rate', 'sconosciuto')} bit/s")

                if self.audio_info:
                    self.log(f"Formato audio: {self.audio_info.get('format', {}).get('format_name', 'sconosciuto')}")
                    self.log(
                        f"Durata audio: {self.audio_info.get('format', {}).get('duration', 'sconosciuta')} secondi")
                    self.log(f"Bitrate audio: {self.audio_info.get('format', {}).get('bit_rate', 'sconosciuto')} bit/s")

                try:
                    if self.align_speed:
                        self.alignSpeedAndApplyAudio()
                    else:
                        self.applyAudioOnly()

                    if self.running:
                        elapsed_time = time.time() - self.start_time
                        self.log(f"Elaborazione completata in {elapsed_time:.1f} secondi")
                        self.completed.emit(self.output_path)
                except Exception as e:
                    if self.running:
                        import traceback
                        error_details = traceback.format_exc()
                        error_msg = f"Errore: {str(e)}\n\nDettagli: {error_details}"
                        self.log(error_msg)
                        self.error.emit(error_msg)

            def alignSpeedAndApplyAudio(self):
                video_clip = None
                audio_clip = None

                try:
                    # Primo step: analisi dei file
                    self.progress.emit(5, "Analisi dei file...")
                    self.log("Inizio caricamento video...")

                    # Utilizziamo librerie di basso livello per le informazioni
                    video_probe = self.get_media_info(self.video_path)
                    audio_probe = self.get_media_info(self.audio_path)

                    video_duration = float(video_probe.get('format', {}).get('duration', 0))
                    audio_duration = float(audio_probe.get('format', {}).get('duration', 0))

                    self.log(f"Durata video: {video_duration:.2f}s, durata audio: {audio_duration:.2f}s")

                    if video_duration <= 0 or audio_duration <= 0:
                        raise ValueError("Durata del video o dell'audio non valida")

                    # Calcola il fattore di velocità
                    speed_factor = round(video_duration / audio_duration, 2)
                    self.log(f"Fattore di velocità calcolato: {speed_factor}")

                    # Per file molto grandi, utilizziamo direttamente ffmpeg invece di moviepy
                    if os.path.getsize(self.video_path) > 500 * 1024 * 1024:  # > 500 MB
                        self.log("File di grandi dimensioni rilevato. Utilizzo elaborazione ottimizzata.")
                        self.progress.emit(20, "Elaborazione file di grandi dimensioni...")
                        return self.process_large_files(speed_factor)

                    # Per file più piccoli continua con moviepy
                    self.progress.emit(15, "Caricamento video...")
                    video_clip = VideoFileClip(self.video_path)
                    self.progress.emit(30, "Caricamento audio...")
                    audio_clip = AudioFileClip(self.audio_path)

                    self.log(f"File caricati con successo. Elaborazione in corso...")

                    # Checkpoint: usiamo la gestione della memoria
                    import gc
                    gc.collect()  # Forza la garbage collection

                    # Applica il cambio di velocità
                    self.progress.emit(40, f"Applicazione fattore velocità: {speed_factor}x...")
                    video_modified = video_clip.fx(vfx.speedx, speed_factor)

                    # Checkpoint
                    self.log("Fattore di velocità applicato, fase di unione audio...")
                    self.progress.emit(60, "Unione audio e video...")

                    # Applica l'audio
                    final_video = video_modified.set_audio(audio_clip)

                    # Checkpoint
                    self.log("Audio unito, preparazione al salvataggio...")
                    self.progress.emit(70, "Preparazione salvataggio...")

                    # Determina il codec audio e video
                    codec_video = "libx264"
                    codec_audio = "aac"

                    # Ottieni il framerate originale
                    fps = video_clip.fps

                    # Configurazioni per ridurre l'uso di memoria
                    write_options = {
                        'codec': codec_video,
                        'audio_codec': codec_audio,
                        'fps': fps,
                        'preset': 'ultrafast',
                        'threads': 4,
                        'logger': None,  # Disabilita il logging verboso
                        'ffmpeg_params': ['-crf', '23']  # Comprimi leggermente senza perdere qualità
                    }

                    # Fase critica: salvataggio
                    self.log("Inizio salvataggio video finale...")
                    self.progress.emit(80, "Salvataggio video finale...")

                    try:
                        # Monitoriamo lo stato durante il salvataggio
                        start_save = time.time()
                        final_video.write_videofile(self.output_path, **write_options,
                                                    progress_bar=False, verbose=False)
                        save_duration = time.time() - start_save
                        self.log(f"Salvataggio completato in {save_duration:.1f} secondi")
                        self.progress.emit(100, "Salvataggio completato")
                    except Exception as save_error:
                        self.log(f"Errore durante il salvataggio: {save_error}")
                        # Tenta un metodo alternativo
                        self.log("Tentativo alternativo con ffmpeg...")
                        self.progress.emit(85, "Tentativo alternativo di salvataggio...")
                        self.save_with_ffmpeg(video_modified, audio_clip)

                except Exception as e:
                    raise Exception(f"Errore nell'allineamento audio-video: {str(e)}")

                finally:
                    # Pulizia risorse
                    self.log("Pulizia risorse...")
                    if video_clip:
                        video_clip.close()
                    if audio_clip:
                        audio_clip.close()
                    import gc
                    gc.collect()  # Forza garbage collection

            def process_large_files(self, speed_factor):
                """Processa file di grandi dimensioni usando direttamente ffmpeg"""
                try:
                    self.progress.emit(30, "Elaborazione file grandi con ffmpeg...")
                    self.log("Utilizzo ffmpeg per file di grandi dimensioni")

                    # Crea un file temporaneo per il video con velocità modificata
                    temp_video = self.parent_window.get_temp_filepath(suffix='.mp4')

                    # Modifica la velocità del video con ffmpeg
                    ffmpeg_speed_cmd = [
                        'ffmpeg/bin/ffmpeg',
                        '-i', self.video_path,
                        '-filter_complex', f'[0:v]setpts={1 / speed_factor}*PTS[v]',
                        '-map', '[v]',
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-crf', '23',
                        '-y',
                        temp_video
                    ]

                    self.log("Esecuzione comando ffmpeg per la velocità...")
                    self.progress.emit(40, "Modifica velocità video...")
                    subprocess.run(ffmpeg_speed_cmd, capture_output=True)
                    self.log("Velocità video modificata")

                    # Aggiungi l'audio al video modificato
                    ffmpeg_audio_cmd = [
                        'ffmpeg/bin/ffmpeg',
                        '-i', temp_video,
                        '-i', self.audio_path,
                        '-map', '0:v',
                        '-map', '1:a',
                        '-c:v', 'copy',  # Non ricodificare il video
                        '-c:a', 'aac',
                        '-shortest',
                        '-y',
                        self.output_path
                    ]

                    self.log("Esecuzione comando ffmpeg per aggiungere audio...")
                    self.progress.emit(70, "Aggiunta audio...")
                    subprocess.run(ffmpeg_audio_cmd, capture_output=True)

                    # Rimuovi il file temporaneo
                    if os.path.exists(temp_video):
                        os.remove(temp_video)

                    self.progress.emit(100, "Elaborazione completata")
                    return True

                except Exception as e:
                    self.log(f"Errore nell'elaborazione con ffmpeg: {e}")
                    raise Exception(f"Errore nell'elaborazione di file grandi: {str(e)}")

            def save_with_ffmpeg(self, video_clip, audio_clip):
                """Salva il video usando ffmpeg direttamente"""
                try:
                    # Salva video e audio temporanei
                    temp_video = self.parent_window.get_temp_filepath(suffix='.mp4')
                    temp_audio = self.parent_window.get_temp_filepath(suffix='.aac')

                    # Salva solo il video senza audio
                    video_clip.without_audio().write_videofile(temp_video, codec='libx264',
                                                               audio=False, fps=video_clip.fps,
                                                               preset='ultrafast', verbose=False,
                                                               progress_bar=False)

                    # Salva l'audio separatamente
                    audio_clip.write_audiofile(temp_audio, codec='aac', verbose=False,
                                               progress_bar=False)

                    # Unisci video e audio con ffmpeg
                    ffmpeg_cmd = [
                        'ffmpeg/bin/ffmpeg',
                        '-i', temp_video,
                        '-i', temp_audio,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-map', '0:v',
                        '-map', '1:a',
                        '-shortest',
                        '-y',
                        self.output_path
                    ]

                    self.log("Unione finale con ffmpeg...")
                    self.progress.emit(90, "Unione finale...")
                    subprocess.run(ffmpeg_cmd, capture_output=True)

                    # Pulizia file temporanei
                    if os.path.exists(temp_video):
                        os.remove(temp_video)
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)

                    self.progress.emit(100, "Completato con metodo alternativo")
                    return True

                except Exception as e:
                    self.log(f"Errore nel salvataggio alternativo: {e}")
                    raise Exception(f"Fallimento anche con metodo alternativo: {str(e)}")

            def applyAudioOnly(self):
                """Applica solo l'audio al video esistente"""
                # Implementazione simile all'allineamento ma senza modificare la velocità
                try:
                    self.progress.emit(10, "Caricamento video...")

                    # Per file molto grandi, utilizziamo direttamente ffmpeg
                    if os.path.getsize(self.video_path) > 500 * 1024 * 1024:  # > 500 MB
                        self.log("File video grande rilevato, utilizzo ffmpeg diretto")
                        return self.apply_audio_with_ffmpeg()

                    video_clip = VideoFileClip(self.video_path)

                    self.progress.emit(30, "Caricamento audio...")
                    audio_clip = AudioFileClip(self.audio_path)

                    # Verifica e gestisci casi in cui la durata dell'audio è diversa dal video
                    video_duration = video_clip.duration
                    audio_duration = audio_clip.duration

                    self.log(f"Durata video: {video_duration:.2f}s, durata audio: {audio_duration:.2f}s")

                    if audio_duration > video_duration:
                        self.progress.emit(40, "Taglio audio per adattarlo al video...")
                        self.log(f"L'audio è più lungo del video. Taglio l'audio a {video_duration}s")
                        audio_clip = audio_clip.subclip(0, video_duration)
                    elif audio_duration < video_duration:
                        # Avvisiamo che l'audio è più corto
                        self.log(f"ATTENZIONE: L'audio è più corto del video di {video_duration - audio_duration:.2f}s")

                    # Applica l'audio
                    self.progress.emit(50, "Applicazione audio...")
                    final_video = video_clip.set_audio(audio_clip)

                    # Impostazioni di output ottimizzate
                    self.progress.emit(70, "Salvataggio video finale...")

                    try:
                        final_video.write_videofile(
                            self.output_path,
                            codec="libx264",
                            audio_codec="aac",
                            fps=video_clip.fps,
                            preset="ultrafast",
                            threads=4,
                            ffmpeg_params=['-crf', '23'],
                            logger=None,
                            verbose=False,
                            progress_bar=False
                        )
                        self.progress.emit(100, "Completato")
                    except Exception as save_error:
                        self.log(f"Errore durante il salvataggio: {save_error}")
                        self.progress.emit(85, "Tentativo alternativo...")
                        return self.save_with_ffmpeg(video_clip, audio_clip)

                except Exception as e:
                    self.log(f"Errore nell'applicazione dell'audio: {e}")
                    raise Exception(f"Errore nella sostituzione dell'audio: {str(e)}")
                finally:
                    # Pulizia risorse
                    import gc
                    gc.collect()

            def apply_audio_with_ffmpeg(self):
                """Applica l'audio al video usando direttamente ffmpeg"""
                try:
                    self.progress.emit(40, "Sostituzione audio con ffmpeg...")
                    self.log("Utilizzo ffmpeg per sostituire l'audio")

                    ffmpeg_cmd = [
                        'ffmpeg/bin/ffmpeg',
                        '-i', self.video_path,
                        '-i', self.audio_path,
                        '-map', '0:v',
                        '-map', '1:a',
                        '-c:v', 'copy',  # Copia il video senza ricodifica
                        '-c:a', 'aac',  # Codifica l'audio in AAC
                        '-shortest',  # Termina quando finisce lo stream più corto
                        '-y',  # Sovrascrivi se esiste
                        self.output_path
                    ]

                    self.log("Esecuzione comando ffmpeg...")
                    self.progress.emit(60, "Elaborazione in corso...")

                    # Esegui il comando ffmpeg
                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    # Leggi l'output per tenere traccia dell'avanzamento
                    while True:
                        line = process.stderr.readline()
                        if not line and process.poll() is not None:
                            break
                        if 'time=' in line:
                            try:
                                # Estrai il timestamp corrente
                                import re
                                time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                                if time_match:
                                    current_time = time_match.group(1)
                                    h, m, s = current_time.split(':')
                                    seconds = float(h) * 3600 + float(m) * 60 + float(s)

                                    # Calcola percentuale di completamento (approssimata)
                                    video_info = self.get_media_info(self.video_path)
                                    total_duration = float(video_info.get('format', {}).get('duration', 0))

                                    if total_duration > 0:
                                        progress = min(95, int((seconds / total_duration) * 90) + 60)
                                        self.progress.emit(progress, f"Elaborazione: {current_time}")
                            except Exception as ex:
                                self.log(f"Errore nel parsing dell'output ffmpeg: {ex}")

                    # Verifica il risultato
                    if process.returncode == 0:
                        self.log("Processo ffmpeg completato con successo")
                        self.progress.emit(100, "Elaborazione completata")
                        return True
                    else:
                        stderr = process.stderr.read()
                        self.log(f"Errore ffmpeg: {stderr}")
                        raise Exception(f"Errore nell'elaborazione ffmpeg: {stderr}")

                except Exception as e:
                    self.log(f"Errore nell'applicazione dell'audio con ffmpeg: {e}")
                    raise Exception(f"Errore nell'applicazione dell'audio: {str(e)}")

            def stop(self):
                self.running = False
                self.log("Richiesta interruzione processo...")

        # Crea il dialog personalizzato invece di QProgressDialog
        progress_dialog = CustomProgressDialog(self)

        # Crea thread per l'elaborazione
        self.audio_video_thread = AudioVideoThread(video_path, new_audio_path, output_path, align_audio_video, self)

        # Collega i segnali - versione corretta
        self.audio_video_thread.progress.connect(
            lambda value, text: (progress_dialog.setValue(value), progress_dialog.setLabelText(text))
        )

        # Passa il dialog come parametro ai metodi di callback
        self.audio_video_thread.completed.connect(
            lambda path: self.onAudioVideoCompleted(path, progress_dialog)
        )
        self.audio_video_thread.error.connect(
            lambda message: self.onAudioVideoError(message, progress_dialog)
        )
        self.audio_video_thread.detailed_log.connect(progress_dialog.addLogMessage)

        # Avvia il thread
        self.audio_video_thread.start()

        # Mostra il dialog
        result = progress_dialog.exec()

        # Se il dialog viene chiuso, interrompi il thread
        if result == QDialog.DialogCode.Rejected:
            self.audio_video_thread.stop()

    # Modifica i metodi di callback per accettare il dialog come parametro
    def onAudioVideoCompleted(self, output_path, dialog=None):
        """Gestisce il completamento dell'elaborazione audio-video"""
        if dialog:
            dialog.accept()
        QMessageBox.information(self, "Successo", f"Il nuovo audio è stato applicato con successo:\n{output_path}")
        self.loadVideoOutput(output_path)

    def onAudioVideoError(self, error_message, dialog=None):
        """Gestisce gli errori durante l'elaborazione audio-video"""
        if dialog:
            dialog.accept()
        QMessageBox.critical(self, "Errore",
                             f"Si è verificato un errore durante l'elaborazione audio-video:\n{error_message}")
    def updateLogInfo(self, message):
        """Aggiorna il log dettagliato"""
        if hasattr(self, 'logTextEdit'):
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            self.logTextEdit.append(f"[{timestamp}] {message}")

            # Auto-scroll al fondo
            cursor = self.logTextEdit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.logTextEdit.setTextCursor(cursor)

    def updateAudioVideoProgress(self, value, message):
        """Aggiorna il dialog di progresso con lo stato attuale"""
        if hasattr(self, 'progressDialog') and self.progressDialog is not None:
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(message)

    def cutVideo(self):
        media_path = self.videoPathLineEdit
        if not media_path:
            self.show_status_message("Per favore, seleziona un file prima di tagliarlo.", error=True)
            return

        if not (media_path.lower().endswith(('.mp4', '.mov', '.avi', '.mp3', '.wav', '.aac', '.ogg', '.flac'))):
            self.show_status_message("Formato file non supportato per il taglio.", error=True)
            return

        is_audio = media_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac'))
        start_time = self.currentPosition / 1000.0

        base_name = os.path.splitext(os.path.basename(media_path))[0]
        directory = os.path.dirname(media_path)
        ext = '.mp3' if is_audio else '.mp4'
        output_path1 = os.path.join(directory, f"{base_name}_part1{ext}")
        output_path2 = os.path.join(directory, f"{base_name}_part2{ext}")

        thread = VideoCuttingThread(media_path, start_time, output_path1, output_path2)
        self.start_task(thread, self.onCutCompleted, self.onCutError, self.update_status_progress)

    def onCutCompleted(self, output_path):
        self.show_status_message(f"File tagliato e salvato con successo.")
        self.loadVideoOutput(output_path)

    def onCutError(self, error_message):
        self.show_status_message(f"Errore durante il taglio: {error_message}", error=True)

    def positionChanged(self, position):
        self.videoSlider.setValue(position)
        self.currentPosition = position  # Aggiorna la posizione corrente
        self.updateTimeCode(position)

    # Slot per aggiornare il range massimo dello slider in base alla durata del video
    def durationChanged(self, duration):
        self.videoSlider.setRange(0, duration)
        self.updateDuration(duration)

    # Slot per aggiornare la posizione dello slider in base alla posizione corrente del video

    # Slot per cambiare la posizione del video quando lo slider viene mosso
    def setPosition(self, position):
        self.player.setPosition(position)

    def applyDarkMode(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #dcdcdc;
            }
            QLineEdit {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #555555;
                border: 1px solid #666666;
                border-radius: 2px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #777777;
            }
            QLabel {
                color: #cccccc;
            }
            QFileDialog {
                background-color: #444444;
            }
            QMessageBox {
                background-color: #444444;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        file_urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if file_urls:

            self.videoPathLineEdit = file_urls[0]  # Aggiorna il percorso del video memorizzato
            self.loadVideo(self.videoPathLineEdit, os.path.basename(file_urls[0]))

    def browseVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video/Audio Files (*avi *.mp4 *.mov *.mp3 *.wav *.aac *.ogg *.flac *.mkv)")
        if fileName:
           self.loadVideo(fileName)

    def browseVideoOutput(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video/Audio Files (*.avi *.mp4 *.mov *.mp3 *.wav *.aac *.ogg *.flac *.mkv)")
        if fileName:
           self.loadVideoOutput(fileName)

    def browseAudioFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona File Audio", "", "Audio Files (*.mp3 *.wav *.aac *.ogg *.flac)")
        if fileName:
            self.loadVideo(fileName)

    def updateRecentFiles(self, newFile):
        if newFile in self.recentFiles:
            self.recentFiles.remove(newFile)

        self.recentFiles.insert(0, newFile)

        if len(self.recentFiles) > 15:  # Limita la lista ai 15 più recenti
            self.recentFiles = self.recentFiles[:15]

        # Salva la lista aggiornata nelle impostazioni
        settings = QSettings("Genius", "GeniusAI")
        settings.setValue("recentFiles", self.recentFiles)

        self.updateRecentFilesMenu()

    def updateRecentFilesMenu(self):
        self.recentMenu.clear()
        for file in self.recentFiles:
            action = QAction(os.path.basename(file), self)
            action.triggered.connect(lambda checked, f=file: self.openRecentFile(f))
            self.recentMenu.addAction(action)

    def updateRecentProjects(self, newProject):
        if newProject in self.recentProjects:
            self.recentProjects.remove(newProject)

        self.recentProjects.insert(0, newProject)

        if len(self.recentProjects) > 15:
            self.recentProjects = self.recentProjects[:15]

        settings = QSettings("Genius", "GeniusAI")
        settings.setValue("recentProjects", self.recentProjects)

        self.updateRecentProjectsMenu()

    def updateRecentProjectsMenu(self):
        self.recentProjectsMenu.clear()
        for project in self.recentProjects:
            project_name = os.path.basename(os.path.dirname(project))
            action = QAction(project_name, self)
            action.triggered.connect(lambda checked, p=project: self.openRecentProject(p))
            self.recentProjectsMenu.addAction(action)

    def loadRecentProjects(self):
        """Carica la lista dei progetti recenti da QSettings."""
        settings = QSettings("Genius", "GeniusAI")
        self.recentProjects = settings.value("recentProjects", [], type=list)
        # Rimuovi i progetti che non esistono più
        self.recentProjects = [p for p in self.recentProjects if os.path.exists(p)]

    def openRecentProject(self, filePath):
        self.load_project(filePath)

    def loadRecentFiles(self):
        """Carica la lista dei file recenti da QSettings."""
        settings = QSettings("Genius", "GeniusAI")
        self.recentFiles = settings.value("recentFiles", [], type=list)
        # Rimuovi i file che non esistono più
        self.recentFiles = [f for f in self.recentFiles if os.path.exists(f)]


    def openRecentFile(self, filePath):
        self.videoPathLineEdit = filePath
        self.player.setSource(QUrl.fromLocalFile(filePath))
        self.fileNameLabel.setText(os.path.basename(filePath))

    def playVideo(self):
        self.player.play()

    def pauseVideo(self):
        self.player.pause()

    def adattaVelocitaVideoAAudio(self, video_path, new_audio_path, output_path):
        try:
            # Log dei percorsi dei file
            logging.debug(f"Percorso video: {video_path}")
            logging.debug(f"Percorso nuovo audio: {new_audio_path}")
            logging.debug(f"Percorso output: {output_path}")

            # Carica il nuovo file audio e calcola la sua durata
            new_audio = AudioFileClip(new_audio_path)
            durata_audio = new_audio.duration
            logging.debug(f"Durata audio: {durata_audio} secondi")

            # Carica il video (senza audio) e calcola la sua durata
            video_clip = VideoFileClip(video_path)
            durata_video = video_clip.duration
            logging.debug(f"Durata video: {durata_video} secondi")

            # Calcola il fattore di velocità
            fattore_velocita = round(durata_video / durata_audio, 1)
            logging.debug(f"Fattore di velocità: {fattore_velocita}")

            # Modifica la velocità del video
            video_modificato = video_clip.fx(vfx.speedx, fattore_velocita)

            # Imposta il nuovo audio sul video modificato
            final_video = video_modificato.set_audio(new_audio)

            # Scrivi il video finale mantenendo lo stesso frame rate del video originale
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=video_clip.fps)
            logging.debug('Video elaborato con successo.')

        except Exception as e:
            logging.error(f"Errore durante l'adattamento della velocità del video: {e}")
    def stopVideo(self):
        self.player.stop()

    def updatePlayButtonIcon(self, state):
        if self.reverseTimer.isActive():
            self.playButton.setIcon(QIcon(get_resource("pausa.png")))
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(QIcon(get_resource("pausa.png")))
        else:
            self.playButton.setIcon(QIcon(get_resource("play.png")))

    def keyPressEvent(self, event):
        """
        Gestisce gli eventi di pressione dei tasti a livello di finestra principale
        per controllare la riproduzione video con le frecce.
        """
        key = event.key()

        # Non intercettare gli eventi quando un campo di testo ha il focus
        if QApplication.focusWidget() and isinstance(QApplication.focusWidget(), (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Left:
            self.rewind5Seconds()
            event.accept()
        elif key == Qt.Key.Key_Right:
            self.forward5Seconds()
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, source, event):
        if source is self.videoOverlay and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.add_video_note()
                return True
        return super().eventFilter(source, event)

    def add_video_note(self):
        if not self.videoPathLineEdit:
            self.show_status_message("Carica un video prima di aggiungere una nota.", error=True)
            return

        self.player.pause()
        position = self.player.position()
        timecode = self.formatTimecode(position)

        note_text, ok = MultiLineInputDialog.getText(self, "Aggiungi Nota", f"Inserisci la nota per il timecode {timecode}:")

        if ok and note_text.strip():
            note_item = f"{timecode} - {note_text.strip()}"
            list_item = QListWidgetItem(note_item)
            list_item.setData(Qt.ItemDataRole.UserRole, position) # Store position in ms
            self.videoNotesListWidget.addItem(list_item)
            self.save_video_notes_to_json()

    def seek_to_note_timecode(self, item):
        position = item.data(Qt.ItemDataRole.UserRole)
        if position is not None:
            self.player.setPosition(position)

    def save_video_notes_to_json(self):
        if not self.videoPathLineEdit:
            return

        notes = []
        for i in range(self.videoNotesListWidget.count()):
            item = self.videoNotesListWidget.item(i)
            position = item.data(Qt.ItemDataRole.UserRole)
            text = item.text().split(" - ", 1)[1]
            notes.append({"position": position, "text": text})

        self._update_json_file(self.videoPathLineEdit, {"video_notes": notes})

    def load_video_notes_from_json(self, data):
        self.videoNotesListWidget.clear()
        notes = data.get("video_notes", [])
        for note in notes:
            position = note.get("position")
            text = note.get("text")
            if position is not None and text:
                timecode = self.formatTimecode(position)
                list_item = QListWidgetItem(f"{timecode} - {text}")
                list_item.setData(Qt.ItemDataRole.UserRole, position)
                self.videoNotesListWidget.addItem(list_item)

    def edit_video_note(self):
        selected_item = self.videoNotesListWidget.currentItem()
        if not selected_item:
            self.show_status_message("Seleziona una nota da modificare.", error=True)
            return

        position = selected_item.data(Qt.ItemDataRole.UserRole)
        timecode = self.formatTimecode(position)
        current_text = selected_item.text().split(" - ", 1)[1]

        new_text, ok = MultiLineInputDialog.getText(self, "Modifica Nota", "Nuovo testo della nota:", text=current_text)

        if ok and new_text.strip():
            selected_item.setText(f"{timecode} - {new_text.strip()}")
            self.save_video_notes_to_json()

    def delete_video_note(self):
        selected_item = self.videoNotesListWidget.currentItem()
        if not selected_item:
            self.show_status_message("Seleziona una nota da cancellare.", error=True)
            return

        reply = QMessageBox.question(self, "Conferma Cancellazione",
                                     f"Sei sicuro di voler cancellare la nota?\n\n'{selected_item.text()}'",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.videoNotesListWidget.takeItem(self.videoNotesListWidget.row(selected_item))
            self.save_video_notes_to_json()

    def updatePlayButtonIconOutput(self, state):
        if self.reverseTimerOutput.isActive():
            self.playButtonOutput.setIcon(QIcon(get_resource("pausa.png")))
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.playButtonOutput.setIcon(QIcon(get_resource("pausa.png")))
        else:
            self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))

    # --- PROJECT MANAGEMENT METHODS ---

    def _clear_workspace(self):
        """
        Pulisce completamente lo stato dell'applicazione per prepararsi a un nuovo progetto.
        """
        # 1. Pulisci i video player e i percorsi associati
        self.releaseSourceVideo()
        self.releaseOutputVideo()

        # 2. Pulisci le aree di testo
        self.transcriptionTextArea.clear()
        self.audioAiTextArea.clear()
        self.summaryTextArea.clear()

        # 3. Resetta lo stato interno delle trascrizioni e dei riassunti
        self.transcription_original = ""
        self.transcription_corrected = ""
        self.summaries = {}
        self.active_summary_type = None
        self.summary_text = ""
        self.summary_generated = ""
        self.summary_generated_integrated = ""
        self.original_audio_ai_html = ""
        self.transcriptionViewToggle.setChecked(False)
        self.transcriptionViewToggle.setEnabled(False)
        self.integrazioneToggle.setChecked(False)
        self.integrazioneToggle.setEnabled(False)

        # 4. Resetta i percorsi e lo stato del progetto
        self.current_project_path = None
        self.current_video_path = None
        self.current_audio_path = None

        # 5. Pulisci i dock informativi
        self.infoDock.clear_info()
        self.projectDock.clear_project()

        self.show_status_message("Workspace pulito. Pronto per un nuovo progetto.")

    def create_new_project(self):
        project_name, ok = QInputDialog.getText(self, "Nuovo Progetto", "Inserisci il nome del nuovo progetto:")
        if not ok or not project_name.strip():
            # L'utente ha annullato o non ha inserito un nome
            return

        # Chiedi all'utente di scegliere una cartella di destinazione
        destination_folder = QFileDialog.getExistingDirectory(self, "Scegli la cartella di destinazione del progetto", self.project_manager.base_dir)
        if not destination_folder:
            # L'utente ha annullato la selezione della cartella
            return

        # Pulisci l'area di lavoro solo dopo che l'utente ha confermato tutto
        self._clear_workspace()

        # Crea il progetto nella cartella scelta
        project_path, gnai_path = self.project_manager.create_project(project_name.strip(), base_dir=destination_folder)

        if project_path:
            self.show_status_message(f"Progetto '{os.path.basename(project_path)}' creato con successo in '{destination_folder}'.")
            self.load_project(gnai_path)
        else:
            self.show_status_message(f"Errore: Il progetto '{project_name.strip()}' esiste già in questa cartella.", error=True)

    def open_project(self):
        gnai_path, _ = QFileDialog.getOpenFileName(self, "Apri Progetto", self.project_manager.base_dir, "GeniusAI Project Files (*.gnai)")
        if gnai_path:
            self._clear_workspace()
            self.load_project(gnai_path)

    def load_project(self, gnai_path):
        project_data, error = self.project_manager.load_project(gnai_path)
        if error:
            self.show_status_message(f"Errore caricamento progetto: {error}", error=True)
            return

        self.current_project_path = os.path.dirname(gnai_path)
        self.folderPathLineEdit.setText(self.current_project_path)
        self.projectDock.load_project_data(project_data, self.current_project_path, gnai_path)
        self.show_status_message(f"Progetto '{project_data.get('projectName')}' caricato.")
        self.updateRecentProjects(gnai_path)
        if not self.projectDock.isVisible():
            self.projectDock.show()

    def load_project_clip(self, video_path, metadata_filename):
        if os.path.exists(video_path):
            # Disconnect the signal to prevent unintended reloads
            try:
                self.projectDock.project_clips_folder_changed.disconnect(self.sync_project_clips_folder)
            except TypeError:
                pass  # Signal was not connected

            self.loadVideo(video_path)

            # Reconnect the signal after loading
            self.projectDock.project_clips_folder_changed.connect(self.sync_project_clips_folder)

            self.show_status_message(f"Clip '{os.path.basename(video_path)}' caricata.")
        else:
            self.show_status_message(f"File video non trovato: {video_path}", error=True)

    def merge_project_clips(self):
        if not self.projectDock.project_data:
            self.show_status_message("Nessun progetto caricato o nessuna clip nel progetto.", error=True)
            return

        clips = self.projectDock.project_data.get("clips", [])
        if not clips:
            self.show_status_message("Nessuna clip da unire nel progetto.", error=True)
            return

        clips_dir = os.path.join(self.current_project_path, "clips")
        clips_paths = sorted([os.path.join(clips_dir, c["clip_filename"]) for c in clips])

        # Proponi un nome di default per il file unito
        project_name = self.projectDock.project_data.get("projectName", "merged_video")
        default_save_path = os.path.join(self.current_project_path, f"{project_name}_merged.mp4")

        output_path, _ = QFileDialog.getSaveFileName(self, "Salva Video Unito", default_save_path, "MP4 Video Files (*.mp4)")
        if not output_path:
            return

        thread = ProjectClipsMergeThread(clips_paths, output_path, self)
        self.start_task(thread, self.on_merge_clips_completed, self.on_merge_clips_error, self.update_status_progress)

    def on_merge_clips_completed(self, output_path):
        self.show_status_message(f"Clip unite con successo. Video salvato in {os.path.basename(output_path)}")
        self.loadVideoOutput(output_path)

    def on_merge_clips_error(self, error_message):
        self.show_status_message(f"Errore durante l'unione delle clip: {error_message}", error=True)

    def sync_project_clips_folder(self):
        """
        Sincronizza il file .gnai con la cartella 'clips', aggiornando lo stato dei file.
        """
        if not self.current_project_path or not self.projectDock.gnai_path:
            return

        clips_dir = os.path.join(self.current_project_path, "clips")
        if not os.path.isdir(clips_dir):
            os.makedirs(clips_dir) # Crea la cartella se non esiste

        try:
            disk_files = {f for f in os.listdir(clips_dir) if os.path.isfile(os.path.join(clips_dir, f)) and f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))}

            project_data, _ = self.project_manager.load_project(self.projectDock.gnai_path)
            if not project_data:
                return

            registered_clips_dict = {c['clip_filename']: c for c in project_data.get('clips', [])}
            now = datetime.datetime.now().isoformat()
            changes_made = False

            # Controlla lo stato dei file registrati
            for filename, clip_data in registered_clips_dict.items():
                if filename in disk_files:
                    # Il file esiste, aggiorna lo stato a 'online' se necessario
                    if clip_data.get('status') != 'online':
                        clip_data['status'] = 'online'
                        changes_made = True
                    clip_data['last_seen'] = now
                    disk_files.remove(filename) # Rimuovi dalla lista dei file non tracciati
                else:
                    # Il file non esiste più, aggiorna lo stato a 'offline'
                    if clip_data.get('status') != 'offline':
                        clip_data['status'] = 'offline'
                        changes_made = True

            # Aggiungi nuovi file trovati sul disco
            if disk_files:
                self.show_status_message(f"Rilevati {len(disk_files)} nuovi file. Aggiunta in corso...")
                for filename in disk_files:
                    clip_path = os.path.join(clips_dir, filename)
                    try:
                        clip_info = VideoFileClip(clip_path)
                        duration = clip_info.duration
                        clip_info.close()
                        size = os.path.getsize(clip_path)
                        creation_date = datetime.datetime.fromtimestamp(os.path.getctime(clip_path)).isoformat()

                        new_clip_data = {
                            "clip_filename": filename,
                            "metadata_filename": os.path.splitext(filename)[0] + ".json",
                            "addedAt": now,
                            "duration": duration,
                            "size": size,
                            "creation_date": creation_date,
                            "status": "new",
                            "last_seen": now
                        }
                        project_data["clips"].append(new_clip_data)
                        changes_made = True
                    except Exception as e:
                        logging.error(f"Impossibile aggiungere la nuova clip {filename}: {e}")

            # Salva e ricarica se ci sono state modifiche
            if changes_made:
                self.project_manager.save_project(self.projectDock.gnai_path, project_data)
                self.load_project(self.projectDock.gnai_path)
                self.show_status_message("Progetto sincronizzato con la cartella clips.")
            else:
                # Ricarica comunque per coerenza, nel caso qualcosa sia cambiato esternamente
                self.load_project(self.projectDock.gnai_path)

        except Exception as e:
            logging.error(f"Errore durante la sincronizzazione della cartella clips: {e}")
            self.show_status_message("Errore durante la sincronizzazione della cartella.", error=True)

    def delete_project_clip(self, clip_filename):
        """
        Chiede all'utente come gestire l'eliminazione di una clip: solo dal progetto
        o anche dal disco.
        """
        if not self.current_project_path:
            self.show_status_message("Nessun progetto attivo.", error=True)
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Rimuovi Clip")
        msg_box.setText(f"Cosa vuoi fare con la clip '{clip_filename}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)

        remove_button = msg_box.addButton("Rimuovi solo dal Progetto", QMessageBox.ButtonRole.ActionRole)
        delete_button = msg_box.addButton("Elimina da Progetto e Disco", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = msg_box.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == remove_button:
            # Rimuovi solo dal JSON
            success, message = self.project_manager.remove_clip_from_project(self.projectDock.gnai_path, clip_filename)
            if success:
                self.load_project(self.projectDock.gnai_path)
                self.show_status_message(f"Clip '{clip_filename}' rimossa dal progetto.")
            else:
                self.show_status_message(f"Errore: {message}", error=True)

        elif msg_box.clickedButton() == delete_button:
            # Rimuovi dal JSON e dal disco
            clip_path = os.path.join(self.current_project_path, "clips", clip_filename)

            # Rimuovi dal JSON
            success, message = self.project_manager.remove_clip_from_project(self.projectDock.gnai_path, clip_filename)
            if not success:
                self.show_status_message(f"Errore nella rimozione dal progetto: {message}", error=True)
                return

            # Rimuovi dal disco
            try:
                if os.path.exists(clip_path):
                    os.remove(clip_path)
                # Rimuovi anche il JSON associato, se esiste
                json_path = os.path.splitext(clip_path)[0] + ".json"
                if os.path.exists(json_path):
                    os.remove(json_path)

                self.load_project(self.projectDock.gnai_path)
                self.show_status_message(f"Clip '{clip_filename}' eliminata dal progetto e dal disco.")
            except Exception as e:
                self.show_status_message(f"Errore durante l'eliminazione del file: {e}", error=True)
                # Se l'eliminazione del file fallisce, è meglio ricaricare lo stato per coerenza
                self.load_project(self.projectDock.gnai_path)

    def rename_project_clip(self, old_filename, new_filename):
        """Rinomina una clip nel progetto, aggiornando il filesystem e il file .gnai."""
        if not self.current_project_path or not self.projectDock.gnai_path:
            self.show_status_message("Nessun progetto attivo.", error=True)
            return

        clips_dir = os.path.join(self.current_project_path, "clips")

        old_video_path = os.path.join(clips_dir, old_filename)
        new_video_path = os.path.join(clips_dir, new_filename)

        old_json_path = os.path.splitext(old_video_path)[0] + ".json"
        new_json_path = os.path.splitext(new_video_path)[0] + ".json"

        # Controlla se il nuovo nome file esiste già
        if os.path.exists(new_video_path):
            self.show_status_message(f"Un file con nome '{new_filename}' esiste già.", error=True)
            return

        try:
            # 1. Rinomina il file video
            if os.path.exists(old_video_path):
                os.rename(old_video_path, new_video_path)

            # 2. Rinomina il file JSON associato
            if os.path.exists(old_json_path):
                os.rename(old_json_path, new_json_path)

            # 3. Aggiorna il file di progetto .gnai
            success, message = self.project_manager.rename_clip_in_project(
                self.projectDock.gnai_path, old_filename, new_filename
            )
            if not success:
                # Se l'aggiornamento del .gnai fallisce, tenta di ripristinare i nomi dei file
                self.show_status_message(f"Errore nell'aggiornamento del progetto: {message}", error=True)
                if os.path.exists(new_video_path):
                    os.rename(new_video_path, old_video_path)
                if os.path.exists(new_json_path):
                    os.rename(new_json_path, old_json_path)
                return

            # 4. Ricarica il progetto per aggiornare la UI
            self.load_project(self.projectDock.gnai_path)
            self.show_status_message(f"Clip '{old_filename}' rinominata in '{new_filename}'.")

        except Exception as e:
            self.show_status_message(f"Errore durante la rinomina del file: {e}", error=True)
            # Tenta di ripristinare se qualcosa va storto
            if os.path.exists(new_video_path) and not os.path.exists(old_video_path):
                 os.rename(new_video_path, old_video_path)
            if os.path.exists(new_json_path) and not os.path.exists(old_json_path):
                 os.rename(new_json_path, old_json_path)

    def relink_project_clip(self, old_filename, new_filepath):
        """Gestisce il ricollegamento di una clip offline."""
        if not self.projectDock.gnai_path:
            self.show_status_message("Nessun progetto attivo.", error=True)
            return

        clips_dir = os.path.join(self.current_project_path, "clips")
        new_filename = os.path.basename(new_filepath)
        dest_path = os.path.join(clips_dir, new_filename)

        # Copia il nuovo file nella cartella clips del progetto
        try:
            shutil.copy2(new_filepath, dest_path)
        except Exception as e:
            self.show_status_message(f"Errore durante la copia del file: {e}", error=True)
            return

        # Aggiorna il file .gnai usando il ProjectManager
        success, message = self.project_manager.relink_clip(
            self.projectDock.gnai_path, old_filename, dest_path
        )

        if success:
            self.load_project(self.projectDock.gnai_path) # Ricarica per aggiornare la UI
            self.show_status_message(f"Clip '{old_filename}' ricollegata a '{new_filename}'.")
        else:
            self.show_status_message(f"Errore nel ricollegamento: {message}", error=True)
            # Se il ricollegamento fallisce, rimuovi il file copiato per pulizia
            if os.path.exists(dest_path):
                os.remove(dest_path)

    def open_project_folder(self):
        """Apre la cartella del progetto corrente nel file explorer di sistema."""
        if self.current_project_path and os.path.isdir(self.current_project_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_project_path))
            self.show_status_message(f"Apertura della cartella: {self.current_project_path}")
        else:
            self.show_status_message("Nessuna cartella di progetto valida da aprire.", error=True)

    def save_project(self):
        """Salva lo stato corrente del progetto."""
        if not self.current_project_path or not self.projectDock.gnai_path:
            self.show_status_message("Nessun progetto attivo da salvare.", error=True)
            return

        # Assicurati che i dati del progetto nel dock siano aggiornati
        # (Questo potrebbe non essere necessario se i dati sono sempre coerenti)
        current_data = self.projectDock.project_data
        if not current_data:
            self.show_status_message("Dati del progetto non validi.", error=True)
            return

        success, message = self.project_manager.save_project(self.projectDock.gnai_path, current_data)
        if success:
            self.show_status_message("Progetto salvato con successo.")
        else:
            self.show_status_message(f"Errore nel salvataggio del progetto: {message}", error=True)

    def get_temp_filepath(self, suffix="", prefix="tmp_"):
        """
        Genera un percorso per un file temporaneo, all'interno della cartella
        temp del progetto se un progetto è attivo.
        """
        if self.current_project_path:
            temp_dir = os.path.join(self.current_project_path, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
            os.close(fd)
            return path
        else:
            fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(fd)
            return path

    def get_temp_dir(self, prefix="tmp_"):
        """
        Genera un percorso per una directory temporanea, all'interno della cartella
        temp del progetto se un progetto è attivo.
        """
        if self.current_project_path:
            temp_dir = os.path.join(self.current_project_path, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            return tempfile.mkdtemp(prefix=prefix, dir=temp_dir)
        else:
            return tempfile.mkdtemp(prefix=prefix)

    def openAddMediaDialog(self):
        if not self.videoPathLineEdit:
            self.show_status_message("Please load a video in the Input Player first.", error=True)
            return

        dialog = AddMediaDialog(parent=self)
        dialog.media_added.connect(self.handle_media_added)
        dialog.exec()

    def handle_media_added(self, media_data):
        output_path = self.get_temp_filepath(suffix=".mp4", prefix=f"{media_data['type']}_overlay_")

        # Determine start time: use first bookmark or current position
        if self.videoSlider.bookmarks:
            start_time = sorted(self.videoSlider.bookmarks)[0][0] / 1000.0
            self.show_status_message(f"Adding overlay at start of bookmark: {start_time:.2f}s")
        else:
            start_time = self.player.position() / 1000.0
            self.show_status_message(f"Adding overlay at current position: {start_time:.2f}s")

        thread = MediaOverlayThread(
            base_video_path=self.videoPathLineEdit,
            media_data=media_data,
            output_path=output_path,
            start_time=start_time,
            parent=self
        )

        self.start_task(
            thread,
            on_complete=self.on_overlay_completed,
            on_error=self.on_overlay_error,
            on_progress=self.update_status_progress
        )

    def on_overlay_completed(self, output_path):
        self.show_status_message("Media overlay applied successfully.")
        self.loadVideoOutput(output_path)

    def on_overlay_error(self, error_message):
        self.show_status_message(f"Error applying media overlay: {error_message}", error=True)


def get_application_path():
    """Determina il percorso base dell'applicazione, sia in modalità di sviluppo che compilata"""
    if getattr(sys, 'frozen', False):
        # Se l'app è compilata con PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # In modalità di sviluppo
        return os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Specifica la cartella delle immagini
    base_path = get_application_path()
    image_folder = os.path.join(base_path, "res", "splash_images")
    print(image_folder)
    # Crea la splash screen con un'immagine casuale dalla cartella
    splash = SplashScreen(image_folder)
    splash.show()

    splash.showMessage("Caricamento risorse...")
    time.sleep(1)  # Simula un ritardo

    splash.showMessage("Inizializzazione interfaccia...")
    time.sleep(1)  # Simula un altro ritardo

    window = VideoAudioManager()

    window.show()

    splash.finish(window)

    sys.exit(app.exec())