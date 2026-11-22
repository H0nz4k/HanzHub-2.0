# Rádio na HUB2

Rádio v Dashboardu přehrává internetové stanice v prohlížeči. InfoLCD
používá samostatný výstup přes ALSA. Oba klienti čtou ICY název ze
stejného nakonfigurovaného streamu, který přehrávají. Bez čerstvého údaje
dostanou prázdný název. Výpadek metadat nemění přehrávání.

Dashboard zpřístupňuje pouze registr FM/SDR předvoleb. Backend HanzRadio
zůstává na loopbacku. Mutace vyžadují místní spojení a původ Dashboardu.
Rozhraní nepřepojuje tuner ani skenování.

Záplaty aplikuj s `git apply --unidiff-zero` na kopie ověřených souborů
běžícího HUB2 adaptéru. Vedle adaptéru nainstaluj `dashboard-radio.js`
a `dashboard-radio.css`. Vedle skriptu `radio-alsa.py` instaluj
`icy_metadata.py`. Před restartem zaznamenej stav stanice a ztlumení.
Po restartu obnov stejnou stanici a ztlumení. Soubory nastavení a databázi
předvoleb zachovej.

Návrat obnoví původní adaptér Dashboardu a ALSA skript ze zálohy.
Stavové soubory a databáze při návratu zůstávají na místě.
