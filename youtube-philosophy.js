/* Daily RDI philosophy: same dated photograph and original reflection as website. */
import {shouldShow} from "./youtube-philosophy-core.mjs";
(()=>{
"use strict";
const stage=document.getElementById("stage");if(!stage)return;
const layer=document.createElement("section");layer.id="rdiPhilosophy";layer.hidden=true;layer.setAttribute("aria-label","Calendario Filosofico RDI");
layer.innerHTML='<div class="rdi-philosophy-photo"></div><div class="rdi-philosophy-shade"></div><div class="rdi-philosophy-copy"><p class="rdi-philosophy-brand">RADIO ROMÂNII DIN ITALIA</p><p class="rdi-philosophy-heading">CALENDARIO FILOSOFICO</p><p class="rdi-philosophy-date"></p><blockquote class="rdi-philosophy-quote"></blockquote><p class="rdi-philosophy-credit">Riflessione originale RDI</p></div><div class="rdi-philosophy-progress"></div>';
stage.append(layer);
const photo=layer.querySelector(".rdi-philosophy-photo"),quote=layer.querySelector(".rdi-philosophy-quote"),date=layer.querySelector(".rdi-philosophy-date"),progress=layer.querySelector(".rdi-philosophy-progress");
let days=[],current=null,readyImage="",active=false,done=null,timeout=null,watch=null,lastShownAt=0,cards=0;
const today=()=>new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
const blocked=()=>["rdiSpotActive","rdiGeoActive","rdiTgActive","rdiWeatherActive","rdiCameraActive","rdiLandscapeActive","rdiDjPromoActive"].some(k=>window[k]);
const preview=new URLSearchParams(location.search).get("rdi_philosophy_preview")==="1";
function dayData(){return current&&current.date===today()?current:null}
function paint(item){
 if(!item)return false;
 quote.textContent=item.quote;
 date.textContent=new Intl.DateTimeFormat("it-IT",{year:"numeric",month:"long",day:"numeric",timeZone:"UTC"}).format(new Date(item.date+"T12:00:00Z"));
 // Image is already hosted by RDI. Escape URL before using a CSS property.
 const url=String(item.image||"");
 if(!/^\/(?!\/)[a-zA-Z0-9/_-]+\.(jpg|jpeg|webp|png)$/i.test(url))return false;
 photo.style.backgroundImage='url("'+url+'")';
 return true;
}
function end(resume=true){
 if(!active)return;
 active=false;window.rdiPhilosophyActive=false;layer.hidden=true;
 clearTimeout(timeout);clearInterval(watch);
 const cb=done;done=null;
 if(resume&&typeof cb==="function"){
  if(!blocked())cb();
  else{
   const gate=setInterval(()=>{if(!blocked()){clearInterval(gate);cb()}},500);
   setTimeout(()=>clearInterval(gate),120000);
  }
 }
}
function startIfDue(next){
 if(active||blocked()||!days.length||typeof next!=="function")return false;
 cards++;
 if(!shouldShow({cards,lastShownAt,now:Date.now()}))return false;
 const item=dayData();
 if(!item||!paint(item))return false;
 if(readyImage!==item.image)return false;
 active=true;window.rdiPhilosophyActive=true;lastShownAt=Date.now();cards=0;done=next;
 window.rdiPauseNews?.();
 layer.hidden=false;progress.style.transition="none";progress.style.width="0%";
 requestAnimationFrame(()=>requestAnimationFrame(()=>{progress.style.transition="width 18000ms linear";progress.style.width="100%";}));
 timeout=setTimeout(()=>end(true),18000);
 watch=setInterval(()=>{if(blocked())end(false)},350);
 return true;
}
async function update(){
 try{
  const response=await fetch("./data/daily-thought.json?v="+Date.now(),{cache:"no-store"});
  const archive=response.ok?await response.json():null;
  const item=Array.isArray(archive?.items)?archive.items.find(x=>x.date===today()&&typeof x.summary==="string"&&typeof x.image==="string"):null;
  current=item?{date:item.date,quote:item.summary,image:item.image}:null;
  days=[];
  const item=dayData();
  if(!item){readyImage="";return}
  const url=String(item.image||"");
  if(!/^(?:\\/(?!\\/)|\\.\\/(?!\\/))[a-zA-Z0-9/_-]+[.](jpg|jpeg|webp|png|svg)$/i.test(url)){readyImage="";return;}
  const preload=new Image();
  preload.onload=()=>{if(dayData()?.image===url){readyImage=url;if(preview&&paint(dayData()))layer.hidden=false}};
  preload.onerror=()=>{if(readyImage===url)readyImage=""};
  preload.src=url;
 }catch(e){console.warn("RDI philosophy unavailable",e)}
}

window.rdiPhilosophyBreak={startIfDue,stop:()=>end(false),get state(){return {active,date:today(),loaded:days.length}}};
update();setInterval(update,15*60*1000);
})();
