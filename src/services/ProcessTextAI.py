# File: src/services/ProcessTextAI.py

import anthropic
import google.generativeai as genai
import requests
import json
import logging
import os
from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

# Importa la configurazione delle azioni e le chiavi/endpoint necessari
from src.config import (
    OLLAMA_ENDPOINT, get_api_key, get_model_for_action,
    PROMPT_TEXT_SUMMARY, PROMPT_TEXT_FIX, PROMPT_YOUTUBE_SUMMARY
)

load_dotenv()

class ProcessTextAI(QThread):
    """
    Thread per elaborare testo (riassumere o correggere) utilizzando
    il modello AI selezionato nelle impostazioni (Claude, Gemini, Ollama).
    """
    progress = pyqtSignal(int, str) # Segnale per aggiornamenti di progresso (percentuale, messaggio)
    completed = pyqtSignal(str)     # Segnale emesso con il testo elaborato al completamento
    error = pyqtSignal(str)        # Segnale emesso in caso di errore

    def __init__(self, text, language, mode="summary", parent=None):
        """
        Inizializza il thread.

        Args:
            text (str): Il testo da elaborare.
            language (str): La lingua del testo (es. "italiano", "inglese").
            mode (str): La modalità di elaborazione ("summary" o "fix"). Default: "summary".
            parent (QObject, optional): Il parent Qt. Defaults to None.
        """
        super().__init__(parent)
        self.text = text
        self.language = language
        self.result = None
        # Valida la modalità
        if mode not in ["summary", "fix", "youtube_summary"]:
            raise ValueError("La modalità deve essere 'summary', 'fix' o 'youtube_summary'")
        self.mode = mode

        # Recupera il modello selezionato per l'azione 'text_processing'
        self.selected_model = get_model_for_action('text_processing')
        self.anthropic_api_key = get_api_key('anthropic')
        self.google_api_key = get_api_key('google')
        self.ollama_endpoint = OLLAMA_ENDPOINT

        logging.info(f"ProcessTextAI ({self.mode}) inizializzato con modello: {self.selected_model}")

    def run(self):
        """Esegue l'elaborazione del testo nel thread."""
        try:
            self.progress.emit(10, f"Avvio elaborazione testo ({self.mode}) con {self.selected_model}...")

            # Chiama il metodo unificato per l'elaborazione
            result_data = self._process_text_with_selected_model(self.text)

            # Controlla il risultato
            if isinstance(result_data, tuple) and len(result_data) == 3:
                self.result, input_tokens, output_tokens = result_data
                self.progress.emit(100, "Elaborazione completata!")
                self.completed.emit(self.result)
                logging.info(f"Elaborazione Testo ({self.mode}) - Token Input: {input_tokens}, Token Output: {output_tokens}")
            else:
                # Se il metodo ritorna un errore (stringa)
                error_msg = f"Errore durante l'elaborazione del testo: {result_data}"
                logging.error(error_msg)
                self.error.emit(error_msg)

        except Exception as e:
            error_msg = f"Errore imprevisto durante l'elaborazione del testo ({self.mode}): {str(e)}"
            logging.exception(error_msg) # Logga l'intero traceback
            self.error.emit(error_msg)

    def _process_text_with_selected_model(self, text_to_process):
        """
        Metodo interno che seleziona l'API corretta e processa il testo.
        Restituisce una tupla (testo_risultante, input_tokens, output_tokens) o una stringa di errore.
        """
        # 1. Scegli il file del prompt corretto in base alla modalità
        if self.mode == "summary":
            prompt_file_path = PROMPT_TEXT_SUMMARY
        elif self.mode == "fix":
            prompt_file_path = PROMPT_TEXT_FIX
        elif self.mode == "youtube_summary":
            prompt_file_path = PROMPT_YOUTUBE_SUMMARY
        else:
            # Questo non dovrebbe accadere grazie alla validazione nel __init__
            error_msg = f"Modalità non valida: {self.mode}"
            logging.error(error_msg)
            return error_msg

        if not prompt_file_path or not os.path.exists(prompt_file_path):
             error_msg = f"File prompt non trovato per la modalità '{self.mode}': {prompt_file_path}"
             logging.error(error_msg)
             return error_msg # Ritorna l'errore invece di sollevare eccezione subito

        # 2. Leggi e formatta il prompt
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            system_prompt_content = prompt_template.format(language=self.language)
        except Exception as e:
            logging.exception(f"Errore lettura/formattazione prompt '{prompt_file_path}'")
            return f"Errore lettura prompt ({self.mode}): {e}"

        # L'input effettivo per l'LLM
        user_prompt = f"Testo da elaborare ({self.mode}):\n{text_to_process}\n\n---\nOutput:"

        # 3. Selezione e chiamata API
        model_name_lower = self.selected_model.lower()
        logging.debug(f"Tentativo elaborazione testo ({self.mode}) con modello: {self.selected_model}")

        try:
            if "ollama:" in model_name_lower:
                # --- Logica per Ollama ---
                logging.info(f"Usando Ollama ({self.selected_model}) per {self.mode}.")
                self.progress.emit(30, f"Invio a Ollama ({self.mode})...")
                ollama_model_name = self.selected_model.split(":", 1)[1]
                api_url = f"{self.ollama_endpoint}/api/generate"
                full_prompt = f"{system_prompt_content}\n\n{user_prompt}" # Combina system e user prompt
                payload = {"model": ollama_model_name, "prompt": full_prompt, "stream": False, "system": system_prompt_content}

                response = requests.post(api_url, json=payload, timeout=300) # Timeout 5 min
                response.raise_for_status()
                response_data = response.json()
                self.progress.emit(80, f"Ricevuta risposta da Ollama ({self.mode})...")
                result_text = response_data.get("response", "").strip()
                if not result_text:
                    error_details = response_data.get("error", "Risposta vuota.")
                    raise Exception(f"Ollama ha restituito un errore o una risposta vuota: {error_details}")
                logging.info(f"Ollama ({self.mode}) completato.")
                return result_text, 0, 0 # Token non disponibili

            elif "gemini" in model_name_lower:
                # --- Logica per Google Gemini ---
                logging.info(f"Usando Gemini ({self.selected_model}) per {self.mode}.")
                if not self.google_api_key: raise ValueError("API Key Google non configurata.")
                self.progress.emit(30, f"Invio a Gemini ({self.mode})...")
                genai.configure(api_key=self.google_api_key)
                model = genai.GenerativeModel(self.selected_model, system_instruction=system_prompt_content)
                response = model.generate_content(user_prompt) # Passa solo user prompt
                self.progress.emit(80, f"Ricevuta risposta da Gemini ({self.mode})...")
                try:
                    result_text = response.text
                except ValueError as ve:
                     logging.warning(f"Possibile blocco risposta Gemini ({self.mode}): {ve}. Dettagli: {response.prompt_feedback}")
                     raise Exception(f"Risposta da Gemini bloccata o non valida ({self.mode}). Causa: {response.prompt_feedback}")
                logging.info(f"Gemini ({self.mode}) completato.")
                return result_text, 0, 0 # Token non disponibili facilmente

            elif "claude" in model_name_lower:
                # --- Logica per Anthropic Claude ---
                logging.info(f"Usando Claude ({self.selected_model}) per {self.mode}.")
                if not self.anthropic_api_key: raise ValueError("API Key Anthropic non configurata.")
                self.progress.emit(30, f"Invio a Claude ({self.mode})...")
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                message = client.messages.create(
                    model=self.selected_model,
                    max_tokens=8192, # Massimo per Claude 3.5
                    temperature=0.7,
                    system=system_prompt_content,
                    messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}]
                )
                self.progress.emit(80, f"Ricevuta risposta da Claude ({self.mode})...")
                if message.stop_reason == 'max_tokens':
                     logging.warning(f"Risposta Claude ({self.mode}) troncata per max_tokens.")

                testo_resultante = message.content[0].text
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                logging.info(f"Claude ({self.mode}) completato.")
                return testo_resultante, input_tokens, output_tokens

            # Aggiungere qui blocchi elif per altri provider se necessario (es. OpenAI)

            else:
                logging.error(f"Modello '{self.selected_model}' non gestito per l'elaborazione testo.")
                return f"Errore: Modello '{self.selected_model}' non supportato."

        # Gestione eccezioni API specifiche
        except requests.exceptions.ConnectionError:
             logging.error(f"Impossibile connettersi a Ollama: {self.ollama_endpoint}")
             return f"Errore di connessione a Ollama ({self.ollama_endpoint}). Verifica che sia in esecuzione."
        except requests.exceptions.Timeout:
             logging.error(f"Timeout durante connessione a Ollama ({self.selected_model})")
             return f"Timeout Ollama ({self.selected_model}). Il modello potrebbe essere lento o non rispondere."
        except Exception as e:
             # Errore generico durante la chiamata API
             logging.exception(f"Errore API durante l'elaborazione testo ({self.mode}) con {self.selected_model}")
             return f"Errore API ({type(e).__name__}): {str(e)}"