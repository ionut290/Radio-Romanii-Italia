/* Oriflame campaign: user-initiated playback, existing radio controls preserved. */
(()=>{
 'use strict';
 if(document.getElementById('oriflame'))return;
 const anchor=document.querySelector('.rdi-broadcast-layout');
 if(!anchor)return;
 const section=document.createElement('section');
 section.id='oriflame';section.className='rdi-oriflame';section.lang='it';section.setAttribute('aria-labelledby','oriflame-title');
 section.innerHTML=`<div class="rdi-oriflame-media"><video id="oriflame-video" controls playsinline preload="none" poster="https://media-cdn.oriflame.com/productImage?externalMediaId=product-management-media%2fProducts%2f47511%2f47511_1.png&amp;MediaId=19156172&amp;Version=1" aria-label="Spot Oriflame Italia con Magda Niculae, 51 secondi"><source src="https://cdn.creativeclaw.co/u/d1fc9b13/videos/b9240cfe-512d-4d8c-93db-2aaf0a44d9a6.mp4" type="video/mp4">Il tuo browser non supporta il video.</video><span>▶ Guarda lo spot · 51 secondi</span></div><div class="rdi-oriflame-copy"><span class="rdi-oriflame-label">PUBBLICITÀ · R.D.I.</span><h2 id="oriflame-title">Scopri Oriflame<br>con Magda.</h2><p>Profumi, make-up e cura della pelle: un mondo di bellezza e opportunità da conoscere insieme.</p><div class="rdi-oriflame-person"><strong>Magda Niculae</strong><span>Direttrice di vendita Oriflame</span></div><div class="rdi-oriflame-actions"><a class="rdi-oriflame-whatsapp" href="https://wa.me/393291184717?text=Ciao%20Magda%2C%20ho%20visto%20lo%20spot%20su%20R.D.I.%20e%20vorrei%20saperne%20di%20pi%C3%B9." target="_blank" rel="noopener noreferrer">Scrivi su WhatsApp ↗</a><a class="rdi-oriflame-phone" href="tel:+393291184717">Chiama 329 118 4717</a></div><button id="oriflame-resume-radio" type="button" hidden>↩ Torna alla radio</button></div>`;
 anchor.insertAdjacentElement('afterend',section);
 const video=section.querySelector('video'),radio=document.getElementById('audio'),resume=document.getElementById('oriflame-resume-radio');
 video.addEventListener('play',()=>{
  if(radio)document.getElementById('stop')?.click();
  resume.hidden=false;
 });
 radio?.addEventListener('play',()=>{if(!video.paused)video.pause();});
 resume.addEventListener('click',()=>{video.pause();document.getElementById('play')?.click();resume.hidden=true;});
 if(location.hash==='#oriflame')requestAnimationFrame(()=>section.scrollIntoView({block:'start'}));
})();
