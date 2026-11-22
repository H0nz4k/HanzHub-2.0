(() => {
  'use strict';

  function element(tag, text) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    return node;
  }

  async function read(path, message) {
    const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(16000)})
      .catch(() => { throw new Error(message); });
    if (!response.ok) throw new Error(message);
    return response.json();
  }

  function panel(view) {
    const section = document.querySelector('#view-' + view);
    const card = element('article');
    card.className = 'card panel hub2-live';
    const notice = element('p');
    notice.className = 'muted';
    notice.setAttribute('role', 'status');
    card.append(notice);
    section.append(card);
    return {section, card, notice};
  }

  const calendar = panel('calendar');
  const iot = panel('iot');
  const deviceList = element('ul');
  const refresh = element('button', 'Obnovit stavy');
  refresh.className = 'button';
  refresh.type = 'button';
  iot.card.prepend(refresh);
  iot.card.append(deviceList);

  let calendarLoading = false;
  let grid;
  async function loadCalendar() {
    if (calendarLoading) return;
    calendarLoading = true;
    calendar.notice.textContent = 'Ověřuji spojení s Google Kalendářem…';
    try {
      const status = await read('/api/calendar/status', 'Služba Kalendář není dostupná.');
      if (!status.connected) {
        grid?.root.remove();
        grid = undefined;
        calendar.notice.textContent = status.configured
          ? 'Google Kalendář není přihlášený.'
          : 'Google Kalendář není nastavený. Chybí OAuth klient.';
        return;
      }

      if (!grid) {
        const root = element('div');
        calendar.card.append(root);
        grid = new HanzCalendarGrid(root, path => read(path, 'Události z Google se nepodařilo načíst.'));
      }
      calendar.notice.textContent = 'Google Kalendář';
      await grid.load();
    } catch (error) {
      grid?.root.remove();
      grid = undefined;
      calendar.notice.textContent = error.message;
    } finally {
      calendarLoading = false;
    }
  }

  function describe(state) {
    if (state.paused) return 'Pozastaveno';
    if (state.online !== true) return 'Nedostupné';
    const values = ['Dostupné'];
    if (typeof state.power === 'boolean') values.push(state.power ? 'Zapnuto' : 'Vypnuto');
    if (Number.isFinite(state.current_temp_c)) values.push(state.current_temp_c + ' °C');
    if (Number.isFinite(state.target_temp_c)) values.push('Cíl ' + state.target_temp_c + ' °C');
    return values.join(' · ');
  }

  async function loadIot(force = false) {
    if (refresh.disabled) return;
    refresh.disabled = true;
    iot.notice.textContent = 'Načítám stavy zařízení…';
    try {
      const {devices} = await read('/api/iot/devices', 'Registr IoT není dostupný.');
      const rows = await Promise.all(devices.map(async device => {
        const row = element('li');
        row.append(element('strong', [device.name, device.room].filter(Boolean).join(' · ')));
        const query = force ? '?fresh=1' : '';
        try {
          const {state} = await read('/api/iot/devices/' + encodeURIComponent(device.id) +
            '/state' + query, 'Stav se nepodařilo načíst.');
          row.append(element('p', describe(state)));
          if (state.checked_at) {
            const checked = new Date(state.checked_at);
            if (Number.isFinite(checked.getTime())) row.append(element('small', 'Ověřeno ' +
              checked.toLocaleTimeString('cs-CZ')));
          }
        } catch (error) {
          row.append(element('p', error.message));
        }
        return row;
      }));
      deviceList.replaceChildren(...rows);
      iot.notice.textContent = devices.length ? 'Registrovaná zařízení' : 'Žádné registrované zařízení.';
    } catch (error) {
      deviceList.replaceChildren();
      iot.notice.textContent = error.message;
    } finally {
      refresh.disabled = false;
    }
  }

  function loadVisible() {
    if (document.hidden) return;
    if (!calendar.section.hidden) loadCalendar();
    if (!iot.section.hidden) loadIot();
  }

  refresh.onclick = () => loadIot(true);
  window.addEventListener('hashchange', loadVisible);
  document.addEventListener('visibilitychange', loadVisible);
  setInterval(() => {
    if (!document.hidden && !iot.section.hidden) loadIot();
  }, 30000);
  loadVisible();
})();
