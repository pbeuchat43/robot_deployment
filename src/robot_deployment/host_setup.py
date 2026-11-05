"""Reviewable account/storage/USB setup for an explicitly selected site."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import shlex


def script(site):
    account = site["runtime_account"]
    paths = [site["storage"]["installation_root"], site["storage"]["data_root"]]
    rules = ("# Managed robot_deployment compatible-device permissions.\n"
             f'SUBSYSTEM=="usb", ENV{{DEVTYPE}}=="usb_device", ATTR{{idVendor}}=="03e7", OWNER="{account}", MODE="0660"\n'
             f'SUBSYSTEM=="usb", ENV{{DEVTYPE}}=="usb_device", ATTR{{idVendor}}=="8086", ATTR{{idProduct}}=="0b5c", OWNER="{account}", MODE="0660"\n')
    return f'''#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
account={shlex.quote(account)}
if ! id "$account" >/dev/null 2>&1; then useradd --create-home --shell /bin/bash "$account"; fi
owner=$(id -u "$account")
group=$(id -gn "$account")
for directory in {shlex.join(paths)}; do
  test ! -L "$directory" || {{ echo "Refusing symlink storage: $directory" >&2; exit 2; }}
  if test -d "$directory" && test "$(stat -c %u "$directory")" != "$owner"; then
    test -z "$(find "$directory" -mindepth 1 -maxdepth 1 -print -quit)" || {{ echo "Refusing nonempty storage owned by another account: $directory" >&2; exit 2; }}
  fi
  install -d -o "$account" -g "$group" -m 0700 "$directory"
done
rule=/etc/udev/rules.d/99-robot-deployment-{account}.rules
expected={shlex.quote(rules)}
if test -e "$rule"; then
  test ! -L "$rule"
  test "$(cat "$rule")" = "${{expected%$'\\n'}}" || {{ echo 'Existing USB rule is not the selected owned content' >&2; exit 2; }}
else
  printf '%s' "$expected" > "$rule"
  chmod 0644 "$rule"
fi
udevadm control --reload-rules
printf '%s\\n' 'Account and storage ready. Replug compatible cameras to apply USB permissions. No firmware was flashed and no workload was started.'
'''
