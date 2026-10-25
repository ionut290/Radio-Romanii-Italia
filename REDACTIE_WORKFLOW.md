# Proiect: Redacția R.D.I. — publicarea știrilor din atașamente

## Flux standard
Când utilizatorul atașează în conversația ChatGPT o fotografie, un afiș, un PDF sau un text și cere publicarea pentru Radio Românii din Italia:

1. Citește integral materialul atașat. Extrage faptele, numele, datele, contactele și sursa. Nu inventa informații; verifică afirmațiile externe atunci când este necesar.
2. Redactează un articol jurnalistic **original în limba română**, cu titlu, rezumat și text complet. Menționează sursa și eventualele informații neverificate.
3. Creează o imagine editorială relevantă; nu prezenta imagini generate drept fotografii autentice. Dacă se folosește afișul original, respectă drepturile de utilizare și păstrează informațiile fidele.
4. Publică în repository-ul GitHub `ionut290/Radio-Romanii-Italia`, ramura `main`. Categoria obligatorie: `Știri din redacție`.
5. Adaugă un articol cu `editorial: true`, `category: "Știri din redacție"`, `id` unic, `title`, `summary`, `body`, `published` ISO 8601, `source`, `byline`, `url` și `image` în `editorial.json`, fără a șterge articolele existente. Imaginile editoriale originale pot fi stocate în `images/` în repository.
6. Verifică existența articolului în fișierul GitHub și, dacă este posibil, pe site-ul public `https://radioromanii.duckdns.org/`. Nu declara verificată afișarea publică dacă nu a fost testată.
7. Nu modifica playerul radio sau celelalte categorii. Articolele din redacție nu expiră automat după 24 de ore.

## Interacțiune
Pentru materiale obișnuite destinate publicării, cererea utilizatorului de a publica sau de a „face restul” autorizează publicarea după redactare, fără a cere o a doua aprobare. Dacă materialul conține acuzații, informații private, afirmații incerte sau alte riscuri editoriale, cere clarificări înainte de publicare.

## Exemplu
Articolul INCA România despre pensii și drepturile lucrătorilor, publicat în `editorial.json`, cu imaginea `images/redactie-inca-romania-pensii.svg`.

## Rezumat pentru distribuirea pe Facebook
Pentru fiecare articol redactat original, scrie în `summary` un rezumat substanțial, de regulă 250–450 de cuvinte în 3–5 paragrafe, dacă materialul verificat permite. Include ce s-a întâmplat, unde și când, persoanele implicate, contextul și implicațiile confirmate. Păstrează limba originală. Nu inventa detalii și nu copia integral textul unei alte publicații. Dacă sursa oferă puține informații, păstrează un rezumat mai scurt și semnalează limita; nu umple textul cu repetiții.
Comanda «Copia post Facebook» copiază titlul, textul disponibil și linkul. Utilizatorul lipește textul în postarea Facebook și publică din Facebook.

## Regula pentru toate știrile noi — 23 octombrie 2026

Formatul cerut de utilizator se aplică tuturor știrilor noi redactate pentru RDI, indiferent de categorie:
- Textul complet din `body` urmărește aproximativ **400–600 de cuvinte**, în paragrafe clare.
- Include faptele verificate, contextul relevant, consecințele confirmate și sursele consultate. Separă explicit analiza redacției de informațiile relatate de surse.
- Dacă prima sursă oferă doar un titlu sau două rânduri, caută informații suplimentare și surse independente înainte de redactare.
- Când informațiile verificabile sunt insuficiente, păstrează un text mai scurt. Nu inventa fapte, citate sau consecințe și nu adăuga repetiții pentru atingerea lungimii.
- Respectă drepturile surselor; redactează original și nu reproduce integral articolele altor publicații.
- Pentru o știre importată din RSS, salvează aprofundarea verificată în `data/news-summaries.json`, cu `body`, `language`, `source_urls`, `reviewed_at` și `published`, folosind URL-ul știrii ca identificator. Acest fișier este utilizat de cititorul aplicației, importator și traduceri.
- Verifică înainte de a raporta publicarea că textul complet este disponibil în aplicație și că o traducere veche nu înlocuiește noul text.

### Starea automatizării

La 23 octombrie 2026 a fost actualizată și reactivată automatizarea ChatGPT **Articoli RDI completi** (ID `6ad3b7b892fc8191ae1a051c6216cbd8`), cu recurența existentă de o oră. Promptul ei cere cercetare, redactare și publicare efectivă în `data/news-summaries.json` pentru știrile importate din toate categoriile, cu obiectiv de 400–600 de cuvinte și coadă `pending` pentru subiectele rămase. Păstrează și sarcina de știri originale din diaspora, evitând duplicatele. A fost solicitată o primă executare imediată; solicitarea nu dovedește finalizarea.

Scripturile RSS continuă să importe știri la frecvența lor existentă și să atașeze aprofundările deja salvate. Redactarea se execută separat prin automatizarea ChatGPT, nu în fiecare execuție RSS. O știre poate apărea inițial ca rezumat până la prelucrare. Frecvența maximă disponibilă pentru această automatizare este o oră; nu promite extindere la fiecare zece minute, finalizare instantanee ori acoperirea întregului flux într-o singură executare. Verifică rezultatele și restanțele înainte să declari toate știrile completate.

Nu este necesară o nouă cheie API pentru această cale. Dacă automatizarea este oprită sau eșuează, raportează situația; nu prezenta simpla existență a regulii în acest document ca dovadă de funcționare.


## Redacție: panou, arhivă și statistici – 25 octombrie 2026

- redactie.html este un **panou public de monitorizare** (nu un CMS securizat). Afișează din data/editorial-status.json numărul știrilor, textele de peste 400 de cuvinte, intrările fără corp, traducerile și coada pending. Actualizarea sa este produsă de scripts/build_editorial_status.py în workflow-ul news.yml; nu declara „în timp real” datele până la următoarea rulare.
- Modificarea și aprobarea materialelor se fac prin contul GitHub autorizat, folosind legăturile din panou. Nu expune tokenuri, chei API sau documente private în browser.
- scripts/archive_editorial.py salvează în data/editorial-archive.json articolele din editorial.json **înainte și după** curățarea feedului de 48 de ore. Cititorii le pot căuta în arhiva.html. Arhiva nu schimbă datele originale și nu reintroduce articolele în lista de actualitate.
- Articolele inexacte trebuie corectate în sursă și în arhivă; în cazul unei retrageri editoriale trebuie revizuit explicit conținutul arhivat. Persistența unei arhive nu prevalează asupra obligațiilor de corectare și confidențialitate.
- romani-italia.html și widgetul homepage folosesc data/romanians-italy.json. La 1 ianuarie 2025, cifra verificată este **1.053.042 cetățeni cu cetățenie română rezidenți în Italia**, sursa statistică ISTAT (https://demo.istat.it/app/?i=RCS&l=it). Sunt excluși cetățenii italieni de origine română; cifra **nu este măsurată în timp real**. Dacă apar date noi, modifică numai după verificarea unei surse oficiale datate și a concordanței sumelor regionale.
- YouTube afișează această statistică doar cu data explicită și mențiunea „nu în timp real”. Nu extrapola zilnic și nu anima artificial cifra.
- Teste dedicate: node --test tests/editorial-system.test.mjs și workflow-ul editorial-check.yml; fluxurile principale de știri și redacție trebuie verificate separat în GitHub Actions.
