"""Loopback Dashboard and service status for the HUB2 console."""
import json
import re
from html import escape
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

try:
    from backup_status import backup_status
except ModuleNotFoundError as error:
    if error.name != "backup_status":
        raise

    def backup_status():
        return {key: {"state": "unknown"} for key in ("daily", "weekly", "storage")}

SERVICES = (
    ("redcheck", "REDcheck", 4091, "/", "/api/version", "learning"),
    ("henkstudio", "Henk Studio", 4002, "/#lab", "/studio-model.js", "iot"),
    ("meteo", "HanzMeteo", 5000, "/", "/api/current", "meteo"),
    ("iot", "IoT moduly", 4011, "/", "/api/iot/health", "iot"),
    ("calendar", "Kalendář", 4012, "/calendar.html", "/api/calendar/status", "learning"),
    ("lora", "LoRa", 8085, "/", "/version", "lora"),
    ("radioama", "Rádio", 4014, "/", "/health", "iot"),
    ("stream", "Stream", 8088, "/", "/status", "stream"),
    ("coinlist", "CoinList", 5001, "/", "/", "coinlist"),
    ("whiteboard", "Whiteboard", 8099, "/", "/api/events/count", "whiteboard"),
    ("predictai", "PredicApp", 8084, "/", "/api/system_health", "learning"),
    ("grafana", "Grafana · Meteo", 3000, "/d/hub2-meteo", "/api/health", "meteo"),
)


def origin(port):
    return f"http://127.0.0.1:{port}"


def service_link(key, port, path):
    return {"calendar": "/calendar.html", "radioama": "/living-glass/#radio"}.get(key, origin(port) + path)


def health(service):
    key, _, port, _, path, _ = service
    try:
        with urlopen(origin(port) + path, timeout=2) as response:
            return key, {"ok": response.status == 200}
    except (URLError, OSError):
        return key, {"ok": False}


RADIO_PRESETS = Path("/etc/hanzhub/radio/stations.json")
DEFAULT_PRESETS = Path(__file__).with_name("radio-stations.json")
UI_RELEASE = "abd6f63f7cb4deb2ccd7bebf8095b2d2416332cd"
SYMBOLS = {
    "henkstudio": "sliders", "meteo": "sun", "iot": "plug",
    "calendar": "calendar", "radioama": "radio", "redcheck": "check",
    "grafana": "sun", "stream": "play", "lora": "wifi",
}
DESCRIPTIONS = {
    "henkstudio": "Reakce, animace a vzhled InfoLCD.",
    "redcheck": "Požadavky v Redmine a přehled Helpdesku.",
    "radioama": "Internetové stanice a předvolby přijímače.",
}
RADIO_VIEW = """
<section class="view" id="view-radio" aria-labelledby="heading-radio" hidden>
  <div class="pagehead"><h1 id="heading-radio">Rádio<span class="mint">.</span></h1>
    <a class="button" href="http://127.0.0.1:4014/">FM a SDR předvolby</a></div>
  <article class="card panel"><h2>Internetové rádio</h2>
    <div class="feature-toolbar"><label for="radio-station">Stanice</label>
      <select id="radio-station" disabled></select>
      <button class="button primary" id="radio-play" disabled>Přehrát</button>
      <button class="button" id="radio-stop" disabled>Zastavit</button></div>
    <audio id="radio-audio" controls preload="none" aria-label="Přehrávač rádia"></audio>
    <p id="radio-status" class="muted" role="status">Načítám stanice…</p>
  </article>
</section>
"""


def living_glass_home():
    html = Path("living-glass/index.html").read_text()
    cards = []
    for key, name, port, path, _, _ in SERVICES:
        url = "#radio" if key == "radioama" else escape(service_link(key, port, path))
        description = DESCRIPTIONS.get(key)
        cards.append(
            f'<a class="card service" data-service="{key}" href="{url}">'
            f'<span class="tile-icon"><svg><use href="#{SYMBOLS.get(key, "grid")}"/></svg></span>'
            '<svg class="service-arrow"><use href="#arrow"/></svg>'
            f'<h3>{escape(name)}</h3>'
            + (f'<p>{escape(description)}</p>' if description else "")
            + '<span class="badge neutral" data-service-status>Stav se načítá</span></a>'
        )
    html, count = re.subn(
        r'(<div class="service-grid"[^>]*>).*?(</div>)',
        lambda match: match[1] + "".join(cards) + match[2], html, count=1, flags=re.S,
    )
    if count != 1:
        raise ValueError("Living Glass service grid is missing")
    html = html.replace(
        '<a href="#calendar" class="navlink" data-page="calendar">',
        '<a href="#radio" class="navlink" data-page="radio">'
        '<svg><use href="#radio"/></svg>Rádio</a>'
        '<a href="#calendar" class="navlink" data-page="calendar">', 1,
    )
    for original, local in {
        "http://192.168.1.3:4001/index.html": "/living-glass/",
        "http://192.168.1.3:4001/calendar.html": "/calendar.html",
        "https://meteo.hanzhub.cz/": origin(5000) + "/",
        "Ukázková data a ovládání. Tento návrh není připojený k HUBu.":
            "Dlaždice a rádio jsou živé. Sekce označené jako ukázka mají odkaz na původní aplikaci.",
    }.items():
        html = html.replace(original, local)
    return html.replace('</head>', '<link rel="icon" href="/favicon.svg"></head>', 1).replace(
        '<footer class="footer">', RADIO_VIEW + '<footer class="footer">', 1,
    ).replace("</body>", '<script src="/dashboard-local.js"></script></body>', 1)


class Dashboard(SimpleHTTPRequestHandler):
    def send_content(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.headers.get("Host") not in ("127.0.0.1:4001", "localhost:4001"):
            self.send_error(400)
            return
        path = urlsplit(self.path).path
        if path == "/api/services":
            data = {"services": [
                {"key": key, "name": name, "url": service_link(key, port, link),
                 "icon": f"/icons/{icon}.svg", "color": "#62c7ad"}
                for key, name, port, link, _, icon in SERVICES
            ]}
        elif path == "/api/health":
            with ThreadPoolExecutor() as pool:
                data = dict(pool.map(health, SERVICES))
        elif path == "/api/backup/status":
            data = backup_status()
        elif path in ("/api/calendar/status", "/api/calendar/calendars", "/api/calendar/events"):
            query = urlsplit(self.path).query
            try:
                with urlopen(origin(4012) + path + ("?" + query if query else ""), timeout=15) as response:
                    self.send_content(response.read(), "application/json", response.status)
            except HTTPError as error:
                with error:
                    self.send_content(error.read(), "application/json", error.code)
            except (URLError, OSError):
                self.send_content(b'{"error":"Calendar API unavailable"}', "application/json", 502)
            return
        elif path == "/iot.html":
            self.send_response(302)
            self.send_header("Location", origin(4011) + "/")
            self.end_headers()
            return
        elif path in ("/", "/index.html", "/radio.html"):
            self.send_response(302)
            self.send_header("Location", "/living-glass/#radio" if path == "/radio.html" else "/living-glass/")
            self.end_headers()
            return
        elif path in ("/living-glass/", "/living-glass/index.html"):
            self.send_content(living_glass_home().encode(), "text/html; charset=utf-8")
            return
        elif path == "/living-glass/app.js":
            script = Path("living-glass/app.js").read_text()
            links = {key: service_link(key, port, link) for key, _, port, link, _, _ in SERVICES}
            local = dict(dashboard="/living-glass/", settings="/settings.html", henk="/ai-slave.html",
                         studio=links["henkstudio"], iot=links["iot"], meteo=links["meteo"],
                         calendar=links["calendar"], radio=origin(4014) + "/")
            script = script.replace(
                "function menu(open)",
                f"Object.assign(originals, {json.dumps(local)});\n"
                "names.radio = 'Rádio';\nfunction menu(open)",
                1,
            )
            script, count = re.subn(
                r"function renderDashboard\(\)\{.*?\n\}",
                "function renderDashboard() {}",
                script, count=1, flags=re.S,
            )
            if count != 1:
                raise ValueError("Living Glass overview renderer is missing")
            self.send_content(script.encode(), "text/javascript; charset=utf-8")
            return
        elif path == "/dashboard-local.js":
            script = Path(__file__).with_name("dashboard-local.js").read_bytes()
            self.send_content(script, "text/javascript; charset=utf-8")
            return
        elif path == "/api/radio/stations":
            try:
                presets = RADIO_PRESETS if RADIO_PRESETS.is_file() else DEFAULT_PRESETS
                data = json.loads(presets.read_text())
            except (OSError, ValueError):
                data = {"stations": []}
        elif path == "/api/dashboard/devices":
            try:
                with urlopen(origin(4011) + "/api/iot/devices", timeout=3) as response:
                    modules = json.load(response)["devices"]
                data = {"devices": [
                    {"name": item["name"], "room": item.get("room"), "online": (item.get("state") or {}).get("online")}
                    for item in modules[:3]
                ]}
            except (OSError, ValueError, KeyError):
                data = {"devices": None}
        elif path == "/api/dashboard/version":
            data = {"living_glass_source": UI_RELEASE}
        else:
            super().do_GET()
            return
        self.send_content(json.dumps(data).encode(), "application/json")


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 4001), Dashboard) as server:
        server.serve_forever()
