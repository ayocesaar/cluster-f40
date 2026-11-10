"""Proceso productor de ejemplo: simula un recorrido escribiendo el archivo de datos.

Corre como un proceso aparte del tablero. Cada `--periodo-ms` calcula los
valores del recorrido (encendido, aceleracion, direccional, emergencia, falla de
frenos, baja presion de aceite y apagado) y reescribe el archivo de forma
atomica, mientras el tablero lo lee: es la demostracion de dos actividades
concurrentes que se comunican por un archivo sin lecturas parciales.

Uso:
    python3 tools/simulador.py                       # en bucle hasta Ctrl+C
    python3 tools/simulador.py --duracion-s 30 --archivo datos/vehiculo.conf"""

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sistema import config as configuracion
from sistema.lector import escribir_atomico

DURACION_RECORRIDO_MS = 22000
CURVAS = {
    "velocidad": [(0, 0), (5000, 0), (8000, 120), (11000, 220), (14000, 220), (16500, 140), (18500, 60), (19500, 0), (22000, 0)],
    "rpm": [(0, 0), (2000, 0), (3000, 900), (5000, 900), (6500, 8200), (6600, 5000), (8300, 8100), (8400, 5600),
            (11000, 7600), (11500, 6000), (14000, 6000), (16500, 2500), (18500, 1500), (19400, 900), (19500, 0), (22000, 0)],
    "presion_aceite": [(0, 0), (2000, 0), (3500, 5), (16000, 5), (16600, 0.6), (19500, 0.6), (22000, 0)],
    "temp_agua": [(0, 40), (2000, 40), (8000, 92), (15000, 100), (18000, 116), (19500, 116), (22000, 40)],
    "presion_turbo": [(0, 0), (5000, 0), (6400, 1.6), (6600, 0.4), (8200, 1.7), (8400, 0.5), (10800, 1.55), (11000, 0.8),
                      (14000, 0.7), (15000, 0.2), (19500, 0), (22000, 0)],
}


def interpolar(puntos, t):
    for (t0, v0), (t1, v1) in zip(puntos, puntos[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return puntos[-1][1]


def valores_en(t_ms):
    """Valores del recorrido en el instante t (ms), ya en su tipo y dentro de rango."""
    t = t_ms % DURACION_RECORRIDO_MS
    valores = {clave: round(interpolar(curva, t), 2) for clave, curva in CURVAS.items()}
    valores["rpm"] = int(round(valores["rpm"]))
    valores["motor"] = 2000 <= t < 19500
    valores["direccional"] = "IZQ" if 11500 <= t < 13500 else "OFF"
    valores["luces_altas"] = 7000 <= t < 12500
    valores["emergencia"] = 13000 <= t < 15500
    valores["falla_frenos"] = 14500 <= t < 17000
    return valores


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simula un recorrido escribiendo el archivo de datos")
    parser.add_argument("--archivo", default=None, help="archivo de datos (por defecto el de config/cluster.ini)")
    parser.add_argument("--periodo-ms", type=int, default=100)
    parser.add_argument("--duracion-s", type=float, default=None, help="por defecto, hasta Ctrl+C")
    args = parser.parse_args(argv)

    ruta = pathlib.Path(args.archivo) if args.archivo else configuracion.cargar().archivo_datos
    inicio = time.monotonic()
    escrituras = 0
    try:
        while args.duracion_s is None or time.monotonic() - inicio < args.duracion_s:
            escribir_atomico(ruta, valores_en((time.monotonic() - inicio) * 1000))
            escrituras += 1
            time.sleep(args.periodo_ms / 1000)
    except KeyboardInterrupt:
        pass
    print(f"simulador: {escrituras} escrituras atomicas en {ruta.name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
