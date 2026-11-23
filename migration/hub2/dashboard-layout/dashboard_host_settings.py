"""LAN-only inventory and saved GPIO assignments, without hardware activation."""
import json
from ipaddress import ip_address
from pathlib import Path
import re
import subprocess
from threading import Lock
import time

ROOT = Path("/var/lib/hanzhub/dashboard-settings")
GPIO_FUNCTIONS = {"lightning": "Blesk Henka", "backlight": "Podsvícení InfoLCD", "haptic": "Haptika InfoLCD"}
SAVE_LOCK = Lock()


def listeners():
    result = {}
    try:
        lines = subprocess.check_output(["/usr/bin/ss", "-H", "-ltn"], text=True, timeout=2)
        for line in lines.splitlines():
            address, port = line.split()[3].rsplit(":", 1)
            result.setdefault(int(port), set()).add(address)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return result


def scan_gpio():
    info = subprocess.check_output(["/usr/bin/gpioinfo", "-c", "gpiochip0"], text=True, timeout=3)
    mux = subprocess.check_output(["/usr/bin/pinctrl", "get", "0-27"], text=True, timeout=3)
    rows = {}
    for line in info.splitlines():
        match = re.match(r'\s*line\s+(\d+):\s+"[^"]+"\s+(input|output)(.*)', line)
        if match and int(match[1]) < 28:
            rows[int(match[1])] = {"pin": int(match[1]), "direction": match[2],
                                   "consumer": re.search(r'consumer="([^"]+)"', line)[1]
                                   if 'consumer="' in line else None}
    for line in mux.splitlines():
        match = re.match(r'\s*(\d+):\s+(\w+).*//.*=\s*(.*)', line)
        if match and int(match[1]) in rows:
            rows[int(match[1])].update(mode=match[2], label=match[3])
    if len(rows) != 28 or any("mode" not in row for row in rows.values()):
        raise ValueError("Incomplete GPIO inventory")
    write(ROOT / "gpio-inventory.json", {"observed": time.time(), "lines": list(rows.values())})


def write(path, data):
    temp = path.with_suffix(".next")
    temp.write_text(json.dumps(data))
    temp.chmod(0o600)
    temp.replace(path)


def gpio():
    try:
        data = json.loads((ROOT / "gpio-inventory.json").read_bytes())
        if not 0 <= time.time() - data["observed"] < 120:
            raise ValueError("stale")
        lines = data["lines"]
        for line in lines:
            line["available"] = (line["pin"] >= 2 and line["mode"] in ("no", "ip")
                                 and line["direction"] == "input" and not line["consumer"])
    except (OSError, KeyError, TypeError, ValueError):
        lines = []
    try:
        saved = json.loads((ROOT / "gpio-assignments.json").read_bytes())
        if not isinstance(saved, dict):
            raise ValueError("invalid assignments")
    except (OSError, ValueError):
        saved = {}
    return {"lines": lines, "assignments": saved, "functions": GPIO_FUNCTIONS}


def settings(handler, services):
    def reply(status, body):
        handler.send_content(json.dumps(body).encode(), "application/json", status)
    address, port = handler.connection.getsockname()[:2]
    host = handler.headers.get("Host")
    hosts = {f"{address}:{port}"}
    if ip_address(address).is_loopback:
        hosts.add(f"localhost:{port}")
    origins = handler.headers.get_all("Origin") or []
    same_origin = origins == [f"http://{host}"]
    write_request = handler.command == "POST"
    if (handler.headers.get_all("Host") != [host] or host not in hosts or not handler.local_data_allowed()
            or handler.headers.get("Cf-Access-Jwt-Assertion")
            or (origins and not same_origin)
            or (write_request and (not same_origin or handler.headers.get("Sec-Fetch-Site") not in (None, "same-origin")))):
        return reply(403, {"error": "Nastavení je dostupné pouze v místní síti."})
    if not write_request:
        actual = listeners()
        ports = [(name, p, p in actual, any(ip not in {"127.0.0.1","[::1]","::1"} for ip in actual.get(p, ())))
                 for _, name, p, *_ in services]
        ports += [(name, p, p in actual, any(ip not in {"127.0.0.1","[::1]","::1"} for ip in actual.get(p, ())))
                  for name, p in (("Dashboard",4001),("HubAgent",4088),("Přehrávání rádia InfoLCD",4020),("InfluxDB",8086))]
        return reply(200, {"ports": ports, "gpio": gpio()})
    lengths = handler.headers.get_all("Content-Length") or []
    if (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,3}", lengths[0])
            or not 0 < int(lengths[0]) <= 256 or handler.headers.get_all("Transfer-Encoding")
            or handler.headers.get_content_type() != "application/json"):
        return reply(400, {"error": "Neplatné nastavení."})
    try:
        handler.connection.settimeout(5)
        data = json.loads(handler.rfile.read(int(lengths[0])))
        if not isinstance(data, dict) or set(data) != {"function","pin"}:
            raise ValueError
        function, pin = data["function"], data["pin"]
        if not isinstance(function,str) or function not in GPIO_FUNCTIONS or (pin is not None and type(pin) is not int):
            raise ValueError
    except (OSError, ValueError):
        return reply(400, {"error": "Neplatné nastavení."})
    with SAVE_LOCK:
        snapshot = gpio()
        assigned = snapshot["assignments"]
        if pin is None:
            assigned.pop(function,None)
        elif (not any(line["pin"] == pin and line["available"] for line in snapshot["lines"])
              or any(other != function and value == pin for other,value in assigned.items())):
            return reply(409, {"error": "Pin je obsazený, rezervovaný nebo stav nelze ověřit."})
        else:
            assigned[function] = pin
        try:
            write(ROOT / "gpio-assignments.json", assigned)
        except OSError:
            return reply(503, {"error": "Přiřazení se nepodařilo uložit."})
    return reply(200, {"assignments": assigned})


if __name__ == "__main__":
    scan_gpio()
