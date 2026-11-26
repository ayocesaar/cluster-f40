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
    {"n": "11", "nombre": "Odómetro (agregado tras la práctica en clase)", "cat": "Información en línea",
     "clave": "calculado a partir de la velocidad; odometro= en datos/vehiculo.conf se rechaza (clave_no_permitida)",
     "fuente": "Calculado por EstadoCluster (logic/odometro.py) a partir de la velocidad mostrada; el kilometraje inicial "
               "se lee de datos/odometro.txt (sistema/odometro_archivo.py)",
     "tipo": "Decimal interno (fracción de km); se muestra como entero de 6 dígitos",
     "rango": "km; 000000 a 999999, después vuelve a 000000; inicial: el guardado en datos/odometro.txt",
     "ciclo": "Cada ciclo de 50 ms; se guarda cada 5 s ([odometro] guardar_cada_s) y al cerrar",
     "visual": "Caja de 6 dígitos dentro del velocímetro, etiqueta 11 ODOMETRO KM",
     "adv": "Sin advertencia; no avanza con el motor apagado (R01) ni con velocidad 0. Nunca disminuye.",
     "invalido": "Archivo ausente, corrupto, mayor a 64 bytes, no UTF-8 o escribible por cualquiera: se usa el respaldo .bak "
                 "(WARN odometro_restaurado) o se inicia en 000000 con aviso en pantalla y ERROR odometro_invalido.",
     "evento": "INFO odometro_cargado, odometro_actualizado (cada km) y odometro_guardado; ERROR odometro_no_guardado",
     "just": "distancia = velocidad × tiempo se integra con el tiempo real del reloj, no contando ciclos; la fracción se "
             "conserva para no perder distancia entre ciclos y la escritura atómica con respaldo evita perder el kilometraje."},
    # Elementos adicionales de seguridad y consumo (Etapa 18): se agregan a los diez aprobados.
    {"n": "12", "nombre": "Puerta abierta (adicional)", "cat": "Testigo informativo", "clave": "puertas",
     "fuente": "datos/vehiculo.conf, clave opcional puertas (la escribe el panel desde los interruptores de puerta)",
     "tipo": "Bits de estado en un entero: bit 0 = conductor, bit 1 = pasajero (0 a 3)",
     "rango": "Sin unidad; 0 a 3; sin dato hasta que el productor la envía", "ciclo": "Cada ciclo; parpadeo de 500 ms en movimiento",
     "visual": "Lente redonda con el contorno de una puerta: ámbar fija con el auto detenido, roja parpadeante desde 3 km/h; "
               "texto PUERTA CONDUCTOR / PASAJERO",
     "adv": "R09. En movimiento es advertencia crítica: WARN prioritario puerta_abierta_en_movimiento.",
     "invalido": "Fuera de 0-3 o no entero: ERROR y se conserva el último válido. Si nunca llega queda sin dato (gris) sin error; "
                 "si deja de llegar, INFO clave_opcional_retirada.",
     "evento": "INFO puerta_abierta / puertas_cerradas; WARN puerta_abierta_en_movimiento (eventos.log)",
     "just": "Dos puertas caben en dos bits: un solo entero representa las cuatro combinaciones sin claves extra (caso de "
             "codificación con bits de estado, bloque 4.1)."},
    {"n": "13", "nombre": "Cinturón del conductor (adicional)", "cat": "Testigo de seguridad", "clave": "cinturon",
     "fuente": "datos/vehiculo.conf, clave opcional cinturon (1 = abrochado)", "tipo": "Booleano 0/1",
     "rango": "Sin dato hasta que el productor la envía", "ciclo": "Cada ciclo; parpadeo de 500 ms sobre 10 km/h",
     "visual": "Rectángulo rojo con la figura de una persona y la banda cruzada",
     "adv": "R10. Fijo con contacto y sin abrochar; WARN prioritario cinturon_desabrochado_en_movimiento sobre 10 km/h. "
            "Cumple la parte visual de FMVSS 208 S7.3 (luz de al menos 60 s; texto actual).",
     "invalido": "Distinto de 0 o 1: ERROR y se conserva el último válido; ausente igual que el elemento 12.",
     "evento": "INFO cinturon_desabrochado / cinturon_abrochado; WARN cinturon_desabrochado_en_movimiento",
     "just": "Dos estados; la guía lo pone como ejemplo de testigo de seguridad y su ejemplo de archivo trae cinturon=1."},
    {"n": "14", "nombre": "Combustible (adicional)", "cat": "Información en línea", "clave": "combustible",
     "fuente": "datos/vehiculo.conf, clave opcional combustible (el panel la calcula con el consumo)",
     "tipo": "Decimal (porcentaje del tanque)", "rango": "%; 0 a 100 (tanque de 120 L); sin dato hasta que llega",
     "ciclo": "500 ms (el nivel cambia despacio)",
     "visual": "Barra horizontal con marcas E, 1/2 y F, zona de reserva pintada, porcentaje y litros; testigo de reserva ámbar",
     "adv": "R11. Reserva con histéresis: enciende con 12 % o menos y se apaga con 15 % o más; WARN combustible_reserva.",
     "invalido": "Fuera de 0-100 o texto: ERROR y se conserva el último válido; ausente igual que el elemento 12.",
     "evento": "WARN combustible_reserva; INFO combustible_sobre_reserva",
     "just": "La guía usa combustible=48 en su ejemplo de archivo; el porcentaje no depende del tamaño del tanque y la "
             "histéresis evita que el testigo parpadee cuando el nivel oscila cerca del umbral."},
    {"n": "15", "nombre": "Protección del motor (adicional)", "cat": "Testigo de seguridad", "clave": "falla_motor",
     "fuente": "datos/vehiculo.conf, clave opcional falla_motor (la decide la ECU simulada del panel, panel/ecu.py)",
     "tipo": "Enumeración: ninguna, sobretemperatura, sobrepresion_turbo, aceite, combustible",
     "rango": "Sin unidad; sin dato hasta que llega", "ciclo": "Cada ciclo",
     "visual": "Rectángulo rojo con la palabra STOP y la causa en texto (SOBRETEMPERATURA, ACEITE...)",
     "adv": "R12. CRÍTICO: WARN prioritario motor_detenido_por_proteccion causa=...; INFO proteccion_motor_liberada.",
     "invalido": "Otra palabra: ERROR y se conserva el último válido; ausente igual que el elemento 12.",
     "evento": "WARN motor_detenido_por_proteccion; INFO proteccion_motor_liberada",
     "just": "El cuadro no decide si el motor puede funcionar: solo muestra la causa que envía la ECU. Una enumeración "
             "cerrada impide causas inventadas."},
    {"n": "16", "nombre": "Carga de batería (adicional, Etapa 20)", "cat": "Testigo de seguridad", "clave": "voltaje",
     "fuente": "datos/vehiculo.conf, clave opcional voltaje (el panel la calcula con su modelo de batería y alternador)",
     "tipo": "Decimal (voltios)", "rango": "V; 0 a 20; sin dato hasta que llega", "ciclo": "Cada ciclo",
     "visual": "Rectángulo rojo con una batería; el voltímetro va en la etiqueta (16 CARGA 14.2 V)",
     "adv": "R13. Encendido con contacto y motor apagado (normal, el alternador no gira); con el motor en marcha y "
            "menos de 13.0 V es crítico: WARN prioritario falla_de_carga.",
     "invalido": "Fuera de 0-20 o texto: ERROR y se conserva el último válido; ausente igual que el elemento 12.",
     "evento": "WARN falla_de_carga; INFO carga_normal",
     "just": "La guía pone batería como ejemplo de testigo de seguridad. Un decimal con décimas basta para distinguir "
             "12.6 V (batería) de 14.2 V (alternador cargando)."},
    {"n": "17", "nombre": "Temperatura de aceite (adicional, Etapa 21)", "cat": "Información en línea",
     "clave": "temp_aceite",
     "fuente": "datos/vehiculo.conf, clave opcional temp_aceite (el panel la calcula: sigue al agua, más lento, y sube "
               "con la carga)",
     "tipo": "Decimal", "rango": "°C; 0 a 160; sin dato hasta que llega", "ciclo": "500 ms (cambia despacio)",
     "visual": "Barra bajo el turbo con la zona roja desde 130 °C; la cifra va en la etiqueta",
     "adv": "R14. Rojo sobre 130 °C, normal con 125 °C o menos (histéresis); WARN temperatura_aceite_rojo.",
     "invalido": "Fuera de 0-160 o texto: ERROR y se conserva el último válido; ausente igual que el elemento 12.",
     "evento": "WARN temperatura_aceite_rojo; INFO temperatura_aceite_normal",
     "just": "El F40 tiene este medidor (catálogo de refacciones). El aceite tarda más que el agua en calentarse: "
             "por eso es un elemento aparte y no se deduce de la temperatura del agua."},
)

REGLAS_AGREGADAS = (
    ("Contacto", "Clave opcional contacto: separa Encendido (elementos 1 y 4, odómetro y testigos) de Motor activo (2, 3 y 5), "
                 "como distingue la especificación (D3). Al pasar a contacto, prueba de testigos de 2 s (R13-H 5.2.21.4)."),
    ("R09", "puertas ≠ 0: testigo 12 ámbar fijo detenido; rojo parpadeante (500 ms) desde 3 km/h con WARN prioritario."),
    ("R10", "Contacto y cinturon = 0: testigo 13 rojo fijo; sobre 10 km/h parpadea (500 ms) con WARN prioritario."),
    ("R11", "combustible ≤ 12 %: testigo de reserva ámbar; se apaga con ≥ 15 % (histéresis). Ciclo de 500 ms."),
    ("R12", "falla_motor ≠ ninguna con el cuadro energizado: testigo 15 rojo con la causa y WARN prioritario."),
    ("R13", "Etapa 20. Contacto y motor apagado: testigo 16 encendido (normal); motor en marcha (≥ 800 rpm) con "
            "voltaje < 13.0 V: testigo 16 y WARN prioritario falla_de_carga."),
    ("R14", "Etapa 21. temp_aceite > 130 °C: elemento 17 en rojo y WARN; ≤ 125 °C: normal (histéresis)."),
)

DECISIONES_AGREGADAS = (
    ("D8", "Las cinco claves nuevas son opcionales: un productor de diez claves sigue funcionando igual. Si una opcional "
           "nunca llega no hay error (sin dato); si deja de llegar se registra INFO clave_opcional_retirada."),
    ("D9", "El validador comprueba consistencia entre claves: motor=1 con contacto=0 es dato_inconsistente; se descarta "
           "el contacto y el cuadro sigue al motor (R01)."),
    ("D10", "La prueba de testigos es solo de presentación: no cambia reglas ni registra advertencias falsas."),
    ("D11", "Los interbloqueos y protecciones viven en el panel (panel/ecu.py, el lado del vehículo), no en el cuadro: "
            "el cuadro muestra, la ECU decide. Son medidas del equipo; el F40 de 1987 no las tenía todas."),
    ("D12", "El sensor de velocidad del panel redondea hacia arriba a la décima para no indicar nunca menos que la "
            "velocidad real (UN R39 5.3); antes redondeaba al más cercano (DEF-16)."),
    ("D13", "Caja negra: archivo binario de tamaño fijo (anillo de 600 registros de 32 bytes) con acceso directo, "
            "escrito por un hilo propio con fsync una vez por segundo; la interfaz nunca espera al disco."),
    ("D14", "La batería del panel se carga y descarga 60 veces más rápido para que la falla del alternador se vea en "
            "la demostración (igual que el calentamiento del motor, que ya estaba acelerado)."),
    ("D15", "La falla de una unidad Weber-Marelli no enciende ningún testigo: en 1987 no había testigo de motor. Se "
            "nota al oído, en el tacómetro y en el banco de liberación (L01)."),
    ("D16", "Etapa 21. El empuje sigue una curva de par que pasa por los datos verificados (577 Nm a 4000 rpm y "
            "478 CV a 7000 rpm) y se calibró con el 0-100 y la velocidad máxima publicados; sin ABS ni control de "
            "tracción, como el F40 original (revista de Ferrari)."),
    ("D17", "Etapa 21. Las prácticas de fallas son corrutinas que el ciclo del panel avanza cada 50 ms "
            "(calendarización cooperativa); verifican con una copia en memoria del cuadro real."),
    ("D18", "Etapa 22. Lo que estaba pendiente se verificó en el texto de la época o del fabricante: el banco exige el "
            "frenado de la Directiva 71/320/CEE vigente en 1987 (M1: 80 km/h, 50.7 m, 5.8 m/s²) junto con R13-H y la "
            "tolerancia de UN R84 en el ciclo urbano; el modelo usa las relaciones de la caja, el frenado publicado y un "
            "consumo por potencia calibrado con el consumo del fabricante (ADAC). Lo que no se pudo verificar sigue "
            "marcado como pendiente."),
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
     "En memoria: el estado de los once elementos y el último valor válido. En disco: configuración, datos de entrada, eventos y errores, en archivos separados, "
     "y el kilometraje del odómetro (datos/odometro.txt con respaldo .bak).",
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
    ("Datos contradictorios entre claves (motor sin contacto)", "Regla de consistencia en el validador (D9)",
     "ERROR dato_inconsistente", "Se descarta el contacto y el cuadro sigue al motor", "CP-164"),
    ("Mensajes falsos o malformados a la bocina de sonido", "Escucha solo en 127.0.0.1 y llega por un túnel SSH; "
     "cada línea JSON se valida (claves, tipos, rangos, sin NaN, máximo 512 bytes)", "Contador de mensajes rechazados",
     "El mensaje se descarta y el audio sigue con el último estado válido", "CP-189"),
    ("Caja negra dañada (corte de luz, disco)", "fsync cada segundo; tamaño fijo; CRC por registro y en la cabecera",
     "Registro con CRC inválido; ERROR caja_negra_invalida", "Se salta el registro; una cabecera mala se aparta y se "
     "crea otra", "CP-193"),
)

SEGURIDAD_VEHICULO = (
    ("Puerta abierta", "La ECU bloquea la tracción (el acelerador no tiene efecto)", "Testigo 12; WARN en movimiento",
     "Al cerrar la puerta se puede avanzar", "CP-167, CP-176, L09"),
    ("Fuga o nivel bajo de aceite", "No arranca (nivel < 50 % o fuga); en marcha, corte con < 0.5 bar durante 3 s",
     "Testigo 9 (R02) y testigo 15 ACEITE", "Reparar y rellenar en TALLER", "CP-172, L01"),
    ("Sobrecalentamiento", "Corte del motor a 120 °C; no arranca hasta reparar y enfriar bajo 100 °C",
     "Elemento 4 en rojo desde 110 °C (R04) y testigo 15", "Reparar el radiador; esperar a que enfríe", "CP-173, L07"),
    ("Sobrepresión del turbo", "Corte del motor con más de 1.5 bar durante 1 s; protección enclavada",
     "Contorno ámbar (R05) y testigo 15", "Reparar la válvula de descarga", "CP-174, L08"),
    ("Falla de frenos", "No hay corte: el auto frena al 30 % (un circuito perdido)", "Testigo 10 (R08)",
     "Reparar; el banco la rechaza (tipo 0 y tipo I)", "CP-175, L03, L04"),
    ("Sin combustible", "El motor se apaga solo; no arranca hasta cargar", "Reserva (R11) y testigo 15",
     "Llenar el tanque", "CP-177"),
    ("Alternador que no carga", "No hay corte inmediato; la batería se descarga; bajo 10.5 V durante 1 s la gestión "
     "electrónica se apaga; con la batería bajo 11.6 V en reposo no arranca", "Testigo 16 y WARN falla_de_carga (R13)",
     "Reparar y cargar la batería", "CP-197, CP-198, L01"),
    ("Una unidad Weber-Marelli sin encendido (el F40 tiene una por banco)", "Sin corte: el motor sigue con 4 cilindros, "
     "medio empuje y un turbo", "Ninguno (como en 1987): se oye cojo y el tacómetro oscila", "Reparar", "CP-199, L01"),
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
    caja_negra = leer(EVID / "caja_negra" / "reporte.txt").splitlines()
    banco = leer(EVID / "banco_liberacion.txt").splitlines()
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
        "Tkinter estilo F40, bitácoras, pruebas P01–P12 y métricas.",
        "Ampliación (Etapa 18): cuatro elementos adicionales de seguridad y consumo (12-15), llave de contacto, ECU "
        "simulada con interbloqueos y protecciones, y un banco de liberación de producción con pruebas normalizadas de "
        "la época (frenado UN R13-H, velocímetro UN R39 y ciclo urbano ECE-15). Etapas 19 y 20: sonido del "
        "motor sintetizado, sistema eléctrico con testigo de carga (16), falla de una unidad Weber-Marelli y "
        "una caja negra binaria de acceso directo. Etapa 21: curva de par con datos verificados, adherencia sin "
        "ABS ni control de tracción, temperatura de aceite (17), agujas con inercia y 15 prácticas de fallas "
        "automáticas.",
        "Fuera del alcance: hardware, ECU y sensores reales; calibraciones del F40; plataformas distintas de Linux y Windows.",
        "La interfaz sigue la distribución del tablero del F40: velocímetro y tacómetro grandes al centro, medidores chicos "
        "a los lados y los testigos críticos arriba, entre las esferas."])
    figura(doc, EVID / "capturas" / "03_umbrales_de_lecturas.png", "Figura 1. Tablero con advertencias activas (captura real).")

    # 3. Diez elementos
    doc.add_heading("3. Descripción y ficha de los elementos", level=1)
    doc.add_paragraph("Categorías según la guía: 2 indicadores principales (1 y 4), 3 de información en línea (2, 3 y 5), "
                      "3 testigos informativos (6, 7 y 8) y 2 testigos de seguridad (9 y 10). El odómetro (11, información "
                      "en línea) se agregó después de la práctica en clase, donde el profesor lo asignó como tema de prueba. "
                      "Los elementos 12 a 15 (puerta, cinturón, combustible y protección del motor) son adicionales: no "
                      "sustituyen a los diez aprobados y llegan en claves opcionales del mismo archivo (decisión D8).")
    tabla(doc, ["N.º", "Elemento", "Categoría", "Clave en datos/vehiculo.conf", "Tipo", "Unidad, rango e inicial"],
          [(f["n"], f["nombre"], f["cat"], f["clave"], f["tipo"], f["rango"]) for f in FICHAS])
    for f in FICHAS:
        doc.add_heading(f"Ficha del elemento {f['n']}: {f['nombre']}", level=2)
        fuente = f.get("fuente") or (f"datos/vehiculo.conf, clave {f['clave']}" if not f["clave"].startswith("calculado")
                                     else "Calculado por EstadoCluster a partir de la clave presion_aceite de datos/vehiculo.conf")
        ficha(doc, [("Categoría", f["cat"]), ("Fuente del dato", fuente),
                    ("Tipo de dato", f["tipo"]), ("Unidad, rango y valor inicial", f["rango"]),
                    ("Frecuencia de actualización", f["ciclo"]), ("Regla de visualización", f["visual"]),
                    ("Advertencia y prioridad", f["adv"]), ("Valor ausente, corrupto o fuera de rango", f["invalido"]),
                    ("Evento y archivo de destino", f["evento"]), ("Justificación", f["just"])])
    doc.add_heading("Reglas de funcionamiento", level=2)
    tabla(doc, ["Regla", "Descripción"], REGLAS, anchos=[1.8, 14.7])
    doc.add_heading("Reglas agregadas por el equipo (Etapa 18)", level=2)
    tabla(doc, ["Regla", "Descripción"], REGLAS_AGREGADAS, anchos=[1.8, 14.7])
    doc.add_heading("Decisiones de la Etapa 18", level=2)
    tabla(doc, ["Decisión", "Descripción"], DECISIONES_AGREGADAS, anchos=[1.8, 14.7])
    figura(doc, EVID / "capturas" / "11_proteccion_por_sobretemperatura.png",
           "Figura 1b. Elementos adicionales: motor detenido por la ECU, cinturón y reserva (captura real).")

    # 4. Arquitectura
    doc.add_heading("4. Arquitectura y estructura de archivos", level=1)
    figura(doc, DOCS / "diagramas" / "arquitectura.png", "Figura 2. Componentes y flujo de datos.")
    tabla(doc, ["Componente", "Archivo", "Responsabilidad", "No hace"], [
        ("Entrada de datos", "sistema/lector.py", "Leer y convertir datos/vehiculo.conf en un hilo propio", "Dibujar la interfaz"),
        ("Validador", "sistema/lector.py y logic/estado.py", "Comprobar tipo, formato, rango y largo (dos capas)", "Aceptar datos inválidos en silencio"),
        ("Modelo del vehículo", "logic/estado.py", "Último estado válido de los diez elementos y reglas R01–R08", "Depender del dibujo"),
        ("Odómetro", "logic/odometro.py, sistema/odometro_archivo.py", "Calcular el kilometraje y conservarlo con respaldo",
         "Aceptar el kilometraje desde datos/vehiculo.conf"),
        ("Interfaz", "ui/presentacion.py, ui/tablero.py", "Representar indicadores y testigos", "Modificar archivos de configuración"),
        ("Registrador", "sistema/bitacora.py, sistema/monitor.py", "Eventos, advertencias y errores con fecha y nivel", "Mezclar niveles en un archivo"),
        ("Configuración", "sistema/config.py, config/cluster.ini", "Rutas, intervalos, rangos y rotación", "Obligar a recompilar"),
        ("Panel, ECU y banco (otro proceso)", "panel/ventana.py, panel/fisica.py, panel/ecu.py, panel/liberacion.py",
         "Simular el vehículo, decidir protecciones y correr las pruebas de liberación", "Tocar el cuadro: solo escribe el archivo"),
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
    doc.add_heading("Sonido del motor: un tercer proceso por socket (Etapa 19)", level=2)
    doc.add_paragraph("El panel sintetiza el sonido del motor por código (panel/sonido.py: pulsos de combustión de un V8, "
                      "4 explosiones por vuelta). Como el panel corre en la máquina virtual y las bocinas están en Windows, "
                      "el panel envía el estado del motor (líneas JSON, 20 por segundo) por un socket TCP a tools/bocina.py a "
                      "través de un túnel SSH inverso. En la bocina, un hilo de tiempo real genera bloques de 30 ms y los "
                      "entrega a waveOut, que bloquea cuando su cola está llena; el hilo nunca va más de 120 ms adelante del "
                      "reloj, así la latencia queda acotada. El estado llega por un buzón de tamaño 1, el mismo patrón del "
                      "lector del tablero. Pruebas CP-184 a CP-190; mediciones del audio en docs/evidencias/sonido/reporte.txt.")
    doc.add_heading("Prácticas de fallas: corrutinas en el ciclo del panel (Etapa 21)", level=2)
    doc.add_paragraph("Los 15 botones de prácticas corren casos completos sin manejar a mano (fuga de aceite, "
                      "sobrecalentamiento, frenos, alternador, lluvia sin ABS, 0-100 km/h...). Cada práctica es un "
                      "generador de Python que cede el control al ciclo del panel cada 50 ms o mientras espera una "
                      "condición: calendarización cooperativa, sin hilos nuevos ni espera activa, y la interfaz no se "
                      "bloquea. El robot mueve los pedales con la misma rapidez que el panel y pisa el embrague en cada "
                      "cambio, así la palanca y los pedales dibujados muestran lo que hace. Las verificaciones usan una "
                      "copia en memoria del cuadro real (mismo formato del archivo, validación, modelo y monitor). "
                      "Evidencia: docs/evidencias/practicas.txt; CP-203 a CP-205.")
    for pregunta, *partes in JUSTIFICACIONES:
        doc.add_heading(pregunta, level=2)
        ficha(doc, list(zip(("Necesidad", "Alternativas", "Criterios", "Decisión", "Consecuencia", "Evidencia"), partes)))

    # 7. Memoria y persistencia
    doc.add_heading("7. Memoria, persistencia y almacenamiento", level=1)
    vinetas(doc, [
        "En memoria: un objeto EstadoCluster de tamaño fijo, el diccionario del último valor válido (10 claves) y un buzón de "
        "capacidad 1. No hay historial en RAM, así que la memoria no crece con el tiempo.",
        "La ventana crea sus figuras (menos de 300) una sola vez y después solo mueve las agujas o recolorea; guarda el último valor "
        "dibujado para no repetir trabajo (localidad: se reutilizan los mismos objetos).",
        "Persistencia: config/cluster.ini y datos/vehiculo.conf se sobrescriben completos (acceso secuencial); las bitácoras "
        "solo se agregan al final y rotan por tamaño (max_bytes y número de respaldos).",
        "Durabilidad: la escritura atómica hace fsync antes del renombrado; tras una interrupción queda la versión vieja "
        "completa o la nueva completa."])
    doc.add_paragraph("Métricas reales de la ejecución prolongada (docs/evidencias/metricas.txt):")
    codigo(doc, metricas)
    doc.add_heading("Caja negra: historial acotado con acceso directo (Etapa 20)", level=2)
    doc.add_paragraph("datos/caja_negra.bin guarda los últimos 60 s a 10 muestras por segundo en un anillo de 600 registros "
                      "de 32 bytes con una cabecera de 64 (19 264 bytes fijos: el historial nunca crece). El registro k "
                      "está en el byte 64 + (k mod 600) × 32 y se escribe con pwrite en ese desplazamiento: acceso "
                      "directo, a diferencia de las bitácoras (secuenciales, solo se agrega al final). Formato binario "
                      "con tamaño, signo y escala por campo (por ejemplo, la temperatura es int16 en décimas para admitir "
                      "valores bajo cero) y CRC-16 por registro. Política de escritura: la interfaz deja la muestra en "
                      "una cola acotada y un hilo escritor la graba con fsync una vez por segundo: se arriesga a lo más el "
                      "último segundo a cambio de no frenar la interfaz. Ante un testigo crítico exporta los 10 s previos a "
                      "CSV. Detalle en docs/caja_negra.md; evidencia real (docs/evidencias/caja_negra/reporte.txt):")
    codigo(doc, caja_negra[:12])

    # 8. Seguridad
    doc.add_heading("8. Seguridad, amenazas y controles", level=1)
    tabla(doc, ["Amenaza", "Preventivo", "Detección", "Recuperación", "Evidencia"], AMENAZAS)
    doc.add_paragraph("No hay contraseñas, tokens ni datos sensibles en el código. Las rutas son relativas al proyecto. "
                      "El programa no ejecuta comandos construidos con datos de entrada.")
    doc.add_heading("Seguridad del vehículo simulado (Etapa 18)", level=2)
    doc.add_paragraph("Además de la seguridad informática, el panel simula la seguridad funcional del auto. Las decisiones "
                      "las toma la ECU simulada (panel/ecu.py); el cuadro solo las muestra. Son medidas del equipo: el F40 "
                      "de 1987 no tenía interbloqueo de puertas ni todas estas protecciones.")
    tabla(doc, ["Riesgo", "Control preventivo", "Detección en el cuadro", "Recuperación", "Evidencia"], SEGURIDAD_VEHICULO)

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
    doc.add_heading("Banco de liberación de producción (pruebas de la época)", level=2)
    doc.add_paragraph("Antes de mandar un auto a producción se corren pruebas normalizadas. tools/banco_liberacion.py las "
                      "reproduce sobre el modelo del panel con la misma ECU y, para las del cuadro, con el código real del "
                      "tablero: frenado tipo 0 y tipo I (UN R13-H anexo 3), exactitud del velocímetro (UN R39 5.3 y anexo 3), "
                      "ciclo urbano ECE-15 de 195 s con el odómetro, prueba de testigos (R13-H 5.2.21.4) y tres criterios del "
                      "equipo (enfriamiento, turbo y puertas). Resultado real (docs/evidencias/banco_liberacion.txt):")
    codigo(doc, [l for l in banco if l.startswith(("MATRIZ", "  ", "Resultado"))][-10:])
    doc.add_paragraph("Detalle de la unidad sin fallas:")
    codigo(doc, banco[4:4 + 1 + 9 * 3 + 1])
    doc.add_heading("Limitaciones", level=2)
    vinetas(doc, [
        "El modelo es didáctico: el frenado, el consumo y las velocidades por marcha se calibraron con datos publicados "
        "del F40 (Etapa 22), pero las temperaturas, el sistema eléctrico y la forma de la curva de par son aproximados. "
        "Los criterios del banco son del texto verificado (R13-H, R39, Directiva 71/320/CEE de 1986, Directiva "
        "75/443/CEE y UN R84); queda pendiente el texto de FMVSS 208 de 1987. El banco no mide emisiones: del ciclo "
        "ECE-15 solo usa el perfil de velocidad.",
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
