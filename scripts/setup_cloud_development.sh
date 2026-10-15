#!/usr/bin/env bash
# Reproduce the tested Debian 13 / Python 3.12 development environment.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv=/workspace/mas-release-venv
tools=/workspace/mas-release-tools
packages=/workspace/mas-system-packages
export PIP_CACHE_DIR=/workspace/mas-release-cache/pip
export UV_CACHE_DIR=/workspace/mas-release-cache/uv
mkdir -p "$tools" "$PIP_CACHE_DIR" "$UV_CACHE_DIR"
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"'
python3 -m venv "$venv"
"$venv/bin/python" -m pip install -c "$repo_root/requirements-development.txt" -e "$repo_root[dev,browser]" uv
"$venv/bin/python" -m pip check

# The managed image provides Chromium. This alias uses that installed executable;
# it does not represent installation of the pinned Playwright browser binary.
chromium_path="$(command -v chromium || command -v google-chrome || true)"
if [[ -z "$chromium_path" ]]; then
    echo 'Install Chromium, or the Playwright-pinned Chromium with its system dependencies.' >&2
    exit 1
fi
ln -sf "$chromium_path" "$tools/google-chrome"

if ! command -v Xvfb >/dev/null || ! command -v xdotool >/dev/null; then
    # No root access is needed: apt authenticates signed package metadata, then
    # extracts tools beneath /workspace instead of changing the system installation.
    . /etc/os-release
    [[ "$ID" == debian && "$VERSION_CODENAME" == trixie && "$(dpkg --print-architecture)" == amd64 ]] || {
        echo 'Install Xvfb and xdotool for this OS; local extraction supports Debian 13 amd64.' >&2
        exit 1
    }
    mkdir -p "$packages/lists/partial" "$packages/cache/archives/partial" "$packages/debs" "$packages/root"
    cat > "$packages/apt.conf" <<EOF
Dir::Etc::parts "-";
Dir::Etc::main "-";
Dir::Etc::sourcelist "$packages/sources.list";
Dir::Etc::sourceparts "-";
Dir::State::lists "$packages/lists";
Dir::Cache "$packages/cache";
EOF
    cat > "$packages/sources.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
EOF
    APT_CONFIG="$packages/apt.conf" apt-get update
    (
        cd "$packages/debs"
        APT_CONFIG="$packages/apt.conf" apt-get download xvfb xdotool libxdo3 libxfont2
        for package_file in ./*.deb; do dpkg-deb --extract "$package_file" "$packages/root"; done
    )
    ln -sf "$packages/root/usr/bin/Xvfb" "$tools/Xvfb"
    cat > "$tools/xdotool" <<EOF
#!/bin/sh
LD_LIBRARY_PATH=$packages/root/usr/lib/x86_64-linux-gnu exec $packages/root/usr/bin/xdotool "\$@"
EOF
    chmod 755 "$tools/xdotool"
fi

image=python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
docker_local=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
"${docker_local[@]}" info --format '{{.ServerVersion}}'
"${docker_local[@]}" pull "$image"
export PATH="$tools:$venv/bin:$PATH"
cd "$repo_root"
python -m mas.cli doctor
echo 'Development dependencies prepared. Run the quality gate separately; setup does not approve a release.'
