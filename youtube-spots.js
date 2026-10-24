// Only visuals: AzuraCast/FFmpeg remain the sole source of broadcast audio.
import {selectCampaign, sceneAt, normalize} from './youtube-spots-core.js';

const endpoint='https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia';
const style=document.createElement('link');
style.rel='stylesheet';style.href='./youtube-spots.css?v=20261024-1';document.head.append(style);
const box=document.createElement('section');
box.id='rdiSpot';box.hidden=true;box.setAttribute('aria-label','Publicitate în direct');
box.innerHTML='<div class="spot-photo"></div><div class="spot-shade"></div><div class="spot-copy"><div class="spot-label">PUBLICITATE · RDI</div><h1></h1><p></p></div><div class="spot-footer"><strong></strong><span></span></div><div class="spot-count"></div>';
document.getElementById('stage').append(box);
const photo=box.querySelector('.spot-photo'),heading=box.querySelector('h1'),copy=box.querySelector('p');
let config=null,active=null,lastSuccess=0,lastFrame='',received=0,nowPlaying=null;
const preloaded=new Map();
function preload(campaign){
 for(const scene of campaign.scenes||[]){
  if(preloaded.has(scene.image))continue;
  const img=new Image();img.src=scene.image;preloaded.set(scene.image,img);
 }
}
function stop(){
 if(!active)return;
 active=null;lastFrame='';window.rdiSpotActive=false;
 box.hidden=true;document.body.classList.remove('rdi-spot-active');
 const badge=document.getElementById('badge');if(badge)badge.textContent='● ȘTIRI LIVE';
 window.rdiResumeNews?.();
}
function render(){
 if(!active||!nowPlaying)return;
 const elapsed=Math.max(0,Number(nowPlaying.elapsed)||0)+(performance.now()-received)/1000;
 const duration=Number(nowPlaying.duration)||0;
 // Fail back to news if metadata disappears or the track outlives its end time.
 if(performance.now()-lastSuccess>10000||(duration>0&&elapsed>duration+3)){stop();return;}
 const timed=duration>0&&duration<active.scenes.length*active.sceneSeconds
  ?{...active,sceneSeconds:duration/active.scenes.length}:active;
 const {scene,index}=sceneAt(timed,elapsed);
 const frame=active.key+'|'+active.trackId+'|'+index;
 if(frame===lastFrame)return;
 lastFrame=frame;
 box.dataset.scene=String(index);box.dataset.campaign=active.id||'automatic';
 box.classList.toggle('spot-poster',scene.poster===true);
 photo.style.backgroundImage='';
 const img=preloaded.get(scene.image);
 if(img?.complete&&img.naturalWidth)photo.style.backgroundImage='url('+JSON.stringify(scene.image)+')';
 else if(scene.image){
  const ticket=frame;
  const pending=img||new Image();
  pending.onload=()=>{if(lastFrame===ticket)photo.style.backgroundImage='url('+JSON.stringify(scene.image)+')';};
  if(!img){pending.src=scene.image;preloaded.set(scene.image,pending);}
 }
 photo.getAnimations().forEach(a=>a.cancel());
 photo.animate([{transform:'scale(1)'},{transform:'scale(1.045)'}],{duration:5000,fill:'forwards'});
 heading.textContent=scene.title||active.title;
 copy.textContent=scene.text||'';
 box.querySelector('.spot-footer strong').textContent=active.footer||'Radio Românii din Italia';
 box.querySelector('.spot-footer span').textContent=active.website||'radioromanii.duckdns.org';
 box.querySelector('.spot-count').textContent=(index+1)+' / '+active.scenes.length;
}
function accept(data){
 const np=data?.now_playing;
 lastSuccess=performance.now();received=lastSuccess;
 window.dispatchEvent(new CustomEvent('rdi:nowplaying',{detail:data}));
 const campaign=data?.is_online===false||data?.live?.is_live?null:selectCampaign(np,config);
 if(!campaign){stop();return;}
 const id=String(np.sh_id||np.played_at||np.song?.id||np.song?.text);
 if(!active||active.trackId!==id){
  active={...campaign,trackId:id,key:normalize(campaign.title)};lastFrame='';
  window.rdiSpotActive=true;window.rdiPauseNews?.();
  document.body.classList.add('rdi-spot-active');box.hidden=false;
  const badge=document.getElementById('badge');if(badge)badge.textContent='● PUBLICITATE';
  preload(active);
 }
 nowPlaying=np;render();
}
async function poll(){
 try{
  const response=await fetch(endpoint+'?rdi_visual='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(!response.ok)throw Error('nowplaying '+response.status);
  accept(await response.json());
 }catch(e){console.warn('RDI spot metadata unavailable',e.message);}
 finally{setTimeout(poll,2000);}
}
async function init(){
 try{
  const response=await fetch('./data/spot-campaigns.json?v=20261024-1',{cache:'no-store'});
  if(!response.ok)throw Error('campaigns '+response.status);
  config=await response.json();
  for(const campaign of config.campaigns||[])preload(campaign);
  poll();setInterval(render,250);
 }catch(e){console.warn('RDI visual spots disabled',e.message);}
}
init();
