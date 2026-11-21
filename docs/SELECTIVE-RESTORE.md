# Selektivní obnova na Debianu 13

Podklady jsou Issue #4, [migrační plán](MIGRATION.md) a [dosavadní inventura](ISSUE-4.md).
V kontrolované relaci byl systémový oddíl na microSD s přibližně 22 GiB
volného místa. Dodaný files.tar.gz je na samostatném svazku. Přístup
blokuje privátní nadřazený adresář. Velikosti níže jsou neověřené.
Velikost dřívějšího dílčího exportu nelze použít pro tento archiv.

| Pořadí | Aplikace | Velikost výběru | Závislosti a podmínky pro spuštění |
| --- | --- | --- | --- |
| 1 | Henk Studio a jeho grafické assety | Neověřena | Identifikovat release editoru a projekty, ověřit runtime dle release, načtení animací a export v izolaci. Hlas a MCP řešit zvlášť. |
| 2 | Henk runtime | Neověřena | Identifikovat release a sadu animací, ověřit vykreslení bez hlasu a MCP, následně audio a konektory samostatně. |
| 3 | Dashboard 2.0 a 7″ HDMI | Neověřena | Ověřit úplný webový build a jeho HTTP server, routy a port. Na cíli zjistit stav HDMI konektoru a dostupné režimy, poté otestovat kiosk na fyzickém displeji. |
| 4 | IoT, InfoLCD závislosti a Meteo | Neověřena pro každou aplikaci | Ověřit compose/runtime, datové zdroje, InfluxDB, Grafanu a mapu GPIO, pokud je používá konkrétní release. 3,5″ ILI9486 je vyřazený. |
| 5 | REDcheck, CoinList, PredicApp | Neověřena pro každou aplikaci | Ověřit runtime, vzdálené integrace a nativní DB export nebo konzistentní SQLite snapshot podle aplikace. |
| 6 | LoRa, rádia, stream | Neověřena pro každou aplikaci | Ověřit USB/SDR, audio, zařízení a GPIO, porty a routy s hardwarem odpojeným při prvním testu. |
| 7 | Calendar a Whiteboard | Neověřena pro každou aplikaci | Ověřit runtime, úložiště, přístupová pravidla a izolovaný test čtení dat. |

Pořadí je návrh. Před obnovou aplikace potvrď její konkrétní závislosti
a revizi. Starý Operations Broker je pozastaven k samostatnému posouzení.
Účet hanz, SSH, síť a konfigurace bootu zůstávají pod správou nového OS.
Původní disk a zdrojový archiv ponech pro návrat. Staré systémové
jednotky, tunely a plánovače slouží jako podklady k revizi.

Před nasazením projdi soupis archivu v oprávněné relaci. Vyber pouze
prověřené soubory a sepiš privátní manifest po aplikacích. Rozděl
runtime, konfiguraci a data. Spočítej velikost pro každou aplikaci a
započti rezervu pro další běh systému. Ověř původ archivu, nezávislou
kopii a možnost obnovy. Poté otestuj vybranou aplikaci do izolovaného
kořene. Instalaci na cíli proveď po schválení jejího plánu. Databázové
importy a spuštění služeb následují v samostatném postupu po kontrole
závislostí, kolizí, účtů a oprávnění.

## Inventura a instalace

Použij Python 3.13 na Debianu 13. Soupis vypisuje JSON Lines s cestami
a velikostmi. Zpracuj ho v privátní relaci a výstup ani manifest
neukládej do GitHubu. Příkazy čtou gzip přímo ze zdrojového svazku.

```sh
ARCHIVE=/mnt/hanzhub-migration/hanzhub-local-20261121T042115018448Z/files.tar.gz
python3 -B migration/selective-restore.py "$ARCHIVE" inventory
python3 -B migration/selective-restore.py "$ARCHIVE" plan "$PRIVATE_MANIFEST"
```

Manifest je JSON objekt podle ID aplikace v pořadí obnovy. Pro každou
aplikaci uveď `repo`, `revision` (pinovaný commit), `dependencies`,
`services`, `ports`, `routes`, `gpio`, `apis` (včetně MCP), `mounts`,
`health`, `backup`, `rollback` a pole `files`. Metadata jsou podklad
pro ruční kontrolu nasazení. Položka `files` má například podobu
`{"source":"old/studio/assets/flame.png","section":"runtime","name":"assets/flame.png"}`.
Cesta zdroje musí odpovídat položce ze soupisu. Vybírej jednotlivé
běžné soubory. Sekce `runtime`, `config` a `data` mapují do
`/opt/<app>`, `/etc/hanzhub/<app>` a `/var/lib/hanzhub/<app>`.
`plan` vypíše součet bajtů i rozpad po sekcích v pořadí manifestu.
Pro přípravu Henk Studia zmapuj vedle editoru také projekty, exporty
a grafiku. Pro Dashboard vyber úplný release a kiosk podklady pro 7″ HDMI.

Pro izolovaný test zvol existující privátní testovací kořen s dostatkem
místa, vytvoř potřebné nadřazené adresáře a použij ověřený SHA-256
z důvěryhodného exportního záznamu.

```sh
umask 077
mkdir -p "$TEST_ROOT"/opt "$TEST_ROOT"/etc/hanzhub "$TEST_ROOT"/var/lib/hanzhub
python3 -B migration/selective-restore.py "$ARCHIVE" install "$PRIVATE_MANIFEST" \
  --app henk-studio --sha256 "$TRUSTED_SHA256" --root "$TEST_ROOT"
```

Pro schválené cílové nasazení spusť stejný příkaz z oprávněné
administrátorské relace bez `--root`. Nadřazené adresáře musí
existovat. Instalace po jedné aplikaci ověří hash, vybrané položky
a volné bloky a inody podle cílového filesystému. Minimální rezerva je
2 GiB na každý dotčený filesystém. Pro větší provozní rezervu nastav
`--reserve-bytes`. Instaluj v době bez souběžných velkých zápisů.

Obsah se zapisuje do privátních dočasných adresářů na cílových
filesystémech. Každá sekce se zveřejní přejmenováním bez přepsání
existujícího cíle. Soubory patří instalujícímu účtu a práva jsou
privátní. Podle ověřeného manifestu je následně nastav pro účty služeb.
Při běžné chybě publikace nástroj přesune dokončené sekce zpět do
stagingu. Při výpadku napájení nebo ukončení SIGKILL zkontroluj
cílové adresáře aplikace a skryté adresáře `.<app>-restore-*`.
Vlastní izolované adresáře z neúspěšného pokusu po kontrole přesuň
stranou podle rollbacku aplikace. Spusť nový pokus až po kontrole
jejich obsahu a uvolnění cílových cest.

Stav tohoto postupu je `prepared`. Pro skutečný archiv zbývá soupis,
privátní manifest s velikostmi a závislostmi, izolovaný test skutečných
dat, kontrola režimu 7″ HDMI a aplikační ověření na cíli.

## Záznam operací na HUB2

- Příprava nástroje, testovacího souboru a tohoto postupu je v lokálním
  commitu `7d8c294`. Syntetické testy nebyly v této relaci spuštěny.
- Systém běží z microSD. Pro `/opt` bylo dostupných 22 GiB.
  Migrační svazek byl připojen s `ro,norecovery`. Nadřazený adresář
  archivu má režim `0700` a vlastní jej root. Pokus o jednorázový výpis
  přes `sudo -n` skončil požadavkem na heslo. Obsah a kontrolní součet
  archivu zůstávají neověřené.
- Henk Studio ani Dashboard 2.0 nebyly obnoveny. Oba HDMI konektory
  hlásily `disconnected` a žádný režim. Starý Operations Broker nebyl
  spuštěn a systémová konfigurace se nezměnila.
