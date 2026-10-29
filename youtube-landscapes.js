/* RDI YouTube live news: licensed scenery interludes from Italy and Romania.
 * Silent visual source only. No impact on AzuraCast/FFmpeg audio.
 * Spot and Geopolitica always take priority over scenery.
 */
import {parseLandscapeConfig,landscapeDue} from "./youtube-landscapes-core.mjs";
(()=>{
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;
  const layer=document.createElement("section");
  layer.id="rdiLandscapes";
  layer.hidden=true;
  layer.setAttribute("aria-label","Immagini di repertorio dell'Italia e della Romania");
  layer.innerHTML='<div class="rdi-landscape-view"></div>'+
    '<div class="rdi-landscape-shade"></div>'+
    '<div class="rdi-landscape-head"><strong>RADIO ROMÂNII DIN ITALIA</strong>'+
      '<span>IMAGINI DE ARHIVĂ · FĂRĂ SUNET</span></div>'+
    '<div class="rdi-landscape-footer"><p class="rdi-landscape-country"></p>'+
      '<h2 class="rdi-landscape-title"></h2><p class="rdi-landscape-credit"></p></div>'+
    '<div class="rdi-landscape-progress"></div>';
  stage.append(layer);
  const view=layer.querySelector(".rdi-landscape-view");
  const progress=layer.querySelector(".rdi-landscape-progress");
  const country=layer.querySelector(".rdi-landscape-country");
  const title=layer.querySelector(".rdi-landscape-title");
  const credit=layer.querySelector(".rdi-landscape-credit");
  const demo=new URLSearchParams(location.search).get("landscape_preview")==="1";
  let cfg={enabled:false,every:4,duration:20,items:[]};
  let completed=0,cursor=0,active=false,endTimer=null,resume=null,generation=0;
  function removeMedia(){
    generation++;
    for(const video of view.querySelectorAll("video")){
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
    view.replaceChildren();
  }
  function stop(){
    clearTimeout(endTimer);endTimer=null;resume=null;
    removeMedia();
    active=false;window.rdiLandscapeActive=false;layer.hidden=true;
    document.body.classList.remove("rdi-landscape-active");
    progress.style.transition="none";progress.style.width="0%";
  }
  function finish(){
    if(!active)return;
    const callback=resume;
    stop();
    if(!window.rdiSpotActive&&!window.rdiGeoActive && typeof callback==="function")callback();
  }
  function show(item,duration,next){
    if(active||window.rdiSpotActive||window.rdiGeoActive||window.rdiCameraActive)return false;
    active=true;window.rdiLandscapeActive=true;resume=next;
    document.body.classList.add("rdi-landscape-active");layer.hidden=false;
    country.textContent=item.country==="Italia"?"🇮🇹 ITALIA":"🇷🇴 ROMÂNIA";
    title.textContent=item.title;
    credit.textContent="Sursa: "+item.credit+" · Imagini de arhivă";
    removeMedia();
    const ticket=generation;
    const poster=document.createElement("img");
    poster.alt=item.title+" · "+item.credit;
    poster.decoding="async";
    poster.addEventListener("error",()=>{if(active&&ticket===generation)finish();},{once:true});
    poster.src=item.poster;
    view.append(poster);
    if(item.kind==="video"){
      const video=document.createElement("video");
      video.autoplay=true;video.muted=true;video.defaultMuted=true;
      video.volume=0;video.loop=true;video.playsInline=true;
      video.controls=false;video.preload="auto";
      video.disablePictureInPicture=true;
      video.setAttribute("aria-hidden","true");
      video.addEventListener("playing",()=>{
        if(active&&ticket===generation){video.style.opacity="1";poster.style.opacity="0";}
      });
      video.addEventListener("error",()=>{video.style.display="none";});
      video.src=item.src;
      view.append(video);
      video.play().catch(()=>{video.style.display="none";});
    }
    progress.style.transition="none";progress.style.width="0%";
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active&&ticket===generation){
        progress.style.transition="width "+duration*1000+"ms linear";
        progress.style.width="100%";
      }
    }));
    endTimer=setTimeout(finish,duration*1000);
    return true;
  }
  async function refresh(){
    try{
      const response=await fetch("./data/youtube-landscapes.json?ts="+Date.now(),
          {cache:"no-store",signal:AbortSignal.timeout(6000)});
      if(!response.ok)throw Error("config "+response.status);
      cfg=parseLandscapeConfig(await response.json());
    }catch{
      cfg={enabled:false,every:4,duration:20,items:[]};
    }
  }
  function startIfDue(next){
    if(active||window.rdiSpotActive||window.rdiGeoActive||window.rdiCameraActive)return false;
    completed++;
    if(!cfg.enabled||!landscapeDue(completed,cfg.every))return false;
    const item=cfg.items[cursor%cfg.items.length];
    cursor++;
    return show(item,cfg.duration,next);
  }
  window.rdiLandscapeBreak={
    startIfDue,stop,
    get state(){return {active,eligible:cfg.items.length,completed,cursor,enabled:cfg.enabled};}
  };
  const configReady=refresh();setInterval(refresh,300000);
  if(demo){
    // Wait for the actual JSON configuration, not for a racing "load" event.
    // Diagnostic status exists only on the explicit preview URL.
    const status=document.createElement("div");
    status.id="rdiLandscapePreviewStatus";
    status.style.cssText="position:absolute;bottom:84px;right:8px;z-index:30;background:#091b32;color:#fff;padding:5px 9px;font-size:11px";
    stage.append(status);
    status.textContent="Landscape preview: loading";
    configReady.then(()=>{
      status.textContent="Landscape preview: "+(cfg.enabled?cfg.items.length+" assets ready":"no valid assets");
      if(cfg.enabled&&!active&&!window.rdiGeoActive&&!window.rdiSpotActive){
        const param=new URLSearchParams(location.search);
        const chosen=cfg.items.find(x=>x.id===param.get("landscape_id"))||cfg.items[0];
        const started=show(chosen,cfg.duration,null);
        status.textContent=started?"Landscape preview: "+chosen.id:"Landscape preview: busy";
      }
    });
  }
})();
