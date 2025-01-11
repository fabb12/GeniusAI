
from PyQt6.QtWidgets import ( QDialog)
from PyQt6.QtWidgets import ( QVBoxLayout, QPushButton, QLabel, QLineEdit)


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Imposta API Key")
        self.layout = QVBoxLayout()

        self.label = QLabel("Inserisci API Key:")
        self.api_key_edit = QLineEdit()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.api_key_edit)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)

    def get_api_key(self):
        return self.api_key_edit.text()

