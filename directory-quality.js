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
function downloadMissing(records, field = "") {
  const columns = ["id", "name", "category", "region", "province", "city", "address",
    "phone", "whatsapp", "email", "website", "hours", "foto_presente",
    "dati_mancanti", "sourceUrl", "detailsSourceUrl"];
  const filtered = records.map(b => ({...b, foto_presente: photos(b) ? "si" : "no",
    dati_mancanti: missingForBusiness(b).join(", ")})).filter(b => b.dati_mancanti && (!field || !value(b[field]) || (field === "photos" && !photos(b))));
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
  const filterInput = panel.querySelector("#rdi-quality-filter");
  let current = [];
  exportBtn.addEventListener("click", () => { if (canView() && current.length) downloadMissing(current, filterInput?.value || ""); });
  filterInput?.addEventListener("change", () => renderRows());
  function renderRows(){
    table.replaceChildren();
    const field=filterInput?.value||"";
    const matches=current.filter(b => field ? (field==="photos"?!photos(b):!value(b[field])):missingForBusiness(b).length);
    table.append(document.createElement("strong"));
    table.firstChild.textContent="Schede da completare: "+matches.length+" (prime 20 visualizzate)";
    for (const b of matches.slice(0,20)) {
      const line=document.createElement("p");line.className="muted";line.style.margin="5px 0";
      line.textContent=[b.name,b.city,"Mancano: "+missingForBusiness(b).join(", ")].filter(Boolean).join(" · ");
      const link=document.createElement("a");link.textContent=" Cerca fonti";
      link.href="https://www.google.com/search?q="+encodeURIComponent([b.name,b.address,b.city,"contatti"].filter(Boolean).join(" "));
      link.target="_blank";link.rel="noopener noreferrer";line.append(link);table.append(line);
    }
    exportBtn.disabled=!matches.length;
  }
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
    renderRows();
  }};
}
