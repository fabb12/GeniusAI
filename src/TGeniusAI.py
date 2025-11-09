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
import torch
import base64
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Librerie PyQt6
from PyQt6.QtCore import (Qt, QUrl, QEvent, QTimer, QPoint, QTime, QSettings, QBuffer, QIODevice)
from PyQt6.QtGui import (QIcon, QAction, QDesktopServices, QImage, QPixmap, QFont, QColor, QTextCharFormat, QTextCursor, QImage, QTextDocument)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QRadioButton, QLineEdit,
    QHBoxLayout, QGroupBox, QComboBox, QSpinBox, QFileDialog,
    QMessageBox, QSizePolicy, QProgressDialog, QToolBar, QSlider,
    QProgressBar, QTabWidget, QDialog,QTextEdit, QInputDialog, QDoubleSpinBox, QFrame,
    QStatusBar, QListWidget, QListWidgetItem, QMenu, QButtonGroup, QDialogButtonBox
)

# PyQtGraph (docking)
from pyqtgraph.dockarea.DockArea import DockArea

from moviepy.editor import (
    ImageClip, CompositeVideoClip, concatenate_audioclips,
    concatenate_videoclips, VideoFileClip, AudioFileClip, vfx, TextClip, ImageSequenceClip
)
from moviepy.audio.AudioClip import CompositeAudioClip, AudioArrayClip
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import cv2

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
from src.services.WhisperTranscript import WhisperTranscriptionThread
from src.services.AudioGenerationREST import AudioGenerationThread
from src.services.VideoCutting import VideoCuttingThread
from src.recorder.ScreenRecorder import ScreenRecorder
from src.managers.SettingsManager import DockSettingsManager
from src.managers.UIManager import UIManager
from src.managers.PlayerManager import PlayerManager
from src.managers.ActionManager import ActionManager
from src.managers.Settings import SettingsDialog
from src.services.PptxGeneration import PptxGeneration
from src.ui.PptxDialog import PptxDialog
from src.ui.ExportDialog import ExportDialog
from src.services.ProcessTextAI import ProcessTextAI
from src.ui.SplashScreen import SplashScreen
from src.services.ShareVideo import VideoSharingManager
from src.ui.MonitorPreview import MonitorPreview
from src.managers.StreamToLogger import setup_logging
from src.services.FrameExtractor import FrameExtractor
from src.services.OperationalGuideThread import OperationalGuideThread
from src.services.VideoCropping import CropThread
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from src.ui.CropDialog import CropDialog
from src.ui.FrameEditorDialog import FrameEditorDialog
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
from src.services.SilenceRemover import SilenceRemoverThread
from src.managers.ProjectManager import ProjectManager
from src.managers.BookmarkManager import BookmarkManager
from src.ui.ProjectDock import ProjectDock
from src.ui.ChatDock import ChatDock
from src.services.BatchTranscription import BatchTranscriptionThread
from src.services.VideoCompositing import VideoCompositingThread
from src.services.utils import remove_timestamps_from_html, generate_unique_filename
from src.services.Translator import TranslationService
from src.services.TranslationThread import TranslationThread
import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import RGBColor
from fpdf import FPDF
from markdownify import markdownify
import io


class ProjectClipsMergeThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, clips_paths, output_path, parent=None):
        super().__init__(parent)
        self.clips_paths = clips_paths
        self.output_path = generate_unique_filename(output_path)
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
        self.output_path = generate_unique_filename(output_path)
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
                draw.text((10 - left, 10 - top), text, font=font, fill=self.media_data['color'])

                # Convert Pillow image to moviepy clip
                overlay_clip = ImageClip(np.array(img))
            elif media_type == 'image':
                self.progress.emit(30, "Creating image overlay...")
                overlay_clip = (ImageClip(self.media_data['path'])
                                .resize(width=self.media_data['size'][0], height=self.media_data['size'][1]))

            elif media_type == 'gif':
                self.progress.emit(30, "Creating GIF overlay...")
                gif_path = self.media_data['path']

                # Use Pillow to extract frames from the GIF, which is more robust than relying on FFMPEG
                with Image.open(gif_path) as img:
                    frames = []
                    try:
                        while True:
                            # Convert frame to RGBA to handle transparency correctly
                            frames.append(np.array(img.convert('RGBA')))
                            img.seek(img.tell() + 1)
                    except EOFError:
                        pass  # Reached the end of the frames

                    # Get the duration of each frame from GIF metadata (in ms)
                    frame_duration_ms = img.info.get('duration', 100)
                    fps = 1000 / frame_duration_ms if frame_duration_ms > 0 else 10 # Default to 10 FPS if duration is 0

                # Create the clip from the sequence of frames, preserving transparency
                overlay_clip = (ImageSequenceClip(frames, fps=fps, with_mask=True)
                                .resize(width=self.media_data['size'][0], height=self.media_data['size'][1]))

                # Loop or trim the clip to match the desired duration
                if overlay_clip.duration > duration:
                    overlay_clip = overlay_clip.subclip(0, duration)
                else:
                    overlay_clip = overlay_clip.loop(duration=duration)

            if not overlay_clip:
                raise ValueError("Unsupported media type or error creating overlay.")

            if not self.running: return

            position = (self.media_data['position']['x'], self.media_data['position']['y'])
            overlay_clip = overlay_clip.set_position(position).set_duration(duration).set_start(self.start_time)

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


class ReverseVideoThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, video_path, start_time=None, end_time=None, is_audio_only=False, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.is_audio_only = is_audio_only
        self.main_window = parent
        self._is_running = True

    def run(self):
        clip = None
        reversed_media = None
        try:
            if not self.video_path or not os.path.exists(self.video_path):
                self.error.emit("Media file not found.")
                return

            self.progress.emit(10, "Loading and clipping media...")
            if self.is_audio_only:
                clip = AudioFileClip(self.video_path)
                if self.start_time is not None and self.end_time is not None:
                    clip = clip.subclip(self.start_time, self.end_time)

                if not self._is_running: return

                self.progress.emit(50, "Reversing audio...")
                audio_frames = [frame for frame in clip.iter_frames()]
                reversed_audio_frames = audio_frames[::-1]
                reversed_media = AudioArrayClip(np.array(reversed_audio_frames), fps=clip.fps)

                temp_path = self.main_window.get_temp_filepath(suffix=".mp3", prefix="reversed_")
                self.progress.emit(70, "Saving reversed audio...")
                reversed_media.write_audiofile(temp_path)
            else:
                clip = VideoFileClip(self.video_path)
                if self.start_time is not None and self.end_time is not None:
                    clip = clip.subclip(self.start_time, self.end_time)

                if not self._is_running: return

                self.progress.emit(30, "Reversing video frames...")
                frames = [frame for frame in clip.iter_frames()]
                reversed_frames = frames[::-1]
                reversed_media = ImageSequenceClip(reversed_frames, fps=clip.fps)

                if clip.audio:
                    self.progress.emit(50, "Reversing audio...")
                    audio_frames = [frame for frame in clip.audio.iter_frames()]
                    reversed_audio_frames = audio_frames[::-1]
                    reversed_audio = AudioArrayClip(np.array(reversed_audio_frames), fps=clip.audio.fps)
                    reversed_media = reversed_media.set_audio(reversed_audio)

                if not self._is_running: return

                temp_path = self.main_window.get_temp_filepath(suffix=".mp4", prefix="reversed_")
                self.progress.emit(70, "Saving reversed video...")
                logger = MergeProgressLogger(self.progress)
                reversed_media.write_videofile(temp_path, codec='libx264', audio_codec='aac', logger=logger)

            if self._is_running:
                self.completed.emit(temp_path)

        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))
        finally:
            if clip: clip.close()
            if reversed_media: reversed_media.close()

    def stop(self):
        self._is_running = False
        self.progress.emit(0, "Cancelling...")


class VideoAudioManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.project_manager = ProjectManager(self)
        self.bookmark_manager = BookmarkManager(self)
        self.translation_service = TranslationService()
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

        # Timer per il salvataggio automatico dei riassunti (debounced)
        self.summary_autosave_timer = QTimer(self)
        self.summary_autosave_timer.setSingleShot(True)
        self.summary_autosave_timer.timeout.connect(self._sync_active_summary_to_model)

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

        self.ui_manager = UIManager(self)
        self.player_manager = PlayerManager(self, self.player, self.playerOutput, self.ui_manager)
        self.action_manager = ActionManager(self, self.ui_manager, self.player_manager)
        self.ui_manager.initUI()
        self.ui_manager.setupMenuBar() # Create the menu bar via the UI manager
        self._connect_signals()

        # Load font settings at startup
        self.apply_and_save_font_settings()


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
        # Struttura dati per i riassunti del singolo file.
        # Conterrà solo testo Markdown grezzo, mai HTML.
        self.summaries = {
            "detailed": "",
            "meeting": "",
            "detailed_integrated": "",
            "meeting_integrated": ""
        }

        # Struttura dati per i riassunti combinati da più file.
        self.combined_summary = {
            "source_files": [],
            "detailed_combined": "",
            "meeting_combined": "",
            "detailed_combined_integrated": "",
            "meeting_combined_integrated": ""
        }
        self.active_summary_type = None # e.g., 'detailed', 'meeting_combined'
        self.original_audio_ai_html = ""
        self.reversed_video_path = None


        # Avvia la registrazione automatica delle chiamate
        #self.teams_call_recorder.start()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.monitor_preview = None
        self.cursor_overlay = CursorOverlay()
        self.current_thread = None
        self.original_status_bar_stylesheet = self.statusBar.styleSheet()
        self.current_translation_widget = None

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
        if hasattr(thread, 'progress'):
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

    def _connect_signals(self):
        # ProjectDock Signals
        self.ui_manager.projectDock.clip_selected.connect(self.load_project_clip)
        self.ui_manager.projectDock.open_folder_requested.connect(self.open_project_folder)
        self.ui_manager.projectDock.delete_clip_requested.connect(self.delete_project_clip)
        self.ui_manager.projectDock.project_clips_folder_changed.connect(self.sync_project_clips_folder)
        self.ui_manager.projectDock.open_in_input_player_requested.connect(self.player_manager.load_video)
        self.ui_manager.projectDock.open_in_output_player_requested.connect(self.player_manager.load_video_output)
        self.ui_manager.projectDock.rename_clip_requested.connect(self.rename_project_clip)
        self.ui_manager.projectDock.rename_from_summary_requested.connect(self.rename_clip_from_summary)
        self.ui_manager.projectDock.relink_clip_requested.connect(self.relink_project_clip)
        self.ui_manager.projectDock.batch_transcribe_requested.connect(self.start_batch_transcription)
        self.ui_manager.projectDock.batch_summarize_requested.connect(self.start_batch_summarization)
        self.ui_manager.projectDock.separate_audio_requested.connect(self.separate_audio_from_video)

        # ChatDock Signals
        self.ui_manager.chatDock.sendMessage.connect(self.handle_chat_message)
        self.ui_manager.chatDock.history_text_edit.timestampDoubleClicked.connect(self.sincronizza_video)

        # Player Input Signals
        self.ui_manager.videoCropWidget.spacePressed.connect(lambda: self.player_manager.toggle_play_pause('input'))
        self.ui_manager.videoOverlay.panned.connect(self.handle_pan)
        self.ui_manager.videoOverlay.zoomed.connect(self.handle_zoom)
        self.ui_manager.videoOverlay.view_reset.connect(self.reset_view)
        self.ui_manager.playButton.clicked.connect(lambda: self.player_manager.toggle_play_pause('input'))
        self.ui_manager.stopButton.clicked.connect(lambda: self.player_manager.stop_video('input'))
        self.ui_manager.setStartBookmarkButton.clicked.connect(self.setStartBookmark)
        self.ui_manager.setEndBookmarkButton.clicked.connect(self.setEndBookmark)
        self.ui_manager.clearBookmarksButton.clicked.connect(self.clearBookmarks)
        self.ui_manager.cutButton.clicked.connect(self.bookmark_manager.cut_all_bookmarks)
        self.ui_manager.cropButton.clicked.connect(self.open_crop_dialog)
        self.ui_manager.rewindButton.clicked.connect(lambda: self.player_manager.rewind_5_seconds('input'))
        self.ui_manager.forwardButton.clicked.connect(lambda: self.player_manager.forward_5_seconds('input'))
        self.ui_manager.frameBackwardButton.clicked.connect(self.player_manager.frame_backward)
        self.ui_manager.frameForwardButton.clicked.connect(self.player_manager.frame_forward)
        self.ui_manager.deleteButton.clicked.connect(self.bookmark_manager.delete_all_bookmarks)
        self.ui_manager.transferToOutputButton.clicked.connect(
            lambda: self.player_manager.load_video_output(self.videoPathLineEdit) if self.videoPathLineEdit else None
        )
        self.ui_manager.timecodeInput.returnPressed.connect(self.player_manager.go_to_timecode)
        self.ui_manager.go_button.clicked.connect(self.player_manager.go_to_timecode)
        self.ui_manager.speedSpinBox.valueChanged.connect(lambda rate: self.player_manager.set_playback_rate(rate, 'input'))
        self.ui_manager.reverseButton.clicked.connect(self.toggleReversePlayback)
        self.ui_manager.volumeSlider.valueChanged.connect(lambda value: self.player_manager.set_volume(value, 'input'))

        # Player Output Signals
        self.ui_manager.videoOutputWidget.spacePressed.connect(lambda: self.player_manager.toggle_play_pause('output'))
        self.ui_manager.playButtonOutput.clicked.connect(lambda: self.player_manager.toggle_play_pause('output'))
        self.ui_manager.stopButtonOutput.clicked.connect(lambda: self.player_manager.stop_video('output'))
        self.ui_manager.changeButtonOutput.clicked.connect(
            lambda: self.player_manager.load_video(self.videoPathLineOutputEdit, os.path.basename(self.videoPathLineOutputEdit))
        )
        self.ui_manager.syncPositionButton.clicked.connect(self.syncOutputWithSourcePosition)
        self.ui_manager.speedSpinBoxOutput.valueChanged.connect(lambda rate: self.player_manager.set_playback_rate(rate, 'output'))
        self.ui_manager.volumeSliderOutput.valueChanged.connect(lambda value: self.player_manager.set_volume(value, 'output'))

        # Transcription and Summary Signals
        self.ui_manager.translateTranscriptionButton.clicked.connect(self.translate_transcription)
        self.ui_manager.transcribeButton.clicked.connect(self.action_manager.transcribe_video)
        self.ui_manager.loadButton.clicked.connect(self.loadText)
        self.ui_manager.saveTranscriptionButton.clicked.connect(self.save_transcription_to_json)
        self.ui_manager.resetButton.clicked.connect(lambda: self.ui_manager.singleTranscriptionTextArea.clear())
        self.ui_manager.fixTranscriptionButton.clicked.connect(self.fixTranscriptionWithAI)
        self.ui_manager.pasteToAudioAIButton.clicked.connect(lambda: self.paste_to_audio_ai(self.ui_manager.singleTranscriptionTextArea))
        self.ui_manager.search_button.clicked.connect(self.open_search_dialog)
        self.ui_manager.timecodeCheckbox.toggled.connect(self.handleTimecodeToggle)
        self.ui_manager.syncButton.clicked.connect(self.sync_video_to_transcription)
        self.ui_manager.insertPauseButton.clicked.connect(self.insertPause)
        self.ui_manager.saveAudioAIButton.clicked.connect(self.save_audio_ai_to_json)
        self.ui_manager.generateGuideButton.clicked.connect(self.generate_operational_guide)
        self.ui_manager.transcriptionViewToggle.toggled.connect(self.toggle_transcription_view)

        # Transcription TextEdit
        self.ui_manager.singleTranscriptionTextArea.textChanged.connect(self.handleTextChange)
        self.ui_manager.singleTranscriptionTextArea.timestampDoubleClicked.connect(self.sincronizza_video)
        self.ui_manager.singleTranscriptionTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: self.handle_insert_frame_request(self.ui_manager.singleTranscriptionTextArea, timestamp, pos)
        )
        self.ui_manager.batchTranscriptionTextArea.timestampDoubleClicked.connect(self.sincronizza_video)


        # Summary Controls
        self.ui_manager.summarize_button.clicked.connect(self.action_manager.process_text_with_ai)
        self.ui_manager.summarize_meeting_button.clicked.connect(self.action_manager.summarize_meeting)
        self.ui_manager.generatePptxActionBtn.clicked.connect(self.openPptxDialog)
        self.ui_manager.highlightTextButton.clicked.connect(self.highlight_selected_text)
        self.ui_manager.pasteSummaryToAudioAIButton.clicked.connect(lambda: self.paste_to_audio_ai(self.get_current_summary_text_area()))
        self.ui_manager.saveSummaryButton.clicked.connect(self.save_summary_to_json)
        self.ui_manager.integraInfoButton.clicked.connect(self.integraInfoVideo)
        self.ui_manager.showTimecodeSummaryCheckbox.toggled.connect(self._update_summary_view)

        # Summary TextEdits
        for text_area in self.ui_manager.summary_widget_map.keys():
            text_area.timestampDoubleClicked.connect(self.sincronizza_video)
            text_area.textChanged.connect(self._on_summary_text_changed)
            text_area.frame_edit_requested.connect(self.handle_frame_edit_request)
            text_area.insert_frame_requested.connect(
                # Use a lambda to capture the current text_area
                lambda timestamp, pos, widget=text_area: self.handle_insert_frame_request(widget, timestamp, pos)
            )

        self.ui_manager.summaryTabWidget.currentChanged.connect(self._update_summary_view)


        # AI Audio Generation Signals
        self.ui_manager.alignspeed.toggled.connect(self.ui_manager.alignspeed_replacement.setChecked)
        self.ui_manager.alignspeed_replacement.toggled.connect(self.ui_manager.alignspeed.setChecked)
        #TODO: add more connections for the audio generation dock

        # Main Player Signals
        self.player.durationChanged.connect(self.durationChanged)
        self.player.positionChanged.connect(self.positionChanged)
        self.player.playbackStateChanged.connect(self.updatePlayButtonIcon)
        self.ui_manager.videoSlider.sliderMoved.connect(self.player_manager.set_position)

        # Output Player Signals
        self.playerOutput.durationChanged.connect(self.updateDurationOutput)
        self.playerOutput.positionChanged.connect(self.updateTimeCodeOutput)
        self.playerOutput.playbackStateChanged.connect(self.updatePlayButtonIconOutput)
        self.ui_manager.videoSliderOutput.sliderMoved.connect(lambda p: self.player_manager.set_position(p, 'output'))
        self.playerOutput.durationChanged.connect(lambda duration: self.ui_manager.videoSliderOutput.setRange(0, duration))
        self.playerOutput.positionChanged.connect(lambda position: self.ui_manager.videoSliderOutput.setValue(position))


        # Status Bar
        self.ui_manager.cancelButton.clicked.connect(self.cancel_task)

        # Toolbar Actions
        self.ui_manager.summarizeMeetingAction.triggered.connect(self.action_manager.summarize_meeting)
        self.ui_manager.summarizeAction.triggered.connect(self.action_manager.process_text_with_ai)
        self.ui_manager.fixTextAction.triggered.connect(self.fixTextWithAI)
        self.ui_manager.generatePptxAction.triggered.connect(self.openPptxDialog)
        self.ui_manager.recordingLayoutAction.triggered.connect(self.dockSettingsManager.loadRecordingLayout)
        self.ui_manager.comparisonLayoutAction.triggered.connect(self.dockSettingsManager.loadComparisonLayout)
        self.ui_manager.transcriptionLayoutAction.triggered.connect(self.dockSettingsManager.loadTranscriptionLayout)
        self.ui_manager.defaultLayoutAction.triggered.connect(self.dockSettingsManager.loadDefaultLayout)
        self.ui_manager.shareAction.triggered.connect(self.onShareButtonClicked)
        self.ui_manager.settingsAction.triggered.connect(self.showSettingsDialog)
        self.ui_manager.findAction.triggered.connect(self.open_search_dialog)

        # Info Extraction Dock Connections
        self.ui_manager.analysisPlayerSelectionCombo.currentIndexChanged.connect(self.on_analysis_player_selection_changed)
        self.ui_manager.runAnalysisButton.clicked.connect(self.run_frame_extraction_and_analysis)
        self.ui_manager.specificObjectSearchButton.clicked.connect(self.run_specific_object_search)
        self.ui_manager.infoExtractionResultArea.timestampDoubleClicked.connect(self.seek_to_search_result_timecode)
        self.ui_manager.smartExtractionCheckbox.toggled.connect(self._toggle_frame_count_spinbox)

        # Menu Connections
        self._connect_menu_signals()

    def open_search_dialog(self):
        """
        Apre un dialogo di ricerca per il CustomTextEdit attualmente attivo.
        Determina quale tra le aree di testo (trascrizione, riassunti) ha il focus
        e passa quel widget al dialogo di ricerca.
        """
        active_text_edit = self.get_active_text_edit()
        if active_text_edit:
            if not hasattr(self, 'search_dialog') or self.search_dialog is None:
                self.search_dialog = SearchDialog(active_text_edit, self)
            else:
                self.search_dialog.set_target_widget(active_text_edit)

            if self.search_dialog.isHidden():
                self.search_dialog.show()
                self.search_dialog.activateWindow()
                self.search_dialog.raise_()
            else:
                self.search_dialog.activateWindow()
        else:
            self.statusBar.showMessage("Nessun campo di testo attivo per la ricerca.", 3000)

    def get_active_text_edit(self):
        """
        Restituisce il widget CustomTextEdit che ha attualmente il focus.
        Se nessun editor di testo ha il focus, cerca di determinare quello attivo
        in base alla tab attualmente visibile.
        """
        widget = QApplication.focusWidget()
        if isinstance(widget, CustomTextEdit):
            return widget

        # Fallback se il focus non è direttamente sull'editor
        if self.ui_manager.transcriptionTabWidget.currentIndex() == 0: # Tab Trascrizione
             if self.ui_manager.transcriptionTabs.currentIndex() == 0:
                 return self.ui_manager.singleTranscriptionTextArea
             else:
                 return self.ui_manager.batchTranscriptionTextArea
        elif self.ui_manager.transcriptionTabWidget.currentIndex() == 1: # Tab Riassunto
            return self.get_current_summary_text_area()
        elif self.ui_manager.transcriptionTabWidget.currentIndex() == 2: # Tab Audio AI
            return self.ui_manager.audioAiTextArea

        return None

    def setupViewMenuActions(self, viewMenu):
        """Imposta le azioni del menu Visualizza per i dock."""
        self.dock_actions = {
            'videoPlayerDock': self.ui_manager.toggleVideoPlayerDockAction,
            'transcriptionDock': self.ui_manager.toggleTranscriptionDockAction,
            'editingDock': self.ui_manager.toggleEditingDockAction,
            'recordingDock': self.ui_manager.toggleRecordingDockAction,
            'audioDock': self.ui_manager.toggleAudioDockAction,
            'videoPlayerOutput': self.ui_manager.toggleVideoPlayerOutputDockAction,
            'projectDock': self.ui_manager.toggleProjectDockAction,
            'videoNotesDock': self.ui_manager.toggleVideoNotesDockAction,
            'infoExtractionDock': self.ui_manager.toggleInfoExtractionDockAction,
            'chatDock': self.ui_manager.toggleChatDockAction,
        }

        for dock_name, action in self.dock_actions.items():
            action.triggered.connect(lambda checked, name=dock_name: self.dockSettingsManager.toggleDockVisibilityAndUpdateMenu(name))

    def _connect_menu_signals(self):
        # File Menu
        self.ui_manager.newProjectAction.triggered.connect(self.project_manager.create_new_project)
        self.ui_manager.loadProjectAction.triggered.connect(self.project_manager.select_project_to_load)
        self.ui_manager.saveProjectAction.triggered.connect(self.save_project)
        self.ui_manager.closeProjectAction.triggered.connect(self._clear_workspace)
        self.ui_manager.importVideoAction.triggered.connect(self.import_videos_to_project)
        self.ui_manager.downloadVideoAction.triggered.connect(self.download_video_from_url)
        self.ui_manager.exportToTxtAction.triggered.connect(lambda: self.export_summary('txt'))
        self.ui_manager.exportToDocxAction.triggered.connect(lambda: self.export_summary('docx'))
        self.ui_manager.exportToPdfAction.triggered.connect(lambda: self.export_summary('pdf'))
        self.ui_manager.exitAction.triggered.connect(self.close)

        # Edit Menu
        self.ui_manager.undoAction.triggered.connect(self.undo_text)
        self.ui_manager.redoAction.triggered.connect(self.redo_text)
        self.ui_manager.cutAction.triggered.connect(self.cut_text)
        self.ui_manager.copyAction.triggered.connect(self.copy_text)
        self.ui_manager.pasteAction.triggered.connect(self.paste_text)
        self.ui_manager.findActionMenu.triggered.connect(self.open_search_dialog)

        # Layout Menu
        self.ui_manager.saveLayoutAction.triggered.connect(self.dockSettingsManager.save_settings)
        self.ui_manager.resetLayoutAction.triggered.connect(self.dockSettingsManager.resetLayout)

        # Tools Menu
        self.ui_manager.settingsActionMenu.triggered.connect(self.showSettingsDialog)

        # Help Menu
        self.ui_manager.aboutAction.triggered.connect(self.about)

    def select_project_to_load(self):
        """Opens a file dialog to select and load a project."""
        gnai_path, _ = QFileDialog.getOpenFileName(self, "Open Project", self.project_manager.base_dir, "GeniusAI Project Files (*.gnai)")
        if gnai_path:
            self._clear_workspace()
            self.load_project(gnai_path)

    def download_video_from_url(self):
        """Opens the download dialog."""
        dialog = DownloadDialog(self)
        dialog.exec()

    def undo_text(self):
        """Performs undo on the active text edit."""
        active_edit = self.get_active_text_edit()
        if active_edit:
            active_edit.undo()

    def redo_text(self):
        """Performs redo on the active text edit."""
        active_edit = self.get_active_text_edit()
        if active_edit:
            active_edit.redo()

    def cut_text(self):
        """Performs cut on the active text edit."""
        active_edit = self.get_active_text_edit()
        if active_edit:
            active_edit.cut()

    def copy_text(self):
        """Performs copy on the active text edit."""
        active_edit = self.get_active_text_edit()
        if active_edit:
            active_edit.copy()

    def paste_text(self):
        """Performs paste on the active text edit."""
        active_edit = self.get_active_text_edit()
        if active_edit:
            active_edit.paste()

    def about(self):
        """Shows the about dialog."""
        QMessageBox.about(self, "About GeniusAI",
                          f"<b>Genius AI</b> version: {self.version}<br>"
                          f"Build Date: {self.build_date}<br><br>"
                          "An AI-powered video and audio management application.")
