# RDI Europa — monitor video istituzionali (fase 1: catalogo, NON in onda)

## Stato

Monitoraggio e catalogo **preparatori**. Questa funzione NON comanda FFmpeg,
YouTube, Facebook, Chromium, AzuraCast e non modifica la musica della radio.
Il relay attuale rimane invariato. Il file di palinsesto ha sempre
`live_enabled: false` e `playback_mode: STAGING_ONLY`.

## Fonti verificate

- **Parlamento europeo** — feed RSS video/eventi in italiano:
  https://www.europarl.europa.eu/rss/video/other-events/it.xml
  (i titoli italiani NON dimostrano che l'audio del video sia italiano).
- **Commissione europea** — pagina ufficiale degli ultimi video:
  https://audiovisual.ec.europa.eu/en/media/video
  (lettura dei link visibili a video; se il sito cambia struttura, il monitor
  registra un errore e conserva il catalogo precedente).

Il workflow `.github/workflows/europa-videos.yml` controlla ogni mezz'ora,
normalizza le fonti, elimina i duplicati per URL e memorizza fino a 150
candidati in `data/europa-video-candidates.json`. I campi diagnostici
`sources` e `success_sources` consentono di scoprire se una fonte è irraggiungibile.
Pagina di consultazione: `/europa-video.html`.

## Criteri necessari PRIMA di una messa in onda

Non utilizzare mai direttamente i candidati. Prima di approvare ogni clip:

1. Verificare guardando/ascoltando il file che **la traccia parlata sia in
   italiano**, non soltanto il titolo o i sottotitoli.
2. Verificare sulla scheda originale i **diritti specifici di riutilizzo,
   pubblicazione su YouTube/Facebook** e presenza di musica, persone, opere o
   elementi di terzi. Il copyright generico dell'istituzione non basta.
3. Usare una copia diretta HTTPS del video ufficiale disponibile
   legittimamente, senza aggirare restrizioni o sistemi di protezione.
4. Registrare la fonte, il link alle condizioni applicabili, un credito
   appropriato, durata, operatore e istante di controllo; usare il filmato
   integrale se richiesto dalla licenza.
5. Verificare attualità, contesto editoriale e correttezza delle eventuali
   scritte RDI. Rimuovere un servizio quando i diritti scadono.

### Schema di un video approvato (modello, NON video reale)

Inserire in `data/europa-video-approved.json` nel campo `items` solo record
controllati. Esempio di struttura, con valori da **sostituire** (NON
incollare come file approvato):

```json
{
  "id": "identificativo-stabile",
  "source_id": "commissione_europea",
  "title": "Titolo originale",
  "source_url": "https://audiovisual.ec.europa.eu/en/media/video/I-XXXX",
  "media_url": "https://URL-DIRETTO-DEL-VIDEO-APPROVATO.mp4",
  "rights_url": "https://audiovisual.ec.europa.eu/en/conditions-of-use",
  "credit": "© European Union, ANNO, CC BY 4.0",
  "duration_seconds": 120,
  "audio_mode": "separate_it",
  "audio_track_language": "it",
  "audio_url": "https://INDIRIZZO-AUDIO-ITALIANO-LECITO.aac",
  "audio_offset_ms": 0,
  "original_audio_muted": true,
  "audio_sync_verified": true,
  "approved": true,
  "audio_italiano_verificato": true,
  "diritti_verificati": true,
  "musica_e_terzi_verificati": true,
  "video_completo": true,
  "reviewed_by": "RDI redazione",
  "reviewed_at": "2026-10-29T19:00:00+01:00",
  "expires_at": null
}
```

Per video del Parlamento usare `source_id: parlamento_europeo`, URL della
pagina originale del Parlamento e credito/condizioni specifiche.

Il modulo `scripts/update_europa_videos.py` scarta automaticamente
registrazioni prive anche di un solo campo obbligatorio; non approva video
basandosi solo sull'RSS. Il catalogo automatico NON sovrascrive
`data/europa-video-approved.json`.

## Palinsesto quotidiano 18:00 Europe/Rome

`data/europa-video-playout.json` prepara fino a 8 prossimi appuntamenti
alle 18:00 italiane, scegliendo a rotazione i soli video già approvati.
Se la libreria approvata è vuota, registra `NESSUN_VIDEO_APPROVATO`
e non inventa un filmato. Le anteprime di programma sono **solo
preparatorie**; il servizio *non va in onda* in questa fase.

## Fase 2 — regia AV separata e collaudo

Il relay YouTube in `youtube-live/visual-relay.sh` mappa **sempre**
l'audio da AzuraCast con `-map 1:a:0`, anche quando Chromium mostra video.
**Aggiungere un elemento video alla pagina non ne trasmetterebbe l'audio!**
Per i servizi parlati serve una commutazione reale e sincronizzata di
**audio + video**, che:
- usi la stessa timeline per immagine e traccia italiana;
- mantenga notiziario, inserti pubblicitari e geopolitica senza
  sovrapposizioni e ridia la precedenza alla diretta operatore;
- abbia un watchdog con ritorno automatico al relay attuale;
- passi un test privato sul server Oracle prima di qualunque switch
  del programma pubblico.

NON attivare autonomamente un playout dei video senza tale collaudo.

## Informazioni legali

Commissione: https://audiovisual.ec.europa.eu/en/conditions-of-use

Parlamento: https://multimedia.europarl.europa.eu/it

I diritti indicati possono escludere opere di terzi e richiedere credits o
autorizzazioni aggiuntive. La disponibilità gratuita NON significa licenza
universale per ritrasmettere su piattaforme commerciali.

## Risultato della prima esecuzione (29/10/2026)

Il workflow ha superato i test e ha acquisito 40 candidati dal portale
audiovisivo della Commissione. Il feed RSS diretto del Parlamento europeo
non ha fornito voci XML leggibili al runner GitHub: la diagnostica ne
segnala l'errore; non si considera attiva quella fonte finché il problema
non sarà risolto. Alcuni servizi espressamente classificati `EP News`
presenti sul portale audiovisivo UE sono riconosciuti come candidati
del Parlamento (sempre senza attribuire automaticamente audio italiano
o autorizzazioni di ritrasmissione).

Nessuno di questi candidati è attualmente pronto per il playout: la
libreria di approvazioni è vuota e la diretta RDI resta invariata.

## Audio italiano alternativo: verifica del 29/10/2026

La scheda ufficiale
https://audiovisual.ec.europa.eu/en/media/video/I-294336
offre nella barra del lettore **LANGUAGE > Italiano**, e nella scheda
**Downloads > Audio > Choose language > Italiano (IT)**. Il menu per il
**video** invece propone solo **Original**. Questo distingue una
interpretazione italiana riproducibile/scaricabile da un video MP4
già doppiato. Il menu è stato verificato via browser; il file IT non
è ancora stato scaricato o ascoltato integralmente, e i diritti del
singolo filmato sono ancora da approvare.

Il monitor `scripts/update_europa_videos.py` esamina progressivamente
le pagine ufficiali cercando "Languages ... Italiano". Imposta
`italian_audio_candidate` ma **non approva l'audio automaticamente**,
perché i metadati possono riferirsi a una variante del video. Le schede
controllate nel lettore hanno in più
`italian_audio_in_player_verified` e
`italian_audio_download_option_verified`; non sono autorizzazioni.

### Procedura per preparare un video italiano senza andare in onda

Una volta che la redazione ha ottenuto legalmente video originale e
audio italiano separato, verificato i diritti, il parlato, l'allineamento
e compilato tutti i campi in
`data/europa-video-approved.json` (inclusi i campi qui sopra), si può
preparare il file locale con:

```bash
python3 scripts/prepare_europa_av_preview.py \
  --id IDENTIFICATIVO_VERIFICATO \
  --video /percorso/locale/originale.mp4 \
  --audio /percorso/locale/italiano.aac \
  --output /percorso/locale/rdi-europa-anteprima.mp4
```

Senza `--execute` fa solo controlli e mostra il piano. Con
`--execute` genera localmente un MP4 di prova, sostituendo l'audio
originale con la traccia italiana. **Non** accede alla chiave YouTube
e **non** modifica FFmpeg live, Facebook, Chromium o AzuraCast.

Per video con audio italiano interno già verificato, usare
`audio_mode: embedded_it` e `audio_stream_index` (indice fra le
tracce audio; non l'indice globale del file); in tal caso omettere
`--audio`. Sono richiesti comunque `audio_track_language: it`,
`audio_sync_verified: true`, approvazione diritti e credito.

La durata ammessa per anteprime approvate è ora fino a 30 minuti.
Un filmato di 15:49 non viene più escluso automaticamente dal limite
precedente di 15 minuti. Ogni preview è soggetta al collaudo umano di
sincronizzazione prima di qualunque eventuale programmazione.

I video della Commissione e del Parlamento non vanno ripubblicati o
ritrasmessi indiscriminatamente: verificare per ciascun filmato
le condizioni di utilizzo e eventuali diritti di terzi, non soltanto
la lingua italiana disponibile.
