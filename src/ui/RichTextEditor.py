from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QToolButton, QFontComboBox, QHBoxLayout)
from PyQt6.QtGui import QIcon, QAction, QTextListFormat, QFont
from PyQt6.QtCore import pyqtSignal

from src.ui.CustomTextEdit import CustomTextEdit
from src.config import get_resource
from src.ui.CollapsibleGroupBox import CollapsibleGroupBox

class RichTextEditor(QWidget):
    """
    A composite widget that combines a QToolBar with a CustomTextEdit to provide
    rich text editing capabilities, with a collapsible UI.
    """
    cursorPositionChanged = pyqtSignal()
    timestampDoubleClicked = pyqtSignal(float)
    insert_frame_requested = pyqtSignal(float, int)
    frame_edit_requested = pyqtSignal(str)
    fontSizeChanged = pyqtSignal(int)
    textChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)

        # The actual text editing widget
        self.text_edit = CustomTextEdit(self)

        self._setup_ui()
        self._connect_signals()

        self.main_layout.addWidget(self.text_edit)

    def _setup_ui(self):
        """Creates and configures the formatting UI."""
        # --- Main Toolbar for all actions ---
        main_toolbar = QToolBar("Main Formatting")
        main_toolbar.setIconSize(main_toolbar.iconSize() / 1.2)
        self.main_layout.addWidget(main_toolbar)

        # Group 1: Character Formatting
        self.bold_action = QAction(QIcon(get_resource("text_fix.png")), "Grassetto (Ctrl+B)", self)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(self.set_bold)
        main_toolbar.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(get_resource("text_sum.png")), "Corsivo (Ctrl+I)", self)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(self.set_italic)
        main_toolbar.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(get_resource("script.png")), "Sottolineato (Ctrl+U)", self)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.setCheckable(True)
        self.underline_action.triggered.connect(self.set_underline)
        main_toolbar.addAction(self.underline_action)

        main_toolbar.addSeparator()

        # Group 2: Font and Size
        self.font_combo = QFontComboBox(self)
        self.font_combo.currentFontChanged.connect(self.set_font_family)
        main_toolbar.addWidget(self.font_combo)

        self.decrease_font_action = QAction(QIcon(get_resource("minus.png")), "Riduci Dimensione", self)
        self.decrease_font_action.triggered.connect(self.decrease_font_size)
        main_toolbar.addAction(self.decrease_font_action)

        self.increase_font_action = QAction(QIcon(get_resource("plus.png")), "Aumenta Dimensione", self)
        self.increase_font_action.triggered.connect(self.increase_font_size)
        main_toolbar.addAction(self.increase_font_action)

        main_toolbar.addSeparator()

        # Group 3: Paragraph Formatting
        self.title_action = QAction(QIcon(get_resource("title.png")), "Titolo", self)
        self.title_action.triggered.connect(lambda: self.set_heading_level(1))
        main_toolbar.addAction(self.title_action)

        self.subtitle_action = QAction(QIcon(get_resource("subtitle.png")), "Sottotitolo", self)
        self.subtitle_action.triggered.connect(lambda: self.set_heading_level(2))
        main_toolbar.addAction(self.subtitle_action)

        self.paragraph_action = QAction(QIcon(get_resource("paragraph.png")), "Paragrafo", self)
        self.paragraph_action.triggered.connect(lambda: self.set_heading_level(0))
        main_toolbar.addAction(self.paragraph_action)

        main_toolbar.addSeparator()

        bullet_action = QAction(QIcon(get_resource("meet.png")), "Elenco Puntato", self)
        bullet_action.triggered.connect(self.insert_bullet_list)
        main_toolbar.addAction(bullet_action)

        numbered_action = QAction(QIcon(get_resource("meet_sum.png")), "Elenco Numerato", self)
        numbered_action.triggered.connect(self.insert_numbered_list)
        main_toolbar.addAction(numbered_action)

        main_toolbar.addSeparator()

        # Group 4: Actions
        self.reset_format_action = QAction(QIcon(get_resource("reset.png")), "Reset Formattazione", self)
        self.reset_format_action.triggered.connect(self.reset_format)
        main_toolbar.addAction(self.reset_format_action)

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
        self.text_edit.setFontWeight(700 if checked else 400)

    def set_italic(self, checked):
        self.text_edit.setFontItalic(checked)

    def set_underline(self, checked):
        self.text_edit.setFontUnderline(checked)

    def reset_format(self):
        self.text_edit.reset_selection_format()

    def increase_font_size(self):
        self.text_edit.modify_selection_font_size(1)

    def decrease_font_size(self):
        self.text_edit.modify_selection_font_size(-1)

    def set_font_family(self, font: QFont):
        self.text_edit.set_selection_font_family(font.family())

    def insert_bullet_list(self):
        self.text_edit.toggle_list_style(QTextListFormat.Style.ListDisc)

    def insert_numbered_list(self):
        self.text_edit.toggle_list_style(QTextListFormat.Style.ListDecimal)

    def set_heading_level(self, level):
        self.text_edit.set_heading_level(level)

    def _update_toolbar_state(self):
        """Updates the checked state of toolbar buttons based on the cursor's current format."""
        self.bold_action.setChecked(self.text_edit.fontWeight() > 500)
        self.italic_action.setChecked(self.text_edit.fontItalic())
        self.underline_action.setChecked(self.text_edit.fontUnderline())

        # Update font combo box
        current_font = self.text_edit.currentFont()
        self.font_combo.blockSignals(True)
        self.font_combo.setCurrentFont(current_font)
        self.font_combo.blockSignals(False)

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
