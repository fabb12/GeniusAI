from PyQt6.QtWidgets import QSlider, QStyleOptionSlider
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

class CustomSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.bookmarkStart = None
        self.bookmarkEnd = None
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #eee;
                height: 10px;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #66ccff;
                border: 1px solid #bbb;
                height: 10px;
                border-radius: 4px;
            }
            QSlider::add-page:horizontal {
                background: #fff;
                border: 1px solid #bbb;
                height: 10px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #66ccff;
                border: 1px solid #66ccff;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #0099cc;
                border: 1px solid #0099cc;
            }
            QSlider::handle:horizontal:pressed {
                background: #005f80;
                border: 1px solid #005f80;
            }
        """)

    def setBookmarkStart(self, position):
        self.bookmarkStart = position
        self.update()

    def setBookmarkEnd(self, position):
        self.bookmarkEnd = position
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            value = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), int(event.position().x()), self.width())
            self.setValue(value)
            self.sliderMoved.emit(value)
            self.sliderPressed.emit()  # Emit the signal to trigger the slot
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.bookmarkStart is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 0, 0, 128)))
            x_start = int(self.bookmarkStart / self.maximum() * self.width())
            painter.drawRect(x_start - 2, 0, 4, self.height())

        if self.bookmarkEnd is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 255, 128)))
            x_end = int(self.bookmarkEnd / self.maximum() * self.width())
            painter.drawRect(x_end - 2, 0, 4, self.height())

            if self.bookmarkStart is not None:
                duration = (self.bookmarkEnd - self.bookmarkStart) / 1000.0  # Calcola la durata in secondi
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_text = f"{minutes:02d}:{seconds:02d}"  # Testo della durata in formato MM:SS

                painter.setPen(QColor(0, 0, 0))
                painter.setFont(QFont("Arial", 10))

                # Calcola la posizione del testo vicino ai bookmark
                text_x = (x_start + x_end) / 2 - painter.fontMetrics().horizontalAdvance(duration_text) / 2
                text_y = self.height() // 2 + painter.fontMetrics().ascent() / 2
                painter.drawText(int(text_x), int(text_y), duration_text)

        painter.end()
