"""Genera informe/Documento_Completo_de_Pruebas_F40.docx y .pdf (Tarea 2).

Sigue la "estructura obligatoria" de la Tarea 2: control documental, introduccion,
alcance, sistema bajo prueba, requisitos de los once elementos (los diez de la
especificacion y el odometro), estrategia, ambiente, riesgos, criterios, 28 casos
(25 con la distribucion pedida y 3 de la practica en clase), trazabilidad,
defectos, resultados con metricas y anexos (evidencias, cambios, actividades
previas, uso de IA y defensa).

El estado de cada caso se calcula de docs/evidencias/junit.xml y de
docs/evidencias/metricas.txt; el historial sale de git; los resultados de la
practica (antes y despues de implementar el odometro) salen de
practica/evidencia_antes/ y practica/evidencia_despues/. Las actividades de la
practica que todavia no ocurren quedan marcadas como pendientes.

Uso (desde la raiz del proyecto): python informe/generar_documento_pruebas.py"""

import datetime
import os
import pathlib
import platform
import re
import subprocess
import sys
from importlib.metadata import version

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from generar_informe import (IDENTIFICACION, cargar_aceptacion, cargar_defectos, cargar_junit, codigo, convertir_pdf,  # noqa: E402
                             ejecuciones, ficha, figura, leer, numero_pagina, sistema_operativo, tabla, version_software,
                             vinetas)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
EVID = DOCS / "evidencias"
SALIDA = RAIZ / "informe" / "Documento_Completo_de_Pruebas_F40.docx"
IDENTIFICADOR = "DCP-F40-T2"
VERSION_DOC = "2.2"
PENDIENTE = "PENDIENTE: todavía no se realiza en clase."
PRACTICA = RAIZ / "practica"
CASOS_PRACTICA = ("CT-26", "CT-27", "CT-28")

REQUISITOS = (
    ("REQ-VEL-01", "1 Velocímetro", "Decimal de 0 a 360 km/h (clave velocidad)", "100 ms",
     "Muestra el valor con una décima en km/h; aguja proporcional al rango", "Sin umbral; vuelve a 0 al apagar el motor (R01)",
     "Conserva el último valor válido y registra ERROR en errores.log"),
    ("REQ-ACE-01", "2 Presión de aceite", "Decimal de 0 a 10 bar (clave presion_aceite)", "100 ms",
     "Muestra el valor con dos decimales en bar", "Aguja ámbar inmediata si < 1 bar con motor activo",
     "Conserva el último valor válido y registra ERROR"),
    ("REQ-RPM-01", "3 Tacómetro", "Entero de 0 a 9000 rpm (clave rpm)", "100 ms",
     "Muestra el valor entero en RPM", "Rojo con rpm ≥ 8000; vuelve a normal con rpm < 7800 (R03)",
     "Un decimal o texto se rechaza; conserva el último valor válido y registra ERROR"),
    ("REQ-TMP-01", "4 Temperatura de agua", "Decimal de 40 a 130 °C (clave temp_agua)", "500 ms",
     "Muestra el valor con una décima en °C", "Rojo con > 110 °C; normal con ≤ 105 °C (R04)",
     "Conserva el último valor válido y registra ERROR"),
    ("REQ-TRB-01", "5 Presión de turbo", "Decimal de 0 a 2 bar (clave presion_turbo)", "100 ms",
     "Muestra el valor con dos decimales en bar", "Contorno ámbar con > 1.5 bar; normal con ≤ 1.4 bar (R05)",
     "Conserva el último valor válido y registra ERROR"),
    ("REQ-DIR-01", "6 Direccionales", "Enumeración off, izquierda, derecha (clave direccional)", "Parpadeo de 500 ms",
     "Testigo verde con flecha del lado elegido, alternando cada 500 ms", "Informativo; cede ante la emergencia (R06, R07)",
     "Otro texto se rechaza; conserva el último valor y registra ERROR"),
    ("REQ-ALT-01", "7 Luces altas", "Booleano 0/1 (clave luces_altas)", "Cada ciclo de 50 ms",
     "Testigo azul fijo, sin parpadeo", "Informativo (R07)", "Un valor distinto de 0/1 se rechaza y se registra"),
    ("REQ-EMG-01", "8 Intermitentes (emergencia)", "Booleano 0/1 (clave emergencia)", "Parpadeo de 500 ms",
     "Testigo ámbar alternando cada 500 ms con precedencia visual sobre el 6", "Informativo; registra INFO al activarse (R07)",
     "Un valor distinto de 0/1 se rechaza y se registra"),
    ("REQ-PAC-01", "9 Baja presión de aceite", "Calculado de presion_aceite con motor activo", "Retardo de 1 s",
     "Testigo rojo fijo con etiqueta CRITICA", "Enciende tras ≥ 1 s con < 1.0 bar; apaga tras ≥ 1 s con ≥ 1.2 bar; WARN prioritario (R02)",
     "Si la presión llega inválida se evalúa con el último valor válido"),
    ("REQ-FRN-01", "10 Falla de frenos", "Booleano 0/1 (clave falla_frenos)", "Parpadeo de 300 ms",
     "Testigo rojo parpadeante con etiqueta CRITICA, también con el motor apagado", "WARN prioritario al activarse (R08)",
     "Un valor distinto de 0/1 se rechaza y se registra"),
    ("REQ-ODO-01", "11 Odómetro (agregado tras la práctica)",
     "Calculado: distancia += velocidad mostrada (km/h) × tiempo transcurrido (h); kilometraje inicial en datos/odometro.txt",
     "Cada ciclo de 50 ms; se guarda cada 5 s y al cerrar",
     "Entero de 6 dígitos (000000–999999 km) dentro del velocímetro; nunca disminuye; INFO odometro_actualizado por cada km",
     "Tras 999999 vuelve a 000000 y cuenta la vuelta; no avanza con el motor apagado (R01) ni con velocidad 0",
     "Archivo ausente, corrupto o escribible por cualquiera: usa el respaldo .bak o inicia en 000000, avisa en pantalla y "
     "registra ERROR; odometro= en datos/vehiculo.conf se rechaza (clave_no_permitida)"),
    ("REQ-SIS-01", "Entrada externa", "Archivo datos/vehiculo.conf (clave=valor)", "Lectura cada 100 ms",
     "El tablero refleja el cambio sin reiniciar", "—", "Archivo ausente, vacío o corrupto: no se detiene y registra ERROR"),
    ("REQ-SIS-02", "Bitácoras", "Eventos del sistema", "Por evento",
     "INFO/WARN en eventos.log y ERROR en errores.log con fecha, nivel, componente y evento", "—",
     "Rotación por tamaño: el espacio total queda acotado"),
    ("REQ-SIS-03", "Seguridad", "Archivos de datos, configuración y bitácoras", "En cada lectura",
     "Bitácoras 640, carpeta de logs 750; rutas solo relativas al proyecto", "—",
     "Archivo escribible por cualquiera o sin permiso: se rechaza y se registra"),
    ("REQ-SIS-04", "Rendimiento", "Productor concurrente escribiendo cada 100 ms", "Continua",
     "Intervalo real de actualización ≤ 100 ms y memoria estable en una ejecución de 60 s", "—", "—"),
)

# (id, nombre, categoria, requisitos, nivel/tipo/tecnica, prioridad, precondiciones, datos, pasos, esperado,
#  pruebas automatizadas de respaldo, evidencia, defecto)
CASOS = (
    ("CT-01", "Velocidad válida desde el archivo", "Funcionamiento normal", ["REQ-VEL-01", "REQ-SIS-01"],
     "Sistema / funcional / partición de equivalencia", "Alta", "Aplicación con motor encendido",
     "velocidad=72 en datos/vehiculo.conf", ["Escribir velocidad=72 en el archivo.", "Esperar un ciclo de lectura (100 ms).",
                                             "Observar el velocímetro y eventos.log."],
     "El velocímetro muestra 72.0 km/h y eventos.log registra INFO valor_actualizado velocidad=72.",
     ["CP-91", "CP-01"], "docs/evidencias/junit.xml; bitacoras/exitosa/eventos.log", "—"),
    ("CT-02", "Tacómetro en rango normal", "Funcionamiento normal", ["REQ-RPM-01"],
     "Unitario / funcional / partición de equivalencia", "Media", "Motor encendido", "rpm=4500 y rpm=7799",
     ["Fijar 4500 rpm y avanzar 100 ms.", "Fijar 7799 rpm y avanzar 100 ms.", "Observar valor y color."],
     "Se muestran 4500 y 7799 rpm en color normal.", ["CP-02", "CP-13"], "junit.xml", "—"),
    ("CT-03", "Temperatura con su ciclo de 500 ms", "Funcionamiento normal", ["REQ-TMP-01"],
     "Unitario / funcional / partición de equivalencia", "Media", "Motor encendido", "temp_agua=90 y 120 °C",
     ["Fijar 90 °C y avanzar 500 ms.", "Fijar 120 °C y observar a los 250 y 500 ms."],
     "90 °C se muestra tras 500 ms; el cambio a 120 °C no aparece antes de cumplirse el ciclo.",
     ["CP-04", "CA-04"], "junit.xml; aceptacion.txt (CA-04)", "—"),
    ("CT-04", "Direccionales alternando cada 500 ms", "Funcionamiento normal", ["REQ-DIR-01"],
     "Sistema / funcional / transición observada", "Media", "Motor encendido", "direccional=izquierda, derecha y off",
     ["Seleccionar izquierda.", "Observar el testigo 6 en t = 0, 500 y 1000 ms.", "Cambiar a derecha y luego a off."],
     "Verde alternando cada 500 ms con flecha del lado elegido; apagado con off.", ["CP-30", "CP-57", "CA-06"],
     "aceptacion.txt (CA-06); captura 05", "—"),
    ("CT-05", "Luces altas fijas y emergencia con precedencia", "Funcionamiento normal", ["REQ-ALT-01", "REQ-EMG-01", "REQ-DIR-01"],
     "Sistema / funcional / tabla de decisión", "Media", "Motor encendido", "luces_altas=1; direccional=izquierda; emergencia=1",
     ["Activar luces altas y observar 500 ms.", "Seleccionar izquierda y activar emergencia.", "Observar los testigos 6 y 8."],
     "Testigo 7 azul fijo; con emergencia solo parpadea el 8 y el 6 no se ilumina.",
     ["CP-64", "CP-31", "CP-71", "CA-07", "CA-08"], "aceptacion.txt; capturas 05 y 06", "—"),
    ("CT-06", "Velocidad en sus límites 0 y 360", "Valores límite", ["REQ-VEL-01"],
     "Unitario / funcional / valores límite", "Alta", "Motor encendido", "0 y 360 km/h",
     ["Escribir velocidad=0 y leer.", "Escribir velocidad=360 y leer."], "Ambos valores se aceptan sin error.",
     ["CP-92", "CP-93", "CP-11", "CP-12"], "junit.xml", "—"),
    ("CT-07", "Tacómetro en el umbral 7799 / 8000", "Valores límite", ["REQ-RPM-01"],
     "Unitario / funcional / valores límite", "Alta", "Motor encendido", "7799 y 8000 rpm",
     ["Fijar 7799 rpm.", "Fijar 8000 rpm."], "7799 en normal; 8000 en rojo.", ["CP-13", "CP-16"], "junit.xml", "—"),
    ("CT-08", "Temperatura en el umbral 110 / 110.1", "Valores límite", ["REQ-TMP-01"],
     "Unitario / funcional / valores límite", "Alta", "Motor encendido", "110 y 110.1 °C",
     ["Fijar 110 °C y avanzar 500 ms.", "Fijar 110.1 °C y avanzar 500 ms."], "110 en normal; 110.1 en rojo.",
     ["CP-22", "CP-23"], "junit.xml", "—"),
    ("CT-09", "Turbo en el umbral 1.5 / 1.51", "Valores límite", ["REQ-TRB-01"],
     "Unitario / funcional / valores límite", "Media", "Motor encendido", "1.5 y 1.51 bar",
     ["Fijar 1.5 bar.", "Fijar 1.51 bar."], "1.5 sin advertencia; 1.51 con contorno ámbar.", ["CP-25", "CP-26"],
     "junit.xml; captura 03", "—"),
    ("CT-10", "Valores fuera de rango en el archivo", "Entradas inválidas", ["REQ-VEL-01", "REQ-RPM-01", "REQ-TMP-01", "REQ-TRB-01", "REQ-SIS-01"],
     "Integración / negativa / partición de equivalencia (clases inválidas)", "Alta", "Archivo con valores válidos previos",
     "velocidad=361 y -1; rpm=9001; temp_agua=39.9; presion_turbo=2.01",
     ["Escribir cada valor fuera de rango.", "Leer el archivo.", "Revisar el valor vigente y errores.log."],
     "Se conserva el último valor válido y errores.log registra fuera_de_rango.", ["CP-94"],
     "junit.xml; bitacoras/con_errores/errores.log", "—"),
    ("CT-11", "Formato incorrecto en el archivo", "Entradas inválidas", ["REQ-TMP-01", "REQ-RPM-01", "REQ-SIS-01"],
     "Integración / negativa / conjetura de errores", "Alta", "Archivo con valores válidos previos",
     "temp_agua=abc; rpm=4500.5; motor=si; direccional=arriba; velocidad=nan",
     ["Escribir cada valor inválido.", "Leer el archivo.", "Revisar el valor vigente y errores.log."],
     "Continúa con el último valor válido; errores.log registra dato_invalido con el texto recibido.", ["CP-95"],
     "junit.xml; bitacoras/con_errores/errores.log", "—"),
    ("CT-12", "Tipos inválidos en el modelo", "Entradas inválidas", ["REQ-RPM-01", "REQ-ACE-01", "REQ-TRB-01"],
     "Unitario / negativa / partición de equivalencia", "Media", "Estado inicial",
     "rpm=5000.0 y True; presion_aceite='alta'; presion_turbo=True",
     ["Enviar cada valor a EstadoCluster.", "Comprobar la excepción y el estado."],
     "Cada valor se rechaza con TypeError y el estado no cambia.", ["CP-40", "CP-41", "CP-44", "CP-48", "CP-52"], "junit.xml", "—"),
    ("CT-13", "Enumeración y booleanos inválidos", "Entradas inválidas", ["REQ-DIR-01", "REQ-ALT-01", "REQ-EMG-01", "REQ-FRN-01"],
     "Unitario / negativa / partición de equivalencia", "Media", "Estado inicial", "direccional='ADELANTE' y 1; motor=1",
     ["Enviar cada valor.", "Comprobar la excepción."], "Valores fuera del conjunto: ValueError; tipos incorrectos: TypeError.",
     ["CP-49", "CP-50", "CP-51"], "junit.xml", "—"),
    ("CT-14", "Histéresis del tacómetro", "Transiciones de estado", ["REQ-RPM-01"],
     "Unitario / funcional / transición de estados", "Alta", "Motor encendido", "8000, 7999, 7900, 7800 y 7799 rpm",
     ["Subir a 8000.", "Bajar a 7999 y 7900.", "Bajar a 7799."], "Rojo en 8000; conserva rojo en la zona 7800–7999; normal en 7799.",
     ["CP-14", "CP-15", "CP-27", "CA-03"], "aceptacion.txt (CA-03)", "—"),
    ("CT-15", "Testigo 9: retardo de 1 s e histéresis", "Transiciones de estado", ["REQ-PAC-01", "REQ-ACE-01"],
     "Unitario / funcional / transición de estados con tiempo", "Alta", "Motor encendido",
     "0.99 bar 999 ms y 1000 ms; 1.0, 1.1 y 1.2 bar",
     ["Mantener 0.99 bar y observar a los 999 y 1000 ms.", "Subir a 1.2 bar y observar a los 1000 ms."],
     "Apagado a 999 ms y rojo a 1000 ms; el medidor 2 ya está ámbar; se apaga tras 1 s en 1.2 bar.",
     ["CP-17", "CP-18", "CP-20", "CP-70", "CA-09"], "aceptacion.txt (CA-09); captura 04", "—"),
    ("CT-16", "Falla de frenos: parpadeo de 300 ms aun con motor apagado", "Transiciones de estado", ["REQ-FRN-01"],
     "Sistema / funcional / transición de estados", "Alta", "Motor apagado", "falla_frenos=1 y 0",
     ["Activar falla de frenos con el motor apagado.", "Observar en t = 0, 300, 600 y 900 ms.", "Desactivar."],
     "Rojo alternando cada 300 ms aunque el motor esté apagado; apagado con falla_frenos=0.",
     ["CP-32", "CP-66", "CA-10"], "aceptacion.txt (CA-10); captura 07", "DEF-01 (rechazado)"),
    ("CT-17", "Archivo vacío o con claves faltantes", "Archivos y errores", ["REQ-SIS-01"],
     "Integración / negativa / conjetura de errores", "Alta", "Lector creado", "Archivo vacío; archivo sin la clave velocidad",
     ["Leer un archivo vacío.", "Leer un archivo sin la clave velocidad."],
     "Estado definido (valores iniciales o último válido) y ERROR clave_faltante registrado.", ["CP-96"],
     "junit.xml; bitacoras/con_errores/errores.log", "—"),
    ("CT-18", "Archivo inexistente y recuperación sin reiniciar", "Archivos y errores", ["REQ-SIS-01"],
     "Integración / negativa / conjetura de errores", "Alta", "Lector creado sin archivo", "Ruta inexistente; luego archivo restaurado",
     ["Leer sin archivo dos veces.", "Restaurar el archivo.", "Leer de nuevo y corregir una entrada inválida."],
     "No termina; un solo ERROR archivo_inexistente; INFO archivo_recuperado al volver; retoma sin reinicio.",
     ["CP-97", "CP-100", "CP-110"], "bitacoras/con_errores", "—"),
    ("CT-19", "Configuración y archivos de escenarios inválidos", "Archivos y errores", ["REQ-SIS-01", "REQ-SIS-03"],
     "Integración / negativa / conjetura de errores", "Media", "—",
     "cluster.ini inexistente, sin secciones o con valores fuera de rango; CSV vacío o con filas inválidas",
     ["Cargar cada archivo.", "Revisar los valores aplicados y los errores informados."],
     "Se usan valores por defecto con un error claro; nunca se detiene.", ["CP-106", "CP-118", "CP-79", "CP-80", "CP-84"],
     "junit.xml", "—"),
    ("CT-20", "Integración archivo → hilo lector → interfaz", "Integración", ["REQ-SIS-01", "REQ-RPM-01", "REQ-FRN-01"],
     "Integración / funcional / basada en escenarios", "Alta", "Aplicación abierta en modo archivo",
     "rpm=8000 y falla_frenos=1; luego rpm=1500; 300 escrituras concurrentes",
     ["Abrir la aplicación.", "Escribir el archivo.", "Observar el tablero y las bitácoras.", "Repetir con un escritor concurrente."],
     "El tablero cambia sin reiniciar, los controles quedan deshabilitados, se registran los WARN y nunca hay lecturas parciales.",
     ["CP-115", "CP-98", "CP-78"], "junit.xml; logs de la prueba", "DEF-02 (cerrado)"),
    ("CT-21", "Aceptación completa sobre la interfaz real", "Integración",
     ["REQ-VEL-01", "REQ-ACE-01", "REQ-RPM-01", "REQ-TMP-01", "REQ-TRB-01", "REQ-DIR-01", "REQ-ALT-01", "REQ-EMG-01", "REQ-PAC-01", "REQ-FRN-01"],
     "Sistema / aceptación / dirigida por datos", "Alta", "tests/datos/escenarios_aceptacion.csv",
     "10 escenarios, 72 pasos", ["Ejecutar python -m aceptacion.escenarios con el CSV.", "Comparar cada paso con lo dibujado."],
     "10/10 escenarios aprobados; una expectativa falsa se detecta como FALLIDO.",
     ["CA-01", "CA-02", "CA-03", "CA-04", "CA-05", "CA-06", "CA-07", "CA-08", "CA-09", "CA-10", "CP-89", "CP-90"],
     "docs/evidencias/aceptacion.txt", "—"),
    ("CT-22", "Intervalo real de actualización", "Rendimiento", ["REQ-SIS-04"],
     "Sistema / rendimiento / medición", "Media", "VM con Xvfb; simulador como proceso aparte",
     "Ejecución de 60 s con escrituras cada 100 ms", ["Ejecutar tools/ejecucion_prolongada.py --duracion-s 60.",
                                                      "Leer el intervalo promedio y p95."],
     "Intervalo promedio ≤ 100 ms.", ["metricas:intervalo"], "docs/evidencias/metricas.txt", "—"),
    ("CT-23", "Ejecución prolongada: memoria y bitácoras acotadas", "Rendimiento", ["REQ-SIS-02", "REQ-SIS-04"],
     "Sistema / rendimiento / medición", "Media", "Igual que CT-22; bitácoras de 16 KB con 2 respaldos",
     "60 s reales y 3000 ciclos acelerados", ["Medir RSS y tamaño de bitácoras al inicio y al final.", "Ejecutar CP-104."],
     "Memoria estable y bitácoras dentro del límite teórico.", ["CP-104", "metricas:acotado"], "metricas.txt; junit.xml", "—"),
    ("CT-24", "Permisos de archivos", "Seguridad", ["REQ-SIS-03"],
     "Integración / seguridad / conjetura de errores", "Alta", "Linux con usuario sin privilegios",
     "Archivo de datos 000 y 666; bitácoras nuevas",
     ["Quitar el permiso de lectura y leer.", "Hacer el archivo escribible por cualquiera y leer.", "Revisar el modo de las bitácoras."],
     "Lectura rechazada y registrada; archivo 666 rechazado; bitácoras 640 y carpeta 750.", ["CP-101", "CP-102", "CP-103"],
     "junit.xml (VM)", "—"),
    ("CT-25", "Entradas maliciosas y rutas fuera del proyecto", "Seguridad", ["REQ-SIS-03", "REQ-SIS-01"],
     "Integración / seguridad / conjetura de errores", "Alta", "—",
     "Líneas sin formato, claves desconocidas, valores de 40 caracteres, archivo de 5000 bytes; logs = /etc en la configuración",
     ["Leer el archivo malicioso.", "Cargar la configuración con una ruta absoluta."],
     "Todo se rechaza con su error; la ruta absoluta se reemplaza por la ruta por defecto.", ["CP-107", "CP-106"],
     "junit.xml", "—"),
    # Casos de la practica en clase (tema asignado por el profesor: odometro), con la duracion corregida.
    ("CT-26", "Odómetro: acumula la distancia recorrida (práctica, CP-ODO-01)", "Funcionamiento normal", ["REQ-ODO-01"],
     "Sistema / funcional / partición de equivalencia", "Alta", "datos/odometro.txt = 62; aplicación abierta; motor encendido",
     "velocidad=120 km/h constante durante 45 s (1.5 km)",
     ["Confirmar que el odómetro muestra 000062.", "Escribir motor=1 y velocidad=120.", "Esperar 45 s.",
      "Leer el odómetro y eventos.log; cerrar y volver a abrir."],
     "El odómetro muestra 000063, eventos.log registra INFO odometro_actualizado km=000063 y el kilometraje se conserva "
     "al reiniciar; con motor apagado o velocidad 0 no avanza.",
     ["CP-120", "CP-121", "CP-123", "CP-127", "CP-128", "CP-134", "CP-135", "CP-137"],
     "practica/evidencia_despues/ (CP-ODO-01); junit.xml", "DEF-03 (cerrado)"),
    ("CT-27", "Odómetro: vuelta a 000000 tras 999999 (práctica, CP-ODO-02)", "Valores límite", ["REQ-ODO-01"],
     "Sistema / funcional / valores límite y transición de estado", "Alta", "datos/odometro.txt = 999999; motor encendido",
     "velocidad=360 km/h durante 15 s (1.5 km)",
     ["Iniciar con el odómetro en 999999.", "Escribir velocidad=360.", "Esperar 15 s.", "Leer el odómetro y las bitácoras."],
     "Pasa de 999999 a 000000 sin error ni 7 dígitos y sigue contando; eventos.log registra la vuelta "
     "(odometro_actualizado km=000000 vuelta_a_cero).",
     ["CP-122", "CP-124", "CP-137"], "practica/evidencia_despues/ (CP-ODO-02); junit.xml", "DEF-03 (cerrado)"),
    ("CT-28", "Odómetro: archivo corrupto o inseguro (práctica, CP-ODO-03)", "Archivos y errores",
     ["REQ-ODO-01", "REQ-SIS-01", "REQ-SIS-03"],
     "Integración / negativa / conjetura de errores", "Alta", "datos/odometro.txt con el texto abc y sin respaldo",
     "odometro.txt = abc; también: respaldo válido, archivo 666, sin lectura, fuera de rango, no UTF-8, odometro= en vehiculo.conf",
     ["Escribir abc en datos/odometro.txt.", "Abrir la aplicación.", "Observar el tablero, el aviso y errores.log.",
      "Repetir con las demás variantes."],
     "No se detiene; arranca en 000000 con el aviso «Odometro: archivo invalido, se inicio en 000000» y ERROR "
     "odometro_invalido; con respaldo válido se restaura de él; odometro= en vehiculo.conf se rechaza.",
     ["CP-125", "CP-126", "CP-129", "CP-130", "CP-131", "CP-132", "CP-133", "CP-136"],
     "practica/evidencia_despues/ (CP-ODO-03); junit.xml", "DEF-03 (cerrado)"),
)

CATEGORIAS = (("Funcionamiento normal", 5), ("Valores límite", 4), ("Entradas inválidas", 4), ("Transiciones de estado", 3),
              ("Archivos y errores", 3), ("Integración", 2), ("Rendimiento", 2), ("Seguridad", 2))

RIESGOS = (
    ("Interpretación ambigua de la especificación (D1–D7)", "Media", "Alto", "Decisiones documentadas y aprobadas; casos que las verifican"),
    ("Valores esperados generados por la misma IA que escribió el código", "Media", "Alto", "Esperados derivados de los umbrales; CP-90 demuestra que el oráculo detecta diferencias; revisión del equipo"),
    ("Lectura parcial del archivo durante una escritura concurrente", "Media", "Alto", "Escritura atómica; validación por clave; CP-98"),
    ("Python de Microsoft Store en Windows falla al cargar Tcl/Tk", "Alta (en ese equipo)", "Medio", "Usar Python de python.org; la ejecución oficial es la de la VM"),
    ("La pantalla virtual (Xvfb) no refleja un monitor real", "Baja", "Medio", "Capturas reales; ejecución manual en Windows"),
    ("Crecimiento ilimitado de bitácoras", "Baja", "Alto", "Rotación por tamaño; CT-23"),
    ("Revisión cruzada, escenario sorpresa y observaciones del profesor aún no realizados", "Alta", "Medio",
     "Formato listo en el anexo C; integrar cuando ocurran"),
    ("Un caso en tiempo real con exactamente 1 km queda en el borde del cambio de dígito", "Media", "Medio",
     "Duraciones con margen (45 s y 15 s = 1.5 km); pruebas con reloj simulado (CP-120 a CP-122); sección 10.1"),
    ("Pérdida o alteración del kilometraje", "Baja", "Alto",
     "Escritura atómica con respaldo .bak, permisos 640, rechazo de archivos escribibles por cualquiera (CT-28)"),
)


def resumen_practica(carpeta):
    """Lee practica/<carpeta>/resumen.txt: lineas 'caso|duracion_s|esperado|obtenido|estado'."""
    ruta = PRACTICA / carpeta / "resumen.txt"
    if not ruta.exists():
        return []
    return [linea.split("|") for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.count("|") == 4]


def casos_en_matriz():
    texto = leer(DOCS / "matriz_trazabilidad.md")
    return len(set(re.findall(r"^\| ((?:CP|CA)-\d+) ", texto, flags=re.M)))


def metrica(lineas, patron):
    for linea in lineas:
        m = re.search(patron, linea)
        if m:
            return m.group(1)
    return None


def evaluar(casos, ids, metricas):
    ejec, faltan, extra = [], [], []
    for ident in ids:
        if ident == "metricas:intervalo":
            valor = metrica(metricas, r"promedio=([\d.]+)")
            ok = valor is not None and float(valor) <= 100
            extra.append((ok, f"intervalo promedio medido {valor} ms"))
        elif ident == "metricas:acotado":
            ok = metrica(metricas, r"acotado=(si)") == "si"
            dif = metrica(metricas, r"diferencia=(-?\d+) KB")
            extra.append((ok, f"bitácoras acotadas, memoria +{dif} KB en 60 s"))
        else:
            e = ejecuciones(casos, ident)
            ejec.extend(e) if e else faltan.append(ident)
    n = {r: sum(c["res"] == r for c in ejec) for r in ("PASS", "FAIL", "SKIP")}
    if faltan or n["SKIP"]:
        estado = "Bloqueada"
    elif n["FAIL"] or not all(ok for ok, _ in extra):
        estado = "Fallida"
    else:
        estado = "Aprobada"
    partes = []
    if ejec:
        partes.append(f"{len(ejec)} ejecuciones automatizadas: {n['PASS']} aprobadas, {n['FAIL']} fallidas, {n['SKIP']} omitidas")
    partes += [texto for _, texto in extra]
    if faltan:
        partes.append(f"sin ejecución registrada: {', '.join(faltan)}")
    return estado, "; ".join(partes) + "."


def historial_git():
    r = subprocess.run(["git", "log", "--reverse", "--date=short", "--format=%h|%ad|%s"], cwd=RAIZ,
                       capture_output=True, text=True, check=False)
    return [linea.split("|", 2) for linea in r.stdout.strip().splitlines() if linea.count("|") >= 2]


def equipo():
    memoria = "no disponible"
    meminfo = pathlib.Path("/proc/meminfo")
    if meminfo.exists():
        kb = int(meminfo.read_text().split("MemTotal:")[1].split()[0])
        memoria = f"{kb / 1024 / 1024:.1f} GB"
    return f"{os.cpu_count()} CPU, {memoria} de RAM"


def construir():
    casos, fecha = cargar_junit()
    aceptacion, _ = cargar_aceptacion()
    metricas = leer(EVID / "metricas.txt").splitlines()
    historial = historial_git()
    hoy = datetime.date.today().isoformat()
    evaluados = [(c, *evaluar(casos, c[10], metricas)) for c in CASOS]
    practica_aprobada = all(estado == "Aprobada" for c, estado, _ in evaluados if c[0] in CASOS_PRACTICA)
    estado_def03 = ("Cerrado: se implementó el elemento 11 y los casos CT-26 a CT-28 están aprobados." if practica_aprobada
                    else "Corregido, en verificación: algún caso CT-26 a CT-28 no está aprobado.")
    antes, despues = resumen_practica("evidencia_antes"), resumen_practica("evidencia_despues")
    estado_req = {}
    for c, estado, _ in evaluados:
        for req in c[3]:
            estado_req.setdefault(req, []).append((c[0], estado))

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10.5)
    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.add_run(f"{IDENTIFICADOR} v{VERSION_DOC} — Documento completo de pruebas — página ")
    numero_pagina(pie)

    # Portada y control documental
    for _ in range(2):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Tarea 2\nDocumento completo de pruebas de software\nClúster simulado del Ferrari F40 (1987)")
    r.bold = True
    r.font.size = Pt(20)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    doc.add_heading("1. Control documental", level=1)
    tabla(doc, ["Campo", "Valor"], list(IDENTIFICACION) + [
        ("Identificador", IDENTIFICADOR),
        ("Versión del documento", VERSION_DOC),
        ("Autores", "César Saúl Vázquez Preciado e Ian Josué Cota Flores (Equipo 3)"),
        ("Fecha de esta versión", hoy),
        ("Estado", "Versión para revisión. Integrada la práctica en clase (odómetro, CT-26 a CT-28). Pendientes: "
                   "revisión cruzada, escenario sorpresa y observaciones del profesor (anexo C)"),
        ("Versión del software probado", version_software()),
        ("Fecha de ejecución de las pruebas", fecha or "no registrada"),
        ("Repositorio", "https://github.com/ayocesaar/cluster-f40 (privado)"),
    ], anchos=[5, 11.5])
    doc.add_heading("Historial del documento", level=2)
    tabla(doc, ["Versión", "Fecha", "Cambio", "Commit"], [
        ("1.0", "2026-10-29", "Tarea 1: informe de pruebas con 25 casos, 108 ejecuciones y matriz de trazabilidad", "eb575e6"),
        ("1.1", "2026-10-29", "Normas ISO verificadas, marco normativo y declaración de colaboración", "d5da68a"),
        ("1.2", "2026-11-09", "Interfaz 8-bit; regresión completa sin cambiar pruebas", "1848f4c"),
        ("1.3", "2026-11-10", "Datos externos, bitácoras, hilo lector, pruebas P01–P12 e informe técnico", "83ca343"),
        ("2.0", "2026-11-16", "Tarea 2: estructura obligatoria, requisitos REQ por elemento, 25 casos con distribución por "
                              "categoría, prioridades, criterios, riesgos con probabilidad, métricas y anexos", "749d580"),
        ("2.1", "2026-11-18", "Práctica en clase (odómetro): REQ-ODO-01, casos CT-26 a CT-28 con resultados antes y después "
                              "de implementar el elemento 11, DEF-03 y corrección de las duraciones de los casos", "a1adda6"),
        (VERSION_DOC, hoy, "Auditoría de robustez: DEF-04 a DEF-14 corregidos, pruebas CP-138 a CP-151 (fallaban antes de "
                          "corregir), fuzzing y prueba de caos con la aplicación real", "esta versión"),
    ], anchos=[1.6, 2.4, 10, 2.5])
    doc.add_page_break()

    # Introduccion
    doc.add_heading("2. Introducción", level=1)
    doc.add_paragraph(
        "El sistema bajo prueba simula el clúster de instrumentos de un Ferrari F40 (1987): diez elementos que se "
        "controlan con datos externos, se validan, se dibujan en una interfaz Tkinter de estética 8-bit y se registran "
        "en bitácoras, más un odómetro (elemento 11) que se calcula a partir de la velocidad. No hay ECU ni sensores "
        "reales; los rangos son parámetros didácticos.")
    doc.add_paragraph(
        "Objetivo de este documento: especificar y evidenciar las pruebas que demuestran que el clúster cumple sus "
        "requisitos, de forma que otra persona pueda repetirlas. Importancia: dos de los elementos son testigos de "
        "seguridad (presión de aceite y frenos); una advertencia que no aparece o aparece tarde es el fallo más grave "
        "posible en un tablero, y las pruebas lo vigilan en cada cambio.")
    doc.add_paragraph("Este documento parte de la Tarea 1 (versión 1.0) y muestra su evolución en el historial y en el "
                      "anexo B.")
    doc.add_paragraph(
        "Versión 2.1: en la práctica en clase el profesor asignó el odómetro. Los tres casos diseñados (CP-ODO-01 a 03) se "
        "ejecutaron primero sobre la versión 749d580, que no tenía odómetro, y revelaron el defecto DEF-03. Después se "
        "implementó el elemento 11 sin modificar ninguna prueba anterior y los casos se repitieron como CT-26 a CT-28 "
        "(sección 10.1).")

    # Alcance
    doc.add_heading("3. Alcance", level=1)
    doc.add_heading("Funciones incluidas", level=2)
    vinetas(doc, ["Los diez elementos y sus reglas R01–R08.", "El odómetro (elemento 11): cálculo, vuelta a cero, "
                  "persistencia en datos/odometro.txt con respaldo y manejo de archivos inválidos.",
                  "Entrada por datos/vehiculo.conf y configuración externa.",
                  "Validación, recuperación de errores y bitácoras.", "Hilo lector, comunicación productor-consumidor y escritura atómica.",
                  "Permisos de archivos, rendimiento y ejecución prolongada.", "Interfaz Tkinter (dibujo de los once elementos)."])
    doc.add_heading("Exclusiones", level=2)
    vinetas(doc, ["Hardware, ECU, sensores y calibraciones reales del F40.",
                  "Acceso desde otros dispositivos por red (solicitado por el profesor; pendiente de construir).",
                  "Plataformas distintas de Ubuntu 22.04 y Windows 11."])
    doc.add_heading("Limitaciones y supuestos", level=2)
    vinetas(doc, ["Las pruebas de interfaz usan una pantalla virtual (Xvfb); la vista en un monitor real se revisa a mano.",
                  "Las pruebas de permisos POSIX solo aplican en Linux; en Windows se omiten.",
                  "Se supone que el archivo de datos lo escribe un solo usuario (el dueño) con escritura atómica.",
                  "Las categorías de los elementos 2, 3 y 5 (información en línea) están por confirmar con el profesor."])

    # Sistema bajo prueba
    doc.add_heading("4. Sistema bajo prueba", level=1)
    figura(doc, DOCS / "diagramas" / "arquitectura.png", "Figura 1. Diagrama de componentes.")
    figura(doc, DOCS / "diagramas" / "flujo_actualizacion.png", "Figura 2. Flujo de una actualización.")
    tabla(doc, ["Aspecto", "Detalle"], [
        ("Archivos", "config/cluster.ini; datos/vehiculo.conf; datos/odometro.txt y su respaldo datos/odometro.txt.bak; "
                     "logs/eventos.log y logs/errores.log; tests/datos/escenarios_aceptacion.csv"),
        ("Procesos e hilos", "Proceso productor externo (tools/simulador.py o tools/escribir_dato.py); hilo lector; hilo principal de Tkinter"),
        ("Dependencias", f"Python {platform.python_version()} con Tkinter (biblioteca estándar). Pruebas: pytest {version('pytest')}, "
                         f"coverage {version('coverage')}, Pillow {version('Pillow')}, python-docx {version('python-docx')}; Xvfb; LibreOffice"),
        ("Registros", "Formato: fecha ISO 8601, nivel, componente, evento, detalle y resultado; rotación por tamaño"),
    ], anchos=[3.5, 13])

    # Requisitos
    doc.add_heading("5. Requisitos", level=1)
    doc.add_paragraph("Once requisitos, uno por elemento (formato de la Tarea 2; REQ-ODO-01 se agregó con la práctica en "
                      "clase), y cuatro requisitos transversales del sistema.")
    for req in REQUISITOS:
        ficha(doc, list(zip(("Identificador", "Elemento", "Entrada", "Frecuencia", "Resultado", "Advertencia", "Error"), req)))

    # Estrategia
    doc.add_heading("6. Estrategia", level=1)
    tabla(doc, ["Nivel", "Qué se prueba", "Cómo"], [
        ("Unitario", "Reglas del modelo, validación, conversión, configuración", "pytest con reloj simulado"),
        ("Integración", "Archivo → hilo lector → buzón → interfaz; bitácoras; permisos", "pytest con archivos temporales e hilos reales"),
        ("Sistema", "Aplicación completa y escenarios de aceptación sobre la ventana real", "Xvfb + ejecutor dirigido por CSV; medición de 60 s"),
    ], anchos=[2.5, 8, 6])
    tabla(doc, ["Técnica", "Por qué"], [
        ("Partición de equivalencia", "Reduce cada entrada a clases válidas e inválidas con un representante"),
        ("Valores límite", "Los umbrales (8000 rpm, 110 °C, 1.5 bar, 1 s) son donde más fallan las comparaciones"),
        ("Transición de estados", "La histéresis y los parpadeos dependen del estado previo y del tiempo"),
        ("Conjetura de errores", "Archivos ausentes, corruptos, concurrentes o con permisos incorrectos"),
        ("Tabla de decisión", "Combinaciones de emergencia y direccional (precedencia visual)"),
        ("Medición", "Rendimiento real: intervalo, memoria y tamaño de bitácoras"),
    ], anchos=[4.5, 12])
    vinetas(doc, [
        "Prioridad alta: testigos de seguridad 9 y 10, umbrales, entrada externa, validación y permisos. Media: lecturas "
        "informativas y rendimiento. Baja: aspecto visual.",
        "Automatización: todos los casos están automatizados con pytest. Manual: la revisión visual en un monitor real y la "
        "demostración en vivo.",
        "Regresión: después de cada cambio se ejecuta la suite completa, la aceptación, las capturas y la medición; el "
        "script de cada etapa compara una huella de las pruebas existentes y no guarda cambios si alguna cambió o falló."])

    # Ambiente
    doc.add_heading("7. Ambiente", level=1)
    tabla(doc, ["Componente", "Valor"], [
        ("Sistema operativo", sistema_operativo()),
        ("Equipo", f"Máquina virtual VirtualBox ({equipo()})"),
        ("Pantalla de pruebas", "Xvfb 1280x1024 a 24 bits; ventana del tablero 1060x640 aprox."),
        ("Lenguaje y bibliotecas", f"Python {platform.python_version()}, Tkinter, pytest {version('pytest')}, coverage {version('coverage')}"),
        ("Directorios", "logic/, sistema/, ui/, tests/, tools/, config/, datos/, logs/, docs/, informe/"),
        ("Datos de prueba", "datos/vehiculo.conf; tests/datos/escenarios_aceptacion.csv; archivos temporales creados por cada prueba"),
    ], anchos=[4, 12.5])
    codigo(doc, ["# Inicio", "./iniciar.sh                      # aplicación (Windows: abrir_cluster.bat)",
                 "xvfb-run -a python -m pytest -v   # pruebas", "# Detención",
                 "Cerrar la ventana o Ctrl+C; la aplicación detiene el hilo lector y registra 'sistema fin'"])

    # Riesgos
    doc.add_heading("8. Riesgos", level=1)
    tabla(doc, ["Riesgo", "Probabilidad", "Impacto", "Mitigación"], RIESGOS, anchos=[5.5, 2.3, 1.8, 6.9])

    # Criterios
    doc.add_heading("9. Criterios", level=1)
    tabla(doc, ["Criterio", "Condición"], [
        ("Entrada", "Código en el repositorio; entorno .venv creado; Xvfb disponible; config/ y datos/ presentes; la suite de la versión anterior pasa"),
        ("Salida", "100% de los casos planeados ejecutados; 0 casos fallidos de prioridad alta; 100% de los requisitos con al menos un caso; 0 defectos abiertos de severidad alta"),
        ("Suspensión", "El ambiente falla (Tk, Xvfb o LibreOffice), un defecto bloquea más del 20% de los casos o cambia un requisito"),
        ("Reanudación", "Ambiente restaurado, defecto bloqueante corregido o requisito actualizado; se repite la regresión completa"),
    ], anchos=[3, 13.5])

    # Casos
    doc.add_heading("10. Casos de prueba", level=1)
    conteo = {cat: sum(1 for c in CASOS if c[2] == cat) for cat, _ in CATEGORIAS}
    tabla(doc, ["Categoría", "Mínimo", "Incluidos"], [(cat, minimo, conteo[cat]) for cat, minimo in CATEGORIAS]
          + [("Total", 25, len(CASOS))], anchos=[8, 4, 4])
    doc.add_paragraph("CT-01 a CT-25 cubren la distribución mínima. CT-26 a CT-28 son los tres casos de la práctica en clase "
                      "(tema asignado por el profesor: odómetro), ya con la duración corregida; su ejecución antes y después "
                      "de implementar el odómetro está en la sección 10.1.")
    for c, estado, obtenido in evaluados:
        doc.add_heading(f"{c[0]} — {c[1]}", level=2)
        ficha(doc, [
            ("ID y nombre", f"{c[0]}: {c[1]}"), ("Categoría", c[2]), ("Requisito", ", ".join(c[3])),
            ("Nivel, tipo y técnica", c[4]), ("Prioridad", c[5]), ("Precondiciones", c[6]), ("Datos", c[7]),
            ("Pasos", "\n".join(f"{i}. {p}" for i, p in enumerate(c[8], 1))), ("Esperado", c[9]),
            ("Obtenido", obtenido), ("Estado", estado),
            ("Evidencia y defecto", f"{c[11]}; pruebas {', '.join(i for i in c[10] if not i.startswith('metricas'))} — defecto: {c[12]}"),
        ], estado=estado)

    # Practica en clase
    doc.add_heading("10.1 Práctica en clase: ejecución antes y después", level=2)
    doc.add_paragraph(
        "Cada caso se ejecutó con la aplicación completa (modo archivo, Xvfb) mediante practica/ejecutar_casos.py: primero "
        "sobre la versión 749d580 (sin odómetro) y después sobre la versión con el elemento 11. «v2» es el caso con la "
        "duración corregida; SONDA intenta escribir odometro=999999 en datos/vehiculo.conf.")
    if antes or despues:
        obtenido_despues = {fila[0]: fila for fila in despues}
        filas = []
        for caso, segundos, esperado, obtenido, estado in antes or despues:
            d = obtenido_despues.get(caso)
            filas.append((caso, f"{segundos} s", esperado, f"{estado}: {obtenido}" if antes else "—",
                          f"{d[4]}: {d[3]}" if d else "sin ejecución registrada"))
        tabla(doc, ["Caso", "Duración", "Esperado", "Antes (749d580)", "Después (elemento 11)"], filas,
              anchos=[2.3, 1.5, 3.6, 4.5, 4.6])
    else:
        doc.add_paragraph("Sin ejecución registrada en practica/evidencia_antes ni practica/evidencia_despues.")
    doc.add_paragraph("Corrección del propio caso (resultado de la ejecución):")
    tabla(doc, ["Caso", "Diseño original", "Corrección", "Motivo"], [
        ("CP-ODO-01", "120 km/h durante 30 s (1 km exacto)", "45 s (1.5 km) → CT-26",
         "Con 1 km exacto el resultado depende de décimas de segundo (arranque de la aplicación y primer ciclo de lectura); "
         "con 1.5 km queda medio kilómetro de margen. La tabla anterior muestra lo observado con ambas duraciones."),
        ("CP-ODO-02", "360 km/h durante 10 s (1 km exacto)", "15 s (1.5 km) → CT-27", "Mismo motivo que CP-ODO-01."),
        ("CP-ODO-03", "odometro.txt = abc", "Sin cambio; se agregaron variantes (respaldo, permisos, formato) → CT-28",
         "El caso cubría un solo tipo de archivo inválido."),
    ], anchos=[2.3, 4, 4.2, 6])

    # Trazabilidad
    doc.add_heading("11. Matriz de trazabilidad", level=1)
    filas = []
    for req, elemento, *_ in REQUISITOS:
        ligados = estado_req.get(req, [])
        cts = [ct for ct, _ in ligados]
        tecnicas = sorted({re.sub(r"\s*\(.*?\)| con tiempo", "", c[4].split("/")[-1]).strip()
                           for c in CASOS if c[0] in cts})
        prioridad = "Alta" if any(c[5] == "Alta" for c in CASOS if c[0] in cts) else "Media"
        estado = "Aprobado" if ligados and all(e == "Aprobada" for _, e in ligados) else ("Sin casos" if not ligados else "Con pendientes")
        defectos = sorted({c[12] for c in CASOS if c[0] in cts and c[12] != "—"})
        filas.append((req, elemento, ", ".join(cts) or "—", "; ".join(tecnicas), prioridad, estado, ", ".join(defectos) or "—"))
    tabla(doc, ["Requisito", "Elemento", "Casos", "Técnica", "Prioridad", "Estado", "Defecto"], filas,
          anchos=[2.2, 2.6, 3.2, 4.4, 1.5, 1.6, 1.5])
    doc.add_paragraph(f"La matriz detallada de las pruebas automatizadas ({casos_en_matriz()} casos CP/CA) está en "
                      "docs/matriz_trazabilidad.md.")

    # Defectos
    doc.add_heading("12. Defectos", level=1)
    doc.add_paragraph("Formato de registro: identificador y título, severidad y prioridad, versión y ambiente, caso relacionado, "
                      "pasos para reproducir, resultado esperado y observado, evidencia y estado.")
    defectos = (
        [("Identificador y título", "DEF-01 — El testigo de falla de frenos parpadea con el motor apagado"),
         ("Severidad y prioridad", "Media / media (asignadas al reportarlo)"),
         ("Versión y ambiente", "commit daad491; Ubuntu 22.04, Python 3.10"),
         ("Caso relacionado", "CT-16 (CP-66)"),
         ("Pasos para reproducir", "1. Crear el estado con motor apagado. 2. falla_frenos=1. 3. Observar el testigo 10."),
         ("Esperado y observado", "Se esperaba apagado (interpretando R01 como apagado general); se observó parpadeo cada 300 ms."),
         ("Evidencia", "docs/registro_defectos.md; commits daad491 y 382a8d9"),
         ("Estado", "Rechazado: R08 no condiciona el testigo al motor. La recomendación original fue de la IA (anexo D).")],
        [("Identificador y título", "DEF-02 — Error de permiso falso al leer durante una escritura concurrente en Windows"),
         ("Severidad y prioridad", "Media / alta"),
         ("Versión y ambiente", "Copia de trabajo previa al commit efc89ad; Windows 11, Python 3.11"),
         ("Caso relacionado", "CT-20 (CP-98, prueba P08)"),
         ("Pasos para reproducir", "1. Escribir el archivo 300 veces con escritura atómica. 2. Leerlo cada 1 ms en otro hilo. 3. Revisar errores.log."),
         ("Esperado y observado", "Se esperaba errores.log vacío; se observaron registros ERROR permiso_denegado. Los datos leídos sí eran consistentes."),
         ("Evidencia", "docs/bitacora_ia.md (Etapa 11); CP-98 aprobado en Windows y en la VM tras la corrección"),
         ("Estado", "Cerrado: el lector reintenta la apertura 5 veces en Windows antes de declarar un error de permisos.")],
        [("Identificador y título", "DEF-03 — El clúster no implementa el odómetro"),
         ("Severidad y prioridad", "Media / alta: no afecta la seguridad, pero falta una función de información en línea"),
         ("Versión y ambiente", "commit 749d580; Ubuntu 22.04, Python 3.10, Xvfb"),
         ("Caso relacionado", "CT-26 a CT-28 (CP-ODO-01 y 02 fallidos, CP-ODO-03 bloqueado en la práctica)"),
         ("Pasos para reproducir", "1. Abrir el clúster en modo archivo. 2. Escribir motor=1 y velocidad=120. 3. Esperar 30 s y buscar "
                                   "el odómetro. 4. Agregar odometro=999999 a datos/vehiculo.conf y revisar errores.log."),
         ("Esperado y observado", "Se esperaba un contador de 6 dígitos que subiera 1 km; no había contador y la clave odometro se "
                                  "rechazaba como clave_desconocida."),
         ("Evidencia", "practica/evidencia_antes/ (capturas, bitácoras y resumen.txt); docs/registro_defectos.md"),
         ("Estado", estado_def03)],
    )
    for d in defectos:
        ficha(doc, d)
    adicionales = [d for d in cargar_defectos() if d["ID"] not in ("DEF-01", "DEF-02", "DEF-03")]
    if adicionales:
        doc.add_paragraph("Auditoría de robustez (versión 2.2): cada defecto se reprodujo con una prueba que falló en 5e9506b "
                          "(docs/evidencias/robustez_antes.txt) y pasa después de corregir. La ficha completa está en "
                          "docs/registro_defectos.md.")
        tabla(doc, ["Defecto", "Título", "Severidad / prioridad", "Caso", "Estado"],
              [(d["ID"], d["Titulo"], d.get("Severidad / prioridad", "—"), d.get("Caso de prueba", "—"), d.get("Estado", "—"))
               for d in adicionales], anchos=[1.6, 6.4, 2.6, 3.4, 2.5])

    # Resultados
    doc.add_heading("13. Resultados", level=1)
    total = len(evaluados)
    estados = {e: sum(1 for _, s, _ in evaluados if s == e) for e in ("Aprobada", "Fallida", "Bloqueada")}
    ejecutados = estados["Aprobada"] + estados["Fallida"]
    reqs_con_caso = sum(1 for req, *_ in REQUISITOS if estado_req.get(req))
    auto = {r: sum(c["res"] == r for c in casos) for r in ("PASS", "FAIL", "SKIP")}
    aprob_ca = sum(1 for a in aceptacion.values() if a["estado"] == "APROBADO")
    tabla(doc, ["Indicador", "Valor"], [
        ("Planeados y ejecutados", f"{total} planeados; {ejecutados} con resultado"),
        ("Aprobados, fallidos, bloqueados", f"{estados['Aprobada']} / {estados['Fallida']} / {estados['Bloqueada']}"),
        ("Pruebas automatizadas de respaldo", f"{len(casos)} ejecuciones: {auto['PASS']} aprobadas, {auto['FAIL']} fallidas, {auto['SKIP']} omitidas; aceptación {aprob_ca}/{len(aceptacion)}"),
        ("Defectos", f"{len(cargar_defectos())} registrados (DEF-01 rechazado; el resto cerrados salvo los indicados); "
                     f"{sum(1 for d in cargar_defectos() if d.get('Estado', '').startswith('Abierto'))} abiertos"),
        ("Cobertura de requisitos", f"{reqs_con_caso} de {len(REQUISITOS)} requisitos con al menos un caso"),
        ("Ejecución = ejecutados / planeados × 100", f"{ejecutados / total * 100:.1f}%"),
        ("Aprobación = aprobados / ejecutados × 100", f"{estados['Aprobada'] / ejecutados * 100:.1f}%" if ejecutados else "—"),
        ("Cobertura = requisitos con prueba / requisitos totales × 100", f"{reqs_con_caso / len(REQUISITOS) * 100:.1f}%"),
    ], anchos=[6.5, 10])
    doc.add_heading("Riesgos pendientes", level=2)
    vinetas(doc, ["Integrar la revisión cruzada, el escenario sorpresa y las observaciones del profesor (anexo C) "
                  "cuando ocurran.",
                  "Confirmar con el profesor las categorías de los elementos 2, 3 y 5.",
                  "En Windows con Python de Microsoft Store, Tkinter falla de forma intermitente (riesgo 4).",
                  "El acceso al tablero por red Wi-Fi está fuera de esta versión."])
    doc.add_heading("Conclusión", level=2)
    if estados["Fallida"] == 0 and estados["Bloqueada"] == 0:
        doc.add_paragraph(f"Liberar el software para la demostración: los {total} casos están aprobados, la aprobación es "
                          "del 100% y no hay defectos abiertos. El documento queda en revisión hasta integrar la revisión "
                          "cruzada, el escenario sorpresa y las observaciones del profesor.")
    else:
        doc.add_paragraph(f"Corregir y repetir pruebas: hay {estados['Fallida']} casos fallidos y {estados['Bloqueada']} bloqueados.")

    # Anexos
    doc.add_heading("14. Anexos", level=1)
    doc.add_heading("A. Evidencias", level=2)
    tabla(doc, ["Archivo", "Contenido"], [
        ("docs/evidencias/pytest.txt, junit.xml", "Salida completa y resultados de cada prueba"),
        ("docs/evidencias/aceptacion.txt", "Los 72 pasos de aceptación con esperado y observado"),
        ("docs/evidencias/metricas.txt", "Medición real de 60 s: intervalo, memoria y bitácoras"),
        ("docs/evidencias/bitacoras/", "Bitácoras de una ejecución exitosa y de una con errores"),
        ("docs/evidencias/capturas/", "Ocho capturas reales del tablero"),
        ("docs/evidencias/coverage.txt, htmlcov/", "Cobertura de líneas y ramas"),
        ("datos/, config/, tests/datos/", "Datos de prueba y configuración"),
        ("practica/", "Práctica del odómetro: ejecutar_casos.py, evidencia antes y después (capturas, bitácoras, "
                      "resumen.txt) y la hoja entregada en DOCX y PDF"),
    ], anchos=[6.5, 10])
    doc.add_heading("B. Historial de cambios (git)", level=2)
    tabla(doc, ["Commit", "Fecha", "Cambio"], historial, anchos=[2, 2.4, 12.1])
    doc.add_heading("C. Integración de actividades previas", level=2)
    tabla(doc, ["Actividad", "Estado", "Integración"], [
        ("Tarea 1 (investigación y planeación)", "Integrada", "Versión 1.0 de este documento (informe de pruebas, commit eb575e6)"),
        ("Tres casos de la práctica en clase (odómetro)", "Integrada",
         "CP-ODO-01 a 03 → CT-26 a CT-28; ejecutados antes y después de implementar el odómetro (sección 10.1); DEF-03"),
        ("Corrección de los propios casos", "Integrada", "Duraciones 30 s → 45 s y 10 s → 15 s; variantes de CT-28 (sección 10.1)"),
        ("Revisión cruzada", "Pendiente", PENDIENTE),
        ("Escenario sorpresa", "Pendiente", PENDIENTE),
        ("Observaciones del profesor", "Pendiente", "Todavía no hay observaciones del profesor sobre la Tarea 1 ni sobre la práctica."),
    ], anchos=[5, 2.5, 9])
    doc.add_paragraph("Formato para la revisión cruzada (llenar uno por cada caso CT-26 a CT-28 cuando ocurra):")
    ficha(doc, [("Caso revisado", "CT-2_"), ("Observación recibida (revisión cruzada)", ""),
                ("Corrección realizada", ""), ("Justificación si no se acepta", "")])
    ficha(doc, [("Escenario sorpresa: ¿qué requisito cambia?", ""), ("¿Qué casos se modifican?", ""), ("¿Qué casos deben repetirse?", ""),
                ("¿Qué riesgo aparece?", ""), ("¿Qué evidencia se necesita?", "")])
    doc.add_heading("D. Uso de inteligencia artificial", level=2)
    tabla(doc, ["Campo", "Contenido"], [
        ("Herramienta", "Claude Code (Anthropic). En las etapas 0 a 3, otro asistente de IA en una sesión distinta."),
        ("Finalidad", "Diseño y programación del clúster y de las pruebas, scripts de evidencia, redacción de los informes y de este documento, revisión de capturas."),
        ("Instrucción (resumen fiel)", "\"Continuar las etapas de pruebas\"; \"adaptar el tablero a una animación 8-bit con todos los testigos\"; "
                                       "\"construir lo que falta de la rúbrica, probarlo todo y subirlo a GitHub\"; \"hacer todo lo posible de la Tarea 2\"; "
                                       "\"la prueba que me dijo fue odómetro\"; \"implementa el odómetro y súbelo todo al repo\"."),
        ("Resultado utilizado", f"Código fuente, {len(casos)} ejecuciones de pruebas automatizadas, evidencias, informe técnico, informe de "
                                "pruebas, la hoja de la práctica y este documento."),
        ("Modificación del equipo", "Decisiones de interpretación D1–D7, ejecución de cada etapa en la VM, revisión de resultados reales, "
                                    "la especificación de los diez elementos y el elemento asignado en la práctica (odómetro)."),
        ("Verificación", "Cada resultado sale de una ejecución real (junit.xml, aceptacion.txt, metricas.txt); las normas se verificaron en sus fichas oficiales."),
        ("Contenido descartado", "1) La propuesta de la IA de tratar DEF-01 como defecto se rechazó al revisar R08. 2) La afirmación de la IA de que la "
                                 "interfaz no tenía lógica se corrigió porque la interfaz aún no existía. 3) Un comando de la IA con '!!' falló en bash "
                                 "y se cambió el método. 4) El primer diseño 8-bit tapaba la cifra con la aguja y se corrigió. "
                                 "5) La IA propuso los casos de la práctica con 30 s y 10 s (1 km exacto); al ejecutarlos se corrigieron "
                                 "a 45 s y 15 s para dejar margen (sección 10.1)."),
    ], anchos=[4, 12.5])
    doc.add_heading("E. Defensa", level=2)
    tabla(doc, ["Pregunta", "Respuesta"], [
        ("¿Por qué eligió una técnica?", "Valores límite en los umbrales porque ahí fallan las comparaciones (CT-07); transición de estados para la histéresis (CT-14)."),
        ("¿Cómo obtuvo los datos y límites?", "De la especificación de los diez elementos (rangos y umbrales R01–R08) y a cada lado de cada umbral; "
                                              "para el odómetro, del máximo de 6 dígitos (999999) y de distancia = velocidad × tiempo."),
        ("¿Qué caso tiene mayor prioridad?", "CT-15 y CT-16: los testigos de seguridad; una advertencia que no aparece es el fallo más grave."),
        ("¿Qué prueba automatizaría?", "Todas ya están automatizadas; la siguiente sería la vista por red cuando se construya."),
        ("¿Cómo se reproduce un defecto?", "Con los pasos de su ficha; por ejemplo DEF-02 se reproduce con la prueba CP-98 sin el reintento."),
        ("¿Qué cambió después de la práctica?", "Los casos del odómetro revelaron DEF-03 (no existía): dos fallidos y uno bloqueado. Se "
                                                "implementó el elemento 11 con persistencia y respaldo, se agregaron REQ-ODO-01, CT-26 a CT-28 "
                                                "y las pruebas CP-120 a CP-137 sin modificar las anteriores, y se corrigieron las duraciones "
                                                "de los casos (sección 10.1)."),
        ("¿Qué recomendación de IA corrigió o descartó?", "DEF-01: se descartó la condición de motor propuesta por la IA; en la práctica "
                                                          "se corrigieron las duraciones de 1 km exacto que propuso la IA (anexo D)."),
    ], anchos=[5, 11.5])
    return doc, evaluados


def main():
    doc, evaluados = construir()
    doc.save(SALIDA)
    for c, estado, _ in evaluados:
        print(f"  {c[0]} [{c[2]}]: {estado}")
    print(f"OK {SALIDA.relative_to(RAIZ)}")
    pdf, paginas = convertir_pdf(SALIDA)
    print(f"OK {pdf.relative_to(RAIZ)} ({paginas} paginas)")
    return 0 if all(estado == "Aprobada" for _, estado, _ in evaluados) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
