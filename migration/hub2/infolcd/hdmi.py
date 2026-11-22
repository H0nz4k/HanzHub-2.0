"""HUB2 console adapter for the unchanged InfoLCD native renderer."""
import fcntl
from functools import partial
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import urllib.request

ROOT = Path(__file__).resolve().parent
CONFIG = Path("/etc/hanzhub/infolcd/hdmi.json")
SIZE = (1024, 600)
KDSETMODE, KD_TEXT, KD_GRAPHICS = 0x4B3A, 0, 1


def main():
    config = json.loads(CONFIG.read_text())
    if any(config.get(key) is not None for key in
           ("backlight_gpio", "haptic_gpio", "henk_lightning_relay_gpio")):
        raise SystemExit("Physical outputs must be disabled on HUB2 HDMI")
    sys.path.insert(0, str(ROOT / "lcd"))

    # The HDMI viewer may send only the original internet-radio commands.
    upstream = urllib.request.urlopen

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    radio = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    radio_paths = {
        "/api/radio/play", "/api/radio/stop", "/api/radio/mute", "/api/radio/volume",
    }

    def restricted(url, data=None, *args, **kwargs):
        method = url.get_method() if isinstance(url, urllib.request.Request) else "GET"
        if data is None and method in ("GET", "HEAD"):
            return upstream(url, None, *args, **kwargs)
        if data is None and method == "POST":
            parsed = urlsplit(url.full_url)
            if (parsed.scheme, parsed.netloc) == ("http", "127.0.0.1:4020") and (
                parsed.path in radio_paths and not parsed.query and not parsed.fragment
            ):
                return radio.open(url, None, *args, **kwargs)
        raise OSError("HUB2 InfoLCD: nepovolený síťový povel")

    urllib.request.urlopen = restricted
    import infopanel
    import infopanel_henk_task

    # Keep the original Henk tile and detail reachable when the task feed is
    # unavailable. Live task entry/exit keeps upstream timing and placement.
    prepare = infopanel_henk_task.prepare

    def prepare_with_offline_henk(model):
        task = model.get("henk_task") or {}
        roles = model.get("home_tiles") or []
        if ("bot" in roles and not (model.get("bot") or {}).get("fresh")
                and task.get("phase", "hidden") == "hidden"):
            model = dict(model, henk_task=dict(task, phase="offline", progress=1,
                                             slot=roles.index("bot"), animating=False))
        return prepare(model)

    infopanel_henk_task.prepare = prepare_with_offline_henk
    import infopanel_preview

    directory = Path(config["data_dir"])
    infopanel_preview.StudioPreview = partial(infopanel_preview.StudioPreview, directory)
    calibration_path = directory / "touch-calibration.json"
    if not calibration_path.exists():
        reader = infopanel.TouchReader(config["touch"])
        try:
            description = reader.description
            ranges = description["ranges"]
            if reader.device.name != "WaveShare WS170120" or tuple(map(tuple, ranges)) != ((0, 1024), (0, 600)):
                raise SystemExit("Unexpected HDMI digitizer; manual calibration required")
            calibration = infopanel.Calibration(ranges, SIZE, ((1024, 0, 0), (0, 600, 0)))
            calibration.save(calibration_path, description["fingerprint"], config["rotate"])
        finally:
            reader.close()

    fcntl.ioctl(0, KDSETMODE, KD_GRAPHICS)
    try:
        return infopanel.main(["--config", str(CONFIG), *sys.argv[1:]])
    finally:
        fcntl.ioctl(0, KDSETMODE, KD_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
