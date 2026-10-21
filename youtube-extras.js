// RDI YouTube information strip. All widgets are optional and never interrupt news.
const box=document.getElementById("rdiExtras");
const label=document.getElementById("rdiExtraLabel");
const value=document.getElementById("rdiExtraValue");
let song="",weather="",events=[],community=[],ads=[],breaking="",pointer=0;
const limitText=(s,n=115)=>String(s||"").trim().slice(0,n);
const italyDay=x=>new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(x);
function options(){
 const out=[];
 if(breaking)out.push(["ULTIMA ORĂ",breaking]);
 if(song)out.push(["ACUM ASCULȚI",song]);
 if(weather)out.push(["METEO ITALIA",weather]);
 out.push(["PODCAST RDI","Riflessioni sulla Diaspora · Ascultă podcastul și pe Spotify"]);
 if(events.length)out.push(["EVENIMENTE",events[pointer%events.length]]);
 if(community.length)out.push(["COMUNITATE",community[pointer%community.length]]);
 if(ads.length)out.push(["PUBLICITATE",ads[pointer%ads.length]]);
 return out;
}
function render(){const all=options();if(!all.length){box.hidden=true;return}const current=all[pointer%all.length];label.textContent=current[0];value.textContent=current[1];box.hidden=false;pointer++}
render();setInterval(render,12000);
async function loadNowPlaying(){
 try{
  const res=await fetch("https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia",{cache:"no-store",signal:AbortSignal.timeout(8000)});
  if(!res.ok)throw Error("AzuraCast HTTP "+res.status);
  const data=await res.json();const info=data.now_playing?.song;
  song=limitText(info?.text||[info?.artist,info?.title].filter(Boolean).join(" — "),90);
 }catch{song=""}
}
loadNowPlaying();setInterval(loadNowPlaying,30000);
const cities=[["Roma",41.90,12.50],["Milano",45.46,9.19],["Bologna",44.49,11.34],["Torino",45.07,7.69],["Napoli",40.85,14.27]];
async function loadWeather(){
 try{
  const u="https://api.open-meteo.com/v1/forecast?latitude="+cities.map(c=>c[1]).join(",")+"&longitude="+cities.map(c=>c[2]).join(",")+"&current=temperature_2m&timezone=Europe%2FRome";
  const response=await fetch(u,{signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error("weather");
  const data=await response.json();const arr=Array.isArray(data)?data:[data];
  weather=cities.map((c,i)=>{const temp=Number(arr[i]?.current?.temperature_2m);return Number.isFinite(temp)?c[0]+" "+Math.round(temp)+"°C":""}).filter(Boolean).join("  ·  ");
 }catch{weather=""}
}
loadWeather();setInterval(loadWeather,900000);
async function loadPublic(){
 try{
  const [n,e]=await Promise.all([
   fetch("./news.json?x="+Date.now(),{cache:"no-store"}).then(r=>r.json()),
   fetch("./events-auto.json?x="+Date.now(),{cache:"no-store"}).then(r=>r.json())
  ]);
  // Breaking news only when explicitly marked by the editorial team.
  const breakingItems=(n.items||[]).filter(x=>x.breaking===true && x.title && Date.now()-Date.parse(x.published)<21600000 && Date.now()>=Date.parse(x.published));
  breaking=limitText(breakingItems[0]?.title);
  const today=italyDay(new Date());
  events=(e.events||[]).filter(x=>(x.endDate||x.date)>=today&&x.title).slice(0,8).map(x=>limitText([x.city,x.title].filter(Boolean).join(" · ")));
 }catch{breaking="";events=[]}
}
loadPublic();setInterval(loadPublic,300000);
async function loadFirebaseWidgets(){try{
 const [{initializeApp,getApps},{getFirestore,collection,query,where,onSnapshot},{firebaseConfig}]=await Promise.all([
  import("https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js"),
  import("https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js"),
  import("./firebase-config.js")
 ]);
 const app=getApps().find(a=>a.options.projectId===firebaseConfig.projectId)||initializeApp(firebaseConfig);
 const db=getFirestore(app);
 onSnapshot(query(collection(db,"posts"),where("status","==","published")),snap=>{
  community=snap.docs.map(d=>d.data()).filter(x=>x.title&&x.category!=="Publicitate gratuită").sort((a,b)=>(b.createdAt?.toMillis?.()||0)-(a.createdAt?.toMillis?.()||0)).slice(0,10).map(x=>limitText([x.city,x.title].filter(Boolean).join(" · ")));
 },()=>{community=[]});
 onSnapshot(query(collection(db,"directoryAds"),where("status","==","approved")),snap=>{
  ads=snap.docs.map(d=>d.data()).filter(x=>x.title&&x.expiresAt?.toMillis?.()>Date.now()).map(x=>limitText(x.title+" · "+(x.body||""))).slice(0,12);
 },()=>{ads=[]});
}catch(e){console.warn("RDI overlay sources unavailable",e)}}
loadFirebaseWidgets();
