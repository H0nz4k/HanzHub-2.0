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
