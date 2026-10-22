import{initializeApp,getApps}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import{getAuth,onAuthStateChanged}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import{getFirestore,collection,addDoc,query,where,onSnapshot,doc,updateDoc,serverTimestamp,Timestamp}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import{getStorage,ref,uploadBytes,getDownloadURL}from"https://www.gstatic.com/firebasejs/10.14.1/firebase-storage.js";
import{firebaseConfig}from"./firebase-config.js";
const app=getApps()[0]||initializeApp(firebaseConfig),db=getFirestore(app),auth=getAuth(app),storage=getStorage(app),$=id=>document.getElementById(id),adminEmail="ionut29019@gmail.com";let user=null,my=[],ads=[],allAds=[],requests=[],ownedUnsub=null,adsUnsub=null,pendingUnsub=null;
function el(tag,txt){const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;return n}
function button(txt,action){const b=el("button",txt);b.type="button";b.onclick=action;return b}
const admin=()=>user?.email?.toLowerCase()===adminEmail&&user.emailVerified;
const active=a=>a.status==="approved"&&a.expiresAt?.toMillis?.()>Date.now();
const date=t=>t?.toDate?.()?.toLocaleDateString("it-IT")||"—";
function renderOwner(){const box=$("my-businesses");if(!box)return;box.replaceChildren();if(!user){box.append(el("p","Accedi con Google nella sezione Aggiungi un'attività, poi torna qui."));return}if(!my.length)box.append(el("p","Nessuna attività associata al tuo account."));for(const b of my){const card=el("section");card.className="panel";card.append(el("h3",b.name),el("p","Stato: "+b.status));if(b.status==="approved"){card.append(button("✏️ Modifica informazioni",()=>editBusiness(b)),button("📢 Crea pubblicità",()=>createAd(b)));}box.append(card)}const adbox=$("my-ads");adbox.replaceChildren(el("h3","Le tue pubblicità"));for(const a of ads){const card=el("div");card.className="panel";card.append(el("strong",a.title),el("p","Stato: "+a.status+" · Scadenza: "+date(a.expiresAt)));if(active(a))card.append(button("Richiedi proroga",async()=>{const reason=prompt("Motivo della richiesta di proroga (max 300 caratteri):");if(!reason)return;try{await addDoc(collection(db,"directoryExtensionRequests"),{adId:a.id,businessId:a.businessId,uid:user.uid,reason:reason.slice(0,300),status:"pending",createdAt:serverTimestamp()});alert("Richiesta inviata all'amministratore.")}catch(e){alert(e.message)}}));adbox.append(card)}}
function editBusiness(b){const fields=[["name","Nome"],["description","Descrizione"],["phone","Telefono"],["whatsapp","WhatsApp"],["website","Sito web"],["address","Indirizzo"],["hours","Orari"]];const overlay=el("div");overlay.className="panel";const form=el("form");form.append(el("h3","Modifica "+b.name));const controls={};for(const [key,label]of fields){const l=el("label",label),i=key==="description"?el("textarea"):el("input");i.value=b[key]||"";i.required=["name","description","address"].includes(key);i.maxLength=key==="description"?1200:250;l.append(i);controls[key]=i;form.append(l)}const submit=el("button","Invia modifiche per approvazione");submit.type="submit";form.append(submit,button("Annulla",()=>overlay.remove()));form.onsubmit=async e=>{e.preventDefault();const changes={};for(const[key]of fields)changes[key]=controls[key].value.trim();submit.disabled=true;try{await addDoc(collection(db,"directoryBusinessEdits"),{businessId:b.id,uid:user.uid,changes,status:"pending",createdAt:serverTimestamp()});alert("Modifiche inviate per approvazione.");overlay.remove()}catch(err){alert(err.message)}finally{submit.disabled=false}};overlay.append(form);$("my-businesses").prepend(overlay);overlay.scrollIntoView({behavior:"smooth"})}
function createAd(b){
const overlay=el("div");overlay.className="panel";const form=el("form");
form.append(el("h3","📢 Publicitate pentru "+b.name),el("p","Publicitatea durează 30 de zile de la aprobare. Poți încărca o fotografie direct din telefon."));
const fields={};
function field(key,label,type,initial="",max=250){
 const l=el("label",label),i=el(type==="textarea"?"textarea":"input");
 if(type!=="textarea")i.type=type;
 i.value=initial;i.maxLength=max;i.required=key==="title"||key==="body";l.append(i);form.append(l);fields[key]=i;return i;
}
field("title","Titlu *","text","",250);
field("body","Mesaj * (maximum 500 caractere)","textarea","",500);
const tierLabel=el("label","Tipul publicității");const tier=el("select");for(const [value,label] of [["standard","Standard · afișare obișnuită"],["gold","GOLD · banner principal RDI (după aprobare)"]]){const option=el("option",label);option.value=value;tier.append(option)}tierLabel.append(tier);form.append(tierLabel);form.append(el("p","GOLD necesită imagine de copertă orizontală și aprobarea administratorului. Disponibilitatea și eventualele costuri sunt comunicate separat."));
const photoLabel=el("label","📷 Adaugă o fotografie din telefon (JPG, PNG sau WebP, max. 5 MB)");
const photo=el("input");photo.type="file";photo.accept="image/jpeg,image/png,image/webp";photoLabel.append(photo);form.append(photoLabel);
const preview=el("img");preview.style.cssText="display:none;max-width:100%;max-height:220px;object-fit:contain;border-radius:10px;margin:8px 0";form.append(preview);
let objectUrl=null;
photo.onchange=()=>{
 if(objectUrl)URL.revokeObjectURL(objectUrl);
 preview.style.display="none";const file=photo.files?.[0];if(!file)return;
 if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>5*1024*1024){alert("Selectează o imagine JPG, PNG sau WebP de maximum 5 MB.");photo.value="";return}
 objectUrl=URL.createObjectURL(file);preview.src=objectUrl;preview.style.display="block";
};
const urlFallback=field("imageUrl","Sau URL imagine (opțional)","url","",500);
const linkLabel=el("label","Unde duce anunțul?");const linkChoice=el("select");
let waDigits=String(b.whatsapp||"").trim().replace(/^@/,"").replace(/\D/g,"");
if(waDigits.startsWith("00"))waDigits=waDigits.slice(2);
if(/^3\d{8,10}$/.test(waDigits))waDigits="39"+waDigits;
const waLink=/^\d{8,15}$/.test(waDigits)?"https://wa.me/"+waDigits:"";
const destinations=[["site","🌐 Site-ul afacerii"],["whatsapp","💬 WhatsApp"],["guide","📍 Pagina din Ghid"],["custom","🔗 Alt link"]];
for(const [value,label]of destinations){if(value==="whatsapp"&&!waLink)continue;if(value==="site"&&!/^https:\/\//.test(b.website||""))continue;const o=el("option",label);o.value=value;linkChoice.append(o)}
linkLabel.append(linkChoice);form.append(linkLabel);
const custom=field("linkUrl","Link personalizat (doar dacă alegi Alt link)","url","",500);
function refreshLink(){custom.parentElement.hidden=linkChoice.value!=="custom";}linkChoice.onchange=refreshLink;refreshLink();
const status=el("p");status.className="status";form.append(status);
const send=el("button","Trimite publicitatea");send.type="submit";
form.append(send,button("Anulează",()=>{if(objectUrl)URL.revokeObjectURL(objectUrl);overlay.remove()}));
form.onsubmit=async e=>{
 e.preventDefault();if(!user)return;send.disabled=true;status.textContent="Se pregătește...";
 try{
 let imageUrl=urlFallback.value.trim();const file=photo.files?.[0];
 if(file){
   if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>5*1024*1024)throw Error("Imagine invalidă sau mai mare de 5 MB.");
   const ext=file.type==="image/png"?"png":file.type==="image/webp"?"webp":"jpg";
   const item=ref(storage,"directory-businesses/"+user.uid+"/ad-"+crypto.randomUUID()+"."+ext);
   status.textContent="Se încarcă fotografia...";
   await uploadBytes(item,file,{contentType:file.type});
   imageUrl=await getDownloadURL(item);
 }
 if(tier.value==="gold"&&!imageUrl)throw Error("Pentru GOLD trebuie adăugată o fotografie.");
 const choice=linkChoice.value;
 const linkUrl=choice==="whatsapp"?waLink:choice==="site"?b.website:choice==="guide"?"https://radioromanii.duckdns.org/ghid.html":custom.value.trim();
 if(!/^https:\/\//.test(linkUrl))throw Error("Link invalid. Folosește https://");
 status.textContent="Se trimite publicitatea...";
 await addDoc(collection(db,"directoryAds"),{
  title:fields.title.value.trim(),body:fields.body.value.trim(),imageUrl,tier:tier.value,
  linkUrl,businessId:b.id,uid:user.uid,status:"pending",createdAt:serverTimestamp()
 });
 alert("Publicitatea a fost trimisă spre aprobare.");if(objectUrl)URL.revokeObjectURL(objectUrl);overlay.remove();
 }catch(err){status.textContent="Eroare: "+err.message}finally{send.disabled=false}
};
overlay.append(form);$("my-businesses").prepend(overlay);overlay.scrollIntoView({behavior:"smooth"});
}
function adminPanel(){if(!admin())return;let box=$("directory-admin-workflow");if(!box){box=el("section");box.id="directory-admin-workflow";box.className="panel";$("admin-panel").prepend(box)}box.replaceChildren(el("h2","🔔 Richieste pubblicità e modifiche"));const waiting=allAds.filter(a=>a.status==="pending");box.append(el("p",waiting.length+" pubblicità in attesa · "+requests.filter(r=>r.status==="pending").length+" proroghe/modifiche in attesa"));for(const a of waiting){const line=el("div");line.className="panel";line.append(el("strong",a.title+" · "+(a.tier==="gold"?"GOLD":"Standard")),el("p",a.body),button("Approva per 30 giorni",()=>setAd(a,"approved")),button("Rifiuta",()=>setAd(a,"rejected")));box.append(line)}for(const r of requests.filter(x=>x.status==="pending")){const line=el("div");line.className="panel";line.append(el("p",r.type==="edit"?"Modifica attività: "+r.businessId:"Proroga pubblicità: "+r.adId),button("Approva",()=>handleRequest(r,true)),button("Rifiuta",()=>handleRequest(r,false)));box.append(line)}}
async function setAd(a,status){try{const data={status,reviewedAt:serverTimestamp()};if(status==="approved"){data.startsAt=serverTimestamp();data.expiresAt=Timestamp.fromMillis(Date.now()+30*86400000)}await updateDoc(doc(db,"directoryAds",a.id),data)}catch(e){alert(e.message)}}
async function handleRequest(r,approve){try{if(approve&&r.type==="extension"){const ad=allAds.find(a=>a.id===r.adId);if(ad)await updateDoc(doc(db,"directoryAds",ad.id),{expiresAt:Timestamp.fromMillis(Math.max(Date.now(),ad.expiresAt?.toMillis?.()||0)+30*86400000)})}if(approve&&r.type==="edit")await updateDoc(doc(db,"directoryBusinesses",r.businessId),{...r.changes,reviewedAt:serverTimestamp()});await updateDoc(doc(db,r.type==="edit"?"directoryBusinessEdits":"directoryExtensionRequests",r.id),{status:approve?"approved":"rejected",reviewedAt:serverTimestamp()})}catch(e){alert(e.message)}}
onAuthStateChanged(auth,u=>{user=u;for(const fn of [ownedUnsub,adsUnsub,pendingUnsub])fn?.();ownedUnsub=adsUnsub=pendingUnsub=null;my=[];ads=[];allAds=[];requests=[];renderOwner();if(!u)return;ownedUnsub=onSnapshot(query(collection(db,"directoryBusinesses"),where("uid","==",u.uid)),s=>{my=s.docs.map(x=>({id:x.id,...x.data()}));renderOwner()},console.warn);adsUnsub=onSnapshot(query(collection(db,"directoryAds"),where("uid","==",u.uid)),s=>{ads=s.docs.map(x=>({id:x.id,...x.data()}));renderOwner()},console.warn);if(admin()){pendingUnsub=onSnapshot(collection(db,"directoryAds"),s=>{allAds=s.docs.map(x=>({id:x.id,...x.data()}));adminPanel()},console.warn);for(const [path,type]of [["directoryExtensionRequests","extension"],["directoryBusinessEdits","edit"]])onSnapshot(query(collection(db,path),where("status","==","pending")),s=>{requests=requests.filter(x=>x.type!==type).concat(s.docs.map(x=>({id:x.id,...x.data(),type})));adminPanel()},console.warn)}});