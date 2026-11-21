"""Serve the restored Calendar API on loopback for local validation."""
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import ssl
import sys
from threading import Thread

sys.path.insert(0, "/opt/hanzhub-calendar")
import server as calendar

calendar.DATA = Path("/var/lib/hanzhub/calendar")
credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.minimum_version = ssl.TLSVersion.TLSv1_2
tls.load_cert_chain(credentials / "server.crt", credentials / "server.key")

with (
    ThreadingHTTPServer(("127.0.0.1", calendar.HTTP_PORT), calendar.Handler) as http,
    ThreadingHTTPServer(("127.0.0.1", calendar.HTTPS_PORT), calendar.Handler) as https,
):
    https.socket = tls.wrap_socket(https.socket, server_side=True)
    Thread(target=http.serve_forever, daemon=True).start()
    https.serve_forever()
