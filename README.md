# HanzHub 2.0

> **Domácí vývojová a provozní základna pro software, hardware, experimenty a data.**
>
> HanzHub má být prostředí, ve kterém lze snadno nasazovat projekty, ověřovat nápady a sledovat výsledky. AI je pomocník a komunikační most — nikoliv podmínka provozu.

## Vize

HanzHub je centrální místo pro vlastní SW/HW projekty: aplikace, senzory, automatizaci, prototypy, laboratorní experimenty a jejich provozní data. Má poskytovat **jednoduchý přehled, spolehlivou správu a možnost zadávat úkoly odkudkoliv**, například hlasem přes ChatGPT během cesty autem.

**Měřítkem úspěchu není počet PR, commitů nebo dokončených plánů. Je jím skutečně fungující služba a ověřený výsledek.**

### Co HanzHub 2.0 není

- Není to nový monolit, do kterého se musí přepsat všechny aplikace.
- Není to administrace Henka s přilepeným dashboardem.
- Není to důvod vypínat, přejmenovávat nebo přepisovat existující funkční služby.
- Není to další vlastní implementace funkcí, které už spolehlivě poskytují osvědčené nástroje.

## Části systému

| Část | Odpovědnost |
| --- | --- |
| **HanzHub (hostitel)** | Provoz aplikací, služeb, hardwaru a jejich dat; experimentální/development prostředí. |
| **HanzHub Dashboard** | Hlavní rozcestník, stav systému, přehled aplikací, metriky, grafy a upozornění. |
| **Katalog aplikací a infrastruktury** | Aktuální evidence služeb, portů, URL, nasazených verzí, závislostí a zařízení. |
| **Správa a automatizace** | Bezpečné, auditovatelné nasazování, aktualizace, zálohování, obnova a diagnostika. |
| **Henk** | Osobní AI operátor: komunikace mezi uživatelem, HanzHubem, ChatGPT a externími službami. |
| **Codex / další AI nástroje** | Vývoj, změny kódu, analýzy a složitější zásahy; bez automatického neomezeného přístupu k hostiteli. |

### Dashboard: aplikace a data na prvním místě

Hlavní obrazovka nabízí rozcestník aplikací, zdraví systému, historii měření, grafy, provozní stavy a upozornění. Henk má **malou stavovou dlaždici** a vlastní oddělené rozhraní. Schvalovací a bezpečnostní obrazovky nemají dominovat úvodnímu dashboardu.

### Zachovat grafickou identitu Henka

Při přechodu na HanzHub 2.0 **zachovat existující vizuální identitu Henka**: plamen/avatar, animace a stavy (idle, práce, chyba, úspěch), dosavadní assety, Henk Studio a ověřené varianty zobrazení na Dashboardu a InfoLCD. Neprovádět redesign ani mazání grafických souborů bez samostatného rozhodnutí vlastníka. Henk má mít na hlavním Dashboardu pouze kompaktní stavovou dlaždici; plná grafika, animace a administrace patří do jeho samostatného rozhraní. Před migrací inventarizovat a archivovat původní soubory a ověřit, že nové UI používá stejnou identitu.

### Henk Studio — zachovat a zprovoznit

**Henk Studio je samostatný existující produkt, který se musí převzít i s jeho grafikou, projekty, exporty a aktuálním (částečně nefunkčním) stavem.** Není dovoleno jej tiše odstranit nebo nahradit novým editorem. Nejprve inventura zdrojů, dat, propojení, assetů a konkrétních nefunkčních funkcí; potom cílené opravy a end-to-end test editor → náhled → export → zobrazení. Rozpracované funkce výslovně evidovat, nevydávat je za hotové.

### Prioritní pilot — nasadit grafiku Dashboardu 2 i na InfoLCD

Majitel žádá **skutečné nasazení dříve vytvořeného grafického návrhu Dashboardu 2.0 a jeho odpovídajícího vzhledu na LCD**, k němuž dosud nedošlo. Jde o prioritu pro první viditelný výsledek HanzHubu 2.0, ne o zadání nového redesignu.

- Dohledat již existující návrhy, větve, PR, vizuální assety a design systém Dashboard v2, InfoLCD a Henka; vybrat konkrétní ověřenou výchozí revizi. Nevytvářet grafiku od nuly.
- Před změnou zachytit živý stav 7″ HDMI displeje, kiosku, konfigurace a závislostí. **3,5″ ILI9486 InfoLCD je vyřazen z rozsahu migrace a nového grafického nasazení**; nic na něm nemaž ani fyzicky nevypínej bez samostatného zadání.
- Vytvořit čitelnou variantu jednotného designu pro web Dashboard a **7″ HDMI displej** podle jeho možností. **Neznamená to běh stejné webové stránky na každém displeji.**
- Zachovat stávající stránky aplikací, meteo, IoT, ovládání relé, navigaci, Henkovy grafické stavy a dostupné provozní funkce. Henk na hlavním Dashboardu pouze kompaktně; plné UI odděleně.
- Nasadit po explicitním schválení rizikových produkčních změn se zálohou a rollbackem. Ověřit skutečný vzhled, čitelnost, chování a restart/power-on přímo na displejích, ne jen screenshot v CI.
- Rozlišovat **design připravený**, **aplikace nasazená** a **fyzický displej ověřený**. Bez posledního nelze prohlásit hotovo.

### Henk: most mezi HanzHubem a okolním světem

Henk má znát **skutečně nasazené** aplikace a jejich možnosti: například REDcheck/Redmine, Meteo, IoT, InfoLCD a další služby. Jeho znalost neznamená pouze název projektu — zahrnuje účel, provozní stav, dostupná data, API, oprávněné akce a vazby na další systémy.

Příklady požadavků:

- „Co dnes přibylo v REDchecku?“
- „Co běží na portu 4001?“
- „Je meteostanice v pořádku?“
- „Nasaď ověřenou verzi aplikace na HanzHub.“
- „Ukaž spotřebu infrapanelu za týden a cenu provozu.“

**Znalost ze staré dokumentace není totéž co živě ověřený stav.** Henk musí umět rozlišovat zdroj a čerstvost informací a nesmí vydávat přijetí úkolu za jeho vykonání.

## Inventář: společný zdroj pravdy

Prvním technickým výstupem bude **read-only inventář aktuálního hostitele**, z něhož budou čerpat Dashboard i Henk. Identifikuje zejména:

- aplikace, služby a jejich účel;
- naslouchající porty, protokoly, adresy a reverse-proxy routy;
- systemd jednotky, Docker/Compose kontejnery a jejich stav;
- repozitáře, verze/commity a umístění nasazení (pokud lze spolehlivě zjistit);
- databáze, datová úložiště, hardware a závislosti;
- stav poslední kontroly, timestamp, zdroj a míru jistoty.

Neznámé služby se **nepřiřazují odhadem**. Inventář nesmí veřejně vystavovat interní adresy, tokeny, hesla, soukromé cesty ani citlivá provozní data.

## Centralizovaná správa GPIO — GPIO Check

**Jedno místo pro evidenci, kontrolu a řízené přidělování GPIO pinů napříč všemi aplikacemi a moduly HanzHubu.** Každý pin má jednoznačně známé využití, vlastníka a stav. Žádná aplikace nesmí potichu přepsat konfiguraci jiné aplikace.

- Inventarizace skutečného stavu Raspberry Pi: SoC GPIO (BCM), fyzické piny headeru, GPIO chip/line, funkce ALT, rezervace kernelu i pinů periferií (I²C/SPI/UART), systémové konfigurace, běžící procesy a hardware.
- Společný katalog: pin, označení BCM/fyzické číslo, směr, pull, active-low, výchozí bezpečný stav, vlastník (app/služba), účel, stav obsazení, konflikt, odkaz na konfiguraci, čas posledního ověření a zdroj informace.
- Přehled v Dashboardu: **volné / obsazené / rezervované / konflikt / neznámé**. Změny pouze přes ověřený plán, s upozorněním na konflikty a potvrzením rizikových zásahů.
- Jednotný deklarativní manifest požadavků aplikací; při nasazení preflight kontroly, aby dvě aplikace současně nekonfigurovaly stejnou linku. Ovládání a exkluzivní runtime vlastnictví navázat na existující Linux GPIO rozhraní (libgpiod / gpiochip), nikoliv stavět vlastní kernelový GPIO driver.
- Změna GPIO je **transakční a auditovaná**: záloha, validace, schválení při riziku, bezpečný výchozí stav, restart pouze dotčené služby a rollback. Zakázat bezmyšlenkovité přepínání pinů na živém hardwaru.
- Existující konfigurace, zejména **GPIO22 (aktivní LOW, Henk/InfoLCD relé)**, nejprve zdokumentovat a chránit proti kolizi. Vyřazení 3,5″ displeje z redesignu **neopravňuje odstranit** jeho stávající GPIO konfiguraci bez samostatného rozhodnutí.
- Read-only inventář musí fungovat i bez Henka. Henk získá přes stejné API informaci „Která služba používá GPIO22?“ a může připravit návrh změny, nikoliv neautorizovaně fyzicky spínat relé.

**Hotovo:** ověřená mapa všech GPIO uživatelů na skutečném HUBu, detekce konfliktů napříč dvěma nezávislými aplikacemi, jednotné čitelné UI/API a bezpečně ověřená plánovaná změna bez porušení ostatních komponent.

## Správa: hotové nástroje před vlastním frameworkem

Uvažované nástroje (zatím **kandidáti, nikoliv zvolená nebo nasazená architektura**): Cockpit pro administraci Linuxu; Ansible a Semaphore UI pro opakovatelné operace; případně jiné osvědčené řešení. OpenJarvis lze nezávisle vyhodnotit jako lokální AI vrstvu.

Výběr se provede podle skutečného pilotu a provozních nákladů, nikoliv podle počtu funkcí na papíře.

**Bezpečnostní pravidla:**
- běžné čtení a diagnostika s minimálními oprávněními;
- změny vymezené konkrétní operací a prostředím, s možností schválení;
- žádný trvalý neomezený root přístup pro cloudového agenta;
- záloha a plán obnovy před rizikovými zásahy;
- audit, potvrzení provedení a nezávislé ověření účinku;
- žádné destruktivní operace na disku, databázi či hardwaru bez výslovného souhlasu.

## Zásady vývoje

1. **Existující služby zůstávají v provozu.** Migrace pouze postupně, s ověřenou náhradou a návratovou cestou.
2. **Fungující výsledek před infrastrukturou.** Nenasazujeme pět vrstev, abychom mohli vykreslit jeden graf.
3. **Jedna schopnost, ne adaptér pro každý projekt.** Generické operace se odlišují deklarativním plánem, ne novou implementací brokeru.
4. **AI je volitelná.** Správa, Dashboard a aplikace musí fungovat i při výpadku Henka, ChatGPT nebo internetu.
5. **Nejdřív ověřit, potom hlásit hotovo.** PR, CI či úspěšné naplánování nejsou potvrzením produkčního nasazení.
6. **Jasné hranice odpovědností.** Katalog zjišťuje fakta, správa provádí schválené změny, Henk komunikuje a koordinuje.

## Roadmapa

| Milník | Cíl | Ověřitelný výsledek |
| --- | --- | --- |
| **M0 — Inventura** | Zmapovat skutečný stav bez zásahu do provozu | Seznam aplikací, portů, služeb a závislostí s datem kontroly |
| **M1 — Stabilní správa** | Vybrat a zavést osvědčené nástroje | Jedna bezpečně vykonaná a ověřená údržbová operace |
| **M2 — Katalog** | Sdílená evidence pro Dashboard a Henka | Dotaz na port/službu vrací doložený aktuální stav |
| **M3 — Dashboard 2.0** | Užitečný rozcestník a přehled dat | Nasazený dashboard se skutečnými daty |
| **M4 — Henk jako most** | Komunikace z telefonu/auta přes externí AI | Dotaz a autorizovaný úkol s doloženou odpovědí |
| **M5 — Automatizace** | Opakovatelné nasazování a provozní workflow | Nasazení další aplikace bez nového projektového adaptéru |
| **M6 — Migrace** | Postupné převzetí funkcí | Ověřený přechod bez ztráty služeb či dat |

### První praktické priority

1. Zachytit výchozí stav produkčního HUBu a oddělit fakta od historických odhadů.
2. Zprovoznit inventář portů, služeb a aplikací v režimu čtení.
3. Dokončit konkrétní uživatelský scénář **měření spotřeby infrapanelu, graf a cena za kWh** — s reálnými, uloženými daty.
4. Zvolit jednoduchou a spolehlivou cestu pro budoucí nasazování bez závislosti na Henkovi.

## Organizace GitHubu

Tento repozitář je **zastřešující dokumentace, cílová architektura, integrační kontrakty a koordinace**. Samostatné aplikace si ponechávají vlastní repozitáře, historii a release proces. GitHub Project `HanzHub 2.0` propojuje úkoly napříč repozitáři; netvoří náhradu za jejich zdrojové kódy.

Existující [HanzHub-Control](https://github.com/H0nz4k/HanzHub-Control) zůstává zdrojem historických rozhodnutí a implementací; případné převzetí či odstavení jeho částí vyžaduje inventuru a ověřenou náhradu.

## Stav projektu

**Fáze: založení vize a inventury.** Tento README je cílové zadání, **nikoliv tvrzení, že uvedené komponenty už byly nasazeny**.

---
*HanzHub 2.0 — nejdřív funkční projekty, potom pohodlná automatizace a inteligence.*
