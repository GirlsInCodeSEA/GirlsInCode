# GIC chapter locations

`chapters.json` is intentionally an empty array until real chapter locations are supplied. No sample pins are shown on the public site. The map opens on Southeast Asia as a regional view; this does not identify a chapter.

To add a chapter, insert an object with:

- `name`: chapter or school name (text)
- `location`: city and country displayed in the directory (text)
- `latitude`: latitude in decimal degrees (number between -90 and 90)
- `longitude`: longitude in decimal degrees (number between -180 and 180)
- `description`: optional short introduction (text)

The map adds one pin and one directory entry for each object, fits the view to the supplied locations, and shows the name and description when a pin is selected. Names and descriptions are rendered as text, not HTML. Keep this file valid JSON with no comments or trailing commas.

Map behaviour lives in `static/chapters.js`; page copy lives in `templates/other_initiatives.html`. Leaflet 1.9.4 is served from `static/vendor/leaflet` with its licence. Basemap tiles are requested from OpenStreetMap in the browser, with visible attribution and standard browser caching. The tile URL is declared on the map element's `data-tiles-url` attribute; update attribution in the script if changing provider.
