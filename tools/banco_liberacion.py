"""Banco de liberacion de produccion del F40 simulado (panel/liberacion.py) desde la terminal.

Uso:
    python3 tools/banco_liberacion.py                          # unidad sin fallas
    python3 tools/banco_liberacion.py --falla frenos           # con una o varias fallas inyectadas
    python3 tools/banco_liberacion.py --evidencia              # unidad sana y cada falla por separado

Codigo de salida: 0 si la unidad es APTA (o, con --evidencia, si el banco distingue: la unidad
sana es APTA y cada unidad con una falla es RECHAZADA); 1 en otro caso. Con --evidencia el
reporte se guarda en docs/evidencias/banco_liberacion.txt (o en --salida)."""

import argparse
import datetime
import pathlib
import platform
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from panel import liberacion  # noqa: E402


def _bloque(titulo, resultados):
    lineas = [f"Unidad: {titulo}"]
    for r in resultados:
        lineas.append(f"  {r.clave} {'APROBADA ' if r.aprobado else 'RECHAZADA'} {r.nombre}  [{r.norma}]")
        lineas.append(f"       criterio: {r.criterio}")
        lineas.append(f"       medido:   {r.medido}")
    lineas.append(f"  DICTAMEN: {liberacion.dictamen(resultados)}")
    return lineas


def main(argv=None):
    parser = argparse.ArgumentParser(description="Banco de liberacion de produccion (pruebas de la epoca)")
    parser.add_argument("--falla", action="append", default=[], choices=liberacion.FALLAS,
                        help="falla inyectada en la unidad (se puede repetir)")
    parser.add_argument("--evidencia", action="store_true", help="unidad sana y cada falla por separado")
    parser.add_argument("--salida", default=None, help="archivo del reporte con --evidencia")
    args = parser.parse_args(argv)

    inicio = time.perf_counter()
    encabezado = ["BANCO DE LIBERACION DE PRODUCCION - Ferrari F40 (1987), cluster simulado",
                  f"Fecha: {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}  "
                  f"Python {platform.python_version()}  {platform.system()}",
                  "Normas: UN R13-H anexo 3 y Directiva 71/320/CEE de 1986 (frenado), UN R39 y Directiva "
                  "75/443/CEE (velocimetro), ciclo ECE-15 con las tolerancias de UN R84; ver "
                  "docs/realismo_y_liberacion.md.", ""]
    if not args.evidencia:
        fallas = {nombre: True for nombre in args.falla}
        resultados = liberacion.ejecutar_banco(fallas)
        print("\n".join(encabezado + _bloque(", ".join(args.falla) or "sin fallas", resultados)))
        return 0 if all(r.aprobado for r in resultados) else 1

    lineas, matriz, distingue = list(encabezado), [], True
    for falla in (None, *liberacion.FALLAS):
        resultados = liberacion.ejecutar_banco({falla: True} if falla else {})
        apto = all(r.aprobado for r in resultados)
        distingue = distingue and (apto if falla is None else not apto)
        lineas += _bloque(falla or "sin fallas", resultados) + [""]
        matriz.append((falla or "sin fallas", [r.clave for r in resultados if not r.aprobado],
                       liberacion.dictamen(resultados)))
    lineas += ["MATRIZ: falla inyectada -> pruebas que la detectan -> dictamen"]
    lineas += [f"  {falla:<20} {', '.join(detectan) or '-':<16} {texto}" for falla, detectan, texto in matriz]
    lineas += ["", f"Resultado: {'el banco distingue' if distingue else 'EL BANCO NO DISTINGUE'}: la unidad sana "
               f"es APTA y cada falla es RECHAZADA ({time.perf_counter() - inicio:.1f} s de simulacion acelerada)."]
    salida = pathlib.Path(args.salida) if args.salida else RAIZ / "docs" / "evidencias" / "banco_liberacion.txt"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[-len(matriz) - 3:]))
    print(f"Reporte: {salida}")
    return 0 if distingue else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
