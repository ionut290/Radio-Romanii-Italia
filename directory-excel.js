// Admin-only CSV workflow (CSV opens and saves in Excel); public JSON rows are export-only.
import {collection,getDocs,doc,updateDoc,addDoc,serverTimestamp} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
const FIELDS=["source","id","name","category","region","province","city","address","phone","whatsapp","website","hours","description","status"];
const FIELDS_EDIT=["name","description","phone","whatsapp","website","address","hours"];
const clean=v=>String(v??"").trim();
const esc=v=>'"'+String(v??"").replaceAll('"','""')+'"';
function csv(rows){return "\uFEFF"+[FIELDS.join(";"),...rows.map(r=>FIELDS.map(k=>esc(r[k])).join(";"))].join("\r\n");}
function parseCsv(text){
  const input=text.replace(/^\uFEFF/,"");let rows=[],row=[],value="",quoted=false;
  const delimiter=(input.split(/\r?\n/)[0].match(/;/g)||[]).length>=(input.split(/\r?\n/)[0].match(/,/g)||[]).length?";":",";
  for(let i=0;i<input.length;i++){
    const c=input[i];
    if(c==='"'){if(quoted&&input[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
    else if(!quoted&&c===delimiter){row.push(value);value="";}
    else if(!quoted&&(c==="\n"||c==="\r")){if(c==="\r"&&input[i+1]==="\n")i++;row.push(value);if(row.some(x=>x!==""))rows.push(row);row=[];value="";}
    else value+=c;
  }
  if(quoted)throw Error("CSV: virgolette non chiuse.");
  row.push(value);if(row.some(x=>x!==""))rows.push(row);
  const headers=rows.shift()?.map(clean)||[];
  if(!FIELDS.every(k=>headers.includes(k)))throw Error("Colonne mancanti: "+FIELDS.filter(k=>!headers.includes(k)).join(", "));
  return rows.map((cells,i)=>({line:i+2,...Object.fromEntries(headers.map((h,j)=>[h,clean(cells[j])]))}));
}
function download(rows){
  const blob=new Blob([csv(rows)],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),link=document.createElement("a");
  link.href=url;link.download="RDI-ghid-attivita-"+new Date().toISOString().slice(0,10)+".csv";
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const nameKey=r=>[r.name,r.city,r.address].map(v=>clean(v).toLocaleLowerCase("ro")).join("|");
export function initDirectoryExcel({db,isAdmin,getPublicRecords,getUid}){
  const wrap=document.getElementById("directory-excel-admin"),exp=document.getElementById("directory-excel-export"),imp=document.getElementById("directory-excel-import"),file=document.getElementById("directory-excel-file"),modal=document.getElementById("directory-excel-review"),summary=document.getElementById("directory-excel-summary"),apply=document.getElementById("directory-excel-apply"),close=document.getElementById("directory-excel-close");
  if(!wrap||!exp||!imp||!file||!modal)return;
  let staged=[];
  const visible=()=>{wrap.hidden=!isAdmin();if(!isAdmin()){staged=[];modal.hidden=true;file.value="";}};
  function error(e){alert("Import/Export: "+(e?.message||e));}
  exp.onclick=async()=>{if(!isAdmin())return;exp.disabled=true;try{
    const docs=await getDocs(collection(db,"directoryBusinesses"));
    const fire=docs.docs.map(d=>({source:"firestore",id:d.id,...d.data()}));
    const pub=getPublicRecords().map(r=>({source:"public-json",...r}));
    download([...pub,...fire]);alert("Esportate "+(pub.length+fire.length)+" schede. Il CSV si apre in Excel; conserva le colonne source e id.");
  }catch(e){error(e)}finally{exp.disabled=false;}};
  imp.onclick=()=>{if(isAdmin())file.click();};
  file.onchange=async()=>{if(!isAdmin()||!file.files[0])return;apply.disabled=true;staged=[];
    try{
      if(file.files[0].size>8_000_000)throw Error("File oltre 8 MB.");
      const rows=parseCsv(await file.files[0].text());
      if(rows.length>10000)throw Error("Troppi record (max 10.000).");
      const snap=await getDocs(collection(db,"directoryBusinesses"));
      const existing=new Map(snap.docs.map(d=>[d.id,d.data()]));
      const used=new Set(snap.docs.map(d=>nameKey(d.data())));
      const seenIds=new Set();let skipped=0,invalid=[],updates=0,adds=0;
      for(const r of rows){
        if(r.source==="public-json"){skipped++;continue;}
        if(r.source!=="firestore"&&r.source!=="new"){invalid.push("Riga "+r.line+": origine sconosciuta");continue;}
        if(r.id&&seenIds.has(r.id)){invalid.push("Riga "+r.line+": ID duplicato");continue;}if(r.id)seenIds.add(r.id);
        if(r.source==="firestore"&&(!r.id||!existing.has(r.id))){invalid.push("Riga "+r.line+": ID Firestore inesistente");continue;}
        const old=existing.get(r.id);
        if(old){const changes=Object.fromEntries(FIELDS_EDIT.filter(k=>clean(old[k])!==clean(r[k])).map(k=>[k,r[k]]));
          if(Object.keys(changes).length){staged.push({kind:"update",id:r.id,changes});updates++;}continue;}
        if(r.id){invalid.push("Riga "+r.line+": nuove attività devono avere ID vuoto e source=new");continue;}
        if(!r.name||r.name.length<2||r.name.length>110||!r.category||r.category.length<3||!r.region||r.region.length<2||!r.province||r.province.length<2||!r.city||r.city.length<2||!r.address||r.address.length<3||r.description.length<25||r.description.length>1200||r.phone.length>40||r.whatsapp.length>40||r.website.length>250||r.hours.length>150){invalid.push("Riga "+r.line+": dati obbligatori mancanti o troppo lunghi");continue;}
        if(used.has(nameKey(r))){invalid.push("Riga "+r.line+": possibile duplicato");continue;}
        used.add(nameKey(r));staged.push({kind:"add",data:Object.fromEntries(FIELDS.filter(k=>!["source","id","status"].includes(k)).map(k=>[k,r[k]]))});adds++;
      }
      summary.textContent="Modifiche da confermare: "+updates+" aggiornamenti, "+adds+" nuove. "+skipped+" schede JSON pubbliche ignorate (non modificabili qui). "+invalid.length+" anomalie. "+(invalid.slice(0,12).join("; ")||"Nessuna anomalia.");
      apply.disabled=invalid.length>0||staged.length===0;modal.hidden=false;
    }catch(e){error(e)}finally{file.value="";}
  };
  close.onclick=()=>{modal.hidden=true;staged=[];};
  apply.onclick=async()=>{if(!isAdmin()||!staged.length)return;
    if(!confirm("Applicare "+staged.length+" modifiche su Firestore? Esporta prima il backup CSV."))return;
    apply.disabled=true;close.disabled=true;let done=0;
    try{
      // Sequential writes intentionally avoid a partial parallel overwrite storm.
      for(const item of staged){
        if(!isAdmin())throw Error("Sessione amministratore terminata.");
        if(item.kind==="update")await updateDoc(doc(db,"directoryBusinesses",item.id),{...item.changes,status:"approved",reviewedAt:serverTimestamp()});
        else await addDoc(collection(db,"directoryBusinesses"),{...item.data,imageUrls:[],uid:getUid(),status:"approved",createdAt:serverTimestamp()});
        done++;
      }
      alert(done+" modifiche completate.");staged=[];modal.hidden=true;
    }catch(e){alert(done+" modifiche riuscite su "+staged.length+". Interrotto: "+(e?.message||e));}finally{apply.disabled=false;close.disabled=false;}
  };
  visible();return visible;
}
