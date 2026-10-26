# RDI – Harta mondială a atacurilor

## Public
- [Harta publică](https://radioromanii.duckdns.org/harta-atacurilor.html) – filtre după zi/interval, țară, tip; hartă cu puncte aproximative și listă accesibilă.
- Date publice: [data/attack-monitor.json](../data/attack-monitor.json). Fiecare eveniment include surse jurnalistice, bilanțuri *raportate* și dată a faptelor. Nu reprezintă toate incidentele din lume.
- Un incident poate fi distribuit separat cu `?incident=<id>&lang=ro|it`; pagina filtrează la acel caz, are comandă de revenire la lista completă, iar marcajul include legătura către articolul RDI dacă acesta există. Butonul „Distribuie incidentul” utilizează opțiunile native de partajare sau copiază linkul, în funcție de browser.
- Valorile necunoscute (`null`) la răniți/decedați sunt afișate cu „—”; ele nu trebuie transformate în zero în bilanțurile redacției.
- Marcajele nu indică coordonate exacte; nu se publică detalii tactice, identitatea minorilor sau a victimelor.
- Nu se clasifică violența în funcție de religia persoanei. Motivul, dacă este cunoscut, se atribuie exclusiv surselor.

## Semnalări zilnice din surse multiple
Workflow [RDI - Monitorizare incidente](../.github/workflows/incident-leads.yml) rulează zilnic la 07:17 UTC și la schimbări ale scriptului. **Nu publică automat atacuri**: actualizează numai coada de documentare [data/attack-candidates.json](../data/attack-candidates.json), cu un maximum de 240 de piste și istoric recent limitat.

Surse active de *descoperire*:
- **CSPII / TheReligionOfPeace** – primul tabel public al incidentelor declarate. Sursa are propria selecție și poate include evenimente viitoare, planuri, acuzații sau date inexacte. Verificare independentă obligatorie.
- **Google News RSS** – căutări în engleză, italiană, spaniolă și franceză pentru atentate și atacuri armate. Agregatorul nu este o confirmare. Linkurile către edițiile originale necesită verificare.
- **GDELT DOC 2.0** – index de articole despre atacuri, atentate și tentative, cu căutări limitate la ultimele 48 de ore. https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- **BBC World RSS** – titluri originale din știrile mondiale, prefiltrate prin termeni despre atacuri sau explozii. https://feeds.bbci.co.uk/news/world/rss.xml

Câmpul `date` din rezultatele Google News reprezintă **data publicării**, iar din GDELT **data observării articolului**, nu data atacului! `date_kind` marchează această diferență, iar `event_date_confirmed: false` indică necesitatea verificării. Doar editorul documentează și stabilește data exactă a evenimentului. Nu inferea coordonate sau bilanțuri din agregatoare.

GDELT este interogat o singură dată pe execuție, cu termeni grupați, pentru a limita răspunsurile de tip HTTP 429. În cazul limitării, `source_status.gdelt` raportează `rate_limited` și codul HTTP, fără încercări agresive de reinterogare. Fluxurile sunt accesate cu cereri reduse și timeout. Dacă GDELT este limitat sau returnează alt format decât JSON, sursa apare ca eroare în `source_status`; NU se consideră că a furnizat piste verificate. Dacă unul e indisponibil, se păstrează pistele anterioare; dacă toate eșuează, scriptul nu suprascrie fișierul existent. `source_status` permite redacției să vadă ce a funcționat în ultima execuție. Atribuirile, evaluările și sursele independente adăugate de editor sunt păstrate după reluare.

Date de referință suplimentare, **nu integrate fără acces/autorizare și verificare**:
- **UCDP Candidate / GED** – date codificate științific despre conflicte violente, inclusiv seturi lunare, nu neapărat flux live: https://ucdp.uu.se/downloads/
- **ACLED** – date despre conflicte, necesită cont myACLED și respectarea condițiilor de acces: https://acleddata.com/api-documentation/getting-started
- **ReliefWeb** – rapoarte umanitare, API cere `appname` aprobat: https://apidoc.reliefweb.int/

**Nicio semnalare nu ajunge automat pe hartă sau în știri.** A nu se confunda numărul de articole cu numărul de atacuri: aceeași întâmplare poate apărea de zeci de ori, iar relatările despre un complot împiedicat nu sunt atacuri realizate.

## Publicarea verificată – procedura editorului
1. Deschide fișierul de semnalări și compară faptele cu minimum o sursă de încredere independentă (ideal două: Reuters/AP, autorități, presă locală credibilă). Nu considera republicări ale aceluiași comunicat ca dovezi independente.
2. Distinge explicit *atac realizat*, *tentativă împiedicată*, *amenințare*, *suspect* și *anchetă*. Evită etichetarea motivelor nesusținute de probe. Separă decesul agresorilor de victime.
3. Introdu un obiect nou în `data/attack-monitor.json` doar cu `id` stabil, `date` ISO al faptelor, `country`, `country_code`, `place`, `lat` și `long` aproximative, `precision`, `type` ("attack"/"foiled"), `status` ("reported"), `killed` și `injured` (număr sau `null` pentru necunoscut), `title_ro`, `title_it`, `description_ro`, `description_it`, `sources` (nume + URL).
4. Pentru o știre completă, scrie un articol original de 400–600 cuvinte, cu surse, în `editorial.json` cu categoria `Știri din redacție`. Leagă `rdi_article_id` din eveniment de `id` articol. Nu copia texte ale altor redacții.
5. Verifică afișarea publică, linkul către articol, harta și corectitudinea bilanțului. Dacă un bilanț se modifică, actualizează atât harta, cât și articolul și arhiva.
6. Nu include numărul total de evenimente din CSPII drept statistici RDI. Numerele din hartă sunt **doar selecția editată vizibilă**, supusă filtrelor.

### Surse de verificare
- https://www.cspii.org/attacks – sursă de semnalări
- https://acleddata.com/conflict-data – date despre conflicte, supuse licenței și condițiilor de acces
- https://www.start.umd.edu/research-projects/global-terrorism-database-gtd – metodologie istorică


## Ediția zilei și știrile din zone de conflict

- Pagina publică **afișează implicit numai evenimentele din ziua calendaristică curentă în fusul Europe/Rome**, nu toate atacurile din ultimele zile. Dacă astăzi nu există incidente documentate, se afișează un mesaj explicit, fără a recicla atacurile de ieri ca fiind de azi.
- Butoanele 7/30/90 zile/Toate rămân disponibile pentru arhivă; un link cu `?incident=<id>` deschide evenimentul istoric chiar dacă data lui nu este azi.
- **Separat de incidente**, fișierul `data/war-zone-news.json` alimentează rubrica „Astăzi în zonele de conflict” și marcajele albastre. `published_date` reprezintă data publicării sau actualizării știrii în calendarul Europe/Rome, iar `event_date` (poate fi `null`) reprezintă data faptelor, doar dacă este confirmată. O relatare actualizată azi poate vorbi despre evenimente trecute; titlul și rezumatul trebuie să explice acest lucru.
- Redacția care revizuiește zilnic această hartă trebuie să consulte, **o dată pe zi**, surse credibile și să actualizeze `data/war-zone-news.json` cu maximum 3–8 știri noi, precise, despre evoluții militare documentate, victime civile, coridoare umanitare, negocieri sau avertismente instituționale în zone de război, din mai multe regiuni dacă există material relevant.
- Pentru fiecare înregistrare: `id` stabil, `published_date`, `event_date` (sau null), `region`, `place`, `lat`/`long` aproximative pentru o **localitate deja publică** (sau omiterea coordonatelor), `precision`, `title_ro`, `title_it`, `summary_ro`, `summary_it`, `source_name`, `source_url`. Nu se folosesc coordonate ale obiectivelor militare, informații tactice, imagini fără drepturi sau detalii despre victime identificabile.
- Verifică articolul și data lui pe site-ul sursei (Reuters/AP, ONU, instituții umanitare, publicații credibile); dacă afirmația este contestată sau provine dintr-o singură parte beligerantă, atribuie-o explicit și explică limitele. Nu inventa statistici, nu schimba data sau prezenta afirmații contestate drept dovezi; evită duplicatele din aceeași zi.
- Înainte de fiecare scriere recitește versiunea GitHub și SHA, unește modificările concurente și păstrează istoricul cel puțin pe termen scurt (maxim 30 zile dacă este nevoie de limitare). Rubrica afișează numai știri cu `published_date` de **astăzi**. Dacă nu există știri verificate, afișează în mod sincer că lista este goală; nu înlocui automat cu ieri și nu include pista neconfirmată din `attack-candidates.json`.
- Marcajele albastre nu cresc nici numărul de „atacuri”, nici statisticile morților sau răniților din incidente. Harta roșie/aurie este pentru incidente cu dată a faptelor documentată; secțiunea albastră este pentru **actualizări de presă publicate azi**, nu pentru statistici de evenimente.
