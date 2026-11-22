"""Connect the original InfoLCD radio API to Creative T60 over ALSA."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from icy_metadata import Titles

sys.path.insert(0, "/opt/hanzhub-radio")
import radio_service as legacy


titles = Titles()


class AlsaEngine(legacy.Engine):
    def snapshot(self):
        with self.cv:
            state = {**self.status, "stations": self.store.list()}
            station = self.store.get(state["station_id"]) if state["playing"] else None
        state["title"] = None
        index = state["url_index"]
        if station and type(index) is int and 0 <= index < len(station["urls"]):
            state.update(titles.get(station["urls"][index]))
        return state

    def play(self, station_id):
        with self.cv:
            if self.desired_id != station_id and self.store.get(station_id):
                self._interrupt()
            return super().play(station_id)

    def _interrupt(self):
        with self.cv:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()

    def _apply_volume(self, _value):
        self._interrupt()

    def _apply_mute(self, _value):
        self._interrupt()

    def _maintain(self, _station_id):
        pass

    def _try_url(self, station, url, _index):
        with self.cv:
            if self.shutdown_flag or self.desired_id != station["id"]:
                return False
            volume = 0 if self.muted else self.volume / 100
            self.proc = proc = subprocess.Popen(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
                 "-rw_timeout", "6000000", "-i", url, "-vn", "-ac", "2", "-ar", "48000",
                 "-af", f"volume={volume}", "-progress", "pipe:2", "-f", "alsa",
                 "plughw:CARD=T60,DEV=0"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
        playing = threading.Event()

        def read_progress():
            with proc.stderr:
                for line in proc.stderr:
                    value = line.strip().removeprefix("out_time_us=")
                    if line.startswith("out_time_us=") and value.isdecimal() and int(value) > 0:
                        playing.set()

        threading.Thread(target=read_progress, daemon=True).start()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and proc.poll() is None:
            if playing.wait(0.2):
                return proc.poll() is None
        return False


class Handler(legacy.Handler):
    def _cors(self):
        self.send_header("Cache-Control", "no-store")

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path != "/api/radio/title":
            return super().do_GET()
        if self.headers.get("Host") != "127.0.0.1:4020" or self.headers.get("Origin"):
            return self._send(403, {"title": None})
        params = parse_qs(url.query)
        station = legacy.APP.engine.store.get(params.get("station", [""])[0])
        index = params.get("stream", [""])[0]
        if not station or not index.isascii() or not index.isdecimal() or len(index) > 2:
            return self._send(404, {"title": None})
        index = int(index)
        if index >= len(station["urls"]):
            return self._send(404, {"title": None})
        self._send(200, titles.get(station["urls"][index]))

    def do_POST(self):
        if self.headers.get("Host") != "127.0.0.1:4020" or self.headers.get("Origin"):
            self._send(403, {"ok": False})
        elif self.path in {"/api/radio/play", "/api/radio/stop", "/api/radio/volume", "/api/radio/mute"}:
            super().do_POST()
        else:
            self._send(404, {"ok": False})

    def do_OPTIONS(self):
        self._send(405, {"ok": False})

    do_DELETE = do_OPTIONS


if __name__ == "__main__":
    class App:
        engine = AlsaEngine(legacy.Store(Path(os.environ["RADIO_STATE"])))

        def status(self):
            return self.engine.snapshot()

    legacy.APP = App()
    try:
        with ThreadingHTTPServer(("127.0.0.1", 4020), Handler) as server:
            server.serve_forever()
    finally:
        legacy.APP.engine.close()
