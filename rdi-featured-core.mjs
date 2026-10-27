/* RDI homepage newsroom selection. Pure utilities, shared by browser and tests. */
export const MAX_AGE_HOURS = 48;
const relevance = /(?:ucrain|ukrain|kyiv|kiev|kharkiv|harkiv|russi|rusia|sudan|gaza|israel|palestin|cisgiord|cisiordan|pace|tregu|ceasefire|armisti|guerr|războ|razbo|conflitt|conflict|criz|crisi|nato|ue\b|europe|europ|summit|elez|aleger|vot|voto|premier|govern|guvern|parlament|embarg|sanzion|sancți|energia|energi|econo|migra|consul|diaspora|românilor din italia|romeni in italia|munc|lavor|transport|scioper|grev|inunda|terrem|cutremur|incendi|alluvion|evacua|umanitar|humanitar|attac|atac|exploz|explos)/i;
const irrelevant = /(?:oroscop|horoscop|vedet|celebrit|zodiac|gossip|loteri|lotto|trucur|sf[âa]ntul|sfanta|mod[ăa]|fashion|hobby|rețet|retet|ricett|sportiv|calcio|fotbal)/i;
const editorialIllustration = /(?:^\.\/editorial-images\/|^\.\/images\/|\.svg(?:$|[?#]))/i;
const genericEditorialImage = /(?:ai-community-rdi|ai-economy-rdi|rdi-conflict-editorial)/i;

export function safeLink(raw) {
  if (typeof raw !== "string" || !raw.trim()) return "";
  try {
    const url = new URL(raw, "https://radioromanii.duckdns.org/");
    return url.protocol === "https:" ? url.href : "";
  } catch { return ""; }
}
export function safeImage(raw) {
  if (typeof raw !== "string") return "";
  if (/^https:\/\/[^/]+\//i.test(raw) || /^\.\/(?!\/)[\w./%-]+(?:[?#][^\s]*)?$/.test(raw) || /^\/(?!\/)[\w./%-]+/.test(raw)) return raw;
  return "";
}
export function imageIsPhotograph(img) {
  return /^https:\/\//i.test(img || "") && !/\.svg(?:$|[?#])/i.test(img);
}
function normalTitle(title) {
  return String(title || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}
function localize(x, translations, lang) {
  const key = String(x.id || x.url || (x.title + "|" + x.published));
  const translation = translations?.[key];
  const target = translation?.[lang];
  if (translation?.original?.title === x.title && target?.title) {
    return { title: target.title, summary: target.summary || "" };
  }
  // Existing feeds are mostly Romanian, while 'Italia' contains Italian items.
  // Without a matching translation, do not silently present Romanian as Italian.
  const t = String(x.title || "");
  const italianPattern = /\b(?:il|lo|gli|della|delle|dopo|sulla|alla|contro|perché|sciopero|ultime|notizie|guerra|italia|governo|elezioni|aiuti)\b/i;
  const romanianPattern = /(?:[ăâîșț]|\b(?:din|și|care|pentru|românia|români|după|știri|astăzi|război|în|cele|fost|sunt)\b)/i;
  if (lang === "it") {
    if (italianPattern.test(t) && !romanianPattern.test(t)) return {title:t,summary:x.summary || ""};
    return null;
  }
  if (lang === "ro") {
    if (romanianPattern.test(t) || (!italianPattern.test(t) && x.category !== "Italia")) return {title:t,summary:x.summary || ""};
    return null;
  }
  return null;
}
export function normalizedCandidates({news=[], editorial=[], war=[], translations={}}, lang, now=Date.now()) {
  const language = lang === "ro" ? "ro" : "it";
  const all = [];
  for (const item of war) {
    const published = String(item.published_date || "");
    const ms = Date.parse(published + "T12:00:00Z");
    const age = now-ms;
    if (!Number.isFinite(ms) || age < -16*3600e3 || age > MAX_AGE_HOURS*3600e3) continue;
    const title=String(item["title_"+language]||"").trim(),summary=String(item["summary_"+language]||"").trim();
    if (title.length < 15 || summary.length < 40 || !safeLink(item.source_url)) continue;
    const region=String(item.region||"");
    all.push({
      id:item.id || item.source_url, category:"Geopolitica", region,
      title,summary,source:item.source_name || "RDI",
      published:published+"T12:00:00Z", url:item.source_url,
      image:"./editorial-images/rdi-conflict-editorial.svg",
      fallbackImage:"./editorial-images/rdi-conflict-editorial.svg",
      editorialIllustration:true, verified:true, editorial:true, fromWar:true,
    });
  }
  for (const item of [...editorial, ...news]) {
    if (!item || typeof item !== "object") continue;
    const ms=Date.parse(item.published), age=now-ms;
    if (!Number.isFinite(ms)||age<0||age>MAX_AGE_HOURS*3600e3)continue;
    if (item.promotion || item.sponsored) continue;
    const localized=localize(item,translations,language);
    if (!localized || localized.title.length<18 || !safeLink(item.url))continue;
    const image=safeImage(item.image),fallback=safeImage(item.fallbackImage||item.fallback_image);
    const illustrative=Boolean(item.imageType==="editorial-illustration"||editorialIllustration.test(image));
    all.push({
      id:item.id||item.url, category:item.category||"Actualitate",
      title:localized.title, summary:localized.summary, published:item.published,
      source:item.source||"RDI",url:item.url, image, fallbackImage:fallback,
      editorialIllustration:illustrative, verified: Boolean(item.editorial && item.review_status==="verified") || Boolean(item.editorial && item.verified===true),
      editorial: item.editorial===true, breaking:item.breaking===true,
    });
  }
  return all;
}
export function scoreStory(x, now=Date.now()) {
  const age=Math.max(0,(now-Date.parse(x.published))/3600e3);
  const title=String(x.title||"");
  let score= Math.max(0,42-age*1.5);
  if(x.fromWar) score+=42;
  if(x.editorial)score+=20;
  if(x.verified)score+=18;
  if(x.breaking)score+=20;
  if(relevance.test(title))score+=32;
  if(irrelevant.test(title))score-=38;
  if(imageIsPhotograph(x.image))score+=32;
  else if(x.image&&!genericEditorialImage.test(x.image))score+=8;
  if(String(x.summary||"").length>65)score+=4;
  if(x.category==="Diaspora" || x.category==="Știri consulare" || x.category==="Drepturile muncitorilor")score+=13;
  return score;
}
export function chooseFeatured(items, now=Date.now(), limit=5) {
  const ranked=items.slice().sort((a,b)=>scoreStory(b,now)-scoreStory(a,now));
  const selected=[], keys=new Set(), categoryCounts=new Map(), topicCounts=new Map();
  const titleOverlap=(a,b)=>{
    const words=t=>new Set(normalTitle(t).split(" ").filter(w=>w.length>=5));
    const wa=words(a),wb=words(b);
    const common=[...wa].filter(w=>wb.has(w)).length;
    return common>=4 && common/Math.min(Math.max(1,wa.size),Math.max(1,wb.size))>=.5;
  };
  // Reserve the prominent hero for a real photo if a relevant image is available.
  const imageLead=ranked.find(x=>imageIsPhotograph(x.image) && scoreStory(x,now)>=55);
  if(imageLead){selected.push(imageLead);keys.add(imageLead.url);}
  function canAdd(x, balance) {
    if(keys.has(x.url) || selected.some(y=>titleOverlap(x.title,y.title))) return false;
    const cat=x.fromWar?"geopolitica":String(x.category||"Altro");
    if(balance && (categoryCounts.get(cat)||0)>=2) return false;
    const region=x.fromWar?String(x.region||"global"):"";
    if(balance && region && (topicCounts.get(region)||0)>=2) return false;
    return true;
  }
  if(imageLead) categoryCounts.set(String(imageLead.category||"Altro"),1);
  // Show at least one checked conflict story when present.
  const firstReviewed=ranked.find(x=>x.fromWar && canAdd(x,true));
  if(firstReviewed && selected.length<limit) {
    selected.push(firstReviewed); keys.add(firstReviewed.url);
    categoryCounts.set("geopolitica",(categoryCounts.get("geopolitica")||0)+1);
    topicCounts.set(firstReviewed.region,(topicCounts.get(firstReviewed.region)||0)+1);
  }
  // Photojournalism deserves its own space; don't let a dense conflict RSS
  // feed replace all other images with generic illustrations.
  const photoTarget=Math.min(3,ranked.filter(x=>imageIsPhotograph(x.image)).length);
  for(const x of ranked.filter(x=>imageIsPhotograph(x.image))) {
    if(selected.length>=limit || selected.filter(y=>imageIsPhotograph(y.image)).length>=photoTarget)break;
    if(!canAdd(x,false))continue;
    selected.push(x);keys.add(x.url);
    const cat=x.fromWar?"geopolitica":String(x.category||"Altro");
    categoryCounts.set(cat,(categoryCounts.get(cat)||0)+1);
  }
  for(const balance of [true,false]){
    for(const x of ranked) {
      if(selected.length>=limit)break;
      if(!canAdd(x,balance))continue;
      selected.push(x);keys.add(x.url);
      const cat=x.fromWar?"geopolitica":String(x.category||"Altro");
      categoryCounts.set(cat,(categoryCounts.get(cat)||0)+1);
      if(x.fromWar)topicCounts.set(x.region,(topicCounts.get(x.region)||0)+1);
    }
    if(selected.length>=limit)break;
  }
  return selected;
}
