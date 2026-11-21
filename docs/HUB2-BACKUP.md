# Zálohování HUB2

Zálohovací úlohy přijímají pouze skutečný připojený zapisovatelný ext4
Samsung SSD s očekávaným UUID na `/mnt/hanzhub-backup`. Systemd jednotka
mount se načítá jako závislost zálohovacích služeb. Aplikace si ponechávají
vlastní služby a konfiguraci. Stav pro Dashboard je na `/api/backup/status`.
Selhání se zapíše do systémového žurnálu a zobrazí na Dashboardu.
Záloha odmítne zápis při rezervě pod 25 GiB.

## Denní Restic

`hanzhub-backup-daily.timer` spouští zálohu každý den v 02:00 podle
systémového času. Úložiště je `/mnt/hanzhub-backup/hub2/restic`.
Zálohuje `/opt`, `/etc` včetně HanzHub a systemd, `/var/lib/hanzhub`,
boot, metadata balíčků, Grafana data a konfiguraci InfluxDB. Zálohovaná
Compose konfigurace je součástí aplikačních stromů. Živé databáze
SQLite se ukládají přes SQLite Backup API s kontrolou integrity.
InfluxDB se exportuje vlastním příkazem `influx backup`. Jeho surový
živý datový svazek se nekopíruje. Pracovní kopie leží na šifrovaném
dočasném filesystemu na SSD. Restic kontroluje všechna uložená data.

Pro návrat jednotlivé aplikace obnov příslušné části snapshotu pomocí
`restic restore --include … --target … --verify` do izolovaného
adresáře. Cesty k SQLite kopiím začínají
`/run/hanzhub-backup/staging/sqlite/` a pokračují původní absolutní
cestou databáze. Influx data jsou v
`/run/hanzhub-backup/staging/influxdb` a obnovují se pomocí
`influx restore` do izolované instance. Při obnově do produkce nejprve
ověř konfiguraci, oprávnění a závislosti a vyžádej zásah do služby.

Lokální ověření vybraného snapshotu provede
`sudo bash /opt/hanzhub/backup/restore-check.sh SNAPSHOT_ID`.
Test obnovuje výběr do dočasného adresáře a izolovaného kontejneru
bez síťového přístupu. Používá skutečný zálohovaný SQLite obsah
a uložený export Meteo. [Dokumentace obnovy InfluxDB](https://docs.influxdata.com/influxdb/v2/admin/backup-restore/restore/)

## Týdenní IMG

Timer má okno každou neděli ve 04:00. Na běžícím HUB2 kontrola skončí
stavem `offline_source_required`. Produkční root je ext4 přímo na SD.
Export celé karty z živého systému nelze ověřit jako konzistentní
a služba nevytváří zavádějící výsledek. Automaticky neodstavuje aplikace.

Pro skutečnou image nabootuj schválený oddělený recovery systém.
Použij stejnou ověřenou SD jen jako zdroj, bez připojených oddílů
a s blokovým přístupem pouze pro čtení. Na recovery systému
zpřístupni zálohovací nástroje, Samsung SSD a klíč age. Úloha
ověřuje tabulku oddílů, FAT a ext4, boot konfiguraci a PARTUUID,
pak čte celý fyzický obraz, včetně tabulky oddílů. Šifrovaný
`hub2.img.age` vzniká uvnitř adresáře `.partial`. Ověřuje se SHA-256
nešifrovaného obsahu po dešifrování proti zdroji i SHA-256 ciphertextu.
Teprve potom se atomicky zveřejní adresář nové generace.

Obnovu nejprve proveď jako soubor do nezávislého zabezpečeného
úložiště. Ověř SHA-256 ciphertextu, dešifruj image a ověř její
`IMG.sha256`. Připoj image jako read-only loop s detekcí oddílů,
ověř boot a root a proveď offline kontroly filesystemu. Pro fyzický
zápis použij novou kartu o velikosti alespoň 62 277 025 792 B až po
schválení její stabilní identity a přesného rozsahu přepsání.
Skutečný boot ověř na nové kartě, kterou lze vyměnit za původní.
U zachovaného staršího obrazu se na HUB2 podařilo připojit
FAT a ext4 pouze pro čtení a přečíst boot konfiguraci a fstab.
Tento krok nepotvrzuje boot nového obrazu HUB2.

## Retence, klíče a nasazení

Denní plán ponechává 14 dní a vždy nejméně jeden snapshot.
Týdenní plán ponechává dvě ověřené nové generace v `hub2/images`.
Nástroje vypisují pouze kandidáty. Každé odstranění nebo prořezání
vyžaduje schválení konkrétních snapshotů a ověření novější zálohy.
Staré IMG v původním adresáři zůstávají mimo tento plán.

Instalátor je `sudo bash migration/hub2/backup/install.sh`.
Předpokládá balíčky `restic`, `gocryptfs`, `fuse3`, `age` a existující
Docker, `fdisk`, `e2fsprogs`, `dosfstools`. Aktivuje oba timery a načte
Dashboard adaptér. Pro odstavení automatizace zakaž oba timery,
současný běh nech doběhnout. Klíče jsou pod `/etc/hanzhub-backup` s
omezením na root. Uchovej jejich nezávislou kopii v zabezpečeném
trezoru vlastníka pro případ ztráty původní SD.

## Ověření na HUB2, 21. 11. 2026

Snapshot `cbd96a8f` má 20 218 351 698 B logických dat. První úložiště
na disku zabírá 3 276 013 568 B. Restic přečetl a ověřil všechny datové
balíky. Výběrová obnova přečetla sedm tabulek CoinListu a 93 tabulek
Grafany. U obou databází prošel `PRAGMA integrity_check`. Export
InfluxDB obnovil bucket Meteo do dočasného kontejneru bez sítě.
Systémový filesystem byl ověřen jako odmítnutý cíl zálohování.
Týdenní úloha odmítla právě používanou systémovou SD a vyvolala
stav chyby v Dashboardu a upozornění v žurnálu. Čtyři staré IMG
zůstaly zachované. Nový obraz a jeho fyzický boot čekají na
schválené recovery okno.
