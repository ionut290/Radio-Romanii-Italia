# RDI news image library

`data/news-image-library.json` is the catalog for editorial covers used when a news source has no usable photo. The collection contains 110 distinct photorealistic context images across 11 themes: community, institutions, finance, health, education, travel, workers, environment, technology, sport, and justice. Of these, 102 are reusable; eight are reserved for the specific stories they illustrate.

Eight are marked `reusable: false` because they were created for a specific article; they remain in the catalog and their URL assignments are preserved in `data/news-cover-assignments.json`, but the feed rotator must not use them for another story.

## Assignment rules

1. Keep a publisher's image when it is available.
2. Keep a URL's saved cover assignment while that article remains in the feed.
3. For an item with a generic or missing image, choose a reusable cover from the closest matching theme that has not already been used in the current feed.
4. If no unused cover fits that theme, retain the per-article SVG fallback. This prevents a photo from being repeated across unrelated items.
5. Show the IA context-image credit on generated covers. These images illustrate a subject and do not document the reported event.

To add a cover, place an optimized 16:9 or 3:2 JPEG under `editorial-images/news-covers/` and add one entry with its theme, description, and credit to `data/news-image-library.json`. Keep paths unique. Mark an image `reusable: false` when it depicts a one-off event or otherwise belongs to a single story.
