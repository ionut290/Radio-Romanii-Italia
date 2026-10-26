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

## Aggiornamento amministrazione del 26 ottobre 2026 — limitazioni e nuovi strumenti
- Il pannello **Qualità del catalogo RDI** ora consente di filtrare per telefono, WhatsApp, email, foto, sito e orari mancanti. Mostra fino a 20 schede alla volta, offre link di ricerca per nome e indirizzo ed esporta un CSV coerente con il filtro.
- Il modulo `directory-public-admin.js` prepara un editor separato per le schede del catalogo pubblico; il codice originale del catalogo resta immutato. **La funzione è intenzionalmente nascosta finché il client non riesce a leggere `directoryOverrides` tramite Firestore.**
- **Attenzione:** nel file `firestore.rules` attualmente versionato NON è presente una regola `directoryOverrides`. L'editor non è abilitato e NON bisogna aspettarsi che salvi modifiche. È necessario progettare, revisionare, testare e pubblicare regole appropriate su Firebase prima di abilitarlo.
- Le integrazioni di recapiti verificate via ricerca sono state aggiunte a `data/directory-enrichments.json`, senza modificare le schede presenti direttamente in Firestore.
- Pubblicazione GitHub Pages e autorizzazioni Firestore sono processi diversi: un commit GitHub non dimostra che le regole Firebase siano già aggiornate.

## Progressi aggiuntivi del 26 ottobre 2026
- Ricerca manuale ampliata in diverse città: nuovi numeri verificati per San Donà di Piave, Bolzano, Flero, Monteriggioni, Firenze, Sciacca, Campobasso, Roma e Dueville. Numeri, email e siti vengono aggiunti solo quando nome e indirizzo corrispondono.
- L'importatore Excel riconosce adesso le righe con `origin=public-json` e differenze nei campi esistenti. Per cambiare telefono, WhatsApp o email pubblici è richiesta la colonna facoltativa `contactSourceUrl` con URL HTTPS verificabile. La colonna `email` resta facoltativa, compatibile con vecchie esportazioni.
- Le correzioni pubbliche sono salvate con `setDoc(..., {merge:true})` nella raccolta `directoryOverrides`; in caso di permessi Firebase mancanti vengono segnalate come bloccate, senza arrestare la preparazione delle altre operazioni.
- Il backup Excel eseguito dal pannello ora include gli arricchimenti pubblici consultati, conservando gli ID originari.
- Il repository contiene ora una regola `directoryOverrides` con scrittura riservata all'amministratore verificato. **Questa regola è presente su GitHub, ma non risulta pubblicata in Firebase tramite i soli commit.**
- Il database delle attività approvate su Firestore non è stato esportato direttamente in questa sessione. I conteggi del catalogo pubblico non rappresentano tutto il database operativo.

### Prima importazione dopo la pubblicazione delle regole
1. Confronta le regole Firestore attive con il repository e pubblica solo la modifica approvata.
2. Accedi al Ghid con l'account amministratore verificato e scarica il backup Excel.
3. Modifica una sola scheda pubblica, lasciando invariati `origin` e `id`; per telefono, WhatsApp ed email nuovi inserisci `contactSourceUrl` HTTPS.
4. Esegui l'importazione di prova, controlla il numero delle modifiche e verifica la scheda nel Ghid.
5. Procedi per lotti e controlla eventuali doppioni o righe escluse; non ripetere un lotto dall'esito incerto.

Le fotografie rimangono assenti dal catalogo pubblico finché non sono fornite o autorizzate. I telefoni mobili non vengono presentati automaticamente come WhatsApp.
