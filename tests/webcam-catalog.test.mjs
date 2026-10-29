import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Script } from 'node:vm';

const html = readFileSync(new URL('../webcam.html', import.meta.url), 'utf8');
const js = readFileSync(new URL('../webcam-catalog.js', import.meta.url), 'utf8');
const verifiedMatch = js.match(/const VERIFIED=(\[[^\n]+\]);/);
const discoveryMatch = js.match(/const DISCOVERY=(\{[^\n]+\});/);
assert.ok(verifiedMatch && discoveryMatch, 'camera lists must exist as serializable data');
const verified = JSON.parse(verifiedMatch[1]);
const discovery = JSON.parse(discoveryMatch[1]);

test('browser directory JavaScript parses cleanly', () => {
  assert.doesNotThrow(() => new Script(js));
});

test('homepage-compatible webcam page includes working controls and sources', () => {
  for(const id of ['webcam-city-list','webcam-search','webcam-country','webcam-view','webcam-more','webcam-stats','camera-frame','camera-title','camera-source','webcam-no-embed','webcam-discover'])
    assert.match(html, new RegExp('id="'+id+'"'));
  assert.match(html, /src="\.\/webcam-catalog\.js/);
  assert.match(html, /https:\/\/webcams\.windy\.com\/webcams\/public\/embed\/player\//);
});

test('only validated numeric 10-digit camera IDs enter the official embed player', () => {
  assert.ok(verified.length>=30);
  assert.equal(new Set(verified.map(c=>c[4])).size,verified.length);
  for(const [country,city,region,place,id] of verified){
    assert.ok(['RO','IT'].includes(country));
    assert.ok(city && region && place);
    assert.match(id,/^\d{10}$/);
  }
  assert.match(js, /https:\/\/webcams\.windy\.com\/webcams\/public\/embed\/player\//);
});

test('directory offers broad search but never mislabels unverified towns as live feeds', () => {
  const names=Object.values(discovery).flatMap(s=>s.split(';'));
  assert.ok(names.length>=550);
  assert.ok(Object.keys(discovery).some(x=>x.startsWith('RO|')));
  assert.ok(Object.keys(discovery).some(x=>x.startsWith('IT|')));
  assert.ok(Object.keys(discovery).some(x=>x.startsWith('MD|')));
  assert.match(js, /Localitate de explorat/);
  assert.match(js, /frame\.src='about:blank'/);
  assert.match(html, /imagini actualizate, nu transmisie video continuă/i);
});
