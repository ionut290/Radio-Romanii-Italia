import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseCameraConfig,validateCamera,slotDue} from '../youtube-camera-core.mjs';
const read=path=>readFile(new URL(path,import.meta.url),'utf8');
const camera={
  id:'bologna_1',country:'Italia',city:'Bologna',operator:'Operatore di prova',
  credit:'Operatore di prova',kind:'iframe',src:'https://example.org/camera/embed',
  youtube_live_rights:true,audio_muted:true,authorized_on:'2026-10-29',
  permission_reference:'autorizzazione editoriale registrata RDI #001'
};
test('webcam broadcasting is disabled until editorial approval is configured',async()=>{
 const file=JSON.parse(await read('../data/youtube-camera-breaks.json'));
 assert.equal(file.enabled,false);assert.deepEqual(file.cameras,[]);
 assert.equal(parseCameraConfig(file).enabled,false);
});
test('permission metadata is mandatory for each webcam before broadcast',()=>{
 assert.equal(validateCamera({...camera, youtube_live_rights:false}),null);
 assert.equal(validateCamera({...camera, audio_muted:false}),null);
 assert.equal(validateCamera({...camera,permission_reference:''}),null);
 assert.equal(validateCamera({...camera,permission_reference:'pending'}),null);
 assert.equal(validateCamera({...camera,authorized_on:''}),null);
 assert.equal(validateCamera({...camera,src:'http://example.org/cam'}),null);
 assert.equal(validateCamera({...camera,src:'https://localhost/cam'}),null);
 assert.equal(validateCamera({...camera,src:'https://127.0.0.1/cam'}),null);
 assert.equal(validateCamera({...camera,src:'javascript:alert(1)'}),null);
 assert.equal(validateCamera(camera)?.city,'Bologna');
});
test('cadence and duration are bounded and 5-news cadence works',()=>{
 const c=parseCameraConfig({enabled:true,after_news_cards:5,duration_seconds:30,cameras:[camera,camera]});
 assert.equal(c.enabled,true);assert.equal(c.cameras.length,1);
 assert.equal(c.every,5);assert.equal(c.duration,30);
 assert.deepEqual([1,2,3,4,5,6,10].map(n=>slotDue(n,c.every)),[false,false,false,false,true,false,true]);
 assert.equal(parseCameraConfig({enabled:true,after_news_cards:999,duration_seconds:999,cameras:[camera]}).duration,60);
 assert.equal(parseCameraConfig({enabled:true,after_news_cards:999,duration_seconds:999,cameras:[camera]}).every,20);
});
test('YouTube visual broadcast integrates camera breaks while preserving spot and geo coordination',async()=>{
 const page=await read('../youtube-news.html');
 const script=await read('../youtube-camera-breaks.js');
 const css=await read('../youtube-camera-breaks.css');
 assert.match(page,/src="\.\/youtube-camera-breaks\.js\?v=/);
 assert.match(page,/href="\.\/youtube-camera-breaks\.css\?v=/);
 assert.match(page,/window\.rdiCameraBreak\?\.startIfDue\(nextNews\)/);
 assert.match(page,/window\.rdiCameraBreak\?\.stop\(\)/);
 assert.match(page,/if\(!stories\.length\|\|window\.rdiSpotActive\|\|window\.rdiGeoActive\|\|window\.rdiTgActive\|\|window\.rdiWeatherActive\|\|window\.rdiDjPromoActive\)return/);
 assert.match(script,/window\.rdiGeoActive\|\|window\.rdiSpotActive/);
 assert.match(script,/document\.body\.classList\.remove\('rdi-camera-active'\)/);
 assert.match(script,/if\(demo\)/);
 assert.match(css,/#rdiCityCamera\[hidden\]/);
 assert.match(css,/body\.rdi-spot-active #rdiCityCamera/);
 assert.doesNotMatch(script,/audio\.pause\(\)|AzuraCast\.pause|#audio|new Audio\(/);
});
