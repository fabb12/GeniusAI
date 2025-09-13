# File: src/services/PptxGeneration.py

import anthropic
import google.generativeai as genai
import requests
import json
import logging
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import QSettings
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
    ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, get_api_key,
    PROMPT_PPTX_GENERATION # Assicurati che questo percorso sia corretto e il file esista
)

load_dotenv() # Carica .env se necessario

class PptxGeneration:
    """
    Classe statica per gestire la generazione di presentazioni PowerPoint
    utilizzando diversi modelli AI (Claude, Gemini, Ollama) basati sulle impostazioni.
    """

    @staticmethod
    def impostaFont(shape, size_pt, text):
        """Imposta il font per un dato shape (helper interno)."""
        try:
            text_frame = shape.text_frame
            # Pulisce il testo predefinito se necessario
            if len(text_frame.paragraphs) == 1 and text_frame.paragraphs[0].text != text and not text_frame.paragraphs[0].runs:
                 text_frame.paragraphs[0].text = "" # Pulisce il testo placeholder
            # Aggiunge o modifica il run
            if not text_frame.paragraphs or not text_frame.paragraphs[0].runs:
                 p = text_frame.paragraphs[0] if text_frame.paragraphs else text_frame.add_paragraph()
                 run = p.add_run()
            else: # Modifica il primo run esistente
                 run = text_frame.paragraphs[0].runs[0]
            run.text = text
            font = run.font
            font.name = 'Calibri' # O un altro font standard
            font.size = Pt(size_pt)
            return run # Ritorna il run per eventuali modifiche successive (bold, color)
        except Exception as e:
            logging.warning(f"Errore in impostaFont: {e}")
            return None

    @staticmethod
    def _aggiungi_paragrafo_formattato(shape_or_tf, text, size_pt, bold=False, color=None, bullet=False, level=0):
        """Aggiunge un paragrafo formattato a uno shape o text_frame."""
        try:
            # Determina se è uno shape o un text_frame
            if hasattr(shape_or_tf, 'text_frame'):
                tf = shape_or_tf.text_frame
                # Pulisce il testo predefinito del placeholder se è la prima aggiunta
                # e il testo non è vuoto e non ci sono già run.
                if len(tf.paragraphs) == 1 and tf.paragraphs[0].text != '' and not tf.paragraphs[0].runs and text:
                    tf.paragraphs[0].text = ""
                    tf.paragraphs[0].level = 0 # Resetta livello
                    tf.paragraphs[0].font.size = None # Resetta font
            elif hasattr(shape_or_tf, 'add_paragraph'): # È un text_frame
                tf = shape_or_tf
            else:
                logging.error("Oggetto non valido passato a _aggiungi_paragrafo_formattato")
                return None

            p = tf.add_paragraph()
            p.text = text.strip() # Imposta il testo direttamente
            p.font.name = 'Calibri'
            p.font.size = Pt(size_pt)
            p.font.bold = bold
            if color:
                p.font.color.rgb = RGBColor(*color)
            if bullet:
                p.level = level
            return p
        except Exception as e:
             logging.warning(f"Errore in _aggiungi_paragrafo_formattato: {e}")
             return None

    @staticmethod
    def _aggiungi_footer(slide):
        """Aggiunge un footer standard a una slide."""
        left, top, width, height = Inches(0.5), Inches(7.0), Inches(9.0), Inches(0.5)
        try:
            footer_box = slide.shapes.add_textbox(left, top, width, height)
            tf = footer_box.text_frame
            p = tf.paragraphs[0]
            p.text = "Made by GeniusAI"
            p.font.name = 'Calibri'
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(128, 128, 128) # Grigio
            # Utilizza l'enumerazione corretta se disponibile o il valore intero
            try:
                 from pptx.enum.text import PP_ALIGN
                 p.alignment = PP_ALIGN.CENTER
            except ImportError:
                 p.alignment = 2 # Valore intero per centro
        except Exception as e:
            logging.warning(f"Impossibile aggiungere footer: {e}")

    @staticmethod
    def _find_placeholder(slide, placeholder_types):
        """Trova il primo placeholder che corrisponde a uno dei tipi dati."""
        for shape in slide.placeholders:
            for p_type in placeholder_types:
                if shape.placeholder_format.type == p_type:
                    return shape
        return None

    @staticmethod
    def createPresentationFromFile(parent, file_path, num_slide, company_name, language):
        """Crea una presentazione leggendo il testo sorgente da un file."""
        try:
            logging.info(f"Tentativo di creare presentazione da file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                testo = file.read()

            if not testo.strip():
                QMessageBox.warning(parent, "File Vuoto", "Il file selezionato è vuoto.")
                return

            # Chiama la logica di generazione del testo
            result_tuple = PptxGeneration.generaTestoPerSlide(testo, num_slide, company_name, language)

            # Controlla il risultato della chiamata API
            if not isinstance(result_tuple, tuple) or len(result_tuple) != 3:
                 # L'errore è già stato loggato in generaTestoPerSlide
                 QMessageBox.critical(parent, "Errore API", f"Errore durante la generazione del testo per le slide.\nDettagli:\n{result_tuple}")
                 return

            testo_per_slide, input_tokens, output_tokens = result_tuple
            logging.info(f"Generazione testo PPTX da file - Token Input: {input_tokens}, Token Output: {output_tokens}")

            # Chiedi dove salvare il file
            save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione", "",
                                                       "PowerPoint Presentation (*.pptx)")
            if save_path:
                # Crea il file PPTX
                PptxGeneration.createPresentationFromText(parent, testo_per_slide, save_path)
            else:
                QMessageBox.warning(parent, "Attenzione", "Salvataggio annullato. Nessun file selezionato.")
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
        # 1. Leggi le impostazioni per ottenere il modello selezionato
        settings = QSettings("ThemaConsulting", "GeniusAI")
        config_pptx = ACTION_MODELS_CONFIG.get('pptx_generation')
        if not config_pptx:
            logging.error("Configurazione 'pptx_generation' non trovata in config.py")
            return "Errore di configurazione: 'pptx_generation' mancante."

        setting_key = config_pptx.get('setting_key')
        default_model = config_pptx.get('default')
        if not setting_key or not default_model:
             logging.error("Configurazione 'pptx_generation' incompleta in config.py (manca setting_key o default).")
             return "Errore di configurazione: 'pptx_generation' incompleta."

        selected_model = settings.value(setting_key, default_model)
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
    def creaPresentazione(parent, transcriptionTextArea, num_slide, company_name, language):
        """Metodo principale chiamato dall'UI per creare la presentazione."""
        testo_attuale = transcriptionTextArea.toPlainText()
        if not testo_attuale.strip():
            QMessageBox.warning(parent, "Testo Mancante", "Inserisci del testo nell'area di trascrizione prima di generare la presentazione.")
            return

        save_path, _ = QFileDialog.getSaveFileName(parent, "Salva Presentazione Come", "",
                                                   "PowerPoint Presentation (*.pptx)")
        if not save_path:
            QMessageBox.information(parent, "Annullato", "Operazione di salvataggio annullata.")
            return

        # Mostra un messaggio di attesa
        wait_msg = QMessageBox(QMessageBox.Icon.Information, "Elaborazione", "Generazione del testo per la presentazione in corso...", QMessageBox.StandardButton.NoButton, parent)
        wait_msg.setWindowModality(Qt.WindowModality.WindowModal)
        wait_msg.show()
        QApplication.processEvents() # Forza l'aggiornamento UI

        try:
            # Chiama la funzione per generare il testo con gestione errori inclusa
            result_tuple = PptxGeneration.generaTestoPerSlide(testo_attuale, num_slide, company_name, language)
            wait_msg.close() # Chiudi il messaggio di attesa

            # Controlla il risultato
            if not isinstance(result_tuple, tuple) or len(result_tuple) != 3:
                QMessageBox.critical(parent, "Errore Generazione Testo", f"Impossibile generare il contenuto della presentazione.\nErrore: {result_tuple}")
                return

            testo_per_slide, input_tokens, output_tokens = result_tuple
            logging.info(f"Generazione testo PPTX completata - Tokens In: {input_tokens}, Out: {output_tokens}")

            # Crea la presentazione dal testo generato
            # Questo metodo ora contiene la logica di salvataggio e apertura
            PptxGeneration.createPresentationFromText(parent, testo_per_slide, save_path)

        except Exception as e:
             wait_msg.close() # Assicurati che il messaggio di attesa sia chiuso anche in caso di errore
             logging.exception("Errore in creaPresentazione")
             QMessageBox.critical(parent, "Errore Imprevisto", f"Si è verificato un errore durante la creazione della presentazione: {e}")


    @staticmethod
    def createPresentationFromText(parent, testo, output_file, template_path=None):
        """Crea il file .pptx dal testo strutturato generato dall'AI."""
        logging.info(f"Tentativo di creare file PPTX: {output_file}")
        try:
            if template_path and os.path.exists(template_path):
                logging.info(f"Utilizzo del template: {template_path}")
                prs = Presentation(template_path)
            else:
                logging.info("Nessun template valido fornito, utilizzo un layout di default.")
                prs = Presentation()

            # Layout comuni (potrebbero variare leggermente tra versioni PPTX)
            title_slide_layout = prs.slide_layouts[0] # Slide titolo
            content_slide_layout = prs.slide_layouts[1] # Slide Titolo e Contenuto
            # blank_slide_layout = prs.slide_layouts[6] # Slide vuota

            # --- Parsing del testo generato dall'AI ---
            # Pulizia preliminare
            clean_text = re.sub(r'\*\*(Titolo|Sottotitolo|Contenuto):', r'\1:', testo, flags=re.IGNORECASE)
            clean_text = re.sub(r'^\s*-\s*', '', clean_text, flags=re.MULTILINE)
            clean_text = re.sub(r'[•*]\s*', '- ', clean_text) # Normalizza bullet a trattino

            # Pattern robusto
            pattern = re.compile(r"Titolo:\s*(.*?)\s*(?:Sottotitolo:\s*(.*?)\s*)?Contenuto:\s*(.*?)(?=\n\s*Titolo:|\Z)", re.DOTALL | re.IGNORECASE)
            slides_data = pattern.findall(clean_text)

            if not slides_data:
                 QMessageBox.warning(parent, "Errore di Parsing", "Impossibile estrarre dati strutturati dal testo generato dall'AI.\nLa presentazione non può essere creata.\n\nTesto ricevuto:\n" + testo[:500] + "...")
                 return

            # --- Creazione Slide ---
            for index, (titolo_text, sottotitolo_text, contenuto_text) in enumerate(slides_data):
                titolo_text = titolo_text.strip() if titolo_text else f"Slide {index + 1}"
                sottotitolo_text = sottotitolo_text.strip() if sottotitolo_text else ""
                contenuto_text = contenuto_text.strip() if contenuto_text else ""

                logging.debug(f"Creazione Slide {index + 1}: Titolo='{titolo_text}', Sottotitolo='{sottotitolo_text}'")

                if index == 0: # Prima slide di titolo
                    slide = prs.slides.add_slide(title_slide_layout)
                    title = slide.shapes.title

                    # Cerca un placeholder per il sottotitolo in modo robusto
                    subtitle_placeholder_types = [
                        PP_PLACEHOLDER.SUBTITLE,
                        PP_PLACEHOLDER.CENTER_TITLE,
                        PP_PLACEHOLDER.BODY
                    ]
                    subtitle = PptxGeneration._find_placeholder(slide, subtitle_placeholder_types)

                    if title:
                        PptxGeneration.impostaFont(title, 44, titolo_text).bold = True
                    if subtitle and sottotitolo_text:
                        PptxGeneration.impostaFont(subtitle, 32, sottotitolo_text)
                else: # Slide di contenuto
                    slide = prs.slides.add_slide(content_slide_layout)
                    title = slide.shapes.title

                    # Cerca un placeholder per il corpo del testo
                    content_placeholder = PptxGeneration._find_placeholder(slide, [PP_PLACEHOLDER.BODY])

                    if title:
                        PptxGeneration.impostaFont(title, 36, titolo_text).bold = True

                    if content_placeholder and content_placeholder.has_text_frame:
                        tf = content_placeholder.text_frame
                        tf.clear() # Pulisce placeholder
                        tf.word_wrap = True

                        # Aggiungi sottotitolo se presente
                        if sottotitolo_text:
                            p_sub = PptxGeneration._aggiungi_paragrafo_formattato(tf, sottotitolo_text, 24, color=(80, 80, 80))
                            if p_sub: p_sub.space_after = Pt(12)

                        # Aggiungi contenuto principale
                        lines = [line.strip() for line in contenuto_text.split('\n') if line.strip()]
                        for line in lines:
                            level = 0
                            is_bullet = False
                            cleaned_line = line

                            # Rileva bullet e livello indentazione
                            indent_match = re.match(r"^(\s*)(- |> |# )\s*", line)
                            if indent_match:
                                indent_space = len(indent_match.group(1))
                                level = indent_space // 2 # Stima livello base (2 spazi per livello)
                                cleaned_line = line[len(indent_match.group(0)):].strip()
                                is_bullet = True

                            # Gestione "Titolo Sezione: Testo" (euristica)
                            section_match = re.match(r"^(.*?):\s+(.*)", cleaned_line)
                            if section_match and len(section_match.group(1)) < 50 and not is_bullet:
                                 heading_text = section_match.group(1).strip() + ":"
                                 body_text = section_match.group(2).strip()
                                 p_head = PptxGeneration._aggiungi_paragrafo_formattato(tf, heading_text, 20, bold=True, level=level)
                                 if p_head and body_text:
                                      # Aggiunge il corpo dopo il titolo sezione nello stesso paragrafo o uno nuovo
                                      # Per semplicità, lo mettiamo in un nuovo paragrafo indentato
                                      PptxGeneration._aggiungi_paragrafo_formattato(tf, body_text, 18, level=level+1 if level < 5 else 5)
                            else:
                                # Riga normale o bullet
                                PptxGeneration._aggiungi_paragrafo_formattato(tf, cleaned_line, 18, bullet=is_bullet, level=level)

                    else:
                        logging.warning(f"Placeholder di contenuto non trovato per slide {index + 1}")

            # Aggiungi footer a tutte le slide
            for slide in prs.slides:
                PptxGeneration._aggiungi_footer(slide)

            # --- Salvataggio e Feedback ---
            if prs.slides:
                prs.save(output_file)
                logging.info(f"Presentazione salvata con successo: {output_file}")
                QMessageBox.information(parent, "Successo",
                                        f"Presentazione generata e salvata:\n{output_file}")
                # Chiedi se aprire il file
                reply = QMessageBox.question(parent, 'Apri File',
                                             'Vuoi aprire la presentazione generata ora?',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                     try:
                          if sys.platform == "win32":
                              os.startfile(output_file)
                          elif sys.platform == "darwin": # macOS
                              subprocess.call(['open', output_file])
                          else: # linux variants
                              subprocess.call(['xdg-open', output_file])
                     except Exception as open_err:
                          logging.error(f"Impossibile aprire automaticamente il file '{output_file}': {open_err}")
                          QMessageBox.warning(parent, "Impossibile Aprire", f"Non è stato possibile aprire automaticamente il file.\nAprilo manualmente da:\n{output_file}")

            else:
                 # Questo caso è già gestito dal controllo su slides_data vuoto
                 logging.warning("Nessuna slide generata.")
                 # QMessageBox.warning(parent, "Attenzione", "Non sono state generate slides.")

        except Exception as e:
             logging.exception("Errore durante la creazione del file PPTX")
             QMessageBox.critical(parent, "Errore Creazione PPTX", f"Errore durante la creazione/salvataggio della presentazione: {e}")

    @staticmethod
    def generate_preview(parent, testo, template_path=None):
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
        temp_image_dir = tempfile.mkdtemp()
        image_paths = []

        try:
            # 1. Crea un file .pptx temporaneo
            fd, temp_pptx_file = tempfile.mkstemp(suffix=".pptx")
            os.close(fd)

            PptxGeneration.createPresentationFromText(parent, testo, temp_pptx_file, template_path)

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
