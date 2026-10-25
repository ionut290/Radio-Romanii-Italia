import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const text=path=>readFile(new URL('../'+path,import.meta.url),'utf8');
const json=async path=>JSON.parse(await text(path));

test('ISTAT count is dated, sourced and explicitly not live',async()=>{
 const data=await json('data/romanians-italy.json');
 assert.equal(data.residents,1053042);
 assert.equal(data.as_of,'2025-01-01');
 assert.equal(data.realtime,false);
 assert.match(data.source_url,/^https:\/\/demo\.istat\.it\//);
 assert.equal(Object.keys(data.regions).length,20);
 assert.equal(Object.values(data.regions).reduce((a,b)=>a+b,0),data.residents);
});

test('home shows the census with a dated fallback and its methodology',async()=>{
 const page=await text('index.html'),detail=await text('romani-italia.html');
 assert.match(page,/id="rdi-census"/);
 assert.match(page,/rdi-census\.js/);
 assert.match(page,/romani-italia\.html/);
 assert.match(detail,/Nu este un contor în timp real/);
 assert.match(detail,/ISTAT/);
});

test('newsroom and archive pages are linked and protect source URLs',async()=>{
 const page=await text('redactie.html'), archive=await text('arhiva.html');
 assert.match(page,/data\/editorial-status\.json/);
 assert.match(page,/autentificare pe GitHub/);
 assert.match(page,/pending_total/);
 assert.match(archive,/data\/editorial-archive\.json/);
 assert.match(archive,/textContent/);
 assert.match(archive,/https:/);
});

test('archived entries retain original publication dates and article bodies',async()=>{
 const data=await json('data/editorial-archive.json');
 assert.ok(Array.isArray(data.items));
 assert.ok(data.items.length>0);
 assert.ok(data.items.every(x=>x.title&&x.published&&x.url&&x.editorial===true));
 const code=await text('scripts/archive_editorial.py');
 assert.match(code,/before\/after feed pruning/);
 assert.doesNotMatch(code,/timedelta\(hours=48\)/);
});

test('automation generates status and preserves old editorial archive',async()=>{
 const editorial=await text('.github/workflows/editorial.yml');
 const news=await text('.github/workflows/news.yml');
 assert.match(editorial,/Arhivează materialele existente înainte de expirarea lor/);
 assert.match(editorial,/git add editorial\.json data\/editorial-archive\.json/);
 assert.match(news,/build_editorial_status\.py/);
 assert.match(news,/git add -A news\.json editorial-images\/ data\/editorial-status\.json/);
});
