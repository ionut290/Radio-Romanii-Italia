// OpenStreetMap candidate import — source data is not published without review.\nimport { readFile, writeFile } from "node:fs/promises";

const endpoint = "https://overpass-api.de/api/interpreter";
const source = JSON.parse(await readFile("data/directory-public.json", "utf8"));
const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const query = `[out:json][timeout:90];
area["ISO3166-1"="IT"][admin_level=2]->.italy;
(
  nwr["name"~"roman|rumen|român",i](area.italy);
);
out center tags;`;

const response = await fetch(endpoint, {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded", "user-agent": "RDI-Ghid-Candidate-Importer/1.0" },
  body: new URLSearchParams({ data: query }),
  signal: AbortSignal.timeout(45000)
});
if (!response.ok) throw new Error(`Overpass returned ${response.status}`);
const payload = await response.json();

const categoryFor = tags => {
  if (tags.amenity === "restaurant" || tags.amenity === "fast_food" || tags.amenity === "cafe") return "Restaurante românești";
  if (["supermarket", "convenience", "deli", "greengrocer"].includes(tags.shop)) return "Magazine românești";
  if (["hairdresser", "beauty"].includes(tags.shop)) return "Îngrijire și frumusețe";
  if (tags.shop === "car_repair" || tags.craft === "car_repair") return "Auto și mecanică";
  if (tags.amenity === "community_centre" || tags.office === "association") return "Asociații și comunitate";
  return "Alte servicii";
};
const addressFor = tags => [tags["addr:street"], tags["addr:housenumber"]].filter(Boolean).join(" ").trim();
const current = new Set(source.businesses.map(b => [normalize(b.name), normalize(b.city), normalize(b.address)].join("|")));
const candidates = (payload.elements || []).map(element => {
  const tags = element.tags || {};
  const city = tags["addr:city"] || tags["addr:place"] || "";
  const address = addressFor(tags);
  return {
    id: `osm-${element.type}-${element.id}`,
    name: tags.name || "",
    category: categoryFor(tags),
    region: "",
    province: "",
    city,
    address,
    phone: tags.phone || tags["contact:phone"] || "",
    whatsapp: tags["contact:whatsapp"] || "",
    website: tags.website || tags["contact:website"] || "",
    hours: tags.opening_hours || "",
    latitude: element.lat || element.center?.lat || null,
    longitude: element.lon || element.center?.lon || null,
    source: "OpenStreetMap / Overpass",
    sourceUrl: `https://www.openstreetmap.org/${element.type}/${element.id}`,
    status: "candidate",
    note: "Candidată găsită în OpenStreetMap; nu este publicată în Ghid până la verificare."
  };
}).filter(b => b.name).filter(b => !current.has([normalize(b.name), normalize(b.city), normalize(b.address)].join("|")))
  .sort((a,b) => a.name.localeCompare(b.name, "ro"));

await writeFile("data/directory-osm-candidates.json", JSON.stringify({
  generatedAt: new Date().toISOString(),
  source: "OpenStreetMap / Overpass API",
  publicationRule: "Candidates only. Manual review is required before publication in the public directory.",
  count: candidates.length,
  candidates
}, null, 2) + "\n");
console.log(`Saved ${candidates.length} OpenStreetMap candidates.`);
