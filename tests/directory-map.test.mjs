import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../directory-map.js',import.meta.url),'utf8');
const {normalize,validPoint,mergeBusinesses,filterBusinesses,locateBusiness,safeUrl} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
test('search ignores Romanian accents and matches addresses and regions',()=>{
  const records=[{name:'Îngrijire acasă',city:'Forlì',region:'Emilia-Romagna',address:'Via Unirii 3',category:'Servicii'}];
  assert.equal(normalize('ȘȚĂ ÎÂ'),'sta ia');
  assert.equal(filterBusinesses(records,{search:'ingrijire',city:'forli',region:'emilia'}).length,1);
  assert.equal(filterBusinesses(records,{search:'Unirii'}).length,1);
  assert.equal(filterBusinesses(records,{category:'Magazine românești'}).length,0);
});
test('approved records take precedence and distinct branches are retained',()=>{
  const external={id:'public',name:'Magazin Ștefan',city:'Roma',address:'Via A 1'};
  const approved={...external,id:'rdi',name:'Magazin Stefan',phone:'+3901'};
  const branch={...external,id:'second',address:'Via A 2'};
  assert.deepEqual(mergeBusinesses([external,branch],[approved]).map(x=>x.id),['rdi','second']);
});
test('invalid coordinates cannot create plausible but false pins',()=>{
  assert.equal(validPoint(null,null),false);assert.equal(validPoint(0,0),false);
  assert.equal(validPoint('44','11'),false);assert.equal(validPoint(NaN,11),false);
  assert.equal(validPoint(44.5,11.3),true);
  assert.equal(locateBusiness({city:'Bologna',address:'Activitate online în toată Italia'},{bologna:[44.5,11.3]}),null);
  assert.deepEqual(locateBusiness({city:'Bologna',address:'Via A 1'},{bologna:[44.5,11.3]}),{lat:44.5,lng:11.3,precision:'city'});
  assert.deepEqual(locateBusiness({lat:44.51,lng:11.31,address:'Via A 1'}),{lat:44.51,lng:11.31,precision:'source'});
  assert.equal(locateBusiness({city:'Unknown'}),null);
});
test('business links reject executable and invalid URLs',()=>{
  assert.equal(safeUrl('javascript:alert(1)'),null);assert.equal(safeUrl('data:text/html,hi'),null);
  assert.equal(safeUrl('https://example.org/path'),'https://example.org/path');
});
test('import contains source references, unique IDs and only valid or absent coordinates',async()=>{
  const data=JSON.parse(await readFile(new URL('../data/directory-public.json',import.meta.url),'utf8'));
  assert.ok(data.businesses.length>0);assert.equal(new Set(data.businesses.map(b=>b.id)).size,data.businesses.length);
  for(const b of data.businesses){assert.ok(b.name);assert.ok(b.city||b.address);assert.ok(safeUrl(b.sourceUrl));assert.equal(b.verification,'public-source');if(b.lat!==null&&b.lat!==undefined)assert.ok(validPoint(b.lat,b.lng));}
});

test('mouse wheel zoom is enabled on the map',()=>{
 assert.ok(source.includes('scrollWheelZoom:true'));
 assert.ok(!source.includes('scrollWheelZoom:false'));
});

test('an updated official address must use an approximate town marker instead of stale street coordinates',()=>{
  const cities={torino:[45.07,7.68]};
  const business={name:'Officina',city:'Torino',address:'Strada nuova 139/32',lat:45.11,lng:7.75,locationPrecision:'city'};
  assert.deepEqual(locateBusiness(business,cities),{lat:45.07,lng:7.68,precision:'city'});
  assert.equal(locateBusiness(business,{}),null);
});
