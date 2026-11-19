"""Genera informe/Catalogo_Completo_de_Pruebas_F40.docx y .pdf: todas las pruebas en un solo documento.

Reune cada conjunto de pruebas del proyecto con su resultado real:
- las ejecuciones automatizadas (docs/evidencias/junit.xml) y sus casos CP/CA
  (docs/matriz_trazabilidad.md), agrupados por archivo de prueba;
- la aceptacion sobre la interfaz (docs/evidencias/aceptacion.txt);
- las pruebas P01-P12 de la guia (informe tecnico) y los casos CT-01 a CT-28
  (Documento completo de pruebas), evaluados con las mismas funciones;
- los casos de la practica del odometro (practica/evidencia_*/resumen.txt);
- la cobertura (coverage.json), la medicion de 60 s (metricas.txt) y los defectos.

Ningun resultado se escribe a mano; si falta una evidencia el script se detiene.
Uso (desde la raiz del proyecto): python informe/generar_catalogo_pruebas.py"""

import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

import generar_documento_pruebas as dcp  # noqa: E402
import generar_informe_tecnico as tec  # noqa: E402
from generar_informe import (IDENTIFICACION, TECNICAS, cargar_aceptacion, cargar_defectos, cargar_junit,  # noqa: E402
                             codigo, convertir_pdf, leer, numero_pagina, sistema_operativo, tabla, version_software)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
EVID = DOCS / "evidencias"
SALIDA = RAIZ / "informe" / "Catalogo_Completo_de_Pruebas_F40.docx"
RESULTADO = {"PASS": "Aprobada", "FAIL": "Fallida", "XFAIL": "Falla esperada", "SKIP": "Omitida"}


def cargar_matriz():
    """Filas de docs/matriz_trazabilidad.md: (id, tecnica, requisitos, descripcion, prueba, resultado)."""
    filas = []
    for linea in leer(DOCS / "matriz_trazabilidad.md").splitlines():
        m = re.match(r"^\| ((?:CP|CA)-\d+) \| (.+?) \| (.+?) \| (.+) \| `(.+?)` \| (\w+) \|$", linea)
        if m:
            filas.append(m.groups())
    if not filas:
        sys.exit("ERROR: docs/matriz_trazabilidad.md no tiene casos")
    return sorted(filas, key=lambda f: (f[0][:2] != "CP", int(f[0][3:])))


def resumen_practica(carpeta):
    ruta = RAIZ / "practica" / carpeta / "resumen.txt"
    if not ruta.exists():
        return {}
    filas = [linea.split("|") for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.count("|") == 4]
    return {f[0]: f for f in filas}


def metrica(lineas, patron):
    return next((m.group(1) for linea in lineas for m in [re.search(patron, linea)] if m), "—")


def construir():
    casos, fecha = cargar_junit()
    aceptacion, total_aceptacion = cargar_aceptacion()
    metricas = leer(EVID / "metricas.txt").splitlines()
    cov = json.loads(leer(EVID / "coverage.json"))
    matriz = cargar_matriz()
    defectos = cargar_defectos()
    antes, despues = resumen_practica("evidencia_antes"), resumen_practica("evidencia_despues")

    auto = {r: sum(c["res"] == r for c in casos) for r in ("PASS", "FAIL", "SKIP")}
    p_eval = [(p, *tec.resultado(casos, p[5])) for p in tec.PRUEBAS]
    ct_eval = [(c, *dcp.evaluar(casos, c[10], metricas)) for c in dcp.CASOS]
    aprob = lambda lista: sum(1 for _, e, _ in lista if e == "Aprobada")  # noqa: E731
    ca_aprob = sum(1 for a in aceptacion.values() if a["estado"] == "APROBADO")
    pasos_ok = sum(a["ok"] for a in aceptacion.values())
    pasos = pasos_ok + sum(a["xx"] for a in aceptacion.values())
    tot = cov["totals"]
    promedio = metrica(metricas, r"promedio=([\d.]+)")
    memoria = metrica(metricas, r"diferencia=(-?\d+) KB")
    acotado = metrica(metricas, r"acotado=(\w+)")

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)
    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.add_run("Catálogo completo de pruebas — Clúster F40 — página ")
    numero_pagina(pie)

    # Portada
    for _ in range(2):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Catálogo completo de pruebas\nClúster simulado del Ferrari F40 (1987)")
    r.bold = True
    r.font.size = Pt(20)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    doc.add_paragraph("Todas las pruebas del proyecto en un solo documento, cada una con su resultado real tomado de "
                      "las evidencias del repositorio.").alignment = WD_ALIGN_PARAGRAPH.CENTER
    tabla(doc, ["Campo", "Valor"], [(k, v) for k, v in IDENTIFICACION if k != "Fecha de entrega"] + [
        ("Fecha de este documento", datetime.date.today().isoformat()),
        ("Versión del software probado", version_software()),
        ("Fecha de ejecución de las pruebas", fecha or "no registrada"),
        ("Ambiente", f"{sistema_operativo()}; pantalla virtual Xvfb"),
        ("Repositorio", "https://github.com/ayocesaar/cluster-f40 (privado)"),
    ], anchos=[5.5, 11.5])
    doc.add_page_break()

    # 1. Resumen
    doc.add_heading("1. Resumen de todos los conjuntos de pruebas", level=1)
    filas = [
        ("Pruebas automatizadas (pytest)", f"{len(casos)} ejecuciones de {len(matriz)} casos CP/CA",
         f"{auto['PASS']} aprobadas, {auto['FAIL']} fallidas, {auto['SKIP']} omitidas", "docs/evidencias/junit.xml"),
        ("Aceptación sobre la interfaz (CA)", f"{len(aceptacion)} escenarios, {pasos} pasos",
         f"{ca_aprob}/{len(aceptacion)} escenarios; {pasos_ok}/{pasos} pasos coinciden", "docs/evidencias/aceptacion.txt"),
        ("Pruebas de la guía (P01–P12)", f"{len(p_eval)} pruebas", f"{aprob(p_eval)}/{len(p_eval)} aprobadas",
         "Informe técnico"),
        ("Casos del Documento de Pruebas (CT)", f"{len(ct_eval)} casos (CT-26 a CT-28 de la práctica)",
         f"{aprob(ct_eval)}/{len(ct_eval)} aprobados", "Documento completo de pruebas v2.1"),
        ("Práctica en clase: odómetro", f"{len(despues)} ejecuciones con la aplicación completa",
         f"Después: {sum(f[4] == 'Aprobado' for f in despues.values())} aprobadas de {len(despues)} "
         "(incluye las duraciones originales, que fallan)", "practica/evidencia_despues/resumen.txt"),
        ("Rendimiento (60 s reales)", "Intervalo, memoria y bitácoras",
         f"promedio {promedio} ms; memoria +{memoria} KB; bitácoras acotadas: {acotado}", "docs/evidencias/metricas.txt"),
        ("Cobertura de código", "Líneas y ramas",
         f"{tot['covered_lines']}/{tot['num_statements']} líneas, {tot['covered_branches']}/{tot['num_branches']} ramas "
         f"({round(tot['percent_covered'])}%)", "docs/evidencias/coverage.json"),
    ]
    tabla(doc, ["Conjunto", "Tamaño", "Resultado", "Fuente"], filas, anchos=[4.2, 4, 5.3, 3.5])
    if total_aceptacion:
        doc.add_paragraph(f"Aceptación: {total_aceptacion}")
    doc.add_paragraph(
        "Cómo se relacionan: los casos CP y CA son las pruebas automatizadas. Las pruebas P01–P12 de la guía y los "
        "casos CT del Documento de Pruebas son vistas de más alto nivel y cada una se respalda con casos CP o CA, por "
        "eso su estado se calcula de las mismas ejecuciones. La práctica del odómetro se ejecutó además con la "
        "aplicación completa, antes y después de implementarlo.")

    # 2. Por tecnica
    doc.add_heading("2. Resultados por técnica (archivo de prueba)", level=1)
    por_modulo = {}
    for c in casos:
        cuenta = por_modulo.setdefault(c["modulo"], {"PASS": 0, "FAIL": 0, "SKIP": 0})
        cuenta[c["res"]] += 1
    tabla(doc, ["Archivo", "Técnica", "Ejecuciones", "Aprobadas", "Fallidas", "Omitidas"],
          [(f"tests/{m}.py", TECNICAS.get(m, m), sum(n.values()), n["PASS"], n["FAIL"], n["SKIP"])
           for m, n in por_modulo.items()] +
          [("Total", "", len(casos), auto["PASS"], auto["FAIL"], auto["SKIP"])],
          anchos=[4.2, 5, 2, 2, 1.9, 1.9])

    # 3. Catalogo de casos automatizados
    doc.add_heading(f"3. Catálogo de los {len(matriz)} casos automatizados", level=1)
    doc.add_paragraph("Agrupados por archivo. La descripción es el docstring de cada prueba y el resultado sale de "
                      "junit.xml (si un caso tiene varias variantes, basta una fallida para marcarlo como fallido).")
    grupos = {}
    for fila in matriz:
        grupos.setdefault(fila[4].split("::")[0], []).append(fila)
    for archivo in sorted(grupos, key=lambda a: list(TECNICAS).index(a[:-3]) if a[:-3] in TECNICAS else 99):
        filas = grupos[archivo]
        doc.add_heading(f"tests/{archivo} — {TECNICAS.get(archivo[:-3], '')} ({len(filas)} casos)", level=2)
        tabla(doc, ["Caso", "Requisitos", "Qué verifica", "Resultado"],
              [(f[0], f[2], f[3], RESULTADO.get(f[5], f[5])) for f in filas], anchos=[1.5, 2.2, 11.3, 2])

    # 4. Pruebas de la guia
    doc.add_heading("4. Pruebas de la guía P01–P12", level=1)
    tabla(doc, ["Prueba", "Nombre", "Datos", "Esperado", "Casos", "Estado"],
          [(p[0], p[1], p[2], p[4], ", ".join(p[5]), e) for p, e, _ in p_eval], anchos=[1.3, 2.6, 4.2, 4.1, 2.6, 2.2])

    # 5. Casos CT
    doc.add_heading("5. Casos del Documento completo de pruebas (CT-01 a CT-28)", level=1)
    tabla(doc, ["Caso", "Nombre", "Categoría", "Prioridad", "Requisitos", "Estado"],
          [(c[0], c[1], c[2], c[5], ", ".join(c[3]), e) for c, e, _ in ct_eval], anchos=[1.3, 5.6, 2.8, 1.6, 3.5, 2.2])

    # 6. Aceptacion
    doc.add_heading("6. Aceptación sobre la interfaz real (CA-01 a CA-10)", level=1)
    descripcion = {f[0]: f[3] for f in matriz}
    tabla(doc, ["Escenario", "Qué verifica", "Pasos que coinciden", "Estado"],
          [(ca, descripcion.get(ca, ""), f"{a['ok']}/{a['ok'] + a['xx']}", a["estado"].capitalize())
           for ca, a in aceptacion.items()], anchos=[1.8, 10.2, 2.6, 2.4])

    # 7. Practica
    doc.add_heading("7. Práctica en clase: casos del odómetro", level=1)
    doc.add_paragraph("Ejecutados con la aplicación completa por practica/ejecutar_casos.py: antes sobre la versión "
                      "749d580 (sin odómetro) y después con el elemento 11. «v2» es la duración corregida.")
    if despues:
        tabla(doc, ["Caso", "Duración", "Antes (749d580)", "Después", "Obtenido después"],
              [(k, f"{f[1]} s", antes.get(k, [""] * 5)[4] or "—", f[4], f[3]) for k, f in despues.items()],
              anchos=[2.3, 1.6, 3, 2, 8.1])
    else:
        doc.add_paragraph("Sin ejecución registrada.")

    # 8. Cobertura
    doc.add_heading("8. Cobertura por módulo", level=1)
    tabla(doc, ["Módulo", "Líneas", "Ramas", "Cobertura"],
          [(ruta, f"{s['covered_lines']}/{s['num_statements']}", f"{s['covered_branches']}/{s['num_branches']}",
            f"{round(s['percent_covered'], 1)}%")
           for ruta, d in sorted(cov["files"].items()) for s in [d["summary"]] if s["num_statements"]],
          anchos=[7, 3.5, 3.5, 3])

    # 9. Rendimiento
    doc.add_heading("9. Medición real de 60 s (P12)", level=1)
    codigo(doc, [linea for linea in metricas if linea.strip() and not linea.startswith(("PID", "   "))][:22])

    # 10. Defectos
    doc.add_heading("10. Defectos encontrados por las pruebas", level=1)
    tabla(doc, ["Defecto", "Título", "Estado"], [(d["ID"], d["Titulo"], d.get("Estado", "—")) for d in defectos],
          anchos=[2, 10.5, 4.5])

    # 11. Como repetirlas
    doc.add_heading("11. Cómo repetir todas las pruebas", level=1)
    codigo(doc, ["cd ~/cluster-f40 && source .venv/bin/activate",
                 "xvfb-run -a python -m pytest -v --junitxml=docs/evidencias/junit.xml",
                 "xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv",
                 "xvfb-run -a python tools/ejecucion_prolongada.py --duracion-s 60",
                 'xvfb-run -a -s "-screen 0 1280x1024x24" python practica/ejecutar_casos.py --version despues',
                 "python tools/trazabilidad.py && python informe/generar_catalogo_pruebas.py"])
    return doc, auto


def main():
    doc, auto = construir()
    doc.save(SALIDA)
    print(f"OK {SALIDA.relative_to(RAIZ)}")
    pdf, paginas = convertir_pdf(SALIDA)
    print(f"OK {pdf.relative_to(RAIZ)} ({paginas} paginas)")
    return 0 if auto["FAIL"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
