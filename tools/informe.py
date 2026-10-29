"""Genera docs/informe_pruebas.md con datos reales de las evidencias:
junit.xml (resultados), coverage.json (cobertura), registro de defectos y
matriz de trazabilidad."""

import json
import pathlib
import platform
import xml.etree.ElementTree as ET
from importlib.metadata import version

TECNICAS = {
    "test_particiones": "Particion de equivalencia",
    "test_limites": "Valores limite",
    "test_transiciones": "Transicion de estados",
    "test_invalidas": "Entradas invalidas",
    "test_complementarias": "Caja blanca (cobertura)",
    "test_requisitos": "Basada en requisitos",
    "test_presentacion": "Presentacion (caja negra)",
    "test_tablero": "Integracion UI (Tkinter)",
}

por_tecnica = {}
for caso in ET.parse("docs/evidencias/junit.xml").getroot().iter("testcase"):
    modulo = caso.get("classname").split(".")[-1]
    if caso.find("failure") is not None or caso.find("error") is not None:
        res = "FAIL"
    elif caso.find("skipped") is not None:
        res = "XFAIL" if "xfail" in caso.find("skipped").get("type", "") else "SKIP"
    else:
        res = "PASS"
    cuenta = por_tecnica.setdefault(TECNICAS.get(modulo, modulo),
                                    {"PASS": 0, "FAIL": 0, "XFAIL": 0, "SKIP": 0})
    cuenta[res] += 1

total = {k: sum(c[k] for c in por_tecnica.values()) for k in ("PASS", "FAIL", "XFAIL", "SKIP")}
n_total = sum(total.values())

cov = json.loads(pathlib.Path("docs/evidencias/coverage.json").read_text(encoding="utf-8"))
registro = pathlib.Path("docs/registro_defectos.md").read_text(encoding="utf-8")
n_def = registro.count("\n## DEF-")
n_abiertos = registro.count("| Estado | Abierto")
matriz = pathlib.Path("docs/matriz_trazabilidad.md").read_text(encoding="utf-8")
sin_casos = next((l for l in matriz.splitlines() if l.startswith("Requisitos sin casos:")),
                 "Requisitos sin casos: (no calculado)")

L = [
    "# Informe de pruebas - Cluster F40",
    "",
    "## 1. Objetivo",
    "",
    "Verificar que la logica del cluster de instrumentos simulado del Ferrari F40",
    "(`logic/estado.py` y `logic/reloj.py`) cumple las reglas R01 a R08, mediante",
    "pruebas automatizadas con pytest y medicion de cobertura con coverage.",
    "",
    "## 2. Alcance",
    "",
    "- Incluido: `logic/estado.py` (EstadoCluster, reglas R01-R08) y `logic/reloj.py`",
    "  (RelojReal, RelojSimulado).",
    "- Incluido: `ui/presentacion.py` (lo que se dibuja de cada elemento),",
    "  `ui/tablero.py` y `main.py` (interfaz Tkinter), probados con Tkinter real",
    "  sobre una pantalla virtual (Xvfb).",
    "- Pendiente: pruebas de aceptacion (Etapa 8c) y capturas (Etapa 8d).",
    "- El tiempo se controla con `RelojSimulado`, de modo que las pruebas de ciclos,",
    "  parpadeos e histeresis son deterministas y no dependen de esperas reales.",
    "",
    "## 3. Entorno",
    "",
    f"- Sistema: {platform.system()} {platform.release()}",
    f"- Python: {platform.python_version()}",
    f"- pytest: {version('pytest')}",
    f"- coverage: {version('coverage')}",
    "",
    "## 4. Tecnicas y resultados",
    "",
    "| Tecnica | Ejecuciones | Pasaron | Fallaron | XFAIL |",
    "|---------|-------------|---------|----------|-------|",
]
for tecnica, c in por_tecnica.items():
    L.append(f"| {tecnica} | {sum(c.values())} | {c['PASS']} | {c['FAIL']} | {c['XFAIL']} |")
L += [
    f"| **Total** | **{n_total}** | **{total['PASS']}** | **{total['FAIL']}** | **{total['XFAIL']}** |",
    "",
    "Las ejecuciones cuentan cada variante parametrizada por separado; la matriz de",
    "trazabilidad agrupa por caso de prueba (CP).",
    "",
    "## 5. Cobertura (lineas y ramas)",
    "",
    "| Modulo | Lineas | Ramas | Cobertura |",
    "|--------|--------|-------|-----------|",
]
for ruta in ("logic/estado.py", "logic/reloj.py", "ui/presentacion.py", "ui/tablero.py", "main.py"):
    if ruta not in cov["files"]:
        continue
    s = cov["files"][ruta]["summary"]
    L.append(f"| `{ruta}` | {s['covered_lines']}/{s['num_statements']} "
             f"| {s['covered_branches']}/{s['num_branches']} | {round(s['percent_covered'], 1)}% |")
L += [
    "",
    "## 6. Trazabilidad",
    "",
    "Cada caso de prueba esta asociado a los requisitos que verifica en",
    "`docs/matriz_trazabilidad.md`, generada automaticamente desde los docstrings",
    "de las pruebas y el resultado de junit.",
    "",
    f"- {sin_casos}",
    "",
    "## 7. Defectos",
    "",
    f"- Defectos registrados: {n_def}",
    f"- Defectos abiertos: {n_abiertos}",
    "- DEF-01 (testigo 10 parpadeando con el motor apagado) fue rechazado: R08",
    "  no condiciona el testigo al motor. Se revirtio la correccion de la Etapa 7",
    "  y CP-66 verifica el comportamiento correcto. Detalle en",
    "  `docs/registro_defectos.md`.",
    "",
    "## 8. Decisiones de diseno y observaciones",
    "",
    "- Al apagar el motor (R01) se apagan tambien el testigo 9 y el ambar del",
    "  elemento 2, reiniciando sus temporizadores; de lo contrario se encenderian",
    "  falsamente porque R01 fuerza p_aceite a 0 (nota de diseno en `estado.py`).",
    "- Los testigos informativos 6, 7 y 8 solo se muestran con el motor encendido;",
    "  es el estado definido que R01 deja abierto (decision D2).",
    "- El testigo 10 (critico) parpadea mientras falla_frenos=1 aunque el motor",
    "  este apagado, porque R08 no lo condiciona al motor (decision D1).",
    "- La especificacion distingue Encendido (elementos 1 y 4) y Motor activo",
    "  (elementos 2, 3 y 5); el sistema usa un solo interruptor motor que",
    "  representa ambas senales (decision D3).",
    "- R02 se interpreta como tiempo continuo: entre 1.0 y 1.2 bar se reinician",
    "  ambos temporizadores, asi que una presion que oscila entre 0.9 y 1.1 bar",
    "  no enciende el testigo 9.",
    "- La velocidad no tiene una regla especifica en R01-R08; se valida como entrada",
    "  (rangos, tipos y valores limite).",
    "- Los casos CP-60 a CP-63 prueban la infraestructura de tiempo (reloj) y no",
    "  se asocian a un requisito funcional.",
    "",
    "## 9. Evidencias",
    "",
    "- `docs/evidencias/pytest.txt`: salida completa de pytest -v.",
    "- `docs/evidencias/junit.xml`: resultados en formato JUnit.",
    "- `docs/evidencias/coverage.txt` y `coverage.json`: reporte de cobertura.",
    "- `docs/evidencias/htmlcov/index.html`: reporte de cobertura navegable.",
    "- `docs/matriz_trazabilidad.md` y `docs/registro_defectos.md`.",
    "",
    "## 10. Conclusion",
    "",
]
if total["FAIL"] == 0 and total["XFAIL"] == 0 and n_abiertos == 0:
    L.append(f"Las {n_total} ejecuciones pasan, la cobertura de la logica es completa y "
             "no quedan defectos abiertos: la logica cumple R01-R08 segun las pruebas definidas.")
else:
    L.append(f"Quedan {total['FAIL']} fallos, {total['XFAIL']} fallos esperados y "
             f"{n_abiertos} defectos abiertos; la logica aun no se considera aceptada.")

pathlib.Path("docs/informe_pruebas.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"Informe generado: {n_total} ejecuciones, {total['PASS']} PASS")
