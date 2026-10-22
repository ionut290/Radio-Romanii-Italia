import {initializeApp,getApps} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import {getFirestore,collection,query,where,onSnapshot} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";
import {firebaseConfig} from "./firebase-config.js";
const app=getApps().find(a=>a.options.projectId===firebaseConfig.projectId)||initializeApp(firebaseConfig);
const db=getFirestore(app);
let businesses=[],ads=[];
const validUrl=u=>typeof u==="string"&&/^https:\/\//i.test(u);
const fresh=a=>a.status==="approved"&&(typeof a.expiresAt?.toMillis!=="function"||a.expiresAt.toMillis()>Date.now());
function publish(){
 const output=[];
 for(const b of businesses.slice(0,8)){
  const imageUrls=(Array.isArray(b.imageUrls)?b.imageUrls:[]).filter(validUrl).slice(0,10);
  output.push({category:"Activități și servicii",title:b.name,summary:b.description||"",source:"Ghidul Românilor din Italia",published:new Date().toISOString(),image:imageUrls[0]||"",imageUrls,promotion:true,phone:b.phone||"",whatsapp:b.whatsapp||"",website:b.website||"",address:[b.address,b.city].filter(Boolean).join(", ")});
 }
 for(const a of ads.filter(fresh).slice(0,8)){
  const imageUrls=[...(Array.isArray(a.imageUrls)?a.imageUrls:[]),a.imageUrl].filter(validUrl).filter((x,i,all)=>all.indexOf(x)===i).slice(0,10);
  output.push({category:"Publicitate",title:a.title||a.name||"Publicitate RDI",summary:a.body||a.description||"",source:"Publicitate RDI",published:new Date().toISOString(),image:imageUrls[0]||"",imageUrls,promotion:true,phone:a.phone||"",whatsapp:a.whatsapp||"",website:a.website||"",address:a.address||""});
 }
 window.rdiPromotions=output;
 if(typeof window.load==="function")window.load();
}
onSnapshot(query(collection(db,"directoryBusinesses"),where("status","==","approved")),snapshot=>{businesses=snapshot.docs.map(d=>d.data());publish()},console.warn);
onSnapshot(query(collection(db,"directoryAds"),where("status","==","approved")),snapshot=>{ads=snapshot.docs.map(d=>d.data());publish()},console.warn);
setInterval(publish,60000);
