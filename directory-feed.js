import{initializeApp,getApps}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import{getFirestore,collection,query,where,onSnapshot}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import{firebaseConfig}from"./firebase-config.js";
const app=getApps()[0]||initializeApp(firebaseConfig),db=getFirestore(app),host=document.getElementById("news-list");
if(host){let businesses=[],ads=[];const active=a=>a.status==="approved"&&a.expiresAt?.toMillis?.()>Date.now();
function card(data,ad){
 const art=document.createElement("article");art.className="news-item directory-promotion";art.dataset.directoryPromotion="1";
 const photos=[...(Array.isArray(data.imageUrls)?data.imageUrls:[]),data.imageUrl].filter(x=>typeof x==="string"&&/^https:\/\//.test(x)).filter((x,i,a)=>a.indexOf(x)===i);
 if(photos.length){const img=document.createElement("img");img.className="news-image";img.loading="lazy";img.alt=data.title||data.name;img.src=photos[0];art.append(img);if(photos.length>1){let current=0;const timer=setInterval(()=>{if(!art.isConnected){clearInterval(timer);return}current=(current+1)%photos.length;img.src=photos[current]},5000)}}
 const label=document.createElement("div");label.className="news-label";label.textContent=ad?"📢 Publicitate · 30 zile":"🏪 Activitate din comunitate";art.append(label);
 const h=document.createElement("h3");h.textContent=data.title||data.name;art.append(h);
 const controls=document.createElement("div");controls.className="directory-promotion-contacts";
 const link=(label,href)=>{const a=document.createElement("a");a.textContent=label;a.href=href;a.target="_blank";a.rel="noopener noreferrer";controls.append(a)};
 const phone=String(data.phone||"").replace(/[^+0-9]/g,"");if(phone)link("📞 Contact","tel:"+phone);
 const wa=String(data.whatsapp||"").replace(/\D/g,"");if(wa)link("💬 WhatsApp","https://wa.me/"+wa);
 if(/^https:\/\//i.test(data.website||""))link("🌐 Site web",data.website);
 if(data.address)link("📍 Posizione","https://www.google.com/maps/search/?api=1&query="+encodeURIComponent([data.address,data.city,data.province].filter(Boolean).join(", ")));
 if(controls.childElementCount)art.append(controls);
 const p=document.createElement("p");p.className="news-summary";p.textContent=(data.body||data.description||"").slice(0,220);art.append(p);
 const a=document.createElement("a");a.className="news-read";a.textContent="Deschide detaliile →";a.href=ad&&/^https:\/\//.test(data.linkUrl||"")?data.linkUrl:"./ghid.html";art.append(a);
 return art;
}
function render(){host.querySelectorAll('[data-directory-promotion="1"]').forEach(x=>x.remove());const items=[...businesses.slice(0,3).map(x=>card(x,false)),...ads.filter(active).slice(0,3).map(x=>card(x,true))];const existing=[...host.querySelectorAll(".news-item:not(.directory-promotion)")];items.forEach((item,i)=>{if(existing.length){const anchor=existing[Math.min((i+1)*3-1,existing.length-1)];anchor.after(item)}else host.append(item)})}
onSnapshot(query(collection(db,"directoryBusinesses"),where("status","==","approved")),s=>{businesses=s.docs.map(x=>x.data()).sort((a,b)=>(b.createdAt?.toMillis?.()||0)-(a.createdAt?.toMillis?.()||0));render()},console.warn);
onSnapshot(query(collection(db,"directoryAds"),where("status","==","approved")),s=>{ads=s.docs.map(x=>x.data());render()},console.warn);
const obs=new MutationObserver(m=>{if(m.some(x=>[...x.addedNodes].some(n=>n.nodeType===1&&!n.classList?.contains("directory-promotion"))))render()});obs.observe(host,{childList:true});setInterval(render,60000);
}