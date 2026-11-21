# Export spuštěný přímo na HUBu

Skript je samostatný, potřebuje Python 3.11+ a findmnt.
Spusť v terminálu přímo na původním HUBu:

```bash
sudo python3 export-local.py --plain --uuid "$(findmnt -n -M /mnt/hanzhub-migration -o UUID)"
```

Před spuštěním zkontroluj, že `/mnt/hanzhub-migration` je požadovaný
SSD (`lsblk -o NAME,MODEL,SERIAL,SIZE,UUID,MOUNTPOINTS`). Skript ověří přesný
mountpoint, UUID a režim RW. Nic nepřipojuje, nepřeformátuje ani nevypíná.
Každý běh vytvoří nový soukromý adresář, předchozí exporty zachová.

Výchozí export je bez šifrování, podle zadání. Obsahuje i SSH klíče a hesla.
Volitelný přepínač `--encrypt` vyžaduje GnuPG a požádá o heslo pro archiv.
Při přípravě vznikají v soukromém adresáři na SSD dočasné nešifrované
DB dumpy a SQLite snapshoty; úspěšný běh je odstraní, přerušený je může zachovat.
Žádné exporty ani jejich privátní reporty nedávej na veřejný GitHub.

Export zahrnuje `/opt`, `/etc`, `/home`, `/root`, `/usr/local`, `/var/lib`,
cron a boot konfiguraci. Zahrnuje tedy i staré aplikace v domovských adresářích.
Zahrnuje skryté soubory, profily a `.ssh` uživatelů i roota: soukromé/veřejné
klíče, `authorized_keys`, `known_hosts` a SSH config. `/etc/ssh` obsahuje také
serverové host keys a konfiguraci sshd. Automaticky přidá i existující domovy
uživatelů UID 1000–65533 mimo `/home` a cíle symlinků v jejich `.ssh`.
Účty a skupiny jsou v `export-metadata/accounts.json` (jméno, UID/GID,
domov, shell, členství); původní `/etc/passwd`, `shadow`, `group`, `gshadow`
a sudoers jsou součástí `/etc`. Práva a číselné vlastnictví jsou v archivu.
Při importu obnov vybrané účty, ne systémové účty nového OS hromadným přepsáním.
Další známý zdroj lze přidat pomocí `--extra /cesta`.
Symlinky zůstávají symlinky; externí cíle a vnořené mounty je potřeba zahrnout
samostatně pomocí `--extra`. Nestandardní data mimo uvedené kořeny nejsou automaticky nalezena.

SQLite soubory rozpoznává podle hlavičky a exportuje online backupem včetně
potvrzených WAL transakcí. Docker ukládá obrazy a inspect konfiguraci, běžným
kontejnerům soubory připojených svazků. Pro rozpoznané PostgreSQL/MySQL/MariaDB
zkusí nativní SQL dump. Export vyžaduje jejich již dostupná oprávnění.
Raw adresáře rozpoznaných databázových serverů vynechá. InfluxDB, Redis,
MongoDB a neúspěšné dumpy zaznamená jako chybějící nativní zálohu.
Neznámé/custom databázové obrazy nelze spolehlivě rozpoznat podle názvu.
Soubory běžících aplikací nejsou transakční snapshot celého systému.
Skript zachovává původní cesty, UID/GID a běžná unixová práva, nikoli ACL/xattrs.

Výsledek: `files.tar.gz` (s `--encrypt` koncovka `.gpg`), `SHA256SUMS`, `STATUS.txt`.
Návratový kód 2 znamená, že archiv vznikl, ale některé operace selhaly;
podrobnosti jsou uvnitř v `export-metadata/report.json`. Nula neznamená
ověřenou aplikační obnovu. Chybějící DB dump je potřeba doplnit před smazáním zdroje.

Kontrola a rozbalení později, v adresáři daného balíku:

```bash
sha256sum -c SHA256SUMS
mkdir -m 700 restored
tar -xzf files.tar.gz -C restored
```

Obnovuj selektivně ze stagingu; nerozbaluj přes kořen nového OS.
Runtime instaluj pod `/opt`, konfiguraci pod `/etc/hanzhub`, data pod
`/var/lib/hanzhub`. SQL dumpy vyžadují import příslušným DB nástrojem,
obrazy `docker load` a služby správné jednotky/config. Automatické spuštění
služeb ani připojení GPIO tento exportér neprovádí.

## Importní skript

Na původní HUB přenes oba soubory vedle sebe: `export-local.py` a
`import-local.py`. Exportér pak uloží importní skript také vedle balíku na SSD.

Na novém OS, z adresáře exportního balíku:

```bash
sudo python3 import-local.py . --apply --root-ssh
```

Importér ověří SHA-256 a rozbalí archiv do nového soukromého adresáře
`/opt/hanzhub/import-*/staging`. Obnoví uživatelské domovy včetně `.ssh`,
vytvoří chybějící běžné uživatele s původním UID/GID, doplní členství
v existujících skupinách. Při kolizi identity skončí před kopírováním.
Obnoví `/opt`, `/usr/local`, `/etc/hanzhub` a `/var/lib/hanzhub`.
Volba `--root-ssh` obnoví i rootovy klientské SSH klíče. Přepsané soubory
odkládá pod `previous-files`. Bez `--apply` provede pouze rozbalení.

Pro jednoho uživatele lze přidat `--user hanz`. `--docker-images` načte
uložené obrazy přes `docker load` (Docker už musí být nainstalovaný).
Hesla účtů, serverové SSH klíče a nastavení nového OS se automaticky nemění.
Původní soubory jsou připravené ve stagingu pro selektivní převzetí.
SQL dumpy, ostatní `/var/lib`, databázové importy, Docker svazky a služby
vyžadují následné aplikační kroky podle `NEXT-STEPS.txt`.
Tento import souborů není automatické zprovoznění všech aplikací.
