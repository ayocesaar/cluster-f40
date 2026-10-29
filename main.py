"""Punto de entrada del cluster de instrumentos simulado del Ferrari F40."""

import argparse
import tkinter as tk

from logic.estado import EstadoCluster
from logic.reloj import RelojReal
from ui.tablero import Tablero


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cluster de instrumentos simulado del Ferrari F40")
    parser.add_argument("--salir-tras-ms", type=int, default=None,
                        help="cierra la ventana tras N ms (prueba de humo)")
    args = parser.parse_args(argv)

    raiz = tk.Tk()
    tablero = Tablero(raiz, EstadoCluster(RelojReal()))
    if args.salir_tras_ms is not None:
        raiz.after(args.salir_tras_ms, lambda: (tablero.detener(), raiz.destroy()))
    raiz.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
