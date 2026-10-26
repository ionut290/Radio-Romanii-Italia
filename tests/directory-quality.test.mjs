import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source=await readFile(new URL("../directory-quality.js",import.meta.url),"utf8");
const {missingForBusiness}=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
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
