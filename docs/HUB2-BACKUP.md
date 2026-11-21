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

Timer má okno každou neděli ve 04:00. Na živé SD bez nedávného
ověřeného obrazu hlásí `offline_source_required`. Sám nikoho
neodstavuje. Na Pi 5 je připravený jednorázový recovery start
prostřednictvím firmware `tryboot`. K použití stačí jeden schválený
start příkazem `sudo reboot '0 tryboot'`. Běžná konfigurace bootu i
jádro zůstaly zachovány. Recovery initramfs pracuje v RAM před
připojením root oddílu a po úspěchu nebo chybě přejde normálním
rebootem zpět. Pokud by se firmware zasekl před startem recovery,
po fyzickém resetu se použije běžná boot konfigurace. Export má
časový limit tři hodiny plus nejvýše minutu na ukončení procesu.
[Dokumentace Raspberry Pi k tryboot](https://www.raspberrypi.com/documentation/computers/config_txt.html)

Recovery čeká na obě známá zařízení, přepne zdrojovou SD v jádře na
read-only a připojí Samsung podle UUID. Klíč age přečte z root
oddílu jen pro čtení do RAM. Root následně odpojí a provede
kontroly filesystemu. Šifrovaný obraz celé karty, včetně tabulky
oddílů, zapisuje pod `.partial`. Do dočasného šifrovaného úložiště
na SSD obnoví image z ciphertextu, ověří velikost a SHA-256 vůči
zdroji a připojí obnovenou image přes read-only loop. Ověří FAT,
ext4, boot soubory a shodu PARTUUID rootu. Teprve potom zveřejní
generaci s kontrolními součty. Po běžném startu systemd importuje
durabilní výsledek ze Samsungu pro Dashboard.

Předpoklad je alespoň dvojnásobek velikosti SD, 25 GiB rezervy a
4 GiB na režii. Nástroje pro tvorbu alternativního initramfs a
jeho kontrolu používá `sudo bash migration/hub2/backup/recovery/install.sh`.
Spusť instalátor znovu po změně jádra nebo recovery modulu.
Nepřepisuje běžné `config.txt` ani nezahajuje reboot.

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

### Stav následné přípravy recovery

Na HUB2 je nainstalovaný alternativní initramfs a povolený import
výsledku. V archivu jsou udev pravidla, modul FUSE a potřebné
programy. Přístupové klíče v archivu nejsou. Ověřeno bylo čtení
dešifrované kopie z dočasného šifrovaného FUSE přes read-only loop
a plný read-only ověřovač oddílů na zachovaném starším IMG.
Živý zdroj byl opět odmítnut. Start do recovery, nový IMG a jeho
obnova na náhradní kartu čekají na schválený jednorázový reboot.
