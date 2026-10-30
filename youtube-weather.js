/* RDI YouTube weather interlude: data from the existing weather refresh,
   followed by one full-screen official radar map. Audio and news sources are untouched. */
(()=> {
  "use strict";
  const stage=document.getElementById("stage");
  if(!stage)return;
  const layer=document.createElement("section");
  layer.id="rdiWeatherOverlay";
  layer.hidden=true;
  layer.setAttribute("aria-label","Rubrica meteo RDI: città e radar");
  layer.innerHTML=
    '<section class="rdi-weather-view" aria-label="Meteo delle città">' +
      '<header class="rdi-weather-header"><div class="rdi-weather-brand">🇷🇴 🇮🇹 RADIO ROMÂNII DIN ITALIA<small>METEO PER LA COMUNITÀ</small></div><span class="rdi-weather-pill">METEO</span></header>' +
      '<div class="rdi-weather-title">METEO ITALIA · ROMANIA</div>' +
      '<div class="rdi-weather-subtitle">Condizioni attuali nelle città · scorrono da destra verso sinistra</div>' +
      '<div class="rdi-weather-country"><div class="rdi-weather-country-head">ITALIA <span>AGGIORNAMENTO AUTOMATICO</span></div><div class="rdi-weather-city-window"><div class="rdi-weather-city-track" id="rdiWeatherItaly"></div></div></div>' +
      '<div class="rdi-weather-country"><div class="rdi-weather-country-head">ROMANIA <span>AGGIORNAMENTO AUTOMATICO</span></div><div class="rdi-weather-city-window"><div class="rdi-weather-city-track" id="rdiWeatherRomania"></div></div></div>' +
      '<div class="rdi-weather-source" id="rdiWeatherSource">Fonte: Open-Meteo (CC BY 4.0) · aggiornamento</div>' +
    '</section>' +
    '<section class="rdi-weather-radar" aria-label="Mappa radar ufficiale">' +
      '<iframe id="rdiWeatherRadar" title="Mappa radar meteorologico" referrerpolicy="strict-origin-when-cross-origin" allow="fullscreen"></iframe>' +
      '<div class="rdi-weather-radar-head"><strong class="rdi-weather-radar-title" id="rdiWeatherRadarTitle"></strong><span class="rdi-weather-radar-credit" id="rdiWeatherRadarCredit"></span></div>' +
      '<div class="rdi-weather-radar-foot" id="rdiWeatherRadarTime"></div>' +
    '</section>' +
    '<div class="rdi-weather-progress" id="rdiWeatherProgress"></div>';
  stage.append(layer);
  const $=id=>document.getElementById(id);
  const italyTrack=$("rdiWeatherItaly"),romaniaTrack=$("rdiWeatherRomania");
  const frame=$("rdiWeatherRadar"),progress=$("rdiWeatherProgress");
  const CITY_SECONDS=30,RADAR_SECONDS=30;
  const radarSources={
    IT:{title:"RADAR METEO · ITALIA",credit:"Fonte: Radar-DPC · Protezione Civile",
      url:"https://mappe.protezionecivile.gov.it/it/mappe-e-dashboard-rischi/piattaforma-radar/"},
    RO:{title:"RADAR METEO · ROMANIA",credit:"Fonte: Administrația Națională de Meteorologie (ANM)",
      url:"https://www.meteoromania.ro/anm2/radarm/radar.index.php"}
  };
  let active=false,cityTimer=null,finishTimer=null,priorityTimer=null;
  let finishCallback=null,lastDisplayedUpdate="",previousDisplayedUpdate="",nextRadarCountry="IT",revision=0;

  function weatherIcon(code){
    const n=Number(code);
    if(n===0)return "☀";
    if([1,2].includes(n))return "🌤";
    if(n===3)return "☁";
    if([45,48].includes(n))return "🌫";
    if([51,53,55,56,57,61,63,65,66,67,80,81,82].includes(n))return "🌧";
    if([71,73,75,77,85,86].includes(n))return "❄";
    if([95,96,99].includes(n))return "⛈";
    return "•";
  }
  function weatherText(code){
    const n=Number(code);
    if(n===0)return "Sereno";
    if([1,2].includes(n))return "Parzialmente nuvoloso";
    if(n===3)return "Nuvoloso";
    if([45,48].includes(n))return "Nebbia";
    if([51,53,55,56,57].includes(n))return "Pioviggine";
    if([61,63,65,66,67,80,81,82].includes(n))return "Pioggia";
    if([71,73,75,77,85,86].includes(n))return "Neve";
    if([95,96,99].includes(n))return "Temporale";
    return "Condizioni variabili";
  }
  function makeCityCard(city){
    const card=document.createElement("div");
    card.className="rdi-weather-city";
    const name=document.createElement("strong");
    name.textContent=city.name;
    const temp=document.createElement("b");
    const value=Number(city.temperature);
    temp.textContent=Number.isFinite(value)?Math.round(value)+"°":"—";
    const condition=document.createElement("span");
    condition.className="rdi-weather-condition";
    condition.textContent=weatherIcon(city.weatherCode)+" "+(city.description||weatherText(city.weatherCode));
    const forecast=document.createElement("span");
    forecast.className="rdi-weather-forecast";
    const min=Number(city.minTemperature),max=Number(city.maxTemperature),rain=Number(city.precipitationProbability);
    const range=Number.isFinite(min)&&Number.isFinite(max)?"Oggi "+Math.round(min)+"°–"+Math.round(max)+"°":"";
    const rainText=Number.isFinite(rain)?"Pioggia "+Math.round(rain)+"%":"";
    forecast.textContent=[range,rainText].filter(Boolean).join(" · ");
    card.append(name,temp,condition);
    if(forecast.textContent)card.append(forecast);
    return card;
  }
  function fillTrack(track,cities){
    track.replaceChildren();
    const valid=(Array.isArray(cities)?cities:[]).filter(x=>x&&typeof x.name==="string");
    const set=valid.length?valid:[{name:"Dati in aggiornamento",temperature:null,description:"In attesa della rilevazione"}];
    for(const city of set)track.append(makeCityCard(city));
    for(const city of set){const copy=makeCityCard(city);copy.setAttribute("aria-hidden","true");track.append(copy);}
    track.style.animationDuration=Math.max(42,set.length*6)+"s";
    track.style.animationPlayState="running";
  }
  function renderCities(data){
    const cities=Array.isArray(data?.cities)?data.cities:[];
    fillTrack(italyTrack,cities.filter(x=>x.country==="Italia"));
    fillTrack(romaniaTrack,cities.filter(x=>x.country==="Romania"));
    const time=Number(data?.updatedAt);
    $("rdiWeatherSource").textContent="Fonte: Open-Meteo (CC BY 4.0) · aggiornato "+(Number.isFinite(time)?
      new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",hour:"2-digit",minute:"2-digit"}).format(new Date(time))+" ora italiana":
      "orario non disponibile");
  }
  function setProgress(seconds){
    progress.style.transition="none";
    progress.style.width="0%";
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(active){progress.style.transition="width "+seconds*1000+"ms linear";progress.style.width="100%";}
    }));
  }
  function showCityView(data){
    layer.classList.remove("rdi-weather-radar-active");
    layer.classList.add("rdi-weather-city-active");
    $("rdiWeatherRadar").src="about:blank";
    renderCities(data);
    setProgress(CITY_SECONDS+RADAR_SECONDS);
    cityTimer=setTimeout(()=>showRadarView(),CITY_SECONDS*1000);
  }
  function showRadarView(){
    if(!active)return;
    const radar=radarSources[activeCountry];
    layer.classList.remove("rdi-weather-city-active");
    layer.classList.add("rdi-weather-radar-active");
    $("rdiWeatherRadarTitle").textContent=radar.title;
    $("rdiWeatherRadarCredit").textContent=radar.credit;
    $("rdiWeatherRadarTime").textContent="Mappa radar ufficiale · schermata visiva senza audio";
    frame.src=radar.url;
  }
  let activeCountry="IT";
  function stop(resume=true){
    if(!active)return;
    clearTimeout(cityTimer);clearTimeout(finishTimer);clearInterval(priorityTimer);
    cityTimer=finishTimer=priorityTimer=null;
    const callback=finishCallback;finishCallback=null;
    if(!resume)lastDisplayedUpdate=previousDisplayedUpdate;
    active=false;window.rdiWeatherActive=false;
    layer.hidden=true;layer.classList.remove("rdi-weather-city-active","rdi-weather-radar-active");
    document.body.classList.remove("rdi-weather-active");
    frame.src="about:blank";progress.style.transition="none";progress.style.width="0%";
    if(resume&&!window.rdiSpotActive&&!window.rdiGeoActive&&!window.rdiTgActive&&typeof callback==="function")callback();
  }
  function startIfDue(next){
    if(active||window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive||
       window.rdiCameraActive||window.rdiLandscapeActive)return false;
    const data=window.rdiWeatherSnapshot;
    const stamp=String(data?.updatedAt||"");
    if(!stamp||stamp===lastDisplayedUpdate)return false;
    previousDisplayedUpdate=lastDisplayedUpdate;
    lastDisplayedUpdate=stamp;
    activeCountry=nextRadarCountry;
    nextRadarCountry=nextRadarCountry==="IT"?"RO":"IT";
    window.rdiPauseNews?.();
    active=true;window.rdiWeatherActive=true;finishCallback=next;
    document.body.classList.add("rdi-weather-active");layer.hidden=false;
    showCityView(data);
    finishTimer=setTimeout(()=>stop(true),(CITY_SECONDS+RADAR_SECONDS)*1000);
    priorityTimer=setInterval(()=>{
      if(window.rdiSpotActive||window.rdiGeoActive||window.rdiTgActive)stop(false);
    },500);
    return true;
  }
  window.addEventListener("rdi:weather-update",event=>{
    const data=event.detail;
    if(data&&Array.isArray(data.cities)&&Number.isFinite(Number(data.updatedAt)))
      window.rdiWeatherSnapshot=data;
  });
  if(window.rdiWeatherSnapshot)renderCities(window.rdiWeatherSnapshot);
  window.rdiWeatherBreak={startIfDue,stop,get state(){return {active,lastDisplayedUpdate,nextRadarCountry};}};
})();