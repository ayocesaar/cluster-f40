"""Consumo normalizado del modelo del F40 contra la cifra publicada del fabricante.

Uso:
    python3 tools/consumo.py                 # deja docs/evidencias/consumo.txt
    python3 tools/consumo.py --salida x.txt

Corre sobre el modelo del panel las tres pruebas de consumo de UN R84 (ciclo urbano de 4 ciclos
ECE-15 desde frio, 90 y 120 km/h constantes) y compara con el consumo del fabricante que publica
ADAC (ciudad 18.4, 90 km/h 8.6 y 120 km/h 10.3 L/100 km). El modelo se acepta a +-10 % (criterio
del equipo). Codigo de salida 0 si las tres pruebas quedan dentro."""

import argparse
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from panel import fisica, liberacion  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Consumo normalizado del modelo contra el dato publicado")
    parser.add_argument("--salida", default=None)
    args = parser.parse_args(argv)
    inicio = time.perf_counter()
    resultados = liberacion.consumo_normalizado()
    lineas = ["CONSUMO NORMALIZADO - modelo del panel (panel/fisica.py) contra el dato del fabricante (ADAC)",
              "Pruebas de UN R84: ciclo urbano (4 ciclos ECE-15 desde frio) y 90 y 120 km/h constantes.",
              f"Modelo: {fisica.CONSUMO_RALENTI_LH:g} L/h en ralenti + {fisica.CONSUMO_POR_MIL_RPM_LH:g} L/h por cada "
              f"1000 rpm + potencia / ({fisica.RENDIMIENTO_MOTOR:g} x {fisica.PODER_CALORIFICO_MJ_L:g} MJ/L); "
              f"masa {fisica.MASA_KG:g} kg.",
              f"Tolerancia del modelo: +-{liberacion.TOLERANCIA_CONSUMO * 100:g} % (criterio del equipo).", ""]
    for prueba, consumo, publicado, ok, detalle in resultados:
        diferencia = (consumo - publicado) / publicado * 100
        lineas.append(f"  {'OK ' if ok else 'MAL'} {prueba:<9} modelo {consumo:5.1f} L/100 km  publicado "
                      f"{publicado:5.1f}  ({diferencia:+.1f} %)  {detalle}")
    aprobadas = sum(r[3] for r in resultados)
    lineas += ["", f"Resultado: {aprobadas}/{len(resultados)} pruebas de consumo dentro de la tolerancia "
                   f"({time.perf_counter() - inicio:.1f} s de calculo)"]
    print("\n".join(lineas))
    salida = pathlib.Path(args.salida) if args.salida else RAIZ / "docs" / "evidencias" / "consumo.txt"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return 0 if aprobadas == len(resultados) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
