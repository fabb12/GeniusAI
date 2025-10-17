# File: src/services/FrameExtractor.py
import re
import anthropic
import google.generativeai as genai
import requests # Non strettamente necessario qui se non usi Ollama per vision, ma utile per consistenza
import json
import logging
import base64
import cv2
import numpy as np
import sys
import time # Per eventuali pause tra richieste API
from moviepy.editor import VideoFileClip
from tqdm import tqdm # Barra di progresso
import io
from PIL import Image

# Importa la configurazione delle azioni e le chiavi/endpoint necessari
from src.config import (
    OLLAMA_ENDPOINT, get_api_key, get_model_for_action,
    PROMPT_FRAMES_ANALYSIS, PROMPT_VIDEO_SUMMARY, PROMPT_OBJECT_RECOGNITION, PROMPT_SPECIFIC_OBJECT_RECOGNITION
)

class FrameExtractor:
    """
    Estrae frame da un video e li analizza usando un modello AI (vision) selezionato
    (Claude, Gemini). Genera anche un riassunto testuale del video.
    """
    def __init__(self, video_path, num_frames, analysis_mode='description', batch_size=5, api_keys=None, search_query=None):
        """
        Inizializza l'estrattore di frame.

        Args:
            video_path (str): Percorso del file video.
            num_frames (int): Numero di frame da estrarre uniformemente dal video.
            analysis_mode (str): La modalità di analisi ('description', 'object_recognition', 'specific_object_search').
            batch_size (int): Numero di frame da inviare all'API in ogni batch (per modelli cloud).
            api_keys (dict, optional): Dizionario contenente le API keys {'anthropic': '...', 'google': '...'}.
                                     Se None, le chiavi verranno lette dalla config globale.
            search_query (str, optional): La query di ricerca per la modalità 'specific_object_search'.
        """
        self.video_path = video_path
        self.num_frames = num_frames
        self.analysis_mode = analysis_mode
        self.search_query = search_query
        # Limita batch_size per Gemini che potrebbe avere limiti inferiori per chiamata
        self.batch_size = min(batch_size, 16) # Gemini ha un limite di 16 immagini per chiamata

        # Gestione API Keys
        api_keys = api_keys or {}
        self.anthropic_api_key = api_keys.get('anthropic', get_api_key('anthropic'))
        self.google_api_key = api_keys.get('google', get_api_key('google'))
        # self.ollama_endpoint = OLLAMA_ENDPOINT # Aggiungi se usi Ollama Vision

        # Recupera il modello selezionato per l'azione 'frame_extractor'
        self.selected_model = get_model_for_action('frame_extractor')
        logging.info(f"FrameExtractor inizializzato con modello: {self.selected_model}")

        # Inizializza il client corretto (verrà fatto nei metodi specifici)
        self.anthropic_client = None
        # Il client Gemini (genai) non richiede un'istanza persistente se configurato globalmente

        # Verifica prerequisiti
        if "gemini" in self.selected_model.lower() and not self.google_api_key:
             logging.warning("Modello Gemini selezionato ma GOOGLE_API_KEY non trovata.")
        if "claude" in self.selected_model.lower() and not self.anthropic_api_key:
             logging.warning("Modello Claude selezionato ma ANTHROPIC_API_KEY non trovata.")
        # Aggiungere controllo per Ollama se implementato

    def _init_anthropic_client(self):
        """Inizializza il client Anthropic se non già fatto."""
        if not self.anthropic_client and self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        elif not self.anthropic_api_key:
             raise ValueError("API Key Anthropic non fornita per inizializzare il client.")

    def _configure_gemini(self):
        """Configura l'SDK Gemini."""
        if not self.google_api_key:
            raise ValueError("API Key Google non fornita per configurare Gemini.")
        try:
            genai.configure(api_key=self.google_api_key)
        except Exception as e:
            logging.exception("Errore durante la configurazione di google.generativeai")
            raise ConnectionError(f"Impossibile configurare l'SDK Gemini: {e}")


    def extract_frames(self):
        """
        Estrae 'num_frames' frame a intervalli equidistanti dal video.

        Returns:
            list: Lista di dizionari, ognuno contenente:
                  {'data': str (immagine base64), 'timestamp': float (in secondi)}
                  Ritorna lista vuota in caso di errore.
        """
        frame_list = []
        cap = None
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                logging.error(f"Impossibile aprire il video con OpenCV: {self.video_path}")
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            if total_frames <= 0 or fps <= 0:
                logging.error(f"Metadati video non validi (frame o fps): {self.video_path}")
                return []

            step = total_frames // self.num_frames
            if step == 0:
                step = 1

            logging.info(f"Estrazione di {self.num_frames} frame da un totale di {total_frames} con un passo di {step} frame.")

            for i in range(self.num_frames):
                frame_index = i * step
                if frame_index >= total_frames:
                    break

                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                success, frame = cap.read()

                if success:
                    timestamp = frame_index / fps
                    success_encode, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if success_encode:
                        frame_base64 = base64.b64encode(buffer).decode("utf-8")
                        frame_list.append({"data": frame_base64, "timestamp": timestamp})
                    else:
                        logging.warning(f"Errore durante la codifica del frame all'indice {frame_index}")
                else:
                    logging.warning(f"Impossibile leggere il frame all'indice {frame_index}")

            logging.info(f"Estratti con successo {len(frame_list)} frame.")

        except Exception as e:
            logging.exception(f"Errore durante l'estrazione dei frame da {self.video_path}")
            return []
        finally:
            if cap:
                cap.release()

        return frame_list

    def _analyze_batch_claude(self, batch, batch_idx, language, prompt_template, search_query=None):
        """Analizza un batch di frame usando Claude."""
        self._init_anthropic_client()
        if not self.anthropic_client: return [] # Errore già loggato

        messages = [{"role": "user", "content": []}]
        content_list = messages[0]["content"]

        for idx, frame in enumerate(batch):
            timestamp_seconds = frame['timestamp']
            minutes = int(timestamp_seconds // 60)
            seconds = int(timestamp_seconds % 60)
            timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
            content_list.append({"type": "text", "text": f"Frame {idx} at timestamp {timestamp_str}:"})
            content_list.append({
                "type": "image",
                "source": { "type": "base64", "media_type": "image/jpeg", "data": frame["data"] }
            })

        format_vars = {'language': language, 'batch_size': len(batch)}
        if search_query:
            format_vars['search_query'] = search_query
        formatted_prompt = prompt_template.format(**format_vars)
        content_list.append({"type": "text", "text": formatted_prompt})

        try:
            response = self.anthropic_client.messages.create(
                model=self.selected_model,
                max_tokens=4096, # Aumenta se necessario
                messages=messages
            )
            raw_text = response.content[0].text.strip()
            # Aggiungi robustezza al parsing JSON
            try:
                # Cerca di estrarre solo il blocco JSON se l'AI aggiunge testo extra
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\]|\{[\s\S]*\})', raw_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(2)
                    frames_json = json.loads(json_str)
                    logging.debug(f"Claude Batch {batch_idx} - JSON Parsed: {frames_json}")
                    return frames_json
                else:
                    logging.error(f"Claude Batch {batch_idx} - Nessun blocco JSON trovato nella risposta: {raw_text}")
                    return []
            except json.JSONDecodeError as jde:
                logging.error(f"Claude Batch {batch_idx} - Errore parsing JSON: {jde}\nRisposta grezza:\n{raw_text}")
                return []
        except Exception as e:
            logging.exception(f"Errore API Claude durante analisi batch {batch_idx}")
            return [] # Ritorna vuoto per questo batch in caso di errore API

    def _analyze_batch_gemini(self, batch, batch_idx, language, prompt_template, search_query=None):
        """Analizza un batch di frame usando Gemini."""
        self._configure_gemini() # Assicura che l'SDK sia configurato

        # Prepara il contenuto per Gemini (lista di testo e oggetti immagine)
        gemini_content = []
        for idx, frame in enumerate(batch):
             timestamp_seconds = frame['timestamp']
             minutes = int(timestamp_seconds // 60)
             seconds = int(timestamp_seconds % 60)
             timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
             gemini_content.append(f"Frame {idx} at timestamp {timestamp_str}:")
             # Gemini richiede oggetti Immagine dall'SDK
             try:
                 # Decodifica base64 in bytes
                 image_bytes = base64.b64decode(frame["data"])
                 img_part = {"mime_type": "image/jpeg", "data": image_bytes}
                 gemini_content.append(img_part)
             except Exception as decode_err:
                  logging.error(f"Gemini Batch {batch_idx} - Errore decodifica Base64 per frame {idx}: {decode_err}")
                  # Potresti saltare questo frame o l'intero batch
                  return [] # Errore nel batch

        # Aggiungi il prompt testuale alla fine
        format_vars = {'language': language, 'batch_size': len(batch)}
        if search_query:
            format_vars['search_query'] = search_query
        formatted_prompt = prompt_template.format(**format_vars)
        gemini_content.append(formatted_prompt)

        try:
            model = genai.GenerativeModel(self.selected_model)
            # Impostazioni generazione (opzionale, per controllare output)
            generation_config = genai.types.GenerationConfig(
                 # response_mime_type="application/json", # Chiedi JSON direttamente
                 temperature=0.5 # Riduci un po' la temperatura per risposte più consistenti
            )
            safety_settings = [ # Rilassa un po' i filtri se necessario, ma con cautela
                 {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]

            response = model.generate_content(
                 gemini_content,
                 generation_config=generation_config,
                 safety_settings=safety_settings
            )

            # Estrai e parsa il JSON dalla risposta
            try:
                # Gemini può restituire direttamente JSON se richiesto, o testo contenente JSON
                # Prova a parsare direttamente response.text
                raw_text = response.text
                # Cerca blocco JSON come per Claude per robustezza
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\]|\{[\s\S]*\})', raw_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(2)
                    frames_json = json.loads(json_str)
                    logging.debug(f"Gemini Batch {batch_idx} - JSON Parsed: {frames_json}")
                    return frames_json
                else:
                    logging.error(f"Gemini Batch {batch_idx} - Nessun blocco JSON trovato nella risposta: {raw_text}")
                    return []
            except json.JSONDecodeError as jde:
                logging.error(f"Gemini Batch {batch_idx} - Errore parsing JSON: {jde}\nRisposta grezza:\n{raw_text}")
                return []
            except ValueError: # Potrebbe essere bloccato da safety
                logging.warning(f"Gemini Batch {batch_idx} - Risposta bloccata o non valida. Feedback: {response.prompt_feedback}")
                return [] # Ritorna vuoto se bloccato
            except AttributeError: # Se response.text non esiste
                 logging.error(f"Gemini Batch {batch_idx} - Attributo 'text' non trovato nella risposta. Risposta completa: {response}")
                 return []

        except Exception as e:
            logging.exception(f"Errore API Gemini durante analisi batch {batch_idx}")
            return [] # Ritorna vuoto per questo batch

    # --- Metodo Principale di Analisi ---
    def analyze_frames_batch(self, frame_list, language):
        """
        Analizza una lista di frame (estratti da extract_frames) usando il modello AI selezionato.

        Args:
            frame_list (list): La lista di dizionari frame da analizzare.
            language (str): La lingua per le descrizioni richieste.

        Returns:
            list: Lista di dizionari con i dati dei frame analizzati:
                  {'frame_number': int, 'description': str, 'timestamp': str 'mm:ss'}
        """
        if not frame_list:
            logging.warning("Lista frame vuota passata ad analyze_frames_batch.")
            return []

        frame_data = [] # Risultato finale
        total_batches = (len(frame_list) + self.batch_size - 1) // self.batch_size # Calcolo corretto per l'ultimo batch
        model_name_lower = self.selected_model.lower()

        # Leggi il template del prompt una sola volta
        try:
            with open(PROMPT_FRAMES_ANALYSIS, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            logging.exception("Errore fatale: impossibile leggere il prompt di analisi frame.")
            raise RuntimeError(f"Errore lettura prompt analisi frame: {e}") # Solleva eccezione perché è critico

        logging.info(f"Inizio analisi di {len(frame_list)} frame in {total_batches} batch usando {self.selected_model}...")

        # Usa tqdm per la barra di progresso nel terminale/log
        for batch_idx in tqdm(range(total_batches), desc="Analisi Frame Batches", unit="batch"):
            batch_start_index = batch_idx * self.batch_size
            batch_end_index = min((batch_idx + 1) * self.batch_size, len(frame_list))
            current_batch = frame_list[batch_start_index:batch_end_index]

            if not current_batch: continue # Salta batch vuoti (non dovrebbe succedere)

            batch_results = []
            # Selezione API
            if "claude" in model_name_lower:
                batch_results = self._analyze_batch_claude(current_batch, batch_idx, language, prompt_template)
            elif "gemini" in model_name_lower:
                batch_results = self._analyze_batch_gemini(current_batch, batch_idx, language, prompt_template)
            # elif "ollama" in model_name_lower:
                # batch_results = self._analyze_batch_ollama_vision(...) # Implementare se necessario
            else:
                logging.error(f"Modello '{self.selected_model}' non supportato per l'analisi frame.")
                # Puoi decidere se fermarti o continuare con gli altri batch
                continue # Salta al prossimo batch

            # Elabora i risultati del batch corrente
            if batch_results:
                 try:
                      for item in batch_results:
                           # L'indice nel JSON è relativo al batch (0, 1, ...)
                           local_index = int(item.get("frame", -1))
                           description = item.get("description", "N/D").strip()

                           if 0 <= local_index < len(current_batch):
                                # Calcola l'indice globale del frame
                                global_frame_number = batch_start_index + local_index
                                timestamp_seconds = current_batch[local_index]['timestamp']
                                minutes = int(timestamp_seconds // 60)
                                seconds = int(timestamp_seconds % 60)

                                frame_data.append({
                                    "frame_number": global_frame_number,
                                    "description": description,
                                    "timestamp": f"{minutes:02d}:{seconds:02d}",
                                })
                           else:
                                logging.warning(f"Batch {batch_idx} - Indice frame non valido ricevuto nel JSON: {local_index}. Item: {item}")
                 except (TypeError, ValueError) as parse_err:
                       logging.error(f"Batch {batch_idx} - Errore durante l'elaborazione dei risultati JSON: {parse_err}. Risultati: {batch_results}")

            # Aggiungi una piccola pausa tra le chiamate API per evitare rate limiting (opzionale)
            # time.sleep(1)

        logging.info(f"Analisi frame completata. Dati estratti per {len(frame_data)} frame.")
        return frame_data

    def analyze_frames_for_objects(self, frame_list, language):
        """
        Analizza una lista di frame per il riconoscimento di oggetti, persone e scene.

        Args:
            frame_list (list): La lista di dizionari frame da analizzare.
            language (str): La lingua per le analisi richieste.

        Returns:
            list: Lista di dizionari con i dati dei frame analizzati:
                  {'frame_number': int, 'analysis': dict, 'timestamp': str 'mm:ss'}
        """
        if not frame_list:
            logging.warning("Lista frame vuota passata ad analyze_frames_for_objects.")
            return []

        frame_data = [] # Risultato finale
        total_batches = (len(frame_list) + self.batch_size - 1) // self.batch_size
        model_name_lower = self.selected_model.lower()

        try:
            with open(PROMPT_OBJECT_RECOGNITION, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            logging.exception("Errore fatale: impossibile leggere il prompt di object recognition.")
            raise RuntimeError(f"Errore lettura prompt object recognition: {e}")

        logging.info(f"Inizio analisi oggetti di {len(frame_list)} frame in {total_batches} batch usando {self.selected_model}...")

        for batch_idx in tqdm(range(total_batches), desc="Analisi Oggetti Batches", unit="batch"):
            batch_start_index = batch_idx * self.batch_size
            batch_end_index = min((batch_idx + 1) * self.batch_size, len(frame_list))
            current_batch = frame_list[batch_start_index:batch_end_index]

            if not current_batch: continue

            batch_results = []
            if "claude" in model_name_lower:
                batch_results = self._analyze_batch_claude(current_batch, batch_idx, language, prompt_template)
            elif "gemini" in model_name_lower:
                batch_results = self._analyze_batch_gemini(current_batch, batch_idx, language, prompt_template)
            else:
                logging.error(f"Modello '{self.selected_model}' non supportato per l'analisi oggetti.")
                continue

            if batch_results:
                try:
                    for item in batch_results:
                        local_index = int(item.get("frame", -1))
                        analysis = item.get("analysis", {})

                        if 0 <= local_index < len(current_batch):
                            global_frame_number = batch_start_index + local_index
                            timestamp_seconds = current_batch[local_index]['timestamp']
                            minutes = int(timestamp_seconds // 60)
                            seconds = int(timestamp_seconds % 60)

                            frame_data.append({
                                "frame_number": global_frame_number,
                                "analysis": analysis,
                                "timestamp": f"{minutes:02d}:{seconds:02d}",
                            })
                        else:
                            logging.warning(f"Batch {batch_idx} - Indice frame non valido ricevuto nel JSON: {local_index}. Item: {item}")
                except (TypeError, ValueError) as parse_err:
                    logging.error(f"Batch {batch_idx} - Errore durante l'elaborazione dei risultati JSON: {parse_err}. Risultati: {batch_results}")

        logging.info(f"Analisi oggetti completata. Dati estratti per {len(frame_data)} frame.")
        return frame_data

    def analyze_frames_for_specific_object(self, frame_list, language, search_query):
        """
        Analizza una lista di frame per cercare un oggetto specifico.

        Args:
            frame_list (list): La lista di dizionari frame da analizzare.
            language (str): La lingua per le analisi richieste.
            search_query (str): L'oggetto da cercare.

        Returns:
            list: Lista di dizionari con i dati dei frame analizzati:
                  {'timestamp': str 'mm:ss', 'description': str}
        """
        if not frame_list:
            logging.warning("Lista frame vuota passata ad analyze_frames_for_specific_object.")
            return []

        frame_data = [] # Risultato finale
        total_batches = (len(frame_list) + self.batch_size - 1) // self.batch_size
        model_name_lower = self.selected_model.lower()

        try:
            with open(PROMPT_SPECIFIC_OBJECT_RECOGNITION, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            logging.exception("Errore fatale: impossibile leggere il prompt di specific object recognition.")
            raise RuntimeError(f"Errore lettura prompt specific object recognition: {e}")

        logging.info(f"Inizio ricerca di '{search_query}' in {len(frame_list)} frame in {total_batches} batch usando {self.selected_model}...")

        for batch_idx in tqdm(range(total_batches), desc="Ricerca Oggetto Specifico", unit="batch"):
            batch_start_index = batch_idx * self.batch_size
            batch_end_index = min((batch_idx + 1) * self.batch_size, len(frame_list))
            current_batch = frame_list[batch_start_index:batch_end_index]

            if not current_batch: continue

            batch_results = []
            if "claude" in model_name_lower:
                batch_results = self._analyze_batch_claude(current_batch, batch_idx, language, prompt_template, search_query)
            elif "gemini" in model_name_lower:
                batch_results = self._analyze_batch_gemini(current_batch, batch_idx, language, prompt_template, search_query)
            else:
                logging.error(f"Modello '{self.selected_model}' non supportato per la ricerca di oggetti specifici.")
                continue

            if batch_results:
                try:
                    for item in batch_results:
                        timestamp_str = item.get("timestamp")
                        description = item.get("description", "N/D").strip()

                        if timestamp_str is not None:
                            frame_data.append({
                                "timestamp": timestamp_str,
                                "description": description,
                            })
                except (TypeError, ValueError) as parse_err:
                    logging.error(f"Batch {batch_idx} - Errore durante l'elaborazione dei risultati JSON: {parse_err}. Risultati: {batch_results}")

        logging.info(f"Ricerca di '{search_query}' completata. Trovate {len(frame_data)} occorrenze.")
        return frame_data

    def get_video_duration(self):
        """Restituisce la durata del video in secondi."""
        try:
             with VideoFileClip(self.video_path) as video:
                  return video.duration
        except Exception as e:
             logging.exception(f"Errore nel recuperare la durata del video: {self.video_path}")
             return 0.0 # Ritorna 0 in caso di errore

    # --- Generazione Riassunto Video (Testuale) ---
    def generate_video_summary(self, frame_data, language):
        """Genera un riassunto testuale del video basato sulle descrizioni dei frame."""
        if not frame_data:
             logging.warning("Nessun dato frame fornito per generare il riassunto.")
             return None

        video_duration_sec = self.get_video_duration()
        video_duration_minutes = video_duration_sec / 60

        # Prepara input per l'LLM (solo descrizioni)
        descriptions = [fd.get('description', '') for fd in frame_data]
        joined_descriptions = "\n".join(f"- {desc}" for desc in descriptions if desc) # Lista puntata

        if not joined_descriptions:
             logging.warning("Nessuna descrizione valida trovata nei dati dei frame per il riassunto.")
             return None

        # Leggi e formatta il prompt per il riassunto
        try:
            with open(PROMPT_VIDEO_SUMMARY, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            prompt_text = prompt_template.format(
                language=language,
                joined_descriptions=joined_descriptions,
                video_duration_minutes=f"{video_duration_minutes:.2f}" # Formatta durata
            )
        except Exception as e:
            logging.exception("Errore lettura/formattazione prompt riassunto video.")
            return None # Non procedere se il prompt fallisce

        # Selezione API (usa lo stesso modello dell'analisi frame o uno dedicato?)
        # Per ora riutilizziamo self.selected_model, assumendo sia testuale/multimodale
        model_name_lower = self.selected_model.lower()
        logging.info(f"Generazione riassunto video con {self.selected_model}...")

        try:
            if "claude" in model_name_lower:
                self._init_anthropic_client()
                if not self.anthropic_client: return None
                response = self.anthropic_client.messages.create(
                    model=self.selected_model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt_text}] # Prompt semplice
                )
                summary = response.content[0].text.strip()
                logging.info("Riassunto video generato con Claude.")
                return summary

            elif "gemini" in model_name_lower:
                self._configure_gemini()
                model = genai.GenerativeModel(self.selected_model)
                response = model.generate_content(prompt_text)
                try:
                     summary = response.text.strip()
                     logging.info("Riassunto video generato con Gemini.")
                     return summary
                except ValueError:
                     logging.warning(f"Risposta riassunto Gemini bloccata. Feedback: {response.prompt_feedback}")
                     return None

            # elif "ollama" in model_name_lower:
                # Implementare chiamata a Ollama per riassunto testuale
                # ...
                # return summary_text_from_ollama

            else:
                logging.error(f"Modello '{self.selected_model}' non supportato per il riassunto video.")
                return None

        except Exception as e:
            logging.exception(f"Errore API durante generazione riassunto video con {self.selected_model}")
            return None # Ritorna None in caso di errore API

    # --- Metodo Principale di Processamento ---
    def process_video(self, output_json="video_analysis.json", language="italiano"):
        """
        Esegue l'intero processo: estrazione frame, analisi, riassunto e salva in JSON.

        Args:
            output_json (str): Percorso del file JSON di output.
            language (str): Lingua per l'analisi e il riassunto.

        Returns:
            dict: Il dizionario contenente i risultati, o None in caso di errore grave.
        """
        results = {"frames": [], "video_summary": None}
        try:
            logging.info(f"--- Inizio Processamento Video: {self.video_path} ---")
            logging.info(f"Parametri: num_frames={self.num_frames}, language='{language}', model='{self.selected_model}'")

            # 1. Estrai Frames
            print(f"Estrazione di {self.num_frames} frame...") # Output per utente console
            frames = self.extract_frames()
            if not frames:
                print("Errore: Impossibile estrarre i frame.")
                logging.error("Processo interrotto: estrazione frame fallita.")
                return None
            print(f"Frame estratti: {len(frames)}.")
            logging.info("Estrazione frame completata.")

            # 2. Analizza Frames
            if self.analysis_mode == 'object_recognition':
                print(f"Analisi oggetti con {self.selected_model}...")
                frame_data = self.analyze_frames_for_objects(frames, language)
                results["frames"] = frame_data
                if not frame_data:
                    print("Attenzione: Analisi oggetti non ha prodotto risultati.")
                    logging.warning("Analisi oggetti non ha prodotto risultati.")
                else:
                    print(f"Analisi oggetti completata per {len(frame_data)} frame.")
                    logging.info("Analisi oggetti completata.")
                # Non generare un riassunto testuale per la modalità di riconoscimento oggetti
                results["video_summary"] = "Object recognition analysis complete."
            elif self.analysis_mode == 'specific_object_search':
                print(f"Ricerca di '{self.search_query}' con {self.selected_model}...")
                frame_data = self.analyze_frames_for_specific_object(frames, language, self.search_query)
                results["frames"] = frame_data
                if not frame_data:
                    print("Attenzione: Ricerca non ha prodotto risultati.")
                    logging.warning("Ricerca non ha prodotto risultati.")
                else:
                    print(f"Ricerca completata. Trovate {len(frame_data)} occorrenze.")
                    logging.info("Ricerca completata.")
                results["video_summary"] = f"Search for '{self.search_query}' complete."
            else: # Modalità 'description'
                print(f"Analisi dei frame con {self.selected_model}...")
                frame_data = self.analyze_frames_batch(frames, language)
                results["frames"] = frame_data
                if not frame_data:
                     print("Attenzione: Analisi frame non ha prodotto risultati.")
                     logging.warning("Analisi frame non ha prodotto risultati.")
                else:
                     print(f"Analisi completata per {len(frame_data)} frame.")
                     logging.info("Analisi frame completata.")

                # 3. Genera Riassunto Testuale
                if frame_data: # Genera riassunto solo se ci sono dati dai frame
                    print("Generazione del riassunto testuale del video...")
                    summary = self.generate_video_summary(frame_data, language)
                    results["video_summary"] = summary
                    if summary:
                        print("Riassunto generato.")
                        logging.info("Riassunto video generato.")
                    else:
                        print("Errore: Impossibile generare il riassunto.")
                        logging.error("Generazione riassunto video fallita.")
                else:
                     print("Salto generazione riassunto: nessun dato dai frame analizzati.")
                     logging.warning("Generazione riassunto saltata.")


            # 4. Salva Risultati in JSON
            try:
                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=4, ensure_ascii=False)
                print(f"Analisi del video salvata con successo in: {output_json}")
                logging.info(f"Risultati salvati in {output_json}")
            except Exception as e:
                print(f"Errore durante il salvataggio del file JSON: {e}")
                logging.exception("Errore salvataggio JSON.")
                # Non ritornare None qui, l'analisi è avvenuta

            logging.info(f"--- Fine Processamento Video: {self.video_path} ---")
            return results

        except Exception as e:
            print(f"\nERRORE GRAVE DURANTE IL PROCESSAMENTO: {e}")
            logging.exception("Errore grave in process_video.")
            return None


# --- Blocco Esecuzione Script Indipendente (main) ---
if __name__ == "__main__":
    print("Esecuzione di FrameExtractor come script.")
    # Verifica argomenti (migliorata)
    if len(sys.argv) < 3 or len(sys.argv) > 6: # Aggiunto api_key opzionale
        print("\nUso: python frameextractor.py <video_path> <num_frames> [language] [output_json] [api_key_google/anthropic]")
        print("  video_path: Percorso del file video.")
        print("  num_frames: Numero di frame da estrarre.")
        print("  language (opzionale): Lingua per l'analisi (default: italiano).")
        print("  output_json (opzionale): Nome del file JSON di output (default: video_analysis.json).")
        print("  api_key (opzionale): Puoi passare una chiave API specifica qui (altrimenti usa quelle da .env/config).")
        sys.exit(1)

    # Parsing Argomenti
    video_path = sys.argv[1]
    try:
        num_frames = int(sys.argv[2])
        if num_frames <= 0: raise ValueError()
    except ValueError:
        print("Errore: num_frames deve essere un numero intero positivo.")
        sys.exit(1)

    language = sys.argv[3] if len(sys.argv) > 3 else "italiano"
    output_json = sys.argv[4] if len(sys.argv) > 4 else "video_analysis.json"
    specific_api_key = sys.argv[5] if len(sys.argv) > 5 else None

    print(f"\nConfigurazione:")
    print(f"  Video: {video_path}")
    print(f"  Num Frame: {num_frames}")
    print(f"  Lingua: {language}")
    print(f"  Output JSON: {output_json}")
    if specific_api_key:
         print("  API Key fornita da argomenti (verrà usata se applicabile).")

    # Configura logging di base per l'esecuzione da script
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')

    # Crea dizionario API keys (passa solo quella fornita se data)
    api_keys_arg = {}
    if specific_api_key:
         # Determina se è Google o Anthropic (euristica semplice)
         if specific_api_key.startswith("AIza"): # Tipico prefisso Google
              api_keys_arg['google'] = specific_api_key
              print("  API Key rilevata come Google.")
         elif specific_api_key.startswith("sk-ant"): # Tipico prefisso Anthropic
              api_keys_arg['anthropic'] = specific_api_key
              print("  API Key rilevata come Anthropic.")
         else:
              print("  Attenzione: Tipo API Key non riconosciuto, verrà ignorata.")


    # Istanzia ed esegui
    try:
        # Passa le API key opzionali
        extractor = FrameExtractor(video_path, num_frames, api_keys=api_keys_arg)
        # Leggi il modello selezionato dalle impostazioni per informazione
        print(f"  Modello selezionato per 'frame_extractor' (da impostazioni): {extractor.selected_model}\n")

        results = extractor.process_video(output_json=output_json, language=language)

        if results:
            print("\nProcesso completato con successo.")
        else:
            print("\nProcesso terminato con errori.")
            sys.exit(1)

    except Exception as main_err:
        print(f"\nErrore irreversibile nello script: {main_err}")
        logging.exception("Errore nello script main.")
        sys.exit(1)