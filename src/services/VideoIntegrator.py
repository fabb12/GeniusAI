# src/services/VideoIntegrator.py

import logging
from PyQt6.QtCore import QThread, pyqtSignal

import logging
from PyQt6.QtCore import QThread, pyqtSignal
from bs4 import BeautifulSoup

from src.services.FrameExtractor import FrameExtractor

class VideoIntegrationThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, video_path, num_frames, language, current_summary, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.num_frames = num_frames
        self.language = language
        self.current_summary = current_summary # Questo ora è HTML

    def run(self):
        try:
            self.progress.emit(10, "Estrazione frame dal video...")
            extractor = FrameExtractor(
                video_path=self.video_path,
                num_frames=self.num_frames
            )
            frames = extractor.extract_frames()
            if not frames:
                self.error.emit("Impossibile estrarre i frame dal video.")
                return

            self.progress.emit(30, "Analisi dei frame in corso...")
            frame_data = extractor.analyze_frames_batch(frames, self.language)
            if not frame_data:
                self.error.emit("L'analisi dei frame non ha prodotto risultati.")
                return

            self.progress.emit(70, "Integrazione delle informazioni nel riassunto...")

            # Costruisci lo snippet HTML per le nuove informazioni
            integration_html = "<h2>Integrazione Video</h2><ul>"
            for item in frame_data:
                description = item['description']
                time_parts = item['timestamp'].split(':')
                timestamp_sec = float(int(time_parts[0]) * 60 + int(time_parts[1]))
                minutes = int(timestamp_sec // 60)
                seconds = timestamp_sec % 60
                # Formatta il timestamp per essere cliccabile: [MM:SS.d]
                timecode = f"[{minutes:02d}:{seconds:.1f}]"

                # Aggiunge la descrizione e il timecode come un elemento di lista
                integration_html += f"<li>{description} - {timecode}</li>"
            integration_html += "</ul>"

            # Accoda il nuovo HTML al riassunto esistente
            # Usiamo BeautifulSoup per assicurarci che sia inserito correttamente nel body
            soup = BeautifulSoup(self.current_summary, 'html.parser')

            # Se non c'è un body, creane uno
            if not soup.body:
                new_body = soup.new_tag('body')
                # Trasferisci i contenuti esistenti nel nuovo body
                for content in list(soup.contents):
                    new_body.append(content.extract())
                soup.append(new_body)

            # Aggiungi il nuovo contenuto al body
            soup.body.append(BeautifulSoup(integration_html, 'html.parser'))

            # Emetti l'HTML completo
            final_html = str(soup)

            self.progress.emit(100, "Completato.")
            self.completed.emit(final_html)

        except Exception as e:
            logging.exception("Errore in VideoIntegrationThread")
            self.error.emit(str(e))
