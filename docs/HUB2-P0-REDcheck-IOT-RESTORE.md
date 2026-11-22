# HUB2 | Obnova přístupu REDchecku a IoT

Ověřeno přímo na HUB2 dne 22. 11. 2026. Navazuje na [dohledání konfigurací](HUB2-P0-CREDENTIAL-RECOVERY.md). Patriot s migračním archivem zůstal připojený jen pro čtení.

## REDcheck | live-verified

Původní uživatelský soubor `.config/redmine-assistant.env` obsahoval platný klíč. Ověření účtu, projektu Helpdesk a seznamu otevřených požadavků vrátilo HTTP 200. Helpdesk obsahoval 28 otevřených požadavků. Synchronizační služba zapsala do SQLite 46 požadavků z kombinace Helpdesku a úloh přiřazených účtu. Dva automatické cykly zapsaly `last_sync` v 00:29:34 a 00:34:46 UTC. Místní `/api/overview` vrátil stejný počet i čas poslední synchronizace, bez chyby.

Klíč je v `/etc/hanzhub/redcheck/redmine.env` s vlastníkem `root:root` a režimem `0600`. Drop-in `40-redmine-sync.conf` jej načítá přes `EnvironmentFile`. Pravidlo odchozí sítě povoluje vedle loopbacku ověřenou adresu Redmine. Služba má vlastní soubor `/etc/hosts` připojený pomocí `BindReadOnlyPaths`. Při změně adresy zdroje je nutné upravit lokální soubor `hosts` a odpovídající pravidlo ve stejném kroku.

## IoT eWeLink | live-verified

Archiv obsahoval původní eWeLink registraci klienta, platný token a SQLite snímky registru IoT. Ve snímcích a v živém účtu se shodoval stabilní identifikátor jediného zařízení eWeLink. Jde o Sonoff S60TPF s původním označením „Zásuvka 2“. Označení „Zás. infra“ se nepodařilo doložit. HUB2 přes existující import přidal právě tento záznam pod původním názvem. Čerstvý dotaz do místního API potvrdil stav online a zdroj eWeLink.

Živý cloud pro stejné zařízení vrátil příkon, napětí, proud a denní i měsíční energetický součet. Surové hodnoty během kontroly byly `power=1005`, `voltage=23385`, `current=6`, `dayKwh=1` a `monthKwh=6037`. Místní ovladač IoT poskytuje stav připojení a spínače. Energetické údaje byly odečteny přímo z cloudu.

Původní nastavení IoT a soubory Tuya v archivu se shodovaly se stávajícími soubory HUB2. Tuya kandidát byl topný panel. LAN čtení vrátilo chybu 914 a Cloud po autentizaci odmítl stav i schéma kódem 28841002 kvůli vypršelému předplatnému.

IoT běží pod původním uživatelem. `/etc/hanzhub/iot/client.json` a `token.json` jsou `root:root`, `0600`. Drop-in `40-ewelink.conf` předává klienta přes `OpenFile` s příznakem `read-only` a token s příznakem `append`. Děděné deskriptory dovolují stejnému ovladači uložit další token bez zpřístupnění konfiguračního adresáře aplikaci. Doplnění tokenu a obnova po přerušeném zápisu byly ověřeny s testovacím tokenem pod účtem služby. Živá rotace tokenu zatím nebyla potřeba.

Odchozí síť je omezená na loopback a ověřené adresy regionálního eWeLink API. Při změně adresy či regionu je potřeba aktualizovat privátní soubor `hosts` a pravidla drop-inu společně. IoT startuje bez plánovače, počet plánů i událostí po importu byl nula. Nebyl odeslán příkaz ke změně stavu zařízení.

## Návrat

Pro REDcheck odeber drop-in `40-redmine-sync.conf`. Pro IoT odeber drop-in `40-ewelink.conf` a vrať původní soubor `/opt/hanzhub/hub2/iot-web.py.before-ewelink` na místo startovacího skriptu. Pak načti konfiguraci systemd a restartuj jen dotčenou službu. Konfigurace a lokální databáze lze ponechat pro následné čtení a ověření. V běhu této obnovy se restartovaly pouze obě cílové jednotky.
