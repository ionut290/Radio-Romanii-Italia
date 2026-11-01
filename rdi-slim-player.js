/* Header radio controls reuse the existing audio, retry logic, and Cast. */
(()=>{
 const button=document.getElementById('rdi-header-toggle');
 const title=document.getElementById('rdi-now-playing');
 const audio=document.getElementById('audio');
 const play=document.getElementById('play');
 const stop=document.getElementById('stop');
 const volume=document.getElementById('volume');
 const miniVolume=document.getElementById('rdi-header-volume');
 const cast=document.getElementById('cast');
 const miniCast=document.getElementById('rdi-header-cast');
 if(!button||!title||!audio||!play||!stop)return;
 function updateButton(){
   const on=!audio.paused&&!audio.ended;
   button.textContent=on?'Ⅱ':'▶';
   button.setAttribute('aria-label',on?'Pausa radio':'Ascultă radioul');
   button.setAttribute('title',on?'Pausa':'Play');
   button.setAttribute('aria-pressed',String(on));
 }
 button.addEventListener('click',()=>{
   if(!audio.paused&&!audio.ended)stop.click();
   else play.click();
   queueMicrotask(updateButton);
 });
 ['playing','play','pause','ended','emptied'].forEach(evt=>audio.addEventListener(evt,updateButton));
 miniVolume?.addEventListener('input',()=>{if(volume){volume.value=miniVolume.value;volume.dispatchEvent(new Event('input',{bubbles:true}))}});
 volume?.addEventListener('input',()=>{if(miniVolume)miniVolume.value=volume.value});
 miniCast?.addEventListener('click',()=>cast?.click());
 updateButton();
 const endpoint='https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia';
 const fallbackCover=new URL('./RADIO-LOGO.png',location.href).href;
 const cover=document.createElement('img');
 cover.id='rdi-now-playing-cover';
 cover.alt='Copertina del brano in onda';
 cover.width=46;cover.height=46;
 cover.style.cssText='width:46px;height:46px;flex:0 0 46px;object-fit:cover;border-radius:8px;background:#152b46;box-shadow:0 2px 8px #0003';
 cover.src=fallbackCover;
 const trackBox=title.closest('.rdi-header-track');
 if(trackBox){trackBox.style.minWidth='0';trackBox.parentElement?.insertBefore(cover,trackBox);}
 cover.addEventListener('error',()=>{if(cover.src!==fallbackCover)cover.src=fallbackCover;});
 async function refreshTrack(){
  try{
   const response=await fetch(endpoint,{cache:'no-store',signal:AbortSignal.timeout(7000)});
   if(!response.ok)throw Error('HTTP '+response.status);
   const data=await response.json();
   const song=data?.now_playing?.song||{};
   const artist=String(song.artist||'').trim();
   const name=String(song.title||'').trim();
   let text=(artist&&name)?artist+' — '+name:(name||song.text||'');
   if(!text&&data?.live?.is_live)text=data.live.streamer_name||'Studio Live';
   title.textContent=text||'Radio Românii din Italia · Live 24/7';
   title.title=title.textContent;
   const art=String(song.art||'').trim();
   const coverUrl=art.startsWith('https://')?art:fallbackCover;
   if(cover.src!==coverUrl)cover.src=coverUrl;
   if(text&&'mediaSession'in navigator&&navigator.mediaSession.metadata){
     navigator.mediaSession.metadata=new MediaMetadata({title:name||text,artist:artist||'Radio Românii din Italia',album:'RDI · Live',artwork:[{src:coverUrl,sizes:'512x512'}]});
   }
  }catch(_){if(!title.dataset.hasTrack)title.textContent='Radio Românii din Italia · Live 24/7'}
 }
 const rawRefresh=refreshTrack;
 refreshTrack=async()=>{await rawRefresh();if(title.textContent!=='Radio Românii din Italia · Live 24/7')title.dataset.hasTrack='1'};
 refreshTrack();
 setInterval(refreshTrack,20000);
})();
