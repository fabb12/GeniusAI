import os
import sys
import logging
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()


def get_app_path():
    """Determina il percorso base dell'applicazione, sia in modalità di sviluppo che compilata"""
    if getattr(sys, 'frozen', False):
        # Se l'app è compilata con PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # In modalità di sviluppo
        return os.path.dirname(os.path.abspath(__file__))


# Directory base dell'applicazione
BASE_DIR = get_app_path()

# API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# AI Models - Claude (solo modelli base)
MODEL_3_7_SONNET = os.getenv("MODEL_3_7_SONNET", "claude-3-7-sonnet-20250219")
MODEL_3_5_HAIKU = os.getenv("MODEL_3_5_HAIKU", "claude-3-5-haiku-20241022")
MODEL_3_5_SONNET_V2 = os.getenv("MODEL_3_5_SONNET_V2", "claude-3-5-sonnet-20241022")
MODEL_3_5_SONNET = os.getenv("MODEL_3_5_SONNET", "claude-3-5-sonnet-20240620")
MODEL_3_OPUS = os.getenv("MODEL_3_OPUS", "claude-3-opus-20240229")
MODEL_3_SONNET = os.getenv("MODEL_3_SONNET", "claude-3-sonnet-20240229")
MODEL_3_HAIKU = os.getenv("MODEL_3_HAIKU", "claude-3-haiku-20240307")

# Modelli per componenti specifici
CLAUDE_MODEL_FRAME_EXTRACTOR = os.getenv("CLAUDE_MODEL_FRAME_EXTRACTOR", MODEL_3_5_SONNET)
CLAUDE_MODEL_TEXT_PROCESSING = os.getenv("CLAUDE_MODEL_TEXT_PROCESSING", MODEL_3_5_SONNET)
CLAUDE_MODEL_PPTX_GENERATION = os.getenv("CLAUDE_MODEL_PPTX_GENERATION", MODEL_3_5_SONNET)
CLAUDE_MODEL_BROWSER_AGENT = os.getenv("CLAUDE_MODEL_BROWSER_AGENT", MODEL_3_HAIKU)
CLAUDE_MODEL_SUMMARY = os.getenv("CLAUDE_MODEL_SUMMARY", MODEL_3_5_SONNET)

# File Paths - Usa percorsi assoluti costruiti da BASE_DIR
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffmpeg.exe")
FFMPEG_PATH_DOWNLOAD = os.path.join(BASE_DIR, "ffmpeg", "bin")
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")
CONTACTS_FILE = os.path.join(BASE_DIR, "contatti_teams.txt")
DOCK_SETTINGS_FILE = os.path.join(BASE_DIR, "dock_settings.json")
LOG_FILE = os.path.join(BASE_DIR, "console_log.txt")

# LOG_LEVEL: Imposta il livello di log per l'intera applicazione.
LOG_LEVEL = logging.INFO

# Directory dei prompt - Usa percorsi assoluti costruiti da BASE_DIR
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

# Prompt per l'estrazione dei frame
PROMPT_FRAMES_ANALYSIS = os.path.join(PROMPTS_DIR, "frames_analysis_prompt.txt")
PROMPT_VIDEO_SUMMARY = os.path.join(PROMPTS_DIR, "video_summary_prompt.txt")

# Prompt per la generazione di presentazioni PowerPoint
PROMPT_PPTX_GENERATION = os.path.join(PROMPTS_DIR, "pptx_generation_prompt.txt")

# Prompt per l'elaborazione del testo
PROMPT_TEXT_SUMMARY = os.path.join(PROMPTS_DIR, "text_summary_prompt.txt")
PROMPT_TEXT_FIX = os.path.join(PROMPTS_DIR, "text_fix_prompt.txt")

# Prompt per l'agente browser
PROMPT_BROWSER_GUIDE = os.path.join(PROMPTS_DIR, "browser_guide_prompt.txt")
PROMPT_BROWSER_AGENT = os.path.join(PROMPTS_DIR, "browser_agent_prompt.txt")

# Prompt per il riassunto delle riunioni
PROMPT_MEETING_SUMMARY = os.path.join(PROMPTS_DIR, "meeting_summary_prompt.txt")

# Prompt per la generazione di audio
PROMPT_TTS = os.path.join(PROMPTS_DIR, "tts_prompt.txt")

# Resource Paths
RESOURCES_DIR = os.path.join(BASE_DIR, "res")


def get_splash_images_dir():
    """Ottiene il percorso della cartella splash_images in modo compatibile con PyInstaller"""
    return os.path.join(RESOURCES_DIR, "splash_images")


SPLASH_IMAGES_DIR = get_splash_images_dir()
MUSIC_DIR = os.path.join(RESOURCES_DIR, "music")
WATERMARK_IMAGE = os.path.join(RESOURCES_DIR, "watermark.png")

# Default Settings
DEFAULT_FRAME_COUNT = 5
DEFAULT_STABILITY = 50
DEFAULT_SIMILARITY = 80
DEFAULT_STYLE = 0
DEFAULT_FRAME_RATE = 25
DEFAULT_AUDIO_CHANNELS = 2

# UI Settings
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# Voice Settings
DEFAULT_VOICES = {
    "Alessio": "BTpQARcEj1XqVxdZjTI7",
    "Marco": "GcAgjAjkhWsmUd4GlPiv",
    "Matilda": "atq1BFi5ZHt88WgSOJRB",
    "Mika": "B2j2knC2POvVW0XJE6Hi"
}


# Funzione di diagnostica per debug di percorsi (utile per verificare percorsi nell'eseguibile)
def debug_paths():
    """Stampa i percorsi principali per diagnosi"""
    paths = {
        "BASE_DIR": BASE_DIR,
        "FFMPEG_PATH": FFMPEG_PATH,
        "PROMPTS_DIR": PROMPTS_DIR,
        "RESOURCES_DIR": RESOURCES_DIR,
        "SPLASH_IMAGES_DIR": SPLASH_IMAGES_DIR,
        "VERSION_FILE": VERSION_FILE
    }

    for name, path in paths.items():
        exists = os.path.exists(path)
        print(f"{name}: {path} - {'ESISTE' if exists else 'MANCANTE'}")

    return paths