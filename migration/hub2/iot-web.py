"""Serve IoT locally without starting the device scheduler."""
import sys

sys.path.insert(0, "/opt/hanzhub-iot/iot")
from server import make_server

with make_server(host="127.0.0.1") as server:
    server.serve_forever()
