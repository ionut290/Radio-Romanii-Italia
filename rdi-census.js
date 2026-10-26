const box=document.getElementById('rdi-census');
if(box){
 const fmt=(n,loc)=>Number(n).toLocaleString(loc);
 const langs={
  ro:{heading:'Cetățeni români rezidenți în Italia',link:'Date și distribuție regională',asof:'Date la'},
  it:{heading:'Cittadini romeni residenti in Italia',link:'Fonte e dati regionali',asof:'Dati al'},
  en:{heading:'Romanian citizens residing in Italy',link:'Source and regional breakdown',asof:'As of'}
 };
 let data={residents:1053042,as_of:'2025-01-01'};
 const render=()=>{
  const lang=document.getElementById('rdi-language')?.value||'ro';
  const labels=langs[lang]||langs.ro;
  const locale=lang==='ro'?'ro-RO':lang==='it'?'it-IT':'en-GB';
  const number=fmt(data.residents,locale);
  const stamp=new Date(data.as_of+'T12:00:00Z');
  const date=new Intl.DateTimeFormat(locale,{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(stamp);
  const link=box.querySelector('[data-census-link]');
  box.querySelector('[data-census-number]').textContent=number;
  box.setAttribute('aria-label',labels.heading);
  link.setAttribute('aria-label',labels.heading+': '+number+'. '+labels.link+'. '+labels.asof+' '+date+' · ISTAT');
  link.title=labels.heading+' · '+labels.asof+' '+date+' · ISTAT';
 };
 document.getElementById('rdi-language')?.addEventListener('change',render);
 render();
 fetch('./data/romanians-italy.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('statistics '+r.status);return r.json()}).then(x=>{
  if(Number.isSafeInteger(x.residents)&&x.residents>0&&/^\d{4}-\d{2}-\d{2}$/.test(x.as_of)&&x.realtime===false){data=x;render();}
 }).catch(()=>{});
}
