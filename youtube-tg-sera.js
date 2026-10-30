/* RDI TG delle 18: images and editorial context only for the exact real AzuraCast track.
   Never produce alternative audio or an unverified/de-synced video bulletin. */
(() => {
  "use strict";
  const radio = "https://radio-romanii-italia.duckdns.org";
  const endpoint = radio + "/api/nowplaying/radio-romanii-italia";
  const layer = document.createElement("section");
  layer.id = "rdiEveningTg";
  layer.hidden = true;
  layer.setAttribute("aria-label", "TG RDI della sera in diretta");
  layer.innerHTML = '<div class="rdi-tg-bg"><img class="rdi-tg-photo" alt=""></div><div class="rdi-tg-shade"></div><div class="rdi-tg-header"><div class="rdi-tg-brand">RADIO ROMÂNII DIN ITALIA</div><div class="rdi-tg-live">TG DELLE 18</div></div><div class="rdi-tg-content"><div class="rdi-tg-kicker"></div><h1 class="rdi-tg-title"></h1><p class="rdi-tg-summary"></p></div><div class="rdi-tg-footer"><div><div class="rdi-tg-source"></div><div class="rdi-tg-notice"></div></div><span class="rdi-tg-count"></span></div><div class="rdi-tg-progress"></div>';
  document.getElementById("stage").append(layer);
  const $ = s => layer.querySelector(s);
  const photo = $(".rdi-tg-photo"), kicker = $(".rdi-tg-kicker"),
    title = $(".rdi-tg-title"), summary = $(".rdi-tg-summary"),
    source = $(".rdi-tg-source"), notice = $(".rdi-tg-notice"),
    count = $(".rdi-tg-count"), progress = $(".rdi-tg-progress");
  let edition = "", manifest = null, pending = "", lastSeen = 0,
    playedAt = 0, startAt = 0, duration = 0, sceneIndex = -1, sectionIndex = -1,
    lockedUntil = 0;
  const headings = ["IL FATTO", "IL CONTESTO", "LE CONSEGUENZE", "GLI SVILUPPI"];
  const clean = text => String(text || "").replace(/\s+/g, " ").trim();
  const editionFrom = np => {
    const s = [np?.song?.title, np?.song?.text].filter(Boolean).join(" ");
    const match = s.match(/RDI[\s_-]*TG[\s_-]*SERA[\s_-]*IT[\s_-]*(20\d{6})/i);
    return match ? match[1] : "";
  };
  function hide() {
    window.rdiTgActive = false;
    layer.hidden = true;
    document.body.classList.remove("rdi-tg-active");
    sceneIndex = -1; sectionIndex = -1; manifest = null;
    photo.removeAttribute("src"); photo.classList.remove("is-visible");
    if (!window.rdiSpotActive && !window.rdiGeoActive) window.rdiResumeNews?.();
  }
  function show() {
    if (window.rdiTgActive) return;
    window.rdiTgActive = true;
    window.rdiPauseNews?.();
    document.body.classList.add("rdi-tg-active");
    layer.hidden = false;
  }
  function check(data, expected) {
    if (data?.schema_version !== 1 || data?.type !== "rdi-daily-tg" ||
        data?.language !== "it" || data?.edition_id !== expected ||
        data?.track_title !== "RDI-TG-SERA-IT-" + expected ||
        !(Number(data.audio_duration_seconds) > 240) ||
        !Array.isArray(data.timeline) || data.timeline.length < 6) return false;
    return data.timeline.every(s =>
      Number.isFinite(s.start_seconds) && Number.isFinite(s.end_seconds) &&
      s.end_seconds > s.start_seconds &&
      (s.kind !== "story" || (clean(s.title) && clean(s.category) && clean(s.source_url).startsWith("https://"))));
  }
  async function load(code) {
    if (pending === code) return;
    pending = code;
    try {
      const res = await fetch("./data/tg-sera/" + code + ".json?ts=" + Date.now(),
        {cache:"no-store",signal:AbortSignal.timeout(7000)});
      if (!res.ok) throw Error("TG chronology missing");
      const data = await res.json();
      if (!check(data, code)) throw Error("Invalid TG chronology");
      if (pending !== code || edition !== code) return;
      manifest = data; sceneIndex = -1; sectionIndex = -1;
      draw();
    } catch (_) {
      if (pending === code) {
        lockedUntil = Date.now() + 12000;
        if (window.rdiTgActive) hide();
      }
    } finally {
      if (pending === code) pending = "";
    }
  }
  function accept(data) {
    const np = data?.now_playing;
    if (!np || data?.is_online === false || data?.live?.is_live === true) return;
    const code = editionFrom(np);
    if (!code) {
      if (window.rdiTgActive && Date.now() - lastSeen > 5000) hide();
      return;
    }
    lastSeen = Date.now();
    if (edition !== code) {
      if (window.rdiTgActive) hide();
      edition = code; manifest = null; sceneIndex = -1; sectionIndex = -1;
    }
    playedAt = Number(np.played_at) || 0;
    duration = Number(np.duration) || 0;
    startAt = Date.now() / 1000 - (Number(np.elapsed) || 0);
    if (!manifest && Date.now() >= lockedUntil) load(code);
    if (manifest) draw();
  }
  function elapsed() {
    if (playedAt > 1_000_000_000) {
      const value = Date.now() / 1000 - playedAt;
      if (value >= -2 && value < 2400) return Math.max(0, value);
    }
    return Math.max(0, Date.now() / 1000 - startAt);
  }
  function setPhoto(url, text) {
    photo.classList.remove("is-visible");
    photo.onerror = () => {photo.classList.remove("is-visible");photo.removeAttribute("src");};
    photo.onload = () => photo.classList.add("is-visible");
    if (typeof url === "string" && /^\.\/editorial-images\/[a-z0-9/_-]+\.(?:jpg|png|webp|svg)$/i.test(url)) {
      photo.alt = text;
      photo.src = url;
    } else {
      photo.removeAttribute("src");
    }
  }
  function draw() {
    if (!manifest || Date.now() - lastSeen > 9000) {
      if (window.rdiTgActive && Date.now() - lastSeen > 9000) hide();
      return;
    }
    const at = elapsed();
    const max = Math.min(Number(manifest.audio_duration_seconds), duration > 0 ? duration : Infinity);
    if (at > max + 1) {hide();return;}
    const scenes = manifest.timeline;
    let i = scenes.findIndex(s => at >= s.start_seconds && at < s.end_seconds);
    if (i === -1) i = at < scenes[0].start_seconds ? 0 : scenes.length - 1;
    const current = scenes[i];
    if (sceneIndex !== i) {
      sceneIndex = i; sectionIndex = -1; show();
      const story = current.kind === "story";
      layer.classList.toggle("rdi-tg-story", story);
      if (!story) {
        kicker.textContent = current.kind === "outro" ? "ARRIVEDERCI" : "IN DIRETTA";
        title.textContent = current.kind === "outro" ? "Grazie per averci seguito" : "TG RDI DELLA SERA";
        summary.textContent = "Le notizie, il contesto e gli approfondimenti da Italia, Romania e diaspora.";
        source.textContent = "Radio Românii din Italia";
        notice.textContent = "Edizione con chiusura notizie alle ore 16:00, ora italiana";
        count.textContent = "EDIZIONE " + manifest.edition_id;
        setPhoto("", "");
      } else {
        kicker.textContent = clean(current.category).toLocaleUpperCase("it");
        title.textContent = clean(current.title);
        source.textContent = clean(current.source_name);
        notice.textContent = clean(current.image_notice);
        const number = scenes.slice(0, i + 1).filter(s => s.kind === "story").length;
        count.textContent = "SERVIZIO " + number + " / " + scenes.filter(s => s.kind === "story").length;
        setPhoto(current.image, current.image_notice);
      }
    }
    if (current.kind === "story") {
      const segments = Array.isArray(current.sections) && current.sections.length === 4 ? current.sections : null;
      const fractions = Array.isArray(current.section_ends) && current.section_ends.length === 4 ? current.section_ends : [.3,.55,.78,1];
      const fraction = (at - current.start_seconds) / Math.max(1, current.end_seconds - current.start_seconds);
      const j = Math.max(0, fractions.findIndex(end => fraction < end));
      if (sectionIndex !== j) {
        sectionIndex = j;
        kicker.textContent = clean(current.category).toLocaleUpperCase("it") + " · " + headings[j];
        summary.textContent = clean(segments?.[j] || current.summary).slice(0, 320);
      }
    }
    progress.style.width = Math.min(100, Math.max(0, 100 * at / Number(manifest.audio_duration_seconds))) + "%";
  }
  async function poll() {
    try {
      const response = await fetch(endpoint + "?tg=" + Date.now(),
        {cache:"no-store",signal:AbortSignal.timeout(5000)});
      if (response.ok) accept(await response.json());
    } catch (_) {
      // Never invent on-air status when the station is unreachable.
    } finally {
      setTimeout(poll, 2500);
    }
  }
  window.addEventListener("rdi:nowplaying", event => accept(event.detail));
  setInterval(draw, 200);
  poll();
})();
