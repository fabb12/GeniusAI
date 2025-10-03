# File: src/services/PptxGeneration.py

import anthropic
import google.generativeai as genai
import requests
import json
import logging
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
import re
import os
import subprocess  # Needed for os.startfile alternative
import sys
import tempfile
from dotenv import load_dotenv

# Importa la configurazione delle azioni e le chiavi/endpoint necessari
from src.config import (
    OLLAMA_ENDPOINT, get_api_key, get_model_for_action,
    PROMPT_PPTX_GENERATION # Assicurati che questo percorso sia corretto e il file esista
)

load_dotenv() # Carica .env se necessario

class PptxGeneration:
    """
    Classe statica per gestire la generazione di presentazioni PowerPoint
    utilizzando diversi modelli AI (Claude, Gemini, Ollama) basati sulle impostazioni.
    """

    @staticmethod
    def _get_layout(prs, layout_names):
        """Trova un layout da una lista di possibili nomi."""
        for name in layout_names:
            for layout in prs.slide_layouts:
                if layout.name.strip().lower() == name.lower():
                    return layout
        return None


    @staticmethod
    def createPresentationFromFile(parent, file_path, num_slide, company_name, language):
        """Crea una presentazione leggendo il testo sorgente da un file."""
        try:
            logging.info(f"Tentativo di creare presentazione da file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                testo = file.read()

            if not testo.strip():
                if hasattr(parent, 'show_status_message'):
                    parent.show_status_message("Il file selezionato è vuoto.", error=True)
                return

            result_tuple = PptxGeneration.generaTestoPerSlide(testo, num_slide, company_name, language)

            if not isinstance(result_tuple, tuple) or len(result_tuple) != 3:
                 QMessageBox.critical(parent, "Errore API", f"Errore durante la generazione del testo per le slide.\nDettagli:\n{result_tuple}")
                 return

            testo_per_slide, input_tokens, output_tokens = result_tuple
            logging.info(f"Generazione testo PPTX da file - Token Input: {input_tokens}, Token Output: {output_tokens}")

            save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione", "", "PowerPoint Presentation (*.pptx)")
            if save_path:
                PptxGeneration.createPresentationFromText(parent, testo_per_slide, save_path, num_slides=num_slide)
            else:
                if hasattr(parent, 'show_status_message'):
                    parent.show_status_message("Salvataggio annullato.", error=True)
        except FileNotFoundError:
             logging.error(f"File non trovato: {file_path}")
             QMessageBox.critical(parent, "Errore", f"File non trovato: {file_path}")
        except Exception as e:
            logging.exception("Errore in createPresentationFromFile")
            QMessageBox.critical(parent, "Errore", f"Si è verificato un errore imprevisto: {e}")

    @staticmethod
    def generaTestoPerSlide(testo, num_slide, company_name, language):
        """
        Genera il testo strutturato per le slide usando il modello AI selezionato.
        Restituisce una tupla (testo_generato, input_tokens, output_tokens) o una stringa di errore.
        """
        # Recupera il modello selezionato per l'azione 'pptx_generation'
        selected_model = get_model_for_action('pptx_generation')
        logging.info(f"Generazione PPTX: Utilizzo del modello '{selected_model}'")

        # 2. Leggi e formatta il prompt
        try:
            with open(PROMPT_PPTX_GENERATION, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            logging.exception("Errore durante la lettura del file prompt PPTX")
            return f"Errore lettura prompt: {e}"

        company_info = (
            f" La presentazione è destinata all'azienda {company_name}. "
            f"Considera il suo ambito, i prodotti principali e il mercato. "
            f"Crea una presentazione personalizzata per {company_name} basata sull'argomento fornito."
            if company_name else ""
        )
        try:
            system_prompt_content = prompt_template.format(
                num_slide=num_slide,
                language=language,
                company_info=company_info
            )
        except KeyError as e:
             logging.error(f"Errore nella formattazione del prompt PPTX. Chiave mancante: {e}")
             return f"Errore nel template del prompt: chiave '{e}' mancante."

        user_prompt = f"Testo sorgente:\n{testo}\n\n---\nGenera la struttura della presentazione come richiesto." # Input principale per l'LLM

        # 3. Selezione e chiamata API
        model_name_lower = selected_model.lower()

        try:
            if "ollama:" in model_name_lower:
                # --- Logica per Ollama ---
                logging.info(f"Chiamata API Ollama: {selected_model}")
                ollama_model_name = selected_model.split(":", 1)[1]
                api_url = f"{OLLAMA_ENDPOINT}/api/generate"
                full_prompt = f"{system_prompt_content}\n\n{user_prompt}"
                payload = {"model": ollama_model_name, "prompt": full_prompt, "stream": False, "system": system_prompt_content} # Passa anche come system

                response = requests.post(api_url, json=payload, timeout=300) # Timeout 5 min
                response.raise_for_status()
                response_data = response.json()
                result_text = response_data.get("response", "").strip()
                if not result_text:
                    error_details = response_data.get("error", "Risposta vuota.")
                    raise Exception(f"Ollama ha restituito un errore o una risposta vuota: {error_details}")
                logging.info("Risposta ricevuta da Ollama.")
                return result_text, 0, 0 # Token non disponibili

            elif "gemini" in model_name_lower:
                # --- Logica per Google Gemini ---
                logging.info(f"Chiamata API Gemini: {selected_model}")
                google_api_key = get_api_key('google')
                if not google_api_key: raise ValueError("API Key Google non configurata.")
                genai.configure(api_key=google_api_key)
                model = genai.GenerativeModel(selected_model, system_instruction=system_prompt_content) # Usa system instruction
                response = model.generate_content(user_prompt) # Passa solo lo user prompt
                # Aggiungi gestione errori risposta Gemini se necessario (es. blocco per safety)
                try:
                    result_text = response.text
                except ValueError as ve:
                     # Potrebbe essere bloccato per safety
                     logging.warning(f"Possibile blocco risposta Gemini: {ve}. Dettagli: {response.prompt_feedback}")
                     raise Exception(f"Risposta da Gemini bloccata o non valida. Causa: {response.prompt_feedback}")

                logging.info("Risposta ricevuta da Gemini.")
                return result_text, 0, 0 # Token non disponibili facilmente

            elif "claude" in model_name_lower:
                # --- Logica per Anthropic Claude ---
                logging.info(f"Chiamata API Claude: {selected_model}")
                anthropic_api_key = get_api_key('anthropic')
                if not anthropic_api_key: raise ValueError("API Key Anthropic non configurata.")
                client = anthropic.Anthropic(api_key=anthropic_api_key)
                message = client.messages.create(
                    model=selected_model,
                    max_tokens=4096,
                    temperature=0.7,
                    system=system_prompt_content,
                    messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}]
                )
                # Aggiungi controllo sul motivo di stop
                if message.stop_reason == 'max_tokens':
                     logging.warning("Risposta Claude troncata per max_tokens.")

                testo_resultante = message.content[0].text
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                logging.info("Risposta ricevuta da Claude.")
                return testo_resultante, input_tokens, output_tokens

            # elif "gpt" in model_name_lower:
                # --- Logica per OpenAI (Esempio) ---
                # logging.info(f"Chiamata API OpenAI: {selected_model}")
                # if not OPENAI_API_KEY: raise ValueError("API Key OpenAI non configurata.")
                # from openai import OpenAI
                # client = OpenAI(api_key=OPENAI_API_KEY)
                # response = client.chat.completions.create(
                #     model=selected_model,
                #     messages=[
                #         {"role": "system", "content": system_prompt_content},
                #         {"role": "user", "content": user_prompt}
                #     ],
                #     temperature=0.7,
                #     max_tokens=4000
                # )
                # testo_resultante = response.choices[0].message.content
                # input_tokens = response.usage.prompt_tokens
                # output_tokens = response.usage.completion_tokens
                # logging.info("Risposta ricevuta da OpenAI.")
                # return testo_resultante, input_tokens, output_tokens

            else:
                logging.error(f"Modello '{selected_model}' non gestito per PPTX.")
                return f"Errore: Modello '{selected_model}' non supportato."

        except requests.exceptions.ConnectionError:
             logging.error(f"Impossibile connettersi a Ollama: {OLLAMA_ENDPOINT}")
             return f"Errore di connessione a Ollama ({OLLAMA_ENDPOINT}). Verifica che sia in esecuzione."
        except requests.exceptions.Timeout:
             logging.error(f"Timeout durante connessione a Ollama ({selected_model})")
             return f"Timeout Ollama ({selected_model}). Il modello potrebbe essere lento o non rispondere."
        except Exception as e:
             logging.exception(f"Errore API durante la generazione del testo per PPTX con {selected_model}")
             return f"Errore API ({type(e).__name__}): {str(e)}"


    @staticmethod
    def creaPresentazione(parent, transcriptionTextArea, num_slide, company_name, language, template_path=None):
        """Metodo principale chiamato dall'UI per creare la presentazione."""
        testo_attuale = transcriptionTextArea.toPlainText()
        if not testo_attuale.strip():
            if hasattr(parent, 'show_status_message'):
                parent.show_status_message("Inserisci del testo prima di generare.", error=True)
            return

        save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione Come", "", "PowerPoint Presentation (*.pptx)")
        if not save_path:
            if hasattr(parent, 'show_status_message'):
                parent.show_status_message("Salvataggio annullato.", error=True)
            return

        wait_msg = QMessageBox(QMessageBox.Icon.Information, "Elaborazione", "Generazione del testo AI in corso...", QMessageBox.StandardButton.NoButton, parent)
        wait_msg.setWindowModality(Qt.WindowModality.WindowModal)
        wait_msg.show()
        QApplication.processEvents()

        try:
            result_tuple = PptxGeneration.generaTestoPerSlide(testo_attuale, num_slide, company_name, language)
            wait_msg.close()

            if not isinstance(result_tuple, tuple) or len(result_tuple) != 3:
                QMessageBox.critical(parent, "Errore Generazione Testo", f"Impossibile generare il contenuto.\nErrore: {result_tuple}")
                return

            testo_per_slide, _, _ = result_tuple

            # Passa num_slides alla creazione del PPTX per il troncamento
            PptxGeneration.createPresentationFromText(parent, testo_per_slide, save_path, template_path, num_slides=num_slide)

        except Exception as e:
             wait_msg.close()
             logging.exception("Errore in creaPresentazione")
             QMessageBox.critical(parent, "Errore Imprevisto", f"Errore durante la creazione: {e}")


    @staticmethod
    def _find_placeholder(slide, placeholder_type):
        """Trova il primo placeholder di un tipo specifico."""
        for shape in slide.placeholders:
            if shape.placeholder_format.type == placeholder_type:
                return shape
        return None

    @staticmethod
    def _find_content_placeholder(slide):
        """Trova il placeholder principale per il contenuto, cercando BODY o OBJECT."""
        logging.info(f"Cerco placeholder BODY in '{slide.slide_layout.name}'")
        placeholders = [p for p in slide.placeholders if p.placeholder_format.type == PP_PLACEHOLDER.BODY]
        if placeholders:
            logging.info(f"Trovati {len(placeholders)} placeholder BODY.")
            return max(placeholders, key=lambda p: p.width * p.height) if len(placeholders) > 1 else placeholders[0]

        logging.info(f"Nessun placeholder BODY trovato. Cerco placeholder OBJECT.")
        placeholders = [p for p in slide.placeholders if p.placeholder_format.type == PP_PLACEHOLDER.OBJECT]
        if placeholders:
            logging.info(f"Trovati {len(placeholders)} placeholder OBJECT.")
            return max(placeholders, key=lambda p: p.width * p.height) if len(placeholders) > 1 else placeholders[0]

        logging.warning("Nessun placeholder BODY o OBJECT trovato.")
        return None

    @staticmethod
    def _add_content_to_slide(slide, content_text, subtitle_text, subtitle_shape):
        """Aggiunge il contenuto principale (bullet points) a una slide."""
        body_shape = PptxGeneration._find_content_placeholder(slide)
        if not body_shape:
            logging.warning("Nessun placeholder per il contenuto (BODY o OBJECT) trovato nella slide.")
            return

        tf = body_shape.text_frame
        # Pulisci i paragrafi esistenti invece di cancellare l'intero textframe per preservare lo stile
        for para in tf.paragraphs:
            para.clear()

        # Rimuovi paragrafi extra
        while len(tf.paragraphs) > 1:
            tf._bodyPr.remove(tf.paragraphs[-1]._p)

        effective_content = ""
        if subtitle_text and not subtitle_shape:
            effective_content = subtitle_text + "\n\n"
        effective_content += content_text

        lines = effective_content.split('\n')
        p = tf.paragraphs[0]
        first_line_processed = False

        for line in lines:
            if not line.strip():
                continue

            clean_line = re.sub(r'^\s*[-*•]\s*', '', line)
            indent_level = (len(line) - len(line.lstrip(' '))) // 2

            if not first_line_processed:
                p.text = clean_line
                p.level = indent_level
                first_line_processed = True
            else:
                p = tf.add_paragraph()
                p.text = clean_line
                p.level = indent_level

    @staticmethod
    def _truncate_slides(slides_data, num_slides):
        """Tronca o avvisa se il numero di slide generate non corrisponde a quello richiesto."""
        if len(slides_data) > num_slides:
            logging.warning(f"L'AI ha generato {len(slides_data)} slide, ma ne sono state richieste {num_slides}. Tronco le slide extra.")
            return slides_data[:num_slides]
        elif len(slides_data) < num_slides:
            logging.warning(f"L'AI ha generato {len(slides_data)} slide, ma ne sono state richieste {num_slides}. Non verranno aggiunte slide vuote.")
        return slides_data

    @staticmethod
    def createPresentationFromText(parent, testo, output_file, template_path=None, num_slides=None, is_preview=False):
        """Crea il file .pptx dal testo strutturato generato dall'AI, rispettando il template."""
        logging.info(f"Tentativo di creare file PPTX: {output_file} con template: {template_path}")
        try:
            prs = Presentation(template_path) if template_path and os.path.exists(template_path) else Presentation()

            title_layouts = ["Title Slide", "Copertina", "Title"]
            content_layouts = ["Title and Content", "Contenuto", "Titolo e contenuto"]

            title_slide_layout = PptxGeneration._get_layout(prs, title_layouts)
            content_slide_layout = PptxGeneration._get_layout(prs, content_layouts)

            if not title_slide_layout or not content_slide_layout:
                QMessageBox.critical(parent, "Errore Template", "Layout 'Title Slide' o 'Title and Content' non trovati nel template.")
                return

            slides_data = []
            current_slide = None
            clean_text = re.sub(r'\*\*(Titolo|Sottotitolo|Contenuto):', r'\1:', testo, flags=re.IGNORECASE)

            for line in clean_text.splitlines():
                line_lower = line.lower()
                if line_lower.startswith('titolo:'):
                    if current_slide: slides_data.append(current_slide)
                    current_slide = {'titolo': line[len('titolo:'):].strip(), 'sottotitolo': '', 'contenuto': ''}
                elif current_slide and line_lower.startswith('sottotitolo:'):
                    current_slide['sottotitolo'] = line[len('sottotitolo:'):].strip()
                elif current_slide and line_lower.startswith('contenuto:'):
                    current_slide['contenuto'] = ""
                elif current_slide:
                    current_slide['contenuto'] += line + '\n'

            if current_slide: slides_data.append(current_slide)

            if not slides_data:
                if hasattr(parent, 'show_status_message'):
                    parent.show_status_message("Impossibile estrarre dati strutturati dal testo dell'AI.", error=True)
                return

            if num_slides is not None:
                slides_data = PptxGeneration._truncate_slides(slides_data, num_slides)

            if not slides_data:
                return

            # --- Gestione Prima Slide (Titolo) ---
            title_slide_data = slides_data.pop(0)
            slide = prs.slides.add_slide(title_slide_layout)
            if slide.shapes.title:
                slide.shapes.title.text = title_slide_data.get('titolo', '').strip()

            subtitle_text = title_slide_data.get('sottotitolo', '').strip()
            subtitle_shape = PptxGeneration._find_placeholder(slide, PP_PLACEHOLDER.SUBTITLE)
            if subtitle_text and subtitle_shape:
                subtitle_shape.text = subtitle_text

            # Aggiungi anche il contenuto alla prima slide, se presente
            content_text = title_slide_data.get('contenuto', '').strip()
            if content_text:
                PptxGeneration._add_content_to_slide(slide, content_text, subtitle_text, subtitle_shape)


            # --- Gestione Slide Successive (Contenuto) ---
            for slide_data in slides_data:
                slide = prs.slides.add_slide(content_slide_layout)
                if slide.shapes.title:
                    slide.shapes.title.text = slide_data.get('titolo', '').strip()
                subtitle_text = slide_data.get('sottotitolo', '').strip()
                subtitle_shape = PptxGeneration._find_placeholder(slide, PP_PLACEHOLDER.SUBTITLE)
                if subtitle_text and subtitle_shape:
                    subtitle_shape.text = subtitle_text
                content_text = slide_data.get('contenuto', '').strip()
                if content_text:
                    PptxGeneration._add_content_to_slide(slide, content_text, subtitle_text, subtitle_shape)

            if prs.slides:
                prs.save(output_file)
                logging.info(f"Presentazione salvata con successo: {output_file}")
                # Mostra il popup solo se non è un'anteprima
                if not is_preview:
                    if parent and hasattr(parent, 'show_status_message'):
                        parent.show_status_message(f"Presentazione generata e salvata: {os.path.basename(output_file)}")
                        reply = QMessageBox.question(parent, 'Apri File', 'Vuoi aprire la presentazione generata?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
                        if reply == QMessageBox.StandardButton.Yes:
                            try:
                                if sys.platform == "win32": os.startfile(output_file)
                                elif sys.platform == "darwin": subprocess.call(['open', output_file])
                                else: subprocess.call(['xdg-open', output_file])
                            except Exception as e:
                                logging.error(f"Impossibile aprire il file '{output_file}': {e}")
                                parent.show_status_message(f"Non è stato possibile aprire il file.", error=True)
            else:
                logging.warning("Nessuna slide è stata generata.")

        except Exception as e:
            logging.exception("Errore durante la creazione del file PPTX")
            if parent:
                QMessageBox.critical(parent, "Errore Creazione PPTX", f"Si è verificato un errore: {e}")

    @staticmethod
    def generate_preview(parent, testo, template_path=None, num_slides=None):
        """Genera un'anteprima della presentazione come immagini."""
        if sys.platform != "win32":
            QMessageBox.warning(parent, "Funzionalità non supportata", "La generazione dell'anteprima è supportata solo su Windows.")
            return None

        try:
            import win32com.client
        except ImportError:
            QMessageBox.critical(parent, "Dipendenza Mancante", "La libreria 'pywin32' è necessaria per l'anteprima. Installala con 'pip install pywin32'.")
            return None

        temp_pptx_file = None
        temp_image_dir = parent.get_temp_dir()
        image_paths = []

        try:
            # 1. Crea un file .pptx temporaneo
            temp_pptx_file = parent.get_temp_filepath(suffix=".pptx")

            # Passa num_slides per coerenza con la generazione finale e is_preview per disabilitare il popup
            PptxGeneration.createPresentationFromText(
                parent, testo, temp_pptx_file, template_path, num_slides=num_slides, is_preview=True
            )

            # 2. Usa COM per esportare le slide come immagini
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            presentation = powerpoint.Presentations.Open(temp_pptx_file, WithWindow=False)

            for i, slide in enumerate(presentation.Slides):
                image_path = os.path.join(temp_image_dir, f"slide_{i + 1}.png")
                slide.Export(image_path, "PNG")
                image_paths.append(image_path)

            presentation.Close()
            powerpoint.Quit()

            return image_paths

        except Exception as e:
            logging.exception("Errore durante la generazione dell'anteprima")
            QMessageBox.critical(parent, "Errore Anteprima", f"Si è verificato un errore: {e}")
            return None
        finally:
            # Pulizia file temporaneo
            if temp_pptx_file and os.path.exists(temp_pptx_file):
                os.remove(temp_pptx_file)
