'use strict';
(() => {
  const target = document.querySelector('[data-settings-root]');
  if (!target) return;
  const apps = [...document.querySelectorAll('[data-service]')];
  const key = 'hh-hidden-apps';
  let hidden = new Set();
  try { hidden = new Set(JSON.parse(localStorage.getItem(key) || '[]')); } catch {}
  const element = (tag, text = '', className = '') => {
    const node = document.createElement(tag);
    node.textContent = text;
    node.className = className;
    return node;
  };
  function card(title) {
    const el = element('article', '', 'card panel host-settings');
    el.append(element('h2', title));
    target.append(el);
    return el;
  }
  const tiles = card('Dlaždice aplikací');
  const choices = element('div', '', 'host-settings-tiles');
  tiles.append(choices);
  const message = element('p', '', 'muted');
  message.setAttribute('role','status');
  tiles.append(message);
  for (const app of apps) {
    const id = app.dataset.service;
    app.hidden = hidden.has(id);
    const label = element('label');
    const check = document.createElement('input');
    check.type = 'checkbox';
    check.checked = !app.hidden;
    label.append(check, document.createTextNode(app.querySelector('h3').textContent));
    check.onchange = () => {
      if (check.checked) hidden.delete(id); else hidden.add(id);
      app.hidden = !check.checked;
      try {
        localStorage.setItem(key, JSON.stringify([...hidden]));
        message.textContent = '';
      } catch { message.textContent = 'Nastavení prohlížeče nelze uložit.'; }
    };
    choices.append(label);
  }
  const ports = card('Služby a porty');
  ports.id = 'hub-host-ports';
  const gpio = card('GPIO na HUB2');
  gpio.append(element('p', 'Přiřazení se ukládá pro celý HUB2. Výstupy se aktivují až po ověření zapojení.', 'muted'));
  const details = element('details');
  details.append(element('summary', 'Stav pinů BCM'));
  gpio.append(details);
  const assigns = element('div');
  gpio.append(assigns);
  const notice = element('p', '', 'muted');
  notice.setAttribute('role','status'); gpio.append(notice);
  function table(headings, rows) {
    const wrap = element('div', '', 'host-settings-scroll');
    const t = element('table'), header = t.createTHead().insertRow();
    for (const label of headings) header.append(element('th', label));
    const body = t.createTBody();
    for (const row of rows) {
      const tr = body.insertRow();
      for (const value of row) tr.insertCell().textContent = value;
    }
    wrap.append(t);
    return wrap;
  }
  async function request(body) {
    const r = await fetch('/api/dashboard/host-settings', {method:body ? 'POST' : 'GET', cache:'no-store',
      headers:body ? {'Content-Type':'application/json'} : {}, body:body && JSON.stringify(body),
      signal:AbortSignal.timeout(6000)});
    const data = await r.json();
    if (!r.ok) throw Error(data.error || 'Nastavení se nepodařilo načíst.');
    return data;
  }
  async function load() {
    try {
      const data = await request();
      ports.querySelector('div')?.remove();
      ports.append(table(['Služba','Port','Poslech'], data.ports.map(([name,p,running,lan]) =>
        [name,p,running?(lan?'Síťové rozhraní':'Pouze na HUB2'):'Nenaslouchá'])));
      details.querySelector('div')?.remove();
      details.append(table(['BCM','Režim','Využití'], data.gpio.lines.map(line =>
        [line.pin,line.label,line.consumer || (line.available ? 'Neobsazený podle systému' : 'Rezervovaný / používá se')])));
      assigns.replaceChildren();
      if (!data.gpio.lines.length) notice.textContent = 'Aktuální stav GPIO není dostupný.';
      for (const [id,title] of Object.entries(data.gpio.functions)) {
        const saved = data.gpio.assignments[id];
        const row = element('div', '', 'host-settings-pin');
        const label = element('label', title);
        const select = document.createElement('select');
        select.add(new Option('Bez přiřazení',''));
        for (const line of data.gpio.lines) {
          if ((line.available && !Object.entries(data.gpio.assignments).some(([key,p])=>key!==id&&p===line.pin))
              || saved === line.pin) select.add(new Option('GPIO '+line.pin,line.pin));
        }
        if (saved != null && ![...select.options].some(o=>Number(o.value)===saved && o.value)) {
          select.add(new Option('GPIO '+saved+' (stav neověřen)',saved));
        }
        select.value = saved ?? '';
        label.append(select);
        const save = element('button','Uložit přiřazení','button');
        save.type = 'button';
        save.onclick = async () => {
          save.disabled = true;
          try {
            await request({function:id, pin:select.value==='' ? null : Number(select.value)});
            notice.textContent = 'Přiřazení uloženo. Výstup čeká na ověření zapojení.';
            await load();
          } catch (e) { notice.textContent = e.message; }
          finally { save.disabled = false; }
        };
        row.append(label,save); assigns.append(row);
      }
    } catch(e) { notice.textContent = e.message; }
  }
  function route() {
    if (!location.hash.startsWith('#settings')) return;
    load();
    if (location.hash.includes('ports=1')) setTimeout(()=>ports.scrollIntoView({block:'start'}),80);
  }
  document.querySelector('.sidebar .brand')?.addEventListener('click',()=> {
    if (location.hash === '#dashboard') document.querySelector('.main').scrollTo({top:0});
  });
  addEventListener('hashchange',route);
  route();
})();
