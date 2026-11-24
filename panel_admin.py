"""Abre el panel de control del cluster F40 (mandos de cabina y atajos de comandos).

Uso: python panel_admin.py [--datos RUTA]
El panel escribe datos/vehiculo.conf; el tablero (main.py) lo lee como siempre.
Con el boton "Abrir tablero" del panel se lanza tambien el cluster."""

import argparse
import tkinter as tk

from panel.ventana import Panel


def main(argv=None):
    parser = argparse.ArgumentParser(description="Panel de control del cluster F40")
    parser.add_argument("--datos", default=None, help="archivo de datos (por defecto el de config/cluster.ini)")
    args = parser.parse_args(argv)
    raiz = tk.Tk()
    Panel(raiz, ruta_datos=args.datos)
    raiz.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
