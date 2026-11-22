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
