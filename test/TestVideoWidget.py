from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QFileDialog, QMessageBox, QProgressDialog, QLabel)
from PyQt6.QtCore import Qt, QRect, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer
import sys
import os
import cv2
from moviepy.editor import VideoFileClip


class VideoFrameLabel(QLabel):
    selectionCompleted = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)

        # Per la selezione
        self.selecting = False
        self.start_point = None
        self.current_point = None
        self.selection_rect = QRect()

        # Per il disegno
        self.setMouseTracking(True)

    def paintEvent(self, event):
        super().paintEvent(event)

        # Disegna sopra il video solo se c'è qualcosa da mostrare
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Disegna il rettangolo durante la selezione
        if self.selecting and self.start_point and self.current_point:
            rect = QRect(self.start_point, self.current_point).normalized()
            self._drawSelection(painter, rect)
        # Disegna il rettangolo di selezione salvato
        elif not self.selection_rect.isEmpty():
            self._drawSelection(painter, self.selection_rect)

    def _drawSelection(self, painter, rect):
        # Disegna un rettangolo con linea tratteggiata rossa
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 0, 0, 30)))  # Rosso semi-trasparente
        painter.drawRect(rect)

        # Disegna maniglie agli angoli come punti rossi
        handle_size = 8
        painter.setBrush(QBrush(QColor(255, 0, 0)))  # Punti rossi
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        corners = [
            (rect.left(), rect.top()),
            (rect.right(), rect.top()),
            (rect.left(), rect.bottom()),
            (rect.right(), rect.bottom())
        ]

        for x, y in corners:
            painter.drawEllipse(x - handle_size // 2, y - handle_size // 2, handle_size, handle_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Tasto destro inizia una nuova selezione
            self.selecting = True
            self.start_point = event.position().toPoint()
            self.current_point = self.start_point
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Tasto sinistro resetta la selezione corrente
            self.clearSelection()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.current_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.selecting:
            self.selecting = False
            self.current_point = event.position().toPoint()
            self.selection_rect = QRect(self.start_point, self.current_point).normalized()
            self.selectionCompleted.emit(self.selection_rect)
            self.update()

    def clearSelection(self):
        # Reset completo di tutti i parametri della selezione
        self.selection_rect = QRect()
        self.selecting = False
        self.start_point = None
        self.current_point = None
        self.update()

    def getSelectionRect(self):
        return self.selection_rect


class VideoSelectionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Selection and Crop Tool")
        self.setMinimumSize(800, 600)

        # Variabili per il video
        self.video_path = None
        self.output_video_path = None
        self.video_capture = None
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.update_frame)
        self.current_frame = None
        self.is_playing = False

        # Layout principale
        main_layout = QVBoxLayout(self)

        # Label per visualizzare i frame
        self.video_label = VideoFrameLabel()
        self.video_label.selectionCompleted.connect(self.on_selection_completed)

        # Aggiungi il label al layout
        main_layout.addWidget(self.video_label)

        # Bottoni
        button_layout = QVBoxLayout()

        self.open_button = QPushButton("Apri Video")
        self.open_button.clicked.connect(self.open_video)
        button_layout.addWidget(self.open_button)

        self.play_button = QPushButton("Play/Pausa")
        self.play_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_button)

        self.clear_button = QPushButton("Cancella Selezione")
        self.clear_button.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_button)

        self.crop_button = QPushButton("Ritaglia Video")
        self.crop_button.clicked.connect(self.crop_video)
        button_layout.addWidget(self.crop_button)

        main_layout.addLayout(button_layout)

        print("Per selezionare un'area, usa il tasto destro del mouse e trascina.")
        print("Per cancellare la selezione, fai clic con il tasto sinistro del mouse.")

    def open_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Apri Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )

        if file_name:
            # Ferma il timer se è in esecuzione
            if self.frame_timer.isActive():
                self.frame_timer.stop()

            # Chiudi il capture precedente se esiste
            if self.video_capture and self.video_capture.isOpened():
                self.video_capture.release()

            # Apri il nuovo video
            self.video_path = file_name
            self.video_capture = cv2.VideoCapture(file_name)

            if not self.video_capture.isOpened():
                QMessageBox.critical(self, "Errore", "Impossibile aprire il video.")
                return

            # Leggi il primo frame
            success, frame = self.video_capture.read()
            if success:
                # Converti il frame da BGR a RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape

                # Converti in QImage e poi in QPixmap
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)

                # Aggiorna il label con l'immagine
                self.video_label.setPixmap(pixmap.scaled(
                    self.video_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

                # Avvia la riproduzione
                self.play_button.setText("Pausa")
                self.is_playing = True
                self.frame_timer.start(33)  # ~30 fps

                self.setWindowTitle(f"Video Selection and Crop Tool - {os.path.basename(file_name)}")
            else:
                QMessageBox.critical(self, "Errore", "Impossibile leggere il video.")

    def update_frame(self):
        if not self.video_capture or not self.video_capture.isOpened():
            return

        success, frame = self.video_capture.read()
        if success:
            # Salva il frame corrente
            self.current_frame = frame

            # Converti il frame da BGR a RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape

            # Converti in QImage e poi in QPixmap
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # Aggiorna il label con l'immagine
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # Fine del video, riavvolgi
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def toggle_play_pause(self):
        if self.is_playing:
            self.frame_timer.stop()
            self.play_button.setText("Play")
            self.is_playing = False
        else:
            if self.video_capture and self.video_capture.isOpened():
                self.frame_timer.start(33)
                self.play_button.setText("Pausa")
                self.is_playing = True

    def clear_selection(self):
        self.video_label.clearSelection()

    def on_selection_completed(self, rect):
        pass

    def crop_video(self):
        if not self.video_path:
            QMessageBox.warning(self, "Errore", "Nessun video caricato.")
            return

        crop_rect = self.video_label.getSelectionRect()
        if crop_rect.isEmpty():
            QMessageBox.warning(self, "Errore", "Seleziona un'area da ritagliare con il tasto destro del mouse.")
            return

        # Chiedi il percorso per salvare il video ritagliato
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Salva Video Ritagliato", "", "Video Files (*.mp4)"
        )

        if not output_path:
            return

        if not output_path.lower().endswith('.mp4'):
            output_path += '.mp4'

        # Mostra un dialogo di progresso
        progress = QProgressDialog("Ritaglio video in corso...", "Annulla", 0, 100, self)
        progress.setWindowTitle("Progresso Ritaglio")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        try:
            # Carica il video con moviepy
            video = VideoFileClip(self.video_path)
            progress.setValue(20)

            # Calcola il fattore di scala tra il label e il video reale
            video_width, video_height = video.size
            pixmap = self.video_label.pixmap()
            if pixmap:
                label_width = pixmap.width()
                label_height = pixmap.height()
            else:
                label_width = self.video_label.width()
                label_height = self.video_label.height()

            # Calcola lo scaling e l'offset per mantenere aspect ratio
            if label_width / label_height > video_width / video_height:
                # Il label è più largo del video
                scale_factor = video_height / label_height
                offset_x = (label_width - (video_width / scale_factor)) / 2
                offset_y = 0
            else:
                # Il label è più alto del video
                scale_factor = video_width / label_width
                offset_x = 0
                offset_y = (label_height - (video_height / scale_factor)) / 2

            # Adatta le coordinate della selezione
            x1 = max(0, int((crop_rect.x() - offset_x) * scale_factor))
            y1 = max(0, int((crop_rect.y() - offset_y) * scale_factor))
            x2 = min(video_width, int((crop_rect.x() + crop_rect.width() - offset_x) * scale_factor))
            y2 = min(video_height, int((crop_rect.y() + crop_rect.height() - offset_y) * scale_factor))

            # Applica il ritaglio
            progress.setValue(50)
            cropped_video = video.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Salva il video ritagliato
            progress.setValue(70)
            cropped_video.write_videofile(output_path, codec='libx264')

            progress.setValue(100)
            progress.close()

            # Memorizza il percorso del video di output
            self.output_video_path = output_path

            # Mostra messaggio di successo
            QMessageBox.information(
                self, "Successo",
                f"Il video ritagliato è stato salvato in {output_path}"
            )

            # Chiedi se caricare il video ritagliato
            reply = QMessageBox.question(
                self,
                "Carica Video Ritagliato",
                "Vuoi caricare il video ritagliato?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Ferma la riproduzione corrente
                if self.frame_timer.isActive():
                    self.frame_timer.stop()

                # Chiudi la capture corrente
                if self.video_capture and self.video_capture.isOpened():
                    self.video_capture.release()

                # Carica il nuovo video
                self.video_path = output_path
                self.video_capture = cv2.VideoCapture(output_path)

                if self.video_capture.isOpened():
                    # Leggi il primo frame
                    success, frame = self.video_capture.read()
                    if success:
                        # Converti e mostra il frame
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_frame.shape
                        bytes_per_line = ch * w
                        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qt_image)
                        self.video_label.setPixmap(pixmap.scaled(
                            self.video_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        ))

                        # Avvia la riproduzione
                        self.is_playing = True
                        self.play_button.setText("Pausa")
                        self.frame_timer.start(33)

                self.setWindowTitle(f"Video Selection and Crop Tool - {os.path.basename(output_path)}")
                self.clear_selection()

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Errore", f"Errore durante il ritaglio: {str(e)}")

    def closeEvent(self, event):
        # Ferma il timer
        if self.frame_timer.isActive():
            self.frame_timer.stop()

        # Rilascia le risorse video
        if self.video_capture and self.video_capture.isOpened():
            self.video_capture.release()

        event.accept()


# Avvia l'applicazione
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = VideoSelectionApp()
    window.show()

    sys.exit(app.exec())