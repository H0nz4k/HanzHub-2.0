"""Check the native HDMI layout and hit map without framebuffer or GPIO access."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

from infopanel_henk_task import grid, prepare
from infopanel_ui import render


def main():
    cells = grid(12)
    assert len({x for x, _, _, _ in cells}) == 4
    assert len({y for _, y, _, _ in cells}) == 3
    assert all(0 <= x < r <= 1024 and 0 <= y < b <= 600 for x, y, r, b in cells)

    modules = [f"{i:012x}" for i in range(1, 8)]
    roles = ["meteo", "heater", "plug", "radio", "calendar", "bot"]
    model = {
        "home_tiles": roles + ["iot:" + uid for uid in modules],
        "display_devices": {"iot:" + uid: {"id": uid, "name": "Test"} for uid in modules},
        "henk_task": {"phase": "offline", "slot": 5, "progress": 1},
        "bot": {"status": "OFFLINE"},
    }
    _, hits = render("home", prepare(model), size=(1024, 600))
    assert next(h.rect for h in hits if h.action == ("page", "bot")) == cells[5]
    on_first_page = [h.rect for h in hits if h.action[0] == "display_device"]
    assert on_first_page == cells[6:]
    assert any(h.action == ("home_page", 1) for h in hits)
    assert not any(h.action[0] == "presence" for h in hits)

    _, hits = render("home", prepare(dict(model, home_page=1)), size=(1024, 600))
    assert [h.rect for h in hits if h.action[0] == "display_device"] == cells[:1]
    assert any(h.action == ("home_page", 0) for h in hits)

    for page in (*roles, "system"):
        if page not in ("home", "bot"):
            _, detail = render(page, model, size=(1024, 600))
            assert any(h.action == ("page", "home") for h in detail)
    print("HDMI: 12 native slots, Henk hitbox, next page, module return and disabled switch")


if __name__ == "__main__":
    main()
