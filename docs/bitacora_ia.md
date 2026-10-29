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
