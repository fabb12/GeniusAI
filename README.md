# ThemaGeniusAI - README

## Panoramica

ThemaGeniusAI è un'applicazione completa per la gestione di video e audio. Offre una vasta gamma di funzionalità, tra cui riproduzione di video, editing, generazione audio, trascrizione e registrazione dello schermo. Questo README fornisce una panoramica delle funzioni e delle caratteristiche principali di ThemaGeniusAI.

## Funzionalità

### 1. Riproduzione di Video e Audio
- **Play/Pausa/Stop**: Controlla la riproduzione di file video e audio.
- **Controllo del Volume**: Regola il volume dell'uscita audio.
- **Controllo della Velocità**: Regola la velocità di riproduzione del video.
- **Visualizzazione del Timecode**: Mostra il tempo corrente e totale del media in riproduzione.
- **Ritaglio Video**: Zooma e muovi l'area di riproduzione del video.

### 2. Editing di Video e Audio
- **Imposta Segnalibri**: Imposta segnalibri di inizio e fine per segnare sezioni del video.
- **Taglia Video**: Taglia sezioni del video tra i segnalibri impostati.
- **Elimina Segmento Video**: Rimuovi segmenti del video tra i segnalibri impostati.
- **Applica Ritaglio**: Ritaglia il video in un'area specifica.
- **Unisci Video**: Unisci due video a un timecode specificato.

### 3. Gestione Audio
- **Sostituisci Audio**: Sostituisci la traccia audio principale di un video con un altro file audio.
- **Applica Pause**: Inserisci pause silenziose nella traccia audio a timecode specificati.
- **Applica Audio di Sottofondo**: Aggiungi audio di sottofondo al video e regola il suo volume.

### 4. Trascrizione e Riassunto
- **Trascrivi Video**: Genera una trascrizione testuale dell'audio del video.
- **Riassumi Testo**: Riassumi il testo trascritto in punti elenco.
- **Inserimento Timecode**: Inserisci automaticamente timecode nel testo trascritto.
- **Rileva Lingua**: Rileva automaticamente la lingua del testo trascritto.

### 5. Generazione Audio con AI
- **Genera Audio con AI**: Genera audio utilizzando l'AI di Eleven Labs con impostazioni personalizzabili per voce, stabilità e stile.
- **Applica Audio Generato**: Applica l'audio generato al video, con opzioni per allineare il video alla nuova durata dell'audio.

### 6. Registrazione Schermo
- **Registra Schermo**: Registra lo schermo con opzioni per selezionare lo schermo e la fonte audio.
- **Pausa/Riprendi Registrazione**: Metti in pausa e riprendi la registrazione dello schermo.
- **Salva Registrazione**: Salva lo schermo registrato come file video.

### 7. Download Video
- **Scarica Video da YouTube**: Scarica video da YouTube, con opzioni per scaricare solo il video o anche l'audio.
- **Monitoraggio del Progresso**: Mostra il progresso del download.

### 8. Impostazioni e Personalizzazione
- **Gestione Layout Dock**: Salva e carica layout personalizzati per i componenti dell'interfaccia dockabile.
- **Modalità Scura**: Applica un tema scuro all'interfaccia dell'applicazione.
- **Gestione Chiave API**: Imposta e gestisci la chiave API per i servizi AI.

## Guida Rapida

### Installazione
1. Assicurati di avere Python installato.
2. Installa le dipendenze richieste:
   ```bash
   pip install -r requirements.txt
   ```

### Avvio dell'Applicazione
1. Avvia l'applicazione utilizzando il seguente comando:
   ```bash
   python main.py
   ```

## Uso

### Caricamento e Riproduzione di Video
1. Utilizza l'opzione **Open Video/Audio** nel menu **File** per caricare un file video o audio.
2. Controlla la riproduzione utilizzando i pulsanti play, pausa e stop.

### Editing di Video
1. Imposta segnalibri per marcare i punti di inizio e fine per tagliare o eliminare segmenti video.
2. Utilizza i pulsanti **Cut Video** o **Delete Video Segment** per eseguire le rispettive azioni.

### Trascrizione e Generazione di Audio
1. Carica un video e utilizza il pulsante **Transcribe Video** per generare una trascrizione.
2. Utilizza il pulsante **Generate AI Audio** per generare audio utilizzando l'AI.

### Registrazione dello Schermo
1. Seleziona lo schermo e la fonte audio nel dock **Recording**.
2. Avvia la registrazione utilizzando i pulsanti appropriati.