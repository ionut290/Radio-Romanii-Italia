import test from "node:test";
import assert from "node:assert/strict";
import {calendarCard,romeDate,shouldShow} from "../youtube-philosophy-core.mjs";
test("Italian timezone handles date switch",()=>{
 assert.deepEqual(romeDate(new Date("2026-10-30T23:30:00Z")),{day:31,month:10,year:2026});
});
test("Every day in 2027 has a unique original wording",()=>{
 const cards=Array.from({length:365},(_,i)=>calendarCard(new Date(Date.UTC(2027,0,i+1,12))));
 assert.equal(new Set(cards.map(x=>x.quote)).size,365);
 assert(cards.every(x=>x.quote&&x.dateLabel&&Number.isInteger(x.hue)));
});
test("Visual interlude respects frequency and cooldown",()=>{
 assert.equal(shouldShow({cards:7,lastShownAt:0,now:20000000}),false);
 assert.equal(shouldShow({cards:8,lastShownAt:0,now:20000000}),true);
 assert.equal(shouldShow({cards:8,lastShownAt:19000000,now:20000000}),false);
 assert.equal(shouldShow({cards:8,lastShownAt:10000000,now:20000000}),true);
});
