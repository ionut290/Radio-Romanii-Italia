import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source=await readFile(new URL("../directory-quality.js",import.meta.url),"utf8");
const {missingForBusiness,filterIncompleteRecords}=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
test("directory coverage highlights missing business contacts and photos without inventing WhatsApp",()=>{
 const b={name:"Negozio Românesc",phone:"+39 3331234567",email:"info@negozio.example",website:"https://negozio.example",hours:"Lun-Ven",imageUrls:[]};
 assert.deepEqual(missingForBusiness(b),["WhatsApp","Fotografie"]);
});
test("directory coverage accepts verified https business images but ignores empty or insecure images",()=>{
 const b={phone:"123",whatsapp:"+39123456",email:"info@example.com",website:"https://example.com",hours:"9-18",imageUrls:["http://example.com/p.jpg"]};
 assert.deepEqual(missingForBusiness(b),["Fotografie"]);
 b.imageUrls=["https://example.com/owned.jpg"];
 assert.deepEqual(missingForBusiness(b),[]);
});

test("public photo source requires documented reuse rights",async()=>{
 const ghid=await readFile(new URL("../ghid.js",import.meta.url),"utf8");
 assert.ok(ghid.includes('entry.photoRightsStatus==="permission-granted"'));
 assert.ok(ghid.includes('entry.photoRightsStatus==="owned-by-rdi"'));
 assert.ok(ghid.includes('approvedImages.length?{imageUrls:approvedImages}'));
});
test("directory rules contain only one approval workflow and allow optional reviewed media",async()=>{
 const rules=await readFile(new URL("../firestore.rules",import.meta.url),"utf8");
 assert.equal(rules.split("match /directoryBusinessEdits/").length-1,1);
 assert.equal(rules.split("match /directoryAds/").length-1,1);
 assert.ok(rules.includes("'email','imageUrls'])"));
});

test("filter and CSV share the same missing-field criteria",()=>{
 const a={name:"Solo email",phone:"+39011",email:"a@b.it",whatsapp:"",website:"https://a.it",hours:"09-17",imageUrls:["https://a.it/a.jpg"]};
 const b={name:"Senza foto",phone:"",email:"",whatsapp:"",website:"",hours:"",imageUrls:[]};
 const rows=[a,b];
 assert.deepEqual(filterIncompleteRecords(rows,"phone"),[b]);
 assert.deepEqual(filterIncompleteRecords(rows,"photos"),[b]);
 assert.deepEqual(filterIncompleteRecords(rows,"whatsapp"),[a,b]);
 assert.deepEqual(filterIncompleteRecords(rows,""),[a,b]);
});
