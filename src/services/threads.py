# File: src/services/threads.py
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.PptxGeneration import PptxGeneration

class PptxGenerationThread(QThread):
    """
    Thread per gestire la generazione di presentazioni PowerPoint in background.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, parent, testo, save_path, template_path, num_slides, company_name, language):
        super().__init__()
        self.parent = parent
        self.testo = testo
        self.save_path = save_path
        self.template_path = template_path
        self.num_slides = num_slides
        self.company_name = company_name
        self.language = language

    def run(self):
        """
        Esegue la generazione del testo e la creazione della presentazione.
        """
        try:
            # 1. Genera il testo per le slide
            result_tuple = PptxGeneration.generaTestoPerSlide(
                self.testo, self.num_slides, self.company_name, self.language
            )

            if not isinstance(result_tuple, tuple) or len(result_tuple) != 3:
                self.error.emit(f"Errore durante la generazione del testo AI: {result_tuple}")
                return

            testo_per_slide, _, _ = result_tuple

            # 2. Crea la presentazione dal testo
            PptxGeneration.createPresentationFromText(
                self.parent,
                testo_per_slide,
                self.save_path,
                self.template_path,
                num_slides=self.num_slides
            )

            self.finished.emit(self.save_path)

        except Exception as e:
            logging.exception("Errore nel thread di generazione PPTX")
            self.error.emit(str(e))
