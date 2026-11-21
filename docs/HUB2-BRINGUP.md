# Uvedení aplikací do provozu na HUB2

Ověřeno 21. 11. 2026 na Raspberry Pi 5 s Debianem 13. Obnovené aplikační
stromy jsou v `/opt`. Nové jednotky jsou v `migration/hub2`. Dvanáct
jednotek běží a je povoleno při startu systému. Odpovědi byly zkontrolovány
přes localhost. Grafana odpověděla uvnitř kontejneru.

| Aplikace | Stav | Port | Ověření | Zbývá |
| --- | --- | --- | --- | --- |
| Dashboard 2.0 | Soubory obnoveny, lokální web běží | 4001 | `/` a `/living-glass/` HTTP 200 | Integrace služeb a kiosk. Oba HDMI konektory hlásily odpojeno. |
| Henk Studio | Soubory a grafika obnoveny, lokální web běží | 4002 | Index a původní WebP HTTP 200 | Editor, náhled, export a projekty v úložišti původního originu. |
| InfluxDB | Běží, funkčně ověřená | 8086 | `/health` pass, autentizovaný seznam bucketů a dotaz Meteo | Používá nové úložiště. |
| Grafana | Běží, health ověřen | 3000 v kontejneru | `/api/health`, DB ok | Datový zdroj a původní dashboardy. |
| Meteo | Soubory obnoveny, web a BLE přijímač běží | 5000 | Čtení aktuálních hodnot a historie HTTP 200 | BLE čidlo se při ověření nenašlo. Dotaz na hodnoty vrátil prázdný výsledek. |
| IoT | Soubory obnoveny, lokální web a API běží | 4011 | `/api/iot/health` a `/api/iot/devices` HTTP 200 | Původní databáze zařízení chybí. Plánovač a přístup k fyzickým modulům jsou vypnuté. |
| CoinList | Soubory obnoveny, lokální web běží nad kopií dat | 5001 | Index HTTP 200 a SQLite integrity check | Zápis a vzdálené závislosti dosud neověřeny. |
| LoRa | Soubory obnoveny, lokální web běží | 8085 | `/version` a `/nodes` HTTP 200 | Příjem a vysílání. V systému se neobjevil identifikovaný LoRa adaptér. |
| HanzRadio | Soubory obnoveny, lokální API běží nad kopií dat | 4014 | `/health` a `/api/v1/presets` HTTP 200, SQLite integrity check | USB SDR nepřítomen, příjem a OpenWebRX neověřeny. Port 4014 zachovává 4012 pro Calendar. |
| Stream | Soubory obnoveny, lokální web běží | 8088 | `/status` HTTP 200 a syntetický vstup převedený původním workerem na místní H.264/FLV | Ve složce videos nejsou soubory. Koncové vysílání neověřeno. |
| Whiteboard | Soubory obnoveny, lokální web běží nad kopií dat | 8099 | `/api/events/count` HTTP 200 a 12 zachovaných událostí | Kamera a příjem nových událostí. Odesílání SMS je vypnuté. |
| Calendar | Soubory obnoveny, lokální HTTP a HTTPS běží | 4012, 4013 | `/api/calendar/status` HTTP 200 na obou portech | Původní OAuth konfigurace a stav účtu chybí. Lokální certifikát je vlastní. |
| PredicApp | Soubory obnoveny, lokální web běží nad kopií dat | 8084 | `/api/system_health` HTTP 200, SQLite quick check, načtené predikce | Plánovač je vypnutý. Prázdný model zlata v2 obsloužil existující fallback v1. |
| REDcheck | Nedoložené soubory a služba | — | Nalezen jen záznam o dřívější uživatelské službě | Zdrojový strom, data a jednotka. Migrační svazek nebyl připojen. |
| InfoLCD, infrapanel, Pi-hole, SMS, notifikace, hlas a další pomocné stromy | Soubory kandidátů v `/opt` | — | Bez funkčního testu | Obnovené konfigurace, závislosti a samostatné ověření. 3,5″ ILI9486 je mimo migraci UI. |

## Konfigurace a návrat

- Lokální jednotky nepublikují nové porty do LAN. Stávající publikování
  portu InfluxDB zůstalo pod správou dříve spuštěného Compose stacku.
- Citlivé konfigurace Meteo, Whiteboard a TLS Calendar jsou pod
  `/etc/hanzhub`. IoT používá závislosti z obnoveného
  `/opt/hanzhub-iot/iot/requirements.txt` ve vlastním prostředí.
- Stavové soubory jsou pod `/var/lib/hanzhub`. Pro CoinList, rádio a
  PredicApp vznikly SQLite kopie přes SQLite backup API. Whiteboard
  převzal kopii souborových událostí. CSV přijímače Meteo začíná v novém
  adresáři bez staré historie. Zdrojová data zůstala dostupná v `/opt`.
- Stream používá balíček FFmpeg z Debianu pro Raspberry Pi. Test původního
  workeru měl vlastní dočasnou konfiguraci a výstup do místního souboru.
- Běh a povolení při startu lze ověřit skriptem `migration/hub2/verify.sh`.
  Jednotlivou novou službu lze vrátit pomocí `systemctl disable --now
  JMÉNO.service`. Zachovej datovou kopii pro případné sloučení následných
  zápisů. Nasazení UI přidalo účtu služby čtecí ACL na oba obnovené stromy.
- Restart hostitele nebyl součástí ověření. Starý Operations Broker se
  nespouštěl. Nebyl proveden žádný test přepínání fyzického GPIO nebo relé.

## Issue #5 — živé kontroly po výchozím rebootu

Stav 21. 11. 2026. Dashboard je dostupný na loopbacku a nepoužívá starý
Operations Broker. Původní stromy Dashboardu a Studia zůstaly na disku.
Kontrola dostupnosti měří odpověď vybraného endpointu.

| Aplikace | Provoz | Funkce ověřená na HUB2 | Omezení / další krok |
| --- | --- | --- | --- |
| Dashboard 2.0 | loopback :4001 | Chromium při 1024 × 600 zobrazil 11/11 služeb. Všech 11 cílových URL odpovědělo, včetně místního Kalendáře a REDcheck. IoT vrací lokální odkaz zpět. | HanzRadio odkazuje na JSON presetů. Stav záloh zůstává neznámý. Living Glass obsahuje ukázkové pohledy. |
| HDMI kiosk | Cage + Chromium, jednotka active a enabled | Po restartu jednotky má HDMI-A-1 aktivní CRTC s obrazem 1024 × 600. | Plný reboot po instalaci kiosku a vizuální kontrola fyzického panelu neprovedeny. |
| Henk Studio | loopback :4002 | Playwright otevřel Studio z Dashboardu, upravil reakci, spustil náhled, ověřil JSON export a název projektu po obnovení stránky. Test měl izolovaný profil. | Původní projekty v jiném originu vyžadují export/import. Fyzický blesk netestován. |
| Meteo / InfluxDB | web a BLE přijímač běží | API aktuálních hodnot a historie odpovídají, obě vracejí prázdný objekt. Bluetooth je zapnutý, přijímač opakovaně nenajde zařízení. | Zpřístupnit BLE vysílač a doložit první měření v grafu. |
| IoT / infrapanel | loopback :4011, plánovač vypnutý | Stav eWeLink hlásí nenakonfigurovaný účet, seznam modulů je prázdný. Čtecí Tuya dotaz na dochované zařízení vrátil chybu 914 bez datových bodů. | Ověřit dostupnost měřidla, jeho kumulativní kWh a skutečný tarif Kč/kWh. |
| Grafana | kontejner, health DB ok | SQLite otevřená v režimu pouze pro čtení potvrdila 0 zdrojů a 0 dashboardů. Administrátorský API dotaz dostal 401. | Potřebný platný přístup pro přidání zdroje a grafů. |
| Kalendář / REDcheck | místní weby odpovídají | Dashboard předává čtecí stav Kalendáře. REDcheck vrací přehled a verzi. | Kalendář hlásí nenastavený účet. REDcheck nemá konfiguraci ani úspěšnou synchronizaci. |
| Whiteboard / rádio / LoRa | místní data a API | Whiteboard vrací 12 existujících událostí. Rádio vrací 4 presety. LoRa vrací odpověď uzlů. | Kamera, SDR příjem a rádiový přenos neověřeny. Nalezené ttyUSB porty patřily modemu. |
| CoinList / Stream / PredicApp | cílové stránky dostupné | Navazují na dřívější ověření dat a místního enkódování. | Zápis, vzdálené vysílání a plánovaná aktualizace zůstávají bez nového testu. |

Nové soubory pro nasazení jsou v `migration/hub2`. Na HUB2 se použily
balíčky Debian/Raspberry Pi `cage` a `chromium`, server
`dashboard-web.py` v `/opt/hanzhub/hub2/` a dvojice drop-inů
`local.conf` pro `hanzhub-dashboard2.service` a `hanzhub-iot.service`.
Grafický profil je v `/var/lib/hanzhub/kiosk`. Jednotka kiosku používá
`tty1` a při startu čeká na lokální Dashboard. Pro návrat vypni kiosk
příkazem `systemctl disable --now hanzhub-kiosk` a spusť
`systemctl start getty@tty1`. Pro návrat Dashboardu a IoT odeber pouze
jejich nově přidané drop-iny `local.conf`, načti jednotky příkazem
`systemctl daemon-reload` a restartuj tyto dvě služby. Zachovej data
a uživatelský profil kiosku.

## P0 — nové zdroje dat

- Grafana na loopbacku používá stávající Compose projekt. Přibyl dashboard
  `hub2-meteo` se čtyřmi panely a datový zdroj `hub2-meteo-influx`.
  Zabezpečený Influx credential posloužil k vydání samostatného tokenu
  omezeného na čtení bucketu Meteo. Grafana uložila zdroj i dashboard.
  Dotazy všech panelů proti živé InfluxDB vracejí HTTP 200 bez řádků.
  Dotaz stejným tokenem do jiného bucketu byl odmítnut. Karta Dashboardu
  vede na přihlášení Grafany se zpětným odkazem na Meteo dashboard.
- IoT na portu 4011 nemá konfiguraci eWeLink ani moduly. Migrační úložiště
  není dostupné. Dochované Tuya záznamy mají shodnou identitu, ale jejich
  název nepotvrzuje „Zás. infra“. Uložený LAN endpoint přijímá TCP, avšak
  čtecí stav s oběma dochovanými klíči a evidovanou verzí 3.4 vrací 914.
  Tuya Cloud vydá token, ale čtení stavu odmítne kódem 28841002 kvůli
  vypršelé službě. Chybí potvrzená identita a skutečná energetická
  telemetrie. Sběr, grafy energie a výpočet Kč se zatím nenasazovaly.
- BLE přijímač skenuje bez chyb. V 180 po sobě jdoucích pokusech nenašel
  očekávaný vysílač. Samostatný sken viděl čtyři jiné inzerenty a žádné
  odpovídající jméno ani servisní UUID. API na portu 5000 nemá aktuální
  data ani historii. Starší historie se neimportovala.
- REDcheck potřebuje platný API klíč pro stávající zdroj. Lokální API
  hlásí prázdný přehled bez úspěšné synchronizace. Kalendář potřebuje
  původního OAuth klienta. Po jeho bezpečném obnovení stačí v Kalendáři
  potvrdit přístup k účtu Google, pokud původní token chybí nebo vypršel.

### Nasazení grafů Meteo

Z adresáře `migration/hub2/grafana` nainstaluj `dashboards.yml` a
`meteo.json` do `/etc/hanzhub/grafana` a spusť `provision-token.py`
jako root. Skript znovu používá pouze aktivní token se stejným účelem a
ověřeným rozsahem. Výsledný soubor `datasource.yml` patří výhradně na HUB2.
Nainstaluj `compose.override.yml` jako `docker-compose.override.yml`
do stávajícího adresáře projektu a aplikuj změnu příkazem
`docker compose up -d --no-deps --pull never grafana`. Původní InfluxDB
zůstala během změny spuštěná. Grafana má původní restart policy
`unless-stopped`. Pro návrat vyjmi přidaný Compose override a přepočítej
pouze službu Grafana stejným příkazem. Grafana si vytvořená nastavení
uchovává v původním datovém svazku.
