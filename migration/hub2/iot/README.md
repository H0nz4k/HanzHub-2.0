# IoT stránka na HUB2

Původní Living Glass načítal živé příkazy přes Health gateway. Na HUB2
stará cesta vrací 404 a zapnutí živého režimu skrývalo i novější čtecí
náhradu. Adaptér nyní obsluhuje samostatnou stránku ze stejného původu,
používá skutečný aktivní registr a ponechává IoT backend na loopbacku.

Příkazy jsou omezené na známé ovladače a místní Dashboard se shodným
původem. Před příkazem se čte čerstvý stav. Stejná požadovaná hodnota se
potvrdí čtením, bez dalšího zápisu. Výsledek musí potvrdit skutečný
driver a klient nejistý požadavek neopakuje. Spotřeba se zobrazuje jen z
dostupných měření.

Záplaty pro Dashboard použij s `git apply --unidiff-zero` na ověřené
kopie jeho nynějšího adaptéru. Soubory `dashboard_iot.py`, CSS a JS
instaluj vedle adaptéru. Zálohuj původní soubory a restartuj pouze
Dashboard, pokud nedoplňuješ import panelu.

Pro prověřený původní BOT panel lze do jednotky IoT přidat drop-in
`infrapanel.conf.example` po nahrazení adresy jeho ověřenou IPv4.
Předej výhradně původní TinyTuya zdroj přes systemd credential. Zálohuj
SQLite online a použij existující lokální import. Registrace ani čtení
nestartují plánovač a nemění stav panelu. Výpadek ověření místního klíče
ponechá fyzické ovládání nedostupné.

Při návratu obnov adaptér ze zálohy. Pokud se vrací také import panelu,
odeber jen přidaný drop-in a restartuj IoT. Záloha SQLite je určena pro
obnovu dat. Neobnovuj celou databázi přes novější změny.

Zkouška bez zařízení je v `python3 -B check_iot_gateway.py`.

## Ověření na HUB2

Běží revize `99a1d197da8261edecc6c05aff260cee2ef87f2a`.
Produkční API vrátilo čerstvý zapnutý stav registrované zásuvky eWeLink.
Příkon zařízení neposkytlo. Původní panel BOT byl přidán z prověřené
identity a dostupné konfigurace, ale ověření místního klíče selhalo.
Stávající Tuya projekt při čtení klíče vrátil `28841002`
(vypršelé cloudové předplatné). Panel je v UI nedostupný a jeho ovladače
jsou zablokované.

Chromium při 1440 a 390 px ověřilo zobrazení skutečných dat i úspěšný
simulovaný výsledek povelu přes UI. Test gateway ověřil shodný původ,
odmítnutí neplatné hodnoty a offline zařízení a kontrolu readbacku.
Produkční pokusy s neplatným povelem skončily 403 a 400 před odesláním
do IoT služby. Porovnání s konzistentní zálohou potvrdilo beze změny
původní registraci a počet událostí ovládání. Fyzická zařízení nebyla
přepnuta. Záloha a návrat jsou na HUB2 v root-only adresáři
`/opt/hanzhub/.rollback-hub2-iot.Hn0Sip`.
