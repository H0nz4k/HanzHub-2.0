'use strict';

// Remote mode displays only verified read-only data; private control stays on LAN.
(() => {
  if (!document.body.classList.contains('public-dashboard')) return;
  const pill = document.querySelector('.demo-pill');
  if (pill) {
    pill.textContent = 'HUB · pouze čtení';
    pill.setAttribute('aria-label', 'Veřejný přehled skutečných dat, pouze čtení');
    pill.title = 'Stavy se načítají z HUBu. Soukromé ovládání je dostupné v místní síti.';
    pill.onclick = () => { location.hash = '#settings'; };
  }
  // The existing router rewrites inline display on navigation.
  const privacyStyle = document.createElement('style');
  privacyStyle.textContent = 'body.public-dashboard #live-link{display:none!important}';
  document.head.append(privacyStyle);
  const henk = document.querySelector('.henk-card');
  if (henk) {
    henk.querySelector('.henk-copy h3').textContent = 'Stav Henka není ověřený.';
    henk.querySelector('.henk-copy p').textContent = 'Soukromé rozhraní Henka je dostupné v místní síti.';
    henk.querySelectorAll('a').forEach(link => { link.href = '#henk'; });
  }
  const messages = {
    henk: 'Stav a ovládání Henka jsou dostupné pouze v místní síti. Vzdálený přehled je nezastupuje ukázkovými úkoly.',
    iot: 'Registr zařízení je uvedený na přehledu. Podrobný stav a ovládání zařízení jsou dostupné pouze v místní síti.',
    meteo: 'Měření není ve vzdáleném přehledu připojené. Ukázkový graf se nezobrazuje.',
    calendar: 'Osobní kalendář je dostupný pouze v místní síti.',
    studio: 'Studio a ovládání InfoLCD jsou dostupné pouze v místní síti.',
    radio: 'Ovládání rádia je dostupné v místní síti.',
    settings: 'Vzdálený přehled používá skutečné stavy služeb a registr HUBu. Správa zařízení a soukromých služeb zůstává v místní síti.'
  };
  for (const [key, message] of Object.entries(messages)) {
    const view = document.querySelector('#view-' + key);
    if (!view) continue;
    const notice = document.createElement('p');
    notice.className = 'card panel public-data-notice';
    notice.textContent = message;
    view.append(notice);
  }
  for (const link of document.querySelectorAll('[data-service]')) {
    const url = new URL(link.href);
    if (link.dataset.service === 'calendar') link.href = '#calendar';
    if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') {
      link.removeAttribute('href');
      link.style.cursor = 'default';
      link.setAttribute('aria-disabled', 'true');
      link.title = 'Aplikace je dostupná pouze v místní síti.';
    }
  }
})();
