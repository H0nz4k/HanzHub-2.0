# HUB2 P0 – dohledání konfigurace REDchecku a IoT

Kontrola proběhla na HUB2 dne 22. 11. 2026 a navazuje na [ověření integrací](HUB2-P0-INTEGRATIONS.md).

## Původní archiv

Původní cesta podle selektivní obnovy je `/mnt/hanzhub-migration/hanzhub-local-20261121T042115018448Z/files.tar.gz`. Přípojný bod je prázdný a Patriot P310 240 GB se nehlásí v seznamu blokových zařízení ani pod `/dev/disk/by-id`. Připojený Samsung 500 GB slouží denním zálohám. Jeho podadresáře se zálohami může číst pouze root a nejsou ověřenou kopií migračního archivu.

**První krok vlastníka:** Připoj původní Patriot P310 k HUB2 a z místní správcovské relace zpřístupni jeho ext4 oddíl jen pro čtení na `/mnt/hanzhub-migration`. Ověř model a sériové číslo a použij odpovídající oddíl pod `/dev/disk/by-id`, například příkazem `sudo mount -t ext4 -o ro,norecovery /dev/disk/by-id/<ověřené-ID-oddílu> /mnt/hanzhub-migration`. Pro cílené čtení archivu a chráněných souborů umožni jednorázovou autorizovanou správcovskou relaci. Nepředávej heslo ani klíče. V této relaci `sudo -n` vyžaduje heslo.

V archivu cíleně hledej původní `.config/redmine-assistant.env`, konfiguraci a systemd drop-iny REDchecku, `hanzhub-iot/.env`, původní databázi modulů, eWeLink `client.json` a `token.json` a Tuya záznamy `devices.json` / `tinytuya.json`. Eviduj jen přítomnost, ověření identity a výsledný stav autentizace. Přihlašovací údaje zpracuj přímo v privilegované relaci a případné pracovní soubory drž s oprávněním `0600`.

## REDcheck

Běží lokální služba. Starší jednotka používá `%h/.config/redmine-assistant.env`. Aktuální jednotka žádný `EnvironmentFile` nenačítá, pro běžící proces chybí klíč a síťové omezení propouští pouze loopback. Původní klíč zatím nelze ověřit. Po zpřístupnění archivu ověř nalezený klíč čtecím voláním `/users/current.json` a přístup k Helpdesku. Následné nasazení vyžaduje schválený změnový plán pro samostatný drop-in a cílený odchozí přístup. Zachovej existující pravidla přiřazování a schvalování.

Pokud původní klíč chybí nebo je odmítnutý, vlastník jednorázově uloží platný klíč účtu s přístupem k Helpdesku do `/etc/hanzhub/redcheck/redmine.env` jako `REDMINE_API_KEY` (root, `0600`).

## IoT / „Zás. infra“

HUB2 obsahuje původní `/opt/hanzhub-iot/.env` a zabezpečené Tuya `/opt/infrapanel/devices.json` a `/opt/infrapanel/tinytuya.json` (vše root, `0600`). Obsah v této relaci nebyl přístupný. eWeLink API hlásí `configured=false` a `connected=false`, jeho výchozí úložiště chybí. Čitelný Tuya snapshot má jeden záznam se šesti datovými body a název se neshoduje se „Zás. infra“. Prozatím tedy chybí potvrzený model, stabilní ID i schéma měření. Z těchto podkladů nelze určit, zda zásuvka podporuje W a kWh. Aktuální ovladače eWeLink a obecný Tuya přepínač poskytují stav spínání. Energetické hodnoty má připravené samostatný ovladač Tapo P110M.

Nejdřív spáruj název s identifikátorem z původní konfigurace nebo aplikace výrobce. Potom čti pouze stav a schéma měření. Pokud se potvrdí eWeLink a obnovitelná konfigurace klienta existuje, ale token je neplatný, uživatel jednorázově projde volbou připojení účtu eWeLink v IoT a schválí OAuth v prohlížeči. Pokud se potvrdí Tuya a zdroj vrátí stejný kód vypršení Cloud služby jako dříve, vlastník v původním Tuya projektu obnoví oprávnění služby pro čtení tohoto zařízení. Platformu zatím nelze vybrat za uživatele.

Běžící aplikace, SSH a časovač denních záloh zůstaly dostupné. Nebyl proveden příkaz k sepnutí ani změna konfigurace služby.
