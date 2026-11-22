# HUB2 P0 | Living Glass a rádio

Ověření proběhlo přímo na HUB2 dne 22. 11. 2026.

## Dashboard 2.0 | live-verified

[PR #26](https://github.com/H0nz4k/Dashboard/pull/26) je vývojová větev Living Glass s živými adaptéry. Oproti jejímu headu `d506a16` je `fix/dashboard-main-live` o 20 commitů dále. Větve `fix/live-health-dashboard-v2` a `feat/henk-dashboard-inbox` jsou předci nasazené revize. `main` obsahuje starý rozcestník. Historická větev `feature/dashboard-v2-glass` se od něj odchýlila jedním commitem a neobsahuje tento Living Glass release.

| Položka | Nasazení |
|---|---|
| Zdroj UI | [Dashboard abd6f63](https://github.com/H0nz4k/Dashboard/commit/abd6f63f7cb4deb2ccd7bebf8095b2d2416332cd), 39 souborů Living Glass porovnaných s blob SHA z GitHubu, včetně původních obrázků Henka |
| Jednotka | `hanzhub-dashboard2.service`, uživatel `hanz`, drop-in `production-living-glass.conf` |
| Runtime | Statický release `/opt/hanzhub/dashboard/abd6f63` a doprovodný server v `/opt/hanzhub/dashboard/runtime-abd6f63` |
| Port a routy | Loopback 4001, vstup `/` vede na `/living-glass/`. `/radio.html` vede do sekce Rádio |
| Rozhraní | Původní seznam služeb, health, zálohy a čtecí proxy kalendáře doplněné o přehled registru IoT a rádiové stanice |
| Vrácení | Odebrat drop-in `production-living-glass.conf`, načíst systemd a restartovat pouze jednotku Dashboardu. Původní statické i serverové soubory zůstaly na místě |

Starý rozcestník měl hlavičku v2.5.1 a samostatný odkaz do Living Glass. Nový výchozí vstup načítá původní rozvržení Living Glass s postranní navigací, původním Henkem a dlaždicemi napojenými na katalog HUB2. REDcheck je samostatná dlaždice. Zmizel nefunkční odkaz ProjectionLab a dlaždice rádia už nevede na JSON. Přehled používá skutečný stav služeb, denní zálohy a jména registrovaných zařízení IoT. Sekce závislé na původní bráně 4010 mají na této instalaci režim ukázky a odkazy na místní aplikace.

Chromium přes Playwright na HUB2 ověřil navigaci, otevření REDchecku, obrázek Henka, 12 jedinečných a dostupných cílů a ovládání rádia při šířkách 1280 a 390 px. Browser plugin v této relaci nebyl dostupný. REDcheck samotný vrací 404 pro implicitní favicon. Nativní jednotka InfoLCD na 7″ HDMI běžela s původním PID a beze změny souborů či konfigurace.

## Rádio | internet live-verified, FM a reproduktor neověřeny

- Internetové stanice byly obnoveny ze souboru `var/lib/hanzhub-radio/state.json` v migračním archivu. Záznamy Radio 1 a ZUN včetně záložních adres jsou shodné s `DEFAULT_STATIONS` původního HanzHubRadio. Výchozí hlasitost je původních 25 %. Přehrávač bere nastavení z `/etc/hanzhub/radio/stations.json` a přehrává v prohlížeči.
- Volba původního USB zvukového výstupu je zachována v `/etc/hanzhub/radio/legacy-state.json` (`root:root`, `0600`). USB zvukové zařízení se na HUB2 nehlásilo. Připojený HDMI displej hlásil nula zvukových formátů a ALSA pokus skončil při otevření zařízení. Výstup přehrávače řídí klientský prohlížeč.
- Přehrání obou stanic v Chromium posunulo čas přes tři sekundy a zvýšilo počitadlo dekódovaných zvukových bajtů. Samostatný FFmpeg dekódoval oba zdroje do PCM s nenulovým signálem. Slyšitelnost na fyzickém reproduktoru zůstává neověřená.
- Původní SDR aplikace Radioama běží na loopbacku 4014, zdrojová revize `9451de5`, jednotka `hanzhub-radio.service` a databáze `/var/lib/hanzhub/radio/hanzradio.sqlite`. Čtyři předvolby, jeden skenovací profil a nastavení stanice se funkčně shodují s archivem. Liší se pouze časy vytvoření a úprav. Databáze tedy zůstala na místě. Rádio nabízí přímý odkaz na skutečné ovládání Radioama.
- SDR přijímač se při kontrole nehlásil přes USB a služba hlásila `OFFLINE`. Po připojení je potřeba ověřit identitu přijímače a zpřístupnění odpovídajícího zařízení jednotce, která teď používá `PrivateDevices=yes`, a pak ověřit FM na archivní předvolbě.
