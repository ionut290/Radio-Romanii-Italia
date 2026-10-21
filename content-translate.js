(()=>{"use strict";
const locale=()=>{const v=localStorage.getItem("rdi-language")||"ro";return ["ro","it","en"].includes(v)?v:"ro"};
const caption={ro:"🌐 Tradu textul",it:"🌐 Traduci testo",en:"🌐 Translate text"};
function add(buttonHost,source,extract){
 if(!buttonHost||buttonHost.querySelector("[data-rdi-translate]"))return;
 const text=extract();if(!text||text.trim().length<5)return;
 const a=document.createElement("a");a.dataset.rdiTranslate="1";
 a.target="_blank";a.rel="noopener noreferrer";a.style.cssText="display:inline-block;margin:8px 6px 8px 0;padding:7px 12px;border-radius:9px;background:#e8edf4;color:#17334a;text-decoration:none;font:600 13px system-ui,sans-serif";
 a.textContent=caption[locale()];
 const set=()=>{const lang=locale();a.textContent=caption[lang];const value=extract().trim().slice(0,4000);a.href="https://translate.google.com/?sl=auto&tl="+encodeURIComponent(lang)+"&text="+encodeURIComponent(value)+"&op=translate";a.title=lang==="ro"?"Deschide în Google Traducere":lang==="it"?"Apri in Google Traduttore":"Open in Google Translate"};
 a.addEventListener("click",set);set();buttonHost.append(a);
}
function refresh(){
 const page=location.pathname;
 if(page.endsWith("ghid.html"))for(const card of document.querySelectorAll(".business")){const p=card.querySelector("p:not(.muted)");if(p)add(card,p,()=>[card.querySelector("h3")?.textContent,p.textContent].filter(Boolean).join("\n\n"))}
 if(page.endsWith("index.html")||page==="/")for(const card of document.querySelectorAll(".news-item")){const title=card.querySelector("h3"),summary=card.querySelector(".news-summary");if(title||summary)add(card,title||summary,()=>[title?.textContent,summary?.textContent].filter(Boolean).join("\n\n"))}
 for(const article of document.querySelectorAll(".post")){const title=article.querySelector("h3"),body=article.querySelector(".post-full-body")||article.querySelector("p");if(title||body)add(article,title||body,()=>[title?.textContent,body?.textContent].filter(Boolean).join("\n\n"))}
}
let scheduled=false;function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;refresh()})}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
function start(){refresh();new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});window.addEventListener("storage",schedule)}
})();