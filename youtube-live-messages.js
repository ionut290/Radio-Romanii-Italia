/* RDI: breve riquadro con tutti i messaggi testuali approvati della giornata. */
(()=> {
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;

  const layer=document.createElement("section");
  layer.id="rdiListenerMessageLayer";
  layer.hidden=true;
  layer.setAttribute("aria-label","Messaggi approvati dalla redazione RDI");
  layer.innerHTML=
    '<div class="rdi-listener-message-card">' +
      '<header class="rdi-listener-message-header"><span>🇷🇴 🇮🇹 RADIO ROMÂNII DIN ITALIA</span><b>RDI LIVE</b></header>' +
      '<div class="rdi-listener-message-kicker">MESSAGGI DALLA COMUNITÀ</div>' +
      '<div class="rdi-listener-message-window"><div class="rdi-listener-message-list" id="rdiListenerMessageList"></div></div>' +
      '<div class="rdi-listener-message-footer">Messaggi selezionati dalla redazione</div>' +
    '</div>' +
    '<div class="rdi-listener-message-progress" id="rdiListenerMessageProgress"></div>';
  const style=document.createElement("style");
  style.textContent=
    '#rdiListenerMessageLayer{position:absolute;inset:0;z-index:30;display:grid;place-items:center;padding:4vw;background:radial-gradient(ellipse at 50% 0%,#214b7e,#09172a 72%);color:#fff}' +
    '#rdiListenerMessageLayer[hidden]{display:none}' +
    '.rdi-listener-message-card{width:min(1120px,92vw);height:min(650px,88vh);padding:clamp(20px,3.2vw,44px);border:1px solid #6c8ba9;border-radius:22px;background:linear-gradient(145deg,#102b49f5,#07182df5);box-shadow:0 20px 70px #0009;display:flex;flex-direction:column;overflow:hidden}' +
    '.rdi-listener-message-header{width:100%;display:flex;justify-content:space-between;gap:18px;align-items:center;font-size:clamp(13px,1.5vw,19px);font-weight:900;letter-spacing:.04em}' +
    '.rdi-listener-message-header b{background:#c92732;padding:9px 15px;border-radius:8px;white-space:nowrap}' +
    '.rdi-listener-message-kicker{margin:clamp(18px,3vh,30px) 0 16px;color:#ffdc82;font-size:clamp(15px,1.8vw,22px);font-weight:900;letter-spacing:.12em;text-align:center}' +
    '.rdi-listener-message-window{position:relative;flex:1;min-height:0;overflow:hidden;mask-image:linear-gradient(to bottom,transparent,#000 3%,#000 97%,transparent)}' +
    '.rdi-listener-message-list{display:flex;flex-direction:column;gap:12px;will-change:transform}' +
    '.rdi-listener-message-item{flex:none;min-height:86px;padding:15px 20px;border:1px solid #456787;border-left:5px solid #e2b957;border-radius:12px;background:linear-gradient(100deg,#173859,#102944);font-size:clamp(17px,2vw,25px);font-weight:700;line-height:1.3;white-space:pre-wrap;overflow-wrap:anywhere;display:flex;align-items:center}' +
    '.rdi-listener-message-footer{padding-top:15px;color:#c2d4e7;font-size:clamp(12px,1.3vw,16px);text-align:center}' +
    '.rdi-listener-message-progress{position:absolute;bottom:0;left:0;height:5px;width:0;background:#f0c05b}' +
    '@media(max-width:700px){.rdi-listener-message-card{height:90vh;width:94vw;padding:16px}.rdi-listener-message-header{font-size:12px}.rdi-listener-message-item{min-height:72px;padding:12px;font-size:clamp(16px,4vw,21px)}}';
  stage.append(style,layer);

  const list=layer.querySelector("#rdiListenerMessageList");
  const progress=layer.querySelector("#rdiListenerMessageProgress");
  const FEED_URL="https://radio-romanii-italia.duckdns.org/rdi-live-feed.json";
  const SHOWN_AT_KEY="rdi-listener-message-last-bulletin";
  let items=[],active=false,finishTimer=null,priorityTimer=null,finishCallback=null;
  let pending=false,dayKey="",memorySeen=new Set(),scrollAnimation=null;

  function romeDay(){
    return new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  }
  function seenKey(day,id){return "rdi-listener-message-seen:"+day+":"+id}
  function alreadySeen(id){
    const key=seenKey(dayKey,id);
    try{return localStorage.getItem(key)==="1"}catch(_){return memorySeen.has(key)}
  }
  function markSeen(id){
    const key=seenKey(dayKey,id);memorySeen.add(key);
    try{localStorage.setItem(key,"1")}catch(_){}
  }
  async function refresh(){
    try{
      const response=await fetch(FEED_URL+"?ts="+Date.now(),{cache:"no-store"});
      if(!response.ok)return;
      const data=await response.json();
      const today=romeDay();
      const incomingDay=typeof data.day==="string"?data.day:today;
      if(incomingDay!==today){items=[];return;}
      if(dayKey!==incomingDay){dayKey=incomingDay;memorySeen=new Set();}
      items=Array.isArray(data.items)?data.items.filter(item=>
        item&&item.type==="text"&&typeof item.id==="string"&&
        typeof item.text==="string"&&item.text.trim().length>0
      ):[];

      // New messages queue one short bulletin. The same list can be shown
      // again at most once an hour while the channel remains quiet.
      for(const item of items){
        if(!alreadySeen(item.id)){markSeen(item.id);pending=true;}
      }
    }catch(_){/* Keep the video rotation running if the feed is unavailable. */}
  }
  function priorityActive(){
    return window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive||
      window.rdiWeatherActive||window.rdiDjPromoActive||window.rdiPhilosophyActive||
      window.rdiCameraActive||window.rdiLandscapeActive;
  }
  function stop(resume=true,completed=false){
    if(!active)return;
    clearTimeout(finishTimer);clearInterval(priorityTimer);
    if(scrollAnimation){scrollAnimation.cancel();scrollAnimation=null;}
    finishTimer=priorityTimer=null;
    const callback=finishCallback;finishCallback=null;
    active=false;window.rdiListenerMessageActive=false;
    layer.hidden=true;
    progress.style.transition="none";progress.style.width="0%";
    if(completed){
      try{localStorage.setItem(SHOWN_AT_KEY,String(Date.now()))}catch(_){}
    }else{
      pending=true;
    }
    if(resume&&!priorityActive()&&typeof callback==="function")callback();
  }
  function makeCards(){
    list.replaceChildren();
    for(const item of items){
      const card=document.createElement("div");
      card.className="rdi-listener-message-item";
      card.textContent=item.text.trim().slice(0,700);
      list.append(card);
    }
  }
  function startIfDue(next){
    if(active||priorityActive()||!items.length)return false;
    let lastShown=0;
    try{lastShown=Number(localStorage.getItem(SHOWN_AT_KEY)||0)}catch(_){}
    const hourlyDue=!lastShown||Date.now()-lastShown>=60*60*1000;
    if(!pending&&!hourlyDue)return false;

    window.rdiPauseNews?.();
    active=true;window.rdiListenerMessageActive=true;finishCallback=next;
    makeCards();layer.hidden=false;pending=false;
    const windowBox=layer.querySelector(".rdi-listener-message-window");
    const distance=Math.max(0,list.scrollHeight-windowBox.clientHeight);
    const duration=Math.max(9000,Math.min(60000,9000+Math.max(0,items.length-5)*850));
    if(distance>0){
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        if(active){
          scrollAnimation=list.animate(
            [{transform:"translateY(0)"},{transform:"translateY(-"+distance+"px)"}],
            {duration,easing:"linear",fill:"forwards"}
          );
        }
      }));
    }
    progress.style.transition="none";progress.style.width="0%";
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active){progress.style.transition="width "+duration+"ms linear";progress.style.width="100%";}
    }));
    finishTimer=setTimeout(()=>stop(true,true),duration);
    priorityTimer=setInterval(()=>{if(priorityActive())stop(false,false)},500);
    return true;
  }
  refresh();setInterval(refresh,15000);
  window.rdiListenerMessageBreak={startIfDue,stop,get state(){return {active,available:items.length,pending};}};
})();