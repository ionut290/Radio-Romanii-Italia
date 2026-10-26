// Loaded only after verified administrator signs in. Never imported at main app startup.
import {collection,getDocs,doc,updateDoc,serverTimestamp} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
const FIELDS=["origin","id","name","category","region","province","city","address","phone","whatsapp","website","hours","description","status"];
const EDIT=["name","address","phone","whatsapp","website","hours","description"];
const str=x=>String(x??"").trim();
let libraryPromise;
function excel(){return libraryPromise ||= new Promise((resolve,reject)=>{
 if(window.XLSX){resolve(window.XLSX);return}
 const script=document.createElement("script");script.src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js";
 script.onload=()=>window.XLSX?resolve(window.XLSX):reject(Error("Excel non disponibile"));
 script.onerror=()=>reject(Error("Caricamento lettore Excel non riuscito"));document.head.append(script);
}).catch(e=>{libraryPromise=null;throw e})}
function validate(row){const limits={name:[2,110],address:[3,180],phone:[0,40],whatsapp:[0,40],website:[0,250],hours:[0,150],description:[25,1200]};return Object.entries(row).every(([k,v])=>{const limitsFor=limits[k];return !!limitsFor&&v.length>=limitsFor[0]&&v.length<=limitsFor[1]&&(k!=="website"||!v||/^https?:\/\//.test(v));})}
export function mountExcel({db,admin,getPublic}){
 const root=document.getElementById("rdi-excel-admin");if(!root)return()=>{};
 const exportBtn=root.querySelector("#rdi-excel-export"),importBtn=root.querySelector("#rdi-excel-import"),picker=root.querySelector("#rdi-excel-file"),report=document.getElementById("rdi-excel-report"),confirmBtn=document.getElementById("rdi-excel-confirm"),cancelBtn=document.getElementById("rdi-excel-cancel");
 let staging=[],currentUser=admin;
 const requireAdmin=()=>{if(!currentUser())throw Error("Permesso amministratore mancante")};
 const reset=()=>{staging=[];report.hidden=true;picker.value="";};
 exportBtn.onclick=async()=>{try{requireAdmin();exportBtn.disabled=true;const XLSX=await excel();const data=await getDocs(collection(db,"directoryBusinesses"));
 const rows=[...getPublic().map(b=>({...b,origin:"public-json",id:str(b.id)})),...data.docs.map(d=>({...d.data(),origin:"firestore",id:d.id}))].map(b=>Object.fromEntries(FIELDS.map(k=>[k,b[k]??""])));
 const wb=XLSX.utils.book_new();XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(rows,{header:FIELDS}),"Attivita");XLSX.writeFile(wb,"RDI-attivita-"+new Date().toISOString().slice(0,10)+".xlsx");
 }catch(e){alert(e.message)}finally{exportBtn.disabled=false}};
 importBtn.onclick=()=>{if(currentUser())picker.click()};
 picker.onchange=async()=>{try{requireAdmin();const file=picker.files[0];reset();if(!file)return;if(file.size>8e6)throw Error("File troppo grande");
 const XLSX=await excel();const book=XLSX.read(await file.arrayBuffer(),{type:"array"}),sheet=book.Sheets[book.SheetNames[0]];if(!sheet)throw Error("Foglio vuoto");
 const rows=XLSX.utils.sheet_to_json(sheet,{defval:"",raw:false});if(rows.length>10000)throw Error("Troppe righe");
 const snap=await getDocs(collection(db,"directoryBusinesses")),byId=new Map(snap.docs.map(d=>[d.id,d.data()]));const seen=new Set();const problems=[];let skipped=0;
 rows.forEach((r,i)=>{const line=i+2,origin=str(r.origin),id=str(r.id);
 if(!FIELDS.every(f=>Object.hasOwn(r,f))){problems.push("Riga "+line+": colonne mancanti");return}
 if(origin==="public-json"){skipped++;return}
 if(origin!=="firestore"||!byId.has(id)){problems.push("Riga "+line+": origine o ID non valido");return}
 if(seen.has(id)){problems.push("Riga "+line+": ID ripetuto");return}seen.add(id);
 const before=byId.get(id),changes=Object.fromEntries(EDIT.filter(k=>str(before[k])!==str(r[k])).map(k=>[k,str(r[k])]));
 if(Object.keys(changes).length){if(!validate(changes))problems.push("Riga "+line+": dati non validi");else staging.push({id,changes})}
 });
 report.hidden=false;report.querySelector("#rdi-excel-summary").textContent=staging.length+" modifiche Firestore, "+skipped+" schede pubbliche non modificabili, "+problems.length+" errori. "+problems.slice(0,8).join("; ");
 confirmBtn.disabled=!!problems.length||!staging.length;
 }catch(e){alert(e.message);reset()}finally{picker.value=""}};
 cancelBtn.onclick=reset;
 confirmBtn.onclick=async()=>{try{requireAdmin();if(!staging.length)return;if(!confirm("Applicare "+staging.length+" aggiornamenti? Salva prima un backup con Esporta Excel."))return;
 confirmBtn.disabled=true;let done=0;for(const item of staging){requireAdmin();await updateDoc(doc(db,"directoryBusinesses",item.id),{...item.changes,status:"approved",reviewedAt:serverTimestamp()});done++}
 alert(done+" schede aggiornate");reset();
 }catch(e){alert("Importazione interrotta: "+e.message)}finally{confirmBtn.disabled=false}};
 return ()=>{reset();root.hidden=true};
}
