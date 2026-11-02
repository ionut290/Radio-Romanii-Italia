import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const page=await readFile(new URL('../youtube-news.html',import.meta.url),'utf8');
const spots=await readFile(new URL('../youtube-spots.js',import.meta.url),'utf8');
const core=await readFile(new URL('../youtube-spots-core.js',import.meta.url),'utf8');
const config=JSON.parse(await readFile(new URL('../data/spot-campaigns.json',import.meta.url),'utf8'));
const {selectCampaign,sceneAt}=await import('data:text/javascript;base64,'+Buffer.from(core).toString('base64'));

test('broadcast loads the spot overlay and pauses the news while advertising',()=>{
  assert.match(page,/src="\.\/youtube-spots\.js\?v=[^"]+"/);
  assert.match(page,/window\.rdiPauseNews=function/);
  assert.match(page,/window\.rdiResumeNews=function/);
  assert.match(page,/if\(!stories\.length\|\|window\.rdiSpotActive\|\|window\.rdiGeoActive\|\|window\.rdiTgActive\|\|window\.rdiWeatherActive\|\|window\.rdiDjPromoActive\|\|window\.rdiPhilosophyActive\)return/);
  assert.match(spots,/window\.rdiPauseNews\?\.\(\)/);
  assert.match(spots,/window\.rdiResumeNews\?\.\(\)/);
});

test('regular music never triggers a visual spot',()=>{
  assert.equal(selectCampaign({playlist:'rock',song:{title:'Rockstar',text:'Rockstar'}},config),null);
});

test('a recognized ad playlist displays nine campaign frames',()=>{
  const campaign=selectCampaign({playlist:'spot',song:{title:'erre di i',text:'erre di i'}},config);
  assert.equal(campaign?.id,'radio');
  assert.equal(campaign.scenes.length,9);
  assert.equal(sceneAt({...campaign,sceneSeconds:10},0).index,0);
  assert.equal(sceneAt({...campaign,sceneSeconds:10},89).index,8);
});

test('new ad audio automatically receives nine branded scenes',()=>{
  const campaign=selectCampaign({playlist:'spot',song:{title:'Nuovo spot locale',text:'Nuovo spot locale',art:'https://example.org/art.jpg'}},config);
  assert.equal(campaign?.id,'automatic');
  assert.equal(campaign.scenes.length,9);
});

test('Oriflame ad uses its video and contact, while ordinary Oriflame music is ignored',()=>{
 const song={title:'Spot Oriflame Italia - Magda Niculae',text:'RDI - Spot Oriflame Italia - Magda Niculae'};
 const campaign=selectCampaign({playlist:'spot',song},config);
 assert.equal(campaign.id,'oriflame');
 assert.match(campaign.video,/^https:\/\//);
 assert.equal(campaign.footer,'329 118 4717');
 assert.equal(selectCampaign({playlist:'rock',song:{title:'Oriflame',text:'Oriflame'}},config),null);
});

test('campaign video is muted and synchronized to radio elapsed time',()=>{
 assert.match(spots,/video\.muted=true/);
 assert.match(spots,/Math\.abs\(video\.currentTime-target\)>1/);
 assert.match(spots,/video\.pause\(\);video\.hidden=true/);
});
