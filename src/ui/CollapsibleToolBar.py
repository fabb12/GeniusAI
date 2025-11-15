from PyQt6.QtWidgets import QToolBar, QToolButton, QMenu, QWidgetAction
from PyQt6.QtCore import Qt

class CollapsibleToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setFloatable(False)

    def addCollapsibleSection(self, title, actions, is_checkable=False):
        tool_button = QToolButton(self)
        tool_button.setText(title)
        tool_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(self)
        for action in actions:
            menu.addAction(action)

        tool_button.setMenu(menu)
        self.addWidget(tool_button)
        return tool_button

    def addFontComboBox(self, font_combo_box):
        self.addWidget(font_combo_box)
