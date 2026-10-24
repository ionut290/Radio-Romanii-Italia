# Audit Ghidul Românilor din Italia — 24 octombrie 2026

## Situația catalogului

- **497** fișe din catalogul public inițial.
- **492** fișe publice păstrate pentru afișare, fără a include înscrierile RDI din Firestore.
- **71** fișe îmbogățite cu informații suplimentare și legături către surse:
  - **55** pe baza site-urilor oficiale, paginilor instituționale ori profilurilor oficiale ale firmelor;
  - **16** din directoare publice terțe — informații de reconfirmat.
- **5** fișe temporar ascunse din cauza contradicțiilor sau a statutului neclar.
- **421** fișe încă fără cercetare suficientă a detaliilor.
- **1** dintre cele rămase au un URL de site/profil în catalogul inițial.

## Categorii cu detalii suplimentare

- Transport România–Italia: 25
- Magazine românești: 16
- Sănătate și servicii profesionale: 16
- Transport și logistică: 6
- Auto și mecanică: 3
- Curățenie: 2
- Asociații și comunitate: 2
- Restaurante românești: 1

## Integritate și transparență

Toate cele 421 de fișe cu informații lipsă sunt în `data/DIRECTORY-RESEARCH-BACKLOG.json`, cu nume, localitate, categorie, sursa inițială, câmpurile de verificat și o legătură de **căutare**, care nu constituie dovadă. Statusul apare diferit pe carduri și pe hartă: surse oficiale, directoare terțe și fișe de bază. Recenziile de pe alte platforme rămân accesibile prin linkuri, fără copierea de scoruri sau texte.

## Fișe reținute pentru clarificări

- **Ristorante Rumeno Robis** (Roletto): La vecchia scheda descrive un ristorante romeno; il sito web associato mostra ora il Ristorante 288, cucina giapponese, con indirizzo diverso. Identità da verificare. — https://www.ristorante288.com/
- **Rotari Trasporti SRL (socio unico)** (Imola): La voce è per Rotari Trasporti SRL, ma il sito collegato descrive Imola Trasporti in Via Gioacchino Zambrini 1 anziché Via Alessandro Manzoni 5. Senza conferma di identità non si devono attribuire i servizi di un'altra azienda. — https://www.imolatrasporti.it/contatti/
- **Dr.ssa Lazarescu Madalina Gabriela** (Uzzano): La scheda pubblica indica Uzzano, mentre il sito ufficiale presenta una sede a Borgo a Buggiano. Verificare indirizzo e coordinate prima della ripubblicazione. — https://www.studiodentisticolazarescu.it/
- **Georgescu Dr. Delia Gabriela** (Erice): Il sito collegato è riferito allo Studio della Dott.ssa Delia Georgescu in Via Marconi 118, ma questa scheda riporta Via Marconi 563 a Erice. Possibile duplicato/conflitto di indirizzo; mantenuta in verifica. — https://www.georgescu.it/contatti.html
- **Dental MTC di Tanase Marius** (Maleo): Un repertorio riporta il laboratorio odontotecnico Dental MTC di Tanase Marius come cessato, mentre un altro pubblica ancora orari di apertura. Verificare lo stato attuale prima di mostrarlo come attivo; non confondere un laboratorio odontotecnico con uno studio dentistico. — https://www.ufficiocamerale.it/4912/dental-mtc-di-tanase-marius-constantin

## Surse și completări realizate în ultima rundă

- Comune di Pescara: asociația română de voluntariat, telefon, email, orar de audiență.
- Studio Florina Gheorghe: servicii odontoiatrice, telefon, email și programări.
- Antras Log Italia: servicii de transport internațional și logistică frigorifică, pagină oficială de companie.
- Magazin La Maricel: telefon și orare din catalog local, de reconfirmat.
- Studio Adela Rosca: contact din repertoriu de structuri convenționate.
- Carrozzeria Praciosa: contact și servicii din directoare terțe.
- Lucaci Daniel: activitatea legală de transport rutier din repertoriu de firmă, fără inventarea rutelor.
- Impresa Pulizie Giulia: telefon și nepotrivire de număr civic — pin aproximativ.
- Studio Delia Georgescu: servicii și orar de pe site-ul oficial; vechea fișă la nr. 563 a fost suspendată pentru conflict.
- Dental MTC: statut neclar — un repertoriu îl indică „cessata”; fișa suspendată până la verificare.
- Transilvania din Lugo și Faenza: adrese din locatorul oficial Digi, pin de oraș până la verificarea coordonatelor.
- Bucovina, Sant’Angelo Lodigiano: înregistrare alimentară din repertoriu public.
- Studio Suciu Maria, Roma: program dintr-o pagină profesională externă, de confirmat.

- Romag-Prodotti Rumeni (Fiano Romano): contatti e orari da Waze legati allo stesso sito e indirizzo, denominazione legale da confermare.

## Reguli editoriale

- Nu inventăm ore, prețuri, servicii, limbi, fotografii, evaluări ori contacte.
- Fiecare completare salvează `detailsSourceUrl`, `detailsSourceName`, `detailsCheckedAt` și `verificationDetail`.
- Un site oficial constituie sursă pentru date, nu certificare profesională ori autorizare a activității.
- Coordonatele inițiale nu sunt folosite ca adresă exactă atunci când există o contradicție.
- Testele automate verifică integritatea catalogului, punctele hărții și lista de cercetare.
