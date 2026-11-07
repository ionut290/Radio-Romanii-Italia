# RDI AI MUSIC — Attivazione account con codice email

## Stato

Il backend e le pagine sono nel repository GitHub. Le modifiche al repository **non aggiornano automaticamente** il backend attivo su Oracle Cloud.

Le pagine pubbliche nuove sono:
- `/accedi-ai-music.html`: registrazione e login via email con codice di 6 cifre valido per 10 minuti.
- `/profilo-ai-music.html`: profilo e brani inviati, visibili solo al proprietario.
- `/artisti-ai.html`: caricamento multiplo da 1 a 10 brani, protetto quando si attiva il login.
- `/spotlight-ai.html`: ascolto sempre pubblico; voto e commenti protetti quando si attiva il login.

## Prerequisiti

1. Una casella email dedicata alla radio e un provider SMTP con autenticazione (TLS STARTTLS su 587 oppure SSL su 465), con credenziali gestite come segreti sul server.
2. Backup del database SQLite e del file `app.py` attualmente in esecuzione.
3. Ambiente Python con Flask già in uso dal backend; le nuove funzioni usano solo librerie standard aggiuntive (`smtplib`, `ssl`, `email.message`).
4. Verificare il percorso effettivo e il servizio di `rdi-ai-music` con `systemctl cat` prima di sostituire alcun file.

## Variabili d'ambiente da impostare sul backend Oracle

```bash
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

Questi sono **esempi**: sostituire con i dati del provider. Non pubblicare le credenziali su GitHub o nella chat. Impostare permessi 600 sull'eventuale file di ambiente e includerlo in un `EnvironmentFile` del servizio systemd. Mantenere il token admin già configurato.

## Ordine di attivazione senza interruzioni

1. Controllare le differenze tra `rdi-ai-music-api/app.py` nel repository e il file in esecuzione; applicare le modifiche rispettando eventuali personalizzazioni locali. Verificare `python3 -m py_compile app.py`, fare backup e riavviare il servizio.
2. Mantenere `RDI_AI_REQUIRE_LOGIN=0` nella prima verifica. Testare `GET /api/ai-music/health` e `GET /api/ai-music/auth/config`, che deve mostrare `"email_available":true`.
3. Accedere alla pagina `accedi-ai-music.html` e inviare un codice a una casella verificabile. Confermare la ricezione dell'email e il funzionamento del codice.
4. Solo dopo un login di prova riuscito, impostare `RDI_AI_REQUIRE_LOGIN=1` e riavviare il backend.
5. Verificare che il caricamento anonimo dia 401, che un account registrato possa caricare, che i voti e i commenti richiedano una sessione valida e che la riproduzione audio e la classifica rimangano pubbliche.
6. Verificare dal pannello Redazione che le candidature restino in attesa dell'approvazione. Il cambio di autenticazione non approva o manda in onda automaticamente alcun brano.

## Protezioni previste

- Sessioni di 14 giorni, bearer token casuali; sul server sono memorizzati solo i loro hash.
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

Non abilitare l'obbligo di login se SMTP o test di autenticazione non funzionano: il sito pubblico deve continuare a riprodurre la musica mentre si configura il servizio.
