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

Această regulă este o instrucțiune editorială, nu un generator de texte. Scripturile RSS actuale preiau rezumatele furnizorilor și atașează aprofundările deja cercetate și salvate. Ele nu cercetează și nu redactează automat articole originale de 400–600 de cuvinte pentru fiecare știre nouă. Nu raporta această funcție ca activă până când nu este implementată și verificată efectiv.
