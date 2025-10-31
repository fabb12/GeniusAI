from PyQt6.QtWidgets import QWidget, QRubberBand, QSizeGrip
from PyQt6.QtCore import QRect, QPoint, Qt

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

        self.size_grips = []
        for i in range(4):
            grip = QSizeGrip(self)
            self.size_grips.append(grip)

        self.show()

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.rubber_band.setGeometry(self.rect())

        self.size_grips[0].setGeometry(0, 0, 10, 10) # Top-left
        self.size_grips[1].setGeometry(self.width() - 10, 0, 10, 10) # Top-right
        self.size_grips[2].setGeometry(0, self.height() - 10, 10, 10) # Bottom-left
        self.size_grips[3].setGeometry(self.width() - 10, self.height() - 10, 10, 10) # Bottom-right

    def mousePressEvent(self, event):
        self.drag_start = event.pos()
        self.resizing = False
        for grip in self.size_grips:
            if grip.geometry().contains(event.pos()):
                self.resizing = True
                self.resize_start = self.geometry()
                self.grip = grip
                break

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_start'):
            if self.resizing:
                delta = event.pos() - self.drag_start
                new_rect = QRect(self.resize_start)
                if self.grip == self.size_grips[0]: # Top-left
                    new_rect.setTopLeft(self.resize_start.topLeft() + delta)
                elif self.grip == self.size_grips[1]: # Top-right
                    new_rect.setTopRight(self.resize_start.topRight() + delta)
                elif self.grip == self.size_grips[2]: # Bottom-left
                    new_rect.setBottomLeft(self.resize_start.bottomLeft() + delta)
                elif self.grip == self.size_grips[3]: # Bottom-right
                    new_rect.setBottomRight(self.resize_start.bottomRight() + delta)

                if self.parentWidget():
                    parent_rect = self.parentWidget().rect()
                    new_rect = new_rect.intersected(parent_rect)

                self.setGeometry(new_rect)
            else:
                delta = event.pos() - self.drag_start
                new_pos = self.pos() + delta

                if self.parentWidget():
                    parent_rect = self.parentWidget().rect()
                    if new_pos.x() < parent_rect.left(): new_pos.setX(parent_rect.left())
                    if new_pos.y() < parent_rect.top(): new_pos.setY(parent_rect.top())
                    if new_pos.x() + self.width() > parent_rect.right(): new_pos.setX(parent_rect.right() - self.width())
                    if new_pos.y() + self.height() > parent_rect.bottom(): new_pos.setY(parent_rect.bottom() - self.height())

                self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        if hasattr(self, 'drag_start'):
            del self.drag_start
