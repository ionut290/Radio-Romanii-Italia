"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const dict = {
    ro: {
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
      sourceNote:"Știri din fluxuri externe. Titlurile pot fi în limba sursei; nu sunt automat verificate de redacție.",
      noResults:"Nicio știre pentru selecția actuală",tryFilters:"Încearcă alt domeniu, o altă regiune sau revino mai târziu.",
      externalDisclaimer:"O selecție de titluri externe, nu o confirmare independentă a evenimentelor. Verifică data și sursa articolului.",
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
      fallback:"Fluxul extern nu este încă disponibil. Sunt afișate materialele existente în observatorul RDI.",
      count:"știri",sourceUnavailable:"Nu există încă materiale pentru această selecție.",
      searchPlaceholder:"Caută un subiect sau o țară…"
    },
    it: {
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
      sourceNote:"Notizie da fonti esterne. I titoli possono essere nella lingua originale; non sono automaticamente verificati dalla redazione.",
      noResults:"Nessuna notizia per questa selezione",tryFilters:"Prova un altro tema, un'altra regione oppure torna più tardi.",
      externalDisclaimer:"Titoli esterni selezionati, non verifiche indipendenti dei fatti. Controlla sempre data e fonte.",
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
      fallback:"Il flusso esterno non è ancora disponibile. Mostriamo i contenuti esistenti nell'osservatorio RDI.",
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
  try {if(localStorage.getItem("rdi-lang")==="it")state.lang="it"}catch(_){}
  function t(key){return dict[state.lang][key]||key}
  function validUrl(value){try {const u=new URL(String(value));return u.protocol==="https:"?u.href:null}catch(_){return null}}
  function dateISO(value){const d=new Date(value||"");return Number.isNaN(d.getTime())?null:d}
  function dateLabel(value){const d=dateISO(value);return d?new Intl.DateTimeFormat(state.lang==="it"?"it-IT":"ro-RO",{timeZone:"Europe/Rome",day:"numeric",month:"short",year:"numeric"}).format(d):""}
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
    if(!item||!validUrl(item.url)||!item.title||!TOPICS.includes(item.category)||!dateISO(item.published))return null;
    const published=dateISO(item.published);
    if(published.getTime()>Date.now()+3600000)return null;
    return {title:String(item.title).slice(0,260),summary:String(item.summary||"").slice(0,400),
      category:item.category,region:REGIONS.includes(item.region)?item.region:regionGuess(item.title),
      url:validUrl(item.url),source:String(item.source||"Publicație externă").slice(0,100),
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
    const name=String(item.title);
    const category=/energie|petrol|gaz|resurse/i.test(name)?"energie":/diploma|negoc|ambasad|onu|tratat/i.test(name)?"diplomatie":/nato|securitate|apărare/i.test(name)?"securitate":/uniunea european|comisia european|bruxelles/i.test(name)?"europa":"conflicte";
    return {title:name,summary:String(item.summary||"").slice(0,400),category,region:regionGuess(name),
      url:validUrl(item.url),source:"RDI / "+String(item.source||"Redacție").slice(0,70),published:item.published,type:"curated"};
  }
  function cardData(){
    const chosen=state.items.filter(x=>(state.topic==="all"||x.category===state.topic)&&(state.region==="all"||x.region===state.region));
    const query=$("search").value.trim().toLocaleLowerCase();
    return chosen.filter(x=>!query||[x.title,x.summary,x.source].join(" ").toLocaleLowerCase().includes(query));
  }
  function makeCard(item,featured=false,second=false){
    const card=node("article",featured?(second?"feature-side":"feature-lead"):"story-card");
    const meta=node("div",featured?"features-meta":"story-meta");
    meta.append(node("span","tag",item.type==="curated"?t("curated"):t("external")));
    const topicKey=TOPIC_NAMES[item.category]?.[0]||"all";
    meta.append(node("span","",t(topicKey)));
    const date=dateLabel(item.published);if(date)meta.append(node("time","",date));
    const title=node("h3","",item.title);card.append(meta,title);
    const intro=String(item.summary||"").replace(/\s+/g," ").trim();
    if(intro && intro.toLocaleLowerCase()!==item.title.toLocaleLowerCase()){card.append(node("p","",intro.slice(0,featured?240:150)+(intro.length>(featured?240:150)?"…":"")))}
    const link=node("a","read-more",t("read"));link.href=item.url;link.target="_blank";link.rel="noopener noreferrer";card.append(link);
    return card;
  }
  function render(){
    const filtered=cardData().slice(0,70);
    $("feed-count").textContent=filtered.length+" "+t("count");
    const featured=$("featured"),list=$("stories");
    featured.replaceChildren();list.replaceChildren();
    const top=filtered.slice(0,2);
    for(let i=0;i<top.length;i++)featured.append(makeCard(top[i],true,i===1));
    for(const item of filtered.slice(2,50))list.append(makeCard(item));
    $("empty").hidden=filtered.length>0;
    if(!state.items.length){$("empty").hidden=false;$("empty").querySelector("p").textContent=t("sourceUnavailable")}
    else $("empty").querySelector("p").textContent=t("tryFilters");
    $("feed-info").textContent=!state.feedOk?t("fallback"):t("sourceNote");
    $("updated").textContent=state.updated?t("updated")+": "+dateLabel(state.updated):t("sourceNote").split(".")[0];
    document.querySelectorAll(".topic").forEach(b=>{const on=b.dataset.topic===state.topic;b.classList.toggle("active",on);b.setAttribute("aria-pressed",String(on))});
    $("region").value=state.region;
  }
  function applyLanguage(){
    document.documentElement.lang=state.lang;
    document.querySelectorAll("[data-i18n]").forEach(el=>{const key=el.dataset.i18n;if(dict[state.lang][key])el.textContent=t(key)});
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
    const results=await Promise.allSettled([getJSON("./data/geopolitica-news.json"),getJSON("./data/war-zone-news.json"),getJSON("./editorial.json")]);
    if(results[0].status==="fulfilled"){
      const data=results[0].value;external=(Array.isArray(data.items)?data.items:[]).map(normalizeExternal).filter(Boolean);
      state.feedOk=external.length>0;state.updated=data.updated_at||"";
    }
    if(results[1].status==="fulfilled")war=Array.isArray(results[1].value.items)?results[1].value.items:[];
    if(results[2].status==="fulfilled")editorial=Array.isArray(results[2].value.items)?results[2].value.items:[];
    refreshContent();
  }
  function refreshContent(){
    const list=[...external,...war.map(normalizeWar),...editorial.map(normalizeEditorial)].filter(Boolean);
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
})();
