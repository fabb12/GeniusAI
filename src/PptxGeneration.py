from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from pptx import Presentation
from pptx.util import Pt, Inches
import re
class PptxGeneration:
    @staticmethod
    def impostaFont(shape, size_pt, text):
        """
        Imposta il font per una shape data con la grandezza specificata.
        """
        text_frame = shape.text_frame
        p = text_frame.paragraphs[0]
        run = p.add_run()
        run.text = text

        font = run.font
        font.size = Pt(size_pt)  # Imposta la grandezza del font

    @staticmethod
    def creaPresentazione(parent, transcriptionTextArea):
        testo_attuale = transcriptionTextArea.toPlainText()
        if testo_attuale.strip() == "":
            # Se la QTextEdit è vuota, chiede all'utente di selezionare un file
            file_path, _ = QFileDialog.getOpenFileName(parent, "Seleziona File di Testo", "", "Text Files (*.txt)")
            if file_path:
                PptxGeneration.createPresentationFromFile(parent, file_path)
            else:
                # Se l'utente non seleziona un file, mostra un messaggio e non fa nulla
                QMessageBox.warning(parent, "Attenzione", "Nessun testo inserito e nessun file selezionato.")
        else:
            # Prompt the user to choose a location to save the presentation
            save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione", "",
                                                       "PowerPoint Presentation (*.pptx)")
            if save_path:
                # Utilizza il testo presente per generare la presentazione e salvare al percorso specificato
                PptxGeneration.createPresentationFromText(parent, testo_attuale,
                                                          save_path)  # Aggiunto parent come primo argomento
            else:
                QMessageBox.warning(parent, "Attenzione", "Salvataggio annullato. Nessun file selezionato.")

    @staticmethod
    def createPresentationFromFile(parent, file_path):
        encodings = ['utf-8', 'windows-1252', 'iso-8859-1']
        text_content = None
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text_content = file.read()
                break  # Se la lettura riesce, interrompe il ciclo
            except UnicodeDecodeError:
                continue  # Prova la prossima codifica
            except IOError as e:
                QMessageBox.critical(parent, "Errore di lettura file", f"Impossibile leggere il file: {str(e)}")
                return
            except Exception as e:
                QMessageBox.critical(parent, "Errore", f"Errore non previsto: {str(e)}")
                return

        if text_content is None:
            QMessageBox.critical(parent, "Errore di lettura",
                                 "Non è stato possibile decodificare il file con le codifiche standard.")
            return

        # Chiedi all'utente dove salvare la presentazione PowerPoint
        output_file, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione", "",
                                                     "PowerPoint Presentation (*.pptx)")
        if not output_file:
            QMessageBox.warning(parent, "Attenzione", "Salvataggio annullato. Nessun file selezionato.")
            return

        # Crea la presentazione PowerPoint utilizzando il testo letto dal file
        PptxGeneration.createPresentationFromText(text_content, output_file)

    @staticmethod
    def generaPresentationConTestoAttuale(parent, transcriptionTextArea):
        testo_attuale = transcriptionTextArea.toPlainText()
        if testo_attuale.strip() == "":
            # Se la QTextEdit è vuota, chiede all'utente di selezionare un file
            file_path, _ = QFileDialog.getOpenFileName(parent, "Seleziona File di Testo", "", "Text Files (*.txt)")
            if file_path:
                PptxGeneration.createPresentationFromFile(parent, file_path)
            else:
                # Se l'utente non seleziona un file, mostra un messaggio e non fa nulla
                QMessageBox.warning(parent, "Attenzione", "Nessun testo inserito e nessun file selezionato.")
        else:
            # Prompt the user to choose a location to save the presentation
            save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione", "",
                                                       "PowerPoint Presentation (*.pptx)")
            if save_path:
                # Utilizza il testo presente per generare la presentazione e salvare al percorso specificato
                PptxGeneration.createPresentationFromText(testo_attuale, save_path)
            else:
                QMessageBox.warning(parent, "Attenzione", "Salvataggio annullato. Nessun file selezionato.")

    def createPresentationFromText(parent, testo, output_file):
        prs = Presentation()
        title_and_content_layout = prs.slide_layouts[1]

        def imposta_testo_e_font(paragraph, text, size_pt, bold=False):
            text = text.replace('*', '')
            run = paragraph.add_run()
            run.text = text
            run.font.size = Pt(size_pt)
            run.font.bold = bold

        clean_text = re.sub(r'\*\*(Titolo|Sottotitolo|Contenuto):', r'\1:', testo)
        clean_text = re.sub(r'-\s*', '\u2022 ', clean_text)

        pattern = r"Titolo:\s*(.*?)\s+Sottotitolo:\s*(.*?)\s+Contenuto:\s*(.*?)\s*(?=Titolo|$)"
        slides_data = re.findall(pattern, clean_text, re.DOTALL)

        for titolo_text, sottotitolo_text, contenuto_text in slides_data:
            slide = prs.slides.add_slide(title_and_content_layout)
            titolo = slide.shapes.title
            imposta_testo_e_font(titolo.text_frame.add_paragraph(), titolo_text.strip(), 32, bold=True)
            left = Inches(1)
            top = Inches(1.5)
            width = Inches(8)
            height = Inches(1)
            sottotitolo_shape = slide.shapes.add_textbox(left, top, width, height)
            sottotitolo_frame = sottotitolo_shape.text_frame
            imposta_testo_e_font(sottotitolo_frame.add_paragraph(), sottotitolo_text.strip(), 24, bold=False)
            contenuto_box = slide.placeholders[1]
            for line in contenuto_text.strip().split('\n'):
                p = contenuto_box.text_frame.add_paragraph()
                if ':' in line:
                    part1, part2 = line.split(':', 1)
                    imposta_testo_e_font(p, part1.strip() + ':', 20, bold=True)
                    imposta_testo_e_font(p, part2.strip(), 20, bold=False)
                else:
                    imposta_testo_e_font(p, line.strip(), 20, bold=False)

        if prs.slides:
            prs.save(output_file)
            QMessageBox.information(None, "Successo", "Presentazione PowerPoint generata con successo e salvata in: " + output_file)
            PptxGeneration.visualizzaPresentazione(parent, output_file)
        else:
            QMessageBox.warning(None, "Attenzione", "Non sono state generate slides a causa di dati di input non validi o mancanti.")

    @staticmethod
    def visualizzaPresentazione(parent, file_path):
        prs = Presentation(file_path)
        dialog = QDialog(parent)
        dialog.setWindowTitle("Visualizza Presentazione")
        layout = QVBoxLayout()

        for i, slide in enumerate(prs.slides):
            slide_label = QLabel(f"Slide {i+1}: {slide.shapes.title.text if slide.shapes.title else 'Senza titolo'}")
            layout.addWidget(slide_label)

        buttonLayout = QHBoxLayout()
        fineSlideButton = QPushButton("Imposta Fine Slide")
        fineSlideButton.clicked.connect(lambda: PptxGeneration.impostaFineSlide(prs, dialog))
        buttonLayout.addWidget(fineSlideButton)

        layout.addLayout(buttonLayout)
        dialog.setLayout(layout)
        dialog.exec()

    @staticmethod
    def impostaFineSlide(prs, dialog):
        # Logica per impostare la fine della slide
        # Qui puoi implementare la funzionalità che desideri
        dialog.accept()
        QMessageBox.information(dialog, "Informazione", "Fine della slide impostata con successo.")