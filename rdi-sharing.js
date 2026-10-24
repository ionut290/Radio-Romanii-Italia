// Shared news and event sharing: keep the same Facebook/native/copy flow.
function rdiLanguage(){const v=localStorage.getItem("rdi-language")||"ro";return v==="it"?"it":"ro"}
function rdiEventLegacyId(e){return e.city?.startsWith("Altedo")&&e.date==="2026-11-28"?"altedo-2026-11-28":e.date+"-"+(e.city||"italia").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"-")}
function rdiEventId(e){return rdiEventLegacyId(e)+"-"+rdiArticleId({id:e.url||e.title+"|"+e.date})}
function rdiEventShareData(e){return {...e,eventId:rdiEventId(e),summary:[e.date,e.endDate&&e.endDate!==e.date?"→ "+e.endDate:"",e.city,e.region].filter(Boolean).join(" · "),body:e.description||""}}
function rdiArticleId(x){const raw=String(x.id||x.url||x.title+"|"+x.published);let h=2166136261;for(let i=0;i<raw.length;i++){h^=raw.charCodeAt(i);h=Math.imul(h,16777619)}return (h>>>0).toString(16)}
function rdiShareUrl(x){if(x.eventId)return new URL("/eventi/"+x.eventId+"-social.html",location.href).href;const key=String(x.id||x.url||x.title+"|"+x.published);const language=rdiLanguage();const localized=rdiTranslations[key]?.[language]?.title?"-"+language:"";return new URL("./articole/"+rdiArticleId(x)+localized+"-social.html",location.href).href}
async function rdiShareArticleFallback(x,anchor){const url=rdiShareUrl(x),title=x.title,it=rdiLanguage()==="it";if(anchor?.disabled)return;if(anchor)anchor.disabled=true;let ready=false;try{const response=await fetch(url,{cache:"no-store"});const page=response.ok?await response.text():"";const parsed=new DOMParser().parseFromString(page,"text/html");ready=parsed.querySelector('meta[property="og:type"]')?.content==="article"&&parsed.querySelector('meta[property="og:url"]')?.content===url.split("?")[0]}catch(error){console.warn("Article preview unavailable",error)}finally{if(anchor)anchor.disabled=false}if(!ready){document.getElementById("rdi-social-share-actions")?.remove();const pending=document.createElement("p");pending.id="rdi-social-share-actions";pending.setAttribute("role","status");pending.textContent=it?"La pagina di questo contenuto è in preparazione. Riprova tra qualche minuto.":"Pagina acestui conținut este în pregătire. Încearcă din nou peste câteva minute.";if(anchor?.parentNode)anchor.after(pending);return}document.getElementById("rdi-social-share-actions")?.remove();const box=document.createElement("div");box.id="rdi-social-share-actions";box.className="rdi-share-actions";box.setAttribute("role","group");box.setAttribute("aria-label",it?"Condividi contenuto":"Distribuie conținutul");const notice=document.createElement("p");notice.textContent=title;box.append(notice);const fb=document.createElement("a");fb.textContent="Facebook";fb.href="https://www.facebook.com/sharer/sharer.php?u="+encodeURIComponent(url);fb.target="_blank";fb.rel="noopener noreferrer";const ios=/iPad|iPhone|iPod/.test(navigator.userAgent||"")||((navigator.platform||"")==="MacIntel"&&navigator.maxTouchPoints>1);if(ios){fb.textContent=it?"Facebook · copia link":"Facebook · copiază linkul";fb.setAttribute("role","button");fb.onclick=async event=>{event.preventDefault();const showInstructions=copied=>{notice.textContent=copied?(it?"Link del contenuto copiato. Apri Facebook, crea un post e tieni premuto nel testo per scegliere Incolla. Attendi l'anteprima, poi premi Pubblica.":"Linkul conținutului a fost copiat. Deschide Facebook, creează o postare și ține apăsat în text pentru a alege Lipește. Așteaptă previzualizarea, apoi apasă Publică."):(it?"Copia il link qui sotto, poi incollalo in un nuovo post Facebook.":"Copiază linkul de mai jos, apoi lipește-l într-o postare nouă pe Facebook.");let field=box.querySelector("[data-facebook-link]");if(!field){field=document.createElement("input");field.type="text";field.readOnly=true;field.value=url;field.setAttribute("data-facebook-link","");field.setAttribute("aria-label",it?"Link del contenuto":"Linkul conținutului");field.onclick=()=>{field.focus();field.select();field.setSelectionRange(0,url.length)};box.append(field)}let open=box.querySelector("[data-facebook-open]");if(!open){open=document.createElement("a");open.setAttribute("data-facebook-open","");open.textContent=it?"Apri Facebook e incolla":"Deschide Facebook și lipește";open.href="https://www.facebook.com/";open.target="_blank";open.rel="noopener noreferrer";box.append(open)}if(!copied){field.focus();field.select();field.setSelectionRange(0,url.length)}};try{await navigator.clipboard.writeText(url);showInstructions(true)}catch(error){showInstructions(false)}}}box.append(fb);const wa=document.createElement("a");wa.textContent="WhatsApp";wa.href="https://api.whatsapp.com/send?text="+encodeURIComponent(title+" "+url);wa.target="_blank";wa.rel="noopener noreferrer";box.append(wa);const copy=document.createElement("button");copy.type="button";copy.textContent=it?"📋 Copia link":"📋 Copiază linkul";copy.onclick=async()=>{try{await navigator.clipboard.writeText(url);notice.textContent=it?"Link copiato. Puoi incollarlo nel post Facebook.":"Link copiat. Îl poți lipi în postarea Facebook."}catch(e){window.prompt(it?"Copia il link dell'articolo":"Copiază linkul conținutului",url)}};box.append(copy);if(navigator.share){const more=document.createElement("button");more.type="button";more.textContent=it?"Altre app…":"Alte aplicații…";more.onclick=async()=>{try{await navigator.share(rdiNativeShareData(url))}catch(e){if(e?.name!=="AbortError")notice.textContent=it?"Scegli Facebook, WhatsApp oppure Copia link.":"Alege Facebook, WhatsApp sau Copiază linkul."}};box.append(more)}const close=document.createElement("button");close.type="button";close.textContent=it?"Chiudi":"Închide";close.onclick=()=>{box.remove();anchor?.focus()};box.append(close);const target=document.getElementById("reader")?.classList.contains("open")?document.getElementById("reader-content"):document.querySelector(".news-section");if(anchor?.parentNode)anchor.after(box);else target?.prepend(box);box.scrollIntoView({behavior:"smooth",block:"nearest"});fb.focus({preventScroll:true})}const rdiShareChecks=new Map();function rdiCheckSharePage(url){const cached=rdiShareChecks.get(url);if(cached&&Date.now()-cached.time<60000)return cached.promise;const promise=(async()=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6000);try{const response=await fetch(url,{cache:"no-store",signal:controller.signal});if(!response.ok)return false;const page=new DOMParser().parseFromString(await response.text(),"text/html");return page.querySelector('meta[property="og:type"]')?.content==="article"&&page.querySelector('meta[property="og:url"]')?.content===url.split("?")[0]}catch(error){return false}finally{clearTimeout(timer)}})();rdiShareChecks.set(url,{time:Date.now(),promise});return promise}
function rdiPrepareShareButton(x,b){const url=rdiShareUrl(x),it=rdiLanguage()==="it";b.disabled=true;b.textContent=it?"Preparazione condivisione…":"Se pregătește distribuirea…";return rdiCheckSharePage(url).then(ready=>{b.disabled=false;b.rdiReadyUrl=ready?url:null;b.textContent=ready?"↗ Distribuie / Condividi":(it?"↻ Riprova condivisione":"↻ Reîncearcă distribuirea");b.setAttribute("aria-label",ready?(it?"Condividi contenuto":"Distribuie conținutul"):(it?"Anteprima in preparazione. Riprova.":"Previzualizare în pregătire. Reîncearcă."));return ready})}
function rdiNativeShareData(url){const ios=/iPad|iPhone|iPod/.test(navigator.userAgent||"")||((navigator.platform||"")==="MacIntel"&&navigator.maxTouchPoints>1);return ios?{text:url}:{url}}
async function rdiShareArticle(x,anchor){document.getElementById("rdi-social-share-actions")?.remove();if(typeof navigator.share==="function"){try{await navigator.share(rdiNativeShareData(rdiShareUrl(x)));return}catch(error){if(error?.name==="AbortError")return;console.warn("Native share unavailable",error)}}return rdiShareArticleFallback(x,anchor)}
function rdiReadableText(x){const summary=String(x.summary||"").trim(),body=String(x.body||"").trim();if(x.extended_summary&&body)return body;return body?(body.startsWith(summary)?body:[summary,body].filter(Boolean).join("\n\n")):summary}
function rdiPostText(x){x=x.eventId?x:rdiTranslated(x);return [x.title,rdiReadableText(x),x.source?"Fonte / Sursa: "+x.source:"",rdiShareUrl(x)].filter(Boolean).join("\n\n")}
function rdiCopyPostButton(x){const b=document.createElement("button");b.type="button";b.className="rdi-share-button";const it=rdiLanguage()==="it";b.textContent=it?"📋 Copia post Facebook":"📋 Copiază postarea Facebook";b.onclick=async()=>{const text=rdiPostText(x);try{await navigator.clipboard.writeText(text);b.textContent=it?"✓ Copiato: incolla nel post Facebook":"✓ Copiat: lipește în postarea Facebook"}catch(error){const area=document.createElement("textarea");area.value=text;area.setAttribute("aria-label",it?"Testo del post da copiare":"Textul postării de copiat");area.style.cssText="display:block;width:100%;min-height:220px;margin:12px 0";const old=b.parentNode.querySelector("textarea");if(old)old.remove();b.after(area);area.focus();area.select();b.textContent=it?"Seleziona e copia il testo qui sotto":"Selectează și copiază textul de mai jos"}};return b}

function rdiFacebookPhotoUrl(x){
  const lang=rdiLanguage();
  const key=String(x.id||x.url||x.title+"|"+x.published);
  const localized=!x.eventId&&typeof rdiTranslations!=="undefined"&&rdiTranslations[key]?.[lang]?.title?"-"+lang:"";
  const ident=x.eventId?"event-"+x.eventId:rdiArticleId(x)+localized;
  return new URL("/share-images/"+ident+"-facebook.jpg",location.href).href;
}
function rdiFacebookPhotoLink(x){
  const it=rdiLanguage()==="it",a=document.createElement("a");
  a.className="rdi-facebook-photo";
  a.textContent=it?"▣ Foto Facebook (1080 × 1350)":"▣ Imagine Facebook (1080 × 1350)";
  a.href=rdiFacebookPhotoUrl(x);
  a.target="_blank";
  a.rel="noopener noreferrer";
  a.setAttribute("aria-label",it?"Apri la foto con il titolo, salvala e pubblicala come immagine su Facebook":"Deschide imaginea cu titlul, salveaz-o și public-o ca fotografie pe Facebook");
  return a;
}
function rdiShareButton(x){
  // Open a lightweight menu only on request; never block Facebook behind a
  // preflight fetch, which can fail or be delayed on iOS even for a valid URL.
  const it=rdiLanguage()==="it",url=rdiShareUrl(x);
  const details=document.createElement("details");
  details.className="rdi-share-menu";
  const toggle=document.createElement("summary");
  toggle.className="rdi-share-toggle";
  toggle.textContent=it?"↗ Condividi":"↗ Distribuie";
  toggle.setAttribute("aria-label",it?"Apri le opzioni di condivisione":"Deschide opțiunile de distribuire");
  const actions=document.createElement("div");
  actions.className="rdi-share-actions";
  const facebook=document.createElement("a");
  facebook.className="rdi-share-facebook";
  facebook.href="https://www.facebook.com/sharer/sharer.php?u="+encodeURIComponent(url);
  facebook.target="_blank";
  facebook.rel="noopener noreferrer";
  facebook.textContent="Facebook ↗";
  actions.append(facebook);
  const status=document.createElement("span");
  status.className="rdi-share-feedback";
  status.setAttribute("role","status");
  status.setAttribute("aria-live","polite");
  const makeCopy=(label,value,message)=>{
    const button=document.createElement("button");
    button.type="button";
    button.className="rdi-share-small";
    button.textContent=label;
    button.onclick=async()=>{
      try{
        await navigator.clipboard.writeText(value());
        status.textContent=message;
      }catch(error){
        // Explicit manual copy path for Safari/PWA restrictions.
        window.prompt(it?"Copia e incolla su Facebook":"Copiază și lipește pe Facebook",value());
        status.textContent=it?"Seleziona il contenuto e copialo.":"Selectează conținutul și copiază-l.";
      }
    };
    return button;
  };
  actions.append(makeCopy(it?"Copia link":"Copiază link",()=>url,it?"Link copiato: incollalo nel post Facebook.":"Link copiat: lipește-l într-o postare Facebook."));
  actions.append(makeCopy(it?"Copia testo":"Copiază textul",()=>rdiPostText(x),it?"Testo copiato: incollalo nel post Facebook.":"Text copiat: lipește-l în postarea Facebook."));
  if(typeof navigator.share==="function"){
    const native=document.createElement("button");
    native.type="button";
    native.className="rdi-share-small";
    native.textContent=it?"Altre app…":"Alte aplicații…";
    native.onclick=async()=>{
      try{await navigator.share({url})}
      catch(error){if(error?.name!=="AbortError")status.textContent=it?"Usa Facebook o Copia link.":"Folosește Facebook sau Copiază link."}
    };
    actions.append(native);
  }
  const photo=rdiFacebookPhotoLink(x);
  photo.textContent=it?"Foto per Facebook ↗":"Imagine pentru Facebook ↗";
  actions.append(photo,status);
  details.append(toggle,actions);
  return details;
}
