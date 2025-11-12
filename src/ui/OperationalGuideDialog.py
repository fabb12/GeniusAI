from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QComboBox, QLineEdit

class OperationalGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni Guida Operativa")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.recipient_input = QComboBox(self)
        self.recipient_input.setEditable(True)
        self.recipient_input.addItems(["Nuovo utente", "Tecnico specializzato", "Manager", "Cliente"])
        form_layout.addRow("Destinatario della guida:", self.recipient_input)

        self.style_input = QComboBox(self)
        self.style_input.addItems(["Professionale", "Informale", "Entusiasta", "Giocoso"])
        form_layout.addRow("Stile della guida:", self.style_input)

        self.synthesis_input = QComboBox(self)
        self.synthesis_input.addItems(["Sintetico", "Informativo", "Dettagliato"])
        form_layout.addRow("Livello di sintesi:", self.synthesis_input)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

    def get_options(self):
        return {
            "recipient": self.recipient_input.currentText(),
            "style": self.style_input.currentText(),
            "synthesis": self.synthesis_input.currentText()
        }
