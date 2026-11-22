"""Exercise the Dashboard write gateway against a disposable fake device."""
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread

import dashboard_iot

PATH = "/api/iot/devices/012345abcdef/command"
calls = []
online = True
matches = True


def simulated(path, body=None):
    calls.append((path, body))
    if body is None:
        return {"state": {"online": online, "power": True, "local_key": "example"}}
    return {"ok": True, "state": {"online": True, "power": not matches}}


class Dashboard(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def local_data_allowed(self):
        return True

    def send_content(self, content, media, status):
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        dashboard_iot.command(self, self.path)


with ThreadingHTTPServer(("127.0.0.1", 0), Dashboard) as server:
    dashboard_iot.relay = simulated
    thread = Thread(target=server.serve_forever)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    origin = "http://" + host

    def post(value, source=origin):
        conn = HTTPConnection(host, timeout=3)
        try:
            conn.request("POST", PATH, json.dumps({"control": "power", "value": value}),
                         {"Origin": source, "Content-Type": "application/json"})
            reply = conn.getresponse()
            return reply.status, json.load(reply)
        finally:
            conn.close()

    try:
        assert post(False, "http://example.invalid")[0] == 403 and not calls
        assert post(0)[0] == 400 and not calls
        code, result = post(True)
        assert code == 200 and len(calls) == 1 and result["state"] == {"online": True, "power": True}
        online = False
        assert post(False)[0] == 409 and len(calls) == 2
        online = True
        assert post(False)[0] == 200 and len(calls) == 4
        matches = False
        assert post(False)[0] == 502 and len(calls) == 6
    finally:
        server.shutdown()
        thread.join()

print("Origin, invalid/offline commands, idempotent read, exact result and no retry passed.")
