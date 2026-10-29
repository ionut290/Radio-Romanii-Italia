/* Open the city webcam gallery over the homepage so the radio audio element keeps playing. */
(()=>{'use strict';
const links=document.querySelectorAll('.rdi-webcam-launch');
const overlay=document.getElementById('rdi-webcam-view');
const frame=document.getElementById('rdi-webcam-frame');
const close=document.getElementById('rdi-webcam-close');
if(!links.length||!overlay||!frame||!close)return;
let returnFocus=null;
function show(e){
 if(e)e.preventDefault();
 returnFocus=document.activeElement;
 overlay.classList.add('open');
 overlay.setAttribute('aria-hidden','false');
 document.body.classList.add('rdi-webcam-open');
 frame.src='./webcam.html';
 close.focus();
}
function hide(){
 overlay.classList.remove('open');
 overlay.setAttribute('aria-hidden','true');
 document.body.classList.remove('rdi-webcam-open');
 frame.src='about:blank';
 if(returnFocus&&typeof returnFocus.focus==='function')returnFocus.focus();
}
links.forEach(link=>link.addEventListener('click',show));
close.addEventListener('click',hide);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&overlay.classList.contains('open'))hide()});
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===frame.contentWindow&&e.data&&e.data.type==='rdi:webcam:close')hide()});
})();
