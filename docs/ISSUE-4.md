# Issue #4 — inventura a export

## Stav na HUBu 21. 11. 2026

Read-only kontrola v omezené relaci potvrdila Raspberry Pi 5 Model B Rev 1.1, aarch64 a Debian 13. Systémový oddíl je na microSD. Samostatný Patriot M.2 P310 240 GB má oddíl ext4 na `/mnt/hanzhub-migration`. V této relaci byl připojený s příznakem `ro` a vykazoval přibližně 208 GiB volného místa. V kořeni byl vidět pouze `lost+found`, jehož obsah nebylo možné přečíst. Historický stav disku a existence nezávislé kopie zůstávají k potvrzení. Identifikátory zařízení jsou v privátní inventuře.

| Kandidát | Viditelné podklady | Chybějící ověření |
| --- | --- | --- |
| Dashboard 2.0, IoT, InfoLCD a infopanel | Aplikační stromy, jednotky, Compose a jeden připojený HDMI konektor | Revize živého nasazení, mapování úložišť, kiosk a GPIO včetně GPIO22 |
| Henk, Studio, hlas a MCP | Release stromy, jednotky pro runtime, audio a MCP, kandidátní release Studia | Aktivní revize, projekty a exporty Studia, použité animace, oprávnění a závislosti |
| REDcheck | Kandidát aplikačního stromu a záloh | Nasazený commit, lokální a vzdálené DB, integrace a konzistentní export |
| Meteo | Jednotky, více aplikačních stromů a Compose | Aktivní stack, datové úložiště, DB engine a export |
| CoinList a PredicApp | Jednotky a kandidátní SQLite soubory | Aktivní soubory, WAL a vazby na konfiguraci |
| LoRa, rádia a stream | Jednotky, release stromy a OpenWebRX Compose | Aktivní vydání, hardware, persistentní data a routy |
| Calendar a Whiteboard | Jednotky a aplikační stromy | Data, závislosti, přístup a funkční test |
| Další infrastruktura | Konfigurace záloh, tunelů, Pi-hole, agentů a plánovaných úloh | Aktivní jednotky, kontejnery, routy, porty, API a zařazení |

Na disku bylo vidět 70 systémových souborů s příponou `.service` v nejvyšší vrstvě konfigurace. Systemd D-Bus, Docker socket, úplný seznam portů, GPIO zařízení a část privátních souborů byly omezené. Názvy jednotek a cesty jsou kandidáti. Stav všech položek zůstává `discovered` v rozsahu dostupných podkladů. Schválené aplikační manifesty a klasifikace zachování zatím chybí. Z grafické migrace je podle zadání vyřazený 3,5″ ILI9486.

## Nástroje a rozhraní

Skripty vyžadují Bash-kompatibilní prostředí s `sh`, Python 3.12+ s podporou filtru tar `data`, GnuPG a util-linux. Privátní scratch pro SQLite snapshoty a rozšifrovaný obsah nastav přes `TMPDIR`. Před produkčním exportem musí být potvrzena identita fyzického cílového média, jeho stav, zápis a samostatná kopie potřebných dat. Identita se ve skriptu kontroluje očekávaným UUID, připojením přímo v daném mountpointu a režimem zápisu.

```sh
umask 077
migration/inventory.sh > "$PRIVATE_DIR/inventory.txt"
migration/backup.sh /mnt/hanzhub-migration "$EXPORT_UUID" "$GPG_RECIPIENT_FPR" "$PRIVATE_PLAN"
migration/verify.sh "$BUNDLE"
migration/restore.sh "$BUNDLE" --list
mkdir -m 700 "$TEST_PARENT"
migration/restore.sh "$BUNDLE" --app coinlist --parent "$TEST_PARENT"
migration/rollback.sh "$TEST_PARENT"
```

Plán je privátní JSON slovník podle ID aplikace. Manifest každé aplikace má evidovat zdroj a pinovaný commit, jednotky, uživatele, porty, routy, GPIO, API a MCP, závislosti, mapování konfigurace a dat, health check a návrat. Skript používá pole `files`; další metadata uloží do šifrovaného manifestu tak, jak byla dodána. Příklad položky je syntetický.

```json
{
  "example": {
    "files": [
      {
        "section": "data",
        "name": "app.sqlite",
        "source": "/example/source.sqlite",
        "method": "sqlite"
      }
    ]
  }
}
```

- `sqlite` používá SQLite online backup a kontrolu integrity samostatné kopie včetně transakcí z WAL. Pro každý další DB engine nejprve připrav jeho vlastní konzistentní export do souboru a zadej ho jako `native-export`. Stejný postup platí pro svazky kontejnerů, které potřebují aplikační snapshot nebo transakční export. Konzistenci přes více aplikací a souborů určuje plán konkrétního stacku.
- `static` je pro jednotlivé stabilní soubory a předem připravené release archivy. Do konfiguračních artefaktů zahrň jednotky i drop-iny pro pozdější revizi. Zdrojové soubory, data a konfigurační artefakty se ukládají pod `opt/<app>`, `var/lib/hanzhub/<app>` a `etc/hanzhub/<app>` uvnitř stagingu.
- Balík tvoří `bundle.tar.gz.gpg` a `SHA256SUMS`. Uvnitř je privátní manifest, časy a payload. Kompletní verifikace vyžaduje dešifrovací klíč a kontroluje shodu payloadu s manifestem i integritu SQLite. `--hash-only` provádí pouze kontrolu SHA-256. Hash bez důvěryhodného původu nedokládá autora balíku.
- `restore.sh --all` nebo `--app` rozbaluje do nového `staged` pod prázdným privátním adresářem. Služby, importy jiných DB, vlastníci souborů a rozbalení release archivů vyžadují aplikační postup. `rollback.sh` odstaví staging přejmenováním na `rolled-back` pro kontrolu a zachová jeho obsah.

## Výsledek testu a podmínky pokračování

Na HUBu prošel syntetický test archivu, online kopie SQLite s otevřeným WAL, kontrolního součtu, selektivního rozbalení a návratu stagingu. Test odmítl pozměněný balík a simulovaný read-only mount. Kontrola skutečného mountpointu a GPG kryptografie byly v tomto testu nahrazené. Plný test `migration/test-bundle.sh` v této relaci blokoval nedostupný GPG agent.

Stav nástrojů je `prepared`. Produkční stavy `exported`, `verified` a `restore-tested` zatím nenastaly. Na ověřeném odděleném hostu nebo VM nejprve proveď úplnou kontrolu balíku a obnovu skutečných DB, konfigurací a runtime. Spouštěj aplikace na izolovaných portech a s odpojeným GPIO a externími integracemi. Ověř pro každou aplikaci očekávanou revizi, běh, health endpoint a čtení referenčních dat. Zaznamenej výsledky i návrat k původnímu boot médiu před jakýmkoli přepnutím provozu.

## Přístup pro export z nativní relace

Hostitel potvrdil existující připojení oddílu v režimu zápisu. Cílená kontrola sandboxu rozlišila `VFS-OPTIONS=ro,nosuid,nodev,relatime` a `FS-OPTIONS=rw,stripe=4`. Uživatel `hanz` vlastní cílový adresář s režimem `0755`. Stačí zpřístupnit stávající mount v režimu RW v relaci exportéru a povolit zápis do `/mnt/hanzhub-migration`. Alternativou je časově omezené spuštění exportéru přímo v nativní relaci HUBu. Ani jedna cesta nevyžaduje remount na hostiteli nebo zásah do diskových dat.

- Exportér potřebuje čtení schválených zdrojů z privátního plánu a privátní scratch s dostatkem místa. Pro databáze vyžadující nativní export potřebuje omezené dump oprávnění, nebo přístup k dumpům vytvořeným správcem. SQLite ve WAL režimu vyžaduje přístup i k pomocným souborům dle pravidel SQLite. Čtení chráněných dat řeš po položkách.
- Pro export stačí importovaný veřejný GPG klíč a ověřený fingerprint příjemce. Úplné ověření a obnovu spusť v relaci příjemce s přístupem k jeho soukromému klíči, GPG agentovi a privátnímu stagingu. Soukromý klíč nemusí být dostupný exportéru.
- Privátní manifest musí vybrat skutečné zdroje a odpovídající metodu exportu. Částečná inventura poskytuje kandidáty. Pro chybějící položky stačí potvrdit jejich konkrétní runtime, data a způsob exportu.

## Export z nativní relace

HUB zpřístupnil SSD přímo pro zápis. Systém běží z microSD, externí SSD je samostatný ext4 mount. Aktuální sada jednotek a kontejnery potvrdily mimo jiné REDcheck jako uživatelskou službu a běžící InfluxDB, Grafanu, Caddy, IoT a Dashboard. Některé aplikační adresáře v /opt dědí nadřazený Git repozitář jiného projektu. Jeho HEAD proto nelze použít jako revizi těchto aplikací.

| Komponenta | Rozsah první sady | Co zbývá k obnově |
| --- | --- | --- |
| Dashboard | Logo a obraz běžícího nginx | Webový strom, routy, vlastní nastavení |
| Dashboard 2.0 a 7″ HDMI | Styly RC a grafika | Úplný release, kiosk a ověření na displeji |
| Henk | Obrázky a animace 13 stavů | Runtime, data, hlas a integrace |
| Henk Studio | Vybrané animace z aktivní verze | Editor, projekty, exporty a skutečný test workflow |
| InfluxDB | Obraz běžícího kontejneru | Nativní záloha InfluxDB včetně metadat a zkušební import |
| Grafana | Obraz běžícího kontejneru | Konzistentní záloha databáze, konfigurace, provisioning a pluginy |
| Caddy | Obraz běžícího kontejneru | Konfigurace a export perzistentních svazků |
| Meteo, IoT, LoRa, REDcheck, CoinList, Radio/SDR, Stream, Calendar, Whiteboard, Pi-hole | Provozní kandidáti | Kód, jednotky, závislosti a aplikačně konzistentní data |
| PredicApp, SMS/modem, Planetum, notifikace, infopanel, Hanz Agent, audio, API/MCP, SSH a tunely | Provozní kandidáti | Přístupová pravidla, konfigurace, data a plán obnovy |
| Staré release a zálohy, nejasné položky | Kandidáti pro oddělený archiv | Zařazení a samostatný šifrovaný export |
| GPIO, USB, systém a plánovače | Částečně inventarizováno | Privátní mapování zařízení, jednotek, timerů, účtů a závislostí |

Příkaz `python3 -B migration/export-public.py MOUNT UUID` použije výběr neprivátních artefaktů uvedený přímo ve skriptu. Zálohuje pouze neměnné distribuční obrazy identifikované z běžících kontejnerů, bez vrstev těchto kontejnerů, jejich nastavení a svazků. Režim `public` je určený výhradně pro prověřené neprivátní soubory. Hlavní export s fingerprintem je šifrovaný. Záznam každé aplikace v souhrnném manifestu obsahuje mapování souborů a původní režim, UID a GID. Staging obnovuje bezpečné režimy a cestu, vlastnictví se při cílovém nasazení mapuje na nové účty.

### Předání klíče pro privátní export

1. Příjemce připraví vlastní OpenPGP klíč se šifrovacím podklíčem na důvěryhodné pracovní stanici a uloží nezávislou zálohu soukromé části.
2. Do privátního exportního prostředí předá pouze veřejný klíč. Plný fingerprint potvrdí nezávislým kanálem. Exportér ověří fingerprint pomocí `gpg --show-keys --with-fingerprint` a importuje veřejný klíč do odděleného adresáře `GNUPGHOME` s režimem 0700. Skript používá přímo ověřený fingerprint.
3. Příjemce v izolovaném prostředí s vlastním klíčem dešifruje testovací zprávu a poté ověří a obnoví reálné zálohy. Citlivé mezisoubory patří do privátního RAM nebo šifrovaného pracovního prostoru s dostatečnou kapacitou.

Pro InfluxDB je potřeba oprávnění pro plný `influx backup`. Pro SQLite aplikace se nejprve potvrdí skutečné otevřené databáze a použije online backup. Docker svazky vyžadují omezený přístup podle konkrétní služby. DB REDchecku vyžaduje zjištění, která data vlastní lokální aplikace a která spravuje případný vzdálený Redmine. Dalším předpokladem čisté instalace zůstává nezávislá kopie potřebných dat, test importu a test na odděleném systému.
