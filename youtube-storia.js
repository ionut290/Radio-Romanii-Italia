/* RDI STORIA: a short historical interlude inside the YouTube news rotation.
   Visual-only. No audio changes, no AzuraCast access, no streaming restart. */
import {validStoriaDay,storyDue} from "./youtube-storia-core.mjs";

(()=>{
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;
  const layer=document.createElement("section");
  layer.id="rdiStoriaTV";
  layer.hidden=true;
  layer.setAttribute("aria-label","RDI STORIA, accadde oggi nella storia");
  layer.innerHTML=
    '<div class="rdi-storia-top"><div class="rdi-storia-brand"><img src="./RADIO-LOGO.png" alt=""><span>RADIO ROMÂNII DIN ITALIA</span></div><span class="rdi-storia-label">RDI STORIA · ACCADDE OGGI</span></div>'+
    '<div class="rdi-storia-stage"><div class="rdi-storia-image-wrap"><div class="rdi-storia-image-fallback"><span>RDI</span><strong>STORIA</strong><i>⌛</i></div><img class="rdi-storia-image" alt="" hidden><div class="rdi-storia-image-caption">ARCHIVIO STORICO · RDI</div></div>'+
    '<div class="rdi-storia-story"><div class="rdi-storia-dateline"></div><div class="rdi-storia-year"></div><div class="rdi-storia-heading"></div><div class="rdi-storia-summary"></div><div class="rdi-storia-attribution"></div></div></div>'+
    '<div class="rdi-storia-bottom"><span>📜 MEMORIA · CULTURA · ISTORIE</span><span>RADIOROMANII.DUCKDNS.ORG/STORIA.HTML</span></div>'+
    '<div class="rdi-storia-progress"></div>';
  stage.append(layer);
  const find=s=>layer.querySelector(s);
  const image=find(".rdi-storia-image"),progress=find(".rdi-storia-progress");
  const duration=19000;
  const preview=new URLSearchParams(location.search).get("rdi_storia_preview")==="1";
  const fmtDay=new Intl.DateTimeFormat("it-IT",{timeZone:"UTC",day:"numeric",month:"long",year:"numeric"});
  const romeDay=()=>new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  const blocked=()=>[
    "rdiSpotActive","rdiGeoActive","rdiTgActive","rdiWeatherActive",
    "rdiCameraActive","rdiLandscapeActive","rdiDjPromoActive",
    "rdiPhilosophyActive","rdiListenerMediaActive","rdiListenerMessageActive"
  ].some(key=>window[key]);
  let day="",events=[],nextEvent=0,cards=0,lastShownAt=0,active=false;
  let finishCallback=null,timeout=null,watch=null,revision=0,readyPictures=new Set();

  function draw(event){
    const today=romeDay();
    find(".rdi-storia-dateline").textContent="ASTĂZI · "+fmtDay.format(new Date(today+"T12:00:00Z"));
    find(".rdi-storia-year").textContent=String(event.year);
    find(".rdi-storia-heading").textContent=event.title;
    find(".rdi-storia-summary").textContent=event.summary;
    const lang=event.language==="ro"?"ROMÂNĂ":event.language==="en"?"ENGLISH":"ITALIANO";
    const credit=[event.credit,event.license].filter(Boolean).join(" · ");
    find(".rdi-storia-attribution").textContent=lang+" · "+(credit||"Immagine illustrativa RDI");
    image.hidden=true;image.removeAttribute("src");
    const url=event.image;
    if(url&&readyPictures.has(url)){
      image.src=url;image.alt=event.title;image.hidden=false;
      image.onerror=()=>{image.hidden=true;image.removeAttribute("src");};
      find(".rdi-storia-image-caption").textContent="FOTO · "+(event.license||"WIKIMEDIA COMMONS");
    }else{
      find(".rdi-storia-image-caption").textContent="RDI STORIA · GRAFICA ILLUSTRATIVA";
    }
  }
  function stop(resume=false){
    if(!active)return;
    clearTimeout(timeout);clearInterval(watch);
    timeout=watch=null;
    const cb=finishCallback;finishCallback=null;
    active=false;window.rdiStoriaActive=false;
    layer.hidden=true;
    progress.style.transition="none";progress.style.width="0%";
    if(resume && !blocked() && typeof cb==="function")cb();
  }
  function run(event,callback){
    if(active||blocked())return false;
    draw(event);
    active=true;window.rdiStoriaActive=true;finishCallback=callback;
    window.rdiPauseNews?.();
    layer.hidden=false;
    progress.style.transition="none";progress.style.width="0%";
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(!active)return;
      progress.style.transition="width "+duration+"ms linear";
      progress.style.width="100%";
    }));
    timeout=setTimeout(()=>stop(true),duration);
    watch=setInterval(()=>{if(blocked())stop(false)},400);
    return true;
  }
  function startIfDue(next){
    if(active||blocked()||!events.length||day!==romeDay()||typeof next!=="function")return false;
    cards++;
    if(!storyDue({cards,lastShownAt,now:Date.now()}))return false;
    const event=events[nextEvent%events.length];
    if(!run(event,next))return false;
    nextEvent=(nextEvent+1)%events.length;
    lastShownAt=Date.now();
    cards=0;
    return true;
  }
  async function update(){
    const requestId=++revision,today=romeDay();
    try{
      const res=await fetch("./data/storia-oggi.json?ts="+Date.now(),{
        cache:"no-store",signal:AbortSignal.timeout(8000)
      });
      if(!res.ok)throw Error("RDI STORIA "+res.status);
      const raw=await res.json();
      const entries=validStoriaDay(raw,today);
      if(requestId!==revision)return;
      if(!entries.length){day="";events=[];readyPictures.clear();return}
      if(day!==today){nextEvent=0;cards=0;lastShownAt=0;readyPictures.clear()}
      day=today;events=entries;
      for(const item of entries){
        const url=item.image;
        if(!url||readyPictures.has(url))continue;
        const pre=new Image();
        pre.onload=()=>{if(day===today)readyPictures.add(url)};
        pre.onerror=()=>{readyPictures.delete(url)};
        pre.src=url;
      }
      if(preview&&!active){
        const first=events[0];
        // Visual inspection only; does not enter the normal news scheduler.
        setTimeout(()=>{if(!active&&events.length&&day===romeDay())run(first,null)},650);
      }
    }catch(err){
      if(requestId===revision && day!==today){day="";events=[]}
      console.warn("RDI STORIA temporarily unavailable:",err);
    }
  }
  window.rdiStoriaBreak={
    startIfDue,stop:()=>stop(false),
    get state(){return {active,loaded:events.length,day,nextEvent,cards,lastShownAt}}
  };
  update();
  setInterval(update,5*60*1000);
})();
