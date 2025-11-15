from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QPushButton, QGridLayout
from PyQt6.QtCore import Qt, pyqtSignal, QParallelAnimationGroup, QPropertyAnimation, QAbstractAnimation

class CollapsibleGroupBox(QWidget):
    """
    A collapsible group box widget composed of a toggle button and a content area.
    The content area can be expanded or collapsed by clicking the button.
    """
    # Signal emitted when the collapsed state changes
    toggled = pyqtSignal(bool)

    def __init__(self, title: str = "", parent: QWidget = None):
        super().__init__(parent)

        # Main layout for this widget
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Toggle button for expanding/collapsing
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                border: 1px solid #333;
                background-color: #555;
            }
            QPushButton:checked {
                background-color: #666;
            }
        """)
        self.toggle_button.clicked.connect(self._toggle)

        # Frame to hold the content, allowing it to be hidden
        self.content_area = QFrame(self)
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setFrameShadow(QFrame.Shadow.Plain)
        self.content_area.setVisible(False) # Start collapsed
        self.content_area.setMaximumHeight(0) # Start with zero height

        # Layout for the content area (to be populated externally)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 5)

        # Add widgets to the main layout
        self.main_layout.addWidget(self.toggle_button, 0, 0)
        self.main_layout.addWidget(self.content_area, 1, 0)

        # Animation setup for smooth collapsing/expanding
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(200) # Animation duration in milliseconds

    def setContentLayout(self, layout: QVBoxLayout):
        """
        Sets the layout for the content area, replacing the existing one.
        """
        # Clear the old layout
        if self.content_area.layout() is not None:
            # Properly delete old layout and its widgets
            while self.content_area.layout().count():
                item = self.content_area.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        self.content_area.setLayout(layout)
        self.content_layout = layout

    def _toggle(self, checked: bool):
        """
        Handles the click event on the toggle button to expand or collapse the content.
        """
        self.toggle_button.setChecked(checked)

        # Calculate the height of the content
        content_height = self.content_area.sizeHint().height()

        # Animate the maximumHeight property
        self.animation.setStartValue(self.content_area.maximumHeight())
        if checked:
            self.animation.setEndValue(content_height)
            self.content_area.setVisible(True)
        else:
            self.animation.setEndValue(0)

        # Hide the widget after the animation finishes collapsing
        if not checked:
            self.animation.finished.connect(lambda: self.content_area.setVisible(False))
        else:
            # Disconnect to avoid hiding on expand
            if self.animation.receivers(self.animation.finished) > 0:
                self.animation.finished.disconnect()

        self.animation.start()
        self.toggled.emit(checked)
