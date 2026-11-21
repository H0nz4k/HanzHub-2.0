"""Loopback Dashboard and service status for the HUB2 console."""
import json
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

SERVICES = (
    ("henkstudio", "Henk Studio", 4002, "/#lab", "/studio-model.js", "iot"),
    ("meteo", "HanzMeteo", 5000, "/", "/api/current", "meteo"),
    ("iot", "IoT moduly", 4011, "/", "/api/iot/health", "iot"),
    ("calendar", "Kalendář", 4012, "/calendar.html", "/api/calendar/status", "learning"),
    ("lora", "LoRa", 8085, "/", "/version", "lora"),
    ("radioama", "HanzRadio API", 4014, "/api/v1/presets", "/health", "iot"),
    ("stream", "Stream", 8088, "/", "/status", "stream"),
    ("coinlist", "CoinList", 5001, "/", "/", "coinlist"),
    ("whiteboard", "Whiteboard", 8099, "/", "/api/events/count", "whiteboard"),
    ("predictai", "PredicApp", 8084, "/", "/api/system_health", "learning"),
    ("redcheck", "REDcheck", 4091, "/", "/api/version", "learning"),
    ("grafana", "Grafana · Meteo", 3000, "/d/hub2-meteo", "/api/health", "meteo"),
)


def origin(port):
    return f"http://127.0.0.1:{port}"


def service_link(key, port, path):
    return path if key == "calendar" else origin(port) + path


def health(service):
    key, _, port, _, path, _ = service
    try:
        with urlopen(origin(port) + path, timeout=2) as response:
            return key, {"ok": response.status == 200}
    except (URLError, OSError):
        return key, {"ok": False}


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
            data = {"daily": {"state": "unknown"}, "weekly": {"state": "unknown"},
                    "storage": {"state": "unknown"}}
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
        elif path in ("/", "/index.html"):
            html = Path("index.html").read_text()
            html = html.replace(
                "isLocal ? 'http://' + location.hostname + ':4010' : location.origin",
                "location.origin",
            ).replace(
                "isLocal && s.key === 'iot' ? 'http://192.168.1.3:4011/' : (s.url || s.ping || '')",
                "(s.url || s.ping || '')",
            )
            html = html.replace(
                '<footer class="footer">',
                '<footer class="footer"><a href="/living-glass/">Living Glass</a><span>·</span>',
                1,
            )
            self.send_content(html.encode(), "text/html; charset=utf-8")
            return
        elif path == "/living-glass/app.js":
            script = Path("living-glass/app.js").read_text()
            links = {key: service_link(key, port, link) for key, _, port, link, _, _ in SERVICES}
            local = dict(dashboard="/", settings="/settings.html", henk="/ai-slave.html",
                         studio=links["henkstudio"], iot=links["iot"],
                         meteo=links["meteo"], calendar=links["calendar"])
            script = script.replace("function menu(open)", f"Object.assign(originals, {json.dumps(local)});\nfunction menu(open)", 1)
            self.send_content(script.encode(), "text/javascript; charset=utf-8")
            return
        else:
            super().do_GET()
            return
        self.send_content(json.dumps(data).encode(), "application/json")


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 4001), Dashboard) as server:
        server.serve_forever()
