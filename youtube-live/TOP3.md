# RDI AI MUSIC — Top 3 quotidiana nel live YouTube

## Stato: puntata completa preparata, quattro passaggi quotidiani su AzuraCast
La pagina pubblica della diretta `youtube-news.html` carica il modulo
`youtube-ai-top3.js` e presenta durante le quattro puntate alle **09:30, 13:30, 17:30 e 20:30 Europe/Rome** una classifica TV
della community (prima la posizione 3, poi 2, poi 1). Il modulo:
- legge la classifica reale dalla API pubblica `/api/ai-music/spotlight?page=1`;
- considera **solo brani approvati con file audio caricato e ascolto pubblico abilitato** (`audio_preview=1`); scarta i brani con solo link esterno;
- **non rimuove** gli esclusi dalla classifica del sito RDI: ricompone soltanto il podio televisivo 3→2→1 con i successivi brani idonei;
- esempio verificato 7 novembre 2026: `Roma` (Massimo Sculli, senza file) è esclusa dalla Top 3 YouTube e sostituita da `Le colline di settembre` (N.p.L);
- usa esclusivamente voti, titoli e artisti presenti nella classifica;
- non ripete l'intermezzo nello stesso giorno nel medesimo browser;
- se ci sono meno di 3 brani, o la API non risponde, **non interrompe le notizie**;
- mostra la canzone `IN RADIO ORA` solo se titolo **e** artista coincidono
  con il reale `nowplaying` di AzuraCast.
- non crea audio o modifica AzuraCast o la chiave YouTube.
- dura 45 secondi, poi riprende la rotazione di notizie.
- è interrotto dalle grafiche prioritarie (spot, TG, ecc.) senza fermare il live.

Preview manuale **senza audio aggiuntivo**:
https://radioromanii.duckdns.org/youtube-news.html?rdi_top3_preview=1

## Per sentire davvero “Numero 3, Numero 2, Numero 1” e le canzoni
Attualmente YouTube usa come **unica sorgente audio** il flusso di AzuraCast:
`youtube-live/visual-relay.sh` passa `SOURCE_URL` direttamente a FFmpeg.
Il browser Chromium genera solo le immagini: audio HTML/non può essere sentito
su YouTube automaticamente. **La grafica TV da sola non trasmette le 3 canzoni.**

Passaggi per l'edizione radiofonica completa:
1. Raccogliere per ciascuna canzone consenso separato e verificabile per la
   trasmissione su **YouTube Live**, eventuale archivio del video e uso del file.
   `spotlight_consent=1` autorizza solo l'ascolto sul sito: **non equivale**
   a una licenza per YouTube.
2. Preparare 3 annunci vocali (“Posizione numero 3…”, “Posizione numero 2…”,
   “Primo posto…”) + i tre brani in ordine 3→2→1. Eseguire il controllo
   preventivo delle licenze dei brani generati con piattaforme esterne.
3. Programmare il blocco nell'AutoDJ/AzuraCast alla stessa ora, possibilmente
   come singola trasmissione/playlist programmata in ordine fisso con le
   preesistenti regole di priorità. Non modificare le playlist attive senza
   controllo e backup: il canale streaming non deve andare fuori onda.
4. Usare i metadati `nowplaying` per sincronizzare la grafica all'audio reale
   e fare partire la classifica TV soltanto quando il blocco Top 3 è
   effettivamente in onda. Le grafiche di "conteggio" non devono essere
   confuse con altre canzoni trasmesse dalla radio.
5. Collaudare in modalità non pubblica e monitorare i possibili reclami
   Content ID. Anche con licenza, un brano può richiedere l'allowlist del
   titolare per il canale YouTube.

**Non attivare il blocco audio finché non sono verificati tutti i passaggi.**
Riferimento YouTube: https://support.google.com/youtube/answer/3367684?hl=it


## Quattro repliche quotidiane (dal 7 novembre 2026)
La playlist `RDI AI MUSIC - TOP 3 del giorno` usa quattro schedule_items
con orari interi HHMM: 09:30–10:10, 13:30–14:10, 17:30–18:10 e
20:30–21:10 (fuso Europe/Rome), ciascuno con `loop_once=true`.
Il workflow giornaliero parte alle 06:30 UTC (07:30 CET / 08:30 CEST)
per aggiornare l'audio del giorno prima del primo appuntamento.
AzuraCast può leggermente posticipare l'avvio per rispettare i brani già in
onda. Nessun audio di Chromium viene inviato al live: la grafica segue
titolo ed elapsed reali dell'audio AzuraCast. La distribuzione verifica la
presenza esatta di tutti e quattro gli orari prima dell'abilitazione.
