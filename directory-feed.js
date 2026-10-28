import{initializeApp,getApps}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import{getFirestore,collection,query,where,onSnapshot}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import{firebaseConfig}from"./firebase-config.js";
const app=getApps()[0]||initializeApp(firebaseConfig),db=getFirestore(app),host=document.getElementById("news-list");
if(host){let businesses=[],ads=[];const sprites={"Restaurante românești":"./directory-category-images/00.png","Magazine românești":"./directory-category-images/01.png","Transport România–Italia":"./directory-category-images/02.png","Contabilitate și fiscalitate":"./directory-category-images/03.png","Traduceri și interpretariat":"./directory-category-images/04.png","Avocatură":"./directory-category-images/05.png","Construcții și renovări":"./directory-category-images/06.png","Curățenie":"./directory-category-images/07.png","Îngrijire și frumusețe":"./directory-category-images/08.png","Auto și mecanică":"./directory-category-images/09.png","Sănătate și servicii profesionale":"./directory-category-images/10.png","Alte servicii":"./directory-category-images/11.png","Voluntariat și colaborări":"./directory-category-images/12.png","Transport și logistică":"./directory-category-images/13.png","Asociații și comunitate":"./directory-category-images/14.png"};
function inferActivityCategory(data){
 const fields=[data.category,data.businessCategory,data.type,data.title,data.name,data.description,data.body].filter(Boolean).join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 const direct=[data.category,data.businessCategory,data.type].find(x=>sprites[x]);if(direct)return direct;
 if(/ristorante|restaurant|trattoria|pizzeria|catering|cucina|mangiare/.test(fields))return "Restaurante românești";
 if(/magazin|negozio|alimentari|macelleria|minimarket|supermerc|market|shop|produse|grocery|alimentar/.test(fields))return "Magazine românești";
 if(/transport|autotrasport|corriere|logistic|spedizion|autobus/.test(fields))return /romania.{0,16}italia|italia.{0,16}romania/.test(fields)?"Transport România–Italia":"Transport și logistică";
 if(/contabil|commercialista|fiscal|tax|account/.test(fields))return "Contabilitate și fiscalitate";
 if(/traduc|interpret|translation/.test(fields))return "Traduceri și interpretariat";
 if(/avvocat|legal|lawyer|studio legale/.test(fields))return "Avocatură";
 if(/costru|edil|ristruttur|murator|impresa edile/.test(fields))return "Construcții și renovări";
 if(/puliz|clean|sanific/.test(fields))return "Curățenie";
 if(/parrucch|estetic|beauty|salon|manicure|coafor/.test(fields))return "Îngrijire și frumusețe";
 if(/officina|meccanic|gommista|autoricambi|autoservice|auto/.test(fields))return "Auto și mecanică";
 if(/clinic|dentist|medic|sanitar|fisioterap|health|farmacia/.test(fields))return "Sănătate și servicii profesionale";
 if(/voluntar|colabor/.test(fields))return "Voluntariat și colaborări";
 if(/asociaz|comunit|associazion|cultur/.test(fields))return "Asociații și comunitate";
 return "Alte servicii";
}
function generatedActivityVisual(data){
 const category=inferActivityCategory(data),url=sprites[category];if(!url)return null;
 const key=String(data.id||data.uid||data.title||data.name||category);let hash=0;for(let i=0;i<key.length;i++)hash=(Math.imul(hash,31)+key.charCodeAt(i))>>>0;
 const frame=hash%10,x=frame%2?100:0,y=Math.floor(frame/2)*25;
 const visual=document.createElement("div");visual.className="news-image directory-generated-visual";
 visual.style.backgroundImage="linear-gradient(0deg,rgba(7,19,34,.55),rgba(7,19,34,.04)),url(\""+url+"\")";
 visual.style.backgroundSize="100% 100%, 200% 500%";visual.style.backgroundPosition="center, "+x+"% "+y+"%";visual.style.backgroundRepeat="no-repeat";visual.style.position="relative";
 visual.setAttribute("role","img");visual.setAttribute("aria-label","Imagine generată, ilustrativă pentru categoria "+category);
 const badge=document.createElement("span");badge.className="directory-generated-label";badge.textContent="Imagine generată · ilustrativă";badge.style.cssText="position:absolute;right:9px;bottom:9px;padding:5px 8px;border-radius:8px;background:#081a2dcc;color:#fff;font-size:11px;line-height:1.2";visual.append(badge);return visual;
}
const active=a=>a.status==="approved"&&a.expiresAt?.toMillis?.()>Date.now();
function card(data,ad){
 const art=document.createElement("article");art.className="news-item directory-promotion";art.dataset.directoryPromotion="1";
 const photos=[...(Array.isArray(data.imageUrls)?data.imageUrls:[]),data.imageUrl].filter(x=>typeof x==="string"&&/^https:\/\//.test(x)).filter((x,i,a)=>a.indexOf(x)===i);
 if(photos.length){const img=document.createElement("img");img.className="news-image";img.loading="lazy";img.alt=data.title||data.name;img.src=photos[0];art.append(img);if(photos.length>1){let current=0;const timer=setInterval(()=>{if(!art.isConnected){clearInterval(timer);return}current=(current+1)%photos.length;img.src=photos[current]},5000)}}
 else{const visual=generatedActivityVisual(data);if(visual)art.append(visual)}
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