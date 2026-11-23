'use strict';

(() => {
  const view = document.querySelector('#view-meteo');
  if (!view) return;
  const panel = document.createElement('div');
  panel.className = 'hub-main hub2-meteo';
  panel.innerHTML = '<p class="muted" role="status"></p><div class="meteo-metrics"></div>' +
    '<section class="card panel"><h2>Historie měření</h2><label for="meteo-live-range">Období</label>' +
    '<select id="meteo-live-range"><option value="1h">1 hodina</option><option value="6h">6 hodin</option>' +
    '<option value="24h" selected>24 hodin</option><option value="7d">7 dní</option><option value="30d">30 dní</option></select>' +
    '<p class="muted" role="status"></p><div class="history-scroll"><table><thead><tr><th>Čas</th><th>Teplota</th><th>Vlhkost</th><th>Tlak</th></tr></thead><tbody></tbody></table></div></section>';
  view.append(panel);
  const [currentStatus, historyStatus] = panel.querySelectorAll('[role=status]');
  const range = panel.querySelector('select');
  const tbody = panel.querySelector('tbody');
  const fields = [['temp','Teplota','°C'],['hum','Vlhkost','%'],['pres','Tlak','hPa'],
    ['soc','Baterie','%'],['lux','Osvětlení','lx'],['uv','UV index','']];
  const fmt = (value, unit) => Number.isFinite(value)
    ? [value.toLocaleString('cs', {maximumFractionDigits: 1}), unit].filter(Boolean).join(' ') : '—';
  const cards = fields.map(([key, title, unit]) => {
    const card = document.createElement('article');
    card.className = 'card meteo-stat';
    const heading = document.createElement('h2');
    heading.textContent = title;
    const value = document.createElement('p');
    value.className = 'stat-value';
    value.textContent = '—';
    card.append(heading, value);
    panel.querySelector('.meteo-metrics').append(card);
    return {key, unit, value};
  });
  async function read(path) {
    const reply = await fetch('/api/dashboard/meteo/' + path, {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    if (!reply.ok) throw Error('Meteo API');
    return reply.json();
  }
  let pending = false;
  async function current() {
    if (view.hidden || document.hidden || pending) return;
    pending = true;
    try {
      const data = await read('current');
      cards.forEach(({key, unit, value}) => {value.textContent = fmt(data[key]?.value, unit);});
      const stamp = Date.parse(data.temp?.time);
      currentStatus.textContent = Number.isFinite(stamp)
        ? (Date.now() - stamp > 30 * 60000 ? 'Starší měření · ' : 'Poslední měření · ') + new Date(stamp).toLocaleString('cs')
        : 'Aktuální měření není dostupné.';
    } catch {
      cards.forEach(({value}) => {value.textContent = '—';});
      currentStatus.textContent = 'Měření se nepodařilo načíst.';
    } finally { pending = false; }
  }
  let generation = 0;
  async function history() {
    if (view.hidden || document.hidden) return;
    const turn = ++generation;
    historyStatus.textContent = 'Načítám historii…';
    tbody.replaceChildren();
    try {
      const data = await read('history?range=' + range.value);
      if (turn !== generation) return;
      const rows = new Map();
      for (const [key,,unit] of fields.slice(0,3)) {
        for (const entry of data[key] || []) {
          const at = Date.parse(entry.time);
          if (!Number.isFinite(at)) continue;
          const row = rows.get(at) || {};
          row[key] = fmt(entry.value, unit);
          rows.set(at, row);
        }
      }
      for (const [at, row] of [...rows].sort(([a],[b]) => b-a)) {
        const tr = tbody.insertRow();
        for (const value of [new Date(at).toLocaleString('cs'), row.temp, row.hum, row.pres]) {
          tr.insertCell().textContent = value || '—';
        }
      }
      historyStatus.textContent = rows.size ? 'Průměry podle zvoleného období' : 'V tomto období nejsou měření.';
    } catch {
      if (turn === generation) historyStatus.textContent = 'Historii se nepodařilo načíst.';
    }
  }
  let loaded = false;
  function visible() {
    if (view.hidden || document.hidden) { loaded = false; return; }
    current();
    if (!loaded) { loaded = true; history(); }
  }
  range.onchange = history;
  new MutationObserver(visible).observe(view, {attributes: true, attributeFilter: ['hidden']});
  document.addEventListener('visibilitychange', visible);
  setInterval(current, 15000);
  visible();
})();
