"""Genera informe/Informe_Tecnico_Cluster_F40.docx y .pdf (entregable 3 de la guia).

Sigue el "contenido sugerido del informe tecnico" de la guia (10 secciones). Los
resultados de las pruebas P01-P12, las metricas, las bitacoras de ejemplo, la
configuracion y los datos de entrada se leen de los archivos reales del
proyecto; si falta una evidencia el script se detiene.

Uso (desde la raiz del proyecto): python informe/generar_informe_tecnico.py"""

import json
import pathlib
import platform
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from generar_informe import (DECISIONES, IDENTIFICACION, REGLAS, cargar_junit, codigo, convertir_pdf,  # noqa: E402
                             ejecuciones, ficha, figura, leer, numero_pagina, sistema_operativo, tabla, version_software,
                             vinetas)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
EVID = DOCS / "evidencias"
SALIDA = RAIZ / "informe" / "Informe_Tecnico_Cluster_F40.docx"

FICHAS = (
    {"n": "1", "nombre": "Velocímetro", "cat": "Indicador principal", "clave": "velocidad", "tipo": "Decimal (float IEEE-754 de 64 bits)",
     "rango": "km/h; 0 a 360; inicial 0.0", "ciclo": "100 ms", "visual": "Aguja de bloques y cifra (120.5 km/h)",
     "adv": "Sin umbral propio; R01: vuelve a 0 al apagar el motor. Prioridad normal.",
     "invalido": "Ausente, texto o fuera de rango: se conserva el último valor válido y se registra ERROR (dato_invalido, fuera_de_rango o clave_faltante) en logs/errores.log.",
     "evento": "INFO valor_actualizado en logs/eventos.log",
     "just": "La especificación usa décimas (120.5 km/h); un decimal evita truncar y la precisión de 64 bits sobra para una décima."},
    {"n": "2", "nombre": "Presión de aceite (medidor)", "cat": "Información en línea", "clave": "presion_aceite", "tipo": "Decimal",
     "rango": "bar; 0 a 10; inicial 0.0", "ciclo": "100 ms", "visual": "Aguja; ámbar inmediato bajo 1 bar con motor activo",
     "adv": "Ámbar < 1 bar. Alimenta al testigo 9. Prioridad media.",
     "invalido": "Igual que el elemento 1.", "evento": "INFO valor_actualizado",
     "just": "Los umbrales 0.99 / 1.0 / 1.2 bar requieren centésimas."},
    {"n": "3", "nombre": "Tacómetro", "cat": "Información en línea", "clave": "rpm", "tipo": "Entero sin fracción",
     "rango": "rpm; 0 a 9000; inicial 0", "ciclo": "100 ms", "visual": "Aguja; rojo ≥ 8000, normal < 7800 (histéresis)",
     "adv": "WARN tacometro_rojo (R03).",
     "invalido": "Un decimal (4500.5) o texto se rechaza: no se redondea en silencio.", "evento": "INFO valor_actualizado; WARN tacometro_rojo",
     "just": "No existen fracciones de rpm; el rango cabe en 16 bits sin signo (0-65535)."},
    {"n": "4", "nombre": "Temperatura de agua", "cat": "Indicador principal", "clave": "temp_agua", "tipo": "Decimal",
     "rango": "°C; 40 a 130; inicial 40.0", "ciclo": "500 ms", "visual": "Aguja; rojo > 110, normal ≤ 105",
     "adv": "WARN temperatura_rojo (R04).", "invalido": "Igual que el elemento 1.", "evento": "INFO valor_actualizado; WARN temperatura_rojo",
     "just": "El umbral 110.1 °C requiere décimas; la temperatura cambia lento, por eso su ciclo es de 500 ms."},
    {"n": "5", "nombre": "Presión de turbo", "cat": "Información en línea", "clave": "presion_turbo", "tipo": "Decimal",
     "rango": "bar; 0 a 2; inicial 0.0", "ciclo": "100 ms", "visual": "Aguja; contorno ámbar > 1.5, normal ≤ 1.4",
     "adv": "WARN turbo_ambar (R05).", "invalido": "Igual que el elemento 1.", "evento": "INFO valor_actualizado; WARN turbo_ambar",
     "just": "Los umbrales 1.5 / 1.51 bar requieren centésimas."},
    {"n": "6", "nombre": "Direccionales", "cat": "Testigo informativo", "clave": "direccional", "tipo": "Enumeración: off, izquierda, derecha",
     "rango": "Sin unidad; inicial off", "ciclo": "Parpadeo de 500 ms", "visual": "Testigo verde con flecha a la izquierda o a la derecha",
     "adv": "Informativo. Cede ante la emergencia (R07).", "invalido": "Otro texto: se conserva el último valor y se registra ERROR dato_invalido.",
     "evento": "INFO valor_actualizado direccional=izquierda",
     "just": "Una enumeración cerrada impide estados imposibles (izquierda y derecha a la vez)."},
    {"n": "7", "nombre": "Luces altas", "cat": "Testigo informativo", "clave": "luces_altas", "tipo": "Booleano codificado 0/1",
     "rango": "Inicial 0", "ciclo": "Sin parpadeo", "visual": "Testigo azul fijo", "adv": "Informativo.",
     "invalido": "Cualquier valor distinto de 0 o 1 se rechaza.", "evento": "INFO valor_actualizado",
     "just": "Dos estados; 0/1 es la codificación del ejemplo de la guía."},
    {"n": "8", "nombre": "Intermitentes (emergencia)", "cat": "Testigo informativo", "clave": "emergencia", "tipo": "Booleano 0/1",
     "rango": "Inicial 0", "ciclo": "Parpadeo de 500 ms", "visual": "Testigo ámbar; tapa al direccional", "adv": "Informativo con precedencia visual (R07).",
     "invalido": "Igual que el elemento 7.", "evento": "INFO emergencia_activada / emergencia_desactivada",
     "just": "Dos estados."},
    {"n": "9", "nombre": "Baja presión de aceite (testigo)", "cat": "Testigo de seguridad", "clave": "calculado a partir de presion_aceite",
     "tipo": "Booleano calculado", "rango": "Inicial apagado", "ciclo": "Retardo de 1 s con histéresis",
     "visual": "Rectángulo rojo con borde grueso y etiqueta CRITICA", "adv": "CRÍTICO. WARN prioritario testigo_9_encendido (R02).",
     "invalido": "Si la presión llega inválida se evalúa con el último valor válido.", "evento": "WARN testigo_9_encendido; INFO testigo_9_apagado",
     "just": "Se mide con marcas de tiempo, no contando ciclos: un retraso de la interfaz no altera el segundo de espera."},
    {"n": "10", "nombre": "Falla de frenos", "cat": "Testigo de seguridad", "clave": "falla_frenos", "tipo": "Booleano 0/1",
     "rango": "Inicial 0", "ciclo": "Parpadeo de 300 ms", "visual": "Rectángulo rojo parpadeante, también con motor apagado (D1)",
     "adv": "CRÍTICO. WARN prioritario testigo_10_encendido (R08).", "invalido": "Igual que el elemento 7.",
     "evento": "WARN testigo_10_encendido; INFO testigo_10_apagado", "just": "Dos estados; el parpadeo más rápido lo distingue de los informativos."},
)

PRUEBAS = (
    ("P01", "Valor normal", "velocidad=72", "Escribir el archivo, leer y aplicar un ciclo", "Indicador actualizado y evento INFO", ["CP-91"]),
    ("P02", "Límite inferior", "0 km/h, 0 rpm, 0 bar, 40 °C, 0 bar", "Leer el archivo con todos los mínimos", "Valores aceptados sin error", ["CP-92"]),
    ("P03", "Límite superior", "360 km/h, 9000 rpm, 10 bar, 130 °C, 2 bar", "Leer el archivo con todos los máximos", "Valores aceptados sin error", ["CP-93"]),
    ("P04", "Fuera de rango", "361, -1, 9001, 39.9, 2.01", "Cambiar un valor fuera de rango", "Rechazo controlado, aviso y ERROR", ["CP-94", "CP-77"]),
    ("P05", "Formato incorrecto", "abc, 4500.5, si, arriba, nan", "Escribir texto donde va un número", "Continúa con el último valor válido", ["CP-95"]),
    ("P06", "Dato ausente", "Archivo vacío; clave faltante", "Leer sin claves", "Estado definido y error registrado", ["CP-96"]),
    ("P07", "Archivo inexistente", "Ruta retirada", "Leer sin archivo y luego restaurarlo", "No termina; se recupera", ["CP-97"]),
    ("P08", "Actualización concurrente", "300 escrituras atómicas mientras el hilo lee cada 1 ms", "Comprobar cada dato leído", "Sin valores parciales ni corrupción", ["CP-98"]),
    ("P09", "Advertencia", "presion_aceite=0.5 sostenida; falla_frenos=1", "Avanzar 1.2 s", "Testigo visible y WARN prioritario", ["CP-99"]),
    ("P10", "Recuperación", "rpm=abc y luego rpm=2500", "Corregir la entrada", "Retoma sin reinicio", ["CP-100", "CP-77"]),
    ("P11", "Permisos", "Archivo 000, archivo 666; bitácoras", "Leer y comprobar modos", "Operación rechazada y registrada; bitácoras 640", ["CP-101", "CP-102", "CP-103"]),
    ("P12", "Ejecución prolongada", "3000 ciclos acelerados y ejecución real con simulador", "Medir bitácoras, memoria e intervalo", "Sin crecimiento ilimitado", ["CP-104"]),
)

JUSTIFICACIONES = (
    ("¿Por qué ese formato de entrada?",
     "Que los diez valores se cambien desde fuera, sin tocar el código.",
     "JSON; CSV; archivo clave=valor.",
     "Sencillez para editar a mano, validación línea por línea, seguridad.",
     "Archivo de texto clave=valor (datos/vehiculo.conf), el formato del ejemplo de la guía.",
     "Se edita con cualquier editor y cada línea se valida por separado; no admite estructuras anidadas (no las necesita).",
     "sistema/lector.py: parsear, convertir; CP-91 a CP-96, CP-107."),
    ("¿Por qué esa frecuencia de actualización?",
     "Mostrar cada cambio sin desperdiciar CPU.",
     "Leer y dibujar en cada evento; ciclos de 10 ms; ciclos de 100/50 ms.",
     "Respuesta, consumo, prioridad.",
     "Lectura cada 100 ms (el ciclo más rápido de la especificación) y refresco cada 50 ms (la mitad, para no perder cambios).",
     "Respuesta de 100 ms o menos con bajo consumo; los valores ya leídos se ignoran si el archivo no cambió (fecha y tamaño).",
     "config/cluster.ini; intervalo real medido en docs/evidencias/metricas.txt."),
    ("¿Qué mecanismo comunica los componentes y qué alternativa se descartó?",
     "Pasar los datos del lector a la interfaz sin bloquearla.",
     "Variables globales compartidas; tubería; cola en memoria.",
     "Seguridad entre hilos, sencillez, memoria acotada.",
     "Entre procesos: archivo con escritura atómica. Entre hilos: queue.Queue(maxsize=1), un buzón productor-consumidor.",
     "Las variables globales se descartaron por condiciones de carrera; la cola ya trae sus candados. Solo se conserva el dato más reciente.",
     "sistema/lector.py: HiloLector, publicar, Consumidor; CP-98, CP-108."),
    ("¿Cómo se evita que dos tareas modifiquen el mismo recurso a la vez?",
     "El lector y la interfaz corren en hilos distintos.",
     "Candados en EstadoCluster; un solo dueño por recurso.",
     "Riesgo de interbloqueo, sencillez.",
     "Un solo dueño: solo el hilo de la interfaz modifica EstadoCluster y la ventana (Tkinter no es seguro entre hilos). El lector solo produce copias.",
     "Sin candados en el modelo y sin interbloqueos. La bitácora usa los candados internos de logging y el contador usa un Lock.",
     "main.py (Aplicacion); sistema/bitacora.py; CP-98, CP-115."),
    ("¿Qué datos se conservan en memoria y cuáles se persisten?",
     "Estado actual rápido, pero historial y errores recuperables.",
     "Guardar todo en disco; todo en memoria; separación.",
     "Rendimiento, durabilidad, recuperación.",
     "En memoria: el estado de los diez elementos y el último valor válido. En disco: configuración, datos de entrada, eventos y errores, en archivos separados.",
     "Memoria constante (sin historial en RAM); la bitácora es la historia y rota por tamaño.",
     "logic/estado.py; sistema/lector.py (ultimo_valido); logs/; CP-104, metricas.txt."),
    ("¿Por qué los permisos y controles son suficientes?",
     "Evitar que otro usuario manipule los datos o lea las bitácoras.",
     "Confiar en los permisos por defecto; restringir.",
     "Mínimo privilegio, detección.",
     "Bitácoras 640, carpeta de logs 750, archivo de datos escrito con 640; un archivo de datos escribible por cualquiera se rechaza.",
     "Otro usuario no puede inyectar datos ni leer las bitácoras; el dueño conserva el control.",
     "sistema/bitacora.py, sistema/lector.py; CP-101 a CP-103."),
    ("¿Cómo se recupera el sistema después de un dato corrupto o una interrupción?",
     "Que un error no detenga el tablero.",
     "Detener y reiniciar; ignorar el error; conservar el último válido.",
     "Disponibilidad, trazabilidad.",
     "Cada clave conserva su último valor válido; el error se registra una vez; al corregir el archivo se aplica sin reiniciar.",
     "El tablero sigue mostrando un estado coherente; durante el error el valor puede estar desactualizado (limitación aceptada).",
     "CP-95, CP-97, CP-100, CP-110, CP-111; docs/evidencias/bitacoras/con_errores."),
)

AMENAZAS = (
    ("Datos de entrada inválidos o manipulados", "Validación de tipo, formato, rango y largo antes de usar cada valor",
     "ERROR en errores.log con el texto recibido", "Se conserva el último valor válido", "CP-94, CP-95, CP-107"),
    ("Otro usuario modifica el archivo de datos", "Permisos 640; rechazo de archivos escribibles por cualquiera",
     "ERROR permisos_inseguros", "Al corregir el permiso se vuelve a leer sin reiniciar", "CP-101, CP-102"),
    ("Lectura de un archivo a medio escribir", "Escritura en temporal + os.replace atómico",
     "Validación de cada clave", "Se descarta el dato incompleto", "CP-98, CP-112"),
    ("Llenado del disco por bitácoras", "Rotación por tamaño con respaldos fijos", "Tamaño medido en la prueba P12",
     "Los archivos más viejos se descartan", "CP-104, metricas.txt"),
    ("Rutas fuera del proyecto en la configuración", "Solo rutas relativas dentro de la carpeta del proyecto",
     "ERROR ruta_rechazada", "Se usa la ruta por defecto", "CP-106"),
    ("Inyección de comandos", "El programa no arma comandos de sistema con datos; ps se llama con lista de argumentos",
     "No aplica", "No aplica", "Revisión de código (subprocess sin shell)"),
)


def resultado(casos, ids):
    ejec = [c for i in ids for c in ejecuciones(casos, i)]
    faltan = [i for i in ids if not ejecuciones(casos, i)]
    n = {r: sum(c["res"] == r for c in ejec) for r in ("PASS", "FAIL", "SKIP")}
    estado = "Bloqueada" if faltan or n["SKIP"] else ("Fallida" if n["FAIL"] else "Aprobada")
    return estado, f"{len(ejec)} ejecuciones de {', '.join(ids)}: {n['PASS']} aprobadas, {n['FAIL']} fallidas, {n['SKIP']} omitidas."


def construir():
    casos, fecha = cargar_junit()
    cov = json.loads(leer(EVID / "coverage.json"))
    metricas = leer(EVID / "metricas.txt").splitlines()
    config = leer(RAIZ / "config" / "cluster.ini").splitlines()
    datos = leer(RAIZ / "datos" / "vehiculo.conf").splitlines()
    ejemplos = {c: {n: leer(EVID / "bitacoras" / c / n).splitlines() if (EVID / "bitacoras" / c / n).exists() else []
                    for n in ("eventos.log", "errores.log")} for c in ("exitosa", "con_errores")}

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10.5)
    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.add_run("Informe técnico — Clúster F40 simulado — página ")
    numero_pagina(pie)

    # 1. Portada
    for _ in range(3):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Informe Técnico\nSimulador del clúster del Ferrari F40 (1987)")
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s.add_run("Proyecto final de Sistemas Operativos. Software simulado: sin ECU ni sensores reales; rangos didácticos.").italic = True
    doc.add_heading("1. Portada e identificación del proyecto", level=1)
    tabla(doc, ["Campo", "Valor"], list(IDENTIFICACION) + [
        ("Vehículo", "Ferrari F40, 1987"),
        ("Fecha de ejecución de las pruebas", fecha or "no registrada"),
        ("Versión del software", version_software()),
        ("Repositorio", "https://github.com/ayocesaar/cluster-f40 (privado)"),
        ("Colaboración", "Claude Code (Anthropic), asistente de inteligencia artificial; ver anexo"),
    ], anchos=[5, 11.5])
    doc.add_paragraph("Documentos relacionados: Informe de pruebas (informe/Informe_Pruebas_Cluster_F40.pdf), "
                      "matriz de trazabilidad (docs/matriz_trazabilidad.md), README.md y carpeta estudio/.")
    doc.add_page_break()

    # 2. Objetivo, alcance y vehiculo
    doc.add_heading("2. Objetivo, alcance y vehículo seleccionado", level=1)
    doc.add_paragraph("Objetivo: simular el clúster de instrumentos de un Ferrari F40 (1987) que recibe sus diez valores desde "
                      "un archivo externo, los valida, actualiza el tablero sin reiniciar, registra eventos y errores en "
                      "bitácoras separadas y aplica mecanismos de sistema operativo: hilos, comunicación productor-consumidor, "
                      "escritura atómica, permisos y rotación de archivos.")
    vinetas(doc, [
        "Dentro del alcance: entrada por archivo, configuración externa, validación, modelo con reglas R01–R08, interfaz "
        "Tkinter 8-bit, bitácoras, pruebas P01–P12 y métricas.",
        "Fuera del alcance: hardware, ECU y sensores reales; calibraciones del F40; plataformas distintas de Linux y Windows.",
        "La interfaz sigue la distribución del tablero del F40: velocímetro y tacómetro grandes al centro, medidores chicos "
        "a los lados y los testigos críticos arriba, entre las esferas."])
    figura(doc, EVID / "capturas" / "03_umbrales_de_lecturas.png", "Figura 1. Tablero con advertencias activas (captura real).")

    # 3. Diez elementos
    doc.add_heading("3. Descripción y ficha de los diez elementos", level=1)
    doc.add_paragraph("Categorías según la guía: 2 indicadores principales (1 y 4), 3 de información en línea (2, 3 y 5), "
                      "3 testigos informativos (6, 7 y 8) y 2 testigos de seguridad (9 y 10).")
    tabla(doc, ["N.º", "Elemento", "Categoría", "Clave en datos/vehiculo.conf", "Tipo", "Unidad, rango e inicial"],
          [(f["n"], f["nombre"], f["cat"], f["clave"], f["tipo"], f["rango"]) for f in FICHAS])
    for f in FICHAS:
        doc.add_heading(f"Ficha del elemento {f['n']}: {f['nombre']}", level=2)
        fuente = (f"datos/vehiculo.conf, clave {f['clave']}" if not f["clave"].startswith("calculado")
                  else "Calculado por EstadoCluster a partir de la clave presion_aceite de datos/vehiculo.conf")
        ficha(doc, [("Categoría", f["cat"]), ("Fuente del dato", fuente),
                    ("Tipo de dato", f["tipo"]), ("Unidad, rango y valor inicial", f["rango"]),
                    ("Frecuencia de actualización", f["ciclo"]), ("Regla de visualización", f["visual"]),
                    ("Advertencia y prioridad", f["adv"]), ("Valor ausente, corrupto o fuera de rango", f["invalido"]),
                    ("Evento y archivo de destino", f["evento"]), ("Justificación", f["just"])])
    doc.add_heading("Reglas de funcionamiento", level=2)
    tabla(doc, ["Regla", "Descripción"], REGLAS, anchos=[1.8, 14.7])

    # 4. Arquitectura
    doc.add_heading("4. Arquitectura y estructura de archivos", level=1)
    figura(doc, DOCS / "diagramas" / "arquitectura.png", "Figura 2. Componentes y flujo de datos.")
    tabla(doc, ["Componente", "Archivo", "Responsabilidad", "No hace"], [
        ("Entrada de datos", "sistema/lector.py", "Leer y convertir datos/vehiculo.conf en un hilo propio", "Dibujar la interfaz"),
        ("Validador", "sistema/lector.py y logic/estado.py", "Comprobar tipo, formato, rango y largo (dos capas)", "Aceptar datos inválidos en silencio"),
        ("Modelo del vehículo", "logic/estado.py", "Último estado válido de los diez elementos y reglas R01–R08", "Depender del dibujo"),
        ("Interfaz", "ui/presentacion.py, ui/tablero.py", "Representar indicadores y testigos", "Modificar archivos de configuración"),
        ("Registrador", "sistema/bitacora.py, sistema/monitor.py", "Eventos, advertencias y errores con fecha y nivel", "Mezclar niveles en un archivo"),
        ("Configuración", "sistema/config.py, config/cluster.ini", "Rutas, intervalos, rangos y rotación", "Obligar a recompilar"),
    ], anchos=[3, 4, 5.5, 4])
    codigo(doc, ["cluster-f40/", "├── main.py, iniciar.sh, abrir_cluster.bat   # arranque",
                 "├── logic/       # modelo (estado.py) y reloj", "├── sistema/     # config, lector, bitácora, monitor",
                 "├── ui/          # presentación y tablero Tkinter", "├── config/      # cluster.ini",
                 "├── datos/       # vehiculo.conf (entrada modificable)", "├── logs/        # eventos.log, errores.log (se generan)",
                 "├── tests/       # pruebas y datos de prueba", "├── tools/       # simulador, escribir_dato, métricas, capturas",
                 "├── aceptacion/  # ejecutor de escenarios", "├── docs/        # evidencias, diagramas, matriz",
                 "├── informe/     # generadores e informes PDF", "└── estudio/     # material de estudio"])

    # 5. Representacion y flujo
    doc.add_heading("5. Representación y flujo de los datos", level=1)
    doc.add_paragraph("Tipos (bloque 4.1). Python representa los enteros con precisión arbitraria y los decimales como "
                      "IEEE-754 de 64 bits; los rangos se validan explícitamente, así que no hay desbordamiento. Las RPM son "
                      "enteras y un decimal se rechaza en lugar de redondearse. Caso de codificación: en Python bool es "
                      "subclase de int (True == 1); por eso la validación revisa primero si el valor es booleano, y en el "
                      "archivo los booleanos se codifican como 0/1 y el direccional como una enumeración de tres palabras.")
    vinetas(doc, ["Formatos aceptados: entero [+-]dígitos; decimal con hasta 4 decimales; se rechazan nan, inf, notación "
                  "científica y valores de más de 32 caracteres.",
                  "Sin desplazamiento ni escala: el valor del archivo es el valor físico en su unidad.",
                  "La conversión es reversible: formatear y convertir son inversas (CP-109)."])
    figura(doc, DOCS / "diagramas" / "flujo_actualizacion.png", "Figura 3. Secuencia de una actualización.")
    doc.add_paragraph("Archivo de datos de la demostración (datos/vehiculo.conf):")
    codigo(doc, datos)

    # 6. Procesos, comunicacion y sincronizacion
    doc.add_heading("6. Procesos, actualización, comunicación y sincronización", level=1)
    tabla(doc, ["Actividad", "Dónde corre", "Frecuencia", "Prioridad"], [
        ("Simulador o editor (productor externo)", "Proceso aparte", "Cuando cambian los datos", "Baja"),
        ("Lectura y validación", "Hilo lector (daemon), Event.wait", "100 ms", "Media"),
        ("Consumo, tick, monitor y dibujo", "Hilo principal, Tk after()", "50 ms", "Alta: el monitor de seguridad va primero"),
        ("Escritura de bitácoras", "Quien detecta el evento; logging con candados", "Por evento", "WARN de seguridad inmediato"),
    ], anchos=[4.5, 4.5, 3, 4.5])
    doc.add_paragraph("La tarea más crítica es la evaluación de los testigos 9 y 10. Si el ciclo se retrasa, la pantalla "
                      "se actualiza tarde, pero las reglas no se equivocan: el retardo de 1 s del testigo 9 se mide con "
                      "marcas de tiempo y los parpadeos con el reloj absoluto. No hay espera activa: el hilo lector "
                      "duerme con Event.wait y la interfaz con after().")
    doc.add_paragraph("Comunicación: productor externo → archivo (escritura atómica) → hilo lector → buzón "
                      "queue.Queue(maxsize=1) → interfaz. Ningún objeto se modifica desde dos hilos. La prueba P08 (CP-98) "
                      "ejecuta 300 escrituras mientras el hilo lee cada 1 ms y comprueba que cada dato leído es "
                      "consistente.")
    for pregunta, *partes in JUSTIFICACIONES:
        doc.add_heading(pregunta, level=2)
        ficha(doc, list(zip(("Necesidad", "Alternativas", "Criterios", "Decisión", "Consecuencia", "Evidencia"), partes)))

    # 7. Memoria y persistencia
    doc.add_heading("7. Memoria, persistencia y almacenamiento", level=1)
    vinetas(doc, [
        "En memoria: un objeto EstadoCluster de tamaño fijo, el diccionario del último valor válido (10 claves) y un buzón de "
        "capacidad 1. No hay historial en RAM, así que la memoria no crece con el tiempo.",
        "La ventana crea sus figuras de pixeles una sola vez y después solo las mueve o recolorea; guarda el último valor "
        "dibujado para no repetir trabajo (localidad: se reutilizan los mismos objetos).",
        "Persistencia: config/cluster.ini y datos/vehiculo.conf se sobrescriben completos (acceso secuencial); las bitácoras "
        "solo se agregan al final y rotan por tamaño (max_bytes y número de respaldos).",
        "Durabilidad: la escritura atómica hace fsync antes del renombrado; tras una interrupción queda la versión vieja "
        "completa o la nueva completa."])
    doc.add_paragraph("Métricas reales de la ejecución prolongada (docs/evidencias/metricas.txt):")
    codigo(doc, metricas)

    # 8. Seguridad
    doc.add_heading("8. Seguridad, amenazas y controles", level=1)
    tabla(doc, ["Amenaza", "Preventivo", "Detección", "Recuperación", "Evidencia"], AMENAZAS)
    doc.add_paragraph("No hay contraseñas, tokens ni datos sensibles en el código. Las rutas son relativas al proyecto. "
                      "El programa no ejecuta comandos construidos con datos de entrada.")

    # 9. Errores y bitacoras
    doc.add_heading("9. Manejo de errores y bitácoras", level=1)
    doc.add_paragraph("Cada línea tiene fecha ISO 8601 con zona horaria, nivel (INFO, WARN, ERROR), componente, evento, "
                      "detalle y resultado. logs/eventos.log guarda la operación normal y las advertencias; logs/errores.log "
                      "guarda solo errores. Un mismo error se registra una vez mientras dura, para no inundar la bitácora "
                      "(CP-110).")
    for nombre, titulo in (("exitosa", "Ejecución exitosa"), ("con_errores", "Ejecución con errores")):
        doc.add_heading(titulo, level=2)
        doc.add_paragraph(f"docs/evidencias/bitacoras/{nombre}/eventos.log:")
        codigo(doc, ejemplos[nombre]["eventos.log"][:18] or ["(vacío)"])
        doc.add_paragraph(f"docs/evidencias/bitacoras/{nombre}/errores.log:")
        codigo(doc, ejemplos[nombre]["errores.log"][:18] or ["(vacío: no hubo errores)"])
    doc.add_paragraph("Configuración vigente (config/cluster.ini):")
    codigo(doc, [l for l in config if l.strip() and not l.startswith("#")])

    # 10. Pruebas, resultados, limitaciones y conclusiones
    doc.add_heading("10. Pruebas, resultados, limitaciones y conclusiones", level=1)
    filas, aprobadas = [], 0
    for pid, caso, entrada, proc, esperado, ids in PRUEBAS:
        estado, obtenido = resultado(casos, ids)
        aprobadas += estado == "Aprobada"
        filas.append((pid, caso, entrada, proc, esperado, obtenido, estado))
    tabla(doc, ["ID", "Caso", "Entrada", "Procedimiento", "Esperado", "Obtenido", "Estado"], filas)
    total = {r: sum(c["res"] == r for c in casos) for r in ("PASS", "FAIL", "SKIP")}
    cob = cov["totals"]
    tabla(doc, ["Indicador", "Valor"], [
        ("Pruebas obligatorias P01–P12", f"{aprobadas}/12 aprobadas"),
        ("Ejecuciones automatizadas (pytest)", f"{len(casos)}: {total['PASS']} aprobadas, {total['FAIL']} fallidas, {total['SKIP']} omitidas"),
        ("Cobertura total (líneas y ramas)", f"{cob['percent_covered']:.1f}%"),
        ("Plataforma", f"{sistema_operativo()}; Python {platform.python_version()}"),
    ], anchos=[6, 10.5])
    doc.add_heading("Limitaciones", level=2)
    vinetas(doc, [
        "Durante un error de entrada el tablero muestra el último valor válido, que puede estar desactualizado.",
        "La interfaz se probó con Tkinter real sobre una pantalla virtual (Xvfb) y en Windows; no en otras plataformas.",
        "El editor de texto que guarde sobre el mismo archivo puede producir una lectura incompleta; la validación la "
        "rechaza y se usa la siguiente. Para cambios en vivo se recomienda tools/escribir_dato.py (atómico).",
        "Los permisos POSIX no aplican en Windows; ahí esas pruebas se omiten.",
        "Las categorías de los elementos 2, 3 y 5 (información en línea) deben confirmarse con el profesor."])
    doc.add_heading("Conclusiones", level=2)
    doc.add_paragraph(
        f"Las {aprobadas} de 12 pruebas obligatorias están aprobadas y las {len(casos)} ejecuciones automatizadas registran "
        f"{total['FAIL']} fallos. El sistema recibe sus datos de un archivo externo, los valida en dos capas, se recupera de "
        "datos corruptos o ausentes sin reiniciar, separa eventos y errores y mantiene acotados la memoria y el disco.")
    doc.add_heading("Anexo: colaboración de inteligencia artificial", level=2)
    doc.add_paragraph("Claude Code (Anthropic) colaboró con el Equipo 3: escribió el código, las pruebas, los scripts de "
                      "evidencia y este informe. El equipo tomó las decisiones de interpretación, ejecutó cada etapa y "
                      "validó los resultados. El detalle está en docs/bitacora_ia.md y en el informe de pruebas.")
    return doc, aprobadas


def main():
    doc, aprobadas = construir()
    doc.save(SALIDA)
    print(f"OK {SALIDA.relative_to(RAIZ)} (P01-P12 aprobadas: {aprobadas}/12)")
    pdf, paginas = convertir_pdf(SALIDA)
    print(f"OK {pdf.relative_to(RAIZ)} ({paginas} paginas)")
    return 0 if aprobadas == 12 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
