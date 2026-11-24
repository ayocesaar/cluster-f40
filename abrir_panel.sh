#!/usr/bin/env bash
# Abre el panel de control del cluster F40 (Linux/macOS).
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python panel_admin.py "$@"
fi
exec python3 panel_admin.py "$@"
