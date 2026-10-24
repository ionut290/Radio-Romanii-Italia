# RDI public directory

`directory-public.json` contains factual names, addresses, contacts and locations
retrieved from the cited public pages on 24 October 2026. Each listing retains its
source URL and is labelled as public-source information requiring confirmation.
The number of imported records is not the size of the source's complete catalog.
No ratings, reviews, photographs or editorial descriptions are copied.

RDI's approved Firestore listings are merged at runtime and take precedence over
public listings with a matching name, street address and town. Public imports do
not create Firestore accounts, submissions, ads, or approval records.

Town-level fallback coordinates in `directory-cities.json` come from
[napolux/italia](https://github.com/napolux/italia), whose documentation identifies
GeoNames and other sources and a municipal data reference date of 23 April 2016.
[GeoNames](https://www.geonames.org/) data is available under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). These are approximate
town positions, never exact premises. Newer or unmatched towns remain unlocated.
Business-specific coordinates are attributed to each listing's source.

Map software: Leaflet 1.9.4 (BSD-2-Clause) and Leaflet.markercluster 1.5.3 (MIT),
with licenses retained alongside the vendored code. Basemap: OpenStreetMap, with
visible contributor attribution. No paid map keys or tracking libraries are used.

Validation: `node --test tests/directory-map.test.mjs`.
