/* RDI listener message break: renders editor-approved text from the read-only Oracle feed. */
(()=> {
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;

  const layer=document.createElement("section");
  layer.id="rdiListenerMessageLayer";
  layer.hidden=true;
  layer.setAttribute("aria-label","Messaggio approvato dalla redazione RDI");
  layer.innerHTML=
    '<div class="rdi-listener-message-card">' +
      '<header class="rdi-listener-message-header"><span>🇷🇴 🇮🇹 RADIO ROMÂNII DIN ITALIA</span><b>MESSAGGIO LIVE</b></header>' +
      '<div class="rdi-listener-message-kicker">LA VOCE DELLA COMUNITÀ</div>' +
      '<p class="rdi-listener-message-text" id="rdiListenerMessageText"></p>' +
      '<div class="rdi-listener-message-footer">Messaggio selezionato dalla redazione</div>' +
    '</div>' +
    '<div class="rdi-listener-message-progress" id="rdiListenerMessageProgress"></div>';
  const style=document.createElement("style");
  style.textContent=
    '#rdiListenerMessageLayer{position:absolute;inset:0;z-index:30;display:grid;place-items:center;padding:5vw;background:radial-gradient(ellipse at 50% 0%,#214b7e,#09172a 72%);color:#fff}' +
    '#rdiListenerMessageLayer[hidden]{display:none}' +
    '.rdi-listener-message-card{width:min(1080px,92vw);max-height:82vh;padding:clamp(24px,5vw,66px);border:1px solid #6c8ba9;border-radius:24px;background:linear-gradient(145deg,#102b49f5,#07182df5);box-shadow:0 20px 70px #0009;display:flex;flex-direction:column;align-items:center;text-align:center;overflow:hidden}' +
    '.rdi-listener-message-header{width:100%;display:flex;justify-content:space-between;gap:18px;align-items:center;font-size:clamp(13px,1.7vw,20px);font-weight:900;letter-spacing:.04em}' +
    '.rdi-listener-message-header b{background:#c92732;padding:10px 16px;border-radius:8px;white-space:nowrap}' +
    '.rdi-listener-message-kicker{margin-top:clamp(34px,7vh,72px);color:#ffdc82;font-size:clamp(16px,2vw,25px);font-weight:900;letter-spacing:.16em}' +
    '.rdi-listener-message-text{max-width:900px;max-height:48vh;margin:26px 0;overflow:hidden;font-size:clamp(28px,4.3vw,55px);font-weight:800;line-height:1.22;white-space:pre-wrap;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:9;-webkit-box-orient:vertical}' +
    '.rdi-listener-message-footer{margin-top:auto;color:#c2d4e7;font-size:clamp(14px,1.6vw,19px)}' +
    '.rdi-listener-message-progress{position:absolute;bottom:0;left:0;height:7px;width:0;background:#f0c05b}' +
    '@media(max-width:700px){.rdi-listener-message-header{align-items:flex-start;flex-direction:column}.rdi-listener-message-text{font-size:clamp(24px,6vw,38px)}}';
  stage.append(style,layer);

  const textNode=layer.querySelector("#rdiListenerMessageText");
  const progress=layer.querySelector("#rdiListenerMessageProgress");
  const FEED_URL="https://radio-romanii-italia.duckdns.org/rdi-live-feed.json";
  const DURATION_MS=24000;
  const shownKey=id=>"rdi-listener-message-shown:"+id;
  let items=[],active=false,finishTimer=null,priorityTimer=null,finishCallback=null;

  function alreadyShown(id){
    try{return localStorage.getItem(shownKey(id))==="1"}catch(_){return false}
  }
  function markShown(id){
    try{localStorage.setItem(shownKey(id),"1")}catch(_){}
  }
  async function refresh(){
    try{
      const response=await fetch(FEED_URL+"?ts="+Date.now(),{cache:"no-store"});
      if(!response.ok)return;
      const data=await response.json();
      items=Array.isArray(data.items)?data.items.filter(item=>
        item&&item.type==="text"&&typeof item.id==="string"&&
        typeof item.text==="string"&&item.text.trim().length>0
      ):[];
    }catch(_){/* Keep the video rotation running if the feed is unavailable. */}
  }
  function priorityActive(){
    return window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive||
      window.rdiWeatherActive||window.rdiDjPromoActive||window.rdiPhilosophyActive||
      window.rdiCameraActive||window.rdiLandscapeActive;
  }
  function stop(resume=true){
    if(!active)return;
    clearTimeout(finishTimer);clearInterval(priorityTimer);
    finishTimer=priorityTimer=null;
    const callback=finishCallback;finishCallback=null;
    active=false;window.rdiListenerMessageActive=false;
    layer.hidden=true;
    progress.style.transition="none";progress.style.width="0%";
    if(resume&&!priorityActive()&&typeof callback==="function")callback();
  }
  function startIfDue(next){
    if(active||priorityActive())return false;
    const item=items.find(x=>!alreadyShown(x.id));
    if(!item)return false;
    markShown(item.id);
    window.rdiPauseNews?.();
    active=true;window.rdiListenerMessageActive=true;finishCallback=next;
    textNode.textContent=item.text.trim().slice(0,700);
    layer.hidden=false;
    progress.style.transition="none";progress.style.width="0%";
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active){progress.style.transition="width "+DURATION_MS+"ms linear";progress.style.width="100%";}
    }));
    finishTimer=setTimeout(()=>stop(true),DURATION_MS);
    priorityTimer=setInterval(()=>{if(priorityActive())stop(false)},500);
    return true;
  }
  refresh();setInterval(refresh,15000);
  window.rdiListenerMessageBreak={startIfDue,stop,get state(){return {active,available:items.length};}};
})();