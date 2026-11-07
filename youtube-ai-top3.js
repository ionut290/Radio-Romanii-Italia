/* RDI AI MUSIC Top 3: graphics synchronized to the ACTUAL AzuraCast show.
 * No sound comes from this browser. The live YouTube relay uses the AzuraCast stream.
 * The old fixed-time visual countdown must NEVER play over unrelated radio music.
 */
import {rankedTop3,normalizeSong} from "./youtube-ai-top3-core.mjs?v=audio-only-20261107";
(()=>{
"use strict";
const stage=document.getElementById("stage");
if(!stage || window.rdiTop3Break)return;
const preview=new URLSearchParams(location.search).get("rdi_top3_preview")==="1";
const API="https://radio-romanii-italia.duckdns.org/api/ai-music";
const NP="https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia";
const layer=document.createElement("section");
layer.id="rdiTop3TV";layer.hidden=true;
layer.setAttribute("aria-label","RDI AI MUSIC Top 3, sincronizzata alla trasmissione radiofonica");
layer.innerHTML=`
 <header class="rdi-top3-header">
  <span class="rdi-top3-brand"><img src="./RADIO-LOGO.png" alt=""> RDI AI MUSIC</span>
  <span class="rdi-top3-live">TOP 3 DEL GIORNO · IN DIRETTA</span>
 </header>
 <div class="rdi-top3-main">
  <div class="rdi-top3-rank"><div class="rdi-top3-medal"></div><div class="rdi-top3-rank-label"></div></div>
  <div class="rdi-top3-main-copy">
   <div class="rdi-top3-kicker"></div><h2 class="rdi-top3-title"></h2>
   <p class="rdi-top3-artist"></p><div class="rdi-top3-votes"></div>
   <div class="rdi-top3-stack"></div>
  </div>
 </div>
 <footer class="rdi-top3-footer">
  <strong class="rdi-top3-link">radioromanii.duckdns.org/spotlight-ai.html</strong>
  <span class="rdi-top3-audio"></span><span class="rdi-top3-progress"></span>
 </footer>`;
stage.append(layer);
const el=q=>layer.querySelector(q);
let manifest=null,active=false,previousStage="",isFetching=false,previewTimer=null;
const blocking=()=>[
  "rdiSpotActive","rdiGeoActive","rdiTgActive","rdiWeatherActive",
  "rdiCameraActive","rdiLandscapeActive","rdiDjPromoActive",
  "rdiPhilosophyActive","rdiStoriaActive","rdiListenerMediaActive",
  "rdiListenerMessageActive"
].some(k=>Boolean(window[k]));
function text(selector,value){el(selector).textContent=String(value??"")}
function present(stageSegment,elapsed,duration){
 const introductory=!stageSegment;
 const rank=stageSegment?.rank;
 layer.classList.toggle("rdi-top3-intro",introductory);
 const medal=el(".rdi-top3-medal");
 medal.classList.toggle("gold",rank===1);
 medal.textContent=introductory?"TOP":"#"+rank;
 text(".rdi-top3-rank-label",introductory?"ERRE DI I AI MUSIC":rank===1?"PRIMO POSTO":rank===2?"SECONDO POSTO":"TERZO POSTO");
 text(".rdi-top3-kicker",introductory?"CLASSIFICA SCELTA DALLA COMMUNITY":"POSIZIONE NUMERO "+rank+" · TOP 3");
 text(".rdi-top3-title",introductory?"Le tre canzoni più votate":stageSegment.title);
 text(".rdi-top3-artist",introductory?"Un nuovo palcoscenico per gli artisti AI":stageSegment.artist);
 text(".rdi-top3-votes",introductory?"Ascolta le nuove canzoni su RDI AI MUSIC":stageSegment.votes+" "+(stageSegment.votes===1?"voto":"voti")+" · classifica della community");
 const stack=el(".rdi-top3-stack");stack.replaceChildren();
 for(const item of manifest?.segments||[]){
   const chip=document.createElement("span");
   chip.className="rdi-top3-chip"+(rank===item.rank?" current":"");
   chip.textContent="#"+item.rank+" "+item.title;stack.append(chip);
 }
 text(".rdi-top3-audio",preview?"Anteprima grafica · audio non incluso":
       stageSegment?(elapsed<stageSegment.music_start?"♫ Presentazione del brano":"♪ In onda: "+stageSegment.artist+" — "+stageSegment.title):
       "♫ In onda: RDI AI MUSIC Top 3");
 const portion=Number.isFinite(duration)&&duration>0?Math.min(100,Math.max(0,100*elapsed/duration)):0;
 el(".rdi-top3-progress").style.transition="width .4s linear";
 el(".rdi-top3-progress").style.width=portion+"%";
}
function stop(){
 if(!active)return;active=false;layer.hidden=true;window.rdiTop3Active=false;previousStage="";
 window.rdiResumeNews?.();
}
function show(segment,elapsed,duration){
 if(blocking()){if(active){layer.hidden=true;window.rdiTop3Active=false}return}
 if(!active){active=true;window.rdiTop3Active=true;window.rdiPauseNews?.()}
 else if(layer.hidden){layer.hidden=false;window.rdiTop3Active=true}
 layer.hidden=false;
 const key=segment?String(segment.id)+":"+segment.rank:"intro";
 if(key!==previousStage || elapsed%2<1)present(segment,elapsed,duration);
 previousStage=key;
}
async function getJSON(url){
 const response=await fetch(url+(url.includes("?")?"&":"?")+"_="+Date.now(),
   {cache:"no-store",signal:AbortSignal.timeout(6500)});
 if(!response.ok)throw Error("HTTP "+response.status);
 return response.json();
}
async function checkOnAir(){
 if(preview||isFetching)return;
 isFetching=true;
 try{
   if(!manifest?.ready)return stop();
   const np=await getJSON(NP);
   const played=np?.now_playing||{};
   const title=normalizeSong(played.song?.title);
   if(!title || title!==normalizeSong(manifest.track_title))return stop();
   const elapsed=Number(played.elapsed);
   if(!Number.isFinite(elapsed)||elapsed<0)return stop();
   const duration=Number(manifest.duration_seconds);
   if(elapsed>duration+10)return stop();
   const segment=manifest.segments.find(s=>elapsed>=s.start&&elapsed<s.end);
   show(segment,elapsed,duration);
 }catch(e){console.warn("RDI Top 3 metadata temporarily unavailable:",e)}
 finally{isFetching=false}
}
async function refreshManifest(){
 if(preview)return;
 try{
   const data=await getJSON(API+"/top3/live");
   if(data.ready&&Array.isArray(data.segments)&&data.segments.length===3&&
      data.segments.map(x=>x.rank).join(",")==="3,2,1"){
     manifest=data;
   }else{manifest=null;stop()}
 }catch(e){console.warn("RDI Top3 timing not ready:",e)}
}
async function previewDisplay(){
 try{
   const data=await getJSON(API+"/spotlight?page=1");
   const rows=rankedTop3(data);
   if(rows.length!==3)return;
   manifest={ready:true,duration_seconds:45,segments:[
     { ...rows[2],start:5,music_start:8,end:18 },
     { ...rows[1],start:18,music_start:21,end:31 },
     { ...rows[0],start:31,music_start:34,end:45 }
   ]};
   const started=Date.now();
   const tick=()=>{
     const t=(Date.now()-started)/1000;
     if(t>=45){stop();clearInterval(previewTimer);previewTimer=null;return}
     const seg=manifest.segments.find(s=>t>=s.start&&t<s.end);
     show(seg,t,45);
   };
   tick();previewTimer=setInterval(tick,500);
 }catch(e){console.warn("RDI Top3 preview not ready",e)}
}
window.rdiTop3Break={
  // Legacy news scheduler may call this; deliberately refuse unsynchronized visuals.
  startIfDue:()=>false,
  stop, get state(){return{active,ready:Boolean(manifest),preview,
    tracks:manifest?.segments?.length||0}}
};
if(preview)previewDisplay();
else{
 refreshManifest().then(checkOnAir);
 setInterval(refreshManifest,30_000);
 setInterval(checkOnAir,2500);
}
})();