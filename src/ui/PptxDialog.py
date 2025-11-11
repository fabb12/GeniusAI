import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QSpinBox,
    QDialogButtonBox, QTextEdit, QApplication
)
from src.services.PptxGeneration import PptxGeneration
from src.ui.PreviewDialog import PreviewDialog


class PptxDialog(QDialog):
    def __init__(self, parent=None, transcription_text=""):
        super().__init__(parent)
        self.setWindowTitle("Genera Presentazione PowerPoint")
        self.setMinimumSize(600, 700)  # Aumenta le dimensioni per il nuovo campo
        self.transcription_text = transcription_text
        self.template_path = ""

        # Layout principale
        main_layout = QVBoxLayout(self)

        # --- Gruppo Impostazioni ---
        settings_group = QGroupBox("1. Impostazioni di Generazione")
        settings_layout = QGridLayout()

        # Numero di slide
        self.num_slides_label = QLabel("Numero di Slide:")
        self.num_slides_input = QSpinBox()
        self.num_slides_input.setMinimum(1)
        self.num_slides_input.setValue(5)
        settings_layout.addWidget(self.num_slides_label, 0, 0)
        settings_layout.addWidget(self.num_slides_input, 0, 1)

        # Nome compagnia
        self.company_name_label = QLabel("Nome Compagnia (opzionale):")
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Es. Acme Inc.")
        settings_layout.addWidget(self.company_name_label, 1, 0)
        settings_layout.addWidget(self.company_name_input, 1, 1)

        # Lingua
        self.language_label = QLabel("Lingua:")
        self.language_input = QComboBox()
        self.language_input.addItems(["Italiano", "Inglese", "Francese", "Spagnolo", "Tedesco"])
        settings_layout.addWidget(self.language_label, 2, 0)
        settings_layout.addWidget(self.language_input, 2, 1)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # --- Gruppo Design Personalizzato ---
        design_group = QGroupBox("2. Design Personalizzato (Opzionale)")
        design_layout = QGridLayout()

        self.template_button = QPushButton("Scegli Template (.pptx)")
        self.template_button.clicked.connect(self.select_template)
        design_layout.addWidget(self.template_button, 0, 0)

        self.template_path_label = QLineEdit()
        self.template_path_label.setPlaceholderText("Nessun template selezionato")
        self.template_path_label.setReadOnly(True)
        design_layout.addWidget(self.template_path_label, 0, 1)

        self.remove_template_button = QPushButton("Rimuovi")
        self.remove_template_button.clicked.connect(self.remove_template)
        design_layout.addWidget(self.remove_template_button, 0, 2)

        design_group.setLayout(design_layout)
        main_layout.addWidget(design_group)

        # --- Gruppo Contenuto AI ---
        ai_content_group = QGroupBox("3. Contenuto Generato dall'AI")
        ai_content_layout = QVBoxLayout()

        self.get_ai_content_button = QPushButton("Genera Contenuto AI")
        self.get_ai_content_button.clicked.connect(self.handle_get_ai_content)
        ai_content_layout.addWidget(self.get_ai_content_button)

        self.ai_content_input = QTextEdit()
        self.ai_content_input.setPlaceholderText("Il contenuto generato dall'AI apparirà qui e sarà modificabile...")
        self.ai_content_input.setReadOnly(True)
        ai_content_layout.addWidget(self.ai_content_input)

        ai_content_group.setLayout(ai_content_layout)
        main_layout.addWidget(ai_content_group)

        # --- Pulsanti di Azione ---
        self.button_box = QDialogButtonBox()
        self.preview_button = self.button_box.addButton("Anteprima", QDialogButtonBox.ButtonRole.ActionRole)
        self.generate_button = self.button_box.addButton("Genera", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        self.preview_button.setEnabled(False)
        self.generate_button.setEnabled(False)

        self.preview_button.clicked.connect(self.handle_preview)
        self.generate_button.clicked.connect(self.handle_generate)
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addWidget(self.button_box)

    def select_template(self):
        """Apre un file dialog per selezionare un template .pptx."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona un Template PowerPoint", "", "Presentazioni PowerPoint (*.pptx)"
        )
        if path:
            self.template_path = path
            self.template_path_label.setText(os.path.basename(path))

    def remove_template(self):
        """Resets the template selection."""
        self.template_path = ""
        self.template_path_label.setText("")
        self.template_path_label.setPlaceholderText("Nessun template selezionato")

    def handle_get_ai_content(self):
        """Genera il contenuto testuale tramite AI e lo mostra nell'editor."""
        if not self.transcription_text.strip():
            self.parent().show_status_message("Il testo di origine è vuoto.", error=True)
            return

        settings = self.get_settings()
        self.get_ai_content_button.setEnabled(False)
        self.get_ai_content_button.setText("Generazione in corso...")
        QApplication.instance().processEvents()

        try:
            result = PptxGeneration.generaTestoPerSlide(
                settings["source_text"],
                settings["num_slides"],
                settings["company_name"],
                settings["language"]
            )

            if isinstance(result, str): # Errore
                QMessageBox.critical(self, "Errore API", f"Errore durante la generazione del testo: {result}")
                self.ai_content_input.setReadOnly(True)
            else: # Successo
                testo_per_slide, _, _ = result
                self.ai_content_input.setPlainText(testo_per_slide)
                self.ai_content_input.setReadOnly(False)
                self.preview_button.setEnabled(True)
                self.generate_button.setEnabled(True)
                self.parent().show_status_message("Contenuto generato. Ora puoi modificarlo e procedere.")

        finally:
            self.get_ai_content_button.setEnabled(True)
            self.get_ai_content_button.setText("Genera Contenuto AI")

    def handle_preview(self):
        """Gestisce la richiesta di anteprima usando il testo dall'editor."""
        ai_text = self.get_ai_text()
        if not ai_text.strip():
            self.parent().show_status_message("Il campo del contenuto AI è vuoto.", error=True)
            return

        settings = self.get_settings()
        image_paths = PptxGeneration.generate_preview(
            self.parent(),
            ai_text,
            settings["template_path"],
            settings["num_slides"]
        )

        if image_paths:
            preview_dialog = PreviewDialog(image_paths, self)
            preview_dialog.exec()  # Mostra la dialog in modo modale
            preview_dialog.cleanup() # Pulisce le immagini temporanee dopo la chiusura

    def handle_generate(self):
        """Gestisce la generazione della presentazione finale."""
        ai_text = self.get_ai_text()
        if not ai_text.strip():
            self.parent().show_status_message("Il campo del contenuto AI è vuoto.", error=True)
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Salva Presentazione", "", "PowerPoint Presentation (*.pptx)")
        if not save_path:
            self.parent().show_status_message("Salvataggio annullato.", error=True)
            return

        settings = self.get_settings()
        PptxGeneration.createPresentationFromText(
            self.parent(),
            ai_text,
            save_path,
            settings["template_path"],
            num_slides=settings["num_slides"]
        )
        self.accept()

    def get_ai_text(self):
        """Restituisce il testo presente nell'area di contenuto AI."""
        return self.ai_content_input.toPlainText()

    def get_settings(self):
        """Restituisce le impostazioni correnti per la generazione."""
        return {
            "num_slides": self.num_slides_input.value(),
            "company_name": self.company_name_input.text(),
            "language": self.language_input.currentText(),
            "template_path": self.template_path,
            "source_text": self.transcription_text
        }
