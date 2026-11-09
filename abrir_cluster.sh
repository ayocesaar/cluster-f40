#!/usr/bin/env bash
# Abre el cluster F40 en Linux o macOS: bash abrir_cluster.sh
cd "$(dirname "$0")" || exit 1
exec python3 main.py
