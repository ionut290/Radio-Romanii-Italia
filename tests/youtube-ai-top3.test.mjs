import test from "node:test";
import assert from "node:assert/strict";
import {rankedTop3,romeClock,due,onAirRank,normalizeSong} from "../youtube-ai-top3-core.mjs";
const id=n=>n.toString(16).padStart(32,"0");
const sample={tracks:[
{id:id(3),title:"Terzo brano",artist:"Artista C",votes:1,audio_preview:1},
{id:id(2),title:"Secondo brano",artist:"Artista B",votes:4,audio_preview:1},
{id:id(1),title:"Primo brano",artist:"Artista A",votes:15,audio_preview:1}
]};
test("API ranking keeps its public, ordered Top 3 and never invents votes",()=>{
 const t=rankedTop3(sample);assert.equal(t.length,3);
 assert.deepEqual(t.map(x=>x.rank),[1,2,3]);assert.deepEqual(t.map(x=>x.votes),[1,4,15]);
 assert.deepEqual(t.map(x=>x.title),["Terzo brano","Secondo brano","Primo brano"]);
});
test("incomplete, malformed and duplicate charts do not broadcast",()=>{
 assert.equal(rankedTop3({tracks:[sample.tracks[0]]}).length,1);
 const unsafe={tracks:[sample.tracks[0],sample.tracks[0],{id:id(2),title:"",artist:"X",votes:1}]};
 assert.equal(rankedTop3(unsafe).length,1);
 assert.equal(rankedTop3(null).length,0);
});
test("20:30 Europe/Rome time and daylight saving uses local clock",()=>{
 const time=new Date("2026-11-07T19:30:00Z");
 assert.deepEqual(romeClock(time),{day:"2026-11-07",hour:20,minute:30});
 assert.equal(due({now:time,shownDay:"",tracks:rankedTop3(sample)}),true);
 assert.equal(due({now:time,shownDay:"2026-11-07",tracks:rankedTop3(sample)}),false);
 assert.equal(due({now:new Date("2026-11-07T18:00:00Z"),shownDay:"",tracks:rankedTop3(sample)}),false);
 assert.equal(due({now:time,shownDay:"",tracks:rankedTop3({tracks:[]})}),false);
 assert.equal(due({now:time,shownDay:"",tracks:rankedTop3(sample),enabled:false}),false);
});
test("only matching AzuraCast song can be labelled as on air",()=>{
 const tracks=rankedTop3(sample);
 assert.equal(onAirRank({now_playing:{song:{title:"Primo brano",artist:"Artista A"}}},tracks)?.rank,3);
 assert.equal(onAirRank({now_playing:{song:{title:"Primo brano",artist:"Artista B"}}},tracks),null);
 assert.equal(onAirRank({now_playing:{song:{title:"An unrelated song",artist:"Artist"}}},tracks),null);
 assert.equal(normalizeSong("Pioggìa — RDI"),"pioggia rdi");
});
