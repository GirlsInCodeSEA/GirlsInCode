// Competition dashboard: countdown, day timeline, local times, copy/download of inputs.
(() => {
  const body = document.body;
  const start = Date.parse(body.dataset.start);
  const end = Date.parse(body.dataset.end);
  const phase = body.dataset.phase;
  // Trust the server's clock over the visitor's: measure the offset once.
  const skew = Date.parse(body.dataset.now) - Date.now() || 0;
  const now = () => Date.now() + skew;
  const LEAD = 0.16;            // share of the track drawn as the "final week" lead-in
  const WEEK = 7 * 24 * 3600e3;
  const pad = n => String(n).padStart(2, '0');

  const units = {};
  document.querySelectorAll('[data-unit]').forEach(el => { units[el.dataset.unit] = el; });
  const clock = document.querySelector('[data-clock]');
  const marker = document.querySelector('[data-tl-marker]');
  const fill = document.querySelector('[data-tl-fill]');
  let reloading = false;

  function tick() {
    const t = now();
    const target = phase === 'before' ? start : end;
    const left = Math.max(0, target - t);
    if (phase !== 'ended' && left === 0 && !reloading) {
      reloading = true;
      setTimeout(() => location.reload(), 1500);  // the server decides the new phase
    }
    const s = Math.floor(left / 1000);
    const parts = { d: Math.floor(s / 86400), h: Math.floor(s / 3600) % 24, m: Math.floor(s / 60) % 60, s: s % 60 };
    Object.entries(parts).forEach(([key, value]) => { if (units[key]) units[key].textContent = pad(value); });
    if (clock && phase !== 'ended') {
      clock.hidden = false;
      const hms = `${pad(parts.h)}:${pad(parts.m)}:${pad(parts.s)}`;
      clock.textContent = (phase === 'before' ? 'starts in ' : 'ends in ') + (parts.d ? `${parts.d}d ` : '') + hms;
    }
    let pos = 1, dayProgress = 1;
    if (phase === 'before') { pos = LEAD * (1 - Math.min(1, (start - t) / WEEK)); dayProgress = 0; }
    else if (phase === 'live') { dayProgress = Math.min(1, (t - start) / (end - start)); pos = LEAD + (1 - LEAD) * dayProgress; }
    if (marker) marker.style.setProperty('--pos', pos);
    if (fill) fill.style.setProperty('--progress', dayProgress);
  }
  if (!Number.isNaN(start) && !Number.isNaN(end)) { tick(); setInterval(tick, 1000); }

  document.querySelectorAll('[data-local-time]').forEach(el => {
    const date = new Date(el.getAttribute('datetime'));
    if (!Number.isNaN(date.getTime())) {
      el.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      el.title = date.toLocaleString();
    }
  });

  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const text = document.querySelector(button.dataset.copy).textContent;
      try { await navigator.clipboard.writeText(text); button.textContent = 'copied'; }
      catch { button.textContent = 'select & copy'; }
      setTimeout(() => { button.textContent = 'copy'; }, 1800);
    });
  });
  document.querySelectorAll('[data-download]').forEach(button => {
    button.addEventListener('click', () => {
      const text = document.querySelector(button.dataset.download).textContent;
      const link = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([text], { type: 'text/plain' })), download: button.dataset.filename,
      });
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    });
  });
})();
