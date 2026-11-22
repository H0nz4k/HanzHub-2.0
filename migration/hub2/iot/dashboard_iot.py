"""Restricted Dashboard gateway to the HUB2 loopback IoT service."""
from http.client import HTTPException
from ipaddress import ip_address
import json
import re
from threading import Lock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

IOT_API = "http://127.0.0.1:4011"
COMMAND = re.compile(r"/api/iot/devices/([a-f0-9]{12})/command")
STATE_KEYS = ("online", "paused", "power", "checked_at", "current_temp_c", "target_temp_c",
              "locked", "timer_minutes", "faults", "error_code", "power_w",
              "energy_today_kwh", "energy_month_kwh", "voltage_v", "current_a")
WRITE_LOCK = Lock()


def public_state(state):
    return {key: state[key] for key in STATE_KEYS if key in state}


def relay(path, body=None):
    request = Request(IOT_API + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=18) as stream:
        return json.load(stream)


def confirmed(state, control, value):
    actual = state.get(control)
    if control == "timer_minutes" and value > 0:
        return type(actual) is int and 0 <= value - actual <= 1
    return type(actual) is type(value) and actual == value


def command(handler, path):
    def reply(status, data):
        handler.send_content(json.dumps(data).encode(), "application/json", status)

    host = handler.headers.get("Host")
    address, port = handler.connection.getsockname()[:2]
    hosts = {f"{address}:{port}"}
    if ip_address(address).is_loopback:
        hosts.add(f"localhost:{port}")
    if (handler.headers.get_all("Host") != [host] or host not in hosts
            or handler.headers.get_all("Origin") != [f"http://{host}"]
            or handler.headers.get("Sec-Fetch-Site") not in (None, "same-origin")
            or not handler.local_data_allowed() or handler.headers.get("Cf-Access-Jwt-Assertion")):
        return reply(403, {"code": "local_dashboard_required"})

    lengths = handler.headers.get_all("Content-Length") or []
    if (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,3}", lengths[0])
            or not 0 < int(lengths[0]) <= 256 or handler.headers.get_all("Transfer-Encoding")
            or handler.headers.get_content_type() != "application/json"):
        return reply(400, {"code": "invalid_command"})
    try:
        handler.connection.settimeout(5)
        data = json.loads(handler.rfile.read(int(lengths[0])))
        if not isinstance(data, dict) or set(data) != {"control", "value"}:
            raise ValueError("invalid command")
        control, value = data["control"], data["value"]
        valid = ((control in ("power", "locked") and type(value) is bool)
                 or (control == "target_temp_c" and type(value) is int and 0 <= value <= 37)
                 or (control == "timer_minutes" and type(value) is int and 0 <= value <= 1440 and value % 60 == 0))
        if not valid:
            raise ValueError("invalid command")
    except (OSError, ValueError):
        return reply(400, {"code": "invalid_command"})

    module = path.removesuffix("/command")
    if not WRITE_LOCK.acquire(blocking=False):
        return reply(409, {"code": "command_busy"})
    try:
        try:
            state = relay(module + "/state?fresh=1")["state"]
            if (state.get("online") is not True
                    or (control == "target_temp_c" and (state.get("locked") is not False or state.get("faults")))):
                return reply(409, {"code": "device_unavailable", "state": public_state(state)})
        except (OSError, HTTPException, ValueError, TypeError, KeyError):
            return reply(503, {"code": "state_unavailable"})

        if type(state.get(control)) is type(value) and state.get(control) == value:
            return reply(200, {"ok": True, "state": public_state(state)})
        try:
            result = relay(path, data)
            state = result["state"]
            if result.get("ok") is True and state.get("online") is True and confirmed(state, control, value):
                return reply(200, {"ok": True, "state": public_state(state)})
        except HTTPError as error:
            error.close()
        except (OSError, HTTPException, ValueError, TypeError, KeyError):
            pass
        return reply(502, {"code": "write_unconfirmed"})
    finally:
        WRITE_LOCK.release()
