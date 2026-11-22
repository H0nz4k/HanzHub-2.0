'use strict';

(async () => {
  const get = async path => {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  };
  const cards = [...document.querySelectorAll('[data-service]')];
  const stats = [...document.querySelectorAll('#view-dashboard > .stats-grid > .stat')];
  function setStat(index, value, detail) {
    const card = stats[index];
    card.querySelector('.stat-value').textContent = value;
    const bottom = card.querySelector('.stat-bottom');
    if (bottom) bottom.textContent = detail;
    card.querySelector('.meter, .segments, .sparkline')?.remove();
  }
  stats[1].querySelector('.stat-title').firstChild.textContent = 'Denní záloha';
  const henk = document.querySelector('.henk-card');
  henk.querySelectorAll('a').forEach(link => { link.href = '/ai-slave.html'; });
  henk.querySelector('.henk-copy .badge').className = 'badge neutral';
  henk.querySelector('.henk-copy .badge').textContent = 'HENK';
  henk.querySelector('.henk-copy .button.primary').firstChild.textContent = 'Otevřít Henka';
  henk.querySelector('.henk-copy .button:not(.primary)').remove();
  henk.querySelector('.henk-copy h3').textContent = 'Tvůj místní agent';
  henk.querySelector('.henk-copy p').textContent = 'Přehled komunikace a zadávání úkolů.';
  henk.querySelector('.henk-footer').hidden = true;
  const devicePanel = document.querySelector('.home-devices');
  const deviceFooter = devicePanel.querySelector('.device-foot');
  const iotUrl = document.querySelector('[data-service="iot"]').href;
  devicePanel.querySelector('.text-link').href = iotUrl;
  function showDevices(modules) {
    devicePanel.querySelectorAll('.device-summary, .device-empty').forEach(node => node.remove());
    if (!modules?.length) {
      const empty = document.createElement('p');
      empty.className = 'device-empty';
      empty.textContent = modules ? 'Žádné registrované zařízení.' : 'Registr IoT se nepodařilo načíst.';
      devicePanel.insertBefore(empty, deviceFooter);
      return;
    }
    for (const module of modules) {
      const link = document.createElement('a');
      link.href = iotUrl;
      link.className = 'device-summary';
      const name = document.createElement('strong');
      name.textContent = module.name;
      const state = document.createElement('small');
      state.textContent = [module.room, module.online === true
        ? 'Dostupné' : module.online === false ? 'Nedostupné' : 'Registrované'].filter(Boolean).join(' · ');
      link.append(name, state);
      devicePanel.insertBefore(link, deviceFooter);
    }
  }
  showDevices(null);
  const refresh = async () => {
    const [health, backup, iot] = await Promise.all([
      get('/api/health').catch(() => ({})),
      get('/api/backup/status').catch(() => ({})),
      get('/api/dashboard/devices').catch(() => ({})),
    ]);
    const info = service => health[service]?.ok === true
      ? 'Dostupné' : health[service]?.ok === false ? 'Nedostupné' : 'Stav neznámý';
    cards.forEach(card => {
      card.querySelector('[data-service-status]').textContent = info(card.dataset.service);
    });
    const up = cards.filter(card => health[card.dataset.service]?.ok).length;
    setStat(0, Object.keys(health).length ? up + ' / ' + cards.length : '—', 'Ověřené služby');
    const daily = backup.daily;
    const size = Number.isFinite(daily?.size_bytes) ? (daily.size_bytes / 2 ** 30).toFixed(1) + ' GiB' : '';
    setStat(1, daily?.state === 'ok' ? 'Ověřena' : daily?.state === 'failed' ? 'Chyba' : '—',
      [size, daily?.detail].filter(Boolean).join(' · '));
    setStat(2, info('iot'), '');
    setStat(3, info('meteo'), '');
    showDevices(iot.devices);
  };
  refresh();
  setInterval(refresh, 30000);

  const station = document.querySelector('#radio-station');
  const audio = document.querySelector('#radio-audio');
  const play = document.querySelector('#radio-play');
  const stop = document.querySelector('#radio-stop');
  const status = document.querySelector('#radio-status');
  const config = await get('/api/radio/stations').catch(() => ({stations: []}));
  for (const item of config.stations) station.add(new Option(item.name, item.id));
  if (!station.options.length) {
    status.textContent = 'Stanice nejsou dostupné.';
    return;
  }
  const storedVolume = storage.get('hanzhub-radio-volume');
  audio.volume = storedVolume !== null && Number.isFinite(Number(storedVolume))
    ? Math.min(1, Math.max(0, Number(storedVolume))) : (config.volume ?? 40) / 100;
  audio.addEventListener('volumechange', () => storage.set('hanzhub-radio-volume', String(audio.volume)));
  let requested = false;
  let attempt = 0;
  const selected = () => config.stations.find(item => item.id === station.value);
  function reset() {
    requested = false;
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    stop.disabled = true;
    status.textContent = selected().name + ' · připraveno';
  }
  function connect() {
    const item = selected();
    const url = item.urls[attempt];
    if (!url) {
      reset();
      status.textContent = item.name + ' · stream se nepodařilo přehrát';
      return;
    }
    status.textContent = item.name + ' · připojování';
    audio.src = url;
    audio.play().catch(error => {
      if (error.name === 'NotAllowedError' && requested) {
        status.textContent = item.name + ' · spusť přehrávání ovladačem zvuku';
      }
    });
  }
  play.onclick = () => {
    attempt = 0;
    requested = true;
    stop.disabled = false;
    connect();
  };
  audio.addEventListener('error', () => {
    if (requested) {
      attempt += 1;
      connect();
    }
  });
  audio.addEventListener('playing', () => { status.textContent = selected().name + ' · přehrává se'; });
  audio.addEventListener('pause', () => {
    if (requested) status.textContent = selected().name + ' · pozastaveno';
  });
  stop.onclick = reset;
  station.onchange = reset;
  station.disabled = play.disabled = false;
  reset();
})();
