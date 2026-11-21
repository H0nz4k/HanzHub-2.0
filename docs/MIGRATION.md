# HanzHub 2.0 — migrační plán a export na externí disk

**Stav:** ZADÁNÍ; žádné formátování ani produkční migrace zatím nebyly provedeny.

## Cíl
Codex s dočasným schváleným SSH přístupem provede kompletní read-only audit původního HUBu, vytvoří reprodukovatelný export vybraných aplikací, konfigurací a dat do **ověřeného externího úložiště**, nástroje `backup.sh`, `verify.sh`, `restore.sh`, `rollback.sh` a otestuje obnovu v izolovaném prostředí. Poté čistý OS na **jiném boot médiu**, selektivní obnova v jednotném standardu `/opt/` a skutečné ověření služeb.

## Povinný STOP před formátováním
Uživatel navrhl „naformátovat ten SSD disk a vše uložit na něj“. Dřívější zpráva z 21. 11. 2026 označuje SSD Patriot jako `ro,norecovery` s cca 213 GB volných. Může obsahovat starší image/zálohy. **Neformátovat zatím nic.** Nejprve vypsat disk model/serial/UUID, celé rozdělení, mounty, původ dat, referencované zálohy a případné chyby disku; potvrdit, který fyzický disk je zamýšlen, zda obsahuje jedinou kopii dat a zda existuje další bezpečná kopie. Formátování je nevratně destruktivní a vyžaduje nové výslovné schválení **konkrétního zařízení po ověření identity**. Pokud disk vykazuje chyby, použít jiné úložiště a neopravovat ho naslepo.

## Fáze 0 — živá read-only inventura
- Host OS/kernel/arch, boot source, USB/SD/SSD, `lsblk -o NAME,PATH,MODEL,SERIAL,SIZE,TRAN,FSTYPE,UUID,MOUNTPOINTS`, `findmnt`, SMART/diagnostika pokud dostupná bez zápisů.
- systemd system/user, timery, Docker images/containers/volumes/Compose, ports and listeners, reverse proxy, local network names.
- Aplikace, skutečná verze zdrojů, závislosti, API/MCP, SSH forwarding, GPIO a aktivní periferie, displeje, USB zařízení.
- Data a konfigurace, záchytné body pro DB, backup/restic stavy, vlastníci adresářů; přesná rizika ztráty.
- Mapovat na `retain / migrate / archive / exclude / unknown`. Rozhodnutí o ponechání neodhadovat.
- Rozlišit živě doloženou informaci od starých GitHub metadat. Nikdy neexportovat tajemství do veřejného repozitáře.

## Fáze 1 — exportní balík
Každá zachovaná aplikace má:
- `manifest.yaml` (id, repo + commit SHA, runtime, dependencies, porty, GPIO, endpoints, user, target dirs, health).
- export kódu/release, konfigurace (privátně), dat a databází konzistentním způsobem; práva, service jednotky a Docker svazky.
- installation/restore plan s deklarativními kroky, očekávanými verzemi, testy a rollbackem.
- export zdrojů pro Henk Studio a grafiku Henka, samostatně Dashboard 2.0 a 7″ HDMI konfiguraci.
- `SHA256SUMS`, obsah/verze prostředí, audit log, čas začátku a dokončení, záznam o výsledku.
- Šifrovaný balík pro citlivá data a klíč odděleně; ne na GitHub.
- Doporučené skripty jsou rozhraní, která má Codex **teprve implementovat**: `backup.sh`, `verify.sh`, `restore.sh --list/--app/--all`, `rollback.sh`.

## Fáze 2 — verifikace
- Hash kontrola celého exportu, kontrola DB dumpek a čitelnosti dat, manifestů a závislostí.
- Reálná testovací obnova na oddělené kartě/VM/testhostu s neprodukčními porty, bez fyzického spínání GPIO; výsledky jednotlivých aplikací doložit.
- Dvě nezávislé kopie důležitých dat, alespoň jedna mimo zařízení, které bude formátováno nebo použito jako boot.
- Nesplněné testy znamenají STOP migrace.

## Fáze 3 — nový OS
- Čistý aktuálně podporovaný OS kompatibilní s RPi5 a používaným hardwarem na **novém/spare boot médiu**; stará SD se nepřepisuje.
- Základní bezpečnost, SSH, storage, síť, Docker/systemd, správné ovladače. Standard: app runtime `/opt/<app>/` nebo `/opt/hanzhub/<component>/`; config `/etc/hanzhub/<app>/`; data `/var/lib/hanzhub/<app>/`.
- Selektivní restore, přemapování portů a HW pouze podle schváleného plánku. Žádné automatické vrácení starého Operations Brokeru, pokud není vybrán.
- Funkční testy každé služby, API, dat, grafů, GPIO, audio, HDMI a externího přístupu. Zaznamenat přesné původní a cílové verze.

## Fáze 4 — převzetí
Dokončeno až po prověření zachovaných aplikací, aktivních timerů, záloh, obnovitelnosti a restartu. Staré boot médium a export ponechat pro návrat.

## Dočasný Codex přístup
- Samostatný omezeně časovaný SSH účet/klíč, explicitní scope a audit. Root eskalace jen v předem schválených operacích. Není nutné povolovat permanentní přístup root přes internet.
- Fáze 0 jen čtecí; neprovádět `mkfs`, `wipefs`, `parted`, `dd`, `fsck` na připojeném FS, restart, `rm -rf` ani nasazování.
- Pro každou destruktivní diskovou operaci připravit **samostatnou** žádost s identitou zařízení, očekávanou ztrátou dat, kopiemi a rollbackem.
