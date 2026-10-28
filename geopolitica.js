"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const dict = {
    ro: {
      brandDesk:"DIN ITALIA / REDACȚIA GLOBALĂ",briefing:"RDI / SINTEZĂ INTERNAȚIONALĂ",mainTitle:"GEOPOLITICĂ",worldMonitoring:"MONITORIZARE GLOBALĂ",worldArea:"RDI · EUROPA / LUME",
      tickerDesk:"RDI · REDACȚIA GLOBALĂ",tickerEurope:"EUROPA",tickerDiplomacy:"DIPLOMAȚIE",tickerSecurity:"SECURITATE",tickerEconomy:"ECONOMIE",tickerEnergy:"ENERGIE",tickerClimate:"CLIMĂ",tickerTech:"TEHNOLOGIE",
      atlasLabel:"RDI / OBSERVATOR MONDIAL",footerDesk:"© RADIO ROMÂNII DIN ITALIA · REDACȚIA GLOBALĂ",
      topicsAria:"Domenii urmărite",navigationAria:"Navigare",languageAria:"Limbă",filtersAria:"Filtre tematice",searchAria:"Caută știri",
      radio:"Radio",news:"Actualitate",atlas:"Observator",archive:"Arhivă",
      subtitle:"Dincolo de titluri. O privire asupra conflictelor, diplomației, puterii economice și deciziilor care schimbă lumea.",
      discover:"Descoperă actualitatea ↗",exploremap:"Explorează harta ↘",
      heroNote:"Surse citate · Date vizibile · Fapte separate de analiză",
      topicsEyebrow:"01 / DOMENII DE INTERES",topicsTitle:"Lumea, explicată pe teme",topicsDescription:"Selectează un domeniu pentru a filtra știrile.",
      all:"Toate temele",allDesc:"Panorama globală",diplomacy:"Diplomație",diplomacyDesc:"Negocieri și alianțe",
      conflicts:"Conflicte & pace",conflictsDesc:"Crize și situații umanitare",europe:"UE & Europa",europeDesc:"Politici și instituții",
      economy:"Economie mondială",economyDesc:"Comerț și finanțe",energy:"Energie & resurse",energyDesc:"Petrol, gaze, tranziție",
      security:"Securitate",securityDesc:"NATO și apărare",technology:"Tehnologie",technologyDesc:"AI, spațiu, competiție",
      climate:"Climă & mediu",climateDesc:"Riscuri și acorduri",
      newsEyebrow:"02 / FLUXUL INTERNAȚIONAL",storiesTitle:"Ce se întâmplă în lume",
      loading:"Se încarcă sursele…",region:"Regiune",allRegions:"Toate regiunile",reset:"Resetează filtrele",
      sourceNote:"Titlurile sunt traduse automat în română. Sursele și datele sunt indicate; RDI nu le verifică independent pe toate.",
      noResults:"Nicio știre pentru selecția actuală",tryFilters:"Încearcă alt domeniu, o altă regiune sau revino mai târziu.",
      externalDisclaimer:"Traducerile automate pot conține erori. Titlurile aparțin publicațiilor citate, nu reprezintă confirmări RDI.",
      archiveOpen:"Arhiva RDI ↗",
      atlasEyebrow:"03 / DATE ȘI CONTEXT",atlasTitle:"Observatorul conflictelor",
      atlasDescription:"Harta interactivă cu incidente documentate, știri din zone de conflict, filtre de perioadă și surse. Nu amestecăm știrile cu bilanțurile incidentelor confirmate.",
      openAtlas:"Deschide harta interactivă ↗",atlasCaution:"Poziții aproximative · Date revizuibile · Fără informații tactice",
      analysisEyebrow:"04 / CONTEXT & ANALIZĂ",analysisTitle:"Chei pentru a înțelege lumea",
      a1:"Ce este geopolitica?",a1text:"Analiza modului în care geografia, resursele, economia, istoria și relațiile de putere influențează deciziile statelor.",
      a1link:"Organizația Națiunilor Unite ↗",a2:"Diplomație și organizații",
      a2text:"Cum funcționează ONU, Uniunea Europeană și NATO, ce decid și unde se află limitele competențelor lor.",
      a2link:"Instituțiile UE ↗",a3:"De ce contează energia?",
      a3text:"Importurile, infrastructura, materiile prime și tranziția energetică pot influența securitatea și prețurile în mai multe țări.",
      a3link:"Agenția Internațională a Energiei ↗",
      ethicsEyebrow:"TRANSPARENȚĂ EDITORIALĂ",ethicsTitle:"Informația cere context.",
      ethicsText:"Fluxul automat colectează titluri și fragmente atribuite publicațiilor. Acestea sunt semnalări jurnalistice, nu fapte verificate independent de RDI. Materialele proprii sunt distincte; o analiză sau o opinie trebuie etichetată ca atare. Data publicării unei știri nu este neapărat data unui eveniment.",
      editorialPolicy:"Despre redacție ↗",back:"Înapoi la radio ↑",read:"Citește sursa ↗",
      curated:"Observator RDI",external:"SURSĂ EXTERNĂ",published:"Publicat",updated:"Flux actualizat",
      fallback:"Fluxul extern tradus nu este încă disponibil. Sunt afișate doar materiale bilingve din observatorul RDI.",
      count:"știri",sourceUnavailable:"Nu există încă materiale pentru această selecție.",
      searchPlaceholder:"Caută un subiect sau o țară…"
    },
    it: {
      brandDesk:"DALL'ITALIA / REDAZIONE INTERNAZIONALE",briefing:"RDI / NOTIZIARIO INTERNAZIONALE",mainTitle:"GEOPOLITICA",worldMonitoring:"MONITORAGGIO GLOBALE",worldArea:"RDI · EUROPA / MONDO",
      tickerDesk:"RDI · REDAZIONE INTERNAZIONALE",tickerEurope:"EUROPA",tickerDiplomacy:"DIPLOMAZIA",tickerSecurity:"SICUREZZA",tickerEconomy:"ECONOMIA",tickerEnergy:"ENERGIA",tickerClimate:"CLIMA",tickerTech:"TECNOLOGIA",
      atlasLabel:"RDI / OSSERVATORIO MONDIALE",footerDesk:"© RADIO ROMÂNII DIN ITALIA · REDAZIONE INTERNAZIONALE",
      topicsAria:"Temi seguiti",navigationAria:"Navigazione",languageAria:"Lingua",filtersAria:"Filtri per argomento",searchAria:"Cerca notizie",
      radio:"Radio",news:"Attualità",atlas:"Osservatorio",archive:"Archivio",
      subtitle:"Oltre i titoli. Uno sguardo a conflitti, diplomazia, potere economico e decisioni che cambiano il mondo.",
      discover:"Esplora le notizie ↗",exploremap:"Esplora la mappa ↘",
      heroNote:"Fonti indicate · Date visibili · Fatti distinti dall'analisi",
      topicsEyebrow:"01 / AREE TEMATICHE",topicsTitle:"Il mondo, per argomenti",topicsDescription:"Seleziona un tema per filtrare le notizie.",
      all:"Tutti i temi",allDesc:"Panorama mondiale",diplomacy:"Diplomazia",diplomacyDesc:"Negoziati e alleanze",
      conflicts:"Conflitti e pace",conflictsDesc:"Crisi ed emergenze umanitarie",europe:"UE ed Europa",europeDesc:"Politiche e istituzioni",
      economy:"Economia globale",economyDesc:"Commercio e finanza",energy:"Energia e risorse",energyDesc:"Petrolio, gas, transizione",
      security:"Sicurezza",securityDesc:"NATO e difesa",technology:"Tecnologia",technologyDesc:"IA, spazio, competizione",
      climate:"Clima e ambiente",climateDesc:"Rischi e accordi",
      newsEyebrow:"02 / NOTIZIE DAL MONDO",storiesTitle:"Cosa succede nel mondo",
      loading:"Caricamento delle fonti…",region:"Regione",allRegions:"Tutte le regioni",reset:"Reimposta filtri",
      sourceNote:"I titoli sono tradotti automaticamente in italiano. Sono indicati fonte e data; RDI non li verifica tutti in modo indipendente.",
      noResults:"Nessuna notizia per questa selezione",tryFilters:"Prova un altro tema, un'altra regione oppure torna più tardi.",
      externalDisclaimer:"Le traduzioni automatiche possono contenere errori. I titoli appartengono alle testate citate, non sono conferme RDI.",
      archiveOpen:"Archivio RDI ↗",
      atlasEyebrow:"03 / DATI E CONTESTO",atlasTitle:"Osservatorio dei conflitti",
      atlasDescription:"La mappa interattiva con episodi documentati, notizie dalle zone di conflitto, filtri temporali e fonti. Le notizie restano distinte dai bilanci degli attacchi confermati.",
      openAtlas:"Apri la mappa interattiva ↗",atlasCaution:"Posizioni approssimative · Dati aggiornabili · Nessun dettaglio tattico",
      analysisEyebrow:"04 / CONTESTO E ANALISI",analysisTitle:"Chiavi per capire il mondo",
      a1:"Cos'è la geopolitica?",a1text:"Studia come geografia, risorse, economia, storia e rapporti di potere influenzano le decisioni degli Stati.",
      a1link:"Organizzazione delle Nazioni Unite ↗",a2:"Diplomazia e organizzazioni",
      a2text:"Come funzionano ONU, Unione europea e NATO, cosa decidono e quali sono i limiti dei loro poteri.",
      a2link:"Istituzioni UE ↗",a3:"Perché conta l'energia?",
      a3text:"Importazioni, infrastrutture, materie prime e transizione energetica possono influenzare sicurezza e prezzi.",
      a3link:"Agenzia internazionale dell'energia ↗",
      ethicsEyebrow:"TRASPARENZA EDITORIALE",ethicsTitle:"Le notizie richiedono contesto.",
      ethicsText:"Il flusso automatico raccoglie titoli e brevi estratti attribuiti alle testate. Sono segnalazioni giornalistiche e non verifiche indipendenti di RDI. I contenuti originali sono separati; analisi e opinioni devono essere indicate come tali. La data dell'articolo non coincide necessariamente con quella dell'evento.",
      editorialPolicy:"La redazione ↗",back:"Torna alla radio ↑",read:"Leggi la fonte ↗",
      curated:"Osservatorio RDI",external:"FONTE ESTERNA",published:"Pubblicato",updated:"Flusso aggiornato",
      fallback:"Il flusso internazionale tradotto non è ancora disponibile. Mostriamo solo contenuti bilingui dell’osservatorio RDI.",
      count:"notizie",sourceUnavailable:"Nessun contenuto disponibile per questa selezione.",
      searchPlaceholder:"Cerca un argomento o un Paese…"
    }
  };
  const TOPIC_NAMES = {
    diplomatie:["diplomacy","diplomacy"],conflicte:["conflicts","conflicts"],europa:["europe","europe"],
    economie:["economy","economy"],energie:["energy","energy"],securitate:["security","security"],
    tehnologie:["technology","technology"],clima:["climate","climate"]
  };
  const REGIONS = ["all","europa","orient","asia","africa","americi","global"];
  const TOPICS = ["diplomatie","conflicte","europa","economie","energie","securitate","tehnologie","clima"];
  const state = {lang:"ro",topic:"all",region:"all",items:[],feedOk:false,updated:""};
  let cachedTranslations = {};
  try {if(localStorage.getItem("rdi-lang")==="it")state.lang="it"}catch(_){}
  function t(key){return dict[state.lang][key]||key}
  function validUrl(value){try {const u=new URL(String(value));return u.protocol==="https:"?u.href:null}catch(_){return null}}
  function dateISO(value){const d=new Date(value||"");return Number.isNaN(d.getTime())?null:d}
  function dateLabel(value){const d=dateISO(value);return d?new Intl.DateTimeFormat(state.lang==="it"?"it-IT":"ro-RO",{timeZone:"Europe/Rome",day:"numeric",month:"short",year:"numeric"}).format(d):""}
  function updateTimeLabel(value){const d=dateISO(value);return d?new Intl.DateTimeFormat(state.lang==="it"?"it-IT":"ro-RO",{timeZone:"Europe/Rome",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(d)+" (Roma)":""}
  function localToday(){return new Intl.DateTimeFormat(state.lang==="it"?"it-IT":"ro-RO",{timeZone:"Europe/Rome",day:"numeric",month:"long",year:"numeric"}).format(new Date())}
  function node(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n}
  function regionGuess(value){
    const s=String(value||"").toLowerCase();
    if(/ucrain|ukrain|russi|rusiei|rusia|moldov|polon|german|europ|italia|românia|romania|bruxell|brussels|serbia|balcan|balkan/.test(s))return "europa";
    if(/israel|gaza|palestin|iran|irak|iraq|siria|syria|liban|leban|yemen|saudi|qatar|turcia|türkiye/.test(s))return "orient";
    if(/china|chinese|japon|japan|taiwan|korea|coreea|india|indone|pakistan|bangladesh|filipin|thailand|asia|pacific/.test(s))return "asia";
    if(/sudan|nigeria|mali|afric|ethiopi|kenya|somalia|congo|sahel|libia|libya/.test(s))return "africa";
    if(/american|united states|statele unite|sua|washington|brazil|mexic|canad|venezuela|argentin/.test(s))return "americi";
    return "global";
  }
  function normalizeExternal(item){
    // Strictly show only a translated headline in the selected language.
    const title=state.lang==="it"?item?.title_it:item?.title_ro;
    if(!item||!validUrl(item.url)||!title||!TOPICS.includes(item.category)||!dateISO(item.published))return null;
    const published=dateISO(item.published);
    if(published.getTime()>Date.now()+3600000)return null;
    const summary=state.lang==="it"?item.summary_it:item.summary_ro;
    return {title:String(title).slice(0,260),summary:String(summary||"").slice(0,400),
      category:item.category,region:REGIONS.includes(item.region)?item.region:regionGuess(title),
      url:validUrl(item.url),source:String(item.source||"RDI").slice(0,100),
      published:item.published,type:"external"};
  }
  function normalizeWar(item){
    if(!item||!validUrl(item.source_url)||!item.title_ro||!item.title_it||!dateISO(item.published_date))return null;
    return {title:state.lang==="it"?item.title_it:item.title_ro,summary:state.lang==="it"?item.summary_it:item.summary_ro,
      category:"conflicte",region:regionGuess(String(item.region||"")+" "+String(item.place||"")),
      url:validUrl(item.source_url),source:String(item.source_name||"RDI").slice(0,100),
      published:item.published_date+"T12:00:00Z",type:"curated",id:item.id};
  }
  function isGeoEditorial(item){const s=String(item.title||"")+" "+String(item.category||"");return /geopolit|diploma[tț]|conflict|război|razboi|atac|sudan|ukrain|ucrain|gaza|israel|nato|mali|nigeria|energie|rusia|china|iran|onu|uniunea europe/i.test(s)}
  function normalizeEditorial(item){
    if(!item||!item.title||!validUrl(item.url)||!isGeoEditorial(item)||!dateISO(item.published))return null;
    const record=cachedTranslations[item.id]||cachedTranslations[item.url];
    const localized=record?.[state.lang];
    if(!record?.ro?.title||!record?.it?.title||!localized?.title)return null;
    const name=String(localized.title);
    const category=/energie|petrol|gaz|resurse|energia|gas|risorse/i.test(name)?"energie":/diploma|negoc|ambasad|onu|tratat|negoziat/i.test(name)?"diplomatie":/nato|securitate|apărare|sicurezza|difesa/i.test(name)?"securitate":/uniunea european|comisia european|bruxelles|unione europea|commissione europea/i.test(name)?"europa":"conflicte";
    return {title:name,summary:String(localized.summary||"").slice(0,400),category,region:regionGuess(name),
      url:validUrl(item.url),source:"RDI / "+String(item.source||"Redacție").slice(0,70),published:item.published,type:"curated"};
  }
  function cardData(){
    const chosen=state.items.filter(x=>(state.topic==="all"||x.category===state.topic)&&(state.region==="all"||x.region===state.region));
    const query=$("search").value.trim().toLocaleLowerCase();
    return chosen.filter(x=>!query||[x.title,x.summary,x.source].join(" ").toLocaleLowerCase().includes(query));
  }
  // Contextual essays deliberately distinguish a reported headline from independently verified events.
  const CONTEXT = {
    ro: {
      diplomatie:["Diplomația nu înseamnă doar întâlniri oficiale. Ea reunește negocieri, semnale politice, canale de comunicare și încercări de a reduce diferențele dintre guverne. Un titlu despre o declarație diplomatică trebuie citit în contextul relațiilor dintre state, al intereselor acestora și al acordurilor deja existente.","O poziție publică nu echivalează întotdeauna cu o decizie oficială. Pentru a înțelege evoluția unei negocieri sunt importante comunicatele instituțiilor implicate, documentele semnate și reacțiile celorlalte părți. Uneori, diferența dintre intenție și rezultat este esențială.","În plan internațional, efectele unei inițiative diplomatice pot depăși statele direct implicate. Comerțul, migrația, securitatea și organizațiile multilaterale se pot influența reciproc. Totuși, aceste consecințe trebuie analizate ca posibilități, nu prezentate ca rezultate certe.","Ce merită urmărit în continuare? Calendarul întâlnirilor, eventualele texte comune, măsurile concrete și confirmările independente. Acest context explică tema, nu certifică afirmația din titlul sursei."],
      conflicte:["Relatările din zone de conflict necesită o atenție deosebită. Informațiile se pot schimba rapid, iar accesul jurnaliștilor și al observatorilor independenți poate fi limitat. De aceea, un titlu despre un incident nu este suficient pentru a stabili singur amploarea, autorii sau consecințele evenimentului.","O analiză responsabilă separă afirmațiile făcute de părțile implicate de informațiile confirmate de surse independente. Datele despre victime, deplasări forțate, infrastructură afectată și negocieri trebuie însoțite de data și proveniența lor, deoarece bilanțurile pot fi revizuite.","Dincolo de dimensiunea militară există și efecte umanitare, diplomatice și economice. Siguranța civililor, accesul la servicii și coridoarele umanitare reprezintă teme distincte, care nu pot fi reduse la o singură declarație sau la un titlu spectaculos.","Pentru evoluții noi trebuie urmărite rapoartele organizațiilor umanitare, declarațiile oficiale și verificările mai multor redacții. Aceste explicații sunt context general, nu o reconstrucție verificată a evenimentului semnalat."],
      europa:["Deciziile europene se formează prin proceduri care implică instituții cu atribuții diferite. O propunere, o dezbatere, un acord politic și o normă deja intrată în vigoare nu sunt același lucru. Diferența este importantă pentru interpretarea corectă a știrilor despre Uniunea Europeană.","Comisia Europeană, Parlamentul European și Consiliul Uniunii Europene participă, în moduri distincte, la elaborarea politicilor. În anumite domenii intervin și guvernele naționale. Cititorii trebuie să verifice exact cine a vorbit și ce competență are instituția citată.","Impactul unei măsuri depinde de textul definitiv, termenele de aplicare și modul în care statele o pun în practică. Efectele asupra economiei, mobilității și securității pot varia considerabil de la un sector la altul.","Documentele instituționale și calendarele legislative sunt esențiale pentru a urmări ce se schimbă cu adevărat. Contextul de față nu trebuie confundat cu o confirmare independentă a titlului extern."],
      economie:["Economia mondială este conectată prin comerț, investiții, cursuri valutare și lanțuri de aprovizionare. O schimbare politică sau financiară poate avea consecințe diferite pentru gospodării, firme și state, iar legăturile cauzale nu pot fi stabilite numai dintr-un titlu.","Indicatorii economici trebuie interpretați ținând cont de perioada analizată, metodologia de calcul și sursa datelor. Prognozele descriu scenarii, nu certitudini. De asemenea, un anunț al unei bănci centrale nu înseamnă automat o schimbare imediată a prețurilor.","În evaluarea efectelor contează rata inflației, ocuparea forței de muncă, producția și condițiile de creditare. Datele naționale pot ascunde diferențe între regiuni și categorii sociale, ceea ce impune prudență în concluzii.","Pentru a înțelege evoluția semnalată trebuie comparate surse statistice și comunicate oficiale. Acest material oferă instrumente de lectură, nu rezultate economice confirmate pentru cazul particular."],
      energie:["Energia se află la intersecția economiei, infrastructurii și securității. Prețurile și disponibilitatea resurselor depind de producție, transport, cerere, stocuri și condiții geopolitice. Niciunul dintre acești factori nu explică singur fiecare variație de piață.","Știrile despre petrol, gaze sau electricitate trebuie diferențiate după tipul informației: estimări, contracte, decizii politice ori modificări efective de ofertă. Rutele de transport și capacitățile de stocare pot influența flexibilitatea sistemelor energetice.","Tranziția energetică adaugă alte dimensiuni, precum investițiile, rețelele electrice, materiile prime și accesibilitatea pentru consumatori. Efectele diferă între țări, iar o schimbare locală nu trebuie generalizată automat la întreaga piață.","Datele operatorilor, agențiilor energetice și instituțiilor de reglementare sunt utile pentru verificări. Acesta este un context explicativ, nu o prognoză sau o confirmare a evenimentului relatat în sursă."],
      securitate:["Securitatea internațională cuprinde apărare, diplomație, alianțe, securitate cibernetică și protecția populației. Declarațiile despre pregătire sau risc nu indică automat că un anumit eveniment va avea loc.","Este important să se distingă între evaluări strategice, exerciții, intenții declarate și măsuri implementate. Documentele oficiale pot conține informații parțiale, iar interpretările experților pot diferi fără ca diferențele să reprezinte fapte confirmate.","Alianțele și parteneriatele au reguli și obligații specifice. O evoluție regională poate atrage atenția mai multor state, însă reacțiile lor depind de circumstanțe și de deciziile politice luate ulterior.","Monitorizarea prudentă presupune compararea comunicatelor, a datelor verificabile și a analizelor independente. Textul explică modul de interpretare a temei, nu validează afirmațiile din titlul citat."],
      tehnologie:["Tehnologia a devenit un domeniu central al competiției economice și strategice. Inteligența artificială, semiconductorii, infrastructura digitală și cercetarea au implicații care depășesc sectorul industrial.","O promisiune de investiții, un prototip și un produs disponibil la scară largă sunt etape diferite. La fel, anunțurile despre restricții comerciale trebuie urmărite până la adoptarea și aplicarea măsurilor concrete.","Consecințele pentru utilizatori și companii depind de costuri, standarde, competențe și reglementări. Unele evoluții ridică și întrebări despre protecția datelor, siguranță și acces echitabil.","Pentru verificare sunt necesare documente tehnice, date publice și surse independente. Acesta este context editorial general, fără pretenția de a confirma știrea originală."],
      clima:["Diplomația climatică încearcă să coordoneze răspunsuri la riscuri care depășesc granițele. Negocierile pot privi reducerea emisiilor, adaptarea, finanțarea și protejarea comunităților vulnerabile.","Un angajament politic nu înseamnă automat că măsurile au fost puse în practică. Contează țintele exacte, calendarul, finanțarea și rapoartele prin care progresele sunt măsurate.","Analiza impactului climatic trebuie diferențiată de atribuirea unui eveniment meteorologic individual. Cercetarea folosește serii de observații și metode specifice pentru a evalua tendințele și riscurile.","Pentru evaluări solide sunt utile rapoartele științifice și documentele oficiale. Aceste paragrafe oferă explicații generale, nu afirmă că știrea citată a fost verificată independent."]
    },
    it: {
      diplomatie:["La diplomazia comprende negoziati, comunicazioni ufficiali, relazioni tra governi e tentativi di trovare punti di convergenza. Un titolo su un colloquio o una dichiarazione va letto nel contesto degli interessi dei Paesi coinvolti e degli accordi preesistenti.","È essenziale distinguere un'intenzione politica da una decisione già formalizzata. Per capire se una trattativa ha prodotto risultati concreti occorre consultare comunicati istituzionali, documenti sottoscritti e reazioni delle parti interessate.","Le iniziative diplomatiche possono avere ricadute su commercio, migrazioni, sicurezza e cooperazione internazionale. Tuttavia, gli scenari possibili non devono essere presentati come conseguenze già accertate.","Per seguire gli sviluppi sono utili i calendari degli incontri, gli eventuali testi congiunti e i riscontri indipendenti. Questo approfondimento fornisce contesto generale, non conferma autonomamente il titolo della fonte."],
      conflicte:["Raccontare un conflitto richiede particolare prudenza. Le informazioni possono cambiare rapidamente e l'accesso alle zone interessate è spesso difficile. Un titolo, da solo, non consente di stabilire dimensioni, responsabilità o conseguenze di un episodio.","Occorre distinguere le dichiarazioni delle parti coinvolte da ciò che è stato verificato in modo indipendente. I dati su vittime, sfollamenti, infrastrutture e aiuti umanitari devono riportare una provenienza e una data, perché possono essere aggiornati.","Accanto agli aspetti militari esistono conseguenze umanitarie, diplomatiche ed economiche. La protezione dei civili e l'accesso ai servizi fondamentali richiedono un'attenzione specifica e non possono essere ridotti a un singolo annuncio.","Per capire gli sviluppi bisogna confrontare più fonti, comprese le organizzazioni umanitarie e le verifiche giornalistiche. Questo è un quadro contestuale, non una ricostruzione indipendentemente verificata dell'evento citato."],
      europa:["Le decisioni dell'Unione europea seguono procedure che coinvolgono istituzioni con competenze diverse. Una proposta, un accordo politico e una norma entrata in vigore non sono equivalenti: questa distinzione è decisiva per interpretare le notizie europee.","Commissione europea, Parlamento europeo e Consiglio dell'Unione europea intervengono in ruoli differenti. Per capire una notizia occorre individuare quale istituzione abbia agito, con quale potere e in quale fase del procedimento.","Gli effetti di una misura dipendono dal testo definitivo, dalle scadenze e dalle modalità di attuazione. L'impatto su imprese, cittadini e amministrazioni può variare fra Stati e settori.","Documenti istituzionali e calendari legislativi aiutano a verificare cosa sia effettivamente cambiato. Questo testo spiega il contesto, senza certificare autonomamente le affermazioni contenute nel titolo."],
      economie:["L'economia mondiale è collegata attraverso commercio, investimenti, valute e catene di approvvigionamento. Una notizia economica può avere implicazioni diverse per famiglie, imprese e governi, ma i rapporti di causa ed effetto non si deducono da un titolo.","Inflazione, occupazione, produzione e condizioni del credito vanno valutate con dati aggiornati e metodologie riconoscibili. Le previsioni economiche descrivono scenari soggetti a incertezza, non esiti garantiti.","Gli effetti possono essere differenti fra Paesi, regioni e categorie sociali. Anche una decisione di politica monetaria non determina automaticamente variazioni immediate dei prezzi al consumo.","Per comprendere la questione occorre confrontare statistiche, comunicati ufficiali e analisi indipendenti. Questo approfondimento propone chiavi di lettura, senza attribuire alla notizia risultati non verificati."],
      energie:["L'energia mette in relazione risorse naturali, infrastrutture, domanda e sicurezza economica. Prezzi e disponibilità dipendono da molti fattori: produzione, trasporti, stoccaggi, politiche pubbliche e condizioni internazionali.","Una previsione, una dichiarazione politica e una modifica effettiva dell'offerta sono fatti di natura diversa. Anche l'impatto sui consumatori dipende dal funzionamento dei mercati e dalle regole nazionali.","La transizione energetica comporta investimenti nelle reti, nuove tecnologie e attenzione alle materie prime. I suoi effetti non sono identici in ogni Paese e richiedono dati comparabili.","Le informazioni degli operatori e delle agenzie energetiche possono aiutare a verificare le tendenze. Questo testo offre contesto, non una previsione né una conferma indipendente della notizia."],
      securitate:["La sicurezza internazionale comprende difesa, diplomazia, alleanze, sicurezza digitale e protezione civile. Parlare di rischi o preparativi non significa necessariamente prevedere che un determinato evento accadrà.","È utile distinguere valutazioni strategiche, esercitazioni, dichiarazioni d'intenti e misure operative già attuate. Le interpretazioni degli analisti possono essere differenti e vanno separate dalle informazioni accertate.","Alleanze e partenariati sono disciplinati da impegni specifici. Le reazioni degli Stati dipendono dal contesto e dalle successive decisioni politiche, senza automatismi che possano essere dedotti da un titolo.","Per seguire l'argomento è opportuno confrontare fonti ufficiali e verifiche indipendenti. Questo approfondimento illustra il contesto strategico ma non certifica quanto riportato dalla testata."],
      tehnologie:["La tecnologia è oggi un elemento della competizione economica e strategica. Intelligenza artificiale, semiconduttori e infrastrutture digitali influenzano industria, ricerca e rapporti internazionali.","Un progetto annunciato, un prototipo e una tecnologia adottata su vasta scala sono fasi distinte. Analogamente, una proposta di restrizioni commerciali non coincide con norme già operative.","Costi, disponibilità delle competenze, standard e regolamentazione influiscono sull'adozione delle innovazioni. La protezione dei dati e la sicurezza costituiscono ulteriori dimensioni da considerare.","Documenti tecnici e informazioni provenienti da fonti indipendenti sono indispensabili per una verifica puntuale. Qui si offre un quadro esplicativo, non la conferma dell'evento segnalato."],
      clima:["La diplomazia climatica affronta problemi che superano i confini nazionali. Gli accordi possono riguardare la riduzione delle emissioni, l'adattamento, il finanziamento e la tutela delle comunità esposte ai rischi.","Un impegno annunciato non garantisce che le misure siano state attuate. Occorre esaminare obiettivi, scadenze, risorse disponibili e meccanismi di rendicontazione.","Anche l'analisi dei fenomeni climatici richiede di distinguere le tendenze di lungo periodo dai singoli eventi meteorologici. La ricerca scientifica utilizza osservazioni e metodi specifici per attribuire cause e valutare rischi.","Rapporti scientifici e documenti ufficiali aiutano a verificare le dichiarazioni. Queste informazioni forniscono contesto generale e non costituiscono una verifica indipendente della notizia citata."]
    }
  };
  function showContext(item){
    const dialog=$("article-dialog");if(!dialog)return;
    const paragraphs=CONTEXT[state.lang][item.category]||CONTEXT[state.lang].diplomatie;
    $("article-category").textContent=t(TOPIC_NAMES[item.category]?.[0]||"all")+" · RDI";
    $("article-title").textContent=item.title;
    $("article-disclaimer").textContent=state.lang==="it"
      ?"Approfondimento contestuale RDI. Il titolo è tratto da una fonte esterna e non è stato verificato indipendentemente. Il testo seguente spiega il contesto generale: non descrive come accertati i dettagli dell'episodio."
      :"Context explicativ RDI. Titlul provine dintr-o sursă externă și nu a fost verificat independent. Textul următor explică tema în general, fără a prezenta drept certe detaliile evenimentului.";
    $("article-body").replaceChildren(coverElement(item,true),...paragraphs.map(p=>node("p","",p)));
    $("article-attribution").textContent=item.source+" · "+dateLabel(item.published);
    $("article-original").href=item.url;
    $("article-original").textContent=t("read");
    if(!dialog.open)dialog.showModal();
  }
  $("article-close")?.addEventListener("click",()=>$("article-dialog").close());
  $("article-dialog")?.addEventListener("click",e=>{if(e.target===$("article-dialog"))e.target.close()});
  // Original, deterministic editorial SVG illustrations: never presented as event photographs.
  const COVER_PALETTES={
    diplomatie:["#102743","#257d9b","#b0e7ec"],conflicte:["#271e3b","#b85556","#ffc9a2"],
    europa:["#15284f","#366fbe","#e7c77e"],economie:["#122f39","#219785","#b8ead2"],
    energie:["#312340","#ce8053","#f1d0a1"],securitate:["#17253a","#4779a2","#9dc7ec"],
    tehnologie:["#14213f","#855cbd","#c6b6ff"],clima:["#173b39","#4eac84","#bbebbb"]
  };
  function storyIllustration(item){
    const colors=COVER_PALETTES[item.category]||COVER_PALETTES.diplomatie;
    const key=String(item.url||item.title||"RDI");
    let seed=0;for(let i=0;i<key.length;i++)seed=(Math.imul(seed,31)+key.charCodeAt(i))>>>0;
    const x=145+(seed%420),y=100+((seed>>>7)%140);
    const themeIcon={
      diplomatie:'<path d="M350 128l-72 45v90l72 45 72-45v-90z M278 173h144 M278 263h144 M350 128v180"/>',
      conflicte:'<path d="M350 134l-100 48v66q0 77 100 131 100-54 100-131v-66z M300 248h100 M350 197v104"/>',
      europa:'<circle cx="350" cy="230" r="103"/><path d="M247 230h206 M350 127v206 M274 163q76 67 152 134 M426 163q-76 67-152 134"/>',
      economie:'<path d="M240 315h230 M275 315v-85h48v85 M341 315V178h48v137 M407 315V132h48v183"/>',
      energie:'<path d="M386 120l-109 140h83l-32 122 112-156h-87z"/>',
      securitate:'<path d="M350 120l117 92-45 143H278l-45-143z M350 120v235 M233 212h234"/>',
      tehnologie:'<rect x="280" y="157" width="140" height="140" rx="18"/><path d="M308 157v-35 M350 157v-35 M392 157v-35 M308 297v35 M350 297v35 M392 297v35 M280 185h-38 M280 227h-38 M280 269h-38 M420 185h38 M420 227h38 M420 269h38"/><circle cx="350" cy="227" r="40"/>',
      clima:'<path d="M266 318q135-24 168-178-152 0-168 178z M266 318q70-100 130-145"/>'
    };
    const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 420" role="img">'+
      '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="'+colors[0]+'"/><stop offset="1" stop-color="'+colors[1]+'"/></linearGradient>'+
      '<radialGradient id="halo"><stop stop-color="'+colors[2]+'" stop-opacity=".43"/><stop offset="1" stop-color="'+colors[2]+'" stop-opacity="0"/></radialGradient></defs>'+
      '<rect width="700" height="420" fill="url(#bg)"/><circle cx="'+x+'" cy="'+y+'" r="220" fill="url(#halo)"/>'+
      '<g opacity=".13" stroke="#fff" fill="none">'+Array.from({length:7},(_,i)=>'<path d="M0 '+(80+i*52)+' Q350 '+(12+i*52)+' 700 '+(80+i*52)+'"/>').join('')+'</g>'+
      '<circle cx="350" cy="225" r="148" fill="none" stroke="'+colors[2]+'" stroke-opacity=".28" stroke-width="2"/>'+
      '<g fill="none" stroke="'+colors[2]+'" stroke-width="11" stroke-linecap="round" stroke-linejoin="round">'+(themeIcon[item.category]||themeIcon.diplomatie)+'</g>'+
      '<text x="28" y="386" fill="#fff" font-family="Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="3">RDI / GEOPOLITICA</text>'+
      '</svg>';
    return "data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);
  }
  function coverElement(item,isLarge){
    const wrap=node("div","rdi-cover-wrap");
    wrap.style.cssText="position:relative;width:100%;margin:0 0 14px;overflow:hidden;border-radius:12px;background:#15283c";
    const img=node("img","rdi-editorial-cover");
    img.src=storyIllustration(item);img.alt=state.lang==="it"?"Illustrazione editoriale originale RDI, non fotografia dell'evento":"Ilustrație editorială RDI, nu fotografie a evenimentului";
    img.loading="lazy";img.decoding="async";
    img.style.cssText="display:block;width:100%;height:auto;aspect-ratio:5/3;object-fit:cover";
    const label=node("span","rdi-cover-caption",state.lang==="it"?"ILLUSTRAZIONE RDI":"ILUSTRAȚIE RDI");
    label.style.cssText="position:absolute;bottom:9px;right:10px;font:600 10px Arial,sans-serif;letter-spacing:.08em;color:white;background:#071421bb;padding:6px 9px;border-radius:4px";
    wrap.append(img,label);return wrap;
  }
  function makeCard(item,featured=false,second=false){
    const card=node("article",featured?(second?"feature-side":"feature-lead"):"story-card");
    const meta=node("div",featured?"features-meta":"story-meta");
    meta.append(node("span","tag",item.type==="curated"?t("curated"):t("external")));
    const topicKey=TOPIC_NAMES[item.category]?.[0]||"all";
    meta.append(node("span","",t(topicKey)));
    const date=dateLabel(item.published);if(date)meta.append(node("time","",date));
    const title=node("h3","",item.title);card.append(coverElement(item,featured),meta,title);
    const intro=String(item.summary||"").replace(/\s+/g," ").trim();
    if(intro && intro.toLocaleLowerCase()!==item.title.toLocaleLowerCase()){card.append(node("p","",intro.slice(0,featured?240:150)+(intro.length>(featured?240:150)?"…":"")))}
    const contextLink=node("button","read-more",state.lang==="it"?"Leggi approfondimento RDI":"Citește analiza RDI");contextLink.type="button";contextLink.style.cssText="cursor:pointer;background:transparent;border:0;color:inherit;text-decoration:underline;padding:8px 10px 8px 0;margin-right:12px";contextLink.addEventListener("click",()=>showContext(item));card.append(contextLink);
    const link=node("a","read-more",t("read"));link.href=item.url;link.target="_blank";link.rel="noopener noreferrer";card.append(link);
    return card;
  }
  function render(){
    const filtered=cardData().slice(0,70);
    $("feed-count").textContent=filtered.length+" "+t("count");
    const featured=$("featured"),list=$("stories");
    featured.replaceChildren();list.replaceChildren();
    const top=[];
    for(const item of filtered){if(!top.length || item.category!==top[0].category){top.push(item);if(top.length===2)break}}
    if(top.length<2){for(const item of filtered){if(!top.includes(item)){top.push(item);break}}}
    for(let i=0;i<top.length;i++)featured.append(makeCard(top[i],true,i===1));
    for(const item of filtered.filter(item=>!top.includes(item)).slice(0,48))list.append(makeCard(item));
    $("empty").hidden=filtered.length>0;
    if(!state.items.length){$("empty").hidden=false;$("empty").querySelector("p").textContent=t("sourceUnavailable")}
    else $("empty").querySelector("p").textContent=t("tryFilters");
    $("feed-info").textContent=!state.feedOk?t("fallback"):t("sourceNote");
    $("updated").textContent=state.updated?t("updated")+": "+updateTimeLabel(state.updated):t("sourceNote").split(".")[0];
    document.querySelectorAll(".topic").forEach(b=>{const on=b.dataset.topic===state.topic;b.classList.toggle("active",on);b.setAttribute("aria-pressed",String(on))});
    $("region").value=state.region;
  }
  function applyLanguage(){
    document.documentElement.lang=state.lang;
    document.querySelectorAll("[data-i18n]").forEach(el=>{const key=el.dataset.i18n;if(dict[state.lang][key])el.textContent=t(key)});
    document.querySelectorAll("[data-i18n-aria]").forEach(el=>{const key=el.dataset.i18nAria;if(dict[state.lang][key])el.setAttribute("aria-label",t(key))});
    document.querySelectorAll("[data-lang]").forEach(b=>{const on=b.dataset.lang===state.lang;b.classList.toggle("selected",on);b.setAttribute("aria-pressed",String(on))});
    const regions={ro:["Toate regiunile","Europa","Orientul Mijlociu","Asia-Pacific","Africa","Americi","Global"],it:["Tutte le regioni","Europa","Medio Oriente","Asia-Pacifico","Africa","Americhe","Globale"]};
    [...$("region").options].forEach((op,i)=>op.textContent=regions[state.lang][i]);
    $("search").placeholder=t("searchPlaceholder");
    $("today").textContent=localToday();
    document.title=(state.lang==="it"?"Geopolitica":"Geopolitică")+" · Radio Românii din Italia";
    render();
  }
  let external=[],war=[],editorial=[];
  async function getJSON(path){const response=await fetch(path+"?v="+Date.now(),{cache:"no-store"});if(!response.ok)throw Error("HTTP "+response.status);return response.json()}
  async function load(){
    const results=await Promise.allSettled([getJSON("./data/geopolitica-news.json"),getJSON("./data/war-zone-news.json"),getJSON("./editorial.json"),getJSON("./news-translations.json")]);
    if(results[0].status==="fulfilled"){
      const data=results[0].value;external=Array.isArray(data.items)?data.items:[];
      state.feedOk=external.some(item=>item.title_ro&&item.title_it);state.updated=data.updated_at||"";
    }
    if(results[1].status==="fulfilled")war=Array.isArray(results[1].value.items)?results[1].value.items:[];
    if(results[2].status==="fulfilled")editorial=Array.isArray(results[2].value.items)?results[2].value.items:[];
    if(results[3].status==="fulfilled")cachedTranslations=results[3].value.items||{};
    refreshContent();
  }
  function refreshContent(){
    const list=[...external.map(normalizeExternal),...war.map(normalizeWar),...editorial.map(normalizeEditorial)].filter(Boolean);
    const seen=new Set();
    state.items=list.filter(x=>{const key=x.url.toLowerCase();if(seen.has(key))return false;seen.add(key);return true})
      .sort((a,b)=>Date.parse(b.published)-Date.parse(a.published));
    render();
  }
  document.querySelectorAll("[data-lang]").forEach(b=>b.addEventListener("click",()=>{state.lang=b.dataset.lang;try{localStorage.setItem("rdi-lang",state.lang)}catch(_){}refreshContent();applyLanguage()}));
  document.querySelectorAll(".topic").forEach(b=>b.addEventListener("click",()=>{state.topic=b.dataset.topic;render();$("actualitate").scrollIntoView({behavior:"smooth",block:"start"})}));
  $("region").addEventListener("change",e=>{state.region=e.target.value;render()});
  $("search").addEventListener("input",render);
  $("clear").addEventListener("click",()=>{state.topic="all";state.region="all";$("search").value="";render()});
  applyLanguage();load();
  // Refresh the open page after the hourly publisher updates the JSON feed.
  setInterval(()=>{if(!document.hidden)load()},60*1000);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)load()});
})();
