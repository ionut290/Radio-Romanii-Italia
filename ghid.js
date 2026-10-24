import {createDirectoryMap, mergeBusinesses, filterBusinesses, categoryTheme, sourceNote, safeUrl} from "./directory-map.js?v=20261024-atlas-4";
import {buildDirectoryExtras,directoryIntro,composeDirectoryDescription,profileUrlAllowed} from "./directory-enrichment.js?v=20261024-details-1";
import {initializeApp} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import {getAuth,GoogleAuthProvider,signInWithPopup,signOut,onAuthStateChanged} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import {getFirestore,collection,addDoc,query,where,onSnapshot,serverTimestamp,doc,updateDoc} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import {getStorage,ref,uploadBytes,getDownloadURL} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-storage.js";
import {firebaseConfig} from "./firebase-config.js";
const $=id=>document.getElementById(id);
const categories=["Restaurante românești","Magazine românești","Transport România–Italia","Contabilitate și fiscalitate","Traduceri și interpretariat","Avocatură","Construcții și renovări","Curățenie","Îngrijire și frumusețe","Auto și mecanică","Sănătate și servicii profesionale","Alte servicii","Voluntariat și colaborări","Transport și logistică","Asociații și comunitate"];
for(const id of ["category","kind"]){const select=$(id);for(const c of categories){const o=document.createElement("option");o.value=c;o.textContent=c;select.append(o)}}
const app=initializeApp(firebaseConfig),auth=getAuth(app),db=getFirestore(app),storage=getStorage(app);
const adminEmail="ionut29019@gmail.com";let user=null,records=[],publicRecords=[],approvedRecords=[],cityIndex={},pending=[],stopPending=null,pageLimit=24;
const directoryMap=createDirectoryMap({onOpen:openBusiness});
const isAdmin=()=>user?.email?.toLowerCase()===adminEmail;
const safeLink=(value)=>{try{const u=new URL(value);return ["https:","http:"].includes(u.protocol)?u.href:null}catch{return null}};
const whatsappNumber=value=>{
 const raw=String(value||"").trim();if(!raw)return "";
 // Accept international prefixes, pasted wa.me links and old @00... values.
 let digits=raw.replace(/[^0-9]/g,"");
 if(digits.startsWith("00"))digits=digits.slice(2);
 if(/^3[0-9]{8,10}$/.test(digits))digits="39"+digits;
 return /^[1-9][0-9]{7,14}$/.test(digits)?digits:null;
};
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
const allowedImages=new Set(["image/jpeg","image/png","image/webp"]);
function validImages(files){const a=Array.from(files||[]);if(a.length>10)throw Error("Poți încărca maximum 10 fotografii.");for(const f of a)if(!allowedImages.has(f.type)||f.size>5*1024*1024)throw Error("Fotografiile trebuie să fie JPG, PNG sau WebP și maximum 5 MB fiecare.");return a}
$("photos").addEventListener("change",()=>{const dest=$("photo-preview");dest.replaceChildren();try{const a=validImages($("photos").files);for(const f of a){const img=node("img");img.src=URL.createObjectURL(f);img.alt=f.name;img.onload=()=>URL.revokeObjectURL(img.src);dest.append(img)}}catch(e){$("photos").value="";alert(e.message)}});
function businessImages(b){return Array.isArray(b.imageUrls)?b.imageUrls.filter(u=>typeof u==="string"&&safeLink(u)).slice(0,10):[]}
function contactLinks(b,container){
 const links=node("div",undefined,"actions");
 if(b.phone){const phone=String(b.phone).replace(/[^+0-9]/g,"");if(phone){const a=node("a","📞 Sună","action secondary");a.href="tel:"+phone;links.append(a)}}
 const isRdiVolunteer=b.category==="Voluntariat și colaborări"&&/radio românii din italia|radio romanii din italia|\\brdi\\b/i.test([b.name,b.description].join(" "));
 const number=whatsappNumber(b.whatsapp)||(isRdiVolunteer?whatsappNumber(b.phone)||"393892352575":null);
 if(number){const a=node("a",isRdiVolunteer?"🤝 Vreau să devin voluntar":"💬 WhatsApp","action");a.href="https://wa.me/"+number;a.target="_blank";a.rel="noopener noreferrer";links.append(a)}
 if(b.website){const href=safeLink(b.website);if(href){const a=node("a","🌐 Site web","action secondary");a.href=href;a.target="_blank";a.rel="noopener noreferrer";links.append(a)}}
 if(b.address&&!/^(online|activitate online)/i.test(b.address)){const a=node("a","📍 Google Maps","action secondary");a.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent([b.address,b.city,b.province,"Italia"].filter(Boolean).join(", "));a.target="_blank";a.rel="noopener noreferrer";links.append(a)}
 container.append(links);
}
function openBusiness(b){
 const dialog=node("dialog",undefined,"business-dialog");
 const inner=node("div",undefined,"business-detail");
 const close=node("button","✕ Închide","detail-close secondary");close.type="button";close.onclick=()=>dialog.close();inner.append(close);
 const images=businessImages(b);
 if(images.length){const cover=node("img",undefined,"detail-hero");cover.src=images[0];cover.alt="Fotografie: "+b.name;inner.append(cover);if(images.length>1){let i=0;const timer=setInterval(()=>{if(!dialog.isConnected){clearInterval(timer);return}i=(i+1)%images.length;cover.src=images[i]},5000);dialog.addEventListener("close",()=>clearInterval(timer),{once:true})}}
 inner.append(node("span",b.category||"Activitate","pill"),node("h2",b.name),node("p",[b.city,b.province,b.region].filter(Boolean).join(" · "),"muted"));
 const intro=directoryIntro(b);const about={ro:"Despre activitate",it:"Informazioni sull’attività",en:"About the business"};const lang=window.rdiLanguage?.()||"ro";
 inner.append(node("h3",about[lang]||about.ro),node("p",intro||({ro:"Descrierea detaliată nu este încă disponibilă.",it:"La descrizione dettagliata non è ancora disponibile.",en:"A detailed description is not available yet."}[lang]||"Descrierea detaliată nu este încă disponibilă.")));
 inner.append(buildDirectoryExtras(b,lang));
 inner.append(sourceNote(b,directoryMap.locate(b)));
 if(directoryMap.locate(b)){const focus=node("button","⌖ "+atlasText("showMap"),"action secondary");focus.type="button";focus.onclick=()=>{dialog.close();directoryMap.focus(b)};inner.append(focus)}
 if(images.length>1){const gallery=node("div",undefined,"photo-gallery");for(const url of images.slice(1)){const a=node("a");a.href=url;a.target="_blank";a.rel="noopener noreferrer";const img=node("img");img.src=url;img.loading="lazy";img.alt="Fotografie: "+b.name;a.append(img);gallery.append(a)}inner.append(gallery)}
 if(b.address)inner.append(node("p","📍 "+b.address));
 if(b.hours)inner.append(node("p","🕒 "+b.hours));
 contactLinks(b,inner);dialog.append(inner);document.body.append(dialog);
 dialog.addEventListener("close",()=>dialog.remove(),{once:true});dialog.addEventListener("click",e=>{if(e.target===dialog)dialog.close()});
 dialog.showModal();window.rdiTranslate?.();
}
function drawCard(b,admin=false){
 const el=node("article",undefined,"panel business business-teaser"+(admin?" pending":""));
 const images=businessImages(b);
 if(images.length){const cover=node("img",undefined,"business-cover");cover.src=images[0];cover.alt="Fotografie: "+b.name;cover.loading="lazy";el.append(cover);if(images.length>1){let i=0;const timer=setInterval(()=>{if(!el.isConnected){clearInterval(timer);return}i=(i+1)%images.length;cover.src=images[i]},5000)}}
 else{const placeholder=node("div",categoryTheme(b.category)[1],"business-placeholder");placeholder.style.color=categoryTheme(b.category)[0];placeholder.setAttribute("aria-hidden","true");el.append(placeholder)}
 const content=node("div",undefined,"business-teaser-content");
 content.append(node("span",b.category||"Activitate","pill"),node("h3",b.name),node("p",[b.city,b.province,b.region].filter(Boolean).join(" · "),"muted"));
 if(!admin)content.append(node("span",b.sourceUrl?atlasText("publicBadge"):atlasText("listedBadge"),b.sourceUrl?"directory-public-badge":"directory-listed-badge"));
 const preview=node("p",directoryIntro(b)||b.services||b.address||"","business-preview");content.append(preview);contactLinks(b,content);
 const open=node("button","Deschide detaliile →","action detail-open");open.type="button";open.onclick=()=>openBusiness(b);content.append(open);if(!admin && directoryMap.locate(b)){const show=node("button","⌖ "+atlasText("showMap"),"directory-show-map");show.type="button";show.onclick=()=>directoryMap.focus(b);content.append(show)}el.append(content);
 if(admin){const controls=node("div",undefined,"actions");for(const [status,label] of [["approved","Aprobă"],["rejected","Respinge"]]){const btn=node("button",label,status==="rejected"?"secondary":"");btn.onclick=async()=>{btn.disabled=true;try{await updateDoc(doc(db,"directoryBusinesses",b.id),{status,reviewedAt:serverTimestamp()})}catch(e){alert("Nu s-a putut actualiza: "+e.message)}finally{btn.disabled=false}};controls.append(btn)}el.append(controls)}
 return el;
}
const atlasMessages={ro:{results:"afaceri și servicii",showMap:"Vezi pe hartă",publicBadge:"Sursă publică · de confirmat",listedBadge:"Publicat pe RDI",empty:"Nu am găsit activități",emptyHelp:"Încearcă alt oraș sau elimină câteva filtre.",more:"Mai multe activități",all:"Toate",public:"listări din surse publice",managed:"listări RDI",coverage:"Ghidul include înregistrările consultate individual și listările RDI aprobate. Nu reprezintă toate firmele românești din Italia.",loadError:"Unele surse nu s-au încărcat. Listările RDI disponibile sunt afișate."},it:{results:"attività e servizi",showMap:"Mostra sulla mappa",publicBadge:"Fonte pubblica · da confermare",listedBadge:"Pubblicata su RDI",empty:"Nessuna attività trovata",emptyHelp:"Prova un’altra città o rimuovi alcuni filtri.",more:"Mostra altre attività",all:"Tutte",public:"schede da fonti pubbliche",managed:"schede RDI",coverage:"La guida include le schede consultate singolarmente e le attività approvate su RDI. Non rappresenta tutte le imprese romene in Italia.",loadError:"Alcune fonti non sono state caricate. Le schede RDI disponibili restano visibili."},en:{results:"businesses and services",showMap:"Show on map",publicBadge:"Public source · to be confirmed",listedBadge:"Published on RDI",empty:"No businesses found",emptyHelp:"Try a different town or remove some filters.",more:"Load more listings",all:"All",public:"public-source listings",managed:"RDI listings",coverage:"This guide includes individually retrieved public listings and approved RDI listings. It is not a complete census of Romanian businesses in Italy.",loadError:"Some sources could not be loaded. Available RDI listings remain visible."}};
function atlasText(key){return (atlasMessages[window.rdiLanguage?.()||"ro"]||atlasMessages.ro)[key]||key}
let sourceError=false,publicSources=[];
function filters(){return Object.fromEntries(["search","category","region","province","city"].map(id=>[id,$(id).value]))}
function renderChips(){
 const chips=$("directory-chips"),counts=new Map();for(const b of records)counts.set(b.category,(counts.get(b.category)||0)+1);
 chips.replaceChildren();
 for(const category of ["",...categories.filter(c=>counts.has(c))]){const btn=node("button");btn.append(node("span",category||atlasText("all")),node("small"," · "+(category?counts.get(category):records.length)));btn.type="button";btn.dataset.category=category;btn.style.setProperty("--category-color",categoryTheme(category)[0]);btn.classList.toggle("active",category===$("category").value);btn.setAttribute("aria-pressed",String(category===$("category").value));btn.onclick=()=>{$("category").value=category;pageLimit=24;render()};chips.append(btn)}
}
function render(){
 const found=filterBusinesses(records,filters());
 $("count").textContent=found.length+" "+atlasText("results");
 if(found.length)$("businesses").replaceChildren(...found.slice(0,pageLimit).map(b=>drawCard(b)));
 else{const empty=node("div",undefined,"directory-empty");empty.append(node("strong",atlasText("empty")),node("span",atlasText("emptyHelp")));$("businesses").replaceChildren(empty)}
 $("directory-more").hidden=found.length<=pageLimit || $("find-panel").hidden;$("directory-more").textContent=atlasText("more")+" ("+Math.min(24,Math.max(0,found.length-pageLimit))+")";
 directoryMap.update(found,cityIndex);renderChips();
 $("directory-coverage").textContent=publicRecords.length+" "+atlasText("public")+" · "+approvedRecords.length+" "+atlasText("managed")+". "+atlasText("coverage")+(sourceError?" "+atlasText("loadError"):"");
 window.rdiTranslate?.();
}
for(const id of ["search","category","region","province","city"])$(id).addEventListener("input",()=>{pageLimit=24;render()});
$("directory-reset").onclick=()=>{for(const id of ["search","category","region","province","city"])$(id).value="";pageLimit=24;render()};
$("directory-more").onclick=()=>{pageLimit+=24;render()};
document.addEventListener("directory-view-change",()=>{render()});
document.addEventListener("rdi-language-changed",render);
async function loadPublicDirectory(){
 const results=await Promise.allSettled([fetch("./data/directory-public.json?v=20261024-atlas-1",{cache:"no-cache"}).then(r=>{if(!r.ok)throw Error("Directory source unavailable");return r.json()}),fetch("./data/directory-cities.json?v=20261024-atlas-1").then(r=>{if(!r.ok)throw Error("Town coordinates unavailable");return r.json()})]);
 if(results[0].status==="fulfilled"){const data=results[0].value;publicRecords=Array.isArray(data.businesses)?data.businesses:[];publicSources=data.sources||[];
 for(const source of publicSources){if(!safeUrl(source.url))continue;const a=node("a",source.name+" ↗");a.href=source.url;a.target="_blank";a.rel="noopener noreferrer";$("directory-source-links").append(a)}}else sourceError=true;
 if(results[1].status==="fulfilled")cityIndex=results[1].value;
 records=mergeBusinesses(publicRecords,approvedRecords);render();
}
loadPublicDirectory();
onSnapshot(query(collection(db,"directoryBusinesses"),where("status","==","approved")),snapshot=>{approvedRecords=snapshot.docs.map(d=>({id:d.id,...d.data()}));records=mergeBusinesses(publicRecords,approvedRecords);render()},error=>{console.warn("RDI listings unavailable",error.code);sourceError=true;render()});
function renderPending(){$("pending").replaceChildren(...(pending.length?pending.map(b=>drawCard(b,true)):[node("p","Nu există cereri în așteptare.")]))}
onAuthStateChanged(auth,u=>{user=u;$("signin").hidden=!!u;$("signout").hidden=!u;$("business-form").hidden=!u;$("admin-panel").hidden=!isAdmin();$("direct-label").hidden=!isAdmin();$("identity").textContent=u?"Conectat: "+(u.displayName||u.email)+(isAdmin()?" · Administrator":""):"Conectează-te pentru a înscrie o afacere.";if(stopPending){stopPending();stopPending=null}if(isAdmin()){stopPending=onSnapshot(query(collection(db,"directoryBusinesses"),where("status","==","pending")),snapshot=>{pending=snapshot.docs.map(d=>({id:d.id,...d.data()}));renderPending()},e=>$("pending").textContent="Nu pot încărca cererile: "+e.message)}});
$("signin").onclick=async()=>{try{await signInWithPopup(auth,new GoogleAuthProvider())}catch(e){alert("Autentificare nereușită: "+e.message)}};
$("signout").onclick=()=>signOut(auth);
$("business-form").addEventListener("submit",async e=>{e.preventDefault();if(!user)return;const submit=$("submit");submit.disabled=true;const status=$("submit-status");status.textContent="Se trimite...";const val=id=>$(id).value.trim();const website=val("website");if(website&&!safeLink(website)){status.textContent="Adresa site-ului nu este validă.";submit.disabled=false;return}const details=Object.fromEntries(["services","products","prices","languages","payments","access","delivery","facebookUrl","instagramUrl"].map(id=>[id,val(id)]));
if(!profileUrlAllowed(details.facebookUrl,"facebook.com")||!profileUrlAllowed(details.instagramUrl,"instagram.com")){status.textContent="Link Facebook sau Instagram invalid. Folosește linkul complet https://";submit.disabled=false;return}
const richDescription=composeDirectoryDescription(val("description"),details);
if(richDescription.length>1200){status.textContent="Descrierea și informațiile suplimentare depășesc limita de 1200 de caractere ("+richDescription.length+"). Scurtează textul.";submit.disabled=false;return}
const wa=val("whatsapp");if(wa&&!whatsappNumber(wa)){status.textContent="Număr WhatsApp invalid. Include prefixul țării, de exemplu +39.";submit.disabled=false;return}try{const photos=validImages($("photos").files);const imageUrls=[];for(let i=0;i<photos.length;i++){status.textContent="Se încarcă fotografia "+(i+1)+" din "+photos.length+"...";const file=photos[i];const ext=file.type==="image/png"?"png":file.type==="image/webp"?"webp":"jpg";const path="directory-businesses/"+user.uid+"/"+crypto.randomUUID()+"."+ext;const item=ref(storage,path);try{await uploadBytes(item,file,{contentType:file.type});imageUrls.push(await getDownloadURL(item))}catch(uploadError){const code=uploadError?.code||"storage/unknown";const proceed=window.confirm("Încărcarea fotografiei "+(i+1)+" a eșuat ("+code+"). Poți publica anunțul fără fotografiile rămase și le poți adăuga ulterior după repararea Storage. Continui publicarea fără aceste fotografii?");if(!proceed)throw uploadError;status.textContent="Fotografiile nu au putut fi încărcate. Se publică anunțul fără cele rămase.";break}}status.textContent="Se trimite afacerea...";await addDoc(collection(db,"directoryBusinesses"),{imageUrls,uid:user.uid,name:val("name"),category:val("kind"),region:val("area"),province:val("county"),city:val("town"),address:val("address"),phone:val("phone"),whatsapp:wa,website,hours:val("hours"),description:richDescription,status:isAdmin()&&$("direct-approve").checked?"approved":"pending",createdAt:serverTimestamp()});status.textContent=isAdmin()&&$("direct-approve").checked?"Afacerea a fost publicată.":"Cererea a fost trimisă. Va apărea după aprobarea administratorului.";e.target.reset();$("photo-preview").replaceChildren()}catch(err){status.textContent="Nu s-a putut trimite: "+err.message}finally{submit.disabled=false}});

// Afișează anunțurile de voluntariat la un singur clic.
const volunteerBtn=document.getElementById("volunteer-show");
if(volunteerBtn)volunteerBtn.addEventListener("click",()=>{document.getElementById("category").value="Voluntariat și colaborări";document.getElementById("search").value="";for(const id of ["region","province","city"])document.getElementById(id).value="";document.querySelector("[data-panel=find]")?.click();render();document.getElementById("find-panel")?.scrollIntoView({behavior:"smooth",block:"start"});});

document.getElementById("show-volunteers")?.addEventListener("click",()=>{document.getElementById("category").value="Voluntariat și colaborări";for(const id of ["search","region","province","city"])document.getElementById(id).value="";render();});
