# GeniusAI

Questo programma offre un’interfaccia avanzata per la gestione di **video** e **audio**, facilitando la creazione di video tutorial con funzionalità di **AI Generative**.

## **Indice dei Contenuti**
- [Funzionalità Principali](#-funzionalità-principali)
- [Video Demo](#video-demo)
- [Processo Principale](#processo-principale)
- [Struttura del Progetto](#struttura-del-progetto)
- [Installazione](#installazione)
- [Avvio](#avvio)
- [Come Usare](#come-usare)
- [Integrazioni AI e TTS](#integrazioni-ai-e-tts)
- [Registrazione Schermo e Gestione Audio/Video](#registrazione-schermo-e-gestione-audiovideo)
- [Creazione Presentazioni AI](#creazione-presentazioni-ai)
- [BarkTest e Generazione Audio](#barktest-e-generazione-audio)
- [API Key](#api-key)
- [Generazione del file requirements.txt](#generazione-del-file-requirementstxt)
- [Installazione delle Dipendenze con install_requirements.py](#installazione-delle-dipendenze-con-install_requirementspy)
- [Generazione dell'Eseguibile (.exe) con PyInstaller](#generazione-delleseguibile-exe-con-pyinstaller)
- [Creazione dell’Installer Windows con Inno Setup (.iss)](#creazione-dellinstaller-windows-con-inno-setup-iss)
 
---

## 🚀 **Funzionalità Principali**

- **Caricamento Video/Audio**: Supporta vari formati (mp4, avi, mov, mp3, wav, ecc.).
- **Taglio e Rimozione di Sezioni**: Possibilità di tagliare e rimuovere parti di video/audio con segnalibri.
- **Docking Flessibile**: Layout personalizzabile grazie a PyQt6 con interfaccia in stile docking.
- **Trascrizione Automatica e Riassunti AI**: Trascrizione con `speech_recognition` e correzione/riassunti con servizi AI.
- **TTS Avanzato**: Generazione di traccie audio con ElevenLabs, Bark, e altre librerie (impostazione API Key).
- **Registrazione Schermo**: Registrazione del desktop e, opzionalmente, di un input audio.
- **Unione Video**: Funzionalità di merge di più clip.
- **Audio Dock**: Caricamento nuove tracce, sostituzione audio, freeze frame, inserimento di pause, ecc.
- **Gestione Presentazioni PowerPoint**: Creazione di slide da testo trascritto o da file .txt con AI (Anthropic).
- **Download da YouTube**: Scarica video o sola traccia audio direttamente da URL con `yt-dlp`.

---

## [Video Demo](https://www.youtube.com/watch?v=ajhi_4QfYA8)

[![Guarda il video Demo](https://img.youtube.com/vi/ajhi_4QfYA8/0.jpg)](https://www.youtube.com/watch?v=ajhi_4QfYA8)

---

### 📚 **Processo Principale:**

1. **Registrazione del Video**: L’utente registra un video tutorial (o carica un video esistente).
2. **Trascrizione Automatica**: Il testo viene trascritto automaticamente e un’AI ottimizza/corregge il testo.
3. **Modifica e Ottimizzazione del Testo**: Possibilità di migliorare manualmente, di ottenere riassunti e di applicare correzioni AI.
4. **Generazione Traccia Audio con TTS**: Creazione di tracce audio professionali con tecnologia TTS (ElevenLabs, Bark, ecc.).
5. [da completare] **Lip Sync**: Sincronizzazione labiale con Wav2Lip.
6. **Condivisione Video**: Condivisione rapida del video generato, ad esempio tramite Microsoft Teams.

Il testo trascritto può essere modificato per ottimizzare ulteriormente la qualità finale dell’audio e del video tutorial.

---

## **Architettura a Livelli**

Il software segue un’architettura a livelli che semplifica l’organizzazione e la manutenzione del codice:

1. **UI Layer (Presentazione)**  
   - **PyQt6** fornisce le interfacce grafiche: Dock personalizzati, pulsanti, menù, slider, ecc.  
   - Esempi: *CustomSlider, CustumTextEdit, CropVideoWidget* e i Docks di gestione (editing, recording, audio dock).  

2. **Application/Business Logic Layer**  
   - Contiene le regole di business e l’orchestrazione delle operazioni.  
   - **`TGeniusAI.py`** fa da fulcro: riceve input dalla UI e coordina i servizi (taglio video, trascrizione, generazione TTS, ecc.).  
   - Gestisce la logica di layout con i *DockManagers*, l’avvio di thread per i processi intensivi (trascrizione, download), e raggruppa i metodi di editing.  

3. **Services/Infrastructure Layer**  
   - Racchiude l’interazione con servizi esterni (API AI, TTS ElevenLabs, Wav2Lip, ffmpeg, ecc.).  
   - Esempi:  
     - *AudioTranscript* (trascrizione con `speech_recognition`),  
     - *ProcessTextAI* (chiamate ad Anthropic),  
     - *DownloadVideo* (integrazione con `yt-dlp`),  
     - *AudioGenerationREST* (invio di richieste a ElevenLabs).  
   - Qui si trova la logica di basso livello: conversioni audio/video con `ffmpeg`, librerie di generazione speech, ecc.

## 📂 **Struttura del Progetto**

La struttura dei file è stata organizzata in diverse cartelle per semplificare l’architettura del codice:

```plaintext
GeniusAI/
├─ generate_requirements.py         # Generazione file requirements.txt
├─ install_requirements.py          # Installazione sicura delle dipendenze
├─ TGeniusAI.spec                   # Configurazione PyInstaller per creare un eseguibile
├─ TGeniusAI.iss                    # Script Inno Setup per creare un installer Windows
├─ README.md                        # Documentazione principale
├─ requirements.txt                 # Elenco delle dipendenze
├─ version_info.txt                 # Informazioni su versione e data di build
├─ res/                             # Risorse statiche (icone, immagini, config)
├─ ffmpeg/                          # Cartella per ffmpeg (da scaricare separatamente)
│  ├─ bin/
│     ├─ ffmpeg.exe                 # Eseguibile ffmpeg per elaborazione audio/video
├─ src/                             # Codice sorgente principale
│  ├─ BarkTest.py                   # Esempio di generazione audio test con libreria Bark
│  ├─ TGeniusAI.py                  # Entry Point principale: Avvio GUI e gestione app
│  ├─ managers/                     # Gestione impostazioni, layout dock, monitor Teams
│  │  ├─ MonitorTeams.py
│  │  ├─ Settings.py
│  │  ├─ SettingsDialog.py
│  │  ├─ SettingsManager.py
│  │  ├─ StreamToLogger.py
│  │  ├─ __init__.py
│  ├─ recorder/                     # Gestione registrazione schermo
│  │  ├─ ScreenRecorder.py
│  │  ├─ __init__.py
│  ├─ services/                     # Servizi di AI, TTS, Download, LipSync, Summarizer, ecc.
│  │  ├─ AudioGeneration.py
│  │  ├─ AudioGenerationREST.py
│  │  ├─ AudioTranscript.py
│  │  ├─ DownloadVideo.py
│  │  ├─ LipSync.py
│  │  ├─ PptxGeneration.py
│  │  ├─ ProcessTextAI.py
│  │  ├─ ShareVideo.py
│  │  ├─ Summarizer.py
│  │  ├─ VideoCutting.py
│  │  ├─ __init__.py
│  ├─ ui/                           # Componenti UI personalizzati (dock, slider, splash, ecc.)
│  │  ├─ CropOverlay.py
│  │  ├─ CustomSlider.py
│  │  ├─ CustumTextEdit.py
│  │  ├─ CustVideoWidget.py
│  │  ├─ ScreenButton.py
│  │  ├─ SplashScreen.py
│  │  ├─ __init__.py
├─ logs/                            # File di log
│  ├─ app.log
```

### **File di rilievo**  
- **TGeniusAI.py**: Avvia l’**interfaccia PyQt6** principale, gestisce i Dock e racchiude gran parte della logica di editing (taglio, merge, TTS, AI, ecc.).  
- **MonitorTeams.py**: Esempio di *registrazione automatica* di chiamate Teams.  
- **LipSync.py**: Implementa la sincronizzazione labiale con [Wav2Lip](https://github.com/Rudrabha/Wav2Lip).  
- **PptxGeneration.py**: Genera automaticamente presentazioni PowerPoint basandosi sul testo trascritto e su input AI (Anthropic).  
- **ProcessTextAI.py**: Riassume o “sistema” il testo tramite API *Anthropic*.  
- **AudioGenerationThread (AudioGenerationREST.py)**: Integra *ElevenLabs* via REST per la generazione vocale.

---

## **Installazione**

1. **Clona il repository**:
   ```bash
   git clone https://github.com/fabb12/GeniusAi.git
   cd GeniusAi
   ```

2. **Crea un ambiente virtuale** (opzionale ma consigliato):
   ```bash
   python -m venv venv
   # Mac/Linux:
   source venv/bin/activate
   # Windows:
   .\venv\Scripts\activate
   ```

3. **ffmpeg**: Scarica manualmente da [https://www.ffmpeg.org/download.html](https://www.ffmpeg.org/download.html) e inserisci `ffmpeg.exe` all’interno di `./ffmpeg/bin/`.  

---

## ▶️ **Avvio**

1. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
2. Avvia il programma:
   ```bash
   python TGeniusAI.py
   ```

---

## 📚 **Come Usare**

1. **Carica o Registra un Video** / Audio:
   - Puoi anche trascinare e rilasciare un file direttamente nella finestra.
   - In alternativa, puoi registrare lo schermo con [**Registrazione Schermo**](#registrazione-schermo-e-gestione-audiovideo).
2. **Modifica**:
   - Taglia, unisci, rimuovi parti superflue del video.
   - Gestisci l’audio (sostituisci traccia, inserisci pause, freeze frame).
3. **Trascrivi**:
   - Trascrizione automatica integrata (basata su `speech_recognition`) e supporto per la lingua selezionata.
   - Correzione e Riassunto con IA (Anthropic).
4. **Genera Audio**:
   - Con ElevenLabs e/o Bark, puoi creare una traccia TTS professionale.
   - *(Opzionale)* Lip Sync (sincronizzazione labiale) con Wav2Lip.
5. **Salva** o **Condividi** il progetto (ad es. su Teams).

---

## **Integrazioni AI e TTS**

- **AudioGenerationREST.py**: integrazione con le API di [**ElevenLabs**](https://elevenlabs.io/) per generare voci di alta qualità.  
- **BarkTest.py**: script di esempio per utilizzare la libreria **Bark** nella generazione di audio “emozionale” e con placeholders (`[laughs]`, `[sighs]`, ecc.).  
- **ProcessTextAI.py**: utilizza *Anthropic* per generare riassunti e correzioni del testo trascritto.  
- **PptxGeneration.py**: crea presentazioni personalizzate con l’aiuto delle stesse API.

Per usare questi servizi, **è necessario impostare** le chiavi API corrispondenti all’interno di un file `.env` oppure tramite variabili d’ambiente (vedi sezione **API Key**).

---

## **Registrazione Schermo e Gestione Audio/Video**

- **ScreenRecorder.py**: Cattura video del desktop (GDI su Windows), con o senza audio.
- **Registrazione Multi-Audio**: È possibile registrare da più fonti audio contemporaneamente (es. microfono + audio di sistema). Per farlo, nella sezione "Seleziona Audio" del dock di registrazione, basta spuntare le caselle di controllo (checkbox) di tutti i dispositivi desiderati. L'applicazione unirà automaticamente le tracce audio.
- Possibilità di selezionare **uno specifico schermo** se multipli.
- **AudioDock**: Dock dedicato alla sostituzione traccia principale, inserimento pause, impostazione audio di sottofondo e freeze frame.

---

## **Creazione Presentazioni AI**

- **PptxGeneration.py**: genera e salva automaticamente presentazioni *.pptx* partendo da un testo.  
- Supporta input da file `.txt` o direttamente dal testo trascritto, integrandosi con *Anthropic* per la creazione di slide strutturate.

---

## 🔑 **API Key**

Alcuni servizi AI (es. ElevenLabs, Anthropic) richiedono una **API Key**.  
- Crea un file `.env` o esporta le variabili d’ambiente con chiavi come `ELEVENLABS_API_KEY` e `ANTHROPIC_API_KEY`.
- In `TGeniusAI.py`, è presente un metodo *Imposta API Key* nel menù a toolbar per aggiornarla anche all’interno dell’applicazione.

---

## 🛠️ **Generazione dell’Eseguibile (.exe) con PyInstaller**

- Utilizza `TGeniusAI.spec` per creare un eseguibile standalone:
  ```bash
  pyinstaller TGeniusAI.spec
  ```
- L’eseguibile è disponibile nella cartella `dist/`.
- Nella cartella `dist/Release` troverai una versione .zip archiviata.

---

## 🛠️ **Creazione dell’Installer Windows con Inno Setup (.iss)**

- Con Inno Setup, puoi creare un installer Windows senza privilegi di amministratore:
  ```bash
  ISCC TGeniusAI.iss
  ```
- L’installer finale verrà generato nella cartella di output specificata dal file `.iss`.

---

## **Autore e Informazioni**

- Sviluppato da **FFA**.  

---
