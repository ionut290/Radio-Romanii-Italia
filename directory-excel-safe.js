// Admin-only Excel workflow: bounded loading, verified preview and safe bulk import.
import {collection,getDocs,doc,updateDoc,addDoc,serverTimestamp,writeBatch} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
const FIELDS=["origin","id","name","category","region","province","city","address","phone","whatsapp","website","hours","description","status"];
const EDIT=["name","address","phone","whatsapp","website","hours","description"];
const str=x=>String(x??"").trim();
const normalize=x=>str(x).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it").replace(/[^\p{L}\p{N}]+/gu," ").trim();
const key=b=>[b.name,b.city,b.address].map(normalize).join("|");
let libraryPromise;
function timeout(p,ms,message){let timer;return Promise.race([p,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(message)),ms)})]).finally(()=>clearTimeout(timer));}
function loadScript(src){return new Promise((resolve,reject)=>{
 const el=document.createElement("script");let finished=false;
 const finish=err=>{if(finished)return;finished=true;clearTimeout(timer);el.onload=null;el.onerror=null;if(err){el.remove();reject(err)}else resolve(window.XLSX)};
 const timer=setTimeout(()=>finish(Error("Timeout del lettore Excel")),12000);
 el.src=src;el.async=true;el.onload=()=>finish(window.XLSX?null:Error("Libreria Excel non disponibile"));el.onerror=()=>finish(Error("CDN Excel non raggiungibile"));document.head.append(el);
});}
function excel(){return libraryPromise ||= (async()=>{
 if(window.XLSX)return window.XLSX;
 let err;
 for(const url of ["https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js","https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"]){
  try{return await loadScript(url)}catch(e){err=e}
 }
 throw Error("Impossibile caricare il lettore Excel (connessione o blocco CDN). "+(err?.message||""));
})().catch(e=>{libraryPromise=null;throw e})}
const limits={name:[2,110],category:[3,80],region:[2,70],province:[2,70],city:[2,70],address:[3,180],phone:[0,40],whatsapp:[0,40],website:[0,250],hours:[0,150],description:[25,1200]};
const valid=(o,fields)=>fields.every(k=>{const v=str(o[k]),[min,max]=limits[k];return v.length>=min&&v.length<=max&&(k!=="website"||!v||/^https?:\/\/[^\s]+$/i.test(v))});
const requiredNew=["name","category","region","province","city","address","phone","whatsapp","website","hours","description"];
const readBusinesses=db=>timeout(getDocs(collection(db,"directoryBusinesses")),25000,"Firebase non risponde entro 25 secondi. Controlla rete, accesso e autorizzazioni.");
export function mountExcel({db,admin,getPublic,getUid}){
 const root=document.getElementById("rdi-excel-admin");if(!root)return()=>{};
 const exportBtn=root.querySelector("#rdi-excel-export"),importBtn=root.querySelector("#rdi-excel-import"),picker=root.querySelector("#rdi-excel-file"),report=document.getElementById("rdi-excel-report"),confirmBtn=document.getElementById("rdi-excel-confirm"),cancelBtn=document.getElementById("rdi-excel-cancel");
 let staging=[],busy=false;
 const status=document.createElement("span");status.id="rdi-excel-status";status.setAttribute("role","status");status.setAttribute("aria-live","polite");status.style.cssText="flex-basis:100%;font-size:12px;font-weight:600;color:#0f5132;";root.append(status);
 const show=message=>{status.textContent=message};
 const requireAdmin=()=>{if(!admin())throw Error("Accesso amministratore non valido. Esci e rientra con l'account autorizzato.")};
 const reset=()=>{staging=[];report.hidden=true;picker.value="";};
 const setBusy=value=>{busy=value;importBtn.disabled=value;exportBtn.disabled=value;confirmBtn.disabled=value||!staging.length;cancelBtn.disabled=value};
 const fetchSnapshot=async()=>{requireAdmin();show("Connessione a Firebase...");return readBusinesses(db)};
 exportBtn.onclick=async()=>{try{requireAdmin();setBusy(true);show("Preparazione del backup Excel...");const XLSX=await excel();const data=await fetchSnapshot();
  const rows=[...getPublic().map(b=>({...b,origin:"public-json",id:str(b.id)})),...data.docs.map(d=>({...d.data(),origin:"firestore",id:d.id}))].map(b=>Object.fromEntries(FIELDS.map(k=>[k,b[k]??""])));
  const wb=XLSX.utils.book_new();XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(rows,{header:FIELDS}),"Attivita");XLSX.writeFile(wb,"RDI-attivita-"+new Date().toISOString().slice(0,10)+".xlsx");show("Backup esportato: "+rows.length+" schede.");
 }catch(e){show("Errore: "+e.message);alert(e.message)}finally{setBusy(false)}};
 importBtn.onclick=()=>{if(!busy&&admin())picker.click()};
 picker.onchange=async()=>{
  const file=picker.files[0];if(!file||busy)return;reset();setBusy(true);
  try{requireAdmin();if(file.size>8000000)throw Error("File oltre 8 MB.");show("Lettura di "+file.name+"...");
   const XLSX=await excel();const book=XLSX.read(await file.arrayBuffer(),{type:"array"}),sheet=book.Sheets.Attivita||book.Sheets[book.SheetNames[0]];
   if(!sheet)throw Error("Foglio Attivita vuoto");const rows=XLSX.utils.sheet_to_json(sheet,{defval:"",raw:false});
   if(!rows.length||rows.length>10000)throw Error("Il file deve contenere da 1 a 10.000 attività.");
   if(!FIELDS.every(f=>Object.hasOwn(rows[0],f)))throw Error("Colonne Excel mancanti: "+FIELDS.filter(f=>!Object.hasOwn(rows[0],f)).join(", "));
   const snap=await fetchSnapshot();show("Verifica di "+rows.length+" schede e duplicati...");
   const byId=new Map(snap.docs.map(d=>[d.id,d.data()]));const publicById=new Map(getPublic().map(d=>[str(d.id),d]));
   const existingKeys=new Set([...snap.docs.map(d=>key(d.data())),...getPublic().map(key)]);
   const seenIds=new Set(),seenKeys=new Set(),problems=[];let skippedPublic=0,duplicates=0,unchanged=0,updates=0,adds=0;
   for(let i=0;i<rows.length;i++){
    const r=rows[i],line=i+2,origin=str(r.origin),id=str(r.id);
    if(!FIELDS.every(f=>Object.hasOwn(r,f))){problems.push("Riga "+line+": colonne mancanti");continue}
    const recordKey=key(r);
    if(id&&seenIds.has(origin+":"+id)){duplicates++;continue}if(id)seenIds.add(origin+":"+id);
    if(origin==="public-json"&&publicById.has(id)){skippedPublic++;continue}
    if(origin==="firestore"){
     if(!id||!byId.has(id)){problems.push("Riga "+line+": ID Firestore sconosciuto");continue}
     const old=byId.get(id);const changes=Object.fromEntries(EDIT.filter(k=>str(r[k])&&str(old[k])!==str(r[k])).map(k=>[k,str(r[k])]));
     if(!Object.keys(changes).length){unchanged++;continue}
     if(!valid(changes,Object.keys(changes))){problems.push("Riga "+line+": valori da aggiornare non validi");continue}
     staging.push({kind:"update",id,changes});updates++;continue;
    }
    if(origin!=="new"&&origin!=="public-json"){problems.push("Riga "+line+": origine sconosciuta");continue}
    if(origin==="new"&&id){problems.push("Riga "+line+": per nuove schede l'ID deve essere vuoto");continue}
    if(!recordKey||existingKeys.has(recordKey)||seenKeys.has(recordKey)){duplicates++;continue}
    if(!valid(r,requiredNew)){problems.push("Riga "+line+": campi obbligatori incompleti o non validi");continue}
    seenKeys.add(recordKey);staging.push({kind:"add",data:Object.fromEntries(requiredNew.map(k=>[k,str(r[k])]))});adds++;
   }
   report.hidden=false;
   report.querySelector("#rdi-excel-summary").textContent=updates+" aggiornamenti, "+adds+" nuove schede, "+skippedPublic+" già nel catalogo pubblico, "+duplicates+" duplicati, "+unchanged+" senza modifiche, "+problems.length+" anomalie escluse. "+problems.slice(0,12).join("; ");
   show("Analisi completata: "+staging.length+" operazioni pronte da confermare."+(problems.length?" Alcune righe sono escluse: consulta il riepilogo.":""));
  }catch(e){reset();show("Errore importazione: "+e.message);alert("Importazione Excel: "+e.message)}finally{picker.value="";setBusy(false)}
 };
 cancelBtn.onclick=()=>{if(!busy){reset();show("Importazione annullata: nessuna modifica applicata.")}};
 confirmBtn.onclick=async()=>{
  if(busy||!staging.length)return;requireAdmin();
  if(!confirm("Applicare "+staging.length+" operazioni in Firebase? Esegui prima Esporta Excel per un backup. Le schede già pubblicate non saranno eliminate."))return;
  setBusy(true);let done=0;
  try{
   const uid=getUid?.();if(!uid)throw Error("Utente Firebase non disponibile. Rientra con Google.");
   // Small atomic groups: no duplicated edits to the same document inside one batch.
   for(let pos=0;pos<staging.length;pos+=40){requireAdmin();const batch=writeBatch(db);const part=staging.slice(pos,pos+40);
    for(const item of part){if(item.kind==="update")batch.update(doc(db,"directoryBusinesses",item.id),{...item.changes,status:"approved",reviewedAt:serverTimestamp()});
     else batch.set(doc(collection(db,"directoryBusinesses")),{...item.data,uid,imageUrls:[],status:"approved",createdAt:serverTimestamp()});}
    show("Salvataggio Firebase: "+done+" di "+staging.length+" completate...");
    await timeout(batch.commit(),45000,"Firebase non ha confermato il salvataggio entro 45 secondi: esito incerto. Non ripetere subito l'importazione, aggiorna prima la pagina e verifica le attività.");
    done+=part.length;show("Salvataggio Firebase: "+done+" di "+staging.length+" completate.");
   }
   reset();show("Importazione completata: "+done+" operazioni. Aggiorna la mappa per verificare le nuove attività.");alert("Importazione completata: "+done+" operazioni.");
  }catch(e){show("Importazione interrotta dopo "+done+" operazioni confermate. "+e.message);alert("Operazioni confermate: "+done+" di "+staging.length+". "+e.message)}finally{setBusy(false)}
 };
 return ()=>{reset();status.remove();root.hidden=true;};
}
