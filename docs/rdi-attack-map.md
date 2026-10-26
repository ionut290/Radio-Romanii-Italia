# RDI – Harta mondială a atacurilor

## Public
- [Harta publică](https://radioromanii.duckdns.org/harta-atacurilor.html) – filtre după zi/interval, țară, tip; hartă cu puncte aproximative și listă accesibilă.
- Date publice: [data/attack-monitor.json](../data/attack-monitor.json). Fiecare eveniment include surse jurnalistice, bilanțuri *raportate* și dată a faptelor. Nu reprezintă toate incidentele din lume.
- Marcajele nu indică coordonate exacte; nu se publică detalii tactice, identitatea minorilor sau a victimelor.
- Nu se clasifică violența în funcție de religia persoanei. Motivul, dacă este cunoscut, se atribuie exclusiv surselor.

## Semnalări zilnice
Workflow [RDI - Monitorizare incidente](../.github/workflows/incident-leads.yml) rulează o dată pe zi (07:17 UTC) și citește **doar primul tabel** din pagina publică CSPII. Scrie maximum 200 de piste în [data/attack-candidates.json](../data/attack-candidates.json). Dacă sursa nu poate fi citită, eșuează fără a șterge datele existente.

**Nicio semnalare nu ajunge automat pe hartă sau în știri.** Site-ul CSPII este o sursă cu o selecție editorială proprie, nu un registru neutru/definitiv; include și tentative, simple planuri și date care necesită rectificări.

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

