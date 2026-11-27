# Bitácora de uso de IA — Proyecto Clúster F40

## Etapa 0 — Auditoría
- Fecha: 2026-10-29 00:13
- Qué se hizo: se auditó /home/ayocesaar/cluster-f40, confirmando que estaba vacía (sin trabajo
  previo). Se instalaron paquetes de sistema (python3-tk, python3-venv) con sudo del usuario. Se
  creó el entorno virtual .venv y se instalaron pytest, coverage, pillow y python-docx dentro de
  él. Se inicializó el repositorio git y se creó la estructura de carpetas base.
- Comandos ejecutados: ver docs/evidencias/pytest_inicial.txt y el historial de esta sesión.
- Resultado real: entorno listo, sin pruebas aún (no existían).
- Qué generó la IA: la estructura de carpetas, el contenido de este archivo y de docs/auditoria.md,
  y el .gitignore. El usuario (César) ejecutó todos los comandos en su VM y verificó la salida real
  en cada paso.

## Etapa 1 y 2 — Entorno y logica central
- Entorno confirmado en la auditoria inicial: Ubuntu 22.04.5 LTS (jammy), Python 3.10.12, git 2.34.1, tkinter disponible tras instalar python3-tk.
- Se crearon logic/reloj.py (RelojReal, RelojSimulado) y logic/estado.py (EstadoCluster con R01-R08), sin dependencias de Tkinter.
- Decision de diseno documentada: al apagar el motor se apaga tambien el testigo 9 y el ambar del elemento 2, y se reinician sus temporizadores de histeresis, para evitar un falso encendido 1s despues de apagar el motor.
- Qué generó la IA: el contenido completo de ambos archivos. El usuario los guardó y verificó que compilan sin errores de sintaxis.

## Etapa 3 — Suite de pruebas pytest
- Fecha: 2026-10-29
- Qué se hizo: 52 casos (CP-01 a CP-52) en tests/test_particiones.py, test_limites.py,
  test_transiciones.py y test_invalidas.py, con conftest.py que inyecta RelojSimulado.
- Resultado real: 52 passed; cobertura total 97% (estado.py 95%, reloj.py 73%). Commit e1b670a.
- Qué generó la IA: todo el código de pruebas. El usuario lo ejecutó en su VM y verificó la salida.
- Incidencias: la sesión SSH se cerró antes del commit; se reconectó y se comprobó con git status
  que no se perdió nada. Se corrigió el docstring de CP-27 (decía 7800, la prueba usa 7799).

## Etapa 4 — Pruebas complementarias de caja blanca
- Qué se hizo: CP-53 a CP-63 para las líneas y ramas sin cubrir (motor_activo, color_aceite,
  testigos apagados, RelojReal, validaciones de RelojSimulado.avanzar). Se reforzaron CP-09,
  CP-31 y CP-32, que no verificaban todos los valores que prueban.
- Resultado real: 65 passed; cobertura 100% en logic/. Commit f7bcff0.
- Qué generó la IA: el análisis de las líneas sin cubrir (a partir del código que pegó el usuario)
  y las pruebas nuevas.

## Etapa 5 — Matriz de trazabilidad
- Qué se hizo: tools/trazabilidad.py genera docs/matriz_trazabilidad.md desde los docstrings y el
  resultado real de pytest (junit.xml).
- Resultado real: 63 casos, 63 PASS. Commit 27d6997.
- Incidencias: el primer bloque falló porque la IA usó "!!" dentro de comillas dobles y bash lo
  interpretó como expansión de historial. Fue un error del comando, no del proyecto; se resolvió
  con set +H.

## Etapa 6 — Trazabilidad completa y registro de defectos
- Qué se hizo: se etiquetaron con R01-R08 los casos sin requisito, se agregaron CP-64 a CP-66 y
  se registró DEF-01 (el testigo de frenos parpadeaba con el motor apagado) en
  docs/registro_defectos.md; CP-66 se marcó xfail para documentar el defecto sin romper la suite.
- Resultado real: 67 passed, 1 xfailed; ningún requisito sin casos. Commit daad491.
- Decisión: la IA propuso interpretar R01 ("encendido/apagado general") como apagado de todos los
  testigos, igual que los demás testigos del código. Debe confirmarse contra la guía original.

## Etapa 7 — Corrección de DEF-01 e informe
- Qué se hizo: se agregó la verificación del motor en testigo_falla_frenos_encendido, se quitó el
  xfail de CP-66 (queda como prueba de regresión) y tools/informe.py genera docs/informe_pruebas.md
  con datos reales de junit, coverage y el registro de defectos.
- Resultado real: 68 passed, cobertura 100% en logic/, DEF-01 cerrado. Commit 382a8d9.
- Qué generó la IA (Etapas 4-7): Claude Code generó los comandos, pruebas, scripts y documentos. El
  usuario ejecutó cada bloque en su VM y pegó la salida real, que se revisó antes de continuar.

## Etapa 8a.1 — Revisión contra la especificación y reversión de DEF-01
- Fecha: 2026-10-29
- Qué se hizo: el usuario proporcionó la especificación completa como texto. La IA comparó
  numeración, rangos, ciclos y reglas R01-R08 contra logic/estado.py; la numeración y los
  umbrales coinciden. Se identificaron seis puntos de decisión (D1-D6) y el usuario aceptó las
  recomendaciones.
- D1: DEF-01 se rechazó. La IA lo había registrado en la Etapa 6 interpretando R01 como apagado
  general; la especificación (R08) no condiciona el testigo 10 al motor. Fue un error de
  interpretación de la IA. Se revirtió el cambio de la Etapa 7 y CP-66 se reescribió con la
  expectativa correcta.
- D2: los testigos 6, 7 y 8 siguen dependiendo del motor, documentado como el estado definido de R01.
- D3: un solo interruptor motor representa Encendido y Motor activo.
- D4 y D5 se aplicarán en las Etapas 8c y 8e. D6: la portada usará la fecha de entrega de la
  especificación (18/10/2026).
- Qué generó la IA: el análisis comparativo, los cambios de código, prueba y documentación. El
  usuario tomó las decisiones y ejecutó el bloque en su VM.

## Etapa 8b — Interfaz Tkinter y main.py
- Fecha: 2026-10-29
- Qué se hizo: ui/presentacion.py (traduce el estado a lo que se dibuja de los 10 elementos, sin
  Tkinter), ui/tablero.py (5 deslizadores, 4 interruptores, selector de direccional; agujas 1-5,
  testigos 6-10, críticos 9 y 10 como rectángulos con borde rojo) y main.py. Pruebas CP-67 a CP-78
  (presentación e integración con Tkinter real bajo Xvfb).
- Decisión D7 (propuesta por la IA y aprobada por el usuario): la precedencia visual de
  R07 se implementa ocultando el testigo 6 mientras la emergencia está activa.
- Incidencias: el primer intento de pegar el bloque completo en la terminal SSH se corrompió por su
  tamaño (la terminal quedó esperando el cierre de un heredoc). Se cambió el método: la IA escribió
  los archivos en Windows, el usuario los copió a la VM con scp y ejecutó un script.
- Qué generó la IA: todo el código de la interfaz, sus pruebas y el script de la etapa. El usuario
  instaló Xvfb, copió los archivos y ejecutó el script en su VM.

## Etapa 8c — Pruebas de aceptación dirigidas por datos
- Fecha: 2026-10-29
- Qué se hizo: aceptacion/escenarios.py carga escenarios desde tests/datos/escenarios_aceptacion.csv,
  los ejecuta sobre la interfaz Tkinter real (reloj simulado, ventana nueva en estado seguro por
  escenario) y compara lo dibujado en pantalla con lo esperado. Diez escenarios CA-01 a CA-10, uno
  por elemento, que recorren los 10 controles y cruzan cada umbral en ambos sentidos. Pruebas de
  manejo del archivo (CP-79 a CP-85, CP-87 a CP-90: inexistente, vacío, columnas faltantes, filas
  inválidas) y CP-86 para el hueco de cobertura de detener(). Decisión D4 aplicada.
- Evidencia: docs/evidencias/aceptacion.txt con la salida real paso a paso.
- Qué generó la IA: el cargador y ejecutor, el CSV de escenarios con sus valores esperados
  (calculados a partir de las reglas R01-R08 y de los ciclos), y las pruebas. El usuario copió los
  archivos a la VM y ejecutó el script; los resultados son los de esa ejecución.

## Etapa 8d — Capturas de pantalla como evidencia
- Fecha: 2026-10-29
- Qué se hizo: tools/capturas.py abre la interfaz real sobre Xvfb (pantalla virtual de 1280x1024,
  24 bits), la lleva a 8 estados representativos con el reloj simulado y fotografía la ventana con
  Pillow. Cada imagen se valida (no vacía) y se registra en docs/evidencias/capturas.txt junto con
  los casos y requisitos que ilustra y el estado de los 10 elementos en ese instante.
- Qué generó la IA: el script y la selección de estados. Las imágenes son las que produjo la
  ejecución en la VM del usuario, sin edición posterior.

## Etapa 8e — Ajuste visual e informe Word/PDF
- Fecha: 2026-10-29
- Ajuste visual: al revisar las capturas de la 8d se vio que la aguja tapaba la cifra en el mínimo y
  que los interruptores tenían un recuadro de foco que parecía tachar el texto. Se corrigió en
  ui/tablero.py, se repitió la regresión completa y se regeneraron las capturas.
- Informe: informe/generar_informe.py produce Informe_Pruebas_Cluster_F40.docx y .pdf con la
  estructura de 14 secciones de la especificación y 25 casos consolidados (CT-01 a CT-25). Los
  resultados, conteos, versiones y porcentajes se leen de docs/evidencias/; el estado de cada CT se
  calcula de junit.xml y aceptacion.txt. Las referencias en línea se verificaron el 29/10/2026; las
  de iso.org quedaron como pendientes de verificar porque el sitio rechazó la consulta automática.
- Qué generó la IA: el ajuste visual, el generador del informe y su texto. Antes de entregarlo se
  probó el generador en Windows con evidencias de prueba (no reales) para revisar el formato. El
  usuario ejecutó la etapa en su VM; el documento final usa solo las evidencias reales de esa
  ejecución.

## Etapa 8e.1 — Corrección visual detectada en el informe
- Fecha: 2026-10-29
- Qué se hizo: al revisar el PDF generado se vio que en las capturas el texto "7 Luces altas" salía
  casi negro: en Xvfb el puntero queda sobre ese interruptor y Tkinter usaba el color de texto
  activo por defecto. Se fijó activeforeground en interruptores y selector, se repitió la regresión
  completa, se regeneraron capturas y evidencias, y se volvió a generar el informe Word/PDF.
- Qué generó la IA: el diagnóstico (a partir del PDF) y el parche. El usuario ejecutó la etapa en su VM.

## Etapa 8e.2 — Normas ISO y declaración de colaboración
- Fecha: 2026-10-29
- Qué se hizo: se verificaron las fichas oficiales de ISO/IEC/IEEE 29119-1:2022, 29119-2:2021,
  29119-3:2021, 29119-4:2021 e ISO 26262-6:2018 mediante búsqueda web (iso.org rechazaba la descarga
  directa), se quitaron las marcas de "pendiente de verificar", se agregó al informe una tabla de
  marco normativo (cómo se aplicó cada norma, sin declarar conformidad) y una declaración breve de la
  colaboración de Claude Code. Se regeneró el informe Word/PDF con las mismas evidencias.
- Qué generó la IA: la verificación de referencias y los cambios al generador. El usuario ejecutó
  la etapa en su VM.

## Etapa 9 — Interfaz 8-bit y apertura en Windows, Linux y macOS
- Fecha: 2026-11-09
- Qué se hizo: se rediseñó ui/tablero.py con estética 8-bit inspirada en la distribución del tablero
  del F40 (velocímetro y tacómetro grandes al centro, medidores chicos a los lados, testigos críticos
  9 y 10 arriba entre las esferas, testigos 6, 7 y 8 dentro de las esferas), con agujas, esferas y
  escalas hechas de bloques de pixeles. Se cambió la paleta en ui/presentacion.py. Se agregaron
  abrir_cluster.bat (Windows), abrir_cluster.sh (Linux/macOS) y README.md con instrucciones.
- Pruebas: no se modificó ninguna prueba. La interfaz conserva lo que las pruebas observan (color de
  aguja y de testigo, texto de cada lectura, círculos para 6-8 y rectángulos para 9-10, controles y
  mensajes). Antes de llevarlo a la VM se corrió la suite completa en Windows: 107 aprobadas y sin
  fallos atribuibles al código; los fallos intermitentes observados se debieron al Python de Microsoft
  Store, que a veces no puede leer su propio init.tcl. La ejecución oficial es la de la VM.
- Qué generó la IA: el rediseño, los lanzadores, el README y la actualización del informe. El usuario
  pidió el cambio, encendió la VM y autorizó la llave SSH con la que la IA ejecutó la etapa.

## Etapa 9.1 — Ajuste visual de la cifra digital
- Fecha: 2026-11-09
- Qué se hizo: al revisar las capturas de la Etapa 9 se vio que, con la aguja en cero, esta cruzaba la
  cifra digital del velocímetro y del tacómetro. Se agregó una ventana tipo LCD detrás de la cifra, por
  encima de la aguja. No se modificó ninguna prueba; se repitió la regresión completa.
- Qué generó la IA: el diagnóstico (a partir de la captura) y el ajuste. La IA ejecutó la etapa en la VM
  por SSH con la llave autorizada por el usuario.

## Etapa 10 — Material de estudio y comparación con la guía oficial
- Fecha: 2026-11-09
- Qué se hizo: el usuario compartió la guía oficial del proyecto final. Se agregó la carpeta estudio/ con
  la guía en PDF, cómo abrir el proyecto en la VM, una guía de estudio para la demostración y una
  comparación punto por punto con la guía. La comparación muestra pendientes: datos desde archivos
  externos, configuración, bitácoras eventos.log/errores.log, comunicación y sincronización, permisos,
  pruebas P08, P11 y P12 e informe técnico con las secciones 4.1–4.7.
- Qué generó la IA: los documentos de estudio. Los pendientes quedan a decisión del equipo.

## Etapa 11 — Proyecto completo según la guía oficial
- Fecha: 2026-11-10
- Qué se hizo: se construyó lo que pedía la guía del proyecto final y faltaba:
  - entrada por archivo externo (datos/vehiculo.conf, clave=valor) con un hilo lector que valida cada
    clave y conserva el último valor válido;
  - configuración externa (config/cluster.ini) con rutas relativas, intervalos, rangos y rotación;
  - bitácoras logs/eventos.log (INFO, WARN) y logs/errores.log (ERROR) con fecha, nivel, componente,
    evento y resultado, rotación por tamaño y permisos 640/750;
  - comunicación productor-consumidor (archivo con escritura atómica → hilo lector →
    queue.Queue(maxsize=1) → interfaz) y monitor de eventos de seguridad;
  - iniciar.sh, tools/escribir_dato.py, tools/simulador.py (proceso productor),
    tools/ejecucion_prolongada.py (P12 con métricas) y tools/demo_bitacoras.py;
  - pruebas P01–P12 y de sistema (CP-91 a CP-119) sin modificar ninguna prueba anterior;
  - diagramas, informe técnico con las 10 secciones de la guía y material de estudio actualizado.
- Hallazgo: en Windows, abrir el archivo justo cuando otro proceso lo reemplaza da un PermissionError
  momentáneo; la prueba P08 lo detectó y el lector ahora reintenta antes de registrarlo.
- Qué generó la IA: todo el código, las pruebas y los documentos de esta etapa. Se probó primero en
  Windows y la ejecución oficial fue en la VM por SSH; luego se subió a GitHub.

## Etapa 12 — Documento completo de pruebas (Tarea 2)
- Fecha: 2026-11-16
- Qué se hizo: informe/generar_documento_pruebas.py genera Documento_Completo_de_Pruebas_F40 (PDF y
  DOCX) con la estructura obligatoria de la Tarea 2: control documental e historial, requisitos REQ por
  elemento, estrategia, ambiente, riesgos con probabilidad, criterios de entrada, salida, suspensión y
  reanudación, 25 casos con la distribución por categoría, trazabilidad, defectos (DEF-01 rechazado y
  DEF-02 cerrado), métricas de la tarea y anexos (evidencias, historial git, actividades previas, uso de
  IA y defensa). El estado de cada caso sale de junit.xml y metricas.txt.
- Pendiente (no inventado): los tres casos de la práctica en clase, la revisión cruzada, el escenario
  sorpresa y las observaciones del profesor todavía no ocurren; quedan con su formato listo en el anexo C.
- Qué generó la IA: el generador y el contenido del documento. El equipo confirmó qué actividades
  previas existen (solo la Tarea 1).

## Etapa 13 — Odómetro (elemento 11) tras la práctica en clase
- Fecha: 2026-11-18
- Origen: en la práctica "Diseño y ejecución supervisada de pruebas" el profesor asignó el odómetro y
  permitió el uso de IA. Los tres casos diseñados (CP-ODO-01 a 03) se ejecutaron sobre 749d580: dos
  fallidos y uno bloqueado, porque el odómetro no existía (DEF-03).
- Qué se hizo: logic/odometro.py (distancia = velocidad mostrada × tiempo, 6 dígitos, vuelta a 000000,
  nunca disminuye); sistema/odometro_archivo.py (datos/odometro.txt con respaldo .bak, escritura atómica,
  rechazo de archivos inválidos o escribibles por cualquiera); dibujo y aviso en ui/tablero.py; carga,
  guardado cada 5 s y al cerrar en main.py; INFO odometro_actualizado por km en sistema/monitor.py;
  odometro= en datos/vehiculo.conf se rechaza (clave_no_permitida); [odometro] guardar_cada_s en
  config/cluster.ini. Pruebas nuevas CP-120 a CP-137 en tests/test_odometro.py.
- Pruebas anteriores: sin cambios (huella sha256 comprobada por run_13.sh antes del commit).
- Práctica: practica/ejecutar_casos.py ejecuta los casos con la aplicación completa antes (worktree de
  749d580) y después; los resultados reales quedan en practica/evidencia_antes/ y evidencia_despues/.
- Corrección del propio caso: 30 s y 10 s daban exactamente 1 km (borde del cambio de dígito); se
  corrigieron a 45 s y 15 s (1.5 km). Esa duración original la propuso la IA.
- Documentos: Documento completo de pruebas v2.1 (REQ-ODO-01, CT-26 a CT-28, sección 10.1, DEF-03),
  ficha 11 en el informe técnico, elemento 11 en el informe de pruebas, README y guía de estudio.
- Pendiente (no inventado): revisión cruzada, escenario sorpresa y observaciones del profesor.
- Qué generó la IA: la implementación, las pruebas, los scripts de la práctica y los documentos. El
  equipo aportó el elemento asignado por el profesor y la decisión de implementarlo.

## Etapa 14 — Auditoría de robustez (DEF-04 a DEF-14)
- Fecha: 2026-11-23
- Origen: una auditoría externa (ChatGPT Codex, commit 5e9506b) reportó fallos con datos decimales,
  avisos, refresco, odómetro, P12, configuración, concurrencia, aceptación e informes. Se reprodujeron
  uno por uno con pruebas nuevas (CP-138 a CP-149) que fallaron en 5e9506b
  (docs/evidencias/robustez_antes.txt); 12 de 12 confirmados.
- Ataque propio: fuzzing (tools/qa/fuzzing.py) encontró dos defectos más: NaN aceptado por el modelo
  (DEF-13) y dígitos no ASCII aceptados (DEF-14); CP-150 y CP-151.
- Correcciones: valor validado directo al modelo, aviso de rechazos en pantalla, refresco que se
  reprograma aunque un ciclo falle y limitado a 100 ms, integración del odómetro por tramos, candado de
  instancia única, configparser sin interpolación y bitácoras de respaldo, firma del lector con inodo,
  candado de escritura en escribir_dato.py, P12 que valida el productor y mide la latencia archivo ->
  tablero, informes que no cuentan omitidas como aprobadas, CSV con rango y elemento 11, odómetro sobre
  la aguja, rechazo de NaN y de dígitos no ASCII.
- Prueba de caos (tools/qa/caos.py): 40 s de aplicación real con el archivo corrompido, borrado, con
  permisos cambiados y una segunda instancia en otro proceso.
- Pruebas anteriores: sin cambios (huella sha256). CP-84 se conserva: el mensaje de elemento inválido
  sigue diciendo "elemento fuera de 1-10" (el 11 solo admite valor=NNNNNN).
- Qué generó la IA: pruebas, correcciones y scripts de ataque. El equipo pidió la auditoría.

## Etapa 15 — Contenido completo de la materia
- Fecha: 2026-11-23
- Qué se hizo: se revisó cada tema del programa (unidades 1 a 6) contra el proyecto
  (estudio/05_mapa_de_la_materia.md). Se añadió lo que aportaba evidencia real con poco costo:
  tools/evidencia_so.sh (strace, inodo, hexdump, procesos e hilos, /proc, señales, flock y permisos),
  tools/diagnostico.sh (analizador de bitácoras en Bash, tema 2.3) y el manejo de SIGTERM y SIGINT.
- Defecto: DEF-15, kill PID terminaba el clúster sin cierre ordenado (código -15, sin "sistema fin",
  kilometraje perdido; docs/evidencias/senales_antes.txt). CP-152 lo cubre.
- No se añadió (y por qué): simuladores de First/Best Fit, SCAN o asignación de bloques (no se
  relacionan con el clúster); bomba fork y desbordamiento de pila (destructivos); prioridades de
  tiempo real con nice/SCHED_FIFO (requieren root, contra el privilegio mínimo).
- Pruebas anteriores: sin cambios (huella sha256).

## Etapa 16 — Panel de control (administrador)
- Fecha: 2026-11-24
- Qué se hizo: panel_admin.py y panel/ (fisica.py, comandos.py, ventana.py). Es un proceso aparte que
  escribe datos/vehiculo.conf con el candado y la escritura atómica de escribir_dato.py; el tablero
  no cambia. Cabina austera inspirada en el F40 (piso de fibra, pedales de aluminio perforado,
  compuerta de cambios, llave de contacto), física simplificada con cifras aproximadas no oficiales,
  luces, fallas de sensores (R02, R04, R05, R08), entradas inválidas con restauración, atajos de
  comandos con consola, y los escenarios CA-01 a CA-10 reproducidos en vivo desde el mismo CSV.
- Pruebas nuevas: CP-155 a CP-162 (tests/test_panel.py). CP-159 recorre 20 000 pasos al azar y
  comprueba que el panel nunca produce un dato que el lector rechace.
- Pruebas anteriores: sin cambios (huella sha256).
- Qué generó la IA: el panel, sus pruebas y la documentación; el diseño lo pidió el equipo.

## Etapa 17 — Rediseño del cuadro inspirado en el F40
- Fecha: 2026-11-24
- Qué se hizo: ui/tablero.py dibuja ahora un cuadro inspirado en el del F40 en lugar de la estética
  8-bit: capota negra mate curva (más alta sobre el tacómetro) sobre un tablero de fieltro gris,
  esferas negras con numerales en blanco cálido de época, escalas con marcas mayores y menores,
  zonas pintadas (roja 8000-9000 RPM y >110 °C, ámbar >1.5 bar de turbo y <1 bar de aceite), agujas
  cónicas con contrapeso y tapa central, odómetro de tambor de 6 dígitos en el velocímetro y una
  barra de testigos con sus símbolos (flechas, faro, triángulo, aceitera, freno). Sin logotipos.
- Contrato que se conserva (pruebas sin cambios): items[1-5] aguja/valor/bloques, items[6-10] forma
  (óvalos 6-8, rectángulos 9-10), items[11] un solo texto de 6 dígitos, controles y métodos públicos.
- Medición (tools de la etapa, VM con Xvfb): construir la ventana 143 ms (antes 222 ms) y menos de
  300 figuras (antes 1206); ciclo con dibujo 21 ms (antes 19 ms).
- Se descartó el reflejo del cristal con trama (stipple): en pantalla se veía como puntos.

## Etapa 18 — Realismo, seguridad y banco de liberación de producción
- Fecha: 2026-11-25
- Pedido del equipo: puertas con testigo que impidan avanzar, fallas con consecuencias reales (frenos que no
  frenan bien, sobrecalentamiento o turbo que detienen el motor, fuga de aceite que impide arrancar), pruebas
  reales de la época para liberar el auto a producción y una nueva revisión de la guía y la rúbrica.
- Cuadro: claves opcionales contacto, puertas (bits de estado), cinturon, combustible y falla_motor (D8: un
  archivo de diez claves funciona igual); llave que separa Encendido de Motor activo (D3); prueba de testigos de
  2 s (R13-H 5.2.21.4); elementos adicionales 12-15 con las reglas agregadas R09-R12; consistencia motor/contacto
  en el validador (D9); franja inferior en el tablero y encabezado con el vehículo.
- Panel: ECU simulada (panel/ecu.py) que no deja arrancar con fuga de aceite o sin combustible y detiene el motor
  por sobretemperatura, sobrepresión o falta de presión de aceite; interbloqueo de puertas; frenos al 30 % con
  falla y pérdida de eficiencia en caliente; consumo con el tanque de 120 L; TALLER; llave y arranque separados.
- Banco de liberación (panel/liberacion.py, tools/banco_liberacion.py): 9 pruebas, entre ellas frenado tipo 0 y
  tipo I de UN R13-H, velocímetro de UN R39 y el ciclo urbano ECE-15 con el odómetro del cuadro. Con --evidencia
  comprueba que la unidad sana sale APTA y cada falla RECHAZADA. Encontró DEF-16 (el sensor de velocidad podía
  indicar menos que la real), corregido.
- Fuentes: los criterios de R13-H y R39 se leyeron en el texto de las ADR 31/01 y 18/03; lo que no se pudo
  verificar (Directiva 71/320/CEE de 1987, versiones de 1987 de R39 y FMVSS 208, cifras reales del F40) quedó
  marcado como pendiente en docs/realismo_y_liberacion.md.
- Pruebas nuevas: CP-163 a CP-183 (tests/test_realismo.py y tests/test_liberacion.py). Pruebas anteriores: sin
  cambios (huella sha256). Un error de una prueba nueva (leía la temperatura un paso después del corte) se
  corrigió en la prueba antes de la corrida oficial.
- Qué generó la IA: el código, las pruebas y la documentación de la etapa; el alcance lo pidió el equipo.

## Etapa 19 — Sonido del motor sintetizado por código
- Fecha: 2026-11-26
- Pedido del equipo: el sonido del motor junto con la acción. Se propuso cortar audio de videos de
  YouTube; se descartó (YouTube no permite descargar sus videos y la guía pide procedencia y licencia
  de los recursos de terceros) y el equipo eligió generarlo por código.
- Qué se hizo: panel/sonido.py (modelo de pulsos de combustión de un V8, 4 explosiones por vuelta,
  tres resonadores, ruido de admisión y viento, turbo con silbido y descarga, limitador, petardeos,
  motor de arranque y alarma del cinturón de 4 a 8 s según FMVSS 208 S7.3); salidas waveOut
  (Windows, ctypes), aplay (Linux, tubería) y WAV; hilo de tiempo real con adelanto máximo de 120 ms;
  tools/bocina.py, que recibe el estado del panel por un socket a través de un túnel SSH y valida cada
  mensaje; tools/sonido_demo.py, que deja un WAV de 22 s y las mediciones del audio en docs/evidencias/sonido.
- La VM tiene tarjeta de sonido (AC97) pero le falta alsa-utils y el usuario no está en el grupo audio
  (requiere sudo con contraseña): por eso la ruta principal es la bocina en Windows.
- Pruebas nuevas: CP-184 a CP-190 (tests/test_sonido.py); miden el audio (ritmo de 15 ms en ralentí,
  frecuencia de encendido, cortes del limitador, silbido del turbo, duración de la alarma). Pruebas
  anteriores: sin cambios (huella sha256).
- Qué generó la IA: el sintetizador, la bocina, las pruebas y la documentación; el sonido es aproximado
  y no se calibró contra un F40.

## Etapa 20 — Caja negra, sistema eléctrico, Weber-Marelli y sonidos de cabina
- Fecha: 2026-11-26
- Pedido del equipo: investigar qué más agregar para dar realismo y presentar un plan; el equipo aprobó
  lo recomendado (cuatro puntos).
- Investigación: se verificó en varias fuentes que el F40 usa dos turbos IHI a 1.1 bar, gestión
  Weber-Marelli IAW con encendido e inyección separados por banco y 577 Nm a 4000 rpm; quedaron
  pendientes las relaciones de marcha (una fuente), el peso (fuentes de 1100 a 1235 kg), las rpm del
  limitador y la lista exacta de testigos (el manual técnico no se pudo consultar).
- Caja negra (sistema/caja_negra.py, tools/caja_negra.py): anillo binario de 600 registros de 32 bytes
  con cabecera de 64, acceso directo con pread/pwrite, CRC-16, hilo escritor con fsync cada segundo,
  eventos CSV de los 10 s previos a un testigo crítico y recuperación de una cabecera dañada.
- Sistema eléctrico: clave opcional voltaje, elemento 16 y regla R13; batería, alternador y cargas en
  el panel (descarga acelerada 60 veces, D14); la ECU no arranca con la batería débil y se apaga bajo
  10.5 V (causa eléctrica).
- Weber-Marelli: falla de una unidad por banco (medio empuje, un turbo, ralentí irregular, sonido cojo),
  sin testigo como en 1987 (D15); el banco la rechaza en L01, que ahora también revisa el voltaje de carga.
- Sonidos de cabina: relevador de las direccionales, chirrido de llantas, ventilador del radiador y
  motor de arranque lento.
- Correcciones durante el desarrollo: muestras y eventos perdidos cuando la prueba no dejaba correr al
  hilo escritor (los eventos ahora van en una lista que no se descarta), tolerancia de 1 µs al programar
  la siguiente muestra, y una falsa falla de carga al arrancar (solo cuenta con 800 rpm o más).
- Pruebas nuevas: CP-191 a CP-202 (tests/test_caja_negra.py y tests/test_electrico.py). Pruebas
  anteriores: sin cambios (huella sha256).

## Etapa 21 — Prácticas de fallas automáticas, curva de par, adherencia sin ABS, aceite e inercia
- Fecha: 2026-11-26
- Pedido del equipo: hacer también lo opcional del plan y agregar opciones para simular las fallas sin
  provocarlas a mano, con la palanca y los pedales correspondiendo a lo que pasa, probadas todas y
  puestas como botones.
- Prácticas (panel/practicas.py, tools/practicas.py): 15 casos como corrutinas que el ciclo del panel
  avanza cada 50 ms; el robot mueve los pedales con la rapidez del panel y pisa el embrague en cada
  cambio; verifican con una copia en memoria del cuadro real. Botones en el panel y evidencia en
  docs/evidencias/practicas.txt.
- Física: curva de par por los datos verificados (577 Nm a 4000 rpm; 478 CV a 7000 rpm) con el turbo;
  empuje y resistencia del aire calibrados con el 0-100 (4.1 s citado; rango 3.5-5.0 s) y la máxima
  (324 km/h); adherencia con patinamiento y bloqueo, porque el F40 no tenía ABS ni control de tracción
  (verificado en la revista de Ferrari); pista mojada al 55 %.
- Elemento 17 (temperatura de aceite) con la regla R14; agujas del tablero con inercia.
- Correcciones durante el desarrollo: dos prácticas verificaban la causa en el mismo instante del corte,
  antes de la siguiente lectura del cuadro; se agregó una espera de 0.3 s. La comparación del
  velocímetro ahora usa la velocidad del momento de la lectura.
- Pruebas nuevas: CP-203 a CP-209 (tests/test_practicas.py; CP-203 corre las 15 prácticas). Pruebas
  anteriores: sin cambios (huella sha256).

## Etapa 22 — Verificación de lo pendiente: normas de la época y datos del fabricante
- Fecha: 2026-11-26
- Pedido del equipo: verificar todo lo que estaba marcado como pendiente de verificar.
- Verificado en el texto (docs/realismo_y_liberacion.md, sección 5): Directiva 71/320/CEE consolidada al
  3-1-1986, la vigente en 1987 (M1: 80 km/h, s <= 0.1 v + v²/150, dm >= 5.8 m/s², <= 500 N); Directiva
  75/443/CEE del velocímetro (nunca indica menos; V1 - V2 <= V2/10 + 4 km/h); UN R84 (± 1 km/h y ± 0.5 s en
  el ciclo urbano; 90 y 120 km/h a ± 2 km/h); FMVSS 208 S7.3 en el CFR de 1996; datos del fabricante en
  ADAC (1250 kg, 120 L, consumo 18.4 / 8.6 / 10.3 L/100 km, llantas); 1100 kg en seco (evo); línea roja
  7750 rpm (Hagerty, supercars.net); relaciones de la caja (dos fuentes secundarias); 60-0 mph en 119 ft
  (duPont Registry). Varias páginas respondieron 403 (NHTSA, FastestLaps, cars-data): no se usan como fuente.
- Banco: L03 exige también el criterio de 1987 y L06 la tolerancia de UN R84 (antes ± 2 km/h del equipo).
- Modelo: velocidades por marcha con las relaciones verificadas; frenado a fondo calibrado con la frenada
  publicada (34.6 km/h por segundo); consumo por potencia calibrado con el consumo del fabricante
  (tools/consumo.py, docs/evidencias/consumo.txt); masa justificada con el peso en orden de marcha.
- Ajustes del robot (no de las pruebas): el manejo normal cambia a 4000 rpm (la 2a más larga ya no llegaba a
  la 3a antes de 80 km/h) y en mojado dosifica al 70 %. DEF-17: el embrague quedaba a fondo solo dos
  ciclos y CP-205 podía no verlo; ahora la palanca se mueve con el embrague a fondo.
- Discrepancia que no se cambió: R03 pone el rojo en 8000 rpm y la línea roja real es 7750 rpm; queda para
  decidir con el profesor.
- Pruebas nuevas: CP-210 a CP-214 (tests/test_verificacion.py). Pruebas anteriores: sin cambios (huella
  sha256).
- 27-nov-2026, decisión del equipo: R03 se conserva en 8000 rpm (la especificación) aunque la línea roja real del
  F40 es 7750 rpm. Lo que sigue sin verificar (FMVSS 208 de 1987, la figura de tolerancias de R84, el origen de la
  frenada y de las relaciones, el limitador real) no cambia ningún criterio ni resultado y queda marcado como pendiente.
