/* RDI ON-AIR: automatic, short city webcam interludes.
   Broadcast is opt-in and blocked unless a separate source-specific YouTube permission is recorded.
   Never change AzuraCast audio, FFmpeg, article feeds, or the advertising timeline.
*/
import {parseCameraConfig,slotDue} from './youtube-camera-core.mjs';
(()=>{
  'use strict';
  const stage=document.getElementById('stage');
  if(!stage)return;
  const layer=document.createElement('section');
  layer.id='rdiCityCamera';
  layer.hidden=true;
  layer.setAttribute('aria-label','Immagini dalla città durante il notiziario');
  layer.innerHTML='<div class="rdi-camera-view" id="rdiCameraView"></div>'+
    '<div class="rdi-camera-shade"></div>'+
    '<div class="rdi-camera-top"><span>RADIO ROMÂNII DIN ITALIA</span><span class="rdi-camera-pill" id="rdiCameraType">● WEBCAM</span></div>'+
    '<div class="rdi-camera-labels"><div class="rdi-camera-country" id="rdiCameraCountry"></div>'+
    '<h2 class="rdi-camera-city" id="rdiCameraCity"></h2>'+
    '<div class="rdi-camera-source" id="rdiCameraCredit"></div></div>'+
    '<div class="rdi-camera-progress" id="rdiCameraProgress"></div>';
  stage.append(layer);
  const el=id=>document.getElementById(id);
  const view=el('rdiCameraView'),progress=el('rdiCameraProgress');
  const demo=new URLSearchParams(location.search).get('camera_preview')==='1';
  let cfg={enabled:false,every:5,duration:30,cameras:[]};
  let nextCamera=0,completed=0,active=false,endTimer=null,finishCallback=null,revision=0;

  function clearMedia(){
    for(const node of view.querySelectorAll('video,iframe,img')){
      if(node.tagName==='VIDEO'){node.pause();node.removeAttribute('src');node.load();}
      if(node.tagName==='IFRAME')node.src='about:blank';
    }
    view.replaceChildren();
  }
  function stop(){
    clearTimeout(endTimer);endTimer=null;finishCallback=null;
    clearMedia();progress.style.transition='none';progress.style.width='0%';
    active=false;window.rdiCameraActive=false;layer.hidden=true;
    document.body.classList.remove('rdi-camera-active');
  }
  function finish(){
    if(!active)return;
    const resume=finishCallback;
    stop();
    if(!window.rdiGeoActive&&!window.rdiSpotActive && typeof resume==='function')resume();
  }
  function render(cam,duration,resume,isDemo=false){
    if(active||window.rdiGeoActive||window.rdiSpotActive)return false;
    active=true;window.rdiCameraActive=true;
    finishCallback=resume;
    document.body.classList.add('rdi-camera-active');
    layer.hidden=false;
    el('rdiCameraCountry').textContent=cam.country.toLocaleUpperCase('it');
    el('rdiCameraCity').textContent=cam.city;
    el('rdiCameraCredit').textContent=isDemo?
       'ANTEPRIMA GRAFICA · nessuna webcam trasmessa':
       'Immagini: '+cam.credit;
    el('rdiCameraType').textContent=isDemo?'● ANTEPRIMA':cam.kind==='image'?'● IMMAGINI AGGIORNATE':'● WEBCAM';
    clearMedia();
    if(isDemo){
      const placeholder=document.createElement('div');
      placeholder.className='rdi-camera-placeholder';
      placeholder.textContent='AREA VIDEO · TELECAMERA AUTORIZZATA';
      view.append(placeholder);
    }else{
      const tag=cam.kind==='iframe'?'iframe':cam.kind==='video'?'video':'img';
      const media=document.createElement(tag);
      media.src=cam.src;
      if(tag==='iframe'){
        media.title='Webcam '+cam.city+' · '+cam.credit;
        media.allow='autoplay; fullscreen';
        media.referrerPolicy='strict-origin-when-cross-origin';
      }else if(tag==='video'){
        media.autoplay=true;media.muted=true;media.defaultMuted=true;
        media.loop=true;media.playsInline=true;media.controls=false;
        media.addEventListener('error',finish,{once:true});
        media.addEventListener('loadeddata',()=>media.play().catch(finish),{once:true});
      }else{
        media.alt='Immagini '+cam.city+' · '+cam.credit;
        media.addEventListener('error',finish,{once:true});
      }
      view.append(media);
    }
    progress.style.transition='none';progress.style.width='0%';
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active){progress.style.transition='width '+duration*1000+'ms linear';progress.style.width='100%';}
    }));
    endTimer=setTimeout(finish,duration*1000);
    return true;
  }
  async function refreshConfig(){
    const token=++revision;
    try{
      const res=await fetch('./data/youtube-camera-breaks.json?ts='+Date.now(),
         {cache:'no-store',signal:AbortSignal.timeout(6000)});
      if(!res.ok)throw Error('config '+res.status);
      const parsed=parseCameraConfig(await res.json());
      if(token===revision)cfg=parsed;
    }catch(error){
      if(token===revision)cfg={enabled:false,every:5,duration:30,cameras:[]};
      // Fail closed: no new external camera slot if the permission registry is unavailable.
    }
  }
  function startIfDue(next){
    if(active||window.rdiGeoActive||window.rdiSpotActive)return false;
    completed++;
    if(!cfg.enabled||!slotDue(completed,cfg.every)||!cfg.cameras.length)return false;
    const cam=cfg.cameras[nextCamera%cfg.cameras.length];
    nextCamera++;
    return render(cam,cfg.duration,next);
  }
  window.rdiCameraBreak={startIfDue,stop,get state(){return {active,eligible:cfg.cameras.length,completed};}};
  refreshConfig();setInterval(refreshConfig,300000);
  if(demo){
    window.addEventListener('load',()=>{
      setTimeout(()=>render({country:'🇮🇹 ITALIA',city:'BOLOGNA',credit:'Solo anteprima',kind:'image'},30,null,true),1000);
    },{once:true});
  }
})();
