"""Serve IoT locally without starting the device scheduler."""
import json
import os
import sys

sys.path.insert(0, "/opt/hanzhub-iot/iot")
from ewelink_driver import Ewelink
from server import make_server


class ManagedEwelink(Ewelink):
    """Read credentials from systemd-opened, root-owned files."""

    def __init__(self, client_fd, token_fd):
        super().__init__()
        self.client_fd = client_fd
        self.token_fd = token_fd
        self.cache = {}

    @staticmethod
    def _contents(fd):
        return os.pread(fd, os.fstat(fd).st_size, 0)

    def read(self, name):
        if name == "client.json":
            return json.loads(self._contents(self.client_fd))
        if name == "token.json":
            # An interrupted append leaves the previous complete token available.
            for line in reversed(self._contents(self.token_fd).splitlines()):
                try:
                    token = json.loads(line)
                except ValueError:
                    continue
                if isinstance(token, dict) and token.get("accessToken"):
                    return token
            return {}
        return self.cache.get(name, {})

    def write(self, name, data):
        if name == "token.json":
            entry = b"\n" + json.dumps(data, separators=(",", ":")).encode() + b"\n"
            if os.write(self.token_fd, entry) != len(entry):
                raise OSError("Incomplete eWeLink token write")
            os.fsync(self.token_fd)
        else:
            self.cache[name] = data


def managed_ewelink():
    if os.environ.get("LISTEN_PID") != str(os.getpid()):
        return None
    names = os.environ.get("LISTEN_FDNAMES", "").split(":")
    if len(names) != int(os.environ.get("LISTEN_FDS", "0")):
        raise RuntimeError("Invalid systemd file descriptor list")
    descriptors = {name: fd for fd, name in enumerate(names, start=3)}
    if not {"ewelink-client", "ewelink-token"} & descriptors.keys():
        return None
    client_fd = descriptors["ewelink-client"]
    token_fd = descriptors["ewelink-token"]
    for fd in (client_fd, token_fd):
        os.set_inheritable(fd, False)
    return ManagedEwelink(client_fd, token_fd)


if __name__ == "__main__":
    with make_server(host="127.0.0.1") as server:
        client = managed_ewelink()
        if client is not None:
            server.manager.ewelink_adapter.client = client
        server.serve_forever()
