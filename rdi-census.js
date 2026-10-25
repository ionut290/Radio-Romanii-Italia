const box=document.getElementById('rdi-census');
if(box){
 const fmt=(n,loc)=>Number(n).toLocaleString(loc);
 const langs={
  ro:{heading:'Cetățeni români rezidenți în Italia',note:'Ultimul număr oficial disponibil, nu un contor în timp real',link:'Date și distribuție regională',asof:'Date la'},
  it:{heading:'Cittadini romeni residenti in Italia',note:'Ultimo dato ufficiale disponibile, non un contatore in tempo reale',link:'Fonte e dati regionali',asof:'Dati al'},
  en:{heading:'Romanian citizens residing in Italy',note:'Latest official count, not a real-time population counter',link:'Source and regional breakdown',asof:'As of'}
 };
 let data={residents:1053042,as_of:'2025-01-01'};
 const render=()=>{
  const lang=document.getElementById('rdi-language')?.value||'ro';
  const labels=langs[lang]||langs.ro;
  box.querySelector('[data-census-title]').textContent=labels.heading;
  box.querySelector('[data-census-number]').textContent=fmt(data.residents,lang==='ro'?'ro-RO':lang==='it'?'it-IT':'en-GB');
  const stamp=new Date(data.as_of+'T12:00:00Z');
  box.querySelector('[data-census-note]').textContent=labels.asof+' '+new Intl.DateTimeFormat(lang==='ro'?'ro-RO':lang==='it'?'it-IT':'en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(stamp)+' · ISTAT. '+labels.note+'.';
  box.querySelector('[data-census-link]').textContent=labels.link+' →';
 };
 document.getElementById('rdi-language')?.addEventListener('change',render);
 render();
 fetch('./data/romanians-italy.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('statistics '+r.status);return r.json()}).then(x=>{
  if(Number.isSafeInteger(x.residents)&&x.residents>0&&/^\d{4}-\d{2}-\d{2}$/.test(x.as_of)&&x.realtime===false){data=x;render();}
 }).catch(()=>{});
}
