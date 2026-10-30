import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const read = path => readFile(new URL(path, import.meta.url),'utf8');

test('daily TG with rights-approved video remains tied to actual AzuraCast audio',async()=>{
  const js=await read('../youtube-tg-sera.js');
  const css=await read('../youtube-tg-sera.css');
  const page=await read('../youtube-news.html');
  assert.match(page,/youtube-tg-sera.js\?v=/);
  assert.match(js,/nowplaying\/radio-romanii-italia/);
  assert.match(js,/editionFrom\(np\)/);
  assert.match(js,/RDI-TG-SERA-IT-/);
  assert.match(js,/validFootage\(current.video\)/);
  assert.match(js,/current.video.seconds/);
  assert.match(js,/footage.muted = true/);
  assert.match(js,/footage.volume = 0/);
  assert.match(js,/footage.defaultMuted = true/);
  assert.match(js,/stopFootage\(\)/);
  assert.match(js,/footage.play\(\)\.catch/);
  assert.match(js,/if \(v.kind === "repertory"\) return u.hostname === "videos.pexels.com"/);
  assert.doesNotMatch(js,/new Audio\(|audio\.play\(|audio\.src\s*=/);
  assert.match(css,/\.rdi-tg-footage.is-visible/);
});
test('video-rights catalog has no unauthorised newsroom originals',async()=>{
  const x=JSON.parse(await read('../data/tg-video-licenses.json'));
  const landscapes=JSON.parse(await read('../data/youtube-landscapes.json'));
  assert.equal(x.schema_version,1);
  assert.deepEqual(x.event_clips,[]);
  for (const b of x.repertory_clips) {
    const src=landscapes.items.find(y=>y.id===b.landscape_id);
    assert.equal(src?.rights_reviewed,true);
    assert.equal(src?.audio_muted,true);
    assert.equal(src?.kind,'video');
    assert.match(src.license_url,/^https:\/\/www\.pexels\.com\//);
    assert.ok(b.all_terms.every(group=>group.length));
    assert.ok(b.max_seconds <= 18);
  }
});
