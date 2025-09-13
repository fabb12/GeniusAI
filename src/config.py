
# File: config.py

import os
import sys
import logging
from PyQt6.QtCore import QSettings
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# --- Funzioni Utilità Percorso ---
def get_app_path():
    """Determina il percorso base dell'applicazione, sia in modalità di sviluppo che compilata"""
    if getattr(sys, 'frozen', False):
        # Se l'app è compilata con PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # In modalità di sviluppo
        # Assumendo che config.py sia in src/
        return os.path.dirname(os.path.abspath(__file__))

def get_application_path():
    """Alias per get_app_path, può essere utile mantenere per compatibilità"""
    return get_app_path()

# --- Impostazione Variabile Ambiente Playwright (solo per bundle) ---
if getattr(sys, 'frozen', False):
    application_path = get_application_path()
    bundled_browser_path = os.path.join(application_path, 'ms-playwright')
    # Log per debug durante l'esecuzione del bundle
    print(f"[Config Init] App bundled. Setting PLAYWRIGHT_BROWSERS_PATH to: {bundled_browser_path}")
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = bundled_browser_path
    # Verifica opzionale (per debug)
    # if not os.path.exists(bundled_browser_path):
    #     print(f"[Config Init] WARNING: Bundled browser path does not exist: {bundled_browser_path}")
    # else:
    #     print(f"[Config Init] Bundled browser path verified.")

# --- Directory Base ---
BASE_DIR = get_app_path()

# --- API Keys ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")    # Se usi OpenAI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")    # Per Gemini Cloud

# --- Funzione Centralizzata per Recupero API Key ---
def get_api_key(service_name: str) -> str:
    """
    Recupera una API key dando priorità a QSettings e fallback a .env.

    Args:
        service_name (str): Il nome del servizio (es. 'google', 'anthropic', 'elevenlabs').

    Returns:
        str: La API key trovata.
    """
    settings = QSettings("ThemaConsulting", "GeniusAI")

    # 1. Prova a leggere da QSettings
    settings_key = f"api_keys_dialog/{service_name.lower()}"
    stored_key = settings.value(settings_key, "")

    if stored_key:
        logging.debug(f"API key for '{service_name}' found in QSettings.")
        return stored_key

    # 2. Se non trovata in QSettings, usa il fallback da .env (caricato in config)
    logging.debug(f"API key for '{service_name}' not found in QSettings, falling back to environment variable.")
    fallback_keys = {
        "google": GOOGLE_API_KEY,
        "anthropic": ANTHROPIC_API_KEY,
        "elevenlabs": ELEVENLABS_API_KEY,
        "openai": OPENAI_API_KEY
    }

    return fallback_keys.get(service_name.lower(), "")

# --- Definizione Identificatori Modello ---
# Claude (Anthropic)
MODEL_3_7_SONNET = "claude-3-5-sonnet-20240620" # Nota: Rinominato per chiarezza, 3.7 non esiste al momento
MODEL_3_5_SONNET = "claude-3-5-sonnet-20240620" # Il più recente 3.5
MODEL_3_OPUS = "claude-3-opus-20240229"
MODEL_3_SONNET = "claude-3-sonnet-20240229"
MODEL_3_HAIKU = "claude-3-haiku-20240307"

# Gemini (Google Cloud)
GEMINI_15_PRO = "gemini-1.5-pro-latest"
GEMINI_15_FLASH = "gemini-1.5-flash-latest"
#GEMINI_25_PRO_EXP = "gemini-2.5-pro-exp-03-25" # Mantenuto come esempio sperimentale
GEMINI_25_PRO = "gemini-2.5-pro"
GEMINI_20_FLASH = "gemini-2.0-flash"
GEMINI_25_FLASH = "gemini-2.5-flash"
GEMINI_20_FLASH_LITE = "gemini-2.0-flash-lite"
GEMINI_15_FLASH_8B = "gemini-1.5-flash-8b" # Nome API specifico

# OpenAI (Esempi se li integri)
# GPT_4_TURBO = "gpt-4-turbo"
# GPT_4O = "gpt-4o"
# GPT_4O_MINI = "gpt-4o-mini"

# Modelli Locali (via Ollama)
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434") # Default Ollama endpoint
OLLAMA_GEMMA_2B = "ollama:gemma:2b"
OLLAMA_GEMMA_7B = "ollama:gemma:7b"
OLLAMA_GEMMA2_9B = "ollama:gemma2:9b"
OLLAMA_LLAMA3_8B = "ollama:llama3:8b"
OLLAMA_MISTRAL_7B = "ollama:mistral:7b" # Esempio Mistral

# --- Liste Categoria Modelli ---
# (Queste liste aiutano a definire quali modelli mostrare per ogni azione)

# Modelli con capacità Vision (per Frame Extractor, Browser Agent con visione)
MODELS_WITH_VISION = [
    MODEL_3_5_SONNET, MODEL_3_OPUS, MODEL_3_SONNET, MODEL_3_HAIKU, # Claude 3/3.5
    GEMINI_15_PRO, GEMINI_15_FLASH, GEMINI_25_PRO, GEMINI_20_FLASH,GEMINI_25_FLASH, GEMINI_20_FLASH_LITE, # Gemini Cloud
    # GPT_4O, GPT_4_TURBO, # Se usi OpenAI Vision
    # Aggiungere modelli Ollama con capacità vision (es. llava) se configurati e testati
    # "ollama:llava:7b",
]

# Modelli testuali veloci (per Browser Agent, Riassunti rapidi, Text Processing base)
FAST_TEXT_MODELS = [
    MODEL_3_HAIKU,
    GEMINI_15_FLASH, GEMINI_20_FLASH, GEMINI_25_FLASH, GEMINI_20_FLASH_LITE, GEMINI_15_FLASH_8B,
    OLLAMA_GEMMA_2B, OLLAMA_GEMMA_7B, OLLAMA_LLAMA3_8B, OLLAMA_MISTRAL_7B, OLLAMA_GEMMA2_9B,
    # GPT_4O_MINI, # Se usi OpenAI
]

# Modelli testuali potenti (per PPTX Generation, Text Processing complesso, Riassunti dettagliati)
POWERFUL_TEXT_MODELS = [
    MODEL_3_5_SONNET, MODEL_3_OPUS, MODEL_3_SONNET,
    GEMINI_15_PRO, GEMINI_25_PRO,
    # GPT_4O, GPT_4_TURBO, # Se usi OpenAI
    # Modelli Ollama più grandi (es. llama3:70b) se l'utente li ha
]

# Tutti i modelli Text/Multimodal conosciuti (per fallback o liste complete)
ALL_KNOWN_MODELS = list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS + MODELS_WITH_VISION)) # Usa set per rimuovere duplicati

# --- Configurazione Modelli per Azione Specifica ---
ACTION_MODELS_CONFIG = {
    # Identificatore unico per l'azione
    'frame_extractor': {
        'display_name': "Estrazione Frame (Visione)", # Etichetta UI
        'setting_key': "models/frame_extractor",    # Chiave QSettings
        'default': os.getenv("DEFAULT_MODEL_FRAME_EXTRACTOR", GEMINI_15_FLASH), # Modello di fallback
        'allowed': MODELS_WITH_VISION # Lista di modelli permessi
    },
    'text_processing': {
        'display_name': "Elaborazione Testo (Summary/Fix)",
        'setting_key': "models/text_processing",
        'default': os.getenv("DEFAULT_MODEL_TEXT_PROCESSING", GEMINI_15_FLASH),
        'allowed': list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS)) # Permette tutti i modelli testuali
    },
    'pptx_generation': {
        'display_name': "Generazione Presentazioni",
        'setting_key': "models/pptx_generation",
        'default': os.getenv("DEFAULT_MODEL_PPTX_GENERATION", MODEL_3_5_SONNET),
        'allowed': POWERFUL_TEXT_MODELS # Preferibilmente modelli potenti
    },
    'browser_agent': {
        'display_name': "Browser Agent",
        'setting_key': "models/browser_agent",
        'default': os.getenv("DEFAULT_MODEL_BROWSER_AGENT", GEMINI_15_FLASH),
        # Permette modelli veloci o modelli potenti che abbiano anche capacità di visione
        'allowed': list(set(FAST_TEXT_MODELS + [m for m in POWERFUL_TEXT_MODELS if m in MODELS_WITH_VISION]))
    },
    'summary': { # Usato da MeetingSummarizer
        'display_name': "Riassunto Meeting",
        'setting_key': "models/summary",
        'default': os.getenv("DEFAULT_MODEL_SUMMARY", GEMINI_15_FLASH),
        'allowed': list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS)) # Tutti i modelli testuali vanno bene
    },
    # Esempio: Se avessi una generazione specifica per la guida operativa
    # 'operational_guide': {
    #     'display_name': "Guida Operativa (da Visione)",
    #     'setting_key': "models/operational_guide",
    #     'default': os.getenv("DEFAULT_MODEL_OPERATIONAL_GUIDE", GEMINI_15_PRO),
    #     'allowed': [m for m in POWERFUL_TEXT_MODELS if m in MODELS_WITH_VISION] # Modelli potenti con visione
    # }
}

# --- Percorsi File e Prompt ---
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffmpeg.exe")
FFMPEG_PATH_DOWNLOAD = os.path.join(BASE_DIR, "ffmpeg", "bin") # Usato da yt-dlp
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")
CONTACTS_FILE = os.path.join(BASE_DIR, "contatti_teams.txt")
DOCK_SETTINGS_FILE = os.path.join(BASE_DIR, "dock_settings.json")
LOG_FILE = os.path.join(BASE_DIR, "console_log.txt")

# --- Livello di Log ---
LOG_LEVEL = logging.INFO

# --- Directory e Percorsi Prompt ---
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

def get_prompt_path(filename):
    """Funzione helper per ottenere il percorso di un prompt e verificare se esiste."""
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        logging.warning(f"File prompt non trovato: {path}")
    return path

PROMPT_FRAMES_ANALYSIS = get_prompt_path("frames_analysis_prompt.txt")
PROMPT_VIDEO_SUMMARY = get_prompt_path("video_summary_prompt.txt")
PROMPT_COMBINED_ANALYSIS = get_prompt_path("combined_analysis_prompt.txt")
PROMPT_PPTX_GENERATION = get_prompt_path("pptx_generation_prompt.txt")
PROMPT_TEXT_SUMMARY = get_prompt_path("text_summary_prompt.txt")
PROMPT_TEXT_FIX = get_prompt_path("text_fix_prompt.txt")
PROMPT_BROWSER_GUIDE = get_prompt_path("browser_guide_prompt.txt")
PROMPT_YOUTUBE_SUMMARY = get_prompt_path("youtube_summary.txt")
# PROMPT_BROWSER_AGENT = get_prompt_path("browser_agent_prompt.txt") # Se esiste
PROMPT_MEETING_SUMMARY = get_prompt_path("meeting_summary_prompt.txt")
PROMPT_TTS = get_prompt_path("tts_prompt.txt") # Se esiste

# --- Percorsi Risorse ---
RESOURCES_DIR = os.path.join(BASE_DIR, "res")

def get_splash_images_dir():
    """Ottiene il percorso della cartella splash_images in modo compatibile."""
    return os.path.join(RESOURCES_DIR, "splash_images")

SPLASH_IMAGES_DIR = get_splash_images_dir()
MUSIC_DIR = os.path.join(RESOURCES_DIR, "music")
WATERMARK_IMAGE = os.path.join(RESOURCES_DIR, "watermark.png")

# --- Impostazioni Default Generali ---
DEFAULT_FRAME_COUNT = 5
DEFAULT_STABILITY = 50
DEFAULT_SIMILARITY = 80
DEFAULT_STYLE = 0
DEFAULT_FRAME_RATE = 25
DEFAULT_AUDIO_CHANNELS = 2

# --- Impostazioni UI ---
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# --- Impostazioni Voci (ElevenLabs) ---
DEFAULT_VOICES = {
    "Alessio": "BTpQARcEj1XqVxdZjTI7",
    "Marco": "GcAgjAjkhWsmUd4GlPiv",
    "Matilda": "atq1BFi5ZHt88WgSOJRB",
    "Mika": "B2j2knC2POvVW0XJE6Hi"
    # Aggiungere altre voci predefinite se necessario
}

# --- Funzione di Diagnostica ---
def debug_config():
    """Stampa la configurazione corrente per diagnosi."""
    print("--- [Config Debug] Percorsi Principali ---")
    paths = {
        "BASE_DIR": BASE_DIR,
        "FFMPEG_PATH": FFMPEG_PATH,
        "PROMPTS_DIR": PROMPTS_DIR,
        "RESOURCES_DIR": RESOURCES_DIR,
        "SPLASH_IMAGES_DIR": SPLASH_IMAGES_DIR,
        "MUSIC_DIR": MUSIC_DIR,
        "WATERMARK_IMAGE": WATERMARK_IMAGE,
        "VERSION_FILE": VERSION_FILE,
        "LOG_FILE": LOG_FILE,
        "OLLAMA_ENDPOINT": OLLAMA_ENDPOINT,
        # API Keys Status
        "ELEVENLABS_API_KEY": "Impostata" if ELEVENLABS_API_KEY else "NON Impostata",
        "ANTHROPIC_API_KEY": "Impostata" if ANTHROPIC_API_KEY else "NON Impostata",
        "GOOGLE_API_KEY": "Impostata" if GOOGLE_API_KEY else "NON Impostata",
        "OPENAI_API_KEY": "Impostata" if OPENAI_API_KEY else "NON Impostata",
    }
    for name, value in paths.items():
        # Verifica esistenza per i percorsi file/dir
        exists_str = ""
        if name not in ["OLLAMA_ENDPOINT"] and "API_KEY" not in name:
             if isinstance(value, str) and os.path.exists(value):
                 exists_str = "- ESISTE"
             elif isinstance(value, str):
                 exists_str = "- MANCANTE!"
        print(f"{name}: {value} {exists_str}")

    print("\n--- [Config Debug] Configurazione Modelli per Azione ---")
    for action, config in ACTION_MODELS_CONFIG.items():
        print(f"Azione: '{action}' (UI: '{config.get('display_name', 'N/D')}')")
        print(f"  Setting Key: '{config['setting_key']}'")
        print(f"  Default: '{config['default']}'")
        print(f"  Modelli Permessi ({len(config['allowed'])}): {config['allowed']}")
        print("-" * 20)

    print("\n--- [Config Debug] Tutti i Modelli Noti ---")
    print(ALL_KNOWN_MODELS)

    return paths, ACTION_MODELS_CONFIG

# Esempio di come chiamare la funzione di debug alla fine del file,
# utile durante lo sviluppo per verificare che tutto sia corretto.
if __name__ == "__main__":
    print("Esecuzione debug_config() da config.py...")
    debug_config()

