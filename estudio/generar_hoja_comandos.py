"""Convierte estudio/04_hoja_de_comandos.md en estudio/Hoja_de_Comandos_F40.docx y .pdf.

Entiende lo que usa la hoja: titulos (#, ##), parrafos con **negritas** y `codigo`,
bloques de codigo (```) y tablas con |. Uso: python estudio/generar_hoja_comandos.py"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "informe"))

from docx import Document  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from generar_informe import convertir_pdf, numero_pagina, tabla  # noqa: E402

AQUI = pathlib.Path(__file__).resolve().parent
ORIGEN = AQUI / "04_hoja_de_comandos.md"
SALIDA = AQUI / "Hoja_de_Comandos_F40.docx"
AZUL = RGBColor(0x1F, 0x3A, 0x5F)


def en_linea(parrafo, texto):
    """Agrega texto con **negritas** y `codigo` en linea."""
    for parte in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", texto):
        if not parte:
            continue
        if parte.startswith("**"):
            parrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("`"):
            r = parrafo.add_run(parte[1:-1])
            r.font.name = "Courier New"
            r.font.size = Pt(9)
        else:
            parrafo.add_run(parte)


def bloque_codigo(doc, lineas):
    for linea in lineas:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.3)
        r = p.add_run(linea or " ")
        r.font.name = "Courier New"
        r.font.size = Pt(7.5)
        if linea.lstrip().startswith("#"):
            r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def construir():
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)
    pie = sec.footer.paragraphs[0]
    pie.add_run("Hoja de comandos — Clúster F40 — página ")
    numero_pagina(pie)

    lineas = ORIGEN.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if linea.startswith("```"):
            fin = next(j for j in range(i + 1, len(lineas)) if lineas[j].startswith("```"))
            bloque_codigo(doc, lineas[i + 1:fin])
            i = fin + 1
            continue
        if linea.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                celdas = [c.strip() for c in lineas[i].strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in celdas):
                    filas.append(celdas)
                i += 1
            tabla(doc, filas[0], filas[1:], anchos=[8, 9])
            continue
        if linea.startswith("# "):
            r = doc.add_paragraph().add_run(linea[2:])
            r.bold = True
            r.font.size = Pt(18)
            r.font.color.rgb = AZUL
        elif linea.startswith("## "):
            doc.add_heading(linea[3:], level=2)
        elif linea.strip():
            en_linea(doc.add_paragraph(), linea)
        i += 1
    return doc


def main():
    doc = construir()
    doc.save(SALIDA)
    pdf, paginas = convertir_pdf(SALIDA)
    print(f"OK {pdf.relative_to(AQUI.parent)} ({paginas} paginas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
