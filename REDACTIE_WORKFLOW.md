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
