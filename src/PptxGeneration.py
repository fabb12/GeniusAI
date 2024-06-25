from PyQt6.QtWidgets import QFileDialog, QMessageBox
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
                PptxGeneration.createPresentationFromText(testo_attuale, save_path)
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

    @staticmethod
    def createPresentationFromText(testo, output_file):

        # Create a PowerPoint presentation
        prs = Presentation()

        # Select the 'Title and Content' layout which is commonly layout index 1
        title_and_content_layout = prs.slide_layouts[1]

        def imposta_testo_e_font(paragraph, text, size_pt, bold=False):
            """
            Helper function to set text and font properties for a given paragraph.
            """
            # Remove asterisks from the text before setting it
            text = text.replace('*', '')  # Removes all asterisks

            run = paragraph.add_run()
            run.text = text
            run.font.size = Pt(size_pt)
            run.font.bold = bold

        # Clean the text: remove format specific asterisks and adjust bullet points
        clean_text = re.sub(r'\*\*(Titolo|Sottotitolo|Contenuto):', r'\1:', testo)  # Remove asterisks around titles
        clean_text = re.sub(r'-\s*', '\u2022 ', clean_text)  # Replace dashes before bullets with bullet points

        # Regex to extract structured information such as title, subtitle, and content
        pattern = r"Titolo:\s*(.*?)\s+Sottotitolo:\s*(.*?)\s+Contenuto:\s*(.*?)\s*(?=Titolo|$)"
        slides_data = re.findall(pattern, clean_text, re.DOTALL)

        for titolo_text, sottotitolo_text, contenuto_text in slides_data:
            # Add a slide with the predefined layout
            slide = prs.slides.add_slide(title_and_content_layout)

            # Set the main title
            titolo = slide.shapes.title
            imposta_testo_e_font(titolo.text_frame.add_paragraph(), titolo_text.strip(), 32, bold=True)

            # Create a textbox for the subtitle directly below the title
            left = Inches(1)
            top = Inches(1.5)
            width = Inches(8)
            height = Inches(1)
            sottotitolo_shape = slide.shapes.add_textbox(left, top, width, height)
            sottotitolo_frame = sottotitolo_shape.text_frame
            imposta_testo_e_font(sottotitolo_frame.add_paragraph(), sottotitolo_text.strip(), 24, bold=False)

            # Set the content
            contenuto_box = slide.placeholders[1]
            for line in contenuto_text.strip().split('\n'):
                p = contenuto_box.text_frame.add_paragraph()
                if ':' in line:
                    part1, part2 = line.split(':', 1)
                    imposta_testo_e_font(p, part1.strip() + ':', 20, bold=True)  # Bold the part before the colon
                    imposta_testo_e_font(p, part2.strip(), 20, bold=False)  # Normal text for the part after the colon
                else:
                    imposta_testo_e_font(p, line.strip(), 20, bold=False)  # Normal text if no colon is present

        # Save the presentation if slides have been created
        if prs.slides:
            prs.save(output_file)
            QMessageBox.information(None, "Successo",
                                    "Presentazione PowerPoint generata con successo e salvata in: " + output_file)
        else:
            QMessageBox.warning(None, "Attenzione",
                                "Non sono state generate slides a causa di dati di input non validi o mancanti.")
