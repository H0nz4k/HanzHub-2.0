"""Serve the existing IoT management UI through the local Dashboard."""
from http.client import HTTPException
from ipaddress import ip_address
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dashboard_iot import COMMAND, command

PREFIX = "/iot-sprava"
ASSETS = {"/", "/iot.html", "/index.html", "/iot.css", "/iot.js", "/ewelink.js",
          "/iot-icon.svg", "/hanzlogo.svg", "/version.json"}
MODULE = r"/api/iot/devices/[a-f0-9]{12}"
ROUTES = {
    "GET": r"/api/iot/(info|devices|candidates|events|ewelink/(status|login|devices))|" +
           MODULE + r"/(state|schedule|presets)",
    "POST": r"/api/iot/(devices|import|ewelink/import)|" + MODULE + r"/(command|schedule)",
    "PUT": MODULE + r"(/presets|/schedule/[a-f0-9]{12})?",
    "DELETE": MODULE + r"(/schedule/[a-f0-9]{12})?",
}


def management(handler):
    def reply(status, message):
        handler.send_content(json.dumps({"error": message}).encode(), "application/json", status)

    method = "GET" if handler.command == "HEAD" else handler.command
    host = handler.headers.get("Host")
    address, port = handler.connection.getsockname()[:2]
    hosts = {f"{address}:{port}"}
    if ip_address(address).is_loopback:
        hosts.add(f"localhost:{port}")
    origins = handler.headers.get_all("Origin") or []
    origin = [f"http://{host}"]
    if (handler.headers.get_all("Host") != [host] or host not in hosts
            or handler.headers.get("Cf-Access-Jwt-Assertion") or not handler.local_data_allowed()
            or (method == "GET" and origins not in ([], origin))
            or (method != "GET" and (origins != origin or
                handler.headers.get("Sec-Fetch-Site") not in (None, "same-origin")))):
        return reply(403, "Správa IoT je dostupná pouze z místního Dashboardu.")

    parsed = urlsplit(handler.path)
    path = parsed.path.removeprefix(PREFIX)
    asset = method == "GET" and path in ASSETS
    if not asset and not re.fullmatch(ROUTES.get(method, r"(?!)"), path):
        return reply(404, "Cesta správy IoT není podporovaná.")
    query = parsed.query
    if not asset and query and not (path.endswith("/state") and query == "fresh=1"
                                    or path == "/api/iot/events" and re.fullmatch(r"id=[a-f0-9]{12}", query)):
        return reply(400, "Neplatný dotaz.")
    if method == "POST" and COMMAND.fullmatch(path):
        return command(handler, path)
    body = None
    if method in ("POST", "PUT"):
        lengths = handler.headers.get_all("Content-Length") or []
        if (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,5}", lengths[0])
                or not 0 < int(lengths[0]) <= 8192 or handler.headers.get_all("Transfer-Encoding")
                or handler.headers.get_content_type() != "application/json"):
            return reply(400, "Neplatný formát požadavku.")
        try:
            handler.connection.settimeout(5)
            body = handler.rfile.read(int(lengths[0]))
            if len(body) != int(lengths[0]) or not isinstance(json.loads(body), dict):
                return reply(400, "Neplatný JSON požadavek.")
        except (OSError, ValueError):
            return reply(400, "Neplatný JSON požadavek.")

    try:
        endpoint = "http://127.0.0.1:4011" + path
        if query and not asset:
            endpoint += "?" + query
        request = Request(endpoint, data=body, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=18) as response:
            payload = response.read(524289)
            status = response.status
            media = response.headers.get("Content-Type", "application/json")
    except HTTPError as error:
        with error:
            return handler.send_content(error.read(8192), "application/json", error.code)
    except (OSError, HTTPException):
        return reply(503, "IoT služba není dostupná.")
    if len(payload) > 524288:
        return reply(502, "Odpověď IoT je příliš velká.")
    if path in ("/iot.js", "/ewelink.js"):
        payload = payload.replace(b"'/api/iot", b"'/iot-sprava/api/iot")
    if path == "/api/iot/info":
        info = json.loads(payload)
        info["dashboard_url"] = "/living-glass/#iot"
        payload = json.dumps(info).encode()
    handler.send_content(payload, media, status)
