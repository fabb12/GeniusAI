from PyQt6.QtWidgets import QSlider, QStyleOptionSlider, QMenu
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QAction
from PyQt6.QtCore import Qt

class CustomSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.bookmarks = []
        self.pending_bookmark_start = None
        self.is_zoomed = False
        self.original_min = self.minimum()
        self.original_max = self.maximum()
        self.current_zoom_level = 1
        self.magnet_enabled = False
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #5c5c5c;
                background: #3e3e3e;
                height: 20px;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #0078d7;
                border: 1px solid #5c5c5c;
                height: 20px;
                border-radius: 10px;
            }
            QSlider::add-page:horizontal {
                background: #3e3e3e;
                border: 1px solid #5c5c5c;
                height: 20px;
                border-radius: 10px;
            }
            QSlider::handle:horizontal {
                background: #0099cc;
                border: 1px solid #b0b0b0;
                width: 8px;
                height: 24px;
                margin: -4px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal:hover {
                background: #00aaff;
                border: 1px solid #c0c0c0;
            }
            QSlider::handle:horizontal:pressed {
                background: #0078d7;
                border: 1px solid #e0e0e0;
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

    def get_bookmark_at(self, pos):
        """Restituisce l'indice del bookmark alla posizione data."""
        if self.maximum() == 0:
            return None
        for i, (start, end) in enumerate(self.bookmarks):
            x_start = int(start / self.maximum() * self.width())
            x_end = int(end / self.maximum() * self.width())
            if x_start <= pos.x() <= x_end:
                return i
        return None

    def contextMenuEvent(self, event):
        """Gestisce il menu contestuale per i bookmark."""
        context_menu = QMenu(self)

        # Azione per resettare tutti i bookmark
        reset_all_action = QAction("Resetta tutti i bookmark", self)
        reset_all_action.triggered.connect(self.resetBookmarks)
        context_menu.addAction(reset_all_action)

        # Azione per rimuovere un bookmark singolo
        bookmark_index = self.get_bookmark_at(event.pos())
        remove_single_action = QAction("Rimuovi bookmark singolo", self)
        if bookmark_index is not None:
            remove_single_action.triggered.connect(lambda: self.removeBookmark(bookmark_index))
        else:
            remove_single_action.setEnabled(False)
        context_menu.addAction(remove_single_action)

        context_menu.addSeparator()

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        context_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        context_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        context_menu.addAction(reset_zoom_action)

        context_menu.addSeparator()

        magnet_action = QAction("Magnet to Bookmarks", self)
        magnet_action.setCheckable(True)
        magnet_action.setChecked(self.magnet_enabled)
        magnet_action.triggered.connect(self.toggle_magnet)
        context_menu.addAction(magnet_action)

        context_menu.exec(event.globalPos())

    def mouseMoveEvent(self, event):
        if self.magnet_enabled and event.buttons() == Qt.MouseButton.LeftButton:

            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            value = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), int(event.position().x()), self.width())

            nearest_bookmark = self.find_nearest_bookmark(value)

            if nearest_bookmark is not None:

                start_pos, end_pos = self.bookmarks[nearest_bookmark]

                if abs(value - start_pos) < abs(value - end_pos):
                    snap_to = start_pos
                else:
                    snap_to = end_pos

                if abs(value-snap_to) < (self.maximum()-self.minimum())*0.05:
                    self.setValue(snap_to)
                    return

        super().mouseMoveEvent(event)

    def find_nearest_bookmark(self, value):
        if not self.bookmarks:
            return None

        nearest_b_index = -1
        min_dist = float('inf')

        for i, (start,end) in enumerate(self.bookmarks):

            dist_to_start = abs(value-start)
            dist_to_end = abs(value-end)

            if dist_to_start < min_dist:
                min_dist = dist_to_start
                nearest_b_index = i

            if dist_to_end < min_dist:
                min_dist = dist_to_end
                nearest_b_index = i

        return nearest_b_index

    def toggle_magnet(self, checked):
        self.magnet_enabled = checked

    def setRange(self, min_val, max_val):
        super().setRange(min_val, max_val)
        if not self.is_zoomed:
            self.original_min = min_val
            self.original_max = max_val

    def zoom_in(self):
        self.is_zoomed = True
        current_min = self.minimum()
        current_max = self.maximum()
        current_val = self.value()

        range_size = (current_max - current_min) / 2
        new_min = int(current_val - range_size / 2)
        new_max = int(current_val + range_size / 2)

        if new_min < self.original_min:
            new_min = self.original_min
        if new_max > self.original_max:
            new_max = self.original_max

        self.setRange(new_min, new_max)

    def zoom_out(self):
        if not self.is_zoomed:
            return

        current_min = self.minimum()
        current_max = self.maximum()
        current_val = self.value()

        range_size = (current_max - current_min) * 2
        new_min = int(current_val - range_size / 2)
        new_max = int(current_val + range_size / 2)

        if new_min < self.original_min:
            new_min = self.original_min
        if new_max > self.original_max:
            new_max = self.original_max

        self.setRange(new_min, new_max)

        if new_min == self.original_min and new_max == self.original_max:
            self.is_zoomed = False

    def reset_zoom(self):
        self.is_zoomed = False
        self.setRange(self.original_min, self.original_max)

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
            painter.setBrush(QBrush(QColor(0, 100, 255, 60)))
            x_start_region = int(start / self.maximum() * self.width())
            x_end_region = int(end / self.maximum() * self.width())
            painter.drawRect(x_start_region, 0, x_end_region - x_start_region, self.height())

            # Draw start marker
            painter.setBrush(QBrush(QColor(255, 0, 0, 128)))
            x_start = int(start / self.maximum() * self.width())
            painter.drawRect(x_start - 2, 0, 4, self.height())

            # Draw end marker
            painter.setBrush(QBrush(QColor(0, 0, 255, 128)))
            x_end = int(end / self.maximum() * self.width())
            painter.drawRect(x_end - 2, 0, 4, self.height())

            # Draw duration text
            duration_ms = end - start
            total_seconds = duration_ms // 1000
            milliseconds = duration_ms % 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_text = f"{int(minutes):02d}:{int(seconds):02d}:{int(milliseconds):03d}"

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 10))

            text_x = (x_start + x_end) / 2 - painter.fontMetrics().horizontalAdvance(duration_text) / 2
            text_y = self.height() // 2 + painter.fontMetrics().ascent() / 2
            painter.drawText(int(text_x), int(text_y), duration_text)

        # Draw pending bookmark start
        if self.pending_bookmark_start is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 165, 0, 200)))
            x_start = int(self.pending_bookmark_start / self.maximum() * self.width())
            painter.drawRect(x_start - 2, 0, 4, self.height())

        painter.end()