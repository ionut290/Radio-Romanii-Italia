# RDI — Webcam cittadine nei 30 secondi del LIVE

## Cosa succede
Il video YouTube/Oracle mostra normalmente ogni notizia per 30 secondi. Dopo **5 notizie completate**, può apparire **1 webcam** per **30 secondi**, con paese, città e proprietario delle immagini visibili sullo schermo. Poi tornano le notizie. Le webcam autorizzate ruotano una dopo l'altra. L'audio AzuraCast rimane esattamente quello già in onda; non viene catturato l'audio delle webcam.

**I messaggi pubblicitari AzuraCast e la Geopolitica sincronizzata hanno precedenza.** Se iniziano, la camera viene rimossa e la normale rotazione riprende alla fine. Un errore nel file delle camere fa saltare lo slot senza interrompere le notizie. Si visualizza una sola camera alla volta, senza download massivo.

## Stato iniziale: nessuna webcam ritrasmessa

`data/youtube-camera-breaks.json` è intenzionalmente:
```json
{
  "enabled": false,
  "after_news_cards": 5,
  "duration_seconds": 30,
  "cameras": []
}
```
Non modificare `enabled` finché RDI non ha almeno una webcam con **autorizzazione esplicita** per la ritrasmissione nel proprio video/live YouTube, non semplicemente per il widget sul sito.

**Attenzione ai diritti.** Il permesso di incorporare una webcam Windy come `iframe` nel sito RDI NON è il permesso di catturarla tramite Chromium/FFmpeg e ritrasmetterla su YouTube. Le condizioni Windy proibiscono normalmente la redistribuzione del contenuto webcam senza diritti specifici. Anche YouTube, SkylineWebcams, EarthCam e altri player pubblici non sono automaticamente liberi da diritti.

## Registrare una webcam con autorizzazione

Quando un titolare conferma per iscritto il diritto di ridiffusione, aggiungere al JSON una voce così (solo esempio: **l'URL non è una vera webcam**):
```json
{
  "enabled": true,
  "after_news_cards": 5,
  "duration_seconds": 30,
  "cameras": [
    {
      "id": "bologna-centro",
      "city": "Bologna",
      "country": "Italia",
      "operator": "Nome vero del proprietario",
      "credit": "Nome vero del proprietario della webcam",
      "kind": "iframe",
      "src": "https://example.org/licensed-camera/embed",
      "youtube_live_rights": true,
      "audio_muted": true,
      "authorized_on": "2026-10-29",
      "permission_reference": "Documento/autorizzazione scritta conservata presso RDI"
    }
  ]
}
```
Scegliere `kind: "iframe"` per player HTML5 del titolare; `"video"` per un MP4/WebM o URL riproducibile direttamente da Chromium; `"image"` per una immagine JPEG/GIF aggiornata dal gestore. Sono accettati **solo URL HTTPS pubblici**; **non** inserire URL con credenziali, stream key, token privati o link a rete locale. Gli HLS `.m3u8` potrebbero non essere riproducibili da Chromium senza un adattatore: testarli prima di autorizzare la pubblicazione.

Annotare chi autorizza, esatta camera, canale YouTube, territorî, durata di utilizzo, necessità di attribuzione, diritto di cattura e ridistribuzione, eventuale monetizzazione e revoca. Il campo `permission_reference` è una prova amministrativa (non la concessione del diritto in sé). L'autorizzazione deve esistere realmente.

## Anteprima senza trasmettere webcam di terzi

Aprire:

[Anteprima grafica camera (nessuna webcam reale)](https://radioromanii.duckdns.org/youtube-news.html?camera_preview=1)

Mostra la grafica per 30 secondi con **ITALIA / BOLOGNA** e una zona neutra chiaramente denominata `ANTEPRIMA`. Non altera la diretta YouTube che il server cattura dall'URL senza parametri.

## Verifiche operative

1. `node --test tests/youtube-camera-breaks.test.mjs` verifica i blocchi legali, la periodicità, durata e integrazione con spot/Geopolitica.
2. `node --check youtube-camera-core.mjs` e `node --check youtube-camera-breaks.js`.
3. La workflow `.github/workflows/refresh-youtube-oracle.yml` controlla gli hash pubblicati dei nuovi asset prima di richiedere il refresh di Chromium su Oracle. Non riavvia FFmpeg.
4. Controllare YouTube Studio: ogni webcam deve funzionare realmente; se nera, bloccata, offline o contesa, disabilitare la voce. Non attribuire a un luogo immagini di un'altra città.

## Sicurezza

L'audio radio e i palinsesti AzuraCast non si modificano. Un iframe/URL esterno è un rischio operativo: usare soltanto URL del titolare autorizzato. I player proprietari possono disabilitare l'incorporamento, passare offline o chiedere interazione. In questo caso rimuovere la voce oppure ottenere un feed fornito espressamente per l'emittente.
