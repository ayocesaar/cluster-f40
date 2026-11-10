"""Cambia valores de datos/vehiculo.conf de forma atomica (temporal + renombrado).

Uso:
    python3 tools/escribir_dato.py motor=1 velocidad=120 direccional=izquierda
    python3 tools/escribir_dato.py --sin-validar temp_agua=abc     # para demostrar un error

Por defecto valida cada valor y no escribe nada si alguno es invalido (codigo 2).
Con --sin-validar escribe el texto tal cual, para provocar a proposito los
errores que el lector debe rechazar y registrar."""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sistema import config as configuracion
from sistema.lector import (CLAVES, VALORES_INICIALES, DatoInvalido, convertir, escribir_texto_atomico, formatear,
                            parsear)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Escribe valores en el archivo de datos del cluster")
    parser.add_argument("pares", nargs="+", help="clave=valor")
    parser.add_argument("--archivo", default=None, help="archivo de datos (por defecto el de config/cluster.ini)")
    parser.add_argument("--sin-validar", action="store_true", help="escribir aunque el valor sea invalido")
    args = parser.parse_args(argv)

    cfg = configuracion.cargar()
    ruta = pathlib.Path(args.archivo) if args.archivo else cfg.archivo_datos
    actuales = {}
    if ruta.is_file():
        pares, _ = parsear(ruta.read_text(encoding="utf-8"))
        actuales.update(pares)

    for par in args.pares:
        clave, signo, texto = par.partition("=")
        clave = clave.strip().lower()
        if not signo or clave not in CLAVES:
            print(f"ERROR: '{par}' no es clave=valor de una clave conocida: {', '.join(CLAVES)}", file=sys.stderr)
            return 2
        if not args.sin_validar:
            try:
                convertir(clave, texto.strip(), cfg.rangos)
            except DatoInvalido as error:
                print(f"ERROR: {error.detalle}", file=sys.stderr)
                return 2
        actuales[clave] = texto.strip()

    lineas = ["# Datos de entrada del cluster F40 (clave=valor). Escrito por tools/escribir_dato.py."]
    for clave in CLAVES:
        lineas.append(f"{clave}={actuales.get(clave, formatear(clave, VALORES_INICIALES[clave]))}")
    escribir_texto_atomico(ruta, "\n".join(lineas) + "\n")
    print(f"OK {ruta.name}: " + " ".join(args.pares))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
