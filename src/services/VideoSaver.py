import os
import subprocess
import re
import json
import shutil
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip


class OpticalFlowThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, source_path, target_path, factor, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.target_path = target_path
        self.factor = int(factor)
        self.running = True

    def run(self):
        temp_video_path = None
        try:
            self.progress.emit(0, "Inizializzazione slow motion con Optical Flow...")

            # 1. Video processing with OpenCV
            cap = cv2.VideoCapture(self.source_path)
            if not cap.isOpened():
                raise IOError("Impossibile aprire il file video.")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            temp_video_path = os.path.splitext(self.target_path)[0] + "_temp_slow.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps * self.factor, (width, height))

            ret, prev_frame = cap.read()
            if not ret:
                raise ValueError("Impossibile leggere il primo frame.")

            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            frame_count = 1

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                progress_percent = int((frame_count / total_frames) * 80)
                self.progress.emit(progress_percent, f"Generazione frames: {frame_count}/{total_frames}")

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

                out.write(prev_frame)

                h, w = flow.shape[:2]
                x, y = np.meshgrid(np.arange(w), np.arange(h))
                for i in range(1, self.factor):
                    if not self.running: break
                    alpha = i / self.factor
                    map_x = (x - (1 - alpha) * flow[..., 0]).astype(np.float32)
                    map_y = (y - (1 - alpha) * flow[..., 1]).astype(np.float32)
                    interp_frame = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
                    out.write(interp_frame)

                if not self.running: break

                prev_frame = frame
                prev_gray = gray
                frame_count += 1

            if self.running:
                out.write(prev_frame) # Scrive l'ultimo frame

            cap.release()
            out.release()

            if not self.running:
                self.error.emit("Operazione annullata.")
                return

            # 2. Audio processing with moviepy
            self.progress.emit(85, "Processo audio...")
            video_clip = VideoFileClip(temp_video_path)

            try:
                original_audio = VideoFileClip(self.source_path).audio
                if original_audio:
                    stretched_audio = original_audio.set_duration(video_clip.duration)
                    final_clip = video_clip.set_audio(stretched_audio)
                else:
                    final_clip = video_clip
            except Exception as e:
                final_clip = video_clip


            # 3. Write final video
            self.progress.emit(90, "Salvataggio finale...")
            final_clip.write_videofile(self.target_path, codec='libx264', audio_codec='aac')

            self.progress.emit(100, "Completato")
            self.completed.emit(self.target_path)

        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            # Cleanup
            if 'cap' in locals() and cap.isOpened(): cap.release()
            if 'out' in locals() and out.isOpened(): out.release()
            if 'video_clip' in locals(): video_clip.close()
            if 'original_audio' in locals() and original_audio: original_audio.close()
            if 'final_clip' in locals(): final_clip.close()
            if temp_video_path and os.path.exists(temp_video_path):
                os.remove(temp_video_path)

    def stop(self):
        self.running = False


class FfmpegThread(QThread):
    """
    Un thread per eseguire comandi FFmpeg in background,
    emettendo segnali per il progresso, il completamento o l'errore.
    """
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, command, source_path, parent=None):
        super().__init__(parent)
        self.command = command
        self.source_path = source_path
        self.process = None

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            video_info = self._get_video_info(self.source_path)
            duration = float(video_info.get('duration', 0))

            while True:
                if self.process is None or self.process.poll() is not None:
                    break

                line = self.process.stderr.readline()
                if 'time=' in line:
                    try:
                        time_pattern = r'time=(\d+:\d+:\d+\.\d+)'
                        match = re.search(time_pattern, line)
                        if match:
                            current_time_str = match.group(1)
                            h, m, s_ms = current_time_str.split(':')
                            s = float(s_ms)
                            seconds = float(h) * 3600 + float(m) * 60 + s
                            if duration > 0:
                                percent = min(int((seconds / duration) * 100), 99)
                                self.progress.emit(percent, f"Elaborazione: {percent}%")
                    except Exception:
                        pass

            if self.process and self.process.returncode != 0:
                error_output = self.process.stderr.read()
                self.error.emit(f"Errore FFmpeg: {error_output}")
            elif self.process:
                self.completed.emit(self.command[-1])

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        if self.process:
            self.process.kill()
            self.process = None

    def _get_video_info(self, video_path):
        try:
            ffprobe_path = 'ffmpeg/bin/ffprobe.exe'
            command = [
                ffprobe_path, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'json', video_path
            ]
            result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                output = json.loads(result.stdout)
                return {'duration': float(output.get('format', {}).get('duration', 0))}
            return {'duration': 0}
        except Exception:
            return {'duration': 0}

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

class VideoSaver:
    """
    Classe per gestire il salvataggio dei video. Restituisce un QThread
    per l'esecuzione asincrona.
    """
    def __init__(self, parent=None):
        self.parent = parent

    def save_with_slow_motion(self, source_path, target_path, factor):
        return OpticalFlowThread(source_path, target_path, factor, self.parent)

    def save_original(self, source_path, target_path, playback_rate=1.0):
        if playback_rate == 1.0:
            return CopyThread(source_path, target_path, self.parent)

        ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'
        command = [ffmpeg_path, '-i', source_path]
        video_filters, audio_filters = self._build_rate_filters(playback_rate)
        if video_filters: command.extend(['-filter:v', ",".join(video_filters)])
        if audio_filters: command.extend(['-filter:a', ",".join(audio_filters)])
        command.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-y', target_path])

        return FfmpegThread(command, source_path, self.parent)

    def save_compressed(self, source_path, target_path, quality=5, playback_rate=1.0):
        crf = 28 - quality
        ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'
        command = [ffmpeg_path, '-i', source_path]
        video_filters, audio_filters = self._build_rate_filters(playback_rate)
        if video_filters: command.extend(['-filter:v', ",".join(video_filters)])
        if audio_filters: command.extend(['-filter:a', ",".join(audio_filters)])
        command.extend(['-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium', '-c:a', 'aac', '-b:a', '128k', '-y', target_path])

        return FfmpegThread(command, source_path, self.parent)

    def _build_rate_filters(self, playback_rate):
        video_filters = []
        audio_filters = []
        if playback_rate != 1.0 and playback_rate > 0:
            video_filters.append(f"setpts={1.0/playback_rate}*PTS")
            atempo_filters = []
            rate = playback_rate
            while rate > 100.0:
                atempo_filters.append("atempo=100.0")
                rate /= 100.0
            while rate < 0.5 and rate > 0:
                atempo_filters.append("atempo=0.5")
                rate /= 0.5
            if rate != 1.0:
                atempo_filters.append(f"atempo={rate}")
            if atempo_filters:
                audio_filters.append(','.join(atempo_filters))
        return video_filters, audio_filters