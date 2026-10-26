import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const text = path => readFileSync(new URL("../"+path,import.meta.url),"utf8");
const incidents=JSON.parse(text("data/attack-monitor.json"));
const candidates=JSON.parse(text("data/attack-candidates.json"));
const articles=JSON.parse(text("editorial.json"));
const iso = /^\d{4}-\d{2}-\d{2}$/;

test("public map has documented incidents with unique IDs, defensible coordinates and traceable HTTPS sources",()=>{
  assert.ok(Array.isArray(incidents.items) && incidents.items.length>=3);
  const ids=new Set();
  for(const v of incidents.items){
    assert.ok(v.id && !ids.has(v.id));ids.add(v.id);
    assert.match(v.date,iso);
    assert.ok(v.date<="2026-10-26","Never label a future event historical in this fixture");
    assert.ok(Number.isFinite(v.lat)&&Number.isFinite(v.long)&&Math.abs(v.lat)<=90&&Math.abs(v.long)<=180);
    assert.ok(v.precision && v.precision.startsWith("approx"));
    assert.ok(["attack","foiled"].includes(v.type));
    for(const field of ["title_ro","title_it","description_ro","description_it","country","place"])assert.ok(v[field]?.length>3,field);
    for(const field of ["killed","injured"])assert.ok(v[field]===null || (Number.isInteger(v[field])&&v[field]>=0));
    assert.ok(v.sources.length>=1);
    for(const source of v.sources)assert.match(source.url,/^https:\/\//);
  }
});
test("incidents link only to real RDI article IDs",()=>{
  const ids=new Set(articles.items.map(x=>x.id));
  for(const v of incidents.items)if(v.rdi_article_id) assert.ok(ids.has(v.rdi_article_id),v.rdi_article_id);
});
test("candidate reports are kept out of the published map and editorial feed by default",()=>{
  assert.ok(Array.isArray(candidates.items));
  assert.ok(incidents.items.every(x=>!x.id.startsWith("lead-")));
  assert.ok(!text("scripts/update_attack_candidates.py").includes('Path("data/attack-monitor.json")'));
  assert.ok(!text("scripts/update_attack_candidates.py").includes('Path("editorial.json")'));
});
test("navigation, map, translation, and provenance links exist",()=>{
  assert.match(text("index.html"),/harta-atacurilor\.html/);
  assert.match(text("redactie.html"),/incident-leads\.yml/);
  assert.match(text("harta-atacurilor.html"),/harta-atacurilor\.js/);
  assert.match(text("harta-atacurilor.js"),/data\/attack-monitor\.json/);
  assert.match(text("harta-atacurilor.html"),/openstreetmap\.org\/copyright/);
});
