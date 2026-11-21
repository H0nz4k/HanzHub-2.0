"""HUB2 console adapter for the unchanged InfoLCD native renderer."""
import fcntl
from functools import partial
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path("/opt/hanzhub/infopanel")
CONFIG = Path("/etc/hanzhub/infolcd/hdmi.json")
SIZE = (1024, 600)
KDSETMODE, KD_TEXT, KD_GRAPHICS = 0x4B3A, 0, 1


def main():
    config = json.loads(CONFIG.read_text())
    if any(config.get(key) is not None for key in
           ("backlight_gpio", "haptic_gpio", "henk_lightning_relay_gpio")):
        raise SystemExit("Physical outputs must be disabled on HUB2 HDMI")
    sys.path.insert(0, str(ROOT / "lcd"))

    # The original clients import urlopen. Limit this deployment to read requests
    # before loading them, including actions against any later restored services.
    upstream = urllib.request.urlopen

    def read_only(url, data=None, *args, **kwargs):
        if data is not None or (isinstance(url, urllib.request.Request)
                                and url.get_method() not in ("GET", "HEAD")):
            raise OSError("HUB2 InfoLCD: čtecí režim")
        return upstream(url, None, *args, **kwargs)

    urllib.request.urlopen = read_only
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
