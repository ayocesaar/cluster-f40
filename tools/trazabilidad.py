"""Genera docs/matriz_trazabilidad.md a partir de los docstrings de las
pruebas y del resultado real de pytest (docs/evidencias/junit.xml)."""

import ast
import pathlib
import re
import xml.etree.ElementTree as ET

TECNICAS = {
    "test_particiones.py": "Particion de equivalencia",
    "test_limites.py": "Valores limite",
    "test_transiciones.py": "Transicion de estados",
    "test_invalidas.py": "Entradas invalidas",
    "test_complementarias.py": "Caja blanca (cobertura)",
    "test_requisitos.py": "Basada en requisitos",
    "test_presentacion.py": "Presentacion (caja negra)",
    "test_tablero.py": "Integracion UI (Tkinter)",
}

# Los casos parametrizados llegan como "test_x[param]": se agrupan por funcion
# y basta un fallo en cualquiera de sus variantes para marcar FAIL.
resultados = {}
for caso in ET.parse("docs/evidencias/junit.xml").getroot().iter("testcase"):
    nombre = caso.get("name").split("[")[0]
    if caso.find("failure") is not None or caso.find("error") is not None:
        estado = "FAIL"
    elif caso.find("skipped") is not None:
        tipo = caso.find("skipped").get("type", "")
        estado = "XFAIL" if "xfail" in tipo else "SKIP"
    else:
        estado = "PASS"
    if resultados.get(nombre) != "FAIL":
        resultados[nombre] = estado

filas = []
for archivo in sorted(pathlib.Path("tests").glob("test_*.py")):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
            doc = ast.get_docstring(nodo) or ""
            m = re.match(r"(CP-\d+):\s*(.*)", doc, re.S)
            cp, desc = (m.group(1), " ".join(m.group(2).split())) if m else ("-", doc)
            filas.append({
                "cp": cp,
                "tecnica": TECNICAS.get(archivo.name, archivo.name),
                "reqs": sorted(set(re.findall(r"R\d{2}", doc))),
                "desc": desc.replace("|", "/"),
                "prueba": f"{archivo.name}::{nodo.name}",
                "res": resultados.get(nodo.name, "NO EJECUTADA"),
            })

filas.sort(key=lambda f: int(f["cp"][3:]) if f["cp"] != "-" else 999)

lineas = [
    "# Matriz de trazabilidad - Cluster F40",
    "",
    "| CP | Tecnica | Requisito | Descripcion | Prueba | Resultado |",
    "|----|---------|-----------|-------------|--------|-----------|",
]
for f in filas:
    lineas.append(f"| {f['cp']} | {f['tecnica']} | {', '.join(f['reqs']) or '-'} "
                  f"| {f['desc']} | `{f['prueba']}` | {f['res']} |")

total = len(filas)
pasaron = sum(f["res"] == "PASS" for f in filas)
lineas += ["", "## Resumen", "", f"- Casos de prueba: {total}",
           f"- Pasaron: {pasaron}",
           f"- Fallo esperado por defecto abierto (XFAIL): {sum(f['res'] == 'XFAIL' for f in filas)}",
           f"- Fallaron / otros: {total - pasaron - sum(f['res'] == 'XFAIL' for f in filas)}", "",
           "## Casos por requisito", "", "| Requisito | Casos |", "|-----------|-------|"]
por_req = {}
for f in filas:
    for r in f["reqs"]:
        por_req.setdefault(r, []).append(f["cp"])
for r in sorted(por_req):
    lineas.append(f"| {r} | {', '.join(por_req[r])} |")

faltan = [f"R0{i}" for i in range(1, 9) if f"R0{i}" not in por_req]
lineas += ["", f"Requisitos sin casos: {', '.join(faltan) or 'ninguno'}"]

pathlib.Path("docs/matriz_trazabilidad.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(f"Matriz generada: {total} casos, {pasaron} PASS")
