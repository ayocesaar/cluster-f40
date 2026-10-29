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
