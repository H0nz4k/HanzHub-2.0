"""Generate the HUB2 navigation overlay from the verified Dashboard bundle."""
import hashlib
import sys
from pathlib import Path

source, output = map(Path, sys.argv[1:])
content = source.read_bytes()
if hashlib.sha256(content).hexdigest() != "60fba92e26d0e8dff1ce6e95d3faba45d3d6daf3fc021d0724ea61a50d9e294a":
    raise SystemExit("Unexpected Dashboard bundle. Review this change against the installed release.")
anchor = b"function menu(open)"
overlay = b"""// On HUB2 the independently running apps are available on loopback.
if (['127.0.0.1', 'localhost'].includes(location.hostname) && location.port === '4001') {
  Object.assign(originals, {
    studio: 'http://127.0.0.1:4002/#lab',
    iot: 'http://127.0.0.1:4011/',
    meteo: 'http://127.0.0.1:5000/'
  });
}
"""
with output.open("xb") as destination:
    destination.write(content.replace(anchor, overlay + anchor, 1))
