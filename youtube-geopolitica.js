/* RDI Geopolitica: strictly synchronize approved article slides to the real
 * AzuraCast MP3 currently on air. Never display a draft before it plays.
 * Visual layer only; it does not start, stop or modify the audio stream.
 */
(() => {
  "use strict";
  const radio = "https://radio-romanii-italia.duckdns.org";
  const url = radio + "/api/nowplaying/radio-romanii-italia";
  const layer = document.createElement("section");
  layer.id = "rdiGeoVideo";
  layer.hidden = true;
  layer.setAttribute("aria-label", "Notiziario geopolitico in diretta");
  layer.innerHTML = '<div class="geo-screen-ambient"></div><div class="geo-screen-head"><span class="geo-screen-kicker">RADIO ROMÂNII DIN ITALIA</span><span class="geo-screen-pill">● GEOPOLITICA</span></div><div class="geo-screen-content"><div class="geo-screen-country"></div><h1 class="geo-screen-title"></h1><p class="geo-screen-summary"></p><div class="geo-screen-divider"></div><p class="geo-screen-site">Articoli completi e fonti su <strong>radioromanii.duckdns.org/geopolitica.html</strong></p></div><div class="geo-screen-foot"><span class="geo-screen-step"></span><span class="geo-screen-date"></span></div><div class="geo-screen-progress"></div>';
  document.getElementById("stage").append(layer);
  const country = layer.querySelector(".geo-screen-country");
  const title = layer.querySelector(".geo-screen-title");
  const summary = layer.querySelector(".geo-screen-summary");
  const footStep = layer.querySelector(".geo-screen-step");
  const date = layer.querySelector(".geo-screen-date");
  const progress = layer.querySelector(".geo-screen-progress");
  let active = null, edition = "", pending = "", lastScene = -1;
  let lastMatched = 0, playedAt = 0, startByElapsed = 0, songDuration = 0;
  let lockedUntil = 0;

  const editionFrom = np => {
    const raw = [np?.song?.title, np?.song?.text].filter(Boolean).join(" ");
    const match = raw.match(/RDI[\s_-]*GEOPOLITICA[\s_-]*IT[\s_-]*(20\d{6})[\s_-]*(\d{4})/i);
    return match ? match[1] + "-" + match[2] : null;
  };
  const clean = text => String(text || "").replace(/\s+/g, " ").trim();
  function stop() {
    active = null; edition = ""; lastScene = -1;
    window.rdiGeoActive = false;
    layer.hidden = true;
    document.body.classList.remove("rdi-geo-active");
    if (!window.rdiSpotActive) window.rdiResumeNews?.();
  }
  function open() {
    if (window.rdiGeoActive) return;
    window.rdiGeoActive = true;
    window.rdiPauseNews?.();
    document.body.classList.add("rdi-geo-active");
    layer.hidden = false;
  }
  function validManifest(manifest, code) {
    const scenes = manifest?.timeline;
    return manifest?.schema_version === 1 && manifest.language === "it" &&
      manifest.edition_id === code &&
      Array.isArray(scenes) && scenes.length >= 4 &&
      Number(manifest.audio_duration_seconds) > 40 &&
      scenes.every(s => Number.isFinite(s.start_seconds) &&
        Number.isFinite(s.end_seconds) && s.end_seconds > s.start_seconds &&
        (s.kind !== "story" || (clean(s.title) && clean(s.country)))) &&
      scenes.some(s => s.kind === "story");
  }
  async function load(code) {
    if (pending === code) return;
    pending = code;
    try {
      // The strict per-edition filename avoids mixing the current audio with
      // visual timings from a newer or older geopolitical bulletin.
      const response = await fetch("./data/geopolitica-tv/" + code + ".json?r=" + Date.now(),
        { cache: "no-store", signal: AbortSignal.timeout(6500) });
      if (!response.ok) throw Error("manifest " + response.status);
      const manifest = await response.json();
      if (!validManifest(manifest, code)) throw Error("invalid manifest");
      if (pending !== code || edition !== code) return;
      active = manifest;
      lastScene = -1;
      render();
    } catch (error) {
      if (pending === code) {
        lockedUntil = Date.now() + 15000;
        if (window.rdiGeoActive) stop();
      }
    } finally {
      if (pending === code) pending = "";
    }
  }
  function accept(data) {
    const np = data?.now_playing;
    if (!np || data?.is_online === false || data?.live?.is_live === true) return;
    const code = editionFrom(np);
    const now = Date.now();
    if (!code) {
      if (window.rdiGeoActive && now - lastMatched > 6000) stop();
      return;
    }
    lastMatched = now;
    const started = Number(np.played_at) || 0;
    const d = Number(np.duration) || 0;
    if (code !== edition) {
      if (window.rdiGeoActive) stop();
      edition = code;
      active = null;
      lastScene = -1;
    }
    playedAt = started > 1000000000 ? started : 0;
    startByElapsed = now / 1000 - (Number(np.elapsed) || 0);
    songDuration = d;
    if (!active && now > lockedUntil) load(code);
    if (active) render();
  }
  function second() {
    if (playedAt > 1000000000) {
      const seconds = Date.now() / 1000 - playedAt;
      if (seconds >= -2 && seconds < 1200) return Math.max(0, seconds);
    }
    return Math.max(0, Date.now() / 1000 - startByElapsed);
  }
  function render() {
    if (!active || !edition || Date.now() - lastMatched > 9000) {
      if (window.rdiGeoActive && Date.now() - lastMatched > 9000) stop();
      return;
    }
    const now = second();
    const max = Math.min(Number(active.audio_duration_seconds), songDuration > 0 ? songDuration : Infinity);
    if (now > max + 1) { stop(); return; }
    const scenes = active.timeline;
    let idx = scenes.findIndex(s => now >= s.start_seconds && now < s.end_seconds);
    if (idx < 0) idx = now < scenes[0].start_seconds ? 0 : scenes.length - 1;
    const scene = scenes[idx];
    if (idx !== lastScene) {
      lastScene = idx;
      open();
      const story = scene.kind === "story";
      layer.classList.toggle("geo-screen-story", story);
      if (story) {
        country.textContent = clean(scene.country).toLocaleUpperCase("it");
        title.textContent = clean(scene.title);
        summary.textContent = clean(scene.summary).slice(0, 480);
        const count = scenes.filter(s => s.kind === "story").length;
        const number = scenes.slice(0, idx + 1).filter(s => s.kind === "story").length;
        footStep.textContent = "NOTIZIA " + number + " / " + count;
        date.textContent = scene.published_date || "";
      } else {
        country.textContent = scene.kind === "outro" ? "ARRIVEDERCI" : "DAL MONDO";
        title.textContent = scene.kind === "outro" ? "Geopolitica, ogni ora" : "RDI GEOPOLITICA";
        summary.textContent = scene.kind === "intro"
          ? "Le principali notizie internazionali. Paese per Paese."
          : "I fatti, il contesto e gli approfondimenti su Radio Românii din Italia.";
        footStep.textContent = scene.kind === "jingle" ? "JINGLE ORIGINALE RDI" : "EDIZIONE ITALIANA";
        date.textContent = "";
      }
    }
    progress.style.width = Math.min(100, Math.max(0, 100 * now / Number(active.audio_duration_seconds))) + "%";
  }
  async function poll() {
    try {
      const response = await fetch(url + "?geo=" + Date.now(), {
        cache: "no-store", signal: AbortSignal.timeout(5000),
      });
      if (response.ok) accept(await response.json());
    } catch (_) {
      // Retain the known track for a short outage, never show it indefinitely.
    } finally {
      setTimeout(poll, 2500);
    }
  }
  window.addEventListener("rdi:nowplaying", event => accept(event.detail));
  setInterval(render, 180);
  poll();
})();
