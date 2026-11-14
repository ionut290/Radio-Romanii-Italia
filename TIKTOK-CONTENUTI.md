# Contenuti TikTok RDI

Il publisher supporta due formati:

- **video**: un file MP4 già presente sul server;
- **photo**: una o più immagini pubblicate tramite URL del dominio verificato.

## Video live

Variabili:

```
RDI_TIKTOK_CONTENT_TYPE=video
RDI_TIKTOK_VIDEO_FILE=/var/lib/rdi-tiktok/rdi-live-promo.mp4
RDI_TIKTOK_TITLE=🔴 RDI è in diretta 24 ore su 24 | Link nel profilo
RDI_TIKTOK_DRY_RUN=true
```

## Foto, notizie e grafiche

```
RDI_TIKTOK_CONTENT_TYPE=photo
RDI_TIKTOK_PHOTO_URLS=https://dominio-verificato.it/rdi/news-1.jpg,https://dominio-verificato.it/rdi/news-2.jpg
RDI_TIKTOK_TITLE=Notizie RDI dall'Italia e dalla Romania
RDI_TIKTOK_DESCRIPTION=Segui RDI per aggiornamenti sulla diaspora romena in Italia.
RDI_TIKTOK_DRY_RUN=true
```

Il bot può quindi pubblicare automaticamente promozioni del live, notizie, citazioni, rubriche, eventi e grafiche. Per pubblicare foto tramite URL, TikTok richiede che il dominio sia verificato. Per rendere i post pubblici servono inoltre approvazione dell'app e autorizzazione dell'account TikTok.

La modalità predefinita è `DRY_RUN=true`: prima verifica il contenuto senza pubblicarlo.
