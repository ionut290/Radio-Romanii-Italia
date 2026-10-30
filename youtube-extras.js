// RDI YouTube information strip. All widgets are optional and never interrupt news.
const box=document.getElementById("rdiExtras");
const label=document.getElementById("rdiExtraLabel");
const value=document.getElementById("rdiExtraValue");
let song="",weather="",events=[],community=[],breaking="",romanianPopulation="",pointer=0;
const limitText=(s,n=115)=>String(s||"").trim().slice(0,n);
const italyDay=x=>new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).format(x);
function options(){
 const out=[];
 if(breaking)out.push(["ULTIMA ORĂ",breaking]);
 if(song)out.push(["ACUM ASCULȚI",song]);
 if(weather)out.push(["METEO ITALIA",weather]);
 if(romanianPopulation)out.push(["ROMÂNII DIN ITALIA · ISTAT",romanianPopulation]);
 out.push(["PODCAST RDI","Riflessioni sulla Diaspora · Ascultă podcastul și pe Spotify"]);
 if(events.length)out.push(["EVENIMENTE",events[pointer%events.length]]);
 if(community.length)out.push(["COMUNITATE",community[pointer%community.length]]);
 return out;
}
function render(){const all=options();if(!all.length){box.hidden=true;return}const current=all[pointer%all.length];label.textContent=current[0];value.textContent=current[1];box.hidden=false;pointer++}
render();setInterval(render,12000);
async function loadNowPlaying(){
 try{
  const res=await fetch("https://radio-romanii-italia.duckdns.org/api/nowplaying/radio-romanii-italia",{cache:"no-store",signal:AbortSignal.timeout(8000)});
  if(!res.ok)throw Error("AzuraCast HTTP "+res.status);
  const data=await res.json();const info=data.now_playing?.song;
  // Prefer structured metadata. Strip long numeric upload/file IDs from titles.
  const clean=v=>String(v||"").replace(/\d{9,}/g," ").replace(/[_]+/g," ").replace(/\s{2,}/g," ").trim();
  const artist=clean(info?.artist),title=clean(info?.title);
  let current=[artist,title].filter(Boolean).join(" — ");
  if(!current)current=clean(info?.text);
  // Avoid showing identifiers or a generic placeholder as a track.
  song=/[A-Za-zÀ-ÿ]{2,}/.test(current)?limitText(current,90):"";
 }catch{song=""}
}
loadNowPlaying();setInterval(loadNowPlaying,30000);
async function loadRomanianPopulation(){
 try{
  const response=await fetch("./data/romanians-italy.json",{cache:"no-store",signal:AbortSignal.timeout(5000)});
  if(!response.ok)throw Error("census");
  const data=await response.json();
  if(Number.isSafeInteger(data.residents)&&data.residents>0&&data.realtime===false&&/^\d{4}-\d{2}-\d{2}$/.test(data.as_of)){
   const date=data.as_of.split("-");
   romanianPopulation=data.residents.toLocaleString("ro-RO")+" cetățeni români rezidenți · date la "+date[2]+"."+date[1]+"."+date[0]+" · nu în timp real";
  }
 }catch{romanianPopulation="";}
}
loadRomanianPopulation();setInterval(loadRomanianPopulation,86400000);
const cities=[
 ["Italia","Roma",41.90,12.50],["Italia","Milano",45.46,9.19],["Italia","Bologna",44.49,11.34],
 ["Italia","Torino",45.07,7.69],["Italia","Napoli",40.85,14.27],["Italia","Firenze",43.77,11.25],
 ["Italia","Venezia",45.44,12.32],["Italia","Palermo",38.12,13.36],["Italia","Bari",41.12,16.87],
 ["Italia","Genova",44.41,8.95],["Italia","Trieste",45.65,13.78],["Italia","Cagliari",39.22,9.12],
 ["Romania","București",44.43,26.10],["Romania","Timișoara",45.75,21.21],["Romania","Cluj-Napoca",46.77,23.62],
 ["Romania","Iași",47.16,27.60],["Romania","Constanța",44.16,28.63],["Romania","Brașov",45.64,25.59],
 ["Romania","Sibiu",45.80,24.13],["Romania","Craiova",44.33,23.79],["Romania","Oradea",47.05,21.92],
 ["Romania","Suceava",47.65,26.26],["Romania","Arad",46.19,21.31],["Romania","Baia Mare",47.66,23.58]
];
function weatherCondition(code){
 const n=Number(code);
 if(n===0)return "sereno";
 if([1,2].includes(n))return "parzialmente nuvoloso";
 if(n===3)return "nuvoloso";
 if([45,48].includes(n))return "nebbia";
 if([51,53,55,56,57].includes(n))return "pioviggine";
 if([61,63,65,66,67,80,81,82].includes(n))return "pioggia";
 if([71,73,75,77,85,86].includes(n))return "neve";
 if([95,96,99].includes(n))return "temporale";
 return "variabile";
}
async function loadWeather(){
 try{
  const u="https://api.open-meteo.com/v1/forecast?latitude="+cities.map(c=>c[2]).join(",")+"&longitude="+cities.map(c=>c[3]).join(",")+"&current=temperature_2m,weather_code&timezone=auto";
  const response=await fetch(u,{signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error("weather");
  const data=await response.json();const arr=Array.isArray(data)?data:[data];
  const cityData=cities.map((c,i)=>{
   const current=arr[i]?.current,temp=Number(current?.temperature_2m),code=Number(current?.weather_code);
   return Number.isFinite(temp)?{country:c[0],name:c[1],temperature:temp,weatherCode:code,description:weatherCondition(code)}:null;
  }).filter(Boolean);
  window.rdiWeatherSnapshot={cities:cityData,updatedAt:Date.now()};
  window.dispatchEvent(new CustomEvent("rdi:weather-update",{detail:window.rdiWeatherSnapshot}));
  weather=cityData.map(c=>c.name+" "+Math.round(c.temperature)+"°C").join("  ·  ");
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
}catch(e){console.warn("RDI overlay sources unavailable",e)}}
loadFirebaseWidgets();
