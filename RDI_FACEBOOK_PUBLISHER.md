# Pubblicatore Facebook RDI

Il file \`rdi-facebook-publisher.py\` legge il feed pubblico \`news.json\`, evita i duplicati tramite un registro locale e prepara/pubblica i post sulla Pagina Facebook RDI.

## Configurazione Oracle

Variabili richieste:

\`\`\`bash
export RDI_FB_PAGE_ID="ID_DELLA_PAGINA"
export RDI_FB_PAGE_TOKEN="TOKEN_DELLA_PAGINA"
export RDI_FB_DRY_RUN="true"
export RDI_FB_MAX_POSTS="3"
\`\`\`

La modalità \`true\` è sicura: registra le bozze ma non pubblica. Dopo il test si può impostare \`RDI_FB_DRY_RUN=false\`.

Il token deve rimanere solo in un file protetto sul server Oracle e non deve essere inserito nel repository.

Esempio di avvio:

\`\`\`bash
python3 rdi-facebook-publisher.py
\`\`\`

Il processo può essere eseguito con un timer systemd ogni 15 minuti. Prima di attivare la pubblicazione reale occorre verificare la Pagina Facebook, il Page ID e i permessi Meta.
