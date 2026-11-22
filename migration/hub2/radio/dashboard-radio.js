'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const station = $('radio-station');
  if (!station) return;
  const audio = $('radio-audio');
  const play = $('radio-play');
  const stop = $('radio-stop');
  const status = $('radio-status');
  const now = $('radio-now');
  const presetsPath = '/api/radio/presets';
  let stations = [];
  let generation = 0;
  let attempt = 0;
  let requested = false;
  let audible = false;
  let pendingTitle = false;
  const selected = () => stations.find(item => item.id === station.value);

  async function request(path, options) {
    const reply = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(6000), ...options});
    const data = await reply.json();
    if (!reply.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Požadavek se nepodařilo ověřit.');
    return data;
  }

  async function refreshTitle() {
    if (!audible || pendingTitle || document.hidden) return;
    const turn = generation;
    pendingTitle = true;
    let title = null;
    try {
      const params = new URLSearchParams({station: station.value, stream: attempt});
      ({title} = await request('/api/radio/title?' + params));
    } catch {}
    pendingTitle = false;
    if (turn === generation && audible) now.textContent = title || 'Název skladby není dostupný';
  }

  function clearTitle(text) {
    generation++;
    audible = false;
    now.textContent = text;
  }

  function reset() {
    requested = false;
    clearTitle('Přehrávání je zastavené');
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    stop.disabled = true;
    status.textContent = selected()?.name || '';
  }

  function connect() {
    const item = selected();
    const url = item?.urls[attempt];
    if (!url) {
      reset();
      now.textContent = 'Stream se nepodařilo přehrát';
      return;
    }
    clearTitle('Připojuji ke streamu…');
    status.textContent = item.name;
    audio.src = url;
    audio.play().catch(error => {
      if (error.name === 'NotAllowedError' && requested) now.textContent = 'Spusť přehrávání ovladačem zvuku';
    });
  }

  request('/api/radio/stations').then(config => {
    stations = config.stations || [];
    for (const item of stations) station.add(new Option(item.name, item.id));
    if (!stations.length) throw Error();
    let volume = null;
    try { volume = localStorage.getItem('hanzhub-radio-volume'); } catch {}
    audio.volume = volume !== null && Number.isFinite(Number(volume))
      ? Math.min(1, Math.max(0, Number(volume))) : (config.volume ?? 40) / 100;
    audio.addEventListener('volumechange', () => {
      try { localStorage.setItem('hanzhub-radio-volume', String(audio.volume)); } catch {}
    });
    play.disabled = station.disabled = false;
    reset();
  }).catch(() => { status.textContent = 'Stanice nejsou dostupné.'; });

  play.onclick = () => {
    requested = true;
    attempt = 0;
    stop.disabled = false;
    connect();
  };
  stop.onclick = reset;
  station.onchange = () => requested ? play.click() : reset();
  audio.addEventListener('error', () => { if (requested) { attempt++; connect(); } });
  audio.addEventListener('playing', () => {
    if (!requested) return;
    audible = true;
    now.textContent = 'Načítám název skladby…';
    refreshTitle();
  });
  audio.addEventListener('pause', () => { if (requested) clearTitle('Přehrávání je pozastavené'); });
  audio.addEventListener('waiting', () => { if (requested) clearTitle('Čekám na stream…'); });
  audio.addEventListener('ended', () => { if (requested) reset(); });
  setInterval(refreshTitle, 4000);
  document.addEventListener('visibilitychange', refreshTitle);

  const form = $('radio-preset-form');
  const name = $('radio-preset-name');
  const frequency = $('radio-preset-freq');
  const mode = $('radio-preset-mode');
  const message = $('radio-preset-status');
  let editing = null;
  function edit(row = null) {
    editing = row;
    form.hidden = false;
    name.value = row?.name || '';
    frequency.value = row ? String(row.carrier_freq_hz / 1e6) : '';
    mode.querySelector('option[data-original]')?.remove();
    const modulation = row?.modulation || 'wfm';
    if (![...mode.options].some(option => option.value === modulation)) {
      const option = new Option(modulation.toUpperCase(), modulation);
      option.dataset.original = '';
      mode.add(option);
    }
    mode.value = modulation;
    name.focus();
  }
  async function readPresets() {
    const data = await request(presetsPath);
    $('radio-presets').replaceChildren(...data.map(row => {
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.className = 'button';
      button.type = 'button';
      button.onclick = () => edit(row);
      const title = document.createElement('strong');
      title.textContent = row.name;
      const info = document.createElement('small');
      info.textContent = (row.carrier_freq_hz / 1e6).toLocaleString('cs', {maximumFractionDigits: 6}) +
        ' MHz · ' + row.modulation.toUpperCase();
      button.append(title, info);
      li.append(button);
      return li;
    }));
    return data;
  }
  $('radio-presets-jump').onclick = () => {
    $('radio-fm').scrollIntoView({block: 'start'});
    $('radio-fm').focus({preventScroll: true});
  };
  $('radio-preset-new').onclick = () => edit();
  $('radio-preset-cancel').onclick = () => {
    form.hidden = true;
    $('radio-preset-new').focus();
  };
  form.onsubmit = async event => {
    event.preventDefault();
    const submit = form.querySelector('[type=submit]');
    const previous = editing;
    const payload = {
      name: name.value.trim(), carrier_freq_hz: Math.round(frequency.valueAsNumber * 1e6),
      modulation: mode.value,
    };
    if (!previous) payload.band = mode.value === 'wfm' ? 'broadcast-fm' : 'unknown';
    submit.disabled = true;
    message.textContent = 'Ukládám…';
    try {
      const saved = await request(presetsPath + (previous ? '/' + previous.id : ''), {
        method: previous ? 'PATCH' : 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const rows = await readPresets();
      if (!rows.some(row => row.id === saved.id && row.name === payload.name &&
          row.carrier_freq_hz === payload.carrier_freq_hz && row.modulation === payload.modulation)) {
        throw Error('Uložení se nepodařilo ověřit v seznamu.');
      }
      form.hidden = true;
      message.textContent = 'Předvolba uložena.';
    } catch (error) {
      message.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  };
  readPresets().then(rows => { message.textContent = rows.length ? '' : 'Žádná uložená předvolba.'; })
    .catch(error => { message.textContent = error.message; });
})();
