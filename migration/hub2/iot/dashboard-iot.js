'use strict';

(() => {
  const view = document.querySelector('#view-iot');
  if (!view) return;
  const panel = document.createElement('div');
  panel.className = 'hub-main hub2-live dashboard-iot';
  panel.innerHTML = '<div class="feature-toolbar"><button class="button" type="button">Obnovit stav</button><p class="muted" role="status"></p></div><div class="dashboard-iot-grid"></div>';
  view.append(panel);
  const status = panel.querySelector('[role=status]');
  const grid = panel.querySelector('.dashboard-iot-grid');
  const refreshButton = panel.querySelector('button');
  const rows = new Map();
  let refreshing = false;
  let commandPending = false;
  let commandGeneration = 0;

  const format = (value, unit) => Number.isFinite(value)
    ? value.toLocaleString('cs', {maximumFractionDigits: 3}) + ' ' + unit : 'Údaj není dostupný';

  function node(tag, value, className = '') {
    const el = document.createElement(tag);
    el.className = className;
    el.textContent = value;
    return el;
  }

  async function api(path, body) {
    const write = body !== undefined;
    const reply = await fetch('/api/iot/devices' + path, {
      method: write ? 'POST' : 'GET', cache: 'no-store', redirect: 'error',
      headers: write ? {'Content-Type': 'application/json'} : {},
      body: write ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(write ? 40000 : 20000),
    });
    const data = await reply.json();
    if (!reply.ok) throw Error(data.code || 'unavailable');
    return data;
  }

  function showState(row, state) {
    row.state = state;
    row.at = Date.now();
    row.stateBadge.textContent = state?.paused ? 'Pozastaveno' : state?.online !== true ? 'Nedostupné'
      : state.power === true ? 'Zapnuto' : state.power === false ? 'Vypnuto' : 'Stav neznámý';
    row.stateBadge.className = 'badge ' + (state?.online ? 'success' : 'neutral');
    const checked = Date.parse(state?.checked_at);
    row.checked.textContent = Number.isFinite(checked)
      ? 'Ověřeno ' + new Date(checked).toLocaleTimeString('cs-CZ') : '';
    row.problem.textContent = state?.error_code === 'authentication_failed'
      ? 'Místní klíč zařízení nebyl ověřen.'
      : state?.paused ? 'Modul je v registru pozastavený.'
      : state?.online === true ? (state.faults || []).join(' · ') : 'Čerstvý stav zařízení se nepodařilo načíst.';
    for (const [field, output, unit] of row.values) output.textContent = format(state?.online ? state[field] : null, unit);
    updateControls(row);
  }

  function updateControls(row) {
    const fresh = row.state?.online === true && Date.now() - row.at < 30000 && !commandPending;
    for (const [field, button] of row.actions) {
      const value = row.state?.[field];
      button.disabled = !fresh || (field === 'power' && typeof value !== 'boolean')
        || (field === 'target_temp_c' && (row.state?.locked !== false || row.state?.faults?.length > 0))
        || (field === 'locked' && typeof value !== 'boolean');
      if (field === 'power') button.textContent = value === true ? 'Vypnout' : 'Zapnout';
      if (field === 'locked') button.textContent = value === true ? 'Odemknout panel' : 'Zamknout panel';
    }
  }

  async function send(row, field, value, description) {
    if (commandPending || row.actions.get(field).disabled || !confirm(row.device.name + ' · ' + description + '?')) return;
    commandPending = true;
    commandGeneration++;
    rows.forEach(updateControls);
    status.textContent = 'Ověřuji výsledek…';
    try {
      const data = await api('/' + row.device.id + '/command', {control: field, value});
      const actual = data.state?.[field];
      const confirmed = field === 'timer_minutes' && value > 0
        ? Number.isInteger(actual) && actual <= value && actual >= value - 1 : actual === value;
      if (data.ok !== true || data.state?.online !== true || !confirmed) throw Error('unconfirmed');
      showState(row, data.state);
      status.textContent = row.device.name + ' · Výsledný stav potvrzen zařízením.';
    } catch {
      showState(row, null);
      status.textContent = 'Výsledek se nepodařilo potvrdit. Před dalším pokusem obnov stav zařízení.';
    } finally {
      commandPending = false;
      rows.forEach(updateControls);
    }
  }

  function card(device) {
    const article = node('article', '', 'card panel');
    const head = node('div', '', 'cardhead');
    const stateBadge = node('span', 'Načítám stav…', 'badge neutral');
    head.append(node('h2', device.name), stateBadge);
    const problem = node('p', '', 'muted');
    const checked = node('p', '', 'muted');
    const actions = node('div', '', 'dashboard-iot-actions');
    const list = node('dl', '', 'dashboard-iot-values');
    const row = {device, article, stateBadge, problem, checked, state: null, at: 0, actions: new Map(), values: []};
    article.append(head, node('p', device.room || device.capabilities?.name || '', 'muted'), problem, checked, list, actions);
    function metric(field, name, unit) {
      const output = node('dd', 'Údaj není dostupný');
      list.append(node('dt', name), output);
      row.values.push([field, output, unit]);
    }
    function action(field, label, run, parent = actions) {
      const button = node('button', label, 'button');
      button.type = 'button';
      button.disabled = true;
      button.onclick = run;
      row.actions.set(field, button);
      parent.append(button);
    }
    const controls = device.capabilities?.controls || [];
    if (controls.includes('power')) action('power', 'Zapnout', () => {
      const desired = !row.state.power;
      send(row, 'power', desired, desired ? 'zapnout zařízení' : 'vypnout zařízení');
    });
    if (device.capabilities?.kind === 'heater') {
      metric('current_temp_c', 'Aktuální teplota', '°C');
      metric('target_temp_c', 'Cílová teplota', '°C');
      metric('timer_minutes', 'Zbývající čas', 'min');
      numeric('target_temp_c', 'Cílová teplota (°C)', 37, 1, 'nastavit teplotu na');
      numeric('timer_minutes', 'Časovač (hodiny)', 24, 60, 'nastavit časovač na');
      if (controls.includes('locked')) action('locked', 'Zamknout panel', () => {
        const desired = !row.state.locked;
        send(row, 'locked', desired, desired ? 'zamknout panel' : 'odemknout panel');
      });
    }
    metric('power_w', 'Příkon', 'W');
    if (device.capabilities?.energy) {
      metric('energy_today_kwh', 'Spotřeba dnes', 'kWh');
      metric('energy_month_kwh', 'Spotřeba tento měsíc', 'kWh');
    }
    function numeric(field, labelText, max, factor, description) {
      if (!controls.includes(field)) return;
      const label = node('label', labelText);
      const input = document.createElement('input');
      input.type = 'number';
      input.min = '0';
      input.max = String(max);
      input.step = '1';
      input.required = true;
      label.append(input);
      const group = node('div', '', 'dashboard-iot-control');
      group.append(label);
      action(field, 'Nastavit', () => {
        if (input.reportValidity()) send(row, field, input.valueAsNumber * factor,
          description + ' ' + input.value + (factor === 60 ? ' h' : ' °C'));
      }, group);
      actions.append(group);
    }
    return row;
  }

  async function refresh(manual = false) {
    if (view.hidden || refreshing || commandPending) return;
    refreshing = true;
    const generation = commandGeneration;
    refreshButton.disabled = true;
    try {
      const data = await api('');
      for (const [id, row] of rows) {
        if (!data.devices.some(device => device.id === id)) {
          row.article.remove();
          rows.delete(id);
        }
      }
      for (const device of data.devices) {
        const old = rows.get(device.id);
        if (old && JSON.stringify(old.device) === JSON.stringify(device)) continue;
        const row = card(device);
        if (old) old.article.replaceWith(row.article);
        else grid.append(row.article);
        rows.set(device.id, row);
      }
      await Promise.all([...rows].map(async ([id, row]) => {
        try {
          const data = await api('/' + id + '/state' + (manual ? '?fresh=1' : ''));
          if (!commandPending && generation === commandGeneration) showState(row, data.state);
        } catch {
          if (!commandPending && generation === commandGeneration) showState(row, null);
        }
      }));
      if (manual || !status.textContent || status.dataset.registryError) {
        status.textContent = rows.size ? '' : 'V registru nejsou žádné moduly.';
        delete status.dataset.registryError;
      }
    } catch {
      if (generation !== commandGeneration) return;
      rows.forEach(row => showState(row, null));
      status.textContent = 'Registr modulů není dostupný.';
      status.dataset.registryError = '1';
    } finally {
      refreshing = false;
      refreshButton.disabled = false;
    }
  }
  refreshButton.onclick = () => refresh(true);
  new MutationObserver(() => refresh()).observe(view, {attributes: true, attributeFilter: ['hidden']});
  setInterval(() => { rows.forEach(updateControls); refresh(); }, 15000);
  refresh();
})();
