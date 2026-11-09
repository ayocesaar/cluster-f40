"""Genera informe/Informe_Pruebas_Cluster_F40.docx y su version .pdf.

Todos los resultados, conteos y porcentajes se leen de las evidencias reales
guardadas en docs/ (junit.xml, coverage.json, aceptacion.txt, capturas.txt,
matriz_trazabilidad.md, registro_defectos.md, bitacora_ia.md). Si falta una
evidencia el script se detiene: ningun resultado se escribe a mano.

Uso (desde la raiz del proyecto): python informe/generar_informe.py
Requiere python-docx y, para el PDF, LibreOffice (soffice) en modo headless."""

import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tkinter
import xml.etree.ElementTree as ET
from importlib.metadata import version

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
EVID = DOCS / "evidencias"
SALIDA = RAIZ / "informe" / "Informe_Pruebas_Cluster_F40.docx"

EVIDENCIAS = ("junit.xml", "coverage.json", "aceptacion.txt", "capturas.txt")

IDENTIFICACION = (
    ("Institución", "Universidad Autónoma de Guadalajara (UAG)"),
    ("Materia", "Sistemas Operativos"),
    ("Profesor", "José de Jesús Velázquez Martínez"),
    ("Equipo", "Equipo 3"),
    ("Integrantes", "César Saúl Vázquez Preciado (5079359)\nIan Josué Cota Flores (5060667)"),
    ("Fecha de entrega", "18 de octubre de 2026"),
)

TECNICAS = {
    "test_particiones": "Particion de equivalencia",
    "test_limites": "Valores limite",
    "test_transiciones": "Transicion de estados",
    "test_invalidas": "Entradas invalidas",
    "test_complementarias": "Caja blanca (cobertura)",
    "test_requisitos": "Basada en requisitos",
    "test_presentacion": "Presentacion (caja negra)",
    "test_tablero": "Integracion UI (Tkinter)",
    "test_aceptacion": "Aceptacion (dirigida por datos)",
}

PRODUCCION = ("logic/estado.py", "logic/reloj.py", "ui/presentacion.py", "ui/tablero.py",
              "main.py", "aceptacion/escenarios.py")

ELEMENTOS = (
    ("1", "Velocímetro", "Decimal", "0–360 km/h", "100 ms", "Encendido = 1", "Aguja y cifra", "Lectura continua"),
    ("2", "Presión de aceite", "Decimal", "0–10 bar", "100 ms", "Motor activo", "Aguja; ámbar si < 1 bar", "Lectura continua"),
    ("3", "Tacómetro", "Entero", "0–9000 RPM", "100 ms", "Motor activo", "Rojo si ≥ 8000 RPM", "Lectura continua"),
    ("4", "Temperatura de agua", "Decimal", "40–130 °C", "500 ms", "Encendido = 1", "Rojo si > 110 °C", "Lectura continua"),
    ("5", "Presión de turbo", "Decimal", "0–2 bar", "100 ms", "Motor activo", "Contorno ámbar si > 1.5 bar", "Lectura continua"),
    ("6", "Direccionales", "OFF / IZQ / DER", "—", "500 ms", "—", "Verde intermitente", "Testigo informativo"),
    ("7", "Luces altas", "Booleano", "—", "—", "—", "Azul fijo", "Testigo informativo"),
    ("8", "Intermitentes (emergencia)", "Booleano", "—", "500 ms", "—", "Ámbar intermitente", "Testigo informativo"),
    ("9", "Baja presión de aceite", "Booleano", "—", "—", "Motor activo (R02)", "Rojo fijo", "Testigo de seguridad (CRÍTICA)"),
    ("10", "Falla de frenos", "Booleano", "—", "300 ms", "—", "Rojo parpadeante", "Testigo de seguridad (CRÍTICA)"),
)

REGLAS = (
    ("R01", "encendido = 1: actualizar velocidad, RPM, temperatura, presión de aceite y turbo según su ciclo "
            "(100/500 ms). encendido = 0: velocidad y RPM a 0; las demás lecturas en un estado definido."),
    ("R02", "motor_activo = 1 y p_aceite < 1.0 bar durante ≥ 1 s: encender el testigo 9 en rojo. "
            "p_aceite ≥ 1.2 bar durante ≥ 1 s: apagarlo (histéresis)."),
    ("R03", "rpm ≥ 8000: indicador 3 en rojo. rpm < 7800: color normal."),
    ("R04", "temp_agua > 110 °C: indicador 4 en rojo. ≤ 105 °C: normal."),
    ("R05", "p_turbo > 1.5 bar: contorno del indicador 5 en ámbar. ≤ 1.4 bar: sin advertencia."),
    ("R06", "Direccional IZQ o DER: la lámpara 6 alterna cada 500 ms. OFF: apagada."),
    ("R07", "luces_altas = 1: testigo 7 azul fijo. emergencia = 1: el testigo 8 parpadea cada 500 ms y tiene "
            "precedencia visual sobre el testigo de giro."),
    ("R08", "falla_frenos = 1: testigo 10 rojo parpadeante cada 300 ms hasta falla_frenos = 0."),
)

DECISIONES = (
    ("D1", "R08 no condiciona el testigo 10 al motor: parpadea aunque el motor esté apagado. El defecto "
           "DEF-01, que suponía lo contrario, se rechazó."),
    ("D2", "Los testigos informativos 6, 7 y 8 solo se muestran con el motor encendido; es el estado "
           "definido que R01 deja abierto."),
    ("D3", "La especificación distingue Encendido (elementos 1 y 4) y Motor activo (2, 3 y 5); la interfaz "
           "tiene un solo interruptor Motor que representa ambas señales."),
    ("D4", "La prueba de aceptación lee sus escenarios de un archivo CSV; así se prueba también el manejo "
           "de archivos (inexistente, vacío, columnas faltantes, filas inválidas)."),
    ("D5", "Este informe presenta 25 casos consolidados (CT-01 a CT-25); cada uno se respalda en pruebas "
           "automatizadas (CP-xx) y de aceptación (CA-xx). La matriz completa está en docs/."),
    ("D6", "La portada usa la fecha de entrega de la especificación; las evidencias conservan su fecha "
           "real de ejecución."),
    ("D7", "Precedencia de R07: mientras la emergencia está activa, el testigo 6 no se ilumina y solo "
           "parpadea el 8."),
    ("R02*", "\"Durante ≥ 1 s\" se interpreta como tiempo continuo: entre 1.0 y 1.2 bar se reinician ambos "
             "temporizadores, por lo que una presión que oscila entre 0.9 y 1.1 bar no enciende el testigo 9."),
)

CASOS = (
    {"id": "CT-01", "titulo": "Estado inicial seguro", "requisitos": ["R01"], "elementos": "1–10",
     "tecnica": "Funcional, caja negra (aceptación)",
     "pre": "Aplicación recién iniciada; ningún control manipulado.",
     "datos": "Ninguno (valores por defecto).",
     "pasos": ["Iniciar la aplicación (python main.py).",
               "Sin tocar los controles, observar los 10 elementos y los controles."],
     "esperado": "Agujas 1–5 en su mínimo (0 km/h, 0 bar, 0 RPM, 40 °C, 0 bar) en color normal; testigos 6–10 "
                 "apagados; interruptor Motor apagado y direccional en OFF.",
     "respaldo": ["CP-68", "CP-74", "CA-01"], "evidencia": "Captura 01"},
    {"id": "CT-02", "titulo": "Encendido: actualización de lecturas según su ciclo", "requisitos": ["R01"],
     "elementos": "1, 3", "tecnica": "Partición de equivalencia, transición de estados",
     "pre": "Motor apagado.", "datos": "velocidad = 120.5 km/h; RPM = 4500; motor = 1",
     "pasos": ["Con el motor apagado fijar 120.5 km/h y comprobar que el velocímetro sigue en 0.",
               "Encender el motor.", "Observar el velocímetro a los 50 ms.", "Observarlo a los 100 ms."],
     "esperado": "Con el motor apagado no hay actualización; tras encenderlo, el valor aparece al cumplirse "
                 "el ciclo de 100 ms y no antes.",
     "respaldo": ["CP-01", "CP-02", "CP-35", "CA-01"], "evidencia": "Captura 02"},
    {"id": "CT-03", "titulo": "Apagado: velocidad y RPM a 0 y estado definido", "requisitos": ["R01", "R02"],
     "elementos": "1–5, 9", "tecnica": "Transición de estados",
     "pre": "Motor encendido con lecturas distintas de cero.",
     "datos": "velocidad 200 km/h, 5000 RPM, aceite 5 bar, turbo 1 bar, temperatura 90 °C",
     "pasos": ["Fijar los valores indicados y esperar 500 ms.", "Apagar el motor.",
               "Observar las lecturas y el testigo 9."],
     "esperado": "Velocidad y RPM en 0; aceite y turbo en 0; temperatura en 40 °C; testigo 9 apagado y su "
                 "temporizador reiniciado.",
     "respaldo": ["CP-36", "CP-37", "CA-03"], "evidencia": "docs/evidencias/aceptacion.txt (CA-03)"},
    {"id": "CT-04", "titulo": "Velocímetro: valores límite del rango", "requisitos": ["R01"], "elementos": "1",
     "tecnica": "Valores límite", "pre": "Motor encendido.",
     "datos": "0 y 360 km/h (válidos); −1 y 361 km/h (inválidos)",
     "pasos": ["Fijar 0 km/h y esperar 100 ms.", "Fijar 360 km/h y esperar 100 ms.",
               "Intentar fijar −1 y 361 km/h."],
     "esperado": "0 y 360 km/h se muestran; −1 y 361 km/h se rechazan con ValueError sin cambiar el valor.",
     "respaldo": ["CP-10", "CP-11", "CP-12", "CP-38", "CP-39"], "evidencia": "docs/evidencias/pytest.txt"},
    {"id": "CT-05", "titulo": "Presión de aceite (medidor 2): ámbar inmediato bajo 1 bar", "requisitos": ["R01"],
     "elementos": "2", "tecnica": "Valores límite, transición de estados", "pre": "Motor encendido.",
     "datos": "5, 0.99 y 1.0 bar",
     "pasos": ["Fijar 5 bar y esperar 100 ms.", "Bajar a 0.99 bar y esperar 100 ms.",
               "Subir a 1.0 bar y esperar 100 ms.", "Apagar el motor."],
     "esperado": "Normal en 5 bar; ámbar en 0.99 bar sin esperar 1 s; normal en 1.0 bar; normal con el motor "
                 "apagado.",
     "respaldo": ["CP-03", "CP-54", "CP-55", "CP-56", "CA-02"], "evidencia": "Captura 03"},
    {"id": "CT-06", "titulo": "Tacómetro: rojo a partir de 8000 RPM", "requisitos": ["R03"], "elementos": "3",
     "tecnica": "Valores límite", "pre": "Motor encendido.", "datos": "7799 y 8000 RPM",
     "pasos": ["Fijar 7799 RPM y esperar 100 ms.", "Fijar 8000 RPM y esperar 100 ms."],
     "esperado": "7799 RPM en color normal; 8000 RPM con el indicador 3 en rojo.",
     "respaldo": ["CP-13", "CP-16", "CA-03"], "evidencia": "Captura 03"},
    {"id": "CT-07", "titulo": "Tacómetro: histéresis entre 7800 y 7999 RPM", "requisitos": ["R03"],
     "elementos": "3", "tecnica": "Transición de estados (histéresis)", "pre": "Motor encendido.",
     "datos": "7800, 8000, 7999, 7900 y 7799 RPM",
     "pasos": ["Partiendo de normal, fijar 7800 RPM.", "Subir a 8000 RPM.", "Bajar a 7999 y luego a 7900 RPM.",
               "Bajar a 7799 RPM."],
     "esperado": "En 7800 conserva normal; en 8000 pasa a rojo; en 7999 y 7900 conserva rojo; en 7799 vuelve "
                 "a normal.",
     "respaldo": ["CP-14", "CP-15", "CP-27", "CA-03"], "evidencia": "docs/evidencias/aceptacion.txt (CA-03)"},
    {"id": "CT-08", "titulo": "Temperatura de agua: rojo sobre 110 °C y ciclo de 500 ms", "requisitos": ["R04"],
     "elementos": "4", "tecnica": "Valores límite", "pre": "Motor encendido.",
     "datos": "90, 110, 110.1 y 120 °C",
     "pasos": ["Fijar 90 °C y esperar 500 ms.", "Fijar 110 °C y esperar 500 ms.",
               "Fijar 110.1 °C y esperar 500 ms.",
               "Desde normal, fijar 120 °C y observar a los 250 y a los 500 ms."],
     "esperado": "90 y 110 °C en normal; 110.1 °C en rojo; el cambio a 120 °C se refleja solo al cumplirse "
                 "500 ms.",
     "respaldo": ["CP-04", "CP-22", "CP-23", "CA-04"], "evidencia": "Captura 03"},
    {"id": "CT-09", "titulo": "Temperatura de agua: histéresis hasta 105 °C", "requisitos": ["R04"],
     "elementos": "4", "tecnica": "Transición de estados (histéresis)", "pre": "Motor encendido.",
     "datos": "115, 105.1, 105 y 104 °C",
     "pasos": ["Fijar 115 °C y esperar 500 ms.", "Bajar a 105.1 °C y esperar 500 ms.",
               "Bajar a 105 °C (o 104 °C) y esperar 500 ms."],
     "esperado": "Rojo en 115 °C; conserva rojo en 105.1 °C; normal en 105 °C o menos.",
     "respaldo": ["CP-21", "CP-28", "CA-04"], "evidencia": "docs/evidencias/aceptacion.txt (CA-04)"},
    {"id": "CT-10", "titulo": "Presión de turbo: contorno ámbar sobre 1.5 bar", "requisitos": ["R05"],
     "elementos": "5", "tecnica": "Valores límite", "pre": "Motor encendido.", "datos": "1.0, 1.5 y 1.51 bar",
     "pasos": ["Fijar 1.0 bar y esperar 100 ms.", "Fijar 1.5 bar y esperar 100 ms.",
               "Fijar 1.51 bar y esperar 100 ms."],
     "esperado": "1.0 y 1.5 bar sin advertencia; 1.51 bar con contorno ámbar.",
     "respaldo": ["CP-05", "CP-25", "CP-26", "CA-05"], "evidencia": "Captura 03"},
    {"id": "CT-11", "titulo": "Presión de turbo: histéresis hasta 1.4 bar", "requisitos": ["R05"],
     "elementos": "5", "tecnica": "Transición de estados (histéresis)", "pre": "Motor encendido.",
     "datos": "1.6, 1.41, 1.4 y 1.3 bar",
     "pasos": ["Fijar 1.6 bar y esperar 100 ms.", "Bajar a 1.41 bar.", "Bajar a 1.4 bar (o 1.3 bar)."],
     "esperado": "Ámbar en 1.6 bar; conserva ámbar en 1.41 bar; sin advertencia en 1.4 bar o menos.",
     "respaldo": ["CP-24", "CP-29", "CA-05"], "evidencia": "docs/evidencias/aceptacion.txt (CA-05)"},
    {"id": "CT-12", "titulo": "Testigo 9: encendido tras 1 s bajo 1 bar", "requisitos": ["R02"],
     "elementos": "2, 9", "tecnica": "Valores límite (tiempo)", "pre": "Motor encendido.",
     "datos": "0.99 bar sostenido 999 ms y 1000 ms; 0.5 bar",
     "pasos": ["Fijar 0.99 bar.", "Observar el testigo 9 a los 999 ms de presión baja.",
               "Observarlo a los 1000 ms.", "Comparar con el medidor 2 en el mismo instante."],
     "esperado": "Testigo 9 apagado a los 999 ms y rojo fijo desde los 1000 ms; el medidor 2 ya estaba en "
                 "ámbar desde el primer ciclo.",
     "respaldo": ["CP-17", "CP-18", "CP-70", "CA-09"], "evidencia": "Captura 04"},
    {"id": "CT-13", "titulo": "Testigo 9: histéresis de apagado", "requisitos": ["R02"], "elementos": "9",
     "tecnica": "Transición de estados (histéresis)", "pre": "Motor encendido.", "datos": "1.0, 1.1 y 1.2 bar",
     "pasos": ["Con el testigo apagado, mantener 1.0 bar más de 1 s.",
               "Encender el testigo (0.5 bar durante 1 s) y subir a 1.1 bar.",
               "Subir a 1.2 bar y observar a los 900 y 1000 ms."],
     "esperado": "1.0 bar no lo enciende; en 1.1 bar sigue encendido; con 1.2 bar se apaga al cumplirse 1 s.",
     "respaldo": ["CP-19", "CP-20", "CA-09"], "evidencia": "docs/evidencias/aceptacion.txt (CA-09)"},
    {"id": "CT-14", "titulo": "Direccionales: alternancia cada 500 ms", "requisitos": ["R06"], "elementos": "6",
     "tecnica": "Transición de estados", "pre": "Motor encendido.", "datos": "IZQ, DER y OFF",
     "pasos": ["Seleccionar IZQ.", "Observar el testigo 6 en t = 0, 500 y 1000 ms.", "Cambiar a DER.",
               "Cambiar a OFF."],
     "esperado": "Verde alternando cada 500 ms con IZQ y con DER; apagado con OFF.",
     "respaldo": ["CP-06", "CP-07", "CP-08", "CP-30", "CP-57", "CA-06"], "evidencia": "Captura 05"},
    {"id": "CT-15", "titulo": "Luces altas: azul fijo", "requisitos": ["R07", "R01"], "elementos": "7",
     "tecnica": "Funcional, transición de estados", "pre": "Motor apagado.", "datos": "luces_altas = 1 / 0",
     "pasos": ["Activar luces altas con el motor apagado.", "Encender el motor.",
               "Observar el testigo 7 en t = 0, 250 y 500 ms.", "Desactivar luces altas."],
     "esperado": "Apagado con el motor apagado (D2); azul fijo, sin parpadeo, con el motor encendido; "
                 "apagado al desactivarlas.",
     "respaldo": ["CP-64", "CP-65", "CP-72", "CA-07"], "evidencia": "Captura 05"},
    {"id": "CT-16", "titulo": "Intermitentes de emergencia: alternancia cada 500 ms", "requisitos": ["R07"],
     "elementos": "8", "tecnica": "Transición de estados", "pre": "Motor encendido.",
     "datos": "emergencia = 1 / 0",
     "pasos": ["Activar la emergencia.", "Observar el testigo 8 en t = 0, 500 y 1000 ms.",
               "Desactivar la emergencia."],
     "esperado": "Ámbar alternando cada 500 ms; apagado al desactivarla.",
     "respaldo": ["CP-31", "CP-58", "CA-08"], "evidencia": "Captura 06"},
    {"id": "CT-17", "titulo": "Precedencia de la emergencia sobre el testigo de giro",
     "requisitos": ["R07", "R06"], "elementos": "6, 8", "tecnica": "Transición de estados",
     "pre": "Motor encendido.", "datos": "direccional = IZQ; emergencia = 1 / 0",
     "pasos": ["Seleccionar IZQ y comprobar que el testigo 6 se enciende.", "Activar la emergencia.",
               "Observar los testigos 6 y 8.", "Desactivar la emergencia."],
     "esperado": "Con emergencia activa solo parpadea el 8 y el 6 no se ilumina (D7); al desactivarla, el 6 "
                 "vuelve a mostrarse.",
     "respaldo": ["CP-33", "CP-34", "CP-71", "CA-08"], "evidencia": "Captura 06"},
    {"id": "CT-18", "titulo": "Falla de frenos: parpadeo cada 300 ms", "requisitos": ["R08"], "elementos": "10",
     "tecnica": "Transición de estados", "pre": "Motor encendido.", "datos": "falla_frenos = 1 / 0",
     "pasos": ["Activar falla de frenos.", "Observar el testigo 10 en t = 0, 300, 600 y 900 ms.",
               "Desactivar falla de frenos."],
     "esperado": "Rojo alternando cada 300 ms; apagado con falla_frenos = 0.",
     "respaldo": ["CP-32", "CP-59", "CA-10"], "evidencia": "docs/evidencias/aceptacion.txt (CA-10)"},
    {"id": "CT-19", "titulo": "Falla de frenos con el motor apagado", "requisitos": ["R08", "R01"],
     "elementos": "10", "tecnica": "Basada en requisitos", "pre": "Motor apagado.", "datos": "falla_frenos = 1",
     "pasos": ["Activar falla de frenos sin encender el motor.", "Observar el testigo 10 durante 900 ms.",
               "Encender el motor y seguir observando."],
     "esperado": "El testigo 10 parpadea en rojo cada 300 ms aunque el motor esté apagado (D1) y no cambia al "
                 "encender el motor.",
     "respaldo": ["CP-66", "CA-10"], "evidencia": "Captura 07"},
    {"id": "CT-20", "titulo": "Alertas críticas visualmente distintas", "requisitos": [], "elementos": "9, 10",
     "tecnica": "Revisión de interfaz", "pre": "Aplicación iniciada.", "datos": "Ninguno",
     "pasos": ["Observar la forma de los testigos 6–10.", "Activar la falla de frenos."],
     "esperado": "Los testigos 9 y 10 se dibujan como rectángulos con borde rojo y la etiqueta CRITICA; los "
                 "informativos 6–8 como círculos; el 10 se ilumina en rojo.",
     "respaldo": ["CP-67", "CP-76"], "evidencia": "Capturas 04 y 07"},
    {"id": "CT-21", "titulo": "Entradas fuera de rango", "requisitos": ["R01", "R02", "R03", "R04", "R05"],
     "elementos": "1–5", "tecnica": "Partición de equivalencia (clases inválidas)",
     "pre": "Aplicación iniciada.",
     "datos": "−1 y 361 km/h; 9001 RPM; 10.1 bar; 39.9 y 130.1 °C; 2.1 bar; 500 km/h",
     "pasos": ["Enviar cada valor al estado del clúster.", "Comprobar la excepción y el estado posterior."],
     "esperado": "Cada valor se rechaza con ValueError y el último valor válido se conserva.",
     "respaldo": ["CP-38", "CP-39", "CP-42", "CP-43", "CP-45", "CP-46", "CP-47", "CP-52"],
     "evidencia": "docs/evidencias/pytest.txt"},
    {"id": "CT-22", "titulo": "Tipos de dato inválidos", "requisitos": ["R01", "R02", "R03", "R05", "R06"],
     "elementos": "2, 3, 5, 6 y motor", "tecnica": "Partición de equivalencia (clases inválidas)",
     "pre": "Aplicación iniciada.",
     "datos": "RPM 5000.0 y True; aceite \"alta\"; turbo True; direccional \"ADELANTE\" y 1; motor 1",
     "pasos": ["Enviar cada valor al estado del clúster.", "Comprobar la excepción."],
     "esperado": "Tipos incorrectos se rechazan con TypeError y valores fuera del conjunto con ValueError.",
     "respaldo": ["CP-40", "CP-41", "CP-44", "CP-48", "CP-49", "CP-50", "CP-51"],
     "evidencia": "docs/evidencias/pytest.txt"},
    {"id": "CT-23", "titulo": "Error informado en la interfaz", "requisitos": [], "elementos": "3",
     "tecnica": "Manejo de errores", "pre": "Aplicación iniciada.", "datos": "RPM = 9001 enviado por programa",
     "pasos": ["Enviar 9001 RPM a la interfaz.", "Observar el mensaje.", "Enviar un valor válido (100 RPM)."],
     "esperado": "Aparece \"Entrada rechazada: …\" sin cambiar el estado; con un valor válido el mensaje "
                 "desaparece.",
     "respaldo": ["CP-77"], "evidencia": "Captura 08"},
    {"id": "CT-24", "titulo": "Manejo del archivo de escenarios", "requisitos": [], "elementos": "—",
     "tecnica": "Manejo de errores y archivos", "pre": "Ejecutor de aceptación disponible.",
     "datos": "Archivo inexistente, vacío, solo cabecera, sin columna esperado, control desconocido, valor no "
              "numérico y seis tipos de fila inválida",
     "pasos": ["Ejecutar el cargador con cada archivo.", "Comprobar el mensaje de error y el código de salida."],
     "esperado": "Cada caso produce un error claro que indica la causa y, cuando aplica, la línea; el ejecutor "
                 "devuelve 2.",
     "respaldo": ["CP-79", "CP-80", "CP-81", "CP-82", "CP-83", "CP-84", "CP-87", "CP-88"],
     "evidencia": "docs/evidencias/pytest.txt"},
    {"id": "CT-25", "titulo": "Prueba de aceptación completa desde archivo",
     "requisitos": ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08"], "elementos": "1–10",
     "tecnica": "Aceptación dirigida por datos", "pre": "Archivo tests/datos/escenarios_aceptacion.csv.",
     "datos": "10 escenarios (CA-01 a CA-10) que recorren los 10 controles",
     "pasos": ["Ejecutar: xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv",
               "Revisar el resultado de cada paso.",
               "Comprobar que una expectativa incorrecta a propósito se detecta como FALLIDO."],
     "esperado": "10/10 escenarios aprobados y el ejecutor detecta una expectativa incorrecta.",
     "respaldo": ["CP-85", "CP-89", "CP-90"] + [f"CA-{n:02d}" for n in range(1, 11)],
     "evidencia": "docs/evidencias/aceptacion.txt"},
)

RIESGOS = (
    ("Interpretación de la especificación (D1–D7)", "Alto",
     "Decisiones documentadas y aprobadas por el equipo; cada una tiene casos que la verifican."),
    ("Los valores esperados se generaron con la misma IA que escribió el código", "Alto",
     "Valores derivados directamente de los umbrales de R01–R08; CP-90 demuestra que el oráculo detecta "
     "diferencias; revisión del equipo."),
    ("La interfaz se probó en una pantalla virtual (Xvfb), no en un monitor real", "Medio",
     "Capturas reales de la ventana; se recomienda una ejecución manual con python main.py."),
    ("El tiempo se simula en las pruebas; no se midió la precisión del reloj real", "Medio",
     "CP-60 y CP-78 prueban el reloj real; el rendimiento queda fuera del alcance."),
    ("Umbrales con decimales (110.1 °C, 1.51 bar, 0.99 bar)", "Bajo",
     "Controles redondeados a su resolución y casos en ambos lados de cada umbral."),
    ("Un solo interruptor para Encendido y Motor activo (D3)", "Bajo",
     "Restricción documentada en el alcance."),
    ("Cobertura alta no garantiza ausencia de defectos", "Medio",
     "Se combinan técnicas de caja negra, aceptación y revisión de la especificación."),
)

NORMAS = (
    ("ISO/IEC/IEEE 29119-1:2022", "Conceptos generales de prueba",
     "Vocabulario del informe: caso de prueba, oráculo, cobertura, defecto, niveles y tipos de prueba."),
    ("ISO/IEC/IEEE 29119-2:2021", "Procesos de prueba",
     "El trabajo siguió las etapas de planificación (auditoría y alcance), diseño e implementación (casos "
     "CP/CA), ejecución con registro de resultados, reporte de incidentes (DEF-01) y cierre (este informe)."),
    ("ISO/IEC/IEEE 29119-3:2021", "Documentación de prueba",
     "Estructura de este documento: alcance, ambiente y datos, especificación de casos con resultado esperado "
     "y obtenido, registro de defectos, trazabilidad y resumen de completitud."),
    ("ISO/IEC/IEEE 29119-4:2021", "Técnicas de prueba",
     "Técnicas basadas en especificación (partición de equivalencia, valores límite, transición de estados) y "
     "basadas en estructura (cobertura de sentencias y ramas)."),
    ("ISO 26262-6:2018", "Seguridad funcional, software automotriz",
     "Solo como contexto: distinción entre testigos críticos (9 y 10) e informativos y verificación por "
     "requisitos. No se pide ni se demuestra conformidad."),
)

HERRAMIENTAS = (
    ("Python", lambda: platform.python_version(), "Lenguaje y ejecución",
     "https://docs.python.org/3/library/tkinter.html"),
    ("Tkinter (Tk)", lambda: str(tkinter.TkVersion), "Interfaz gráfica",
     "https://docs.python.org/3/library/tkinter.html"),
    ("pytest", lambda: version("pytest"), "Ejecución de pruebas automatizadas", "https://docs.pytest.org/en/stable/"),
    ("coverage.py", lambda: version("coverage"), "Cobertura de líneas y ramas", "https://coverage.readthedocs.io/"),
    ("Pillow", lambda: version("Pillow"), "Capturas de pantalla", "https://pillow.readthedocs.io/"),
    ("python-docx", lambda: version("python-docx"), "Generación de este informe",
     "https://python-docx.readthedocs.io/"),
    ("Xvfb", lambda: "paquete xvfb de Ubuntu", "Pantalla virtual para la interfaz",
     "https://manpages.ubuntu.com/manpages/jammy/man1/Xvfb.1.html"),
    ("LibreOffice", lambda: "modo headless (soffice)", "Conversión del informe a PDF", "https://www.libreoffice.org/"),
)

REFERENCIAS = (
    "Especificación del proyecto Clúster F40, Sistemas Operativos, UAG (documento del curso).",
    "ISO/IEC/IEEE 29119-1:2022, Software and systems engineering — Software testing — Part 1: General concepts. "
    "https://www.iso.org/standard/81291.html (ficha verificada el 29/10/2026).",
    "ISO/IEC/IEEE 29119-2:2021, Software and systems engineering — Software testing — Part 2: Test processes. "
    "https://www.iso.org/standard/79428.html (ficha verificada el 29/10/2026).",
    "ISO/IEC/IEEE 29119-3:2021, Software and systems engineering — Software testing — Part 3: Test documentation. "
    "https://www.iso.org/standard/79429.html (ficha verificada el 29/10/2026).",
    "ISO/IEC/IEEE 29119-4:2021, Software and systems engineering — Software testing — Part 4: Test techniques. "
    "https://webstore.iec.ch/publication/71836 (ficha verificada el 29/10/2026).",
    "ISO 26262-6:2018, Road vehicles — Functional safety — Part 6: Product development at the software level. "
    "https://www.iso.org/standard/68388.html (ficha verificada el 29/10/2026). Solo como contexto; no se "
    "demuestra conformidad.",
    "pytest documentation. https://docs.pytest.org/en/stable/ (consultado el 29/10/2026).",
    "Coverage.py documentation. https://coverage.readthedocs.io/ (consultado el 29/10/2026).",
    "tkinter — Python interface to Tcl/Tk. https://docs.python.org/3/library/tkinter.html (consultado el 29/10/2026).",
    "Pillow documentation. https://pillow.readthedocs.io/ (consultado el 29/10/2026).",
    "python-docx documentation. https://python-docx.readthedocs.io/ (consultado el 29/10/2026).",
    "Xvfb(1), Ubuntu Manpage. https://manpages.ubuntu.com/manpages/jammy/man1/Xvfb.1.html (consultado el 29/10/2026).",
    "LibreOffice. https://www.libreoffice.org/ (consultado el 29/10/2026).",
)


# --------------------------------------------------------------------------- evidencias

def leer(ruta):
    if not ruta.is_file():
        sys.exit(f"ERROR: falta la evidencia {ruta.relative_to(RAIZ)}; ejecuta primero las pruebas")
    return ruta.read_text(encoding="utf-8")


def cargar_junit():
    raiz = ET.fromstring(leer(EVID / "junit.xml"))
    suite = raiz.find("testsuite") if raiz.tag == "testsuites" else raiz
    casos = []
    for c in raiz.iter("testcase"):
        if c.find("failure") is not None or c.find("error") is not None:
            res = "FAIL"
        elif c.find("skipped") is not None:
            res = "SKIP"
        else:
            res = "PASS"
        casos.append({"modulo": c.get("classname").split(".")[-1], "nombre": c.get("name"), "res": res})
    return casos, (suite.get("timestamp") or "")[:10]


def ejecuciones(casos, ident):
    prefijo = "test_" + ident.lower().replace("-", "") + "_"
    return [c for c in casos if c["nombre"].startswith(prefijo)]


def cargar_aceptacion():
    resumen, total = {}, ""
    actual = None
    for linea in leer(EVID / "aceptacion.txt").splitlines():
        m = re.match(r"(CA-\d+): (APROBADO|FALLIDO)$", linea)
        if m:
            actual = m.group(1)
            resumen[actual] = {"estado": m.group(2), "ok": 0, "xx": 0}
        elif actual and linea.strip().startswith("OK "):
            resumen[actual]["ok"] += 1
        elif actual and linea.strip().startswith("XX "):
            resumen[actual]["xx"] += 1
        elif linea.startswith("Resumen:"):
            total = linea
    return resumen, total


def cargar_capturas():
    capturas = []
    for linea in leer(EVID / "capturas.txt").splitlines():
        m = re.match(r"(\S+\.png) \((.+)\)$", linea)
        if m:
            capturas.append({"archivo": m.group(1), "detalle": m.group(2)})
        elif capturas and linea.startswith("  ") and ":" in linea:
            clave, valor = linea.strip().split(":", 1)
            capturas[-1][clave] = valor.strip()
    for c in capturas:
        if not (EVID / "capturas" / c["archivo"]).is_file():
            sys.exit(f"ERROR: falta la imagen {c['archivo']}")
    return capturas


def cargar_defectos():
    defectos = []
    for linea in leer(DOCS / "registro_defectos.md").splitlines():
        m = re.match(r"## (DEF-\d+) - (.+)", linea)
        if m:
            defectos.append({"ID": m.group(1), "Titulo": m.group(2), "_texto": []})
            continue
        if not defectos:
            continue
        m = re.match(r"\| ([^|]+?) \| ([^|]+?) \|$", linea)
        if m:
            if m.group(1) not in ("Campo", "ID"):
                defectos[-1][m.group(1)] = m.group(2).replace("`", "")
        elif not linea.startswith("|"):
            defectos[-1]["_texto"].append(linea.replace("`", ""))
    return defectos


def parrafos_markdown(lineas):
    """Agrupa lineas de markdown en parrafos y vinetas, uniendo las lineas de continuacion."""
    items = []
    for linea in lineas:
        s = linea.strip()
        if not s:
            items.append(None)
            continue
        es_vineta = bool(re.match(r"(-|\d+\.)\s", s))
        if es_vineta or not items or items[-1] is None:
            items.append({"texto": re.sub(r"^(-|\d+\.)\s+", "", s).replace("**", ""), "vineta": es_vineta,
                          "negrita": s.startswith("**") and s.endswith("**")})
        else:
            items[-1]["texto"] += " " + s.replace("**", "")
    return [i for i in items if i]


def cargar_por_requisito():
    filas = {}
    for linea in leer(DOCS / "matriz_trazabilidad.md").splitlines():
        m = re.match(r"\| (R0\d) \| (.+) \|$", linea)
        if m:
            filas[m.group(1)] = m.group(2)
    return filas


def version_software():
    def git(*args):
        r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)
        return r.stdout.strip()
    commit = git("rev-parse", "--short", "HEAD") or "desconocida"
    cambios = git("status", "--porcelain", "--", "logic", "ui", "main.py", "aceptacion", "tests")
    return f"commit {commit}" + (" (con cambios sin commit)" if cambios else "")


def sistema_operativo():
    ruta = pathlib.Path("/etc/os-release")
    if ruta.is_file():
        m = re.search(r'^PRETTY_NAME="?([^"\n]+)', ruta.read_text(), re.M)
        if m:
            return f"{m.group(1)} (kernel {platform.release()})"
    return f"{platform.system()} {platform.release()}"


def evaluar(caso, casos_junit, aceptacion):
    ejec, faltan = [], []
    for ident in caso["respaldo"]:
        e = ejecuciones(casos_junit, ident)
        if e:
            ejec.extend(e)
        else:
            faltan.append(ident)
    n = {r: sum(c["res"] == r for c in ejec) for r in ("PASS", "FAIL", "SKIP")}
    if faltan or n["SKIP"]:
        estado = "Bloqueada"
    elif n["FAIL"]:
        estado = "Fallida"
    else:
        estado = "Aprobada"
    texto = (f"{len(ejec)} ejecuciones automatizadas ({', '.join(caso['respaldo'])}): "
             f"{n['PASS']} aprobadas, {n['FAIL']} fallidas, {n['SKIP']} omitidas.")
    if faltan:
        texto += f" Sin ejecución registrada: {', '.join(faltan)}."
    for ident in caso["respaldo"]:
        a = aceptacion.get(ident)
        if a:
            texto += f" {ident}: {a['estado']} ({a['ok']}/{a['ok'] + a['xx']} pasos verificados en pantalla)."
    return estado, texto


# --------------------------------------------------------------------------- formato

COLOR_ESTADO = {"Aprobada": "C6EFCE", "Fallida": "FFC7CE", "Bloqueada": "D9D9D9"}


def sombrear(celda, color):
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def escribir(celda, texto, negrita=False, tam=9):
    celda.text = ""
    run = celda.paragraphs[0].add_run(str(texto))
    run.bold = negrita
    run.font.size = Pt(tam)


def tabla(doc, encabezados, filas, anchos=None):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    for i, h in enumerate(encabezados):
        escribir(t.rows[0].cells[i], h, negrita=True)
        sombrear(t.rows[0].cells[i], "D9E2F3")
    encabezado = OxmlElement("w:tblHeader")
    encabezado.set(qn("w:val"), "true")
    t.rows[0]._tr.get_or_add_trPr().append(encabezado)
    for fila in filas:
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            escribir(celdas[i], valor)
    if anchos:
        for fila in t.rows:
            for i, ancho in enumerate(anchos):
                fila.cells[i].width = Cm(ancho)
    doc.add_paragraph()
    return t


def ficha(doc, campos, estado=None):
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for clave, valor in campos:
        celdas = t.add_row().cells
        escribir(celdas[0], clave, negrita=True)
        sombrear(celdas[0], "F2F2F2")
        escribir(celdas[1], valor, negrita=(clave == "Estado"))
        if clave == "Estado" and estado:
            sombrear(celdas[1], COLOR_ESTADO[estado])
    for fila in t.rows:
        fila.cells[0].width = Cm(4.2)
        fila.cells[1].width = Cm(12.3)
    doc.add_paragraph()


def vinetas(doc, lineas):
    for linea in lineas:
        doc.add_paragraph(linea, style="List Bullet")


def codigo(doc, lineas):
    for linea in lineas:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(linea)
        run.font.name = "Courier New"
        run.font.size = Pt(8.5)
    doc.add_paragraph()


def numero_pagina(parrafo):
    run = parrafo.add_run()
    for tipo, texto in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texto
        run._r.append(el)


def figura(doc, ruta, titulo):
    doc.add_picture(str(ruta), width=Cm(15.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(titulo)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(9)


# --------------------------------------------------------------------------- documento

def construir():
    casos_junit, fecha_ejecucion = cargar_junit()
    cov = json.loads(leer(EVID / "coverage.json"))
    aceptacion, resumen_aceptacion = cargar_aceptacion()
    capturas = cargar_capturas()
    defectos = cargar_defectos()
    por_requisito = cargar_por_requisito()
    bitacora = leer(DOCS / "bitacora_ia.md")
    evaluados = [(c, *evaluar(c, casos_junit, aceptacion)) for c in CASOS]

    doc = Document()
    seccion = doc.sections[0]
    seccion.left_margin = seccion.right_margin = Cm(2.2)
    seccion.top_margin = seccion.bottom_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.add_run("Informe de pruebas — Clúster F40 simulado — página ")
    numero_pagina(pie)

    # 1. Portada e identificacion
    for _ in range(3):
        doc.add_paragraph()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run("Informe de Pruebas\nClúster de instrumentos simulado del Ferrari F40 (1987)")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Software simulado, sin ECU ni sensores reales. Los rangos y umbrales son parámetros "
                "didácticos, no calibraciones oficiales del F40.").italic = True
    doc.add_paragraph()
    doc.add_heading("1. Portada e identificación", level=1)
    tabla(doc, ["Campo", "Valor"], list(IDENTIFICACION) + [
        ("Fecha de ejecución de las pruebas", fecha_ejecucion or "no registrada en junit.xml"),
        ("Versión del software probado", version_software()),
        ("Colaboración", "Claude Code (Anthropic), asistente de inteligencia artificial; ver sección 14"),
        ("Documento generado por", "informe/generar_informe.py a partir de las evidencias en docs/"),
    ], anchos=[5, 11.5])
    doc.add_heading("Contenido", level=2)
    vinetas(doc, ["1. Portada e identificación", "2. Vehículo y descripción del clúster",
                  "3. Los diez elementos y las reglas", "4. Alcance y exclusiones",
                  "5. Ambiente y datos de prueba", "6. Niveles, tipos y técnicas aplicadas",
                  "7. Herramientas", "8. Riesgos", "9. Casos de prueba",
                  "10. Matriz de trazabilidad", "11. Registro de defectos",
                  "12. Resumen cuantitativo y conclusión de calidad", "13. Referencias",
                  "14. Anexo: uso de inteligencia artificial"])
    doc.add_page_break()

    # 2. Vehiculo y descripcion
    doc.add_heading("2. Vehículo y descripción del clúster", level=1)
    doc.add_paragraph(
        "El sistema bajo prueba simula el clúster de instrumentos de un Ferrari F40 (1987). No se conecta a una "
        "ECU ni a sensores: los valores se introducen con controles en pantalla (5 deslizadores, 4 interruptores y "
        "un selector de direccional) y el clúster los muestra en 5 medidores de aguja y 5 testigos luminosos. "
        "Los rangos y umbrales son parámetros didácticos definidos por la especificación del curso.")
    doc.add_paragraph(
        "La interfaz tiene una estética 8-bit inspirada en la distribución del tablero del F40: velocímetro y "
        "tacómetro grandes al centro, medidores chicos a los lados y los dos testigos críticos arriba, entre las "
        "esferas. Agujas, esferas y escalas se dibujan con bloques de pixeles; los testigos 6, 7 y 8 van dentro de "
        "las esferas. Se abre en Windows, Linux y macOS con Python 3.10 o superior (ver README.md).")
    doc.add_paragraph("Arquitectura del software:")
    tabla(doc, ["Módulo", "Responsabilidad"], [
        ("logic/estado.py", "Estado del clúster y reglas R01–R08; valida las entradas; sin dependencias de interfaz."),
        ("logic/reloj.py", "Reloj inyectable: real (time.monotonic) o simulado para pruebas deterministas."),
        ("ui/presentacion.py", "Traduce el estado a lo que se dibuja de cada uno de los 10 elementos."),
        ("ui/tablero.py", "Interfaz Tkinter: dibuja medidores y testigos y envía los controles al estado."),
        ("main.py", "Punto de entrada de la aplicación."),
        ("aceptacion/escenarios.py", "Carga y ejecuta los escenarios de aceptación desde un archivo CSV."),
    ], anchos=[4.5, 12])
    figura(doc, EVID / "capturas" / "02_motor_encendido_valores_normales.png",
           "Figura 1. Vista general del clúster con el motor encendido (captura 02).")

    # 3. Elementos y reglas
    doc.add_heading("3. Los diez elementos y las reglas", level=1)
    doc.add_paragraph("Categorías: 1–5 lecturas continuas; 6–8 testigos informativos; 9–10 testigos de "
                      "seguridad. El testigo 9 es distinto del medidor continuo 2.")
    tabla(doc, ["N.º", "Elemento", "Tipo", "Rango", "Ciclo", "Condición", "Comportamiento", "Categoría"],
          ELEMENTOS)
    doc.add_heading("Reglas de funcionamiento", level=2)
    tabla(doc, ["Regla", "Descripción"], REGLAS, anchos=[1.8, 14.7])

    # 4. Alcance
    doc.add_heading("4. Alcance y exclusiones", level=1)
    doc.add_heading("Dentro del alcance", level=2)
    vinetas(doc, [
        "Reglas R01–R08 y validación de entradas en logic/estado.py; reloj en logic/reloj.py.",
        "Presentación de los 10 elementos (ui/presentacion.py) e interfaz Tkinter (ui/tablero.py, main.py), "
        "probadas con Tkinter real sobre una pantalla virtual (Xvfb).",
        "Prueba de aceptación dirigida por datos (aceptacion/escenarios.py) y manejo de su archivo de escenarios.",
        "Evidencia visual: capturas reales de la ventana en estados representativos."])
    doc.add_heading("Fuera del alcance", level=2)
    vinetas(doc, [
        "Hardware, ECU, sensores y calibraciones reales del vehículo.",
        "Rendimiento, carga y precisión temporal del reloj real.",
        "Otras plataformas: solo se probó en la máquina virtual descrita en la sección 5.",
        "Ejecución interactiva prolongada de main.py sin la opción --salir-tras-ms (se recomienda una prueba manual).",
        "Demostrar conformidad con ISO 26262; la norma solo se usa como contexto."])
    doc.add_heading("Decisiones de interpretación", level=2)
    doc.add_paragraph("Puntos donde la especificación admite más de una lectura. Fueron propuestos durante el "
                      "análisis y aprobados por el equipo; cada uno tiene casos que lo verifican.")
    tabla(doc, ["ID", "Decisión"], DECISIONES, anchos=[1.5, 15])

    # 5. Ambiente
    doc.add_heading("5. Ambiente y datos de prueba", level=1)
    doc.add_heading("Ambiente de ejecución", level=2)
    tabla(doc, ["Componente", "Versión"], [
        ("Sistema operativo", sistema_operativo()),
        ("Python", platform.python_version()),
        ("Tk", str(tkinter.TkVersion)),
        ("pytest", version("pytest")),
        ("coverage.py", version("coverage")),
        ("Pillow", version("Pillow")),
        ("python-docx", version("python-docx")),
        ("Pantalla", "Xvfb (pantalla virtual); capturas a 1280x1024, 24 bits"),
    ], anchos=[5, 11.5])
    doc.add_heading("Preparación", level=2)
    codigo(doc, [
        "sudo apt-get install -y python3-tk python3-venv xvfb",
        "sudo apt-get install -y --no-install-recommends libreoffice-writer-nogui fonts-liberation",
        "python3 -m venv .venv && source .venv/bin/activate",
        "pip install -r requirements.txt",
        "Abrir la aplicación: bash abrir_cluster.sh (Linux/macOS) o doble clic en abrir_cluster.bat (Windows)"])
    doc.add_heading("Archivos y datos de prueba", level=2)
    tabla(doc, ["Archivo", "Contenido"], [
        ("tests/conftest.py", "Fixtures: reloj simulado, estado inicial y estado con motor encendido."),
        ("tests/test_*.py", "Pruebas automatizadas CP-01 a CP-90 y CA-01 a CA-10."),
        ("tests/datos/escenarios_aceptacion.csv", "Escenarios de aceptación: control, valor, tiempo, elemento y "
                                                  "resultado esperado de cada paso."),
        ("tools/capturas.py", "Generación de capturas en estados representativos."),
        ("tools/trazabilidad.py", "Matriz de trazabilidad desde los docstrings y junit.xml."),
    ], anchos=[6, 10.5])
    doc.add_heading("Ejecución", level=2)
    codigo(doc, [
        "xvfb-run -a python -m coverage run --branch -m pytest -v --junitxml=docs/evidencias/junit.xml",
        "python -m coverage report -m",
        "xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv",
        "xvfb-run -a -s \"-screen 0 1280x1024x24\" python tools/capturas.py",
        "python tools/trazabilidad.py",
        "python informe/generar_informe.py"])
    doc.add_heading("Criterios de evaluación", level=2)
    tabla(doc, ["Estado", "Criterio"], [
        ("Aprobada", "Todas las ejecuciones que respaldan el caso pasaron y, si incluye escenarios de aceptación, "
                     "todos sus pasos coinciden con lo esperado en pantalla."),
        ("Fallida", "Al menos una ejecución que respalda el caso falló."),
        ("Bloqueada", "No hay ejecución registrada de alguna prueba de respaldo, o se omitió (por ejemplo, sin "
                      "servidor gráfico)."),
    ], anchos=[3, 13.5])

    # 6. Tecnicas
    doc.add_heading("6. Niveles, tipos y técnicas aplicadas", level=1)
    tabla(doc, ["Nivel", "Qué se prueba"], [
        ("Unitario", "logic/estado.py y logic/reloj.py de forma aislada, con reloj simulado."),
        ("Integración", "ui/presentacion.py y ui/tablero.py con Tkinter real; main.py como prueba de humo."),
        ("Sistema / aceptación", "Escenarios completos sobre la ventana real, observando lo dibujado."),
    ], anchos=[4, 12.5])
    conteo = {}
    for c in casos_junit:
        t = TECNICAS.get(c["modulo"], c["modulo"])
        conteo.setdefault(t, {"PASS": 0, "FAIL": 0, "SKIP": 0})[c["res"]] += 1
    tabla(doc, ["Técnica", "Ejecuciones", "Aprobadas", "Fallidas", "Omitidas"],
          [(t, sum(v.values()), v["PASS"], v["FAIL"], v["SKIP"]) for t, v in conteo.items()])
    doc.add_paragraph("Tipos de prueba: funcional (caja negra), estructural (caja blanca con cobertura de ramas), "
                      "regresión (toda la suite se ejecuta tras cada cambio), manejo de errores y archivos, y "
                      "aceptación dirigida por datos.")
    doc.add_heading("Marco normativo", level=2)
    doc.add_paragraph("El proceso y este documento se inspiran en la serie ISO/IEC/IEEE 29119; ISO 26262-6 se "
                      "usa solo como contexto automotriz. No se declara conformidad con ninguna de ellas.")
    tabla(doc, ["Norma", "Tema", "Cómo se aplicó en este proyecto"], NORMAS, anchos=[4, 3.5, 9])

    # 7. Herramientas
    doc.add_heading("7. Herramientas", level=1)
    tabla(doc, ["Herramienta", "Versión", "Uso", "Fuente oficial"],
          [(n, v(), u, f) for n, v, u, f in HERRAMIENTAS], anchos=[3, 3, 4.5, 6])

    # 8. Riesgos
    doc.add_heading("8. Riesgos", level=1)
    tabla(doc, ["Riesgo", "Impacto", "Mitigación"], RIESGOS, anchos=[6, 2, 8.5])

    # 9. Casos
    doc.add_heading("9. Casos de prueba", level=1)
    doc.add_paragraph("Los 25 casos CT-01 a CT-25 consolidan las pruebas ejecutadas. Cada uno indica las "
                      "pruebas automatizadas (CP-xx) y de aceptación (CA-xx) que lo respaldan; el resultado "
                      "obtenido y el estado se calculan de docs/evidencias/junit.xml y aceptacion.txt.")
    for caso, estado, obtenido in evaluados:
        doc.add_heading(f"{caso['id']} — {caso['titulo']}", level=2)
        ficha(doc, [
            ("Identificador", caso["id"]),
            ("Requisitos", ", ".join(caso["requisitos"]) or "Especificación (interfaz y manejo de errores)"),
            ("Elementos", caso["elementos"]),
            ("Técnica", caso["tecnica"]),
            ("Precondiciones", caso["pre"]),
            ("Datos de prueba", caso["datos"]),
            ("Pasos", "\n".join(f"{i}. {p}" for i, p in enumerate(caso["pasos"], 1))),
            ("Resultado esperado", caso["esperado"]),
            ("Resultado obtenido", obtenido),
            ("Estado", estado),
            ("Evidencia", f"{caso['evidencia']}; docs/evidencias/junit.xml"),
        ], estado=estado)
    doc.add_heading("Evidencia visual", level=2)
    for n, c in enumerate(capturas, 1):
        figura(doc, EVID / "capturas" / c["archivo"],
               f"Captura {n:02d}. {c.get('Descripcion', c['archivo'])} ({c.get('Casos', '')}).")

    # 10. Trazabilidad
    doc.add_heading("10. Matriz de trazabilidad", level=1)
    filas = []
    for regla, _ in REGLAS:
        cts = [c["id"] for c in CASOS if regla in c["requisitos"]]
        filas.append((regla, ", ".join(cts) or "—", por_requisito.get(regla, "—")))
    tabla(doc, ["Requisito", "Casos del informe", "Pruebas automatizadas (docs/matriz_trazabilidad.md)"], filas,
          anchos=[2, 5, 9.5])
    doc.add_heading("Elementos y casos", level=2)
    tabla(doc, ["Elemento", "Casos del informe"], [
        (f"{n} {nombre}", ", ".join(c["id"] for c in CASOS if _incluye(c["elementos"], int(n))))
        for n, nombre, *_ in ELEMENTOS], anchos=[5, 11.5])
    sin_caso = [regla for regla, cts, _ in filas if cts == "—"]
    doc.add_paragraph("Requisitos sin casos: " + (", ".join(sin_caso) if sin_caso else "ninguno") + ".")

    # 11. Defectos
    doc.add_heading("11. Registro de defectos", level=1)
    if not defectos:
        doc.add_paragraph("No se registraron defectos.")
    for d in defectos:
        doc.add_heading(f"{d['ID']} — {d['Titulo']}", level=2)
        ficha(doc, [(k, v) for k, v in d.items() if not k.startswith("_") and k != "Titulo"])
        for item in parrafos_markdown(d["_texto"]):
            if item["vineta"]:
                doc.add_paragraph(item["texto"], style="List Bullet")
            else:
                doc.add_paragraph().add_run(item["texto"]).bold = item["negrita"]

    # 12. Resumen
    doc.add_heading("12. Resumen cuantitativo y conclusión de calidad", level=1)
    estados = {e: sum(1 for _, s, _ in evaluados if s == e) for e in ("Aprobada", "Fallida", "Bloqueada")}
    total = {r: sum(c["res"] == r for c in casos_junit) for r in ("PASS", "FAIL", "SKIP")}
    aprob_ca = sum(1 for a in aceptacion.values() if a["estado"] == "APROBADO")
    abiertos = sum(1 for d in defectos if d.get("Estado", "").startswith("Abierto"))
    tabla(doc, ["Indicador", "Valor"], [
        ("Casos del informe (CT)", f"{len(CASOS)}: {estados['Aprobada']} aprobados, {estados['Fallida']} fallidos, "
                                   f"{estados['Bloqueada']} bloqueados"),
        ("Ejecuciones automatizadas (pytest)", f"{len(casos_junit)}: {total['PASS']} aprobadas, {total['FAIL']} "
                                               f"fallidas, {total['SKIP']} omitidas"),
        ("Escenarios de aceptación", f"{aprob_ca}/{len(aceptacion)} aprobados ({resumen_aceptacion})"),
        ("Capturas de evidencia", str(len(capturas))),
        ("Defectos registrados", f"{len(defectos)} ({abiertos} abiertos)"),
    ], anchos=[6, 10.5])
    filas_cov, con_huecos = [], []
    for ruta in PRODUCCION:
        if ruta in cov["files"]:
            s = cov["files"][ruta]["summary"]
            faltan = cov["files"][ruta].get("missing_branches") or []
            if faltan or cov["files"][ruta].get("missing_lines"):
                con_huecos.append(ruta)
            filas_cov.append((ruta, f"{s['covered_lines']}/{s['num_statements']}",
                              f"{s['covered_branches']}/{s['num_branches']}", f"{s['percent_covered']:.1f}%",
                              ", ".join(f"{a}->{'salida' if b < 0 else b}" for a, b in faltan) or "—"))
    tabla(doc, ["Módulo", "Líneas", "Ramas", "Cobertura", "Ramas sin cubrir"], filas_cov)
    if con_huecos == ["main.py"]:
        doc.add_paragraph("La única rama sin cubrir es la ejecución normal de main.py sin la opción "
                          "--salir-tras-ms: la ventana queda abierta hasta que el usuario la cierra, por lo que se "
                          "deja a una prueba manual.")
    elif con_huecos:
        doc.add_paragraph("Módulos con líneas o ramas sin cubrir: " + ", ".join(con_huecos) + ".")
    doc.add_heading("Conclusión de calidad", level=2)
    if estados["Aprobada"] == len(CASOS) and total["FAIL"] == 0 and aprob_ca == len(aceptacion) and abiertos == 0:
        doc.add_paragraph(
            f"Los {len(CASOS)} casos del informe están aprobados, las {len(casos_junit)} ejecuciones automatizadas "
            f"pasan, los {len(aceptacion)} escenarios de aceptación coinciden con lo esperado en pantalla y no "
            "quedan defectos abiertos. Con los criterios de la sección 5, el software cumple R01–R08 y los "
            "comportamientos observables de los 10 elementos según la especificación y las decisiones de la "
            "sección 4. Las limitaciones principales son las de la sección 8: interpretación de la "
            "especificación, ejecución sobre pantalla virtual y tiempo simulado.")
    else:
        doc.add_paragraph(
            f"Hay {estados['Fallida']} casos fallidos, {estados['Bloqueada']} bloqueados, {total['FAIL']} "
            f"ejecuciones fallidas y {abiertos} defectos abiertos. El software no se considera aceptado hasta "
            "resolverlos.")

    # 13. Referencias
    doc.add_heading("13. Referencias", level=1)
    for i, r in enumerate(REFERENCIAS, 1):
        doc.add_paragraph(f"[{i}] {r}")

    # 14. Anexo IA
    doc.add_heading("14. Anexo: uso de inteligencia artificial", level=1)
    doc.add_heading("Declaración de colaboración", level=2)
    doc.add_paragraph(
        "Claude Code, asistente de inteligencia artificial de Anthropic, colaboró con el Equipo 3 en la "
        "realización de este proyecto: escribió el código del clúster y de su interfaz, diseñó y programó las "
        "pruebas y los escenarios de aceptación, preparó los scripts de evidencia, revisó las capturas y "
        "redactó este informe. Las decisiones sobre la especificación (D1–D7) las tomó el equipo, que además "
        "ejecutó cada etapa en su propio equipo y validó los resultados reales antes de continuar.")
    doc.add_heading("Detalle", level=2)
    doc.add_paragraph(
        "En este proyecto se usaron asistentes de inteligencia artificial. Según la bitácora, las Etapas 0 a 3 se "
        "trabajaron con un asistente en otra sesión y las Etapas 4 a 8e con Claude Code (Anthropic). La IA generó "
        "el código, las pruebas, los valores esperados de los escenarios, los scripts de evidencia y este "
        "documento. El equipo ejecutó cada etapa en su máquina virtual, revisó la salida real antes de continuar "
        "y tomó las decisiones de interpretación D1–D7. Ningún resultado de este informe se escribió a mano: "
        "todos provienen de las ejecuciones guardadas en docs/evidencias/. La bitácora completa se transcribe a "
        "continuación.")
    for linea in bitacora.splitlines():
        if linea.startswith("# "):
            continue
        if linea.startswith("## "):
            doc.add_heading(linea[3:], level=3)
        elif linea.startswith("- "):
            doc.add_paragraph(linea[2:], style="List Bullet")
        elif linea.strip() and doc.paragraphs:
            doc.paragraphs[-1].add_run(" " + linea.strip())
    return doc, evaluados


def _incluye(rango, n):
    for parte in re.split(r",\s*", rango):
        m = re.match(r"(\d+)(?:–(\d+))?$", parte.strip())
        if m and int(m.group(1)) <= n <= int(m.group(2) or m.group(1)):
            return True
    return False


def convertir_pdf(docx):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("ERROR: falta LibreOffice (soffice) para generar el PDF")
    r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                       capture_output=True, text=True, timeout=300)
    pdf = docx.with_suffix(".pdf")
    if r.returncode != 0 or not pdf.is_file():
        sys.exit(f"ERROR al convertir a PDF: {r.stderr or r.stdout}")
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    return pdf, paginas


def main():
    for nombre in EVIDENCIAS:
        leer(EVID / nombre)
    doc, evaluados = construir()
    SALIDA.parent.mkdir(exist_ok=True)
    doc.save(SALIDA)
    print(f"OK {SALIDA.relative_to(RAIZ)}")
    for caso, estado, _ in evaluados:
        print(f"  {caso['id']}: {estado}")
    pdf, paginas = convertir_pdf(SALIDA)
    print(f"OK {pdf.relative_to(RAIZ)} ({paginas} paginas)")
    return 0 if all(estado == "Aprobada" for _, estado, _ in evaluados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
