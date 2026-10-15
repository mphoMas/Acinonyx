#!/usr/bin/env bash
# Fresh pilot host preparation only. Does not fetch secrets, enable a service,
# approve work, dispatch workers or deploy an application image.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates curl docker.io git python3 python3-venv \
    bubblewrap xvfb xdotool openssl
systemctl enable --now docker

disk=/dev/disk/by-id/google-mas-core-data
test -b "$disk"
if filesystem="$(blkid -s TYPE -o value "$disk")"; then
    [[ "$filesystem" == ext4 ]] || { echo 'Existing data disk must use ext4; refusing to format.' >&2; exit 1; }
else
    result=$?
    [[ "$result" == 2 ]] || exit "$result"
    signatures="$(wipefs --no-act --noheadings --output TYPE "$disk")"
    [[ -z "$signatures" ]] || { echo 'Unrecognized disk signatures; refusing to format.' >&2; exit 1; }
    mkfs.ext4 -L mas-core-state "$disk"
fi
mkdir -p /var/lib/mas-core
if mountpoint -q /var/lib/mas-core; then
    [[ "$(findmnt -n -o UUID /var/lib/mas-core)" == "$(blkid -s UUID -o value "$disk")" ]]
else
    mount -t ext4 "$disk" /var/lib/mas-core
fi
disk_uuid="$(blkid -s UUID -o value "$disk")"
if ! grep -Fq "UUID=$disk_uuid /var/lib/mas-core " /etc/fstab; then
    printf 'UUID=%s /var/lib/mas-core ext4 defaults 0 2\n' "$disk_uuid" >> /etc/fstab
fi
if ! id mas-core >/dev/null 2>&1; then
    useradd --system --uid 10001 --home-dir /var/lib/mas-core --shell /usr/sbin/nologin mas-core
fi
[[ "$(id -u mas-core)" == 10001 ]]
install -d -o mas-core -g mas-core -m 0700 \
    /var/lib/mas-core/private /var/lib/mas-core/swarm /var/lib/mas-core/workspace
install -d -o root -g root -m 0700 /etc/mas-core

cat > /etc/systemd/system/mas-core-dashboard.service <<'EOF'
[Unit]
Description=MAS-Core staged private pilot dashboard
Requires=docker.service
After=docker.service network-online.target
RequiresMountsFor=/var/lib/mas-core
ConditionPathExists=/etc/mas-core/runtime.env

[Service]
EnvironmentFile=/etc/mas-core/runtime.env
ExecStartPre=/usr/bin/docker image inspect ${MAS_RUNTIME_IMAGE}
ExecStartPre=-/usr/bin/docker rm --force mas-core-dashboard
ExecStart=/usr/bin/docker run --rm --name mas-core-dashboard --pull=never --read-only --cap-drop=ALL --security-opt=no-new-privileges --memory=2g --cpus=1 --pids-limit=256 --tmpfs=/tmp:rw,nosuid,nodev,size=256m --publish=127.0.0.1:8080:8080 --mount=type=bind,src=/var/lib/mas-core/workspace,dst=/app/workspace --env=MAS_ENABLE_LIVE_DISPATCH=false --env=MAS_GIT_QUEUE_AUTOSYNC=false --env=MAS_SANDBOX_PYTHON=true --env=MAS_TOOL_ACL=true ${MAS_RUNTIME_IMAGE}
ExecStop=/usr/bin/docker stop --time=20 mas-core-dashboard
Restart=on-failure
RestartSec=5
TimeoutStopSec=40

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
echo 'Host prepared. No application service enabled; image and admission remain operator-controlled.'
