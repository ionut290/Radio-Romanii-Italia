// RDI public-directory admin corrections. Original public JSON remains untouched.
import {doc,getDoc,setDoc,serverTimestamp} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import {ref,uploadBytes,getDownloadURL} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-storage.js";
const FIELDS=[["phone","Telefono",40],["whatsapp","WhatsApp verificato",40],["email","Email aziendale",250],["website","Sito web",250],["hours","Orari",150],["address","Indirizzo",180],["description","Descrizione",1200]];
const clean=x=>String(x??"").trim();
const https=x=>{try{const u=new URL(x);return u.protocol==="https:"&&!!u.hostname}catch{return false}};
const el=(tag,value)=>{const n=document.createElement(tag);if(value!==undefined)n.textContent=value;return n};
function verify(fields) {
 if(fields.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email))throw Error("Email aziendale non valida.");
 if(fields.website&&!/^https?:\/\/[^\s]+$/i.test(fields.website))throw Error("Sito web non valido.");
 if(fields.address&&fields.address.length<3)throw Error("L'indirizzo deve contenere almeno tre caratteri.");
 if(fields.description&&fields.description.length<25)throw Error("La descrizione richiede almeno 25 caratteri.");
}
export function openPublicEditor({business,db,storage,getAdminUid}) {
 const uid=getAdminUid();
 if(!uid||!/^public-[A-Za-z0-9_-]+$/.test(clean(business.id)))throw Error("Solo l'amministratore può modificare una scheda pubblica.");
 const modal=el("dialog");modal.className="business-dialog";
 const body=el("form");body.className="business-detail";body.style.maxWidth="650px";
 const title=el("h2","Completa scheda: "+clean(business.name));body.append(title);
 body.append(el("p","Le modifiche saranno salvate separatamente, senza eliminare la scheda originale. Usa solo dati aziendali verificati."));
 const controls={};
 for(const [key,label,max] of FIELDS){
  const wrap=el("label",label);wrap.style.display="block";wrap.style.margin="10px 0";
  const input=key==="description"?el("textarea"):el("input");
  input.value=clean(business[key]);input.maxLength=max;
  if(key==="website")input.type="url";
  if(key==="email")input.type="email";
  input.style.width="100%";wrap.append(input);body.append(wrap);controls[key]=input;
 }
 const sourceLabel=el("label","Fonte dei nuovi recapiti (URL HTTPS)");
 const source=el("input");source.type="url";source.maxLength=500;
 source.value=clean(business.contactSourceUrl||"");source.placeholder="https://sito-ufficiale.example/contatti";
 source.style.width="100%";sourceLabel.append(source);body.append(sourceLabel);
 const photoLabel=el("label","Foto aziendale autorizzata (opzionale)");
 const photo=el("input");photo.type="file";photo.accept="image/jpeg,image/png,image/webp";
 photo.style.display="block";photoLabel.append(photo);body.append(photoLabel);
 const rightLabel=el("label");rightLabel.style.display="block";
 const rights=el("input");rights.type="checkbox";rights.style.width="auto";
 rightLabel.append(rights,el("span"," Dichiaro di avere un'autorizzazione valida alla pubblicazione della fotografia."));
 body.append(rightLabel);
 const status=el("p");status.setAttribute("role","status");status.className="status";body.append(status);
 const row=el("div");row.className="actions";
 const save=el("button","Salva correzioni");save.type="submit";
 const cancel=el("button","Annulla");cancel.type="button";cancel.className="secondary";
 cancel.onclick=()=>modal.close();row.append(save,cancel);body.append(row);
 body.onsubmit=async event=>{
  event.preventDefault();
  const changes={};
  try{
   if(!getAdminUid()||getAdminUid()!==uid)throw Error("Sessione amministratore terminata.");
   for(const [k] of FIELDS){const val=clean(controls[k].value);if(val!==clean(business[k]))changes[k]=val;}
   verify(changes);
   const contactsChanged=["phone","whatsapp","email"].some(k=>Object.hasOwn(changes,k));
   const src=clean(source.value);
   if(contactsChanged&&!https(src))throw Error("Per cambiare telefono, WhatsApp o email inserisci una fonte HTTPS verificabile.");
   if(src&&!https(src))throw Error("La fonte deve utilizzare HTTPS.");
   if(contactsChanged)changes.contactSourceUrl=src;
   if(Object.hasOwn(changes,"address"))changes.locationPrecision="city";
   const image=photo.files?.[0];
   if(image){
    if(!rights.checked)throw Error("Conferma prima i diritti sulla fotografia.");
    if(!["image/jpeg","image/png","image/webp"].includes(image.type)||image.size>5*1024*1024)throw Error("Sono ammesse foto JPG/PNG/WebP fino a 5 MB.");
    if((business.imageUrls?.length||0)>=10)throw Error("Questa attività ha già 10 fotografie.");
   }
   if(!Object.keys(changes).length&&!image){status.textContent="Non ci sono modifiche da salvare.";return;}
   save.disabled=true;cancel.disabled=true;status.textContent="Verifica dell'accesso al database...";
   const target=doc(db,"directoryOverrides",business.id);
   await getDoc(target); // Prevent orphan photo uploads if Firestore rules are not deployed.
   if(image){
    status.textContent="Caricamento fotografia autorizzata...";
    const ext=image.type==="image/png"?"png":image.type==="image/webp"?"webp":"jpg";
    const storageRef=ref(storage,"directory-businesses/"+uid+"/public-"+crypto.randomUUID()+"."+ext);
    await uploadBytes(storageRef,image,{contentType:image.type});
    const url=await getDownloadURL(storageRef);
    changes.imageUrls=[...(Array.isArray(business.imageUrls)?business.imageUrls:[]),url];
    changes.photoRightsStatus="permission-granted";
   }
   status.textContent="Salvataggio delle correzioni...";
   await setDoc(target,{...changes,updatedAt:serverTimestamp()},{merge:true});
   status.textContent="Scheda aggiornata: la guida mostra le modifiche dopo la sincronizzazione.";
   setTimeout(()=>modal.close(),1100);
  }catch(error){
   status.textContent="Salvataggio non riuscito: "+(error?.message||error);
  }finally{save.disabled=false;cancel.disabled=false;}
 };
 modal.append(body);document.body.append(modal);
 modal.addEventListener("close",()=>modal.remove(),{once:true});
 modal.addEventListener("click",e=>{if(e.target===modal)modal.close()});
 modal.showModal();
}
