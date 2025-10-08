import os
import subprocess
import re
import json
import shutil
import tempfile
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip

class VideoProcessingThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, source_path, target_path, options, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.target_path = target_path
        self.options = options
        self.process = None
        self.running = True
        self.temp_interpolated_video = None

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            self.progress.emit(0, "Annullamento in corso...")
            try:
                self.process.stdin.write(b'q')
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except (subprocess.TimeoutExpired, IOError, BrokenPipeError):
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logging.error(f"Errore imprevisto durante l'annullamento del processo ffmpeg: {e}")
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
            finally:
                self.process = None

    def run(self):
        try:
            video_input_path = self.source_path

            # Stage 1: Frame Interpolation (Optional)
            if self.options.get('use_interpolation'):
                self.temp_interpolated_video = self._run_interpolation_stage()
                if not self.running: return
                video_input_path = self.temp_interpolated_video

            # Stage 2: FFmpeg Processing
            self._run_ffmpeg_stage(video_input_path)

        except Exception as e:
            if self.running:
                self.error.emit(f"Errore: {e}")
        finally:
            # Cleanup temporary files
            if self.temp_interpolated_video and os.path.exists(self.temp_interpolated_video):
                os.remove(self.temp_interpolated_video)

    def _run_interpolation_stage(self):
        self.progress.emit(0, "Fase 1: Interpolazione frame con Optical Flow...")

        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            raise IOError("Impossibile aprire il file video sorgente.")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        factor = self.options['interpolation_factor']

        temp_video_path = os.path.join(tempfile.gettempdir(), f"temp_interpolated_{os.path.basename(self.target_path)}")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps * factor, (width, height))

        ret, prev_frame = cap.read()
        if not ret:
            raise ValueError("Impossibile leggere il primo frame del video.")

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        frame_count = 0

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            progress_percent = int((frame_count / total_frames) * 50) # Interpolation is 50% of the work
            self.progress.emit(progress_percent, f"Interpolazione: Frame {frame_count}/{total_frames}")

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

            out.write(prev_frame)

            h, w = flow.shape[:2]
            x, y = np.meshgrid(np.arange(w), np.arange(h))
            for i in range(1, factor):
                if not self.running: break
                alpha = i / factor
                map_x = (x + alpha * flow[..., 0]).astype(np.float32)
                map_y = (y + alpha * flow[..., 1]).astype(np.float32)
                interp_frame = cv2.remap(prev_frame, map_x, map_y, cv2.INTER_LINEAR)
                out.write(interp_frame)

            if not self.running: break

            prev_frame = frame
            prev_gray = gray
            frame_count += 1

        if self.running:
            out.write(prev_frame)

        cap.release()
        out.release()

        if not self.running:
            raise InterruptedError("Processo di interpolazione annullato.")

        return temp_video_path

    def _run_ffmpeg_stage(self, video_input_path):
        self.progress.emit(50, "Fase 2: Processo FFmpeg...")

        ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'
        command = [ffmpeg_path, '-y', '-i', video_input_path]

        # Audio input must always be the original source
        command.extend(['-i', self.source_path])

        video_filters = []
        audio_filters = []

        # Speed change
        if self.options.get('save_with_speed', False):
            # The parent window must have a speedSpinBoxOutput attribute
            playback_rate = self.parent().speedSpinBoxOutput.value() if self.parent() else 1.0
            if playback_rate == 0: playback_rate = 1.0

            if playback_rate != 1.0 and playback_rate > 0:
                video_filters.append(f"setpts={1.0/playback_rate}*PTS")

                # Build atempo filter chain for audio
                atempo_filters = []
                rate = playback_rate
                while rate > 2.0:
                    atempo_filters.append("atempo=2.0")
                    rate /= 2.0
                if rate != 1.0:
                    atempo_filters.append(f"atempo={rate}")
                if atempo_filters:
                    audio_filters.append(','.join(atempo_filters))

        if video_filters:
            command.extend(['-filter:v', ",".join(video_filters)])
        if audio_filters:
            command.extend(['-filter:a', ",".join(audio_filters)])

        # Compression
        if self.options.get('use_compression', False):
            quality = self.options.get('compression_quality', 5)
            crf = 28 - quality
            command.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf)])
            command.extend(['-c:a', 'aac', '-b:a', '128k'])
        else:
            command.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '18'])
            command.extend(['-c:a', 'aac', '-b:a', '192k'])

        # Map streams: video from the (potentially interpolated) input, audio from the original source
        command.extend(['-map', '0:v:0', '-map', '1:a:0?'])
        command.extend([self.target_path])

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        duration = self._get_video_duration(self.source_path)

        while self.running:
            if self.process is None or self.process.poll() is not None:
                break

            line = self.process.stderr.readline()
            if 'time=' in line:
                match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                if match:
                    current_time_str = match.group(1)
                    h, m, s_ms = current_time_str.split(':')
                    seconds = float(h) * 3600 + float(m) * 60 + float(s_ms)
                    if duration > 0:
                        percent = 50 + min(int((seconds / duration) * 50), 49)
                        self.progress.emit(percent, f"Finalizzazione: {percent}%")

        if not self.running:
             raise InterruptedError("Processo FFmpeg annullato.")

        if self.process.returncode != 0:
            error_output = self.process.stderr.read()
            raise RuntimeError(f"Errore FFmpeg: {error_output}")

        self.progress.emit(100, "Completato")
        self.completed.emit(self.target_path)

    def _get_video_duration(self, video_path):
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            return 0


class VideoSaver:
    def __init__(self, parent=None):
        self.parent = parent

    def save_video(self, source_path, target_path, options):
        # If no special options are selected, just copy the file
        if not options.get('use_interpolation') and not options.get('save_with_speed') and not options.get('use_compression'):
             # We use a simple copy thread for consistency
            return CopyThread(source_path, target_path, self.parent)

        return VideoProcessingThread(source_path, target_path, options, self.parent)


class CopyThread(QThread):
    """Un semplice thread per copiare un file, per coerenza con l'API asincrona."""
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, src, dst, parent=None):
        super().__init__(parent)
        self.src = src
        self.dst = dst

    def run(self):
        try:
            self.progress.emit(50, "Copia del file in corso...")
            shutil.copy(self.src, self.dst)
            self.progress.emit(100, "Copia completata.")
            self.completed.emit(self.dst)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        pass