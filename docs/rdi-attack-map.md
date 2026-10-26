# RDI – Harta mondială a atacurilor

## Public
- [Harta publică](https://radioromanii.duckdns.org/harta-atacurilor.html) – filtre după zi/interval, țară, tip; hartă cu puncte aproximative și listă accesibilă.
- Date publice: [data/attack-monitor.json](../data/attack-monitor.json). Fiecare eveniment include surse jurnalistice, bilanțuri *raportate* și dată a faptelor. Nu reprezintă toate incidentele din lume.
- Marcajele nu indică coordonate exacte; nu se publică detalii tactice, identitatea minorilor sau a victimelor.
- Nu se clasifică violența în funcție de religia persoanei. Motivul, dacă este cunoscut, se atribuie exclusiv surselor.

## Semnalări zilnice din surse multiple
Workflow [RDI - Monitorizare incidente](../.github/workflows/incident-leads.yml) rulează zilnic la 07:17 UTC și la schimbări ale scriptului. **Nu publică automat atacuri**: actualizează numai coada de documentare [data/attack-candidates.json](../data/attack-candidates.json), cu un maximum de 240 de piste și istoric recent limitat.

Surse active de *descoperire*:
- **CSPII / TheReligionOfPeace** – primul tabel public al incidentelor declarate. Sursa are propria selecție și poate include evenimente viitoare, planuri, acuzații sau date inexacte. Verificare independentă obligatorie.
- **Google News RSS** – căutări în engleză, italiană, spaniolă și franceză pentru atentate și atacuri armate. Agregatorul nu este o confirmare. Linkurile către edițiile originale necesită verificare.
- **GDELT DOC 2.0** – index de articole despre atacuri, atentate și tentative, cu căutări limitate la ultimele 48 de ore. https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Câmpul `date` din rezultatele Google News reprezintă **data publicării**, iar din GDELT **data observării articolului**, nu data atacului! `date_kind` marchează această diferență, iar `event_date_confirmed: false` indică necesitatea verificării. Doar editorul documentează și stabilește data exactă a evenimentului. Nu inferea coordonate sau bilanțuri din agregatoare.

Fluxurile sunt accesate cu cereri reduse și timeout. Dacă unul e indisponibil, se păstrează pistele anterioare; dacă toate eșuează, scriptul nu suprascrie fișierul existent. `source_status` permite redacției să vadă ce a funcționat în ultima execuție. Atribuirile, evaluările și sursele independente adăugate de editor sunt păstrate după reluare.

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

