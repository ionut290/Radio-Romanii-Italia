import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizedCandidates, chooseFeatured, scoreStory, safeImage, safeLink
} from "../rdi-featured-core.mjs";

const now=Date.parse("2026-10-27T12:00:00Z");
const at="2026-10-27T10:00:00Z";
const img="https://example.com/photography/ukraine.jpg";
function news(title,url,extra={}) {
  return {title,url,published:at,summary:"Aggiornamento internazionale sul paese, con le informazioni disponibili e i dettagli dall'articolo originale.",source:"Fonte test",image:img,category:"Italia",...extra};
}
test("selects a real photo as first lead",()=>{
  const candidates=normalizedCandidates({
    news:[
      news("Guerra in Ucraina: nuove trattative diplomatiche","https://example.com/1"),
      news("Sulla crisi nel Sudan arrivano nuove informazioni","https://example.com/2",{image:"./editorial-images/rdi-conflict-editorial.svg"})
    ],
    war:[{id:"rdi-sudan",published_date:"2026-10-27",region:"Sudan",title_it:"Sudan: rischio carestia e accesso umanitario",summary_it:"È stato lanciato un appello internazionale per la protezione degli operatori umanitari e dei civili.",source_name:"Fonte ufficiale",source_url:"https://example.com/w"}]
  },"it",now);
  const result=chooseFeatured(candidates,now);
  assert.equal(result[0].image,img);
  assert.ok(result.some(x=>x.fromWar));
});
test("IT titles require translation or native Italian original",()=>{
  const c=normalizedCandidates({
    news:[news("Știri din România pentru muncitorii din Italia","https://example.com/1",{category:"România"})]
  },"it",now);
  assert.equal(c.length,0);
  const x=news("Știri din România pentru muncitorii din Italia","https://example.com/1",{category:"România",id:"story"});
  const translated=normalizedCandidates({news:[x],translations:{"story":{original:{title:x.title},it:{title:"Notizie dalla Romania per i lavoratori in Italia",summary:"Il notiziario è aggiornato oggi."}}}},"it",now);
  assert.equal(translated.length,1);
  assert.equal(translated[0].title,"Notizie dalla Romania per i lavoratori in Italia");
});
test("missing Italian summary does not expose Romanian original",()=>{
  const x=news("Știri noi în România","https://example.com/3",{id:"3",category:"România",summary:"Acesta este un rezumat doar în limba română."});
  const result=normalizedCandidates({news:[x],translations:{"3":{original:{title:x.title},it:{title:"Nuove notizie in Romania"}}}},"it",now);
  assert.equal(result[0].summary,"");
});
test("RO stories and verified war feed use their Romanian text",()=>{
  const x=news("Guvernul anunță măsuri noi în România","https://example.com/3",{category:"România"});
  const war={published_date:"2026-10-27",region:"Sudan",title_ro:"Sudan: ajutoare umanitare urgente",summary_ro:"Organizațiile au anunțat necesitatea unor măsuri concrete și ajutor umanitar.",source_url:"https://example.org/report"};
  const result=normalizedCandidates({news:[x],war:[war]},"ro",now);
  assert.equal(result.length,2);
  assert.ok(result.some(y=>y.title.includes("ajutoare")));
});
test("stale content, untranslatable stories and unsafe links are excluded",()=>{
  const old=news("Guerra in Ucraina: riunione diplomatica","https://example.com/old",{published:"2026-10-19T00:00:00Z"});
  const unsafe=news("Guerra in Ucraina: riunione diplomatica","javascript:alert(1)");
  assert.equal(normalizedCandidates({news:[old,unsafe]},"it",now).length,0);
  assert.equal(safeLink("javascript:alert(1)"),"");
  assert.equal(safeImage("javascript:alert(1)"),"");
});
test("ranking includes relevance, urgency and quality of photography",()=>{
  const war=news("Guerra in Ucraina: nuove trattative diplomatiche","https://example.com/a",{editorial:true});
  const trivia=news("Hobby curioso tra i giovani in Italia","https://example.com/b",{image:"./RADIO-COVER.jpg"});
  assert.ok(scoreStory(war,now)>scoreStory(trivia,now));
});
test("deduplication and category balancing",()=>{
  const input=[
    news("Guerra in Ucraina: nuove trattative diplomatiche","https://example.com/1"),
    news("Guerra in Ucraina: nuove trattative diplomatiche","https://example.com/1"),
    news("Guerra in Ucraina: nuove trattative diplomatiche oggi","https://example.com/2"),
    news("Nuove elezioni e voto in Italia","https://example.com/3"),
    news("Sciopero dei trasporti, nuove decisioni in Italia","https://example.com/4"),
    news("Sudan: richieste di aiuti umanitari","https://example.com/5"),
    news("Bilancio economico: nuove decisioni UE","https://example.com/6"),
  ];
  let selected=chooseFeatured(input,now,5);
  assert.ok(selected.length<=5);
  assert.equal(new Set(selected.map(x=>x.url)).size,selected.length);
});
