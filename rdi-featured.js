import {normalizedCandidates,chooseFeatured,safeImage,imageIsPhotograph} from "./rdi-featured-core.mjs?v=20261027a";

/* RDI – auto-updated homepage editorial picks. No separate publishing service. */
const section=document.getElementById("rdi-featured");
const grid=document.getElementById("rdi-featured-grid");
const heading=document.getElementById("rdi-featured-title");
const strap=document.getElementById("rdi-featured-kicker");
const note=document.getElementById("rdi-featured-note");
const allLink=document.getElementById("rdi-featured-all");
const picker=document.getElementById("rdi-language");
let collections={news:[],editorial:[],war:[],translations:{}};
let fetchedAt=0;
let refreshPromise=null;
const translations={
  it:{
    kicker:"RDI · IN PRIMO PIANO",title:"Le notizie più importanti",
    all:"Tutte le notizie",read:"Leggi l'articolo",illustration:"Illustrazione editoriale · non è una foto dell'evento",
    image:"Foto relativa all'articolo",date:"it-IT",
    notice:"Selezione automatica di notizie recenti e rilevanti. Le informazioni delle testate esterne sono attribuite alle rispettive fonti e non tutte sono verificate indipendentemente da RDI."
  },
  ro:{
    kicker:"RDI · ÎN PRIM-PLAN",title:"Cele mai importante știri",
    all:"Toate știrile",read:"Citește articolul",illustration:"Ilustrație editorială · nu este fotografia evenimentului",
    image:"Fotografie asociată articolului",date:"ro-RO",
    notice:"Selecție automată de știri recente și relevante. Informațiile publicațiilor externe sunt atribuite surselor și nu toate sunt verificate independent de RDI."
  }
};
function language(){return picker?.value==="ro"?"ro":"it";}
async function fetchJson(path) {
  const response=await fetch(path+"?rdi="+Date.now(),{cache:"no-store",signal:AbortSignal.timeout(9500)});
  if(!response.ok)throw Error("HTTP "+response.status);
  return response.json();
}
function plainParagraph(text,max=180) {
  const clean=String(text||"").replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim();
  if(clean.length<=max)return clean;
  const stop=clean.lastIndexOf(" ",max);
  return clean.slice(0,stop>max*.65?stop:max)+"…";
}
function element(tag,className,text) {
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined)node.textContent=text;
  return node;
}
function addIllustrationLabel(visual,cfg) {
  if(visual.querySelector(".rdi-featured-photo-label"))return;
  visual.append(element("span","rdi-featured-photo-label",cfg.illustration));
}
function displayImage(visual,article,cfg,lead=false) {
  const container=element("div","rdi-featured-image-placeholder");
  container.append(element("span","", "◉"),element("strong","","RDI"));
  visual.append(container);
  const selected=safeImage(article.image);
  const fallback=safeImage(article.fallbackImage)||"./RADIO-COVER.jpg";
  const image=document.createElement("img");
  image.loading=lead?"eager":"lazy";
  image.decoding="async";
  image.alt=cfg.image;
  if(lead)image.fetchPriority="high";
  let triedFallback=false;
  image.addEventListener("load",()=>{
    container.hidden=true;
    if(article.editorialIllustration||triedFallback||!imageIsPhotograph(image.src)){
      image.alt=cfg.illustration;
      addIllustrationLabel(visual,cfg);
    }
  });
  image.addEventListener("error",()=>{
    if(!triedFallback && fallback && selected!==fallback) {
      triedFallback=true;
      image.src=fallback;
    } else {
      image.remove();
      container.hidden=false;
      addIllustrationLabel(visual,cfg);
    }
  });
  if(article.editorialIllustration)addIllustrationLabel(visual,cfg);
  image.src=selected||fallback;
  visual.append(image);
}
function paint() {
  if(!section||!grid)return;
  const lang=language(),cfg=translations[lang],now=Date.now();
  heading.textContent=cfg.title;
  strap.textContent=cfg.kicker;
  allLink.textContent=cfg.all+" ›";
  note.textContent=cfg.notice;
  const candidates=normalizedCandidates(collections,lang,now);
  const stories=chooseFeatured(candidates,now,5);
  grid.replaceChildren();
  if(!stories.length){section.hidden=true;return;}
  for(const [index,story] of stories.entries()){
    const storyNode=element("article","rdi-featured-story");
    const link=element("a","rdi-featured-link");
    link.href=story.url;
    link.target="_blank";
    link.rel="noopener noreferrer";
    link.setAttribute("aria-label",cfg.read+": "+story.title);
    const visual=element("div","rdi-featured-visual");
    displayImage(visual,story,cfg,index===0);
    const body=element("div","rdi-featured-story-body");
    const meta=element("div","rdi-featured-meta");
    const category=element("span","rdi-featured-category",story.category==="Geopolitica"?(lang==="ro"?"Geopolitică":"Geopolitica"):story.category);
    const date=new Date(story.published);
    const dateString=Number.isFinite(date.getTime())?new Intl.DateTimeFormat(cfg.date,{timeZone:"Europe/Rome",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(date):"";
    meta.append(category,element("time","",dateString));
    const title=element("h3","",story.title);
    const summary=element("p","rdi-featured-excerpt",plainParagraph(story.summary,index===0?240:145));
    if(!summary.textContent)summary.hidden=true;
    const source=element("small","rdi-featured-source",story.source || "RDI");
    const read=element("span","rdi-featured-read",cfg.read+" ›");
    body.append(meta,title,summary,source,read);
    link.append(visual,body);
    storyNode.append(link);
    grid.append(storyNode);
  }
  section.hidden=false;
}
async function update() {
  if(refreshPromise)return refreshPromise;
  refreshPromise=(async()=>{
    const previous=collections;
    const entries=await Promise.allSettled([
      fetchJson("./news.json"),
      fetchJson("./editorial.json"),
      fetchJson("./data/war-zone-news.json"),
      fetchJson("./news-translations.json")
    ]);
    // Keep previous valid data if one upstream endpoint briefly fails.
    collections={
      news:entries[0].status==="fulfilled"&&Array.isArray(entries[0].value.items)?entries[0].value.items:previous.news,
      editorial:entries[1].status==="fulfilled"&&Array.isArray(entries[1].value.items)?entries[1].value.items:previous.editorial,
      war:entries[2].status==="fulfilled"&&Array.isArray(entries[2].value.items)?entries[2].value.items:previous.war,
      translations:entries[3].status==="fulfilled"&&entries[3].value.items?entries[3].value.items:previous.translations
    };
    fetchedAt=Date.now();
    paint();
  })().catch(error=>{console.warn("RDI in primo piano:",error);paint()}).finally(()=>refreshPromise=null);
  return refreshPromise;
}
if(section&&grid&&picker) {
  picker.addEventListener("change",paint);
  window.addEventListener("storage",event=>{if(event.key==="rdi-language")paint()});
  window.addEventListener("focus",()=>{if(Date.now()-fetchedAt>11*60*1000)update()});
  setInterval(update,10*60*1000);
  update();
}
