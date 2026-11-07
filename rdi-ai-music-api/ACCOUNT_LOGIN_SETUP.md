# RDI AI MUSIC — Attivazione account con Google o codice email

## Stato

Il backend e le pagine sono nel repository GitHub. Le modifiche al repository **non aggiornano automaticamente** il backend attivo su Oracle Cloud.

Le pagine pubbliche nuove sono:
- `/accedi-ai-music.html`: **Continua con Google** tramite Google Identity Services e, in alternativa, login via email con codice di 6 cifre valido per 10 minuti.
- `/profilo-ai-music.html`: profilo e brani inviati, visibili solo al proprietario.
- `/artisti-ai.html`: caricamento multiplo da 1 a 10 brani, protetto quando si attiva il login.
- `/spotlight-ai.html`: ascolto sempre pubblico; voto e commenti protetti quando si attiva il login.

## Prerequisiti

1. **Google Login:** un Client ID OAuth di tipo **Applicazione web** generato su [Google Cloud Console](https://console.cloud.google.com/auth/clients) con origine JavaScript autorizzata esatta `https://radioromanii.duckdns.org`. Includere l'account fra i test users se la schermata di consenso è in modalità Testing. Non servono redirect URI né una password Google: il popup è gestito da Google Identity Services.
2. **Login via email facoltativo:** una casella email dedicata alla radio e un provider SMTP con autenticazione (TLS STARTTLS su 587 oppure SSL su 465), con credenziali gestite come segreti sul server.
3. Backup del database SQLite e del file `app.py` attualmente in esecuzione.
4. Ambiente Python del backend con `Flask` e **`google-auth[requests]`** installati: `python -m pip install 'google-auth[requests]>=2.30,<3'` nell'ambiente virtuale usato da Gunicorn. Per i codici email vengono usate anche librerie standard (`smtplib`, `ssl`, `email.message`).
5. Verificare il percorso effettivo e il servizio di `rdi-ai-music` con `systemctl cat` prima di sostituire alcun file.

## Variabili d'ambiente da impostare sul backend Oracle

```bash
RDI_AI_GOOGLE_CLIENT_ID=123456789012-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
RDI_AI_SMTP_HOST=smtp.example.net
RDI_AI_SMTP_PORT=587
RDI_AI_SMTP_SSL=0
RDI_AI_SMTP_USER=radio@example.net
RDI_AI_SMTP_PASSWORD=<password dell'app email>
RDI_AI_SMTP_FROM=radio@example.net
RDI_AI_AUTH_SECRET=<stringa casuale robusta, almeno 32 caratteri>
RDI_AI_REQUIRE_LOGIN=0
RDI_AI_SUBMISSION_RATE_MAX=12
```

Questi sono **esempi**: il Client ID deve essere quello effettivo del progetto Google RDI. È un identificatore pubblico e può essere incluso nella configurazione che la pagina legge da `GET /api/ai-music/auth/config`; **mai pubblicare Client Secret, chiavi o password**. L'accesso Google non richiede SMTP, quindi le variabili `RDI_AI_SMTP_*` si possono omettere finché non si vuole attivare l'email con codice. Sostituire gli altri dati con quelli del provider. Non pubblicare le credenziali su GitHub o nella chat. Impostare permessi 600 sull'eventuale file di ambiente e includerlo in un `EnvironmentFile` del servizio systemd. Mantenere il token admin già configurato.

## Ordine di attivazione senza interruzioni

1. Controllare le differenze tra `rdi-ai-music-api/app.py` nel repository e il file in esecuzione; applicare le modifiche rispettando eventuali personalizzazioni locali. Verificare `python3 -m py_compile app.py`, fare backup e riavviare il servizio.
2. Mantenere `RDI_AI_REQUIRE_LOGIN=0` nella prima verifica. Testare `GET /api/ai-music/health` e `GET /api/ai-music/auth/config`, che deve mostrare `"google_available":true`, `"google_client_id":"...apps.googleusercontent.com"`. Se SMTP è configurato, anche `"email_available":true`.
3. Accedere a `accedi-ai-music.html` e verificare **Continua con Google** da un account di prova, la creazione della sessione, il recupero delle vecchie canzoni e il logout. Se SMTP è configurato, verificare anche l'arrivo del codice email e il funzionamento dell'accesso alternativo.
4. **Solo dopo un login Google reale riuscito** (e, se desiderato, email) impostare `RDI_AI_REQUIRE_LOGIN=1` e riavviare il backend.
5. Verificare che il caricamento anonimo dia 401, che un account registrato possa caricare, che i voti e i commenti richiedano una sessione valida e che la riproduzione audio e la classifica rimangano pubbliche.
6. Verificare dal pannello Redazione che le candidature restino in attesa dell'approvazione. Il cambio di autenticazione non approva o manda in onda automaticamente alcun brano.

## Protezioni previste

- Sessioni di 14 giorni, bearer token casuali; sul server sono memorizzati solo i loro hash.
- ID token Google con firma, pubblico destinatario (audience), issuer, validità temporale, nonce ed email verificati dal server tramite libreria ufficiale `google-auth`.
- Collegamento account tramite il `sub` Google stabile; protezione contro l'associazione di due account Google diversi alla stessa email.
- Codice email utilizzabile una sola volta, scadenza a 10 minuti e massimo cinque tentativi.
- Limite alle richieste di codice per email/IP; nessun codice di accesso esposto nelle risposte API.
- Un voto per account e brano, controllato dal database.
- 12 caricamenti per account per ora e limite separato per IP; mantenimento della moderazione.
- Vecchie candidature legate a un account solo dopo la verifica della stessa email.

## Verifica di regressione

Eseguire:
```bash
python -m unittest discover -s rdi-ai-music-api -p 'test_*.py' -v
```

Non abilitare l'obbligo di login se nessuno dei provider (Google o SMTP) funziona: il sito pubblico deve continuare a riprodurre la musica mentre si configura il servizio.
