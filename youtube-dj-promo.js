// RDI: silent 16:9 promotional interlude between news cards, never audio.
import {validRules,eligible,priorityBlocked} from "./youtube-dj-promo-core.mjs";
(()=>{
"use strict";
const stage=document.getElementById("stage");
if(!stage)return;
const layer=document.createElement("section");
layer.id="rdiDjPromo";
layer.hidden=true;
layer.setAttribute("aria-label","Radio Românii din Italia: anteprima fasce musicali");
const image=document.createElement("img");
image.alt="Programmazione oraria musicale RDI: relax, risveglio, urban e pop, energia, melodie, relax. Anteprima.";
image.src="./editorial-images/rdi-dj-programmazione-live.svg";
image.decoding="async";
const progress=document.createElement("div");
progress.className="rdi-dj-promo-progress";
layer.append(image,progress);
stage.append(layer);
let config=validRules({enabled:false});
let active=false,lastShownAt=null,cardsSince=0,callback=null,finishTimer=null,
  priorityWatch=null,generation=0,preloaded=false;
const isBlocked=()=>priorityBlocked(window);
const preview=new URLSearchParams(location.search).get("rdi_dj_promo_preview")==="1";
function updateProgress(){
 progress.style.transition="none";progress.style.width="0%";
 requestAnimationFrame(()=>requestAnimationFrame(()=>{
  if(active){
   progress.style.transition="width "+config.durationSeconds*1000+"ms linear";
   progress.style.width="100%";
  }
 }));
}
function end(resume=true){
 if(!active)return;
 const next=callback;callback=null;
 clearTimeout(finishTimer);clearInterval(priorityWatch);
 finishTimer=priorityWatch=null;
 active=false;window.rdiDjPromoActive=false;
 layer.hidden=true;document.body.classList.remove("rdi-dj-promo-active");
 progress.style.transition="none";progress.style.width="0%";
 if(resume&&typeof next==="function"&&!isBlocked())next();
 else if(resume&&typeof next==="function"){
  // A high-priority broadcast overlay owns the screen. Resume as soon as
  // it finishes; no second concurrent news timeline.
  const ticket=++generation;
  const check=setInterval(()=>{
    if(ticket!==generation){clearInterval(check);return;}
    if(!isBlocked()){
      clearInterval(check);next();
    }
  },500);
  setTimeout(()=>{if(ticket===generation)clearInterval(check);},120000);
 }
}
function startIfDue(next){
 if(active||isBlocked()||typeof next!=="function")return false;
 const now=Date.now();
 cardsSince++;
 if(!eligible({rules:config,cardsSince,lastShownAt,now,blocked:false}))return false;
 if(!preloaded||!image.complete||image.naturalWidth===0)return false;
 lastShownAt=now;cardsSince=0;callback=next;active=true;
 window.rdiDjPromoActive=true;
 window.rdiPauseNews?.();
 layer.hidden=false;document.body.classList.add("rdi-dj-promo-active");
 updateProgress();
 finishTimer=setTimeout(()=>end(true),config.durationSeconds*1000);
 priorityWatch=setInterval(()=>{if(isBlocked())end(false)},350);
 return true;
}
async function loadConfig(){
 try{
  const r=await fetch("./data/youtube-dj-promo.json?ts="+Date.now(),{
   cache:"no-store",signal:AbortSignal.timeout(6000)});
  if(!r.ok)throw new Error("configuration not published");
  const data=await r.json();
  config=validRules(data);
 }catch(e){
  // Fail closed if configuration is unavailable; never interrupt news.
  config=validRules({enabled:false});
 }
}
image.addEventListener("load",()=>{preloaded=true});
image.addEventListener("error",()=>{preloaded=false;end(false)});
window.rdiDjPromoBreak={startIfDue,stop:()=>end(false),
 get state(){return {active,cardsSince,lastShownAt,config,preloaded}}};
const ready=loadConfig();
setInterval(loadConfig,300000);
if(preview)ready.then(()=>{
 if(isBlocked())return;
 config={...config,enabled:true,durationSeconds:60,everyNewsCards:1};
 cardsSince=1;
 startIfDue(()=>{});
});
})();
