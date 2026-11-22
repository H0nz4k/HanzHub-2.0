"""Bounded ICY title probes for configured internet stations."""
from concurrent.futures import ThreadPoolExecutor
import re
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen

TITLE = re.compile(r"(?:^|;)StreamTitle='(.*?)'(?:;|$)", re.IGNORECASE)


def read_title(url):
    request = Request(url, headers={"Icy-MetaData": "1", "User-Agent": "HanzHub Radio"})
    with urlopen(request, timeout=5) as stream:
        interval = int(stream.headers.get("icy-metaint", "0"))
        if not 0 < interval <= 131072 or len(stream.read(interval)) != interval:
            return None
        length = stream.read(1)
        if not length or not length[0]:
            return None
        value = stream.read(length[0] * 16).rstrip(b"\0")
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            text = value.decode("cp1252", errors="replace")
        found = TITLE.search(text)
        title = " ".join(found[1].split())[:200] if found else ""
        return title if title.casefold() not in {"", "none", "null", "-"} else None


class Titles:
    def __init__(self):
        self.lock = Lock()
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.pending = {}
        self.results = {}

    def get(self, url):
        now = monotonic()
        with self.lock:
            future = self.pending.get(url)
            if future is not None and future.done():
                self.results[url] = future.result()
                self.pending.pop(url)
            title, observed = self.results.get(url, (None, 0))
            # Stagger probes and cap outstanding work even if a stream stalls.
            if now - observed >= 8 and url not in self.pending and len(self.pending) < 4:
                self.pending[url] = self.pool.submit(self.probe, url)
        return {"title": title if now - observed < 18 else None}

    @staticmethod
    def probe(url):
        try:
            title = read_title(url)
        except (OSError, ValueError):
            title = None
        return title, monotonic()
