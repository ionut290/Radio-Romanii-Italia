# RDI YouTube live — intermezzi Italia e România tra le notizie

Implementato nel percorso **`youtube-news.html`** (pagina visiva catturata da
Chromium per il live YouTube). Non modifica il sito delle notizie statiche,
i feed degli articoli, AzuraCast, l'audio della trasmissione o FFmpeg.

## Sequenza in onda

- Ogni articolo di oggi resta visibile per 30 secondi.
- **Dopo ogni 4 notizie**, viene visualizzato per **20 secondi** un intermezzo
  silenzioso con immagini di Italia o România.
- L'ordine alterna i paesi, senza spacciare i contenuti per notizie correnti:
  nel riquadro compare sempre **IMAGINI DE ARHIVĂ · FĂRĂ SUNET**.
- Priorità: pubblicità AzuraCast, notiziario geopolitico, telecamere cittadine
  esplicitamente autorizzate; i video di paesaggio si fermano quando uno
  di questi programmi entra in onda.
- Il pulsante **muto** è applicato direttamente a ogni video; non viene
  creato alcun `Audio()` o nuovo stream da inviare alla radio.
- Se un MP4 Pexels non parte, appare il fermo immagine dello stesso filmato.
  Se anche l'immagine manca, il riquadro si chiude e riprendono le notizie.
- Le fotografie NASA non sono video in diretta: sono immobili con
  un lento movimento di panoramica grafica.

## Sei scene nella rotazione

1. **Roma (Italia)** — ripresa aerea, Florian Delée / Pexels;
   https://www.pexels.com/video/aerial-view-of-historic-rome-skyline-36386388/
2. **Bucegi (România)** — ripresa con drone, vlad sandu / Pexels;
   https://www.pexels.com/video/drone-footage-of-a-road-in-the-bucegi-mountains-romania-14664241/
3. **Italia di notte dallo spazio** — fotografia ISS040-E-90739 / NASA JSC;
   https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?frame=90739&mission=ISS040&roll=E
4. **Delta del Danubio dallo spazio (România)** — fotografia ISS005-E-18952 / NASA JSC;
   https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?frame=18952&mission=ISS005&roll=E
5. **Dolomiti (Italia)** — ripresa aerea, Rui Veiga / Pexels;
   https://www.pexels.com/video/scenic-aerial-view-of-seceda-dolomites-32070064/
6. **Rupea / Transilvania (România)** — ripresa con drone, vlad sandu / Pexels;
   https://www.pexels.com/video/drone-footage-of-rupea-fortress-in-transylvania-romania-14864544/

## Licenze e limiti

- Pexels: https://www.pexels.com/license/ — utilizzo editoriale/social
  gratuito generalmente consentito; non implicare sponsorizzazione.
  Verificare diritti di marchi/persone riconoscibili in ogni filmato.
- NASA JSC: https://www.nasa.gov/nasa-brand-center/images-and-media/
  e https://eol.jsc.nasa.gov/FAQ/ — credito alla NASA/JSC, immagini usate
  solo in contesto editoriale, senza implicare endorsement.
  Non utilizzare il logo NASA come marchio della radio.

## Controlli e gestione

Config: `data/youtube-landscapes.json`
`enabled`, `after_news_cards`, `duration_seconds`, `items`.
Solo fonti Pexels/NASA ammesse in `youtube-landscapes-core.mjs`; ogni
riga richiede credito, fonte, licenza, revisione e video muto.
Il file di configurazione può essere aggiornato senza cambiare il codice.
Per spegnere immediatamente una nuova programmazione, impostare
`enabled: false`. Per fermare una scena già in corso, la regia rispetta
`window.rdiLandscapeBreak.stop()` e le priorità degli spot e di geopolitica.

Per vedere una scena **solo in anteprima** senza aspettare la cadenza:
`/youtube-news.html?landscape_preview=1`.
Per controllare un'altra scena:
`/youtube-news.html?landscape_preview=1&landscape_id=ro-nasa-delta`.

L'aggiornamento automatico della pagina già aperta in Chromium segue
`data/youtube-build.json`; il client controlla ogni minuto.
I test di distribuzione includono `tests/youtube-landscapes.test.mjs`
e `node --check` del modulo.

**Nota:** il risultato di GitHub Actions verifica la logica, non prova da
solo che il browser del server Oracle riceva i video o che l'attuale
streaming YouTube sia online. Controllare sempre la pagina in browser.
