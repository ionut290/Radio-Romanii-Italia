import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validStoriaDay,storyDue} from "../youtube-storia-core.mjs";

const root=new URL("../",import.meta.url);
const html=readFileSync(new URL("youtube-news.html",root),"utf8");
const js=readFileSync(new URL("youtube-storia.js",root),"utf8");
const css=readFileSync(new URL("youtube-storia.css",root),"utf8");
const today=JSON.parse(readFileSync(new URL("data/storia-oggi.json",root),"utf8"));
const build=JSON.parse(readFileSync(new URL("data/youtube-build.json",root),"utf8"));

test("La rubrica entra tra le notizie, non negli spot o nell'audio",()=>{
 assert.match(html,/youtube-storia\.js\?/);
 assert.match(html,/youtube-storia\.css\?/);
 assert.match(html,/rdiStoriaBreak\?\.startIfDue\(nextNews\)/);
 assert.match(html,/window\.rdiStoriaActive\)return;/);
 assert.match(js,/rdiPauseNews\?\.\(\)/);
 assert.doesNotMatch(js,/azuracast|audio\.play\(|ffmpeg/i);
 assert.match(css,/#rdiStoriaTV/);
});

test("Nuovo build sincronizzato con la ricarica automatica YouTube",()=>{
 assert.match(html,new RegExp(build.build));
});

test("Seleziona solo i fatti della giornata corretta",()=>{
 assert.equal(validStoriaDay(today,"2026-11-07").length,0);
 assert.equal(validStoriaDay(today,today.date).length,5);
});

test("Blocca immagini esterne e filtra eventi incompleti",()=>{
 const payload={date:"2026-11-06",events:[
  {year:1910,title_it:"Un evento storico completo",text_it:"Il racconto storico contiene abbastanza testo per essere visualizzato senza tagli assurdi.",image:"https://unsafe.example/portrait.jpg"},
  {year:1910,title_it:"Un evento storico completo",text_it:"Il racconto storico contiene abbastanza testo per essere visualizzato senza tagli assurdi.",image:"https://unsafe.example/portrait.jpg"},
  {year:1911,title_ro:"Un eveniment românesc important",text_ro:"Un eveniment verificabil este prezentat cu o descriere suficient de lungă.",image:"https://upload.wikimedia.org/wikipedia/commons/3/3c/example.jpg"}
 ]};
 const result=validStoriaDay(payload,"2026-11-06");
 assert.equal(result.length,2);
 assert.equal(result[0].image,"");
 assert.equal(result[1].language,"ro");
 assert.match(result[1].image,/wikimedia/);
});

test("Slot storico: ogni otto schede e con almeno dodici minuti di pausa",()=>{
 assert.equal(storyDue({cards:7,lastShownAt:0,now:1_000_000}),false);
 assert.equal(storyDue({cards:8,lastShownAt:0,now:1_000_000}),true);
 assert.equal(storyDue({cards:8,lastShownAt:1_000_000,now:1_700_000}),false);
 assert.equal(storyDue({cards:8,lastShownAt:1_000_000,now:1_721_000}),true);
 assert.equal(storyDue({cards:0,lastShownAt:0,now:0,preview:true}),true);
});
