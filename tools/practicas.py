"""Corre las practicas de fallas en tiempo simulado y deja la evidencia.

Uso:
    python3 tools/practicas.py                       # las 15 practicas; docs/evidencias/practicas.txt
    python3 tools/practicas.py --practica frenos     # una (se puede repetir)

Cada practica maneja el modelo del panel como una persona (pedales con la misma rapidez del panel
y el embrague en cada cambio) y verifica con una copia del cuadro real lo que el tablero mostraria.
Codigo de salida 0 si todas las practicas aprueban."""

import argparse
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from panel import practicas  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Practicas de fallas automaticas (tiempo simulado)")
    parser.add_argument("--practica", action="append", default=[], choices=list(practicas.CATALOGO))
    parser.add_argument("--salida", default=None)
    args = parser.parse_args(argv)
    claves = args.practica or list(practicas.CATALOGO)
    lineas = ["Practicas de fallas automaticas (panel/practicas.py), en tiempo simulado con pasos de 50 ms", ""]
    aprobadas, inicio = 0, time.perf_counter()
    for clave in claves:
        ejecucion = practicas.correr(clave)
        m = ejecucion.m
        aprobadas += ejecucion.aprobada
        lineas.append(f"{'APROBADA   ' if ejecucion.aprobada else 'NO APROBADA'} {ejecucion.practica.nombre} "
                      f"({m.t:.1f} s simulados): {ejecucion.practica.descripcion}")
        for criterio, ok, medido in m.resultados:
            lineas.append(f"    {'OK ' if ok else 'MAL'} {criterio}{f': {medido}' if medido else ''}")
        warns = sorted(set(m.avisos_del_cuadro()))
        lineas.append(f"    el tablero registro WARN: {', '.join(warns) or 'ninguno'}")
        lineas.append(f"    causas de proteccion vistas: {', '.join(sorted(m.causas)) or 'ninguna'}")
    lineas += ["", f"Resultado: {aprobadas}/{len(claves)} practicas aprobadas "
                   f"({time.perf_counter() - inicio:.1f} s de calculo)"]
    print("\n".join(lineas))
    if not args.practica or args.salida:
        salida = pathlib.Path(args.salida) if args.salida else RAIZ / "docs" / "evidencias" / "practicas.txt"
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return 0 if aprobadas == len(claves) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
