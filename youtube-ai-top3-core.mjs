/* Pure RDI AI MUSIC TV chart rules: no browser, no audio, no side effects. */
export function normalizeSong(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("it").replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
}
export function rankedTop3(payload) {
  if (!payload || !Array.isArray(payload.tracks)) return [];
  const rows = [], seen = new Set();
  for (const t of payload.tracks) {
    if (!t || typeof t !== "object" || !/^[a-f0-9]{32}$/i.test(String(t.id || ""))) continue;
    const title = String(t.title || "").trim().slice(0, 140);
    const artist = String(t.artist || "").trim().slice(0, 100);
    if (!title || !artist || seen.has(t.id)) continue;
    // Live countdown must contain only approved tracks whose original audio
    // is available for public playback on RDI. A link-only entry is ineligible.
    if (t.audio_preview !== 1 && t.audio_preview !== true) continue;
    seen.add(t.id);
    const votes = Number(t.votes);
    if (!Number.isSafeInteger(votes) || votes < 0) continue;
    rows.push({id:t.id, title, artist, votes, created_at:String(t.created_at||""),audio_preview:t.audio_preview===1 || t.audio_preview===true});
  }
  // Maintain API ranking order among audio-eligible entries. The YouTube
  // Top 3 is a distinct, audio-only chart; the main public chart is unchanged.
  // E.g. public #2 'Roma' (no uploaded audio) is skipped and the next
  // approved, playable song moves into the TV countdown.
  return rows.slice(0, 3).map((r, index)=>({...r,rank:index+1}));
}
export function romeClock(input) {
  const dt = input instanceof Date ? input : new Date(input);
  if (!Number.isFinite(dt.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-GB",{
    timeZone:"Europe/Rome", year:"numeric",month:"2-digit",day:"2-digit",
    hour:"2-digit",minute:"2-digit",hourCycle:"h23"
  }).formatToParts(dt);
  const get = type => parts.find(p=>p.type===type)?.value;
  return {day:get("year")+"-"+get("month")+"-"+get("day"),
    hour:Number(get("hour")),minute:Number(get("minute"))};
}
export function due({now,shownDay,tracks,preview=false,enabled=true}) {
  if (!enabled || !Array.isArray(tracks) || tracks.length!==3) return false;
  if (preview) return true;
  const clock = romeClock(now);
  if (!clock || clock.day===shownDay) return false;
  const minute=clock.hour*60+clock.minute;
  return minute>=20*60+30 && minute<23*60+50;
}
export function onAirRank(nowplaying,top3) {
  const song=nowplaying?.now_playing?.song || {};
  const title=normalizeSong(song.title);
  const artist=normalizeSong(song.artist);
  if (!title || !artist || !Array.isArray(top3)) return null;
  return top3.find(t=>normalizeSong(t.title)===title && normalizeSong(t.artist)===artist) || null;
}
