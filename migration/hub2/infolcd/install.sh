#!/bin/bash
set -euo pipefail

# Argument is the staged, private InfoLCD tree including the original Studio JPEGs.
source_tree=$(realpath "${1:?Usage: install.sh STAGED_INFOLCD_TREE}")
package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime=/opt/hanzhub/infopanel
config=/etc/hanzhub/infolcd

(cd "$source_tree" && sha256sum --check --quiet "$package/source.sha256")
/usr/bin/python3 -c 'import PIL, evdev, psutil'
test -c /dev/fb0
test -c /dev/input/by-id/usb-WaveShare_WS170120-event-if00

install -d -m 755 "$runtime" "$config"
while read -r _ path; do
    install -D -m 644 "$source_tree/$path" "$runtime/$path"
done < "$package/source.sha256"
install -m 644 "$package/hdmi.py" "$runtime/"
if [[ ! -e "$config/hdmi.json" ]]; then
    install -m 644 "$package/hdmi.json" "$config/"
fi
install -m 644 "$package/hanzhub-infolcd-hdmi.service" /etc/systemd/system/
systemctl daemon-reload
