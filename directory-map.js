// RDI directory map. Business data and contact details are never inserted as HTML.
export const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
export function validPoint(lat, lng) {
  return typeof lat === 'number' && typeof lng === 'number' && Number.isFinite(lat) && Number.isFinite(lng) && lat >= 35 && lat <= 48 && lng >= 6 && lng <= 19;
}
export function mergeBusinesses(publicRecords, approvedRecords) {
  const result = [], seen = new Set();
  // A directly managed RDI record takes precedence over a matching public listing.
  for (const record of [...approvedRecords, ...publicRecords]) {
    const key = [normalize(record.name), normalize(record.address), normalize(record.city)].join('|');
    if (!seen.has(key)) { seen.add(key); result.push(record); }
  }
  return result;
}
export function filterBusinesses(records, filters) {
  const q = normalize(filters.search), region = normalize(filters.region), province = normalize(filters.province), city = normalize(filters.city);
  return records.filter(b => (!filters.category || b.category === filters.category)
    && (!region || normalize(b.region).includes(region))
    && (!province || normalize([b.province,b.provinceName].filter(Boolean).join(" ")).includes(province))
    && (!city || normalize(b.city).includes(city))
    && (!q || normalize([b.name, b.category, b.description, b.address, b.city, b.province, b.region].join(' ')).includes(q)));
}
export function locateBusiness(b, cities = {}) {
  // Online-only listings must not be presented as physical premises.
  if (/^(online|activitate online|attivit[aà] online)/i.test(b.address || '')) return null;
  if (validPoint(b.lat, b.lng)) return {lat:b.lat, lng:b.lng, precision:b.locationPrecision || 'source'};
  if (validPoint(b.latitude, b.longitude)) return {lat:b.latitude, lng:b.longitude, precision:'source'};
  const city = cities[normalize(b.city)];
  return city && validPoint(city[0], city[1]) ? {lat:city[0], lng:city[1], precision:'city'} : null;
}
const themes = {
  'Magazine românești':['#167a65','▣'], 'Restaurante românești':['#c26b27','♨'],
  'Construcții și renovări':['#5864bd','⌂'], 'Îngrijire și frumusețe':['#b7467b','✦'],
  'Sănătate și servicii profesionale':['#167ea3','+'], 'Transport România–Italia':['#4479b2','↗'],
  'Transport și logistică':['#4479b2','↗'], 'Curățenie':['#2b8c9e','✧'],
  'Auto și mecanică':['#697484','⚙'], 'Asociații și comunitate':['#93529c','♡']
};
export const categoryTheme = category => themes[category] || ['#b08a40','●'];
const messages = {
  ro:{loading:'Se încarcă harta…',unavailable:'Harta nu este disponibilă acum. Lista și contactele rămân accesibile.',retry:'Reîncearcă',source:'Date din sursă publică · de confirmat',managed:'Listare publicată pe RDI',approximate:'Poziție aproximativă: centrul localității',position:'Poziție indicată de sursă; confirmă adresa înainte de deplasare.',details:'Vezi detaliile',directions:'Indicații',call:'Sună',site:'Site web',reference:'Sursa informațiilor',located:'pe hartă',without:'fără poziție',none:'Nicio activitate pentru filtrele alese.',locating:'Se caută poziția…',denied:'Poziția nu este disponibilă. Poți căuta după oraș.',yourLocation:'Poziția ta',tiles:'Fundalul hărții nu s-a încărcat. Lista activităților este disponibilă mai jos.',near:'Harta este centrată pe poziția ta.',zoom:'Apropie pentru a vedea activitățile',expand:'Mărește harta',collapse:'Micșorează harta'},
  it:{loading:'Caricamento della mappa…',unavailable:'La mappa non è disponibile. Elenco e contatti restano accessibili.',retry:'Riprova',source:'Dati da fonte pubblica · da confermare',managed:'Scheda pubblicata su RDI',approximate:'Posizione approssimativa: centro della località',position:'Posizione indicata dalla fonte; conferma l’indirizzo prima di partire.',details:'Apri i dettagli',directions:'Indicazioni',call:'Chiama',site:'Sito web',reference:'Fonte delle informazioni',located:'sulla mappa',without:'senza posizione',none:'Nessuna attività per i filtri selezionati.',locating:'Ricerca della posizione…',denied:'Posizione non disponibile. Puoi cercare per città.',yourLocation:'La tua posizione',tiles:'Lo sfondo della mappa non si è caricato. L’elenco è disponibile qui sotto.',near:'Mappa centrata sulla tua posizione.',zoom:'Ingrandisci per vedere le attività',expand:'Espandi la mappa',collapse:'Riduci la mappa'},
  en:{loading:'Loading map…',unavailable:'The map is unavailable. Listings and contacts remain accessible.',retry:'Try again',source:'Public-source information · to be confirmed',managed:'Listing published on RDI',approximate:'Approximate position: town centre',position:'Position supplied by the source; confirm the address before travelling.',details:'View details',directions:'Directions',call:'Call',site:'Website',reference:'Information source',located:'on the map',without:'without a location',none:'No businesses match your filters.',locating:'Finding your location…',denied:'Location unavailable. You can search by town.',yourLocation:'Your location',tiles:'Map tiles could not be loaded. Listings remain available below.',near:'Map centred on your location.',zoom:'Zoom in to see businesses',expand:'Expand map',collapse:'Reduce map'}
};
export const mapText = key => (messages[window.rdiLanguage?.() || 'ro'] || messages.ro)[key] || key;
export function safeUrl(value) { try {const u = new URL(value); return ['http:','https:'].includes(u.protocol) ? u.href : null;} catch {return null;} }
const element = (tag, text, className) => {const el=document.createElement(tag); if(text != null)el.textContent=text; if(className)el.className=className; return el;};
function anchor(label, href, className) {
  const a=element('a',label,className); a.href=href; a.target='_blank'; a.rel='noopener noreferrer'; return a;
}
export function sourceNote(b, point) {
  const box=element('div',null,'directory-provenance');
  box.append(element('span',b.sourceUrl ? mapText('source') : mapText('managed')));
  if(point)box.append(element('small',mapText(point.precision==='city'?'approximate':'position')));
  if(b.sourceUrl && safeUrl(b.sourceUrl))box.append(anchor(mapText('reference')+' ↗',safeUrl(b.sourceUrl)));
  return box;
}
function loadScript(src) {
  return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.onload=resolve;script.onerror=()=>{script.remove();reject(Error('Map library unavailable'));};document.head.append(script);});
}
let libraryPromise;
async function libraries() {
  if(!libraryPromise)libraryPromise=(async()=>{
    if(!window.L)await loadScript('./vendor/leaflet/leaflet.js');
    if(!window.L.markerClusterGroup)await loadScript('./vendor/leaflet-markercluster/leaflet.markercluster.js');
    return window.L;
  })().catch(e=>{libraryPromise=null;throw e;});
  return libraryPromise;
}
export function createDirectoryMap({onOpen}) {
  const host=document.getElementById('directory-map'), shell=document.getElementById('map-shell'), status=document.getElementById('map-status');
  let map, clusters, rows=[], cities={}, signature='', loading=false, markerById=new Map(), userMarker;
  const report=text=>{status.textContent=text;};
  const points=()=>rows.map(b=>({b,point:locateBusiness(b,cities)}));
  function updateCounts(){const data=points(), n=data.filter(x=>x.point).length;document.getElementById('map-count').textContent=`${n} ${mapText('located')}${data.length-n?' · '+(data.length-n)+' '+mapText('without'):''}`;}
  function fit(){if(!map || !clusters?.getLayers().length)return;map.fitBounds(clusters.getBounds().pad(.12),{maxZoom:13,padding:[28,28],animate:false});}
  function popup(b,point) {
    const box=element('div',null,'directory-popup');
    const [color]=categoryTheme(b.category), tag=element('span',b.category,'directory-popup-category');tag.style.color=color;
    box.append(tag,element('h3',b.name),element('p',[b.address,b.city,b.province].filter(Boolean).join(' · ')));
    box.append(sourceNote(b,point));
    const actions=element('div',null,'directory-popup-actions'), btn=element('button',mapText('details'),'map-primary');btn.type='button';btn.onclick=()=>onOpen(b);actions.append(btn);
    // A town-centre pin must never be used as an exact navigation destination.
    const destination=[b.address,b.city,b.province,'Italia'].filter(Boolean).join(', ');
    actions.append(anchor(mapText('directions'),'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(destination),'map-link'));
    const phone=String(b.phone||'').replace(/[^+0-9]/g,'');if(phone)actions.append(anchor(mapText('call'),'tel:'+phone,'map-link'));
    box.append(actions);return box;
  }
  function redraw(force=false){
    updateCounts();if(!map)return;
    const next=rows.map(b=>b.id+':'+b.name+':'+b.address).join('|');if(!force && signature===next)return;signature=next;
    clusters.clearLayers();markerById.clear();
    const markers=[];
    for(const {b,point} of points()) {
      if(!point)continue;
      const [color,symbol]=categoryTheme(b.category), icon=element('span',symbol,'directory-pin');icon.style.setProperty('--pin-color',color);
      const marker=window.L.marker([point.lat,point.lng],{title:b.name,alt:b.name,keyboard:true,icon:window.L.divIcon({html:icon,className:'directory-marker',iconSize:[34,42],iconAnchor:[17,40],popupAnchor:[0,-36]})});
      marker.on('add',()=>marker.getElement()?.setAttribute('aria-label',b.name));
      marker.bindPopup(()=>popup(b,point),{maxWidth:310,minWidth:220});markerById.set(b.id,marker);markers.push(marker);
    }
    clusters.addLayers(markers);fit();
    if(!rows.length)report(mapText('none'));else report('');
  }
  async function ensure(){
    if(map || loading || shell.hidden || document.getElementById('find-panel').hidden)return;
    loading=true;report(mapText('loading'));
    try{
      const L=await libraries();
      map=L.map(host,{scrollWheelZoom:false,zoomControl:false}).setView([42.2,12.4],5);
      L.control.zoom({position:'bottomright'}).addTo(map);
      const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}).addTo(map);
      let failures=0;tiles.on('tileerror',()=>{if(++failures>=3)report(mapText('tiles'));});tiles.on('load',()=>{if(!failures)report('');});
      clusters=L.markerClusterGroup({showCoverageOnHover:false,chunkedLoading:true,maxClusterRadius:48,spiderfyOnMaxZoom:true,iconCreateFunction:cluster=>L.divIcon({html:'<span>'+cluster.getChildCount()+'</span>',className:'directory-cluster',iconSize:[44,44]})});map.addLayer(clusters);
      new ResizeObserver(()=>map.invalidateSize()).observe(host);
      redraw(true);report(rows.length?'':mapText('none'));
    }catch(e){
      report(mapText('unavailable'));const retry=element('button',mapText('retry'),'map-link');retry.type='button';retry.onclick=()=>{loading=false;ensure();};status.append(' ',retry);
    }finally{loading=false;}
  }
  document.addEventListener('directory-view-change',e=>{if(e.detail.view==='find'){ensure();requestAnimationFrame(()=>map?.invalidateSize());}else{shell.classList.remove('map-expanded');document.getElementById('map-expand').textContent=mapText('expand');document.getElementById('map-expand').setAttribute('aria-pressed','false');}});
  document.getElementById('map-fit').onclick=fit;
  document.getElementById('map-expand').onclick=()=>{const expanded=shell.classList.toggle('map-expanded');document.getElementById('map-expand').textContent=mapText(expanded?'collapse':'expand');document.getElementById('map-expand').setAttribute('aria-pressed',String(expanded));map?.invalidateSize();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&shell.classList.contains('map-expanded')){shell.classList.remove('map-expanded');document.getElementById('map-expand').textContent=mapText('expand');document.getElementById('map-expand').setAttribute('aria-pressed','false');map?.invalidateSize();}});
  document.getElementById('map-near').onclick=()=>{
    if(!navigator.geolocation){report(mapText('denied'));return;}
    report(mapText('locating'));
    navigator.geolocation.getCurrentPosition(async position=>{
      await ensure();if(!map)return;
      const {latitude,longitude}=position.coords;
      if(userMarker)userMarker.remove();userMarker=window.L.circleMarker([latitude,longitude],{radius:8,color:'#fff',weight:3,fillColor:'#2563eb',fillOpacity:1}).addTo(map).bindTooltip(mapText('yourLocation'));
      map.setView([latitude,longitude],11);report(mapText('near'));
    },()=>report(mapText('denied')),{timeout:12000,maximumAge:60000});
  };
  document.querySelectorAll('[data-map-mode]').forEach(btn=>btn.onclick=()=>{
    const hidden=btn.dataset.mapMode==='list';shell.hidden=hidden;
    document.querySelectorAll('[data-map-mode]').forEach(x=>{const active=x===btn;x.classList.toggle('selected',active);x.setAttribute('aria-pressed',String(active));});
    if(!hidden){ensure();requestAnimationFrame(()=>map?.invalidateSize());}
  });
  document.addEventListener('rdi-language-changed',()=>{redraw(true);});
  return {
    update(found,cityIndex){rows=found;cities=cityIndex||cities;updateCounts();ensure();redraw();},
    locate:b=>locateBusiness(b,cities),
    focus:async b=>{shell.hidden=false;document.querySelector('[data-panel="find"]').click();await ensure();const marker=markerById.get(b.id);if(marker)clusters.zoomToShowLayer(marker,()=>{marker.openPopup();host.scrollIntoView({behavior:'smooth',block:'center'});});}
  };
}
