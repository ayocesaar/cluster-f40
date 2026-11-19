"""Genera la hoja de la practica en clase (odometro) en DOCX.

Los resultados salen de las ejecuciones reales de practica/ejecutar_casos.py:
evidencia_antes/ (version 749d580, sin odometro) y evidencia_despues/ (con el
elemento 11). Uso: python practica/generar_practica.py"""

import ast
import pathlib
import re
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = pathlib.Path(__file__).resolve().parent
ANTES = AQUI / "evidencia_antes"
DESPUES = AQUI / "evidencia_despues"
SALIDA = AQUI / "Practica_Odometro_Cesar_Vazquez.docx"


def resumen(carpeta):
    ruta = carpeta / "resumen.txt"
    if not ruta.exists():
        return {}
    filas = [linea.split("|") for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.count("|") == 4]
    return {f[0]: f for f in filas}


def pruebas_odometro():
    """(CP, que verifica, resultado) de tests/test_odometro.py con el resultado real de docs/evidencias/junit.xml."""
    raiz = AQUI.parent
    junit = raiz / "docs" / "evidencias" / "junit.xml"
    resultados = {}
    if junit.exists():
        for c in ET.parse(junit).getroot().iter("testcase"):
            res = "FAIL" if c.find("failure") is not None or c.find("error") is not None else (
                "SKIP" if c.find("skipped") is not None else "PASS")
            resultados.setdefault(c.get("name").split("[")[0], []).append(res)
    filas = []
    arbol = ast.parse((raiz / "tests" / "test_odometro.py").read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
            m = re.match(r"(CP-\d+): (.+)", ast.get_docstring(nodo) or "")
            if m:
                res = resultados.get(nodo.name, [])
                texto = (f"Aprobada ({res.count('PASS')}/{len(res)})" if res and res.count("PASS") == len(res)
                         else (f"{res.count('PASS')}/{len(res)} aprobadas" if res else "sin ejecución registrada"))
                filas.append((m.group(1), m.group(2), texto))
    filas.sort(key=lambda f: int(f[0][3:]))
    total = sum(len(v) for v in resultados.values())
    aprobadas = sum(v.count("PASS") for v in resultados.values())
    return filas, total, aprobadas


R_ANTES, R_DESPUES = resumen(ANTES), resumen(DESPUES)
EVIDENCIA = {"CP-ODO-01": "CP-ODO-01_normal_30s", "CP-ODO-01 v2": "CP-ODO-01_v2_normal_45s",
             "CP-ODO-02": "CP-ODO-02_limite_10s", "CP-ODO-02 v2": "CP-ODO-02_v2_limite_15s",
             "CP-ODO-03": "CP-ODO-03_archivo_corrupto", "SONDA": "SONDA_odometro_en_vehiculo_conf"}


def sombrear(celda, color):
    pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    pr.append(shd)


def tabla(doc, encabezados, filas, anchos):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    for i, h in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9)
        sombrear(c, "D9E2F3")
    for fila in filas:
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            celdas[i].text = ""
            r = celdas[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(9)
            if encabezados[0] == "Campo" and i == 0:
                r.bold = True
                sombrear(celdas[i], "F2F2F2")
    for fila in t.rows:
        for i, a in enumerate(anchos):
            fila.cells[i].width = Cm(a)
    doc.add_paragraph()


def ficha(doc, filas):
    tabla(doc, ["Campo", "Respuesta del alumno"], filas, [4, 12.5])


def lineas(ruta):
    return ruta.read_text(encoding="utf-8").strip().splitlines() if ruta.exists() else []


doc = Document()
s = doc.sections[0]
s.left_margin = s.right_margin = Cm(2.2)
s.top_margin = s.bottom_margin = Cm(2)
doc.styles["Normal"].font.name = "Arial"
doc.styles["Normal"].font.size = Pt(10.5)

t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Práctica en clase: Diseño y ejecución supervisada de pruebas")
r.bold = True
r.font.size = Pt(18)
r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
tabla(doc, ["Campo", "Valor"], [
    ("Alumno", "César Saúl Vázquez Preciado (5079359), Equipo 3"),
    ("Proyecto", "Clúster simulado del Ferrari F40 (1987). Versiones probadas: commit 749d580 (antes, sin odómetro) "
                 "y Etapa 13 (después, con el odómetro implementado)"),
    ("Elemento asignado", "Odómetro"),
    ("Técnica y condición", "El profesor solo asignó el elemento; la técnica de cada caso la eligió el alumno (se indica en cada caso)"),
    ("Uso de IA", "Permitido por el profesor. Claude Code apoyó el diseño y ejecutó los casos en la VM (ver anexo)"),
], [4, 12.5])

doc.add_heading("Requisito interpretado", level=1)
doc.add_paragraph(
    "El odómetro no está entre los diez elementos del proyecto, así que primero se definió el requisito a probar, "
    "tomando como referencia el F40 real (contador de 6 dígitos, la foto del tablero muestra 000062) y la guía del "
    "proyecto, que pone el odómetro como ejemplo de información en línea.")
ficha(doc, [
    ("Identificador", "REQ-ODO-01"),
    ("Elemento", "Odómetro (información en línea)"),
    ("Entrada", "Se calcula de la velocidad: distancia += velocidad (km/h) × tiempo transcurrido (h). No se escribe desde el archivo de datos"),
    ("Rango y formato", "Entero de 0 a 999 999 km, mostrado con 6 dígitos y ceros a la izquierda"),
    ("Frecuencia", "Con el ciclo de la velocidad (100 ms)"),
    ("Persistencia", "Se guarda en datos/odometro.txt y continúa al reiniciar"),
    ("Regla", "Nunca disminuye; al pasar de 999 999 vuelve a 000 000"),
    ("Error", "Si datos/odometro.txt falta o está corrupto: no se detiene, conserva el último valor válido (0 la primera vez), avisa y registra ERROR"),
])

doc.add_heading("Parte A. Diseño individual", level=1)
casos = (
    ("CP-ODO-01 · Funcionamiento normal",
     [("Identificador", "CP-ODO-01"), ("Requisito", "REQ-ODO-01: el odómetro acumula la distancia recorrida"),
      ("Tipo y técnica", "Sistema, funcional, caja negra / partición de equivalencia (velocidad válida constante)"),
      ("Precondiciones", "Aplicación abierta en modo archivo; motor encendido; odómetro en 000062"),
      ("Datos", "velocidad=120 km/h constante durante 30 s (datos/vehiculo.conf)"),
      ("Pasos", "1. Confirmar que el odómetro muestra 000062.\n2. Escribir motor=1 y velocidad=120.\n3. Esperar 30 s.\n4. Leer el odómetro y eventos.log."),
      ("Resultado esperado", "120 km/h × 30 s = 120 × 30/3600 = 1 km: el odómetro muestra 000063 y eventos.log registra INFO odometro_actualizado"),
      ("Evidencia prevista", "Captura del tablero a los 30 s y eventos.log")]),
    ("CP-ODO-02 · Condición límite",
     [("Identificador", "CP-ODO-02"), ("Requisito", "REQ-ODO-01: rango 0–999 999 y vuelta a cero"),
      ("Tipo y técnica", "Sistema, funcional / valores límite (máximo del contador) y transición de estado"),
      ("Precondiciones", "Motor encendido; datos/odometro.txt = 999999"),
      ("Datos", "velocidad=360 km/h durante 10 s (= 1 km)"),
      ("Pasos", "1. Iniciar con el odómetro en 999999.\n2. Escribir velocidad=360.\n3. Esperar 10 s.\n4. Leer el odómetro y las bitácoras."),
      ("Resultado esperado", "360 × 10/3600 = 1 km: pasa de 999999 a 000000 sin error ni 7 dígitos; queda registrado el cambio"),
      ("Evidencia prevista", "Captura del tablero y bitácoras")]),
    ("CP-ODO-03 · Entrada inválida o falla",
     [("Identificador", "CP-ODO-03"), ("Requisito", "REQ-ODO-01: comportamiento ante archivo corrupto"),
      ("Tipo y técnica", "Integración, negativa / conjetura de errores (archivo corrupto)"),
      ("Precondiciones", "datos/odometro.txt contiene el texto abc"),
      ("Datos", "odometro.txt = abc; velocidad=120"),
      ("Pasos", "1. Escribir abc en datos/odometro.txt.\n2. Iniciar la aplicación.\n3. Observar el tablero y errores.log."),
      ("Resultado esperado", "No se detiene; el odómetro arranca en 000000 (no hay valor válido previo); aviso en pantalla y ERROR odometro_invalido en errores.log"),
      ("Evidencia prevista", "Captura y errores.log")]),
)
for titulo, filas in casos:
    doc.add_heading(titulo, level=2)
    ficha(doc, filas)

doc.add_paragraph("Estos son los casos tal como se diseñaron. Al ejecutarlos se corrigieron las duraciones de CP-ODO-01 "
                  "y CP-ODO-02 (ver «Corrección del propio caso»).")


def tabla_resultados(resultados, claves, carpeta):
    filas = []
    for clave in claves:
        f = resultados.get(clave)
        if f:
            filas.append((f[0], f"{f[1]} s", f[2], f[3], f[4], f"{carpeta}/{EVIDENCIA[clave]}.png y sus .log"))
        else:
            filas.append((clave, "—", "—", "sin ejecución registrada", "—", "—"))
    tabla(doc, ["Caso", "Duración", "Esperado", "Obtenido", "Estado", "Evidencia"], filas, [2.0, 1.4, 3.3, 5.2, 2.0, 2.6])


def figura(ruta, texto):
    if ruta.exists():
        doc.add_picture(str(ruta), width=Cm(15))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(texto).alignment = WD_ALIGN_PARAGRAPH.CENTER


def bitacora(ruta, filtro):
    for linea in lineas(ruta):
        if filtro in linea:
            p = doc.add_paragraph()
            rr = p.add_run(linea)
            rr.font.name = "Courier New"
            rr.font.size = Pt(8)


doc.add_heading("Parte B. Ejecución (versión 749d580, antes de implementar)", level=1)
doc.add_paragraph("Los tres casos se ejecutaron de verdad en la máquina virtual (Ubuntu 22.04) con la aplicación completa "
                  "sobre una pantalla virtual (practica/ejecutar_casos.py --version antes). Se guardaron capturas, los "
                  "textos del tablero y las bitácoras de cada ejecución. El estado se calcula de lo observado.")
tabla_resultados(R_ANTES, ("CP-ODO-01", "CP-ODO-02", "CP-ODO-03"), "evidencia_antes")
doc.add_paragraph("Prueba adicional (SONDA): al intentar dar el valor por el archivo de datos (odometro=999999), el lector "
                  "lo rechazó y lo registró:")
bitacora(ANTES / "SONDA_odometro_en_vehiculo_conf_errores.log", "odometro")
estados_antes = tuple(R_ANTES.get(c, [""] * 5)[4] for c in ("CP-ODO-01", "CP-ODO-02", "CP-ODO-03"))
if estados_antes == ("Fallido", "Fallido", "Bloqueado (DEF-03)"):
    doc.add_paragraph("Por qué dos fallidos y un bloqueado: en CP-ODO-01 y 02 el sistema sí corrió y el resultado "
                      "observado es distinto del esperado (fallido). En CP-ODO-03 la falla a probar (leer un archivo "
                      "corrupto) ni siquiera puede ocurrir mientras no exista el odómetro, así que el caso queda "
                      "bloqueado por el defecto.")
figura(ANTES / "CP-ODO-01_normal_30s.png", "Figura 1. CP-ODO-01 antes de implementar, a los 30 s: velocímetro en "
                                            "120 km/h y ningún odómetro en el tablero.")

doc.add_heading("Reporte de defecto", level=2)
ficha(doc, [
    ("Identificador", "DEF-03"),
    ("Título", "El clúster no implementa el odómetro"),
    ("Caso relacionado", "CP-ODO-01, CP-ODO-02 (fallidos) y CP-ODO-03 (bloqueado)"),
    ("Severidad y prioridad", "Media / alta: no afecta la seguridad, pero falta una función que la guía cita como información en línea"),
    ("Pasos para reproducir", "1. Abrir el clúster en modo archivo.\n2. Escribir motor=1 y velocidad=120.\n3. Esperar 30 s y buscar el odómetro en el tablero.\n4. Opcional: agregar odometro=999999 a datos/vehiculo.conf y revisar errores.log."),
    ("Esperado y observado", "Esperado: un contador de 6 dígitos que sube 1 km. Observado: no hay contador; la clave odometro se rechaza como clave_desconocida."),
    ("Evidencia", "evidencia_antes/: capturas, bitácoras y resumen.txt; en 749d580 no hay coincidencias de 'odometr' en "
                  "logic/, sistema/, ui/ ni main.py"),
    ("Estado", ("Cerrado en la Etapa 13: odómetro implementado y regresión aprobada (Parte B.2)"
                if all(R_DESPUES.get(c, [""] * 5)[4] == "Aprobado" for c in ("CP-ODO-01 v2", "CP-ODO-02 v2", "CP-ODO-03"))
                else "Abierto: la regresión de la Parte B.2 no está aprobada por completo")),
])

doc.add_heading("Parte B.2 Regresión después de implementar el odómetro", level=1)
doc.add_paragraph(
    "Se implementó el elemento 11 (logic/odometro.py, sistema/odometro_archivo.py, dibujo en ui/tablero.py y guardado "
    "en main.py) sin modificar ninguna de las pruebas anteriores, y se repitieron los mismos casos con el mismo script "
    "(--version despues). «v2» es el caso con la duración corregida.")
tabla_resultados(R_DESPUES, ("CP-ODO-01", "CP-ODO-01 v2", "CP-ODO-02", "CP-ODO-02 v2", "CP-ODO-03", "SONDA"),
                 "evidencia_despues")
doc.add_paragraph("Líneas de la bitácora del caso CP-ODO-01 v2:")
bitacora(DESPUES / "CP-ODO-01_v2_normal_45s_eventos.log", "odometro")
doc.add_paragraph("Líneas de la bitácora del caso CP-ODO-03 (archivo corrupto):")
bitacora(DESPUES / "CP-ODO-03_archivo_corrupto_errores.log", "odometro")
figura(DESPUES / "CP-ODO-01_v2_normal_45s.png", "Figura 2. CP-ODO-01 v2 después de implementar, a los 45 s: el "
                                                 "odómetro dentro del velocímetro.")
figura(DESPUES / "CP-ODO-03_archivo_corrupto.png", "Figura 3. CP-ODO-03 después de implementar: odómetro en 000000 "
                                                    "y aviso en la parte inferior.")

doc.add_heading("Corrección del propio caso", level=2)
tabla(doc, ["Caso", "Diseño original", "Corrección", "Motivo"], [
    ("CP-ODO-01", "120 km/h durante 30 s (1 km exacto)", "45 s (1.5 km)",
     "Con 1 km exacto el resultado depende de décimas de segundo (arranque de la aplicación y primer ciclo de lectura); "
     "con 1.5 km queda medio kilómetro de margen. La Parte B.2 muestra lo observado con ambas duraciones."),
    ("CP-ODO-02", "360 km/h durante 10 s (1 km exacto)", "15 s (1.5 km)", "Mismo motivo que CP-ODO-01."),
    ("CP-ODO-03", "odometro.txt = abc", "Sin cambio; se agregaron variantes en las pruebas automatizadas "
                  "(respaldo, permisos, formato)", "El caso cubría un solo tipo de archivo inválido."),
], [2.2, 3.8, 4, 6.5])
doc.add_paragraph("Los tres casos corregidos también quedaron automatizados con reloj simulado en tests/test_odometro.py "
                  "(CP-120, CP-122 y CP-125) y están en el Documento completo de pruebas v2.1 como CT-26 a CT-28.")

doc.add_heading("Parte B.3 El odómetro implementado y sus pruebas automatizadas", level=1)
doc.add_paragraph("Cómo funciona el elemento 11 después de la corrección de DEF-03:")
for texto in (
    "Cálculo (logic/odometro.py): en cada ciclo de 50 ms suma velocidad mostrada × tiempo transcurrido; solo avanza "
    "con el motor encendido y velocidad mayor que 0. Guarda la fracción de kilómetro para no perder distancia.",
    "Pantalla (ui/tablero.py): contador de 6 dígitos dentro del velocímetro (000000–999999); después de 999999 vuelve "
    "a 000000 y cuenta la vuelta. Nunca disminuye.",
    "Persistencia (sistema/odometro_archivo.py, main.py): datos/odometro.txt con un respaldo .bak, escritura atómica "
    "(temporal + fsync + os.replace) y permisos 640; se guarda cada 5 s y al cerrar.",
    "Errores: un archivo ausente, corrupto, demasiado grande, que no es UTF-8 o que cualquiera puede escribir se "
    "rechaza; se usa el respaldo o se inicia en 000000, con aviso en pantalla y ERROR en errores.log.",
    "Bitácora (sistema/monitor.py): INFO odometro_actualizado cada kilómetro, como pedía el esperado de CP-ODO-01.",
    "Seguridad: odometro= en datos/vehiculo.conf se rechaza (clave_no_permitida); el kilometraje solo lo calcula el sistema.",
):
    doc.add_paragraph(texto, style="List Bullet")
filas_odo, total_suite, aprobadas_suite = pruebas_odometro()
doc.add_paragraph(f"Pruebas automatizadas del odómetro (tests/test_odometro.py, {len(filas_odo)} casos). El resultado "
                  "sale de la ejecución registrada en docs/evidencias/junit.xml:")
tabla(doc, ["Caso", "Qué verifica", "Resultado"], filas_odo, [1.6, 11.4, 3.5])
doc.add_paragraph(f"Suite completa en la misma ejecución: {aprobadas_suite} de {total_suite} ejecuciones aprobadas. "
                  "Las pruebas anteriores al odómetro no se modificaron: el script de la etapa compara su huella "
                  "sha256 antes de guardar cualquier cambio.")

doc.add_heading("Parte C. Revisión cruzada", level=1)
doc.add_paragraph("Revisión de un caso de un compañero (llenar en clase):")
tabla(doc, ["Aspecto", "Pregunta", "Observación"], [
    ("Objetivo", "¿Se entiende qué comportamiento verifica?", ""), ("Requisito", "¿Existe una relación identificable?", ""),
    ("Precondiciones", "¿El estado previo es suficiente?", ""), ("Datos", "¿Son concretos y adecuados a la técnica?", ""),
    ("Procedimiento", "¿Otra persona puede repetirlo?", ""), ("Resultado", "¿Es observable y medible?", ""),
    ("Cobertura", "¿Qué caso adicional hace falta?", ""),
], [3, 6.5, 7])
doc.add_paragraph("Registro de retroalimentación recibida sobre mis casos (llenar en clase):")
tabla(doc, ["Observación recibida", "Corrección realizada", "Justificación si no se acepta"], [("", "", ""), ("", "", "")], [5.5, 5.5, 5.5])

doc.add_heading("Parte D. Escenario sorpresa", level=1)
doc.add_paragraph("Escenario que plantee el profesor: ______________________________________________")
tabla(doc, ["Pregunta", "Respuesta"], [("¿Qué requisito cambia?", ""), ("¿Qué casos se modifican?", ""),
                                       ("¿Qué casos deben repetirse?", ""), ("¿Qué riesgo aparece?", ""),
                                       ("¿Qué evidencia se necesita?", "")], [5, 11.5])

doc.add_heading("Cómo explicarlo (guía rápida)", level=1)
for texto in (
    "Cálculo: distancia = velocidad × tiempo. 120 km/h durante 30 s son 120 × 30 / 3600 = 1 km; 360 km/h durante 10 s también es 1 km.",
    "Técnicas: partición de equivalencia para el caso normal (una velocidad válida representa a todas); valores límite para el máximo del contador (999 999 → 000 000); conjetura de errores para el archivo corrupto.",
    "Fallido contra bloqueado: fallido es cuando el caso corre y el resultado no coincide; bloqueado es cuando el caso no se puede ejecutar porque falta algo (aquí, el propio odómetro).",
    "Hallazgo: el defecto DEF-03 muestra que el proyecto no cubre un elemento que la guía usa como ejemplo de información en línea; la corrección es implementar el odómetro y repetir los tres casos como regresión.",
    "Caso adicional que haría falta (cobertura): intentar modificar el odómetro desde datos/vehiculo.conf debe rechazarse siempre, para impedir alterar el kilometraje. Se agregó como SONDA y ahora se rechaza con clave_no_permitida.",
    "Regresión: después de corregir un defecto se repiten los mismos casos; además se ejecutan las pruebas anteriores sin modificarlas para comprobar que nada se rompió.",
    "Corrección del propio caso: un esperado de exactamente 1 km en tiempo real queda en el borde del cambio de dígito; por eso se corrigió a 1.5 km.",
    "Persistencia: el kilometraje se guarda cada 5 s y al cerrar en datos/odometro.txt con escritura atómica y un respaldo .bak; si el archivo se corrompe se usa el respaldo o se inicia en 000000 con aviso.",
):
    doc.add_paragraph(texto, style="List Bullet")

doc.add_heading("Anexo: uso de IA", level=1)
tabla(doc, ["Campo", "Contenido"], [
    ("Herramienta", "Claude Code (Anthropic)"),
    ("Finalidad", "Definir el requisito del odómetro, redactar los casos, ejecutarlos en la VM e implementar el odómetro"),
    ("Instrucción", "\"La prueba que me dijo fue odómetro; sí me permitió el uso de IA\"; \"implementa el odómetro y súbelo todo al repo\""),
    ("Resultado utilizado", "Los tres casos, las ejecuciones reales antes y después, el reporte DEF-03, la implementación del "
                            "elemento 11 y esta hoja"),
    ("Verificación", "Ejecuciones reales en la VM con capturas y bitácoras (evidencia_antes/ y evidencia_despues/); suite "
                     "completa de pruebas con las pruebas anteriores sin cambios"),
    ("Recomendación corregida", "La IA propuso 30 s y 10 s (1 km exacto); se corrigió a 45 s y 15 s (Corrección del propio caso)"),
], [4, 12.5])

doc.save(SALIDA)
print("OK", SALIDA)
