import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const base=JSON.parse(await readFile(new URL('../data/directory-public.json',import.meta.url),'utf8'));
const detail=JSON.parse(await readFile(new URL('../data/directory-enrichments.json',import.meta.url),'utf8'));
const ids=new Set(base.businesses.map(x=>x.id));
const values=Object.values(detail.records);
test('every enrichment belongs to an existing business and cites public evidence',()=>{
 assert.ok(values.length>=30);
 for(const [id,b] of Object.entries(detail.records)){
  assert.ok(ids.has(id),id);
  assert.match(b.detailsCheckedAt,/^\d{4}-\d{2}-\d{2}$/);
  assert.match(b.detailsSourceUrl,/^https:\/\//);
  assert.ok(b.detailsSourceName);
  assert.ok(['official-source','public-directory','location-conflict','identity-conflict'].includes(b.verificationDetail));
  if(b.reviewHold)assert.ok(b.reviewReason);
  else assert.ok(b.description&&b.services);
 }
});
test('quarantined records must not appear in public directory',()=>{
 const held=values.filter(b=>b.reviewHold);
 assert.ok(held.length>=2,'at least the originally conflicted listings should remain on hold');
 const publicRows=base.businesses.filter(b=>!detail.records[b.id]?.reviewHold);
 assert.equal(publicRows.length,base.businesses.length-held.length);
});
test('approved own business listings remain independent of imported enrichment metadata',()=>{
 assert.equal(base.businesses.length,new Set(base.businesses.map(x=>x.id)).size);
 assert.ok(!values.some(x=>Object.hasOwn(x,'uid')||Object.hasOwn(x,'status')));
});

test('research backlog covers exactly all remaining public listings without inventing data',async()=>{
 const backlog=JSON.parse(await readFile(new URL('../data/DIRECTORY-RESEARCH-BACKLOG.json',import.meta.url),'utf8'));
 const expected=base.businesses.filter(b=>!Object.hasOwn(detail.records,b.id));
 assert.equal(backlog.total,expected.length);
 assert.equal(backlog.items.length,expected.length);
 assert.equal(new Set(backlog.items.map(x=>x.id)).size,backlog.items.length);
 assert.deepEqual(new Set(backlog.items.map(x=>x.id)),new Set(expected.map(x=>x.id)));
 for(const entry of backlog.items){
   assert.equal(entry.status,'da_ricercare');
   assert.match(entry.sourceUrl,/^https:\/\//);
   assert.ok(entry.missing.includes('description'));
 }
});
