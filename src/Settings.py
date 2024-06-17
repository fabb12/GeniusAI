from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QRadioButton, QButtonGroup, QDialogButtonBox, QLabel

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Impostazioni")

        layout = QVBoxLayout(self)

        # Creazione del widget tab
        tabs = QTabWidget()
        tabs.addTab(self.createTTSSettingsTab(), "Motori TTS")

        layout.addWidget(tabs)

        # Aggiunta dei pulsanti OK e Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def createTTSSettingsTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.elevenLabsRadio = QRadioButton("Eleven Labs")
        self.internalRadio = QRadioButton("Motore Interno")

        # Gruppo di pulsanti per assicurarsi che solo uno sia selezionato
        self.ttsButtonGroup = QButtonGroup()
        self.ttsButtonGroup.addButton(self.elevenLabsRadio)
        self.ttsButtonGroup.addButton(self.internalRadio)

        layout.addWidget(QLabel("Seleziona il motore TTS da utilizzare:"))
        layout.addWidget(self.elevenLabsRadio)
        layout.addWidget(self.internalRadio)

        # Layout placeholder
        layout.addStretch(1)

        return tab
