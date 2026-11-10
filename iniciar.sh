#!/usr/bin/env bash
# Arranque reproducible del cluster F40 (Linux/macOS).
#   ./iniciar.sh             lee los valores de datos/vehiculo.conf (modo normal)
#   ./iniciar.sh --manual    usa los controles de la ventana
# Eventos en logs/eventos.log y errores en logs/errores.log.
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python main.py "$@"
fi
exec python3 main.py "$@"
