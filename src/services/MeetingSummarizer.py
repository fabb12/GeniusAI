# File: src/services/MeetingSummarizer.py

import anthropic
import google.generativeai as genai
import requests
import json
import logging
import os
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from dotenv import load_dotenv

# Importa la configurazione delle azioni e le chiavi/endpoint necessari
from src.config import (
    ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, get_api_key,
    PROMPT_MEETING_SUMMARY # Assicurati che questo percorso sia corretto
)

load_dotenv()

class MeetingSummarizer(QThread):
    """
    Thread per generare un riassunto strutturato di una trascrizione di riunione
    utilizzando il modello AI selezionato (Claude, Gemini, Ollama).
    """
    update_progress = pyqtSignal(int, str) # Segnale (percentuale, messaggio)
    process_complete = pyqtSignal(str)     # Segnale con il riassunto completato
    process_error = pyqtSignal(str)        # Segnale in caso di errore

    def __init__(self, text, language, parent=None):
        """
        Inizializza il thread del riassuntore.

        Args:
            text (str): La trascrizione della riunione da riassumere.
            language (str): La lingua del testo e del riassunto desiderato.
            parent (QObject, optional): Il parent Qt. Defaults to None.
        """
        super().__init__(parent)
        self.text = text
        self.language = language
        self.result = None

        # Recupera le impostazioni e le chiavi API
        settings = QSettings("ThemaConsulting", "GeniusAI")
        config_summary = ACTION_MODELS_CONFIG.get('summary') # Usa la chiave 'summary'
        if not config_summary:
            raise ValueError("Configurazione 'summary' non trovata in config.py")

        setting_key = config_summary.get('setting_key')
        default_model = config_summary.get('default')
        if not setting_key or not default_model:
            raise ValueError("Configurazione 'summary' incompleta (manca setting_key o default).")

        self.selected_model = settings.value(setting_key, default_model)
        self.anthropic_api_key = get_api_key('anthropic')
        self.google_api_key = get_api_key('google')
        self.ollama_endpoint = OLLAMA_ENDPOINT

        logging.info(f"MeetingSummarizer inizializzato con modello: {self.selected_model}")

    def run(self):
        """Esegue la generazione del riassunto nel thread."""
        try:
            self.update_progress.emit(10, f"Avvio riassunto meeting ({self.selected_model})...")

            # Chiama il metodo unificato per l'elaborazione
            result_data = self._summarize_with_selected_model(self.text)

            # Controlla il risultato
            if isinstance(result_data, tuple) and len(result_data) == 3:
                self.result, input_tokens, output_tokens = result_data
                self.update_progress.emit(100, "Riassunto completato!")
                self.process_complete.emit(self.result)
                logging.info(f"Riassunto Meeting - Token Input: {input_tokens}, Token Output: {output_tokens}")
            else:
                # Se il metodo ritorna un errore (stringa)
                error_msg = f"Errore durante la generazione del riassunto: {result_data}"
                logging.error(error_msg)
                self.process_error.emit(error_msg)

        except Exception as e:
            error_msg = f"Errore imprevisto durante il riassunto meeting: {str(e)}"
            logging.exception(error_msg) # Logga l'intero traceback
            self.process_error.emit(error_msg)

    def _summarize_with_selected_model(self, text_to_summarize):
        """
        Metodo interno che seleziona l'API corretta e genera il riassunto.
        Restituisce una tupla (testo_riassunto, input_tokens, output_tokens) o una stringa di errore.
        """
        # 1. Verifica percorso prompt
        if not PROMPT_MEETING_SUMMARY or not os.path.exists(PROMPT_MEETING_SUMMARY):
             error_msg = f"File prompt non trovato per riassunto meeting: {PROMPT_MEETING_SUMMARY}"
             logging.error(error_msg)
             return error_msg

        # 2. Leggi e formatta il prompt
        try:
            with open(PROMPT_MEETING_SUMMARY, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            system_prompt_content = prompt_template.format(language=self.language)
        except Exception as e:
            logging.exception(f"Errore lettura/formattazione prompt '{PROMPT_MEETING_SUMMARY}'")
            return f"Errore lettura prompt riassunto: {e}"

        # L'input effettivo per l'LLM
        user_prompt = f"Trascrizione della riunione:\n{text_to_summarize}\n\n---\nGenera il riassunto come richiesto."

        # 3. Selezione e chiamata API
        model_name_lower = self.selected_model.lower()
        logging.debug(f"Tentativo riassunto meeting con modello: {self.selected_model}")
        self.update_progress.emit(20, f"Preparazione richiesta per {self.selected_model}...")

        try:
            if "ollama:" in model_name_lower:
                # --- Logica per Ollama ---
                logging.info(f"Usando Ollama ({self.selected_model}) per riassunto meeting.")
                self.update_progress.emit(40, f"Invio a Ollama...")
                ollama_model_name = self.selected_model.split(":", 1)[1]
                api_url = f"{self.ollama_endpoint}/api/generate"
                # Combina system e user prompt per Ollama
                full_prompt = f"{system_prompt_content}\n\n{user_prompt}"
                payload = {"model": ollama_model_name, "prompt": full_prompt, "stream": False, "system": system_prompt_content}

                response = requests.post(api_url, json=payload, timeout=300) # Timeout 5 min
                response.raise_for_status()
                response_data = response.json()
                self.update_progress.emit(85, f"Ricevuta risposta da Ollama...")
                result_text = response_data.get("response", "").strip()
                if not result_text:
                    error_details = response_data.get("error", "Risposta vuota.")
                    raise Exception(f"Ollama ha restituito un errore o una risposta vuota: {error_details}")
                logging.info(f"Ollama riassunto meeting completato.")
                return result_text, 0, 0 # Token non disponibili

            elif "gemini" in model_name_lower:
                # --- Logica per Google Gemini ---
                logging.info(f"Usando Gemini ({self.selected_model}) per riassunto meeting.")
                if not self.google_api_key: raise ValueError("API Key Google non configurata.")
                self.update_progress.emit(40, f"Invio a Gemini...")
                genai.configure(api_key=self.google_api_key)
                # Passa le istruzioni di sistema direttamente al modello
                model = genai.GenerativeModel(self.selected_model, system_instruction=system_prompt_content)
                # Invia solo il prompt dell'utente
                response = model.generate_content(user_prompt)
                self.update_progress.emit(85, f"Ricevuta risposta da Gemini...")
                try:
                    result_text = response.text.strip()
                except ValueError as ve:
                     logging.warning(f"Possibile blocco risposta Gemini (riassunto): {ve}. Feedback: {response.prompt_feedback}")
                     raise Exception(f"Risposta da Gemini bloccata o non valida (riassunto). Causa: {response.prompt_feedback}")
                except AttributeError: # Se response.text non esiste
                     logging.error(f"Attributo 'text' non trovato nella risposta Gemini (riassunto). Risposta: {response}")
                     raise Exception("Formato risposta Gemini inatteso (manca .text).")

                logging.info(f"Gemini riassunto meeting completato.")
                return result_text, 0, 0 # Token non disponibili facilmente

            elif "claude" in model_name_lower:
                # --- Logica per Anthropic Claude ---
                logging.info(f"Usando Claude ({self.selected_model}) per riassunto meeting.")
                if not self.anthropic_api_key: raise ValueError("API Key Anthropic non configurata.")
                self.update_progress.emit(40, f"Invio a Claude...")
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                message = client.messages.create(
                    model=self.selected_model,
                    max_tokens=4096, # Massimo per Claude 3.5
                    temperature=0.7,
                    system=system_prompt_content, # Usa prompt di sistema
                    messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}] # Passa testo come user
                )
                self.update_progress.emit(85, f"Ricevuta risposta da Claude...")
                if message.stop_reason == 'max_tokens':
                     logging.warning(f"Risposta Claude (riassunto) troncata per max_tokens.")

                testo_resultante = message.content[0].text.strip()
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                logging.info(f"Claude riassunto meeting completato.")
                return testo_resultante, input_tokens, output_tokens

            # Aggiungere qui blocchi elif per altri provider se necessario

            else:
                logging.error(f"Modello '{self.selected_model}' non gestito per il riassunto meeting.")
                return f"Errore: Modello '{self.selected_model}' non supportato."

        # Gestione eccezioni API specifiche
        except requests.exceptions.ConnectionError:
             logging.error(f"Impossibile connettersi a Ollama: {self.ollama_endpoint}")
             return f"Errore di connessione a Ollama ({self.ollama_endpoint}). Verifica che sia in esecuzione."
        except requests.exceptions.Timeout:
             logging.error(f"Timeout durante connessione a Ollama ({self.selected_model}) per riassunto")
             return f"Timeout Ollama ({self.selected_model}). Il modello potrebbe essere lento o non rispondere."
        except Exception as e:
             # Errore generico durante la chiamata API
             logging.exception(f"Errore API durante riassunto meeting con {self.selected_model}")
             return f"Errore API ({type(e).__name__}): {str(e)}"