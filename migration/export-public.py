"""Export the reviewed, non-sensitive subset of the live HUB."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

import bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mount", type=Path)
    parser.add_argument("uuid")
    args = parser.parse_args()
    args.recipient = "public"
    os.umask(0o077)
    bundle.check_mount(args.mount, args.uuid)
    dashboard = Path("/opt/HubDastboard")
    plan = {}

    def add(app, source, name):
        manifest = plan.setdefault(app, {"coverage": "partial", "files": []})
        manifest["files"].append(dict(section="runtime", source=str(source),
                                      name=name, method="static"))
        return manifest

    add("dashboard", dashboard / "hanzlogo.svg", "hanzlogo.svg")
    for name in ("style.css", "theme.css", "infolcd.css", "assets/henk-idle.png"):
        manifest = add("dashboard-v2", dashboard / "living-glass" / name, name)
        manifest["release"] = "2.0.0-rc.1"

    for state in ("idle", "working", "success", "error", "blocked", "queued", "testing",
                  "deploying", "waiting_review", "unknown", "preparing", "publishing", "saving"):
        for name in ("animation.webp", "frame-00.png"):
            asset = Path("v0.7.0") / state / name
            add("henk", dashboard / "henk-assets" / asset, str(asset))
    studio = (dashboard / "henk-studio").resolve(strict=True)
    for asset in sorted((studio / "assets").glob("henk-*.webp")):
        add("henk-studio", asset, f"assets/{asset.name}")

    with tempfile.TemporaryDirectory(prefix=".public-input-", dir=args.mount) as work:
        scratch = Path(work)
        for app, container, repository in (
            ("dashboard", "hanzhub_dashboard", "nginx"),
            ("influxdb", "influxdb", "influxdb"),
            ("grafana", "grafana", "grafana/grafana"),
            ("caddy", "caddy", "caddy"),
        ):
            image = subprocess.check_output(
                ["docker", "inspect", "--type", "container", "--format", "{{.Image}}", container],
                text=True,
            ).strip()
            info, = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))
            upstream = next(d for d in info["RepoDigests"] if d.startswith(repository + "@sha256:"))
            archive = scratch / f"{app}.docker.tar"
            subprocess.run(["docker", "image", "save", "--output", str(archive), image], check=True)
            add(app, archive, "image.docker.tar").update(image_id=image, upstream=upstream)
        args.plan = scratch / "plan.json"
        args.plan.write_text(json.dumps(plan))
        bundle.backup(args)


if __name__ == "__main__":
    main()
