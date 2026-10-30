/* RDI: play only editor-approved Telegram audio, photos and videos. */
(()=> {
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;

  const layer=document.createElement("section");
  layer.id="rdiListenerMediaLayer";
  layer.hidden=true;
  layer.setAttribute("aria-label","Contenuto multimediale approvato dalla redazione RDI");
  layer.innerHTML=
    '<div class="rdi-listener-media-card">' +
      '<header class="rdi-listener-media-header"><span>🇷🇴 🇮🇹 RADIO ROMÂNII DIN ITALIA</span><b>RDI LIVE</b></header>' +
      '<div class="rdi-listener-media-kicker" id="rdiListenerMediaKicker"></div>' +
      '<div class="rdi-listener-media-content" id="rdiListenerMediaContent"></div>' +
      '<div class="rdi-listener-media-caption" id="rdiListenerMediaCaption"></div>' +
      '<footer class="rdi-listener-media-footer">Contenuto approvato dalla redazione</footer>' +
    '</div>' +
    '<div class="rdi-listener-media-progress" id="rdiListenerMediaProgress"></div>';
  const style=document.createElement("style");
  style.textContent=
    '#rdiListenerMediaLayer{position:absolute;inset:0;z-index:31;display:grid;place-items:center;padding:4vw;background:radial-gradient(ellipse at 50% 0%,#214b7e,#09172a 72%);color:#fff}' +
    '#rdiListenerMediaLayer[hidden]{display:none}' +
    '.rdi-listener-media-card{width:min(1120px,92vw);height:min(650px,88vh);padding:clamp(20px,3.2vw,44px);border:1px solid #6c8ba9;border-radius:22px;background:linear-gradient(145deg,#102b49f5,#07182df5);box-shadow:0 20px 70px #0009;display:flex;flex-direction:column;overflow:hidden}' +
    '.rdi-listener-media-header{display:flex;justify-content:space-between;gap:18px;align-items:center;font-size:clamp(13px,1.5vw,19px);font-weight:900;letter-spacing:.04em}' +
    '.rdi-listener-media-header b{background:#c92732;padding:9px 15px;border-radius:8px;white-space:nowrap}' +
    '.rdi-listener-media-kicker{margin:clamp(16px,2vh,24px) 0 12px;color:#ffdc82;font-size:clamp(15px,1.8vw,22px);font-weight:900;letter-spacing:.12em;text-align:center}' +
    '.rdi-listener-media-content{position:relative;flex:1;min-height:0;display:grid;place-items:center;overflow:hidden;border:1px solid #456787;border-radius:14px;background:#061326}' +
    '.rdi-listener-media-content img,.rdi-listener-media-content video{display:block;width:100%;height:100%;object-fit:contain;background:#061326}' +
    '.rdi-listener-audio-visual{display:grid;place-items:center;width:100%;height:100%;background:radial-gradient(circle at center,#1b4771,#08172b 70%);text-align:center}' +
    '.rdi-listener-audio-icon{font-size:clamp(64px,12vw,130px);filter:drop-shadow(0 0 18px #38a6ff)}' +
    '.rdi-listener-audio-visual strong{display:block;margin-top:14px;font-size:clamp(20px,3vw,36px);letter-spacing:.08em}' +
    '.rdi-listener-media-content audio{position:absolute;left:50%;bottom:18px;transform:translateX(-50%);width:min(600px,85%);height:44px}' +
    '.rdi-listener-media-caption{min-height:1.5em;padding:12px 4px 0;font-size:clamp(15px,1.8vw,22px);font-weight:700;text-align:center;overflow-wrap:anywhere}' +
    '.rdi-listener-media-footer{padding-top:8px;color:#c2d4e7;font-size:clamp(12px,1.3vw,16px);text-align:center}' +
    '.rdi-listener-media-progress{position:absolute;bottom:0;left:0;height:5px;width:0;background:#f0c05b}' +
    '@media(max-width:700px){.rdi-listener-media-card{height:90vh;width:94vw;padding:16px}.rdi-listener-media-header{font-size:12px}}';
  stage.append(style,layer);

  const content=layer.querySelector("#rdiListenerMediaContent");
  const kicker=layer.querySelector("#rdiListenerMediaKicker");
  const caption=layer.querySelector("#rdiListenerMediaCaption");
  const progress=layer.querySelector("#rdiListenerMediaProgress");
  const FEED_URL="https://radio-romanii-italia.duckdns.org/rdi-live-feed.json";
  const queue=[];
  const memorySeen=new Set();
  let active=false,current=null,finishTimer=null,priorityTimer=null,finishCallback=null;

  function romeDay(){
    return new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  }
  function seenKey(item){return "rdi-listener-media-seen:"+romeDay()+":"+item.id}
  function alreadySeen(item){
    const key=seenKey(item);
    try{return localStorage.getItem(key)==="1"}catch(_){return memorySeen.has(key)}
  }
  function markSeen(item){
    const key=seenKey(item);memorySeen.add(key);
    try{localStorage.setItem(key,"1")}catch(_){}
  }
  function validMedia(item){
    if(!item||!["photo","video","audio"].includes(item.type)||
      typeof item.id!=="string"||typeof item.url!=="string")return false;
    try{
      const url=new URL(item.url);
      return url.origin==="https://radio-romanii-italia.duckdns.org"&&
        url.pathname.startsWith("/rdi-live-media/");
    }catch(_){return false;}
  }
  async function refresh(){
    try{
      const response=await fetch(FEED_URL+"?ts="+Date.now(),{cache:"no-store"});
      if(!response.ok)return;
      const data=await response.json();
      if(data.day!==romeDay())return;
      if(!Array.isArray(data.items))return;
      for(const item of data.items){
        if(!validMedia(item)||alreadySeen(item)||queue.some(x=>x.id===item.id)||
          (current&&current.id===item.id))continue;
        queue.push(item);
      }
      queue.sort((a,b)=>Date.parse(a.date||0)-Date.parse(b.date||0));
    }catch(_){/* Keep the video rotation running if the media feed is unavailable. */}
  }
  function priorityActive(){
    return window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive||
      window.rdiWeatherActive||window.rdiDjPromoActive||window.rdiPhilosophyActive||
      window.rdiCameraActive||window.rdiLandscapeActive;
  }
  function cleanupPlayer(){
    for(const player of content.querySelectorAll("audio,video")){
      player.pause();
      player.removeAttribute("src");
      player.load?.();
    }
    content.replaceChildren();
  }
  function stop(resume=true,completed=false){
    if(!active)return;
    clearTimeout(finishTimer);clearInterval(priorityTimer);
    finishTimer=priorityTimer=null;
    if(!completed&&current)queue.unshift(current);
    current=null;
    cleanupPlayer();
    const callback=finishCallback;finishCallback=null;
    active=false;window.rdiListenerMediaActive=false;
    layer.hidden=true;
    progress.style.transition="none";progress.style.width="0%";
    if(resume&&!priorityActive()&&typeof callback==="function")callback();
  }
  function finishCurrent(){
    if(!active)return;
    if(current)markSeen(current);
    current=null;
    clearTimeout(finishTimer);finishTimer=null;
    cleanupPlayer();
    if(queue.length){playNext();return;}
    stop(true,true);
  }
  function playNext(){
    if(!active||!queue.length){stop(true,true);return;}
    current=queue.shift();
    kicker.textContent=current.type==="video"?"VIDEO DALLA COMUNITÀ":
      current.type==="audio"?"MESSAGGIO AUDIO":"FOTO DALLA COMUNITÀ";
    caption.textContent=typeof current.text==="string"?current.text.trim().slice(0,220):"";
    progress.style.transition="none";progress.style.width="0%";

    let player;
    if(current.type==="photo"){
      player=document.createElement("img");
      player.alt="Foto inviata alla redazione RDI";
      player.src=current.url;
    }else if(current.type==="video"){
      player=document.createElement("video");
      player.playsInline=true;
      player.autoplay=true;
      player.controls=true;
      player.preload="auto";
      player.src=current.url;
      player.addEventListener("ended",finishCurrent,{once:true});
    }else{
      const visual=document.createElement("div");
      visual.className="rdi-listener-audio-visual";
      visual.innerHTML='<div><div class="rdi-listener-audio-icon">🎙️</div><strong>ASCOLTA IL MESSAGGIO</strong></div>';
      content.append(visual);
      player=document.createElement("audio");
      player.autoplay=true;
      player.controls=true;
      player.preload="auto";
      player.src=current.url;
      player.addEventListener("ended",finishCurrent,{once:true});
    }
    if(current.type!=="audio")content.append(player);
    else content.append(player);

    const duration=current.type==="photo"?10000:30000;
    finishTimer=setTimeout(finishCurrent,duration);
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active){progress.style.transition="width "+duration+"ms linear";progress.style.width="100%";}
    }));
    if(current.type!=="photo"){
      const play=player.play();
      if(play&&typeof play.catch==="function")play.catch(()=>finishCurrent());
    }
  }
  function startIfDue(next){
    if(active||priorityActive()||!queue.length)return false;
    window.rdiPauseNews?.();
    active=true;window.rdiListenerMediaActive=true;finishCallback=next;
    layer.hidden=false;
    playNext();
    priorityTimer=setInterval(()=>{if(priorityActive())stop(false,false)},500);
    return true;
  }

  refresh();setInterval(refresh,15000);
  window.rdiListenerMediaBreak={startIfDue,stop,get state(){return {active,queued:queue.length};}};
})();