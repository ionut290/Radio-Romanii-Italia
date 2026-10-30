import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {parseLandscapeConfig,validateLandscape,safeLandscapeURL,landscapeDue} from "../youtube-landscapes-core.mjs";

const read=path=>readFile(new URL(path,import.meta.url),"utf8");
const config=JSON.parse(await read("../data/youtube-landscapes.json"));
const page=await read("../youtube-news.html");
const script=await read("../youtube-landscapes.js");
const css=await read("../youtube-landscapes.css");
const build=JSON.parse(await read("../data/youtube-build.json"));

test("RDI landscapes are strictly Italy/Romania, source credited, without audio",()=>{
 const p=parseLandscapeConfig(config);
 assert.equal(p.enabled,true);
 assert.equal(p.every,4);
 assert.equal(p.duration,20);
 assert.equal(p.items.length,6);
 assert.deepEqual(p.items.map(x=>x.country),["Italia","România","Italia","România","Italia","România"]);
 for(const scene of config.items){
  assert.equal(scene.audio_muted,true);
  assert.equal(scene.rights_reviewed,true);
  assert.ok(validateLandscape(scene),scene.id);
  assert.ok(scene.credit && scene.source_url && scene.license_url);
 }
 assert.equal(config.items.filter(x=>x.kind==="video").length,4);
 assert.equal(config.items.filter(x=>x.kind==="image").length,2);
});

test("bad origins, invalid rights and audio fail closed",()=>{
 const first=config.items[0];
 assert.equal(validateLandscape({...first,audio_muted:false}),null);
 assert.equal(validateLandscape({...first,rights_reviewed:false}),null);
 assert.equal(validateLandscape({...first,src:"https://videos.pexels.com.evil.example/demo.mp4"}),null);
 assert.equal(validateLandscape({...first,src:"http://videos.pexels.com/demo.mp4"}),null);
 assert.equal(validateLandscape({...first,country:"France"}),null);
 assert.equal(validateLandscape({...first,license_url:"https://example.com/license"}),null);
 assert.equal(safeLandscapeURL("https://localhost/demo.mp4","video"),false);
 assert.equal(parseLandscapeConfig({enabled:true,items:[first]}).enabled,false);
 assert.equal(parseLandscapeConfig({enabled:false,items:config.items}).enabled,false);
});

test("four-news cadence provides a 20-second interlude",()=>{
 assert.deepEqual([1,2,3,4,5,8,12].map(n=>landscapeDue(n,4)),
   [false,false,false,true,false,true,true]);
 const changed=parseLandscapeConfig({...config,after_news_cards:0,duration_seconds:100});
 assert.equal(changed.every,3);
 assert.equal(changed.duration,30);
});

test("RDI live page includes silent visuals only and respects priority overlays",()=>{
 assert.match(page,/src="\.\/youtube-landscapes\.js\?v=/);
 assert.match(page,/href="\.\/youtube-landscapes\.css\?v=/);
 assert.match(page,/window\.rdiLandscapeBreak\?\.startIfDue\(nextNews\)/);
 assert.match(page,/window\.rdiLandscapeBreak\?\.stop\(\)/);
 assert.match(page,/window\.rdiCameraBreak\?\.startIfDue\(nextNews\)/);
 assert.match(page,/window\.rdiSpotActive\|\|window\.rdiGeoActive/);
 assert.match(script,/video\.muted=true;video\.defaultMuted=true/);
 assert.match(script,/video\.volume=0/);
 assert.match(script,/window\.rdiSpotActive\|\|window\.rdiGeoActive/);
 assert.match(script,/window\.rdiLandscapeBreak=/);
 assert.match(script,/configReady\.then/);
 assert.match(css,/body\.rdi-spot-active #rdiLandscapes/);
 assert.match(css,/body\.rdi-geo-active #rdiLandscapes/);
 assert.match(script,/IMAGINI DE ARHIVĂ/);
 assert.doesNotMatch(script,/new Audio\(|audio\.play\(|\.volume=1/);
 assert.match(build.build,/^20\d{6}-[a-z0-9-]+$/);
 assert.match(page,new RegExp(build.build));
});
