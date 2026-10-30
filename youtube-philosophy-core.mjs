/* Pure deterministic daily calendar, Europe/Rome. No network and no repeating quote within a year. */
export const THOUGHTS=[
"Non tutto ciò che pesa è un ostacolo: a volte è una radice.",
"La libertà comincia quando smettiamo di confondere l'abitudine con il destino.",
"Un gesto gentile non cambia il passato, ma può cambiare il prossimo minuto.",
"Il silenzio non è vuoto quando impariamo ad ascoltarlo.",
"Non sempre serve una risposta: qualche domanda ci rende più attenti.",
"Il coraggio non elimina la paura; le impedisce di decidere al posto nostro.",
"Una vita consapevole non è senza errori, ma capace di riconoscerli.",
"Ciò che non controlliamo può insegnarci ciò che scegliamo.",
"Non misurare il giorno da quanto hai ottenuto, ma da quanto hai compreso.",
"Ogni incontro è una possibilità di vedere il mondo con altri occhi.",
"La pace non nasce dall'avere tutti ragione, ma dal saperci ascoltare.",
"La pazienza è il modo in cui il tempo diventa cura.",
"Non confondere la velocità con la direzione.",
"Un confine sano protegge la possibilità di essere generosi.",
"Quando cambia la prospettiva, anche il problema cambia forma.",
"L'incertezza è il prezzo della scoperta, non il suo contrario.",
"Non possiamo trattenere un giorno, ma possiamo abitarlo davvero.",
"Una parola precisa vale più di cento parole pronunciate per riempire il vuoto.",
"Il rispetto si riconosce soprattutto quando non siamo d'accordo.",
"Essere presenti è un modo semplice e difficile di amare.",
"La curiosità è un ponte tra ciò che sappiamo e ciò che potremmo capire.",
"Non ogni perdita è una sconfitta, non ogni conquista è un successo.",
"L'umiltà non diminuisce il nostro valore: lascia spazio a quello degli altri.",
"La speranza è un lavoro quotidiano, non una garanzia.",
"Il cambiamento più profondo a volte non fa rumore.",
"Chi ascolta davvero lascia entrare una parte di mondo.",
"Le cose importanti chiedono attenzione, non sempre urgenza.",
"Non c'è crescita senza la disponibilità a cambiare idea.",
"Un passo piccolo e sincero vale più di una promessa infinita.",
"La gratitudine non cancella la fatica: le dà un altro orizzonte.",
"Anche un dubbio, se accolto bene, può diventare conoscenza.",
"La dignità non ha bisogno di spettatori.",
"La memoria ci orienta; non deve impedirci di camminare.",
"Scegliere con cura è una forma concreta di libertà.",
"Il tempo condiviso è uno dei pochi doni che non si possono restituire.",
"Non puoi cambiare il vento, ma puoi conoscere meglio la tua vela.",
"La bellezza non richiede perfezione, ma uno sguardo disponibile.",
"Dire non lo so è spesso il primo atto di intelligenza.",
"Quando giudichiamo meno in fretta, comprendiamo più a fondo.",
"Restare umani significa non ridurre nessuno al suo momento peggiore."
];
const THEMES=["La domanda di oggi","Uno sguardo diverso","La libertà interiore","Il valore del tempo","La cura delle relazioni","L'arte di comprendere","Pensare con gentilezza","Il coraggio quotidiano","La forza del dubbio","Il senso delle scelte","La misura delle cose"];
export function romeDate(d=new Date()){
 const p=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(d);
 const f=Object.fromEntries(p.filter(x=>x.type!=="literal").map(x=>[x.type,Number(x.value)]));
 return f;
}
export function calendarCard(d=new Date()){
 const f=romeDate(d),year=f.year;
 const day=Math.floor((Date.UTC(f.year,f.month-1,f.day)-Date.UTC(year,0,1))/86400000);
 // Co-prime 137 with 365 and 366: stable permutation across days; short phrases vary
 // alongside a distinct editorial theme and graphic palette.
 const n=(day*137+year*23)%THOUGHTS.length;
 const title=THEMES[(day*7+year)%THEMES.length];
 const dateLabel=new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",day:"numeric",month:"long",year:"numeric"}).format(d);
 return {dateLabel,quote:THOUGHTS[n],theme:title,hue:((day*37)%240)+145,sunX:20+(day*17)%60,day};
}
export function shouldShow({cards,lastShownAt,now}){
 return cards>=8 && (!lastShownAt||now-lastShownAt>=45*60000);
}
