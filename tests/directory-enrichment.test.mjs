import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../directory-enrichment.js',import.meta.url),'utf8');
const {splitDirectoryDescription,composeDirectoryDescription,businessReviewLinks,profileUrlAllowed,directoryIntro}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
test('optional business offerings stored as readable text compatible with Firestore rules',()=>{
 const desc=composeDirectoryDescription('Servicii pentru comunitate.',{services:'Livrări și catering',languages:'română, italiană',facebookUrl:'https://www.facebook.com/afacere'});
 const {intro,fields}=splitDirectoryDescription(desc);
 assert.equal(intro,'Servicii pentru comunitate.');
 assert.equal(fields.services,'Livrări și catering');
 assert.equal(fields.languages,'română, italiană');
 assert.equal(fields.facebookUrl,'https://www.facebook.com/afacere');
 assert.equal(directoryIntro({description:desc}),intro);
});
test('Google Maps query uses company and address without invented ratings',()=>{
 const links=businessReviewLinks({name:'Magazin Românesc',address:'Via Roma 10',city:'Bologna',category:'Magazine românești'});
 assert.ok(links.find(x=>x.name==='Google Maps').url.includes('query=Magazin%20Rom'));
 assert.ok(links.find(x=>x.name==='Facebook'));
 assert.ok(!links.find(x=>x.name==='Tripadvisor'));
 assert.ok(links.every(x=>!('rating' in x)));
});
test('a known Google Place ID links directly without copying reviews',()=>{
 const google=businessReviewLinks({name:'Business',city:'Roma',googlePlaceId:'ChIJGcmcg7ZC1moRAOacd3HoEwM'}).find(x=>x.name==='Google Maps');
 assert.ok(google.direct);
 assert.ok(google.url.includes('query_place_id=ChIJGcmcg7ZC1moRAOacd3HoEwM'));
});
test('source review pages link to original directory listing',()=>{
 const links=businessReviewLinks({name:'Example',city:'Como',sourceUrl:'https://deafara.com/firme/ro-it-example'});
 assert.equal(links.find(x=>x.name==='De afară').url,'https://deafara.com/firme/ro-it-example');
});
test('social profiles must be trustworthy domain URLs',()=>{
 assert.equal(profileUrlAllowed('https://facebook.com/verified','facebook.com'),true);
 assert.equal(profileUrlAllowed('javascript:alert(1)','facebook.com'),false);
 assert.equal(profileUrlAllowed('https://facebook.com.bad.test/review','facebook.com'),false);
});
