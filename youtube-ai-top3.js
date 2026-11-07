/* RDI AI MUSIC Top 3 for YouTube: visuals only.
 * YouTube relay takes AUDIO from AzuraCast, never this browser. Do not claim
 * an RDI Spotlight track is being heard unless confirmed by real now-playing.
 */
import {rankedTop3,due,romeClock,onAirRank} from "./youtube-ai-top3-core.mjs";
(()=>{
"use strict";
const stage=document.getElementById("stage");
if(!stage)return;
const preview=new URLSearchParams(location.search).get("rdi_top3_preview")==="1";
const DAY_KEY="rdi-ai-top3-last-live-day-v1";
const API="https://radio-romanii-italia.duckdns.org/api/ai-music/spotlight?page=1";
const NP="https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia";
const layer=document.createElement("section");
layer.id="rdiTop3TV";layer.hidden=true;layer.setAttribute("aria-label","RDI AI MUSIC: classifica Top 3 della community");
layer.innerHTML=`
 <header class="rdi-top3-header">
  <span class="rdi-top3-brand"><img src="./RADIO-LOGO.png" alt=""> RDI AI MUSIC</span>
  <span class="rdi-top3-live">CLASSIFICA DEL GIORNO · TOP 3</span>
 </header>
 <div class="rdi-top3-main">
  <div class="rdi-top3-rank"><div class="rdi-top3-medal"></div><div class="rdi-top3-rank-label"></div></div>
  <div class="rdi-top3-main-copy">
   <div class="rdi-top3-kicker"></div>
   <h2 class="rdi-top3-title"></h2>
   <p class="rdi-top3-artist"></p>
   <div class="rdi-top3-votes"></div>
   <div class="rdi-top3-stack"></div>
  </div>
 </div>
 <footer class="rdi-top3-footer">
  <strong class="rdi-top3-link">radioromanii.duckdns.org/spotlight-ai.html</strong>
  <span class="rdi-top3-audio">In onda: Radio RDI · Ascolta i brani anche sul sito</span>
  <span class="rdi-top3-progress"></span>
 </footer>`;
stage.append(layer);
const el=q=>layer.querySelector(q);
let top=[],fetchedDay="",active=false,callback=null,timers=[],watch=null,lastRunDay="",editionDay="";
let lastNowPlaying=null;
try{lastRunDay=localStorage.getItem(DAY_KEY)||""}catch{}
const blocking=()=>[
 "rdiSpotActive","rdiGeoActive","rdiTgActive","rdiWeatherActive",
 "rdiCameraActive","rdiLandscapeActive","rdiDjPromoActive",
 "rdiPhilosophyActive","rdiStoriaActive","rdiListenerMediaActive",
 "rdiListenerMessageActive"
].some(k=>window[k]);
function text(selector,value){el(selector).textContent=String(value||"")}
function setAudioStatus(){
 const found=onAirRank(lastNowPlaying,top);
 text(".rdi-top3-audio",found?"♪ In radio adesso: "+found.artist+" — "+found.title:
 "♪ Audio della diretta da AzuraCast · Ascolta i brani anche su RDI AI MUSIC");
}
function draw(index){
 const intro=index<0;
 layer.classList.toggle("rdi-top3-intro",intro);
 const rank=intro?null:top[index];
 const medal=el(".rdi-top3-medal");
 medal.classList.toggle("gold",rank?.rank===1);
 medal.textContent=intro?"TOP":"#"+rank.rank;
 text(".rdi-top3-rank-label",intro?"LA COMMUNITY SCEGLIE":rank.rank===1?"PRIMO POSTO":rank.rank===2?"SECONDO POSTO":"TERZO POSTO");
 text(".rdi-top3-kicker",intro?"OGGI SU RDI AI MUSIC":"POSIZIONE NUMERO "+rank.rank+" · TOP 3");
 text(".rdi-top3-title",intro?"Le tre canzoni più votate":rank.title);
 text(".rdi-top3-artist",intro?"Scopri la classifica della community":rank.artist);
 text(".rdi-top3-votes",intro?"Scopri il podio aggiornato oggi":rank.votes+" "+(rank.votes===1?"voto":"voti")+" · classifica pubblica");
 const stack=el(".rdi-top3-stack");stack.replaceChildren();
 for(const r of [top[2],top[1],top[0]]){
  const chip=document.createElement("span");chip.className="rdi-top3-chip"+(rank?.id===r.id?" current":"");
  chip.textContent="#"+r.rank+" "+r.title;
  stack.append(chip);
 }
 setAudioStatus();
}
function cleanup(){
 timers.forEach(clearTimeout);timers=[];if(watch){clearInterval(watch);watch=null}
 active=false;window.rdiTop3Active=false;layer.hidden=true;callback=null;
}
function stop(completed=false){
 const done=callback;
 if(completed&&!preview&&editionDay){lastRunDay=editionDay;try{localStorage.setItem(DAY_KEY,lastRunDay)}catch{}}
 cleanup();
 if(typeof done==="function")done();
}
async function nowPlaying(){
 try{const response=await fetch(NP+"?ts="+Date.now(),{cache:"no-store",signal:AbortSignal.timeout(5000)});
 if(response.ok){lastNowPlaying=await response.json();if(active)setAudioStatus()}}
 catch{ /* Last checked broadcast identity stays visible. */ }
}
function run(next){
 if(active||top.length!==3||blocking())return false;
 editionDay=romeClock(new Date())?.day||"";
 callback=next;active=true;window.rdiTop3Active=true;window.rdiPauseNews?.();
 layer.hidden=false;draw(-1);nowPlaying();
 // 5s intro, then #3, #2, #1 (13 seconds each); 45 seconds total.
 const sequence=[{at:5000,index:2},{at:18000,index:1},{at:31000,index:0}];
 for(const item of sequence)timers.push(setTimeout(()=>{if(active)draw(item.index)},item.at));
 const bar=el(".rdi-top3-progress");bar.style.transition="none";bar.style.width="0%";
 requestAnimationFrame(()=>requestAnimationFrame(()=>{if(active){bar.style.transition="width 45000ms linear";bar.style.width="100%"}}));
 timers.push(setTimeout(()=>stop(true),45000));
 watch=setInterval(()=>{if(active&&blocking())stop(false)},500);
 return true;
}
function startIfDue(next){
 if(active||typeof next!=="function"||blocking())return false;
 if(!due({now:new Date(),shownDay:lastRunDay,tracks:top,preview:false,enabled:true}))return false;
 return run(next);
}
async function refresh(){
 const today=romeClock(new Date())?.day;
 if(!today)return;
 try{
  const response=await fetch(API+"&ts="+Date.now(),{cache:"no-store",signal:AbortSignal.timeout(8000)});
  if(!response.ok)throw Error("RDI chart unavailable");
  const tracks=rankedTop3(await response.json());
  if(tracks.length!==3){top=[];return}
  top=tracks;fetchedDay=today;
  if(preview&&!active)timers.push(setTimeout(()=>{if(!active)run(null)},1200));
 }catch(e){console.warn("RDI AI MUSIC Top 3 not ready; news continues.",e)}
}
window.rdiTop3Break={startIfDue,stop:()=>stop(false),get state(){return{active,loaded:top.length,day:fetchedDay,lastRunDay}}};
window.addEventListener("rdi:nowplaying",event=>{lastNowPlaying=event.detail;if(active)setAudioStatus()});
refresh();setInterval(refresh,120000);setInterval(()=>{if(active)nowPlaying()},10000);
})();
