# Integrazione TikTok RDI

Il progetto è predisposto per pubblicare video promozionali verticali sul profilo TikTok `@ionelvarga7`.

## Configurazione necessaria

- creare un’app su TikTok for Developers;
- autorizzare il profilo con lo scope `video.publish`;
- salvare il token come secret Oracle `TIKTOK_ACCESS_TOKEN`;
- completare la revisione TikTok per la pubblicazione pubblica;
- generare sul server il file MP4 verticale:
  `/var/lib/rdi-tiktok/rdi-live-promo.mp4`.

Il video deve promuovere il live RDI 24/7 e invitare a usare il link nel profilo. Il publisher parte in modalità bozza finché `RDI_TIKTOK_DRY_RUN=false`.

TikTok richiede una chiamata a `creator_info/query`, il rispetto delle opzioni privacy restituite e poi l'inizializzazione Direct Post.
