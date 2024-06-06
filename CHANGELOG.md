# Changelog

Tutti i cambiamenti notevoli a questo progetto saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), e questo progetto aderisce a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nuova funzionalità per la trascrizione video con supporto multilingua.
- Possibilità di unire video con timecode specificato dall'utente.
- Opzione per aggiungere pause audio in punti specifici del video.
- Implementazione della funzionalità di zoom e pan nel widget di ritaglio video.

### Changed
- Miglioramento dell'interfaccia utente per la selezione del dispositivo audio.
- Ottimizzazione delle prestazioni durante il caricamento dei video.

### Fixed
- Risolto un bug che causava il crash dell'applicazione durante il caricamento di file audio non supportati.
- Corretto un problema con la visualizzazione dei timecode nelle trascrizioni.

## [1.1.14] - 2024-06-06

### Added
- Implementata l'opzione per sincronizzare il video con la trascrizione tramite timecode.
- Aggiunta la funzionalità per tagliare segmenti di video tra due bookmark.

### Changed
- Modificata la barra degli strumenti principale per includere azioni di caricamento delle impostazioni dei dock.
- Aggiornamento della modalità scura per migliorare la leggibilità.

### Fixed
- Risolto un problema con la funzione di riproduzione che non si avviava correttamente dopo aver caricato un nuovo video.

## [1.1.13] - 2024-05-28

### Added
- Aggiunto supporto per la generazione di audio con Eleven Labs AI.
- Implementata la funzione per generare presentazioni PowerPoint dalla trascrizione del video.

### Changed
- Migliorata l'interfaccia utente per la gestione delle impostazioni della voce.
- Aggiornamento del layout dei dock per una migliore usabilità.

### Fixed
- Risolto un problema con la sincronizzazione del timecode durante la trascrizione.
- Corretto un bug che causava l'errato salvataggio delle impostazioni dell'utente.

## [1.1.12] - 2024-05-20

### Added
- Aggiunta la funzionalità per estrarre l'audio dai video e applicare nuovi audio.
- Implementata la possibilità di aggiungere pause nel testo trascritto.

### Changed
- Aggiornamento del design dell'interfaccia utente per una migliore esperienza visiva.
- Ottimizzazione del codice per migliorare le prestazioni durante la riproduzione video.

### Fixed
- Risolto un bug che causava errori di decodifica durante il caricamento di alcuni file di testo.
- Corretto un problema di crash quando si selezionava un dispositivo audio non valido.
