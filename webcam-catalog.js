/* RDI city webcam directory. Verified IDs were checked against Windy's public embed endpoints 2026-10-29.
   Discovery-only locations are NOT represented as active webcams. No API key or restricted stream is used. */
(()=>{'use strict';
const VERIFIED=[["RO","București","București","Piața Unirii · Bulevardul Unirii","1793907437"],["RO","Brașov","Brașov","Piața Sfatului · Centrul istoric","1793910742"],["RO","Brașov","Brașov","Fiteducation · Tenis Arena","1423399645"],["RO","Sibiu","Sibiu","Piața Mare · Fântâna Medievală","1206379396"],["RO","Sibiu","Sibiu","Grădina Zoologică","1405786356"],["RO","Sibiu","Sibiu","Primăria · Centrul istoric","1567662837"],["RO","Baia Mare","Maramureș","Bulevardul Unirii","1214491523"],["RO","Iași","Iași","Biserica Sfântul Nicolae Domnesc","1465668398"],["RO","Câmpulung Moldovenesc","Suceava","Panoramă spre sud","1334671197"],["RO","Bascov","Argeș","Strada Rotărești · Bulevardul Nicolae Bălcescu","1401975375"],["RO","Târgu Jiu","Gorj","Masa Tăcerii","1445095039"],["RO","Buzău","Buzău","Panoramă oraș","1482376182"],["RO","Vaslui","Vaslui","Crucea Gării","1496994047"],["RO","Deva","Hunedoara","Hotel Deva","1513721464"],["RO","Galați","Galați","Faleza Dunării · Parc La Elice","1513721465"],["RO","Caracal","Olt","Primăria Municipiului Caracal","1519797614"],["RO","Oradea","Bihor","Panoramă oraș · Bihor","1544647937"],["RO","Hunedoara","Hunedoara","Panoramă Hunedoara","1591000404"],["RO","Vârtop","Alba","Pârtia de schi Vârtop","1545292409"],["RO","Poiana Brașov","Brașov","Hotel Alpin · Pârtia Bradul","1547077952"],["RO","Rânca","Gorj","Rânca · Novaci","1577553797"],["RO","Târgu Mureș","Mureș","Budai Nagy Antal · Nord-vest","1608400733"],["IT","Roma","Lazio","Piazza Venezia · Municipio Roma I","1600351836"],["IT","Bologna","Emilia-Romagna","Ospedale Maggiore · Ovest","1454628812"],["IT","Milano","Lombardia","Duomo di Milano · Centro","1170927034"],["IT","Procida","Campania","Panorama verso Napoli e il Vesuvio","1202493407"],["IT","Palermo","Sicilia","Panorama di Palermo","1200850755"],["IT","Palermo","Sicilia","Teatro Massimo · Piazza Verdi","1398172386"],["IT","Genova","Liguria","Panorama di Genova","1636067231"],["IT","Bacoli","Campania","Panorama costiero","1670723274"],["IT","Rimini","Emilia-Romagna","Bagno Loretta 99","1531307653"],["IT","Rimini","Emilia-Romagna","Panorama Rimini","1637783915"],["IT","Venezia","Veneto","Piazza San Marco · Museo Correr","1645625119"]];
const DISCOVERY={"RO|Alba":"Alba Iulia;Aiud;Blaj;Cugir;Sebeș;Abrud;Ocna Mureș;Teiuș;Zlatna","RO|Arad":"Arad;Ineu;Lipova;Chișineu-Criș;Nădlac","RO|Argeș":"Pitești;Curtea de Argeș;Câmpulung;Mioveni;Costești;Topoloveni","RO|Bacău":"Bacău;Onești;Moinești;Comănești;Buhuși;Slănic-Moldova;Târgu Ocna","RO|Bihor":"Salonta;Marghita;Beiuș;Ștei;Aleșd","RO|Bistrița-Năsăud":"Bistrița;Năsăud;Beclean;Sângeorz-Băi","RO|Botoșani":"Botoșani;Dorohoi;Darabani;Săveni;Ștefănești","RO|Brăila":"Brăila;Ianca;Însurăței","RO|Brașov":"Făgăraș;Codlea;Râșnov;Săcele;Zărnești;Predeal;Victoria;Rupea","RO|București":"Otopeni;Buftea;Voluntari;Pantelimon;Popești-Leordeni","RO|Buzău":"Râmnicu Sărat;Nehoiu;Pătârlagele","RO|Caraș-Severin":"Reșița;Caransebeș;Bocșa;Oravița;Moldova Nouă;Anina;Băile Herculane","RO|Călărași":"Călărași;Oltenița;Fundulea;Lehliu-Gară","RO|Cluj":"Cluj-Napoca;Turda;Dej;Gherla;Câmpia Turzii;Huedin","RO|Constanța":"Constanța;Mangalia;Medgidia;Năvodari;Eforie Nord;Eforie Sud;Mamaia;Costinești;Vama Veche;Cernavodă;Hârșova;Techirghiol","RO|Covasna":"Sfântu Gheorghe;Târgu Secuiesc;Covasna;Baraolt","RO|Dâmbovița":"Târgoviște;Moreni;Găești;Pucioasa;Titu;Fieni","RO|Dolj":"Craiova;Băilești;Filiași;Calafat;Segarcea;Dăbuleni","RO|Galați":"Tecuci;Târgu Bujor;Berești","RO|Giurgiu":"Giurgiu;Bolintin-Vale;Mihăilești","RO|Gorj":"Motru;Rovinari;Novaci;Tismana;Bumbești-Jiu","RO|Harghita":"Miercurea Ciuc;Odorheiu Secuiesc;Gheorgheni;Toplița;Borsec;Băile Tușnad;Vlăhița","RO|Hunedoara":"Petroșani;Lupeni;Vulcan;Orăștie;Simeria;Hațeg;Brad;Călan","RO|Ialomița":"Slobozia;Urziceni;Fetești;Țăndărei","RO|Iași":"Pașcani;Târgu Frumos;Hârlău;Podu Iloaiei","RO|Ilfov":"Măgurele;Bragadiru;Chitila;Corbeanca","RO|Maramureș":"Sighetu Marmației;Borșa;Vișeu de Sus;Baia Sprie;Târgu Lăpuș;Seini;Cavnic","RO|Mehedinți":"Drobeta-Turnu Severin;Orșova;Strehaia;Vânju Mare","RO|Mureș":"Sighișoara;Reghin;Târnăveni;Luduș;Sovata;Iernut","RO|Neamț":"Piatra Neamț;Roman;Târgu Neamț;Bicaz;Roznov","RO|Olt":"Slatina;Balș;Corabia;Drăgănești-Olt;Scornicești","RO|Prahova":"Ploiești;Câmpina;Sinaia;Bușteni;Azuga;Breaza;Vălenii de Munte;Comarnic;Slănic;Mizil","RO|Sălaj":"Zalău;Șimleu Silvaniei;Jibou;Cehu Silvaniei","RO|Satu Mare":"Satu Mare;Carei;Negrești-Oaș;Tășnad","RO|Sibiu":"Mediaș;Cisnădie;Avrig;Agnita;Dumbrăveni;Păltiniș;Ocna Sibiului","RO|Suceava":"Suceava;Rădăuți;Fălticeni;Vatra Dornei;Gura Humorului;Siret;Dolhasca;Salcea","RO|Teleorman":"Alexandria;Roșiorii de Vede;Turnu Măgurele;Zimnicea;Videle","RO|Timiș":"Timișoara;Lugoj;Sânnicolau Mare;Jimbolia;Buziaș;Deta;Făget","RO|Tulcea":"Tulcea;Sulina;Babadag;Măcin;Isaccea","RO|Vaslui":"Bârlad;Huși;Negrești;Murgeni","RO|Vâlcea":"Râmnicu Vâlcea;Drăgășani;Călimănești;Băile Olănești;Horezu;Brezoi;Băile Govora","RO|Vrancea":"Focșani;Adjud;Mărășești;Odobești;Panciu","IT|Abruzzo":"L'Aquila;Pescara;Chieti;Teramo;Avezzano;Sulmona;Vasto;Lanciano;Giulianova;Roseto degli Abruzzi","IT|Basilicata":"Potenza;Matera;Melfi;Policoro;Pisticci;Lauria;Venosa","IT|Calabria":"Reggio Calabria;Catanzaro;Cosenza;Crotone;Vibo Valentia;Lamezia Terme;Corigliano-Rossano;Rende;Scalea;Tropea;Soverato","IT|Campania":"Napoli;Salerno;Caserta;Benevento;Avellino;Pozzuoli;Torre del Greco;Castellammare di Stabia;Pompei;Ercolano;Sorrento;Amalfi;Positano;Capri;Ischia;Aversa;Cava de' Tirreni;Agropoli;Nocera Inferiore;Giugliano in Campania","IT|Emilia-Romagna":"Modena;Parma;Reggio Emilia;Ferrara;Ravenna;Forlì;Cesena;Piacenza;Imola;Faenza;Riccione;Cesenatico;Carpi;Sassuolo;Cervia;Comacchio;Fidenza;San Lazzaro di Savena;Castel Maggiore;San Giovanni in Persiceto;Bellaria-Igea Marina;Argenta","IT|Friuli-Venezia Giulia":"Trieste;Udine;Pordenone;Gorizia;Monfalcone;Lignano Sabbiadoro;Grado;Cividale del Friuli","IT|Lazio":"Latina;Frosinone;Viterbo;Rieti;Civitavecchia;Tivoli;Anzio;Nettuno;Fiumicino;Ostia;Albano Laziale;Velletri;Formia;Gaeta;Terracina;Cassino;Fiuggi;Bracciano","IT|Liguria":"La Spezia;Savona;Imperia;Sanremo;Rapallo;Chiavari;Sestri Levante;Ventimiglia;Albenga;Santa Margherita Ligure;Finale Ligure;Portofino;Alassio","IT|Lombardia":"Bergamo;Brescia;Monza;Como;Varese;Lecco;Pavia;Lodi;Cremona;Mantova;Sondrio;Busto Arsizio;Gallarate;Legnano;Sesto San Giovanni;Cinisello Balsamo;Rho;Desenzano del Garda;Sirmione;Vigevano;Treviglio;Crema;Erba","IT|Marche":"Ancona;Pesaro;Urbino;Fano;Senigallia;Jesi;Fabriano;Macerata;Civitanova Marche;Fermo;Porto San Giorgio;Ascoli Piceno;San Benedetto del Tronto;Recanati","IT|Molise":"Campobasso;Isernia;Termoli;Venafro;Larino","IT|Piemonte":"Torino;Novara;Alessandria;Asti;Biella;Vercelli;Cuneo;Verbania;Ivrea;Pinerolo;Moncalieri;Rivoli;Chieri;Alba;Bra;Borgomanero;Omegna;Arona;Susa;Bardonecchia;Sestriere","IT|Puglia":"Bari;Lecce;Brindisi;Taranto;Foggia;Barletta;Andria;Trani;Monopoli;Polignano a Mare;Ostuni;Gallipoli;Otranto;Martina Franca;Altamura;Molfetta;Manfredonia;San Giovanni Rotondo;Vieste;Fasano;Alberobello","IT|Sardegna":"Cagliari;Sassari;Nuoro;Oristano;Olbia;Alghero;Porto Torres;Quartu Sant'Elena;Carbonia;Iglesias;Villasimius;Arzachena;La Maddalena;Santa Teresa Gallura","IT|Sicilia":"Catania;Messina;Siracusa;Ragusa;Trapani;Agrigento;Caltanissetta;Enna;Taormina;Giardini Naxos;Cefalù;Marsala;Mazara del Vallo;Sciacca;Modica;Noto;Acireale;Aci Castello;Milazzo;Erice;Lampedusa;San Vito Lo Capo","IT|Toscana":"Firenze;Pisa;Lucca;Livorno;Prato;Pistoia;Arezzo;Siena;Grosseto;Massa;Carrara;Viareggio;Forte dei Marmi;Pietrasanta;Montecatini Terme;Volterra;San Gimignano;Cortona;Empoli;Follonica;Piombino;Portoferraio","IT|Trentino-Alto Adige":"Trento;Bolzano;Rovereto;Merano;Bressanone;Brunico;Vipiteno;Riva del Garda;Arco;Canazei;Ortisei;Madonna di Campiglio;Predazzo;Cavalese","IT|Umbria":"Perugia;Terni;Assisi;Foligno;Spoleto;Orvieto;Gubbio;Città di Castello;Todi;Norcia;Spello","IT|Valle d'Aosta":"Aosta;Courmayeur;Saint-Vincent;Cervinia;La Thuile;Cogne","IT|Veneto":"Verona;Padova;Treviso;Vicenza;Belluno;Rovigo;Chioggia;Mestre;Jesolo;Caorle;Bibione;Cortina d'Ampezzo;Bassano del Grappa;Asiago;Conegliano;Castelfranco Veneto;Vittorio Veneto;San Donà di Piave;Montebelluna;Portogruaro;Abano Terme","MD|Moldova":"Chișinău;Bălți;Cahul;Ungheni;Orhei;Soroca;Comrat;Edineț;Drochia;Strășeni;Căușeni;Hîncești;Nisporeni;Ialoveni;Cimișlia;Taraclia","EU|Europa":"Londra;Parigi;Madrid;Barcellona;Berlino;Monaco di Baviera;Francoforte;Amburgo;Vienna;Salisburgo;Zurigo;Ginevra;Bruxelles;Amsterdam;Rotterdam;Dublino;Lisbona;Porto;Praga;Budapest;Varsavia;Cracovia;Copenaghen;Stoccolma;Oslo;Helsinki;Atene;Sofia;Belgrado;Zagabria;Lubiana;Bratislava;Istanbul;Lussemburgo;Malta;Nicosia;Skopje;Tirana;Sarajevo;Podgorica;Tallinn;Riga;Vilnius;Edimburgo;Manchester;Birmingham;Lione;Marsiglia;Nizza;Valencia;Siviglia;Bilbao;Bordeaux;Colonia;Stoccarda;Düsseldorf;Dortmund;Norimberga;Innsbruck"};
const countryNames={RO:'România',IT:'Italia',MD:'Republica Moldova',EU:'Europa'};
const flags={RO:'🇷🇴',IT:'🇮🇹',MD:'🇲🇩',EU:'🌍'};
const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('ro').replace(/[^a-z0-9]+/g,' ').trim();
const records=new Map();
function record(country,city,region){
 const key=country+'|'+normalize(city);
 if(!records.has(key))records.set(key,{key,country,city,region,cameras:[]});
 return records.get(key);
}
for(const row of VERIFIED){
 const [country,city,region,place,id]=row;
 if(!/^\d{10}$/.test(id))continue;
 const item=record(country,city,region);
 if(!item.cameras.some(c=>c.id===id))item.cameras.push({id,place});
}
for(const [group,raw] of Object.entries(DISCOVERY)){
 const [country,region]=group.split('|');
 for(const name of raw.split(';').map(s=>s.trim()).filter(Boolean))record(country,name,region);
}
const entries=Array.from(records.values());
const verifiedEntries=entries.filter(x=>x.cameras.length);
const $$=selector=>document.querySelector(selector);
const list=$$('#webcam-city-list'),search=$$('#webcam-search'),stats=$$('#webcam-stats');
const frame=$$('#camera-frame'),currentTitle=$$('#camera-title'),place=$$('#camera-location');
const source=$$('#camera-source'),area=$$('#camera-viewer'),noCamera=$$('#webcam-no-embed');
const outside=$$('#webcam-discover'),next=$$('#webcam-more');
const countryPicker=$$('#webcam-country'),viewPicker=$$('#webcam-view'),empty=$$('#webcam-empty');
if(!list||!search||!frame||!stats)return;
let chosen=records.get('RO|'+normalize('București'))||verifiedEntries[0];
let visibleLimit=70;
let filtered=[];
function searchLink(city,country){
 const query='webcam '+city+' '+countryNames[country]+' Windy webcam';
 return 'https://www.google.com/search?q='+encodeURIComponent(query);
}
function choose(item,cameraIndex=0){
 if(!item)return;
 chosen=item;
 list.querySelectorAll('[data-key]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.key===item.key)));
 currentTitle.textContent=item.city;
 $$('#camera-country').textContent=flags[item.country]+' '+countryNames[item.country]+' · '+item.region;
 if(item.cameras.length){
  const cam=item.cameras[Math.min(cameraIndex,item.cameras.length-1)];
  $$('#webcam-active-status').textContent='Player Windy · imagini actualizate / timelapse';
  place.textContent=cam.place;
  $$('#webcam-camera-choice').replaceChildren();
  if(item.cameras.length>1){
   for(const [i,c] of item.cameras.entries()){
    const b=document.createElement('button'); b.type='button'; b.className='webcam-camera-btn';
    b.textContent=c.place;b.setAttribute('aria-pressed',String(cam.id===c.id));
    b.addEventListener('click',()=>choose(item,i));$$('#webcam-camera-choice').append(b);
   }
  }
  source.href='https://www.windy.com/webcams/'+cam.id;
  source.textContent='Vezi camera pe Windy ↗';
  source.hidden=false;
  outside.href=searchLink(item.city,item.country);
  outside.textContent='Alte camere în '+item.city+' ↗';
  area.hidden=false;noCamera.hidden=true;
  frame.title='Webcam '+item.city+' – '+cam.place+' (Windy, imagini periodice)';
  const url='https://webcams.windy.com/webcams/public/embed/player/'+cam.id+'/day';
  if(frame.src!==url)frame.src=url;
 }else{
  $$('#webcam-active-status').textContent='Localitate de explorat · fără player verificat';
  place.textContent=item.region;
  $$('#webcam-camera-choice').replaceChildren();
  frame.src='about:blank';
  area.hidden=true;noCamera.hidden=false;source.hidden=true;
  outside.href=searchLink(item.city,item.country);
  outside.textContent='Caută webcam din '+item.city+' ↗';
  $$('#webcam-no-embed-link').href=outside.href;
 }
 $$('#camera-description').textContent=item.cameras.length?'Camera selectată folosește playerul public Windy. Imaginile pot fi periodice, iar disponibilitatea depinde de operator.':'Nu am găsit încă un player public Windy verificat pentru această localitate. Caută pe site-urile operatorilor, fără a confunda rezultatele cu o cameră confirmată.';
}
function buildList(){
 const q=normalize(search.value), country=countryPicker.value,view=viewPicker.value;
 filtered=entries.filter(x=>(country==='all'||x.country===country)&&(view==='all'||x.cameras.length>0)
   &&(!q||normalize(x.city+' '+x.region+' '+countryNames[x.country]).includes(q)));
 filtered.sort((a,b)=>Number(!!b.cameras.length)-Number(!!a.cameras.length)||a.city.localeCompare(b.city,'ro'));
 list.replaceChildren();
 const part=filtered.slice(0,visibleLimit);
 for(const item of part){
  const b=document.createElement('button');b.type='button';b.className='webcam-city';
  b.dataset.key=item.key;
  b.setAttribute('aria-pressed',String(item.key===chosen?.key));
  const name=document.createElement('strong');name.textContent=item.city;
  const meta=document.createElement('small');meta.textContent=flags[item.country]+' '+item.region;
  const status=document.createElement('span');status.className='webcam-city-type';
  status.textContent=item.cameras.length?'📷 '+item.cameras.length+' '+(item.cameras.length>1?'camere':'cameră'):'🔎 Caută webcam';
  b.append(name,meta,status);
  b.addEventListener('click',()=>{choose(item);$$('#camera-title').scrollIntoView({behavior:'smooth',block:'start'});});
  list.append(b);
 }
 empty.hidden=filtered.length!==0;
 stats.textContent=filtered.length+' localități · '+verifiedEntries.length+' cu player verificat · '+VERIFIED.length+' camere testate';
 next.hidden=filtered.length<=visibleLimit;
 next.textContent='Vezi mai multe orașe ('+Math.max(0,filtered.length-visibleLimit)+')';
}
search.addEventListener('input',()=>{visibleLimit=70;buildList()});
countryPicker.addEventListener('change',()=>{visibleLimit=70;buildList()});
viewPicker.addEventListener('change',()=>{visibleLimit=70;buildList()});
next.addEventListener('click',()=>{visibleLimit+=70;buildList()});
$$('#webcam-clear').addEventListener('click',()=>{search.value='';countryPicker.value='all';viewPicker.value='all';visibleLimit=70;buildList();search.focus()});
$$('#webcam-world').href='https://www.windy.com/webcams';
$$('#webcam-romania-all').href='https://webcamromania.ro/camere/';
choose(chosen);buildList();
window.RDIWebcamDirectory={totalCities:entries.length,embeddedCities:verifiedEntries.length,cameras:VERIFIED.length};
})();
