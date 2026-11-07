/* RDI Video News: licensed, Italian-audio clips only.
   Security: items are approved manually in rights registry; no scraping or YouTube ripping.
   The segment is disabled until the first item meets ALL approval criteria.
*/
(()=>{'use strict';
const REGISTRY='./rdi-video-news-rights.json';
const MIN_GAP_MS=45*60*1000, MAX_CLIP_MS=8*60*1000;
let playlist=[], lastPlayed=0, index=0, active=false, loading=false, lastCheck=0, next=null;
const stage=document.querySelector('#stage');
if(!stage)return;
const layer=document.createElement('section');
layer.id='rdiLicensedVideoNews';
layer.setAttribute('aria-label','Servizio video autorizzato con audio italiano');
Object.assign(layer.style,{position:'absolute',inset:'0',zIndex:'55',background:'#061327',color:'#fff',display:'none',fontFamily:'Arial,sans-serif'});
const video=document.createElement('video');
video.setAttribute('playsinline','');video.preload='none';video.controls=false;video.muted=false;
Object.assign(video.style,{height:'100%',width:'100%',objectFit:'contain',background:'#000'});
const credit=document.createElement('div');
Object.assign(credit.style,{position:'absolute',bottom:'12px',left:'30px',right:'30px',padding:'12px 18px',background:'rgba(5,17,36,.85)',borderRadius:'9px',fontSize:'20px',fontWeight:'700'});
layer.append(video,credit);stage.append(layer);
function romeToday(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())}
function sameRomeDay(v){if(typeof v!=='string'||!v.trim())return false;
 const date=new Date(v);if(Number.isNaN(date.getTime()))return false;
 return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(date)===romeToday();
}
function eligible(x){
 if(!x||x.approved_for_youtube_live!==true||x.audio_language!=='it')return false;
 if(!sameRomeDay(x.published_at)||!sameRomeDay(x.event_date))return false;
 if(!x.audio_language_verified_at||!x.audio_language_verification_method||!x.rights_checked_at||!x.rights_evidence)return false;
 if(!x.source_id||!x.title||!x.source_page_url||!x.license_name||!x.license_url||!x.attribution)return false;
 const path=x.downloaded_file_path;
 // Same-origin local MP4 only. Explicitly disallow YouTube/third-party embeds.
 return typeof path==='string'&&/^\/(?!\/)[a-zA-Z0-9_./-]+\.mp4(?:\?[a-zA-Z0-9_=&-]+)?$/.test(path)&&!path.includes('..');
}
async function refresh(){
 if(loading)return;
 loading=true;
 try{
  const res=await fetch(REGISTRY+'?t='+Date.now(),{cache:'no-store'});
  if(!res.ok)throw Error('registry unavailable');
  const data=await res.json();lastCheck=Date.now();
  playlist=(data.broadcast?.enabled===true&&data.broadcast?.required_audio_language==='it')
   ? (data.videos||[]).filter(eligible) : [];
 }catch(e){playlist=[];console.warn('[RDI Video News] playlist disabled',e)}
 finally{loading=false}
}
function stop(){
 if(!active)return;
 active=false;window.rdiLicensedVideoActive=false;
 clearTimeout(next);next=null;video.pause();video.removeAttribute('src');video.load();
 layer.style.display='none';
 const callback=onDone;onDone=null;
 try{callback?.()}catch(e){console.warn('[RDI Video News] resume error',e)}
}
let onDone=null;
video.addEventListener('ended',stop);
video.addEventListener('error',stop);
function startIfDue(done){
 if(active||!playlist.length||Date.now()-lastPlayed<MIN_GAP_MS)return false;
 if(window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive||window.rdiWeatherActive||window.rdiDjPromoActive||window.rdiPhilosophyActive||window.rdiStoriaActive||window.rdiTop3Active||window.rdiCameraActive||window.rdiLandscapeActive)return false;
 const item=playlist[index++%playlist.length];
 if(!eligible(item))return false;
 active=true;window.rdiLicensedVideoActive=true;lastPlayed=Date.now();onDone=done;
 layer.style.display='block';
 credit.textContent=item.title+' • '+item.attribution;
 video.src=item.downloaded_file_path;
 video.currentTime=0;
 next=setTimeout(stop,Math.min(MAX_CLIP_MS,Math.max(10000,(Number(item.duration_seconds)||MAX_CLIP_MS)*1000+5000)));
 const attempt=video.play();
 if(attempt?.catch)attempt.catch(e=>{console.warn('[RDI Video News] autoplay refused; skip safely',e);stop()});
 return true;
}
window.rdiLicensedVideoNews={startIfDue,refresh,stop,getStatus:()=>({enabled:playlist.length>0,approvedClips:playlist.length,lastRegistryCheck:lastCheck,active})};
refresh();setInterval(refresh,5*60*1000);
})();
