# Known Issues

Tutti i problemi noti e le funzionalità pianificate saranno documentati in questo file.
## [2.8.0] - ?? 
- [x] aggiungere lo scopo durante l'estrazione dell info dal video 
- [ ] aggiungere selezione range temporale per trascrizione testo
- [x] aggiungere ctrl-f nel text edit 
- [ ] sistemare i dock quando vengono sganciati
- [ ] aggiungere dock per inserire copertina iniziale
- [ ] sistemare inserimento pausa nel audio 
- [x] implementare un sistema di auto apprendimento della dinamica del video 
- [x] aggiungere registrazione solo audio
- [x] aggiungere tasto condividi via what app , teams ecc...
- [x] aggiungere splash screen
- [x] aggiungere sync trascrizione video originali  
- [x] aggiungere caricamento metadati video e trascrizione
- [ ] aggiungere scrorrimento trascrizione evidenziandola mentre e' il video e' riproduzione
- [x] aggiungere zoom testo in area trascrizione con rotella + / -
- [x] non funziona generazione powerpoint 
- [ ] sistemare cuffie
- [ ] mettere webcam in pip'

- [ ] mettere strumenti evidenziazione del testo nel riassunto
- [x] sistemare watermark e puntatore cerchio
- [ ] togliere video e mettere in file
- [x] mettere tasto di esportazione word
- [ ] metter sincro video nel riassunto
-  
- [x] tasto trasferimento da video player input a video player output
- [x] migliorare funzionamento rettangolo ritaglio
- [x] mettere la barra di progressione quando uso la musica di sottofondo
- [x] mettere tasto di apertura file direttamente nel video player input e video  player output
- [x] cambiare label solo video
- [x] resettare x velocità ogni volta che apro
- [x] salvare il json appena viene modificata la trascrizione 
- [x] resettare i bookmark quando carico nuovo video
- [x] aumentare la precisione 00:00:000 quando selezione porzione con bookmark
- [x] metti la possibilità di mettere piu ritagli con i bookmark
- [x] quando salvo il video cambiando la velocità di riproduzione deve essere salvato anche con risoluzione originale non solo compressa
  gestisci un solo parametro per salvare con la velocità di riproduzione desiderata, tiene solo quella nella finestra di salvataggio,
  togli quella nelle impostazioni.
- [x] aggiungi metti in loop la musica di sottofondo se video>audio
- [x] aggiungere possibilità di mettere video in picture in picture, scegliendo la posizione da avere nel video finale 
- [x] aggiungere la possibilità di poter inserire un immagine, scegliendo la posizione e dimensione 
- [x] crea un nuovo menu con dentro , inserimento video pip e inserimento immagine 
- 
- [x] migliora la visualizzazione della barra di riproduzione, da fare piu grande e con una grafica piu professionale 
- [x] aggiugne barra di progresso quando taglio cancellazione
- [ ] implementare integrazione della webcam, nelle imopstazione metti un tab nouvo per selezionare il tipo di webcam , se la web cam è attiva dovrei vedre qulel che registra nel player input 
- [x] aggiugere una barra di stato sotto in fondo per segnalare per esempio che il video è stato elaborato o ha fintio di registrato  e togli i messagge box , 
- [x] scritta tempo diff in bianco nella timeline
- [ ] salvare posizione finestre anche quando sono floating
- [ ] salvare word con formattazione markdown  
- [ ] quando incollo testo ai rimuovi timecode
- [ ] usare whisper 
- [x] salvare su disco i file recenti 
- [ ] gestire meglio i contatti teams
- [ ] drag e drop da sistemare
- [ ] browser use 
- [x] mettere tasto salvataggio nel tab trascrzione , rissunto e audio ai , salva il json nnelle rispettive chiavi, e salva ogni 5 minuti automaticamente 
- [x] aggiungere replace nel search box e sistema il numero di elmentei trovati e sistema il colore di quadno non trova nulla metti colore arancione 
- [x] mettere tasti frecce per andare aventi e indietro nel playback del video
- [x] crea un nuovo dock note video dove mostro le note che  utente ha inserito nel video, tramite una funzione inserisci nota con tasto sx del mouse sul frame che in quel momento e visibile 
- [x] togliere dock downlaod e metterno sotto voce import come nuovo menu . deve aprire un dialog cone le stess impostazioni del dock
- [x] aggiungi il dock unisci video nel dock gestione audio (rinomina audio e video) , togli il dock unisci video 
- [x] quando premo su video nel dock progetto devi asggiornare anche informaizon video 
- [x] rendi coerente anche il dock registrazione (percorso file e nome della registrazione) con la nuova sezione dock progetti 
- [x] sistemare timecode audio ai 
- [x] migliroa evidenziazione del testo con colori giusto per sfondo scuro e scritta chiara
- [x] quando salvo video caricato nel video player outpout salvalo nella cartella clip mettendo il postfisso come _output nella cartella progetto  aggiungi un nuona voce nel menu file con 'salva' 
- [x] aggiorna visualzizaione del dock progetto in base a se trovi nuovoi file , se ne trovi aggiorna la vista , inoltere mettei anche al funzione di elimna file con tasto desto sul file 
- [x] quando crea nuovo progetto da la possiblia di sceleter anceh la cartella di dove salvare il progetto
- [x] esport corerttamten il riassuti nel file docx , esportta tutte informazoni del riassunto scritto mantenendo il piu possible la formattazione
-quando cancello un file dal dock progetto e dal fila .gnai cancella solo dalla vista non dal file system 
- aggiung funzoan import video da metter nel progetto '
- tasto desto su clip sceglie  dove aprire il video in  quale video player, input o ouput
- qundo fa il crop deve slvare nella cartella clip con prefisso cropped mantenendo stesso nome
## [1.2.2] - 2024-06-30
- [x] controllare periferiche audio come vengono associate
- 
## [1.2.1] - 2024-06-20
- [x] su alcune macchine la velocita' del video e' sbagliata rispetto a quello originale
- [x] aggiungere stretch video player output
- [x] aggiungere log nel file di testo
- [x] aggiungere indicatore presenza audio 
- [x] aggiungere tasto pausa rec
- [x] aggiungere nome timecode per video registrato
## [1.1.15] - 2024-06-10

- [x] aggiungere titolo del file da registrare nel dock di registrazione
- [x] aggiungere interruzione trascrizione
- [x] aggiungere la funzione ritaglio
- [x] aggiungere chiusura dock
- [x] modificare il processo di registrazione usand