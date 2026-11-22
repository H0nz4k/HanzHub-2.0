"""Exercise real ICY framing with a disposable local stream."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from icy_metadata import read_title


class Stream(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        assert self.headers.get("Icy-MetaData") == "1"
        title = self.server.title
        self.send_response(200)
        if title is not None:
            self.send_header("icy-metaint", "8")
        self.end_headers()
        if title is None:
            return
        record = ("StreamTitle='" + title + "';").encode()
        length = (len(record) + 15) // 16
        self.wfile.write(b"audio123" + bytes([length]) + record.ljust(length * 16, b"\0"))


with ThreadingHTTPServer(("127.0.0.1", 0), Stream) as server:
    thread = Thread(target=server.serve_forever)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/stream"
    try:
        for title in ("První skladba", "Druhá skladba", None):
            server.title = title
            assert read_title(url) == title
    finally:
        server.shutdown()
        thread.join()

print("Same-stream title change and missing metadata passed.")
