/* RDI sponsored homepage placement and archived advertising: Italy-local 30-day campaigns. */
(()=>{
 'use strict';
 const timezone='Europe/Rome',dayMs=86400000;
 const host=document.querySelector('.rdi-broadcast-layout');
 const newsList=document.getElementById('news-list');
 if(!host)return;
 let campaigns=[],loaded=false,slot=null;
 const getRomeDay=()=>{
  const p=new Intl.DateTimeFormat('en-GB',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const v=Object.fromEntries(p.filter(x=>x.type!=='literal').map(x=>[x.type,Number(x.value)]));
  return Date.UTC(v.year,v.month-1,v.day);
 };
 const startMs=ad=>Date.parse(String(ad.startDate||'')+'T00:00:00Z');
 const remaining=(ad,today)=>Number(ad.durationDays||30)-Math.round((today-startMs(ad))/dayMs);
 const eligible=(ad,today)=>Number.isFinite(startMs(ad))&&remaining(ad,today)>0&&today>=startMs(ad);
 const expired=(ad,today)=>Number.isFinite(startMs(ad))&&remaining(ad,today)<=0;
 const advertised=ad=>String(ad.title||'Pubblicità RDI');
 function manageSound(video,resume){
  const radio=document.getElementById('audio');
  video.addEventListener('play',()=>{
   if(radio&&!radio.paused)document.getElementById('stop')?.click();
   if(resume)resume.hidden=false;
  });
  radio?.addEventListener('play',()=>{if(!video.paused)video.pause();});
  if(resume)resume.addEventListener('click',()=>{video.pause();document.getElementById('play')?.click();resume.hidden=true;});
 }
 function addVideo(video,ad){
  video.controls=true;video.playsInline=true;video.preload='none';
  video.poster=ad.poster||'./RADIO-COVER.jpg';
  const source=document.createElement('source');
  source.type='video/mp4';source.src=ad.videoUrl||'';
  video.append(source);
 }
 function activeSlot(ad,days){
  const section=document.createElement('section');
  section.id='oriflame';section.className='rdi-oriflame';section.lang='it';
  section.dataset.campaign=ad.id;section.dataset.placement='active';
  section.setAttribute('aria-labelledby','oriflame-title');
  section.innerHTML=`<div class="rdi-ad-compact"><button class="rdi-ad-preview" type="button" aria-label="Guarda la pubblicità di Magda a schermo intero"><img class="rdi-ad-thumb" alt="Anteprima prodotti Oriflame" loading="lazy"><span class="rdi-ad-play" aria-hidden="true">▶</span></button><div class="rdi-ad-details"><small class="rdi-oriflame-label">PUBBLICITÀ · R.D.I.</small><h2 id="oriflame-title"></h2><span class="rdi-ad-description"></span><div class="rdi-ad-compact-actions"><button class="rdi-ad-watch" type="button">▶ Guarda la pubblicità</button><a class="rdi-oriflame-whatsapp" target="_blank" rel="noopener noreferrer">WhatsApp</a></div></div><div class="rdi-ad-offer"><strong>Questo spazio potrebbe essere anche tuo!</strong><span class="rdi-ad-counter">Ancora <b id="rdi-ad-days"></b> <span id="rdi-ad-days-unit">giorni</span> in evidenza</span></div></div><dialog class="rdi-ad-dialog" aria-label="Pubblicità Oriflame con Magda"><div class="rdi-ad-dialog-inner"><button type="button" class="rdi-ad-close" aria-label="Chiudi la pubblicità">✕</button><div class="rdi-ad-dialog-video"><video id="oriflame-video" aria-label="Spot pubblicitario Oriflame Italia" playsinline preload="none"></video></div><div class="rdi-ad-dialog-info"><h3>Scopri Oriflame con Magda</h3><p class="rdi-oriflame-person"><strong></strong> · <span></span></p><div class="rdi-oriflame-actions"><a class="rdi-oriflame-whatsapp" target="_blank" rel="noopener noreferrer">Scrivi su WhatsApp</a><a class="rdi-oriflame-phone">Chiama Magda</a></div><button id="oriflame-resume-radio" type="button" hidden>↩ Torna alla radio</button></div></div></dialog>`;
  section.querySelector('h2').textContent=advertised(ad);
  section.querySelector('.rdi-ad-description').textContent=ad.description||'';
  section.querySelector('.rdi-ad-thumb').src=ad.poster||'./RADIO-COVER.jpg';
  section.querySelector('.rdi-oriflame-person strong').textContent=ad.person||ad.brand||'';
  section.querySelector('.rdi-oriflame-person span').textContent=ad.role||'';
  section.querySelectorAll('.rdi-oriflame-whatsapp').forEach(w=>w.href=ad.whatsappUrl||'./publicitate.html');
  const p=section.querySelector('.rdi-oriflame-phone');p.href=ad.phoneHref||'./publicitate.html';
  p.textContent='Chiama '+(ad.phoneDisplay||'RDI');
  const video=section.querySelector('video');addVideo(video,ad);
  const dialog=section.querySelector('.rdi-ad-dialog');
  const open=()=>{if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');video.play().catch(()=>{});};
  const close=()=>{video.pause();if(dialog.open&&typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open');};
  section.querySelector('.rdi-ad-preview').addEventListener('click',open);
  section.querySelector('.rdi-ad-watch').addEventListener('click',open);
  section.querySelector('.rdi-ad-close').addEventListener('click',close);
  dialog.addEventListener('click',e=>{if(e.target===dialog)close();});
  dialog.addEventListener('close',()=>video.pause());
  manageSound(video,section.querySelector('#oriflame-resume-radio'));
  setCountdown(section,days);
  return section;
 }
 function setCountdown(section,days){
  const n=section.querySelector('#rdi-ad-days'),unit=section.querySelector('#rdi-ad-days-unit');
  if(n)n.textContent=String(days);
  if(unit)unit.textContent=days===1?'giorno':'giorni';
 }
 function vacantSlot(){
  const section=document.createElement('section');
  section.id='oriflame';section.className='rdi-oriflame rdi-ad-vacant';section.lang='it';
  section.dataset.placement='vacant';
  section.innerHTML=`<div class="rdi-ad-vacancy-inner"><small>SPAZIO PUBBLICITARIO · R.D.I.</small><h2>Questo spazio potrebbe essere anche tuo!</h2><p>Fai conoscere la tua attività alla comunità di Radio Românii din Italia.</p><div class="rdi-oriflame-actions"><a class="rdi-oriflame-whatsapp" href="./publicitate.html">Scopri lo spazio pubblicitario</a><a class="rdi-oriflame-phone" href="#news-filters">Vedi la categoria Pubblicità</a></div></div>`;
  return section;
 }
 function renderSlot(){
  const today=getRomeDay();
  const active=campaigns.filter(ad=>eligible(ad,today)).sort((a,b)=>startMs(b)-startMs(a))[0];
  const state=active?'active':'vacant';
  const id=active?.id||'';
  if(slot&&slot.dataset.placement===state&&(!active||slot.dataset.campaign===id)){
   if(active)setCountdown(slot,remaining(active,today));
  }else{
   const replacement=active?activeSlot(active,remaining(active,today)):vacantSlot();
   if(slot)slot.replaceWith(replacement);
   else host.insertAdjacentElement('afterend',replacement);
   slot=replacement;
  }
  if(document.querySelector('#news-filters button[data-category="Pubblicità"]')?.getAttribute('aria-pressed')==='true'){
   window.renderNews?.();
  }
 }
 function renderArchive(target,query){
  if(!target)return;
  const today=getRomeDay();
  const items=campaigns.filter(ad=>ad.archive!==false&&expired(ad,today))
   .filter(ad=>[ad.title,ad.brand,ad.description,ad.person].join(' ').toLocaleLowerCase('it').includes(String(query||'').toLocaleLowerCase('it')));
  target.replaceChildren();
  if(!loaded){const p=document.createElement('p');p.textContent='Caricamento pubblicità…';target.append(p);return;}
  if(!items.length){
   const p=document.createElement('p');p.className='rdi-ad-empty';
   p.textContent='Le pubblicità terminate resteranno disponibili qui. Nessuna campagna archiviata al momento.';
   target.append(p);return;
  }
  for(const ad of items){
   const card=document.createElement('article');card.className='news-item rdi-ad-archive-card';
   const video=document.createElement('video');video.className='rdi-ad-archive-video';addVideo(video,ad);
   manageSound(video,null);
   const badge=document.createElement('div');badge.className='news-label';badge.textContent='PUBBLICITÀ · ARCHIVIO';
   const title=document.createElement('h3');title.textContent=advertised(ad);
   const desc=document.createElement('p');desc.className='news-summary';desc.textContent=ad.description||'';
   const meta=document.createElement('div');meta.className='news-meta';
   const end=new Date(startMs(ad)+Number(ad.durationDays||30)*dayMs);
   meta.textContent=(ad.person||ad.brand||'RDI')+' · Campagna conclusa il '+new Intl.DateTimeFormat('it-IT',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(end);
   const actions=document.createElement('div');actions.className='rdi-oriflame-actions';
   if(ad.whatsappUrl){const a=document.createElement('a');a.href=ad.whatsappUrl;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Contatta '+(ad.person||'l’inserzionista');a.className='rdi-oriflame-whatsapp';actions.append(a);}
   if(ad.phoneHref){const a=document.createElement('a');a.href=ad.phoneHref;a.textContent=ad.phoneDisplay||'Chiama';a.className='rdi-oriflame-phone';actions.append(a);}
   card.append(video,badge,title,desc,meta,actions);target.append(card);
  }
 }
 window.rdiAdvertisingRenderNews=(target,query)=>{renderArchive(target||newsList,query);};
 function ensureFilter(){
  const filters=document.getElementById('news-filters');
  if(!filters||filters.querySelector('[data-category="Pubblicità"]'))return;
  const button=document.createElement('button');
  button.type='button';button.dataset.category='Pubblicità';
  button.setAttribute('aria-pressed','false');button.textContent='📢 Pubblicità';
  filters.append(button);
 }
 async function load(){
  try{
   const response=await fetch('./data/rdi-advertising.json?ts='+Date.now(),{cache:'no-store'});
   if(!response.ok)throw new Error('Advertising config: '+response.status);
   const data=await response.json();
   if(!Array.isArray(data.campaigns))throw new Error('Advertising campaigns invalid');
   campaigns=data.campaigns;loaded=true;renderSlot();
  }catch(e){
   console.warn('RDI advertising: fallback placement until config is available',e);
   if(!slot)renderSlot();
   setTimeout(load,60000);
  }
 }
 ensureFilter();renderSlot();load();
 setInterval(renderSlot,60000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)renderSlot();});
 window.addEventListener('focus',renderSlot);
 if(location.hash==='#oriflame')setTimeout(()=>slot?.scrollIntoView({block:'start'}),200);
})();
