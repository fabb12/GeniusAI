import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QSpinBox,
    QDialogButtonBox
)
from PyQt6.QtCore import QSettings
from src.services.PptxGeneration import PptxGeneration
from src.ui.PreviewDialog import PreviewDialog

class PptxDialog(QDialog):
    def __init__(self, parent=None, transcription_text=""):
        super().__init__(parent)
        self.setWindowTitle("Genera Presentazione PowerPoint")
        self.setMinimumSize(500, 400)
        self.transcription_text = transcription_text
        self.template_path = ""

        # Layout principale
        main_layout = QVBoxLayout(self)

        # --- Gruppo Impostazioni ---
        settings_group = QGroupBox("Impostazioni di Generazione")
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
        design_group = QGroupBox("Design Personalizzato (Opzionale)")
        design_layout = QGridLayout()

        self.template_button = QPushButton("Scegli Template (.pptx)")
        self.template_button.clicked.connect(self.select_template)
        design_layout.addWidget(self.template_button, 0, 0)

        self.template_path_label = QLineEdit()
        self.template_path_label.setPlaceholderText("Nessun template selezionato")
        self.template_path_label.setReadOnly(True)
        design_layout.addWidget(self.template_path_label, 0, 1)

        design_group.setLayout(design_layout)
        main_layout.addWidget(design_group)

        # --- Pulsanti di Azione ---
        self.button_box = QDialogButtonBox()
        self.preview_button = self.button_box.addButton("Anteprima", QDialogButtonBox.ButtonRole.ActionRole)
        self.generate_button = self.button_box.addButton("Genera", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        self.preview_button.clicked.connect(self.handle_preview)
        self.generate_button.clicked.connect(self.handle_generate)
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addWidget(self.button_box)

    def select_template(self):
        """Apre un file dialog per selezionare un template .pptx."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona un Template PowerPoint",
            "",
            "Presentazioni PowerPoint (*.pptx)"
        )
        if path:
            self.template_path = path
            self.template_path_label.setText(os.path.basename(path))

    def handle_preview(self):
        """Gestisce la richiesta di anteprima."""
        if not self.transcription_text.strip():
            QMessageBox.warning(self, "Testo Mancante", "Il testo di origine è vuoto.")
            return

        settings = self.get_settings()

        # Genera prima il testo per le slide
        testo_per_slide, _, _ = PptxGeneration.generaTestoPerSlide(
            settings["source_text"],
            settings["num_slides"],
            settings["company_name"],
            settings["language"]
        )

        if "Errore" in testo_per_slide:
            QMessageBox.critical(self, "Errore API", f"Errore durante la generazione del testo: {testo_per_slide}")
            return

        # Genera le immagini di anteprima
        image_paths = PptxGeneration.generate_preview(
            self,
            testo_per_slide,
            settings["template_path"]
        )

        if image_paths:
            preview_dialog = PreviewDialog(image_paths, self)
            if preview_dialog.exec():
                # Se l'utente clicca "Salva" nell'anteprima, procedi con il salvataggio
                self.accept()

            preview_dialog.cleanup()

    def handle_generate(self):
        """Gestisce la generazione della presentazione."""
        if not self.transcription_text.strip():
            QMessageBox.warning(self, "Testo Mancante", "Il testo di origine è vuoto. Inserisci del testo nell'area di trascrizione.")
            return

        # Logica di generazione
        self.accept()

    def get_settings(self):
        """Restituisce le impostazioni correnti per la generazione."""
        return {
            "num_slides": self.num_slides_input.value(),
            "company_name": self.company_name_input.text(),
            "language": self.language_input.currentText(),
            "template_path": self.template_path,
            "source_text": self.transcription_text
        }
