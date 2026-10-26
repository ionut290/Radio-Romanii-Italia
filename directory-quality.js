// Admin-only, read-only coverage dashboard for the RDI business directory.
const PRESENT_FIELDS = [
  ["phone", "Telefono"],
  ["whatsapp", "WhatsApp"],
  ["email", "Email"],
  ["photos", "Fotografie"],
  ["website", "Sito web"],
  ["hours", "Orari"]
];
function value(v) { return typeof v === "string" ? v.trim() : ""; }
function photos(b) { return Array.isArray(b.imageUrls) && b.imageUrls.some(v => /^https:\/\//i.test(value(v))); }
export function missingForBusiness(b) {
  return PRESENT_FIELDS.filter(([field]) => field === "photos" ? !photos(b) :
    !value(b[field])).map(([, label]) => label);
}
function quoted(s) { return '"' + String(s ?? "").replaceAll('"', '""') + '"'; }
function downloadMissing(records) {
  const columns = ["id", "name", "category", "region", "province", "city", "address",
    "phone", "whatsapp", "email", "website", "hours", "foto_presente",
    "dati_mancanti", "sourceUrl", "detailsSourceUrl"];
  const filtered = records.map(b => ({...b, foto_presente: photos(b) ? "si" : "no",
    dati_mancanti: missingForBusiness(b).join(", ")})).filter(b => b.dati_mancanti);
  const text = "\uFEFF" + columns.join(";") + "\r\n" +
    filtered.map(b => columns.map(k => quoted(b[k])).join(";")).join("\r\n");
  const blob = new Blob([text], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "RDI-schede-da-completare-" + new Date().toISOString().slice(0, 10) + ".csv";
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}
export function createDirectoryQualityPanel({canView}) {
  const panel = document.getElementById("rdi-quality-admin");
  if (!panel) return {render() {}};
  const summary = panel.querySelector("#rdi-quality-summary");
  const table = panel.querySelector("#rdi-quality-missing");
  const exportBtn = panel.querySelector("#rdi-quality-export");
  let current = [];
  exportBtn.addEventListener("click", () => { if (canView() && current.length) downloadMissing(current); });
  return {render(records) {
    panel.hidden = !canView();
    if (!canView()) { current = []; return; }
    current = Array.isArray(records) ? records : [];
    const total = current.length;
    const counts = PRESENT_FIELDS.map(([f, title]) =>
      [title, current.filter(b => f === "photos" ? !photos(b) : !value(b[f])).length]);
    const cards = counts.map(([title, count]) => title + ": " + count).join(" · ");
    summary.textContent = total + " schede visibili nel catalogo · Dati assenti — " + cards +
      ". Un numero telefonico non implica che l'attività utilizzi WhatsApp.";
    table.replaceChildren();
    const head = document.createElement("strong");
    head.textContent = "Prime 15 schede da completare";
    table.append(head);
    for (const b of current.filter(b => missingForBusiness(b).length).slice(0, 15)) {
      const p = document.createElement("p"); p.className = "muted"; p.style.margin = "4px 0";
      p.textContent = [b.name, b.city, "Mancano: " + missingForBusiness(b).join(", ")].filter(Boolean).join(" · ");
      table.append(p);
    }
    exportBtn.disabled = !current.some(b => missingForBusiness(b).length);
  }};
}
