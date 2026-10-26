# RDI — Completamento contatti e fotografie (26 ottobre 2026)

## Funzioni attuali
- La guida pubblica visualizza telefono, WhatsApp ed email solo quando presenti nella scheda.
- L'amministratore vede la sezione **Qualità del catalogo RDI**, con contatori dei campi mancanti e un export CSV delle sole schede incomplete.
- Il pulsante **Esporta Excel** include ora la colonna facoltativa `email`. Il vecchio tracciato Excel resta leggibile senza quella colonna.
- Il proprietario di una scheda Firestore può richiedere l'aggiunta di un'email e caricare una fotografia JPG/PNG/WebP (massimo 5 MB). Il sistema crea una richiesta di modifica in attesa. Le fotografie NON sono approvate automaticamente.
- L'amministratore vede i dati e l'anteprima della foto proposta prima di approvarli.
- Per le schede pubbliche JSON, sono ammesse immagini solo se `photoRightsStatus` è `permission-granted` o `owned-by-rdi` e gli URL sono HTTPS.

## Passaggio necessario: pubblicare le regole di Firestore
Le modifiche a `firestore.rules` in GitHub **non aggiornano automaticamente** le regole del progetto Firebase. Prima di utilizzare email e foto nelle richieste o nell'importazione, una persona con privilegi Firebase deve confrontare le regole correnti con quelle del repository, verificare che non siano state introdotte altre modifiche in produzione e pubblicare il file aggiornato in **Firebase Console → Firestore Database → Rules → Publish**. In alternativa utilizzare Firebase CLI soltanto da un ambiente già autenticato e con l'identità del progetto verificata.

Non sostituire alla cieca una versione di regole diversa da quella nel repository. Eseguire un backup ed eventualmente salvare le regole correnti.

## Procedura verificata da ripetere prima del rilascio
1. Accedere alla guida con l'account amministratore verificato.
2. Scaricare il backup Excel.
3. Esaminare il pannello di copertura e il CSV delle schede incomplete.
4. Verificare in ambiente di test la creazione di una scheda con e senza email.
5. Eseguire una modifica foto con account titolare e verificare che resti `pending`.
6. Approvare la foto e verificare che il nuovo URL appaia soltanto nella scheda corretta.
7. Importare un piccolo Excel con il campo email, verificare i risultati e solo poi procedere con file grandi.
8. Verificare che i dati preesistenti e le immagini già caricate restino intatti.

## Fonti e fotografie delle schede pubbliche
I dati di contatto devono avere una fonte consultabile, salvata con `contactSourceUrl`, `phoneSourceUrl` o `whatsappSourceUrl`, e una data di controllo. Una normale numerazione mobile non costituisce prova di disponibilità WhatsApp.

Le immagini da Google Maps, social network o directory non sono automaticamente riutilizzabili. Inserire foto esterne solo dopo autorizzazione del titolare o altra licenza idonea, documentando la provenienza in `photoRightsSourceUrl`. Esempio autorizzato:

```json
{
  "imageUrls": ["https://esempio.it/foto-autorizzata.jpg"],
  "photoRightsStatus": "permission-granted",
  "photoRightsSourceUrl": "https://esempio.it/autorizzazione-o-licenza"
}
```

Non aggiungere URL fotografici quando manca l'autorizzazione. Per le schede prive di immagini restano i segnaposto tematici, senza attribuire fotografie errate.

## Limiti noti
- Il CSV "schede incomplete" è un report, non deve essere reimportato direttamente in Firestore.
- Le email importate tramite Excel sono sottoposte a validazione, ma richiedono la pubblicazione delle nuove regole di Firestore.
- La colonna email è facoltativa: i file precedenti restano compatibili.
- Le fotografie non sono prelevate in automatico dal web; i titolari possono inviarle al processo di approvazione.
- RDI non può dedurre la disponibilità di WhatsApp dal solo numero telefonico.
