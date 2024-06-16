#!/usr/bin/env python3

import vlc
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QPushButton, QFileDialog, QHBoxLayout, QFrame, QApplication
from PyQt6.QtGui import QPalette, QColor, QPainter, QPen
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
import os
import sys

class MediaPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.instance = vlc.Instance()
        self.media = None
        self.mediaplayer = self.instance.media_player_new()

        self.is_paused = False
        self.cropping = False
        self.start_point = QPoint()
        self.end_point = QPoint()

        self.create_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)

    def create_ui(self):
        self.videoframe = QFrame(self)
        self.videoframe.setMouseTracking(True)

        self.overlay = QWidget(self.videoframe)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.palette = self.videoframe.palette()
        self.palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.positionslider = QSlider(Qt.Orientation.Horizontal, self)
        self.positionslider.setMaximum(1000)
        self.positionslider.sliderMoved.connect(self.set_position)
        self.positionslider.sliderPressed.connect(self.set_position)

        self.hbuttonbox = QHBoxLayout()
        self.playbutton = QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.play_pause)

        self.stopbutton = QPushButton("Stop")
        self.hbuttonbox.addWidget(self.stopbutton)
        self.stopbutton.clicked.connect(self.stop)

        self.volumeslider = QSlider(Qt.Orientation.Horizontal, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.hbuttonbox.addWidget(self.volumeslider)
        self.volumeslider.valueChanged.connect(self.set_volume)

        self.vboxlayout = QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.setLayout(self.vboxlayout)

    def play_pause(self):
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.is_paused = True
            self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return
            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.timer.start()
            self.is_paused = False

    def stop(self):
        self.mediaplayer.stop()
        self.playbutton.setText("Play")

    def open_file(self):
        dialog_txt = "Choose Media File"
        filename, _ = QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'))
        if not filename:
            return

        self.media = self.instance.media_new(filename)
        self.mediaplayer.set_media(self.media)
        self.media.parse()
        self.mediaplayer.set_hwnd(int(self.videoframe.winId()))
        self.play_pause()

    def set_volume(self, volume):
        self.mediaplayer.audio_set_volume(volume)

    def set_position(self):
        self.timer.stop()
        pos = self.positionslider.value()
        self.mediaplayer.set_position(pos / 1000.0)
        self.timer.start()

    def update_ui(self):
        media_pos = int(self.mediaplayer.get_position() * 1000)
        self.positionslider.setValue(media_pos)

        if not self.mediaplayer.is_playing():
            self.timer.stop()
            if not self.is_paused:
                self.stop()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.cropping:
            painter = QPainter(self.overlay)
            painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(QRect(self.start_point, self.end_point))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.videoframe.underMouse():
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.cropping = True

    def mouseMoveEvent(self, event):
        if self.cropping:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.cropping:
            self.end_point = event.position().toPoint()
            self.cropping = False
            self.update()
            self.crop_video()

    def crop_video(self):
        rect = QRect(self.start_point, self.end_point)
        if rect.isValid():
            # Implement cropping functionality here
            # Note: VLC Python bindings do not directly support cropping; this is a placeholder for actual crop logic
            logging.debug(f"Cropping to rectangle: {rect}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MediaPlayerWidget()
    player.setWindowTitle("Media Player")
    player.resize(800, 600)
    player.show()
    sys.exit(app.exec())
