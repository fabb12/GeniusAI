import re
import os
import datetime

def generate_unique_filename(filepath):
    """
    Checks if a file exists at the given path. If it does, appends a timestamp
    to the filename to make it unique.
    """
    if not os.path.exists(filepath):
        return filepath

    directory, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{name}_{timestamp}{ext}"
    new_filepath = os.path.join(directory, new_filename)

    # In the rare case the timestamped file also exists, add a counter
    counter = 1
    while os.path.exists(new_filepath):
        new_filename = f"{name}_{timestamp}_{counter}{ext}"
        new_filepath = os.path.join(directory, new_filename)
        counter += 1

    return new_filepath

def remove_timestamps_from_html(html_content):
    """
    Removes timestamp tags and raw timestamps (e.g., [00:12:34.5] or [01:23]) from an HTML string,
    and cleans up surrounding whitespace.
    """
    if not html_content:
        return ""

    # Remove styled timestamps, replacing with a space to preserve word separation.
    font_timestamp_pattern = re.compile(r'\s*<font[^>]*color=["\']?#ADD8E6["\']?[^>]*>\[.*?\]</font>\s*', re.IGNORECASE)
    content = font_timestamp_pattern.sub(' ', html_content)

    # Remove raw timestamps, also replacing with a space.
    raw_timestamp_pattern = re.compile(r'\s*\[\d{1,2}:\d{2}(:\d{2})?(\.\d{1,2})?\]\s*')
    content = raw_timestamp_pattern.sub(' ', content)

    # Clean up whitespace issues that may result from the removal.
    # Collapse multiple spaces into a single space.
    content = re.sub(r'\s+', ' ', content)
    # Remove space that might be left after an opening <p> tag.
    content = re.sub(r'<p>\s+', '<p>', content)
    # Remove space that might be left before a closing </p> tag.
    content = re.sub(r'\s+</p>', '</p>', content)

    return content.strip()

import markdown
from markdownify import markdownify

def parse_timestamp_to_seconds(timestamp_str):
    """Converte un timestamp stringa [HH:MM:SS] o [MM:SS] in secondi totali."""
    if not isinstance(timestamp_str, str):
        return 0

    clean_ts = timestamp_str.replace('[', '').replace(']', '').strip()
    parts = clean_ts.split(':')

    try:
        if len(parts) == 3:
            h, m, s = map(float, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(float, parts)
            return m * 60 + s
        else:
            return 0
    except (ValueError, TypeError):
        return 0

def convert_html_to_markdown(html_text):
    """Converte un testo da HTML a Markdown."""
    return markdownify(html_text, heading_style="ATX")

def convert_markdown_to_html(markdown_text):
    """Converte un testo da Markdown a HTML."""
    return markdown.markdown(markdown_text, extensions=['fenced_code', 'tables'])

import requests
import logging

def _call_ollama_api(endpoint, model_name, system_prompt, user_prompt, images=None, timeout=300):
    """
    Funzione helper centralizzata per chiamare l'API di Ollama, con gestione per modelli di testo e vision.
    """
    # Se vengono fornite immagini, usa sempre e solo /api/generate
    if images:
        logging.info(f"Modalità Vision: tentativo Ollama con /api/generate per il modello '{model_name}'...")
        api_url = f"{endpoint}/api/generate"
        payload = {
            "model": model_name,
            "prompt": user_prompt,
            "system": system_prompt,
            "images": images,
            "stream": False
        }
        try:
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()
            result_text = response_data.get("response", "").strip()
            if result_text:
                logging.info("Successo con /api/generate in modalità Vision.")
                return result_text
            raise Exception("Risposta vuota o formato non valido da /api/generate in modalità Vision.")
        except Exception as e:
            logging.error(f"Errore in modalità Vision con /api/generate: {e}")
            raise e

    # Logica esistente per i modelli di solo testo
    # Tentativo 1: /api/chat (moderno)
    try:
        logging.info(f"Modalità Testo: tentativo Ollama con /api/chat per il modello '{model_name}'...")
        api_url = f"{endpoint}/api/chat"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {"model": model_name, "messages": messages, "stream": False}

        response = requests.post(api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        response_data = response.json()

        if "message" in response_data and "content" in response_data["message"]:
            result_text = response_data["message"]["content"].strip()
            if result_text:
                logging.info("Successo con /api/chat.")
                return result_text
        raise Exception("Risposta vuota o formato non valido da /api/chat.")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logging.warning("Endpoint /api/chat non trovato (404). Tento il fallback a /api/generate...")
        else:
            raise e
    except Exception as e:
        logging.error(f"Errore durante la chiamata a /api/chat: {e}")
        raise e

    # Tentativo 2: /api/generate (fallback per testo)
    try:
        logging.info(f"Modalità Testo: tentativo Ollama con /api/generate per il modello '{model_name}'...")
        api_url = f"{endpoint}/api/generate"
        payload = {
            "model": model_name,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False
        }
        response = requests.post(api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        response_data = response.json()
        result_text = response_data.get("response", "").strip()
        if result_text:
            logging.info("Successo con /api/generate.")
            return result_text
        raise Exception("Risposta vuota o formato non valido da /api/generate.")
    except Exception as e:
        logging.error(f"Anche il fallback a /api/generate è fallito: {e}")
        raise e