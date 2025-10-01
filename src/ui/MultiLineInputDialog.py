from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

class MultiLineInputDialog(QDialog):
    def __init__(self, parent=None, title="Enter Text", label="", text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)

        layout = QVBoxLayout(self)

        self.textEdit = QTextEdit()
        if label:
            self.textEdit.setPlaceholderText(label)
        self.textEdit.setText(text)
        layout.addWidget(self.textEdit)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def get_text(self):
        return self.textEdit.toPlainText()

    @staticmethod
    def getText(parent=None, title="Enter Text", label="", text=""):
        dialog = MultiLineInputDialog(parent, title, label, text)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.get_text(), True
        return "", False