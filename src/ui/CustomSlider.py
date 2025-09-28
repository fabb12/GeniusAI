from PyQt6.QtWidgets import QSlider, QStyleOptionSlider
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

class CustomSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.bookmarks = []
        self.pending_bookmark_start = None
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3c3c3c;
                background: #343434;
                height: 16px;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0078d7, stop:1 #005a9e);
                border: 1px solid #3c3c3c;
                height: 16px;
                border-radius: 8px;
            }
            QSlider::add-page:horizontal {
                background: #5a5a5a;
                border: 1px solid #3c3c3c;
                height: 16px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal {
                background: #0078d7;
                border: 2px solid #ffffff;
                width: 20px;
                height: 20px;
                margin: -4px 0;
                border-radius: 12px;
            }
            QSlider::handle:horizontal:hover {
                background: #0099cc;
                border: 2px solid #e0e0e0;
            }
            QSlider::handle:horizontal:pressed {
                background: #005a9e;
                border: 2px solid #d0d0d0;
            }
        """)

    def setPendingBookmarkStart(self, position):
        self.pending_bookmark_start = position
        self.update()

    def addBookmark(self, start, end):
        if start >= end:
            self.pending_bookmark_start = None
            self.update()
            return
        self.bookmarks.append((start, end))
        self.bookmarks.sort()
        self.pending_bookmark_start = None
        self.update()

    def removeBookmark(self, index):
        if 0 <= index < len(self.bookmarks):
            del self.bookmarks[index]
            self.update()

    def resetBookmarks(self):
        self.bookmarks = []
        self.pending_bookmark_start = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            value = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), int(event.position().x()), self.width())
            self.setValue(value)
            self.sliderMoved.emit(value)
            self.sliderPressed.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.maximum() == 0: # Avoid division by zero
            return

        # Draw existing bookmarks
        for start, end in self.bookmarks:
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw filled region
            painter.setBrush(QBrush(QColor(0, 120, 215, 70)))
            x_start_region = int(start / self.maximum() * self.width())
            x_end_region = int(end / self.maximum() * self.width())
            painter.drawRect(x_start_region, 0, x_end_region - x_start_region, self.height())

            # Draw start marker
            painter.setBrush(QBrush(QColor(255, 80, 80, 150)))
            x_start = int(start / self.maximum() * self.width())
            painter.drawRect(x_start - 2, 0, 4, self.height())

            # Draw end marker
            painter.setBrush(QBrush(QColor(80, 80, 255, 150)))
            x_end = int(end / self.maximum() * self.width())
            painter.drawRect(x_end - 2, 0, 4, self.height())

            # Draw duration text
            duration_ms = end - start
            total_seconds = duration_ms // 1000
            milliseconds = duration_ms % 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_text = f"{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}"

            painter.setPen(QColor(220, 220, 220))
            painter.setFont(QFont("Arial", 10))

            text_x = (x_start + x_end) / 2 - painter.fontMetrics().horizontalAdvance(duration_text) / 2
            text_y = self.height() // 2 + painter.fontMetrics().ascent() / 2
            painter.drawText(int(text_x), int(text_y), duration_text)

        # Draw pending bookmark start
        if self.pending_bookmark_start is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 180, 0, 220)))
            x_start = int(self.pending_bookmark_start / self.maximum() * self.width())
            painter.drawRect(x_start - 2, 0, 4, self.height())

        painter.end()