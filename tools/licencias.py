"""Dependencias externas y su licencia, leidas de los metadatos de los paquetes instalados.

La guia pide identificar las dependencias y la procedencia y licencia de los recursos de
terceros. Este script no inventa nada: lee requirements.txt y, para cada paquete, la version
y la licencia que declara el propio paquete instalado (importlib.metadata).

Uso (desde la raiz, con el entorno activado): python tools/licencias.py [SALIDA]"""

import importlib.metadata as md
import pathlib
import platform
import sys
import tkinter

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def licencia(meta):
    texto = meta.get("License-Expression") or meta.get("License") or ""
    texto = texto.splitlines()[0].strip() if texto.strip() else ""
    clasificadores = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License")]
    if texto and len(texto) <= 60:
        return texto
    return "; ".join(clasificadores) or (texto[:60] + "...") or "no declarada en los metadatos"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    salida = pathlib.Path(argv[0]) if argv else RAIZ / "docs" / "evidencias" / "licencias.txt"
    lineas = ["Dependencias externas (requirements.txt) y su licencia segun los metadatos instalados",
              f"Python {platform.python_version()} (PSF-2.0, biblioteca estandar); Tcl/Tk {tkinter.TkVersion} "
              "(licencia BSD de Tcl/Tk, incluido con Python)", ""]
    faltan = 0
    for linea in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines():
        nombre = linea.split("==")[0].strip()
        if not nombre or nombre.startswith("#"):
            continue
        try:
            meta = md.metadata(nombre)
            lineas.append(f"{nombre:<20} {md.version(nombre):<10} {licencia(meta)}")
        except md.PackageNotFoundError:
            lineas.append(f"{nombre:<20} {'-':<10} NO INSTALADO")
            faltan += 1
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 1 if faltan else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
