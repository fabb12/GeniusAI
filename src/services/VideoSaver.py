import os
import subprocess
import re
import json
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

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