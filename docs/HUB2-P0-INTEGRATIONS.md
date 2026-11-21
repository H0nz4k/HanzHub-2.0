# HUB2 P0 – ověření integrací 2026-11-21

Kontrola na HUB2 navázala na stav větve `hub2-issue5` a na dřívější [bring-up](HUB2-BRINGUP.md). Dashboard přes `/api/health` potvrdil dostupnost IoT, Meteo, Grafany a REDchecku. SSH a časovač denní zálohy běžely. Dashboard hlásil denní zálohu ve stavu `ok`.

| Aplikace | Běží | Skutečná data | Funkce ověřena | Omezení |
|---|---|---|---|---|
| IoT / infrapanel | Lokální web a API | SQLite má 0 modulů a 0 událostí. | `/api/iot/health` a `/api/iot/devices` odpovídají, seznam je prázdný. Runtime nespouští plánovač. | Zabezpečené soubory Tuya existují, proces kontroly k nim nemá oprávnění. Migrační svazek není připojený. Předchozí čtecí pokusy skončily chybou Tuya LAN 914 a Cloud 28841002. |
| Meteo | BLE přijímač, web, InfluxDB a Grafana | Přímý autentizovaný dotaz do bucketu za 24 hodin vrátil 0 hodnot `meteo` a 0 hodnot `receiver_status`. | Bluetooth je zapnutý a skenuje. Za 10 minut 100 pokusů bez shody, žádná chyba skenu. `/api/current` a `/api/history` vrátily prázdné objekty. Grafana odpovídá a stránka Meteo vede na přihlášení. | Přijímač čeká na inzerované jméno `ESP32-Meteo`. Identita fyzického vysílače a zápis paketu zůstávají neověřené. |
| REDcheck | Lokální web a synchronizační vlákno | SQLite má 0 požadavků a 0 událostí. `last_sync` je prázdný. | `/api/overview` hlásí chybějící `REDMINE_API_KEY`. Zdroj na `/users/current.json` odpověděl z hostitele HTTP 401 bez autentizace. | Jednotka omezuje síť na loopback a nemá připojený soubor s přihlašovacími údaji. |

## Podmínky pro ověření funkcí

- **IoT:** Získej čtecí přístup k funkční konfiguraci a potvrď stabilní ID „Zás. infra“ v účtu. Z jednoho ověřeného zařízení odečti W a zjisti jednotky i význam kWh údajů. Na jejich základě zapoj sběr a denní, týdenní a měsíční graf v existujícím IoT. Pro výpočet ceny použij potvrzený tarif v Kč/kWh. Při kontrole nebyla zásuvka ani panel sepnuty a nevznikla náhradní měření.
- **Meteo:** Zpřístupni stávající vysílač v dosahu HUB2. Po zachycení ověř jednoznačnou identitu vysílače a stejný čas prvního skutečného měření v InfluxDB, `/api/current` a grafu. Historie se neimportovala.
- **REDcheck – jediný krok vlastníka:** Ulož platný klíč účtu s přístupem k projektu Helpdesk do rootem vlastněného souboru `/etc/hanzhub/redcheck/redmine.env` s režimem `0600`, jako položku `REDMINE_API_KEY`. Klíč neposílej do chatu ani do GitHubu.

Po zpřístupnění klíče je plánovaná změna jednotky REDchecku samostatný drop-in s `EnvironmentFile=/etc/hanzhub/redcheck/redmine.env` a síťovým pravidlem pro aktuální ověřené IP adresy zdroje při zachování omezení na loopback pro ostatní cíle. Po schválení změny a restartu jednotky ověř dva automatické běhy podle rostoucího `last_sync` a podle počtu požadavků ze zdroje. Existující synchronizační kód i pravidla přiřazení a schvalování zůstala beze změn. Návrat spočívá v odebrání tohoto drop-inu a restartu pouze REDchecku.

Stav P0 je **BLOCKED** pro všechny tři datové integrace. Tato kontrola nezměnila žádnou běžící službu.
