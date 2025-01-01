# GeniusAI 

Questo programma offre un'interfaccia avanzata per la gestione di **video** e **audio**, facilitando la creazione di video tutorial.

Include funzionalità di **AI Generative** per la trascrizione automatica dei testi, con possibilità di generare riassunti chiari e strutturati, **TTS** per tracce audio professionali, **editing video** e **registrazione dello schermo**.

L'interfaccia grafica è stata sviluppata utilizzando **PyQt6**, garantendo un ambiente intuitivo e flessibile. Inoltre, è stato implementato un sistema di **docking delle finestre**, che permette all'utente di personalizzare il layout dell'applicazione per migliorare l'esperienza di utilizzo.

### 📚 **Processo Principale:**

1. **Registrazione del Video:** L'utente registra un video del tutorial che desidera creare.
2. **Trascrizione Automatica:** Il testo viene trascritto automaticamente e l'AI ottimizza e corregge eventuali errori.
3. **Modifica e Ottimizzazione del Testo:** Dopo la trascrizione, è possibile modificare il testo per ottimizzare ulteriormente il contenuto. Inoltre, l'utente ha la possibilità di ottenere un riassunto chiaro e strutturato, facilitando il processo di editing.
4. **Generazione Traccia Audio con TTS:** Una traccia audio viene generata con tecnologia TTS, garantendo un risultato finale chiaro e professionale.

Il testo trascritto può essere modificato per ottimizzare la qualità finale dell'audio e del video tutorial.

## 🚀 **Funzionalità Principali**

### 🎥 **Caricamento Video e Audio**

- Supporto a vari formati video (mp4, avi, mov) e audio (mp3, wav).
- Input e output video simultanei per lavorare su più clip.

### ✂️ **Taglio e Rimozione di Sezioni**

- Imposta segnalibri di inizio/fine per tagliare o rimuovere sezioni.
- Salva automaticamente le modifiche in nuovi file.

### 🔊 **Audio Dock**

- **Sostituzione Audio:** Carica una nuova traccia audio.
- **Pausa Audio:** Inserisci silenzi in punti specifici.
- **Freeze Frame:** Congela un frame video.
- **Audio di Sottofondo:** Aggiungi musica o effetti con controllo del volume.

### 🎞️ **Unione Video (Video Merge)**

- Unisci più clip video in un unico file.
- Specifica il timecode di unione.

### 📝 **Trascrizione e Sintesi Audio**

- Trascrivi audio/video in testo.
- Genera riassunti e correzioni con AI.
- Editor di testo avanzato con timecode automatici.
- Possibilità di ottimizzare e riassumere il testo trascritto.

### 🗣️ **Generazione Audio AI (ElevenLabs)**

- Genera tracce vocali sintetiche.
- Aggiungi pause automatiche.
- Sincronizzazione labiale con Wav2Lip. [To be completed]

### 📥 **Download da YouTube**

- Scarica video/audio direttamente da URL.

### 🖥️ **Registrazione Schermo**

- Registra lo schermo con supporto audio.
- Pausa e riprendi registrazioni.

### 📊 **Gestione Presentazioni AI**

- Genera presentazioni PowerPoint partendo da testo trascritto.

### 🛠️ **Gestione Layout Dock**

- Personalizza l'interfaccia con dock configurabili.
- Sistema di docking flessibile per organizzare le finestre di lavoro.

## 💻 **Requisiti**

- **Python 3.8+**
- **PyQt6**, **moviepy**, **pydub**, **pyaudio**, ecc.
- **ffmpeg** (non incluso, scaricabile dal sito ufficiale: [https://www.ffmpeg.org/download.html](https://www.ffmpeg.org/download.html) e da collocare nella cartella `./src/ffmpeg`).

## Installazione

1. **Clona il repository**:
   ```bash
   git clone https://github.com/fabb12/MFHelpDeskAI.git
   cd MFHelpDeskAI
   ```

2. **Crea un ambiente virtuale**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # per Mac/Linux
   # oppure:
   .\venv\Scripts\activate    # per Windows
   ```


## ▶️ **Avvio**

1. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
2. Avvia il programma:
   ```bash
   python TGeniusAI.py
   ```

## 📚 **Come Usare**

- Carica file video/audio.
- Modifica, taglia, unisci e aggiungi tracce.
- Trascrivi e genera audio con AI.
- Salva i risultati finali.

## 🔑 **API Key**

- Imposta la chiave API per la generazione vocale nelle impostazioni.

## 🛠️ **Generazione del file requirements.txt**

- Utilizza lo script `generate_requirements.py` per creare o aggiornare automaticamente il file `requirements.txt` con le librerie effettivamente utilizzate nel progetto.
- Esegui lo script:
  ```bash
  python generate_requirements.py
  ```

## 🛠️ **Installazione delle Dipendenze con install_requirements.py**

- Utilizza lo script `install_requirements.py` per installare in modo sicuro tutte le dipendenze elencate nel file `requirements.txt`.
- Esegui lo script:
  ```bash
  python install_requirements.py
  ```
- Lo script installerà le dipendenze una alla volta, segnalando eventuali pacchetti problematici.

## 🛠️ **Generazione dell'Eseguibile (.exe) con PyInstaller**

- Utilizza il file `.spec` per generare un eseguibile standalone.
- Comando di creazione:
  ```bash
  pyinstaller TGeniusAI.spec
  ```
- L'eseguibile verrà creato nella cartella `dist/`.
- Una versione archivio `.zip` sarà disponibile nella cartella `dist/Release`.

## 🛠️ **Creazione dell'Installer Windows con Inno Setup (.iss)**

- Utilizza il file `.iss` per creare un installer Windows senza richiedere privilegi di amministratore.
- Esegui il comando nel software **Inno Setup Compiler**:
  ```
  ISCC TGeniusAI.iss
  ```
- L'installer verrà generato nella cartella di output specificata nel file `.iss`.

## ℹ️ **Autore e Informazioni**

- Sviluppato da FFA.
- Per supporto, consulta la documentazione o contatta l'autore.

