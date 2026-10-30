import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
const root=process.cwd();
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
test("2026 daily calendar covers Oct 30 through Dec 31 without duplicates",()=>{
 const days=read("data/calendario-filosofico-2026.json").days;
 assert.equal(days.length,63);
 assert.equal(days[0].date,"2026-10-30");
 assert.equal(days.at(-1).date,"2026-12-31");
 assert.equal(new Set(days.map(x=>x.date)).size,63);
 assert.equal(new Set(days.map(x=>x.quote)).size,63);
});
test("current pointer is valid, and image exists in repository",()=>{
 const d=read("data/calendario-filosofico-oggi.json");
 assert.match(d.date,/^\d{4}-\d{2}-\d{2}$/);
 assert.ok(d.quote?.length>12);
 assert.match(d.image,/^\/(?!\/)[a-zA-Z0-9/_-]+\.(png|jpg|jpeg|webp)$/i);
 assert.equal(fs.existsSync(path.join(root,d.image.slice(1))),true);
});
test("each daily fallback photo is present; never use an unresolvable path",()=>{
 for(const d of read("data/calendario-filosofico-2026.json").days) {
   assert.match(d.image,/^\/(?!\/)[a-zA-Z0-9/_-]+\.(png|jpg|jpeg|webp)$/i);
   assert.equal(fs.existsSync(path.join(root,d.image.slice(1))),true,d.date);
 }
});
