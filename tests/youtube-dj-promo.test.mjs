import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validRules,eligible,priorityBlocked} from '../youtube-dj-promo-core.mjs';

const page=await readFile(new URL('../youtube-news.html',import.meta.url),'utf8');
const overlay=await readFile(new URL('../youtube-dj-promo.js',import.meta.url),'utf8');
const css=await readFile(new URL('../youtube-dj-promo.css',import.meta.url),'utf8');
const config=JSON.parse(await readFile(new URL('../data/youtube-dj-promo.json',import.meta.url),'utf8'));
const art=await readFile(new URL('../editorial-images/rdi-dj-programmazione-live.svg',import.meta.url),'utf8');

test('RDI live news loads DJ promo asset, config, visual overlay and priority guard',()=>{
 assert.match(page,/youtube-dj-promo\.js\?v=/);
 assert.match(page,/youtube-dj-promo\.css\?v=/);
 assert.match(page,/window\.rdiDjPromoBreak\?\.startIfDue\(nextNews\)/);
 assert.match(page,/window\.rdiDjPromoActive/);
 assert.match(overlay,/window\.rdiPauseNews\?\.\(\)/);
 assert.match(overlay,/\.\/data\/youtube-dj-promo\.json/);
 assert.match(css,/#rdiDjPromo\[hidden\]/);
 assert.match(css, /rdi-dj-promo-active/);
 assert.match(art,/<svg /);
 assert.match(art,/>PROGRAMMAZIONE ORARIA</);
 assert.match(art,/>ANTEPRIMA/);
});
test('promo is enabled and appears after 12 complete news cards no more than every 30 minutes',()=>{
 const x=validRules(config);
 assert.deepEqual(x,{enabled:true,durationSeconds:16,everyNewsCards:12,minMinutesBetween:30});
 assert.equal(eligible({rules:x,cardsSince:11,lastShownAt:null,now:3600000,blocked:false}),false);
 assert.equal(eligible({rules:x,cardsSince:12,lastShownAt:null,now:3600000,blocked:false}),true);
 assert.equal(eligible({rules:x,cardsSince:30,lastShownAt:3500000,now:3600000,blocked:false}),false);
 assert.equal(eligible({rules:x,cardsSince:30,lastShownAt:100000,now:3600000,blocked:false}),true);
});
test('radio spot, geopolitica, TG, weather and cameras always block visual DJ promo',()=>{
 for(const name of ['rdiSpotActive','rdiGeoActive','rdiTgActive','rdiWeatherActive','rdiCameraActive','rdiLandscapeActive']){
  assert.equal(priorityBlocked({[name]:true}),true,name);
 }
 assert.equal(priorityBlocked({}),false);
 const x=validRules(config);
 assert.equal(eligible({rules:x,cardsSince:50,lastShownAt:null,now:3600000,blocked:true}),false);
});
test('no promo audio, no AzuraCast modifications, fail closed on missing config',()=>{
 assert.doesNotMatch(overlay,/\.play\(|new Audio\(|ffmpeg|POST|\/api\/station/);
 assert.doesNotMatch(overlay,/localStorage|sessionStorage/);
 assert.equal(validRules({}).enabled,false);
 assert.equal(validRules({enabled:true,durationSeconds:100,everyNewsCards:1,minMinutesBetween:1}).durationSeconds,25);
 assert.equal(validRules({enabled:true,durationSeconds:100,everyNewsCards:1,minMinutesBetween:1}).minMinutesBetween,15);
});
