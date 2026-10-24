// Visual-only ad overlay: audio continues to come exclusively from AzuraCast/FFmpeg.
// Prefer AzuraCast's realtime feed; the regular (cached) API is only a safety net.
import {selectCampaign, sceneAt, normalize} from './youtube-spots-core.js';

const station='radio-romanii-italia';
const origin='https://radio-romanii-italia.duckdns.org';
const endpoint=origin+'/api/nowplaying/'+station;
const realtimeUrl='wss://radio-romanii-italia.duckdns.org/api/live/nowplaying/websocket';
const style=document.createElement('link');
style.rel='stylesheet';style.href='./youtube-spots.css?v=20261024-1';document.head.append(style);
const box=document.createElement('section');
box.id='rdiSpot';box.hidden=true;box.setAttribute('aria-label','Publicitate în direct');
box.innerHTML='<div class="spot-photo"></div><div class="spot-shade"></div><div class="spot-copy"><div class="spot-label">PUBLICITATE · RDI</div><h1></h1><p></p></div><div class="spot-footer"><strong></strong><span></span></div><div class="spot-count"></div>';
document.getElementById('stage').append(box);
const photo=box.querySelector('.spot-photo'),heading=box.querySelector('h1'),copy=box.querySelector('p');
let config=null,active=null,armed=null,lastFrame='',nowPlaying=null;
let lastSuccess=0,lastSeenPlayedAt=0,lastFinishedStart=0,received=0;
let serverClockOffset=0,socket=null,reconnectMs=1000,wsRetry=null;
const preloaded=new Map();

function clockSeconds(){return Date.now()/1000+serverClockOffset;}
async function syncClock(){
 try{
  const before=Date.now()/1000;
  const response=await fetch(origin+'/api/time?ts='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(!response.ok)return;
  const data=await response.json(),stamp=Number(data.timestamp),after=Date.now()/1000;
  if(Number.isFinite(stamp)&&stamp>1000000000)serverClockOffset=stamp-(before+after)/2;
 }catch(e){console.warn('RDI clock synchronization unavailable',e.message);}
}
function preload(campaign){
 for(const scene of campaign.scenes||[]){
  if(!scene.image||preloaded.has(scene.image))continue;
  const img=new Image();preloaded.set(scene.image,img);img.src=scene.image;
 }
}
function stop(completed=false){
 if(!active)return;
 if(completed&&active.playedAt>0)lastFinishedStart=active.playedAt;
 active=null;nowPlaying=null;lastFrame='';window.rdiSpotActive=false;
 box.hidden=true;document.body.classList.remove('rdi-spot-active');
 const badge=document.getElementById('badge');if(badge)badge.textContent='● ȘTIRI LIVE';
 window.rdiResumeNews?.();
}
function start(campaign,trackId,playedAt,duration,predicted=false){
 const wasActive=Boolean(active);
 active={...campaign,trackId,key:normalize(campaign.title),playedAt,duration,predicted};
 nowPlaying=null;lastFrame='';
 if(!wasActive){window.rdiSpotActive=true;window.rdiPauseNews?.();}
 document.body.classList.add('rdi-spot-active');box.hidden=false;
 photo.style.backgroundImage='none'; // Never show the previous advert while an image loads.
 const badge=document.getElementById('badge');if(badge)badge.textContent='● PUBLICITATE';
 preload(active);
}
function render(){
 const now=clockSeconds();
 // The next scheduled spot can start at the song boundary, before a cached API notices it.
 if(!active&&armed){
  if(now>=armed.playedAt&&now<armed.playedAt+3){
   start(armed.campaign,'predicted:'+armed.playedAt,armed.playedAt,armed.duration,true);
  }else if(now>=armed.playedAt+3)armed=null;
 }
 if(!active)return;
 const duration=Number(active.duration)||0;
 const elapsed=active.playedAt>0?Math.max(0,now-active.playedAt):
  Math.max(0,Number(nowPlaying?.elapsed)||0)+(performance.now()-received)/1000;
 // Never leave an image on screen after the declared spot duration.
 if(duration>0&&elapsed>=duration){stop(true);armed=null;return;}
 if(!active.predicted&&performance.now()-lastSuccess>15000){stop();return;}
 const timed=duration>0&&active.scenes.length
  ?{...active,sceneSeconds:duration/active.scenes.length}:active;
 const {scene,index}=sceneAt(timed,elapsed);
 const frame=active.key+'|'+active.trackId+'|'+index;
 if(frame===lastFrame)return;
 lastFrame=frame;
 box.dataset.scene=String(index);box.dataset.campaign=active.id||'automatic';
 box.classList.toggle('spot-poster',scene.poster===true);
 const img=preloaded.get(scene.image);
 if(img?.complete&&img.naturalWidth)photo.style.backgroundImage='url('+JSON.stringify(scene.image)+')';
 else if(scene.image){
  const ticket=frame,pending=img||new Image();
  pending.onload=()=>{if(lastFrame===ticket)photo.style.backgroundImage='url('+JSON.stringify(scene.image)+')';};
  if(!img){preloaded.set(scene.image,pending);pending.src=scene.image;}
 }
 photo.getAnimations().forEach(a=>a.cancel());
 const displayMs=(Number(timed.sceneSeconds)||5)*1000;
 photo.animate([{transform:'scale(1)'},{transform:'scale(1.065)'}],{duration:displayMs,fill:'forwards',easing:'linear'});
 photo.animate([{opacity:.42},{opacity:1}],{duration:850,fill:'forwards',easing:'ease-out'});
 heading.textContent=scene.title||active.title;
 copy.textContent=scene.text||'';
 box.querySelector('.spot-footer strong').textContent=active.footer||'Radio Românii din Italia';
 box.querySelector('.spot-footer span').textContent=active.website||'radioromanii.duckdns.org';
 box.querySelector('.spot-count').textContent=(index+1)+' / '+active.scenes.length;
}
function armNext(data){
 const np=data?.now_playing,next=data?.playing_next;
 const candidate=selectCampaign(next,config);
 const playedAt=Number(np?.played_at),length=Number(np?.duration),duration=Number(next?.duration);
 if(!candidate||!(playedAt>0)||!(length>0)||!(duration>0))return;
 const expected=playedAt+length,now=clockSeconds();
 // Pre-arm only a documented next-in-queue ad with a plausible start time.
 if(expected>now-4&&expected<now+600){
  armed={campaign:candidate,playedAt:expected,duration};
  preload(candidate);
 }
}
function accept(data){
 const np=data?.now_playing;
 if(!np?.song||!config)return;
 const startedAt=Number(np.played_at)||0;
 // A cached HTTP result must not undo a newer websocket announcement.
 if(startedAt>0&&lastSeenPlayedAt>0&&startedAt<lastSeenPlayedAt)return;
 if(data.is_online===false||data.live?.is_live){armed=null;stop();return;}
 const campaign=selectCampaign(np,config);
 if(!campaign)armNext(data);
 // AzuraCast can keep returning the previous song for a while after a predicted boundary.
 if(active?.predicted&&!campaign&&startedAt>0&&startedAt<active.playedAt)return;
 if(startedAt>0)lastSeenPlayedAt=Math.max(startedAt,lastSeenPlayedAt);
 lastSuccess=performance.now();
 window.dispatchEvent(new CustomEvent('rdi:nowplaying',{detail:data}));
 if(!campaign){if(active)stop();return;}
 if(startedAt>0&&lastFinishedStart>0&&Math.abs(startedAt-lastFinishedStart)<2)return;
 const id=String(np.sh_id||np.played_at||np.song?.id||np.song?.text);
 const duration=Number(np.duration)||0;
 const playedAt=startedAt>0?startedAt:clockSeconds()-Math.max(0,Number(np.elapsed)||0);
 if(active?.predicted&&active.id===campaign.id&&Math.abs(active.playedAt-playedAt)<4){
  active={...active,trackId:id,playedAt,duration:duration||active.duration,predicted:false};
  lastFrame='';
 }else if(!active||active.trackId!==id){
  start(campaign,id,playedAt,duration);
 }
 armed=null;nowPlaying=np;received=performance.now();render();
}
function handlePublication(pub){
 let payload=pub?.data;
 if(typeof payload==='string'){try{payload=JSON.parse(payload);}catch(e){return;}}
 if(payload?.np)accept(payload.np);
 else if(payload?.now_playing)accept(payload);
}
function connectRealtime(){
 if(typeof WebSocket==='undefined')return;
 try{
  socket=new WebSocket(realtimeUrl);
  socket.onopen=()=>{
   reconnectMs=1000;
   socket.send(JSON.stringify({subs:{['station:'+station]:{recover:true}}}));
  };
  socket.onmessage=event=>{
   let message;
   try{message=JSON.parse(event.data);}catch(e){return;}
   if(message.pub)handlePublication(message.pub);
   if(message.connect){
    const connected=message.connect;
    if(Array.isArray(connected.data))connected.data.forEach(handlePublication);
    for(const sub of Object.values(connected.subs||{})){
     for(const publication of sub.publications||[])handlePublication(publication);
    }
   }
  };
  socket.onclose=()=>{
   socket=null;
   clearTimeout(wsRetry);
   wsRetry=setTimeout(connectRealtime,reconnectMs);
   reconnectMs=Math.min(30000,reconnectMs*2);
  };
  socket.onerror=()=>socket?.close();
 }catch(e){
  clearTimeout(wsRetry);
  wsRetry=setTimeout(connectRealtime,5000);
 }
}
async function poll(){
 try{
  const response=await fetch(endpoint+'?rdi_visual='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(!response.ok)throw Error('nowplaying '+response.status);
  accept(await response.json());
 }catch(e){console.warn('RDI spot backup metadata unavailable',e.message);}
 finally{setTimeout(poll,1500);}
}
async function init(){
 try{
  const response=await fetch('./data/spot-campaigns.json?v=20261024-1',{cache:'no-store'});
  if(!response.ok)throw Error('campaigns '+response.status);
  config=await response.json();
  for(const campaign of config.campaigns||[])preload(campaign);
  syncClock();setInterval(syncClock,600000);
  connectRealtime();poll();setInterval(render,120);
 }catch(e){
  console.warn('RDI spot metadata init delayed; retrying',e.message);
  setTimeout(init,10000);
 }
}
init();
