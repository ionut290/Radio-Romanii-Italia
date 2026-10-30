/* RDI Calendario Filosofico: visual break, original text, no audio or third-party images. */
import {calendarCard,shouldShow} from "./youtube-philosophy-core.mjs";
(()=>{
"use strict";
const stage=document.getElementById("stage");
if(!stage)return;
const shell=document.createElement("section");
shell.id="rdiPhilosophy";shell.hidden=true;
shell.setAttribute("aria-label","Calendario filosofico quotidiano RDI");
shell.innerHTML='<div class="rdi-philosophy-art" aria-hidden="true"><span class="rdi-philosophy-orbit"></span><span class="rdi-philosophy-sun"></span><span class="rdi-philosophy-mountain"></span></div><div class="rdi-philosophy-copy"><p class="rdi-philosophy-eyebrow">RADIO ROMÂNII DIN ITALIA · CALENDARIO FILOSOFICO</p><p class="rdi-philosophy-date"></p><blockquote class="rdi-philosophy-quote"></blockquote><p class="rdi-philosophy-credit">Riflessione originale RDI · Un pensiero per oggi</p></div><div class="rdi-philosophy-progress"></div>';
stage.append(shell);
const text=shell.querySelector(".rdi-philosophy-quote"),date=shell.querySelector(".rdi-philosophy-date");
const progress=shell.querySelector(".rdi-philosophy-progress");
let active=false,done=null,timer=null,watch=null,lastShownAt=0,cards=0,seq=0;
const blocked=()=>["rdiSpotActive","rdiGeoActive","rdiTgActive","rdiWeatherActive","rdiCameraActive","rdiLandscapeActive","rdiDjPromoActive"].some(k=>window[k]);
function finish(resume=true){
 if(!active)return;
 active=false;window.rdiPhilosophyActive=false;shell.hidden=true;document.body.classList.remove("rdi-philosophy-active");
 clearTimeout(timer);clearInterval(watch);timer=watch=null;
 const cb=done;done=null;
 if(resume&&typeof cb==="function"){
   if(!blocked())cb();
   else{
     const ticket=++seq;
     const gate=setInterval(()=>{if(ticket!==seq){clearInterval(gate);return;}if(!blocked()){clearInterval(gate);cb();}},500);
     setTimeout(()=>clearInterval(gate),120000);
   }
 }
}
function startIfDue(next){
 if(active||blocked()||typeof next!=="function")return false;
 cards++;
 if(!shouldShow({cards,lastShownAt,now:Date.now()}))return false;
 const item=calendarCard(new Date());
 if(!item)return false;
 text.textContent=item.quote;date.textContent=item.dateLabel;
 shell.style.setProperty("--ph-hue",String(item.hue));
 shell.style.setProperty("--ph-sun-x",String(item.sunX)+"%");
 lastShownAt=Date.now();cards=0;done=next;active=true;window.rdiPhilosophyActive=true;
 window.rdiPauseNews?.();
 shell.hidden=false;document.body.classList.add("rdi-philosophy-active");
 progress.style.transition="none";progress.style.width="0%";
 requestAnimationFrame(()=>requestAnimationFrame(()=>{if(active){progress.style.transition="width 18000ms linear";progress.style.width="100%";}}));
 timer=setTimeout(()=>finish(true),18000);
 watch=setInterval(()=>{if(blocked())finish(false)},350);
 return true;
}
window.rdiPhilosophyBreak={startIfDue,stop:()=>finish(false),get state(){return {active,cards,lastShownAt}}};
const preview=new URLSearchParams(location.search).get("rdi_philosophy_preview")==="1";
if(preview){
 const item=calendarCard(new Date());text.textContent=item.quote;date.textContent=item.dateLabel;
 shell.style.setProperty("--ph-hue",String(item.hue));shell.style.setProperty("--ph-sun-x",String(item.sunX)+"%");
 shell.hidden=false;
}
})();
