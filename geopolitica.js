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
  let aiArticles={};
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
    return {id:item.id,title:String(title).slice(0,260),summary:String(summary||"").slice(0,400),
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
  // Per-news analysis must be grounded in a separately sourced RDI editorial article.
  function articleFor(item){
    if(item.id && aiArticles[item.id])return aiArticles[item.id];
    const original=validUrl(item.url);
    if(!original)return null;
    const matches=Object.values(aiArticles).filter(record=>{
      if(!record || !record.it?.title || !record.ro?.title)return false;
      return [record.source_url,...(Array.isArray(record.source_urls)?record.source_urls:[])]
        .some(url=>validUrl(url)===original);
    });
    return matches.length===1?matches[0]:null;
  }
  function showContext(item){
    const dialog=$("article-dialog");if(!dialog)return;
    const record=articleFor(item);
    const publishedArticle=record?.[state.lang];
    $("article-category").textContent=t(TOPIC_NAMES[item.category]?.[0]||"all")+" · RDI";
    $("article-title").textContent=item.title;
    $("article-disclaimer").textContent=publishedArticle?(record.editorial_status==="editorially_reviewed"?(state.lang==="it"?"Approfondimento RDI con fonti indicate e revisione editoriale.":"Analiză RDI cu surse indicate și revizuire editorială."):(state.lang==="it"?"Analisi RDI assistita dall'IA, non ancora revisionata dalla redazione.":"Analiză RDI asistată de IA, încă nerevizuită editorial.")) : state.lang==="it"
      ?"Scheda della notizia selezionata. La fonte esterna è indicata in fondo: RDI non dispone ancora di un approfondimento verificato per questo specifico articolo."
      :"Fișa știrii selectate. Sursa externă este indicată mai jos: RDI nu are încă o analiză verificată pentru acest articol.";
    const body=$("article-body");body.replaceChildren(coverElement(item,true));
    if(publishedArticle){
      if(publishedArticle.lead)body.append(node("p","",String(publishedArticle.lead)));
      for(const section of publishedArticle.sections||[]){
        if(section.heading)body.append(node("h3","",String(section.heading)));
        for(const p of section.paragraphs||[])body.append(node("p","",String(p)));
      }
      if(publishedArticle.conclusion){body.append(node("h3","",state.lang==="it"?"Conclusioni":"Concluzii"));body.append(node("p","",String(publishedArticle.conclusion)))}
    } else {
      // No generic category essay masquerading as a specific news analysis.
      body.append(node("h3","",state.lang==="it"?"La notizia":"Știrea"));
      body.append(node("p","",item.title));
      if(item.summary)body.append(node("p","",item.summary));
      body.append(node("h3","",state.lang==="it"?"Cosa sappiamo dalla fonte":"Ce știm din sursă"));
      body.append(node("p","",state.lang==="it"
        ?"Questa scheda riporta il titolo pubblicato dalla testata indicata, con la data di pubblicazione. Per i dettagli, i protagonisti, le cause e le conseguenze occorre consultare l'articolo originale: non aggiungiamo ricostruzioni non documentate."
        :"Această fișă redă titlul publicației citate și data publicării. Pentru detalii, persoanele implicate, cauze și consecințe, consultați articolul original; nu adăugăm explicații neverificate."));
    }
    const image=record?.image;
    if(typeof image==="string" && image.startsWith("./data/geopolitica-images/") && image.endsWith(".png")){
      const img=body.querySelector(".rdi-editorial-cover");if(img)img.src=image;
    }
    $("article-attribution").textContent=item.source+" · "+dateLabel(item.published);
    $("article-original").href=item.url;
    $("article-original").textContent=t("read");
    if(publishedArticle && Array.isArray(record.source_urls)){
      const distinct=[...new Set(record.source_urls.map(validUrl).filter(Boolean))];
      if(distinct.length){
        body.append(node("h3","",state.lang==="it"?"Fonti dell'approfondimento":"Sursele analizei"));
        const ul=node("ul","");
        distinct.forEach((url,index)=>{
          const li=node("li","");
          const a=node("a","", (state.lang==="it"?"Fonte ":"Sursa ")+(index+1));
          a.href=url;a.target="_blank";a.rel="noopener noreferrer";
          li.append(a);ul.append(li);
        });
        body.append(ul);
      }
    }
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
    const picture=item.id&&aiArticles[item.id]?.image;
    const category=TOPICS.includes(item.category)?item.category:"diplomatie";
    const identity=String(item.id||item.url||item.title||"rdi");
    let imageHash=2166136261;
    for(let i=0;i<identity.length;i++){imageHash=Math.imul(imageHash^identity.charCodeAt(i),16777619)>>>0}
    const variant=(imageHash%10)+1;
    const categoryPicture="./data/geopolitica-images/categories/"+category+"/"+String(variant).padStart(2,"0")+".webp";
    img.src=categoryPicture;
    img.onerror=()=>{
      img.onerror=null;img.src=storyIllustration(item);
    };
    img.alt=state.lang==="it"?"Illustrazione editoriale originale RDI, non fotografia dell'evento":"Ilustrație editorială RDI, nu fotografie a evenimentului";
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
    const title=node("h3","",item.title);const cover=coverElement(item,featured);
    card.append(cover,meta,title);
    const intro=String(item.summary||"").replace(/\s+/g," ").trim();
    if(intro && intro.toLocaleLowerCase()!==item.title.toLocaleLowerCase()){card.append(node("p","",intro.slice(0,featured?240:150)+(intro.length>(featured?240:150)?"…":"")))}
    const hasLongArticle=!!(item.id&&aiArticles[item.id]?.[state.lang]);
    const contextLink=node("button","read-more",state.lang==="it"?(hasLongArticle?"Leggi articolo completo RDI":"Dettagli della notizia"):(hasLongArticle?"Citește articolul complet RDI":"Detaliile știrii"));contextLink.type="button";contextLink.style.cssText="cursor:pointer;background:transparent;border:0;color:inherit;text-decoration:underline;padding:8px 10px 8px 0;margin-right:12px";contextLink.addEventListener("click",()=>showContext(item));card.append(contextLink);
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
    const results=await Promise.allSettled([getJSON("./data/geopolitica-news.json"),getJSON("./data/war-zone-news.json"),getJSON("./editorial.json"),getJSON("./news-translations.json"),getJSON("./data/geopolitica-articles.json")]);
    if(results[0].status==="fulfilled"){
      const data=results[0].value;external=Array.isArray(data.items)?data.items:[];
      state.feedOk=external.some(item=>item.title_ro&&item.title_it);state.updated=data.updated_at||"";
    }
    if(results[1].status==="fulfilled")war=Array.isArray(results[1].value.items)?results[1].value.items:[];
    if(results[2].status==="fulfilled")editorial=Array.isArray(results[2].value.items)?results[2].value.items:[];
    if(results[3].status==="fulfilled")cachedTranslations=results[3].value.items||{};
    if(results[4].status==="fulfilled")aiArticles=results[4].value.items||{};
    refreshContent();
  }
  function refreshContent(){
    const standalone=Object.values(aiArticles).filter(x=>x&&x.id&&x.source_url&&x.it?.title&&x.ro?.title).map(x=>({
      id:x.id,title:String(x[state.lang].title),summary:String(x[state.lang].lead||"").slice(0,400),
      category:TOPICS.includes(x.category)?x.category:"diplomatie",
      region:REGIONS.includes(x.region)?x.region:"global",
      url:x.source_url,source:"RDI / "+String(x.source_name||"Redazione"),
      published:x.source_published,type:"curated"
    }));
    const list=[...standalone,...external.map(normalizeExternal),...war.map(normalizeWar),...editorial.map(normalizeEditorial)].filter(Boolean);
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
