import{initializeApp,getApps}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import{getFirestore,collection,query,where,onSnapshot}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import{firebaseConfig}from"./firebase-config.js";
const app=getApps()[0]||initializeApp(firebaseConfig),db=getFirestore(app);
const img=document.getElementById("rdi-gold-image"),link=document.getElementById("rdi-gold-link"),message=document.getElementById("rdi-gold-message"),mark=document.getElementById("rdi-gold-mark");
let timer=null,all=[];
function valid(ad){const expires=ad.expiresAt?.toMillis?.()||0;return ad.status==="approved"&&ad.tier==="gold"&&expires>Date.now()&&/^https:\/\//.test(ad.imageUrl||"")&&/^https:\/\//.test(ad.linkUrl||"")}
function draw(){const active=all.filter(valid);if(!active.length){img.src="./RADIO-COVER.jpg";img.alt="Radio Românii din Italia";link.href="./ghid.html?tab=manage";message.textContent="Acest spațiu poate fi al tău";mark.textContent="Publicitate GOLD";return}
const ad=active[Math.floor(Date.now()/10000)%active.length];img.src=ad.imageUrl;img.alt=ad.title||"Publicitate GOLD";link.href=ad.linkUrl;message.textContent=ad.title||"Publicitate GOLD";mark.textContent="GOLD · Publicitate";}
try{onSnapshot(query(collection(db,"directoryAds"),where("status","==","approved")),s=>{all=s.docs.map(d=>d.data());draw()},()=>draw())}catch(e){console.warn("Gold ads",e)}
timer=setInterval(draw,10000);
