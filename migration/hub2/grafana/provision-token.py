"""Render Grafana's local provisioning file using a bucket-scoped Influx token."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = "http://127.0.0.1:8086/api/v2/"
DESCRIPTION = "HUB2 Grafana Meteo read-only"
TOKEN_FILE = Path("/opt/meteo3/secrets/influx_token")
DESTINATION = Path("/etc/hanzhub/grafana/datasource.yml")


def request(path, token, data=None):
    headers = {"Authorization": f"Token {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    with urlopen(Request(ROOT + path, data, headers), timeout=15) as response:
        return json.load(response)


def main():
    template = Path(__file__).with_name("datasource.yml").read_text()
    if template.count("__INFLUX_READ_TOKEN__") != 1:
        raise SystemExit("Missing or ambiguous datasource token placeholder")
    admin = TOKEN_FILE.read_text().strip()
    buckets = request("buckets?name=meteo&org=vysilac_v3", admin)["buckets"]
    if len(buckets) != 1:
        raise SystemExit("Expected exactly one Meteo bucket")
    bucket = buckets[0]
    permission = {"action": "read", "resource": {"type": "buckets", "id": bucket["id"]}}
    authorizations = request("authorizations?orgID=" + bucket["orgID"], admin)["authorizations"]
    matches = [
        item for item in authorizations
        if item["description"] == DESCRIPTION and item["status"] == "active"
    ]
    if len(matches) > 1:
        raise SystemExit("Multiple active Grafana authorizations have the provisioning label")
    if matches:
        granted = matches[0]["permissions"]
        if len(granted) != 1 or any(granted[0]["resource"].get(k) != v for k, v in
                                    permission["resource"].items()) or granted[0]["action"] != "read":
            raise SystemExit("Existing Grafana authorization does not match expected scope")
        token = matches[0]["token"]
    else:
        token = request("authorizations", admin, {
            "orgID": bucket["orgID"], "description": DESCRIPTION, "permissions": [permission]
        })["token"]
    if not token or token == admin:
        raise SystemExit("A separate Grafana read token is required")

    temporary = DESTINATION.with_suffix(".tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400), "w") as stream:
        stream.write(template.replace("__INFLUX_READ_TOKEN__", json.dumps(token)))
        os.fchown(stream.fileno(), 472, 0)
    os.replace(temporary, DESTINATION)
    print("Provisioned Grafana datasource with read access only to Meteo")


if __name__ == "__main__":
    main()
