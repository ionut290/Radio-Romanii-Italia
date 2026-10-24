// RDI richer directory details. No external review scores are cached or represented as RDI-verified.
const locales={
 ro:{about:"Despre activitate",offers:"Ce oferă",services:"Servicii oferite",products:"Produse / meniu",prices:"Prețuri orientative",languages:"Limbi vorbite",payments:"Modalități de plată",access:"Accesibilitate",delivery:"Livrare / programări",contact:"Profiluri și informații",reviews:"Recenzii pe alte platforme",disclaimer:"Se deschide o căutare externă, nu o recenzie verificată de RDI. Verifică numele și adresa firmei înainte de a decide.",search:"Caută pe",direct:"Deschide pe",missing:"Descrierea detaliată nu este încă disponibilă. Verifică informațiile direct cu activitatea.",consulted:"Sursă consultată la"},
 it:{about:"Informazioni sull'attività",offers:"Cosa offre",services:"Servizi offerti",products:"Prodotti / menù",prices:"Prezzi indicativi",languages:"Lingue parlate",payments:"Metodi di pagamento",access:"Accessibilità",delivery:"Consegna / appuntamenti",contact:"Profili e informazioni",reviews:"Recensioni su altre piattaforme",disclaimer:"Si apre una ricerca esterna, non una recensione verificata da RDI. Controlla nome e indirizzo dell'attività.",search:"Cerca su",direct:"Apri su",missing:"La descrizione dettagliata non è ancora disponibile. Verifica le informazioni direttamente con l'attività.",consulted:"Fonte consultata il"},
 en:{about:"About the business",offers:"What it offers",services:"Services",products:"Products / menu",prices:"Indicative prices",languages:"Languages spoken",payments:"Payment methods",access:"Accessibility",delivery:"Delivery / bookings",contact:"Online profiles and information",reviews:"Reviews on other platforms",disclaimer:"This opens an external search, not an RDI-verified review. Check the business name and address before deciding.",search:"Search on",direct:"Open on",missing:"A detailed description is not yet available. Confirm the information directly with the business.",consulted:"Source checked on"}
};
const fieldNames={"Servicii oferite":"services","Produse sau meniu":"products","Prețuri orientative":"prices","Limbi vorbite":"languages","Modalități de plată":"payments","Accesibilitate":"access","Livrare și programări":"delivery","Facebook":"facebookUrl","Instagram":"instagramUrl"};
const labels={services:"services",products:"products",prices:"prices",languages:"languages",payments:"payments",access:"access",delivery:"delivery"};
const text=(tag,value,cls)=>{const el=document.createElement(tag);if(value!==undefined)el.textContent=value;if(cls)el.className=cls;return el};
const tidy=value=>typeof value==="string"?value.trim():Array.isArray(value)?value.filter(x=>typeof x==="string").join(", ").trim():"";
function httpUrl(value){try{const u=new URL(value);return (u.protocol==="https:"||u.protocol==="http:")?u.href:null}catch{return null}}
function reviewUrl(value,domains){const href=httpUrl(value);if(!href)return null;const host=new URL(href).hostname.toLowerCase();return domains.some(x=>host===x||host.endsWith("."+x))?href:null}
export function splitDirectoryDescription(raw){
 const sections={},prose=[];
 for(const line of String(raw||"").split(/\r?\n/)){
  const match=line.trim().match(/^([^:]{2,45}):\s*(.*)$/);
  const key=match&&fieldNames[match[1]];
  if(key&&match[2])sections[key]=match[2].trim();
  else prose.push(line);
 }
 return {intro:prose.join("\n").trim(),fields:sections};
}
export function businessReviewLinks(b){
 const q=[b.name,b.address,b.city,b.province,"Italia"].filter(Boolean).join(", ");
 const nameCity=[b.name,b.city,"Italia"].filter(Boolean).join(" ");
 const details=b.reviewLinks&&typeof b.reviewLinks==="object"?b.reviewLinks:{};
 const google=reviewUrl(details.google||b.googleMapsUrl,["google.com","google.it","maps.google.com"]);
 const placeId=/^[A-Za-z0-9_-]{8,255}$/.test(b.googlePlaceId||"")?b.googlePlaceId:null;
 const mapsSearch="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(q)+(placeId?"&query_place_id="+encodeURIComponent(placeId):"");
 const facebook=reviewUrl(details.facebook||b.facebookUrl,["facebook.com","fb.com"]);
 const tripadvisor=reviewUrl(details.tripadvisor||b.tripadvisorUrl,["tripadvisor.it","tripadvisor.com"]);
 const trustpilot=reviewUrl(details.trustpilot||b.trustpilotUrl,["trustpilot.com"]);
 const out=[
  {name:"Google Maps",url:google||mapsSearch,direct:!!google||!!placeId},
  {name:"Facebook",url:facebook||"https://www.facebook.com/search/pages/?q="+encodeURIComponent(nameCity),direct:!!facebook}
 ];
 if(/restaurante|restaurant|turism|hotel|cazare|ospitalit/i.test(String(b.category||"")))out.push({name:"Tripadvisor",url:tripadvisor||"https://www.tripadvisor.it/Search?q="+encodeURIComponent(nameCity),direct:!!tripadvisor});
 if(b.website||trustpilot)out.push({name:"Trustpilot",url:trustpilot||"https://it.trustpilot.com/search?query="+encodeURIComponent(b.name||""),direct:!!trustpilot});
 const source=reviewUrl(b.sourceUrl,["deafara.com"]);if(source)out.push({name:"De afară",url:source,direct:true});
 return out;
}
export function directoryIntro(b){return splitDirectoryDescription(b.description).intro;}
export function buildDirectoryExtras(b,language="ro"){
 const t=locales[language]||locales.ro;
 const frag=document.createDocumentFragment(),part=splitDirectoryDescription(b.description);
 const facts=text("section",undefined,"rdi-business-facts"),items=[];
 const values={...part.fields};
 for(const key of Object.keys(labels)){const v=tidy(b[key]||b[key==="prices"?"priceInfo":key==="products"?"productList":key]);if(v)values[key]=v}
 for(const key of Object.keys(labels))if(values[key])items.push([t[key],String(values[key]).slice(0,650)]);
 if(items.length){
  facts.append(text("h3",t.offers));
  const dl=text("dl",undefined,"rdi-business-grid");
  for(const [label,value] of items){const group=text("div",undefined,"rdi-business-fact");group.append(text("dt",label),text("dd",value));dl.append(group)}
  facts.append(dl);frag.append(facts);
 }
 const profiles=[];
 for(const [key,domains,name] of [["facebookUrl",["facebook.com","fb.com"],"Facebook"],["instagramUrl",["instagram.com"],"Instagram"]]){
  const href=reviewUrl(b[key]||part.fields[key],domains);if(href)profiles.push({name,url:href});
 }
 const menu=httpUrl(b.menuUrl);if(menu)profiles.push({name:language==="ro"?"Meniu":"Menu",url:menu});
 const booking=httpUrl(b.bookingUrl);if(booking)profiles.push({name:language==="ro"?"Rezervări":language==="it"?"Prenotazioni":"Bookings",url:booking});
 if(profiles.length){const block=text("section",undefined,"rdi-business-external");block.append(text("h3",t.contact));const group=text("div",undefined,"rdi-external-links");for(const profile of profiles){const a=text("a",profile.name+" ↗","rdi-external-link");a.href=profile.url;a.target="_blank";a.rel="noopener noreferrer";group.append(a)}block.append(group);frag.append(block)}
 const review=text("section",undefined,"rdi-business-reviews");review.append(text("h3","★ "+t.reviews));
 const links=text("div",undefined,"rdi-external-links");
 for(const link of businessReviewLinks(b)){const a=text("a",(link.direct?t.direct:t.search)+" "+link.name+" ↗","rdi-external-link");a.href=link.url;a.target="_blank";a.rel="noopener noreferrer";links.append(a)}
 review.append(links,text("p",t.disclaimer,"rdi-review-disclaimer"));frag.append(review);
 if(b.detailsSourceUrl&&httpUrl(b.detailsSourceUrl)){
  const proof=text("p",undefined,"rdi-source-proof");
  const pText={ro:"Detalii din sursa oficială",it:"Dettagli dalla fonte ufficiale",en:"Details from the official source"};
  const link=text("a",(pText[language]||pText.ro)+" ↗");
  link.href=httpUrl(b.detailsSourceUrl);link.target="_blank";link.rel="noopener noreferrer";proof.append(link);
  if(/^\d{4}-\d{2}-\d{2}$/.test(b.detailsCheckedAt||""))proof.append(text("span"," · "+t.consulted+" "+b.detailsCheckedAt));
  frag.append(proof);
 }
 if(/^\d{4}-\d{2}-\d{2}$/.test(b.checkedAt||""))frag.append(text("p",t.consulted+" "+b.checkedAt,"rdi-source-date"));
 return frag;
}
export function composeDirectoryDescription(description, fields){
 const additions=Object.entries(fieldNames).map(([label,key])=>{const raw=String(fields[key]||"").trim();return raw?label+": "+raw:null}).filter(Boolean);
 return [String(description||"").trim(),...additions].filter(Boolean).join("\n");
}
export function profileUrlAllowed(value,domain){return !value||!!reviewUrl(value,[domain]);}
