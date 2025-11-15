from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolBar)
from PyQt6.QtGui import QIcon, QAction, QTextListFormat
from PyQt6.QtCore import pyqtSignal

from src.ui.CustomTextEdit import CustomTextEdit
from src.config import get_resource

class RichTextEditor(QWidget):
    """
    A composite widget that combines a QToolBar with a CustomTextEdit to provide
    rich text editing capabilities.
    """
    # Expose signals from the underlying CustomTextEdit for seamless integration
    cursorPositionChanged = pyqtSignal()
    timestampDoubleClicked = pyqtSignal(float)
    insert_frame_requested = pyqtSignal(float, int)
    frame_edit_requested = pyqtSignal(str)
    fontSizeChanged = pyqtSignal(int)
    textChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar for formatting actions
        self.toolbar = QToolBar(self)
        layout.addWidget(self.toolbar)

        # The actual text editing widget
        self.text_edit = CustomTextEdit(self)
        layout.addWidget(self.text_edit)

        self._setup_toolbar()
        self._connect_signals()

    def _setup_toolbar(self):
        """Creates and configures the formatting toolbar."""
        # --- Character Formatting ---
        self.bold_action = QAction(QIcon(get_resource("text_fix.png")), "Grassetto", self)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(self.set_bold)
        self.toolbar.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(get_resource("text_sum.png")), "Corsivo", self)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(self.set_italic)
        self.toolbar.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(get_resource("script.png")), "Sottolineato", self)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.setCheckable(True)
        self.underline_action.triggered.connect(self.set_underline)
        self.toolbar.addAction(self.underline_action)

        self.toolbar.addSeparator()

        # --- Paragraph Formatting (Lists) ---
        bullet_action = QAction(QIcon(get_resource("meet.png")), "Elenco Puntato", self)
        bullet_action.triggered.connect(self.insert_bullet_list)
        self.toolbar.addAction(bullet_action)

        numbered_action = QAction(QIcon(get_resource("meet_sum.png")), "Elenco Numerato", self)
        numbered_action.triggered.connect(self.insert_numbered_list)
        self.toolbar.addAction(numbered_action)

        # Connect cursor position changes to update toolbar button states
        self.text_edit.cursorPositionChanged.connect(self._update_toolbar_state)

    def _connect_signals(self):
        """Forwards signals from the internal CustomTextEdit to the outside world."""
        self.text_edit.cursorPositionChanged.connect(self.cursorPositionChanged)
        self.text_edit.timestampDoubleClicked.connect(self.timestampDoubleClicked)
        self.text_edit.insert_frame_requested.connect(self.insert_frame_requested)
        self.text_edit.frame_edit_requested.connect(self.frame_edit_requested)
        self.text_edit.fontSizeChanged.connect(self.fontSizeChanged)
        self.text_edit.textChanged.connect(self.textChanged)

    # --- Toolbar Action Slots ---

    def set_bold(self, checked):
        """Toggles bold formatting."""
        self.text_edit.setFontWeight(700 if checked else 400)

    def set_italic(self, checked):
        """Toggles italic formatting."""
        self.text_edit.setFontItalic(checked)

    def set_underline(self, checked):
        """Toggles underline formatting."""
        self.text_edit.setFontUnderline(checked)

    def insert_bullet_list(self):
        """Inserts a bullet list at the cursor position."""
        cursor = self.text_edit.textCursor()
        cursor.createList(QTextListFormat.Style.ListDisc)

    def insert_numbered_list(self):
        """Inserts a numbered list at the cursor position."""
        cursor = self.text_edit.textCursor()
        cursor.createList(QTextListFormat.Style.ListDecimal)

    def _update_toolbar_state(self):
        """Updates the checked state of toolbar buttons based on the cursor's current format."""
        self.bold_action.setChecked(self.text_edit.fontWeight() > 500)
        self.italic_action.setChecked(self.text_edit.fontItalic())
        self.underline_action.setChecked(self.text_edit.fontUnderline())

    # --- Methods to expose CustomTextEdit's public interface ---
    # This allows the RichTextEditor to be a drop-in replacement.

    def toPlainText(self):
        return self.text_edit.toPlainText()

    def toHtml(self):
        return self.text_edit.toHtml()

    def setHtml(self, html):
        self.text_edit.setHtml(html)

    def setPlainText(self, text):
        self.text_edit.setPlainText(text)

    def setMarkdown(self, markdown):
        self.text_edit.setMarkdown(markdown)

    def clear(self):
        self.text_edit.clear()

    def setPlaceholderText(self, text):
        self.text_edit.setPlaceholderText(text)

    def textCursor(self):
        return self.text_edit.textCursor()

    def setTextCursor(self, cursor):
        self.text_edit.setTextCursor(cursor)

    def document(self):
        return self.text_edit.document()

    def setReadOnly(self, isReadOnly):
        self.text_edit.setReadOnly(isReadOnly)

    def isReadOnly(self):
        return self.text_edit.isReadOnly()

    def openSearchDialog(self):
        self.text_edit.openSearchDialog()

    def blockSignals(self, block):
        # Block signals on both the wrapper and the internal widget
        super().blockSignals(block)
        self.text_edit.blockSignals(block)

    def insert_image_with_metadata(self, displayed_pixmap, width, height, video_path, timestamp, original_image=None):
        return self.text_edit.insert_image_with_metadata(displayed_pixmap, width, height, video_path, timestamp, original_image)
