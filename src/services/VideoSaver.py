import os
import subprocess
import re
import json
import shutil
from PyQt6.QtWidgets import QProgressDialog, QApplication
from PyQt6.QtCore import Qt
from src.config import FFMPEG_PATH


class VideoSaver:
    """
    Classe per gestire il salvataggio dei video, inclusa la compressione.
    """

    def __init__(self, parent=None):
        self.parent = parent

    def save_original(self, source_path, target_path):
        """
        Copia semplicemente il video originale nel percorso di destinazione.

        Returns:
            tuple: (success, error_message)
        """
        try:
            shutil.copy(source_path, target_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def save_compressed(self, source_path, target_path, quality=5):
        """
        Comprime il video per email o condivisione.

        Parameters:
            source_path (str): Percorso del video sorgente
            target_path (str): Percorso dove salvare il video compresso
            quality (int): Livello di qualità da 1 (minima) a 10 (massima)

        Returns:
            tuple: (success, error_message)
        """
        try:
            # Calcola il valore CRF (23 è il default, più basso = qualità maggiore)
            # Mappa qualità 1-10 a CRF 28-18
            crf = 28 - quality

            # Crea una dialog di progresso
            progress_dialog = QProgressDialog("Compressione video in corso...", "Annulla", 0, 100, self.parent)
            progress_dialog.setWindowTitle("Progresso Compressione")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setValue(0)
            progress_dialog.show()

            command = [
                FFMPEG_PATH,
                '-i', source_path,
                '-c:v', 'libx264',
                '-crf', str(crf),
                '-preset', 'medium',  # Compromesso tra velocità e compressione
                '-c:a', 'aac',
                '-b:a', '128k',  # Bitrate audio
                '-y',  # Sovrascrivi file di output
                target_path
            ]

            # Esegui il comando
            process = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Monitora il processo FFmpeg
            while True:
                if progress_dialog.wasCanceled():
                    process.kill()
                    return False, "Operazione annullata dall'utente"

                # Controlla se il processo è terminato
                if process.poll() is not None:
                    break

                # Cerca di aggiornare il progresso in base all'output di FFmpeg
                line = process.stderr.readline()
                if 'time=' in line:
                    try:
                        # Estrai il tempo corrente
                        time_pattern = r'time=(\d+:\d+:\d+\.\d+)'
                        match = re.search(time_pattern, line)
                        if match:
                            current_time = match.group(1)
                            h, m, s = current_time.split(':')
                            seconds = float(h) * 3600 + float(m) * 60 + float(s)

                            # Ottieni la durata del video
                            video_info = self.get_video_info(source_path)
                            duration = float(video_info.get('duration', 0))

                            if duration > 0:
                                # Calcola la percentuale di progresso
                                progress = min(int((seconds / duration) * 100), 99)
                                progress_dialog.setValue(progress)
                    except Exception:
                        pass

                # Breve pausa per non occupare la CPU
                QApplication.processEvents()

            progress_dialog.setValue(100)

            # Controlla se FFmpeg ha avuto successo
            if process.returncode != 0:
                error_output = process.stderr.read()
                return False, f"Errore FFmpeg: {error_output}"

            return True, None

        except Exception as e:
            return False, str(e)

    def get_video_info(self, video_path):
        """Ottieni informazioni sul file video."""
        try:
            ffprobe_path = FFMPEG_PATH.replace('ffmpeg.exe', 'ffprobe.exe')
            command = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]

            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                output = json.loads(result.stdout)
                return {
                    'duration': float(output.get('format', {}).get('duration', 0))
                }
            return {'duration': 0}
        except Exception:
            return {'duration': 0}