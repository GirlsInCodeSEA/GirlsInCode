(() => {
  const container = document.getElementById('chapter-map');
  if (!container) return;
  const status = document.getElementById('chapter-map-status');
  const empty = document.getElementById('chapter-empty-message');
  const warning = document.getElementById('map-load-warning');
  const list = document.getElementById('chapter-list');
  const reset = document.getElementById('reset-chapter-map');
  if (!window.L) {
    warning.textContent = 'The interactive map could not load. Please refresh to try again.';
    warning.hidden = false;
    return;
  }

  // This is a regional starting view, not a chapter location.
  const initialCenter = [7, 110];
  const map = L.map(container, {scrollWheelZoom: false, minZoom: 2}).setView(initialCenter, 4);
  const tiles = L.tileLayer(container.dataset.tilesUrl, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  let tileFailed = false;
  tiles.on('loading', () => { tileFailed = false; });
  tiles.on('tileerror', () => {
    tileFailed = true;
    warning.textContent = 'Some map tiles could not load. You can still use the chapter directory.';
    warning.hidden = false;
  });
  tiles.on('load', () => { if (!tileFailed) warning.hidden = true; });

  const markers = L.featureGroup().addTo(map);
  const showAll = () => {
    if (markers.getLayers().length) map.fitBounds(markers.getBounds(), {padding: [45, 45], maxZoom: 12});
    else map.setView(initialCenter, 4);
  };
  reset.disabled = false;
  reset.addEventListener('click', showAll);
  const pin = L.divIcon({
    className: 'chapter-marker',
    html: '<span class="chapter-pin" aria-hidden="true"></span>',
    iconSize: [30, 38], iconAnchor: [15, 36], popupAnchor: [0, -34],
  });
  const validChapter = chapter => chapter &&
    typeof chapter.name === 'string' && chapter.name.trim() &&
    typeof chapter.location === 'string' && chapter.location.trim() &&
    Number.isFinite(chapter.latitude) && Math.abs(chapter.latitude) <= 90 &&
    Number.isFinite(chapter.longitude) && Math.abs(chapter.longitude) <= 180;

  fetch(container.dataset.locationsUrl)
    .then(response => {
      if (!response.ok) throw new Error('Chapter data unavailable');
      return response.json();
    })
    .then(chapters => {
      if (!Array.isArray(chapters) || !chapters.every(validChapter)) throw new Error('Invalid chapter data');
      if (!chapters.length) return;
      empty.hidden = true;
      status.textContent = `${chapters.length} ${chapters.length === 1 ? 'chapter' : 'chapters'} on the map.`;
      chapters.forEach(chapter => {
        const coordinates = [chapter.latitude, chapter.longitude];
        const popup = document.createElement('div');
        const heading = document.createElement('strong');
        heading.textContent = chapter.name;
        const location = document.createElement('p');
        location.textContent = chapter.location;
        popup.append(heading, location);
        if (typeof chapter.description === 'string' && chapter.description.trim()) {
          const description = document.createElement('p');
          description.textContent = chapter.description;
          popup.append(description);
        }
        const marker = L.marker(coordinates, {icon: pin, title: chapter.name, alt: chapter.name})
          .bindPopup(popup).addTo(markers);
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        const name = document.createElement('strong');
        name.textContent = chapter.name;
        const detail = document.createElement('span');
        detail.textContent = chapter.location;
        button.append(name, detail);
        button.addEventListener('click', () => {
          map.setView(coordinates, 12);
          marker.openPopup();
          marker.getElement()?.focus({preventScroll: true});
        });
        item.append(button);
        list.append(item);
      });
      showAll();
    })
    .catch(() => {
      status.textContent = 'Chapter locations are temporarily unavailable.';
      empty.textContent = 'Please refresh the page to try again.';
    });
})();
