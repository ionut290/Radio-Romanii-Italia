/* RDI STORIA TV: deterministic presentation rules; no network or browser globals. */
export function validStoriaDay(raw, day) {
  if (!raw || raw.date !== day || !Array.isArray(raw.events)) return [];
  const seen = new Set();
  const entries = [];
  for (const x of raw.events) {
    if (!x || !Number.isInteger(x.year) || x.year < 1 || x.year > Number(day.slice(0, 4))) continue;
    const title = String(x.title_ro || x.title_it || "").trim();
    const summary = String(x.text_ro || x.text_it || "").trim();
    if (title.length < 12 || summary.length < 35) continue;
    const key = x.year + ":" + title.toLocaleLowerCase("ro");
    if (seen.has(key)) continue;
    seen.add(key);
    const image = String(x.image || "");
    // Restrict external images to Wikimedia Commons to avoid arbitrary URL injection.
    const trustedImage = /^https:\/\/(?:upload|thumb)\.wikimedia\.org\/wikipedia\/commons\//.test(image) ||
      /^https:\/\/commons\.wikimedia\.org\/wiki\/Special:FilePath\//.test(image) ? image : "";
    entries.push({
      year: x.year, title: title.slice(0, 155), summary: summary.slice(0, 490),
      image: trustedImage,
      credit: String(x.image_credit || "Wikimedia Commons").slice(0, 110),
      license: String(x.image_license || "").slice(0, 45),
      source: String(x.source || "").slice(0, 300),
      language: x.title_ro && x.text_ro ? "ro" : (x.original_language === "en" ? "en" : "it")
    });
  }
  return entries.slice(0, 8);
}

export function storyDue({cards, lastShownAt, now, preview = false}) {
  if (preview) return true;
  return cards >= 8 && (!lastShownAt || now - lastShownAt >= 12 * 60 * 1000);
}
