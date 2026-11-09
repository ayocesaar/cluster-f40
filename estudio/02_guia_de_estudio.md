# Guía de estudio para la demostración

Cómo usar esta guía: para cada pregunta hay una **respuesta corta** (lo que se dice), **dónde está** en el código
(para poder enseñarlo) y **cómo demostrarlo** en vivo. Las marcas ⚠️ señalan preguntas cuya respuesta completa
depende de algo que todavía falta construir (ver `03_cumplimiento_de_la_guia.md`); ahí conviene decir qué hay
hoy y cuál es el plan, nunca inventar.

---

## 1. El proyecto en dos minutos

- **Qué es:** un simulador del clúster de instrumentos del **Ferrari F40 (1987)** con 10 elementos. No usa ECU ni
  sensores reales; los rangos son didácticos.
- **Cómo está armado** (de abajo hacia arriba):

| Capa | Archivo | Qué hace |
|---|---|---|
| Reloj | `logic/reloj.py` | Da el tiempo: `RelojReal` (usa `time.monotonic`) o `RelojSimulado` (lo avanzan las pruebas). |
| Modelo y reglas | `logic/estado.py` | `EstadoCluster`: valida entradas, guarda el último estado válido y aplica R01–R08. No sabe nada de la interfaz. |
| Presentación | `ui/presentacion.py` | `vista(estado)`: traduce el estado a lo que se dibuja (valor, posición de aguja, color, testigo encendido). |
| Interfaz | `ui/tablero.py` | Ventana Tkinter 8-bit: dibuja y manda los valores de los controles al estado. |
| Arranque | `main.py`, `abrir_cluster.sh/.bat` | Crea el reloj real, el estado y la ventana. |
| Aceptación | `aceptacion/escenarios.py` + `tests/datos/escenarios_aceptacion.csv` | Lee escenarios de un archivo y los ejecuta sobre la ventana real. |
| Pruebas | `tests/` | 108 ejecuciones (100 casos CP/CA), 100% de cobertura de la lógica. |

- **Flujo de un valor:** control (deslizador) → `Tablero.enviar` → `EstadoCluster.set_*` (valida) → `tick()` lo
  aplica cuando se cumple su ciclo → `vista()` decide color y ángulo → `refrescar()` lo dibuja.

## 2. Los diez elementos

| N.º | Elemento | Tipo | Rango | Ciclo | Regla |
|---|---|---|---|---|---|
| 1 | Velocímetro | decimal (`float`) | 0–360 km/h | 100 ms | R01: a 0 al apagar |
| 2 | Presión de aceite | decimal | 0–10 bar | 100 ms | ámbar inmediato bajo 1 bar con motor activo |
| 3 | Tacómetro | entero (`int`) | 0–9000 rpm | 100 ms | R03: rojo ≥ 8000, normal < 7800 |
| 4 | Temperatura de agua | decimal | 40–130 °C | 500 ms | R04: rojo > 110, normal ≤ 105 |
| 5 | Presión de turbo | decimal | 0–2 bar | 100 ms | R05: contorno ámbar > 1.5, normal ≤ 1.4 |
| 6 | Direccionales | enumeración (`OFF`/`IZQ`/`DER`) | — | 500 ms | R06: verde alternando |
| 7 | Luces altas | booleano | — | — | R07: azul fijo |
| 8 | Emergencia | booleano | — | 500 ms | R07: ámbar alternando, tapa al 6 |
| 9 | Baja presión de aceite | booleano (calculado) | — | — | R02: rojo tras 1 s bajo 1 bar; se apaga tras 1 s en ≥ 1.2 bar |
| 10 | Falla de frenos | booleano | — | 300 ms | R08: rojo alternando, aun con motor apagado |

## 3. Las preguntas de la guía (sección 9)

### 3.1 ¿Por qué eligió ese tipo de dato para cada elemento?

**Respuesta corta.** Cada tipo es el mínimo que representa el dato sin ambigüedad:
- Velocidad, presiones y temperatura son **decimales** porque la especificación usa fracciones (120.5 km/h,
  0.99 bar, 110.1 °C) y los umbrales caen en decimales. En Python un `float` es un IEEE-754 de 64 bits: precisión
  de sobra para una décima o centésima.
- Las **RPM son enteras**: no existen 4500.5 rpm. Por eso `set_rpm(5000.0)` se **rechaza** con `TypeError` en vez
  de convertirse en silencio. Así evitamos una conversión ambigua.
- Los interruptores son **booleanos**, y aquí hay un detalle de codificación: en Python `bool` es subclase de
  `int` (`True == 1`). Por eso la validación revisa primero `isinstance(valor, bool)`: así `set_motor(1)` se
  rechaza y `set_rpm(True)` también.
- El direccional es una **enumeración** de tres textos (`OFF`, `IZQ`, `DER`); cualquier otro se rechaza.

**Dónde está.** `logic/estado.py`: `_validar_numero` (rangos, tipo `int` para RPM, rechazo de `bool`),
`_validar_bool`, `set_direccional` y `DIRECCIONALES_VALIDAS`.

**Cómo demostrarlo.** `xvfb-run -a python -m pytest -v -k "cp40 or cp41 or cp48 or cp50 or cp51"`

### 3.2 ¿Qué ocurre si el archivo cambia mientras está siendo leído? ⚠️

**Qué hay hoy.** El tablero recibe los valores desde los controles de la ventana, no de un archivo que se lea
continuamente. El único archivo de entrada es el CSV de escenarios de aceptación: se abre, se lee completo y se
valida línea por línea antes de ejecutar nada (`aceptacion/escenarios.py`, función `cargar`). Si una línea está
corrupta, se rechaza el archivo completo con un error que dice la línea; nunca se ejecuta un escenario a medias.

**Qué falta.** La guía espera un archivo de datos que otro proceso modifica mientras el tablero lo lee. La solución
planeada es que el escritor guarde en un **archivo temporal y luego lo renombre** (`os.replace`). El renombrado es
**atómico** dentro del mismo sistema de archivos, así que el lector ve el archivo viejo completo o el nuevo
completo, nunca uno a medias.

### 3.3 ¿Cuál tarea tiene mayor prioridad y por qué?

**Respuesta corta.** La evaluación de los **testigos de seguridad** (9 y 10), que ocurre en cada `tick()`, antes de
dibujar. Si el bucle se retrasa, la pantalla se actualiza tarde, pero las reglas no se equivocan:
- El retardo de 1 s del testigo 9 se mide con **marcas de tiempo** (`ahora - inicio`), no contando ciclos.
- Los parpadeos se calculan con el **reloj absoluto** (`int(ahora // periodo) % 2`), así que no se desfasan.

**Dónde está.** `logic/estado.py`: `tick`, `_actualizar_histeresis_aceite`, `_parpadeo`. `ui/tablero.py`:
`_programar` (cada 50 ms llama a `ciclo`, que hace `tick` y luego `refrescar`).

**Por qué 50 ms.** Es la mitad del ciclo más rápido (100 ms), así que ningún cambio se pierde, y está lejos de
saturar el procesador. El bucle usa `after()` de Tkinter, no `while True` con `sleep`: no hay espera activa.

### 3.4 ¿Qué información permanece en memoria y cuál se almacena? ⚠️

**En memoria.** Un solo objeto `EstadoCluster` con tamaño fijo:
- Los **objetivos** recibidos (`_obj_velocidad`, ...).
- Las **lecturas** ya aplicadas (`velocidad`, `rpm`, ...).
- Los **colores** de cada indicador.
- Las **marcas de tiempo** de cada ciclo y de la histéresis del aceite.

No hay historial, así que no crece. La ventana crea sus figuras de pixeles (varios cientos) una sola vez y después solo las
mueve o recolorea (`coords`, `itemconfigure`). Además guarda el último valor dibujado (`ultimo`) para no repetir
trabajo.

**Almacenado.** Hoy solo las evidencias de las pruebas (`docs/evidencias/`). Falta definir la persistencia que pide
la guía: configuración, datos, eventos y errores.

### 3.5 ¿Cómo evita que las bitácoras crezcan indefinidamente? ⚠️

**Qué hay hoy.** Todavía no hay bitácoras en tiempo de ejecución.

**Plan.** Usar `logging.handlers.RotatingFileHandler` con un tamaño máximo y un número fijo de respaldos (por
ejemplo 1 MB × 3 archivos). Al llenarse, el archivo se renombra y se empieza otro, así que el espacio total queda
acotado. Se demostraría con la prueba P12, midiendo `du -h logs/*.log` antes y después.

### 3.6 ¿Qué amenaza considera más probable y qué control la reduce?

**La más probable: entradas inválidas o malintencionadas.** Pueden ser valores fuera de rango, texto donde va un
número, o `True` usado como número.
- **Preventivo:** validación de tipo y rango antes de aceptar cualquier valor.
- **Detección:** el rechazo produce `TypeError` o `ValueError` y un aviso en pantalla.
- **Recuperación:** se conserva el último valor válido.
- **Pruebas que lo demuestran:** CP-38 a CP-52 y CP-77.

**Otras dos amenazas:**
- **Archivo de escenarios corrupto o manipulado.** El cargador valida cada columna y cada línea, y rechaza con el
  número de línea (CP-79 a CP-84).
- **Inyección de comandos.** El programa nunca arma comandos de sistema con datos de entrada.

**Ya cumplido:** no hay contraseñas ni tokens en el código.
**Pendiente:** permisos de archivos (P11).

### 3.7 ¿Qué alternativa técnica evaluó y por qué la descartó?

Tres buenas respuestas:
- **Hilos contra `after()` de Tkinter.** Tkinter no es seguro para hilos: tocar la ventana desde otro hilo puede
  corromperla. Se eligió un solo hilo con `after()`, que además evita esperas activas.
- **`time.sleep` en las pruebas contra un reloj inyectable.** Con `sleep`, las pruebas de parpadeo e histéresis
  serían lentas y frágiles. Con `RelojSimulado` las 108 pruebas corren en segundos y siempre dan lo mismo.
- **Escenarios en el código contra un archivo CSV.** El CSV se puede editar sin tocar el código y permitió probar
  el manejo de archivos (inexistente, vacío, con errores).

### 3.8 ¿Cómo demostraría que el sistema se recupera de un error?

**Respuesta corta.** Se manda un valor inválido, se ve que se rechaza sin detener nada y que se conserva el último
valor válido; luego se manda uno válido y todo sigue normal, sin reiniciar.

**Cómo demostrarlo:**
1. Prueba CP-77: `xvfb-run -a python -m pytest -v -k cp77`. Manda 9001 RPM, aparece "Entrada rechazada", el estado
   no cambia; luego manda 100 RPM y el aviso desaparece.
2. Con el archivo de escenarios:
   - Copia el CSV y cambia un valor por `mucho`.
   - Ejecuta `python -m aceptacion.escenarios copia.csv`: sale `ERROR: linea N: el valor 'mucho' de rpm no es
     numerico` con código 2.
   - Corrige el valor y repite: pasa.

## 4. Otras preguntas probables (por la rúbrica)

- **¿Qué es la histéresis y por qué se usa?** Son dos umbrales distintos para encender y apagar una advertencia
  (rojo en 8000, normal hasta bajar de 7800). Evita que el indicador parpadee si el valor oscila justo en el
  límite. Se prueba con CP-14, CP-15 y CP-27.
- **¿Por qué el testigo 9 es distinto del medidor 2?** El medidor se pone ámbar al instante bajo 1 bar. El testigo
  9 espera 1 s continuo (no es una falsa alarma por un pico) y se apaga solo tras 1 s en 1.2 bar o más. Se prueba
  con CP-70 y CA-09.
- **¿Por qué el testigo 10 parpadea con el motor apagado?** R08 no lo condiciona al motor y es una alerta crítica
  (decisión D1). Al principio se registró como defecto (DEF-01) y se rechazó al revisar la especificación: está
  en `docs/registro_defectos.md`.
- **¿Qué pasa al apagar el motor?** R01: velocidad y RPM a 0; aceite y turbo a 0; temperatura a 40; colores en
  normal; testigo 9 apagado y temporizadores reiniciados. Sin ese reinicio, el testigo 9 se encendería un segundo
  después de apagar. Se prueba con CP-36 y CP-37.
- **¿Cómo prueban la interfaz si la VM no tiene pantalla?** Con Xvfb, una pantalla virtual. Las pruebas abren la
  ventana real de Tkinter y leen los colores del dibujo.
- **¿Qué mide la cobertura?** Qué líneas y qué ramas del código ejecutaron las pruebas. La lógica tiene 100%; la
  única rama sin cubrir es abrir `main.py` sin cerrarla sola, que se prueba a mano.
- **¿Qué técnicas de prueba usaron?** Partición de equivalencia, valores límite, transición de estados, caja
  blanca (cobertura), aceptación dirigida por datos y regresión.
- **¿Por qué el reloj se "inyecta"?** El estado recibe el reloj desde afuera. La app usa el real y las pruebas uno
  simulado que adelantan a voluntad. Así el mismo código se prueba sin esperar segundos reales.

## 5. Guion de la demostración (sección 9 de la guía)

| Momento | Qué hacer | Qué decir |
|---|---|---|
| 1 Contexto | Mostrar el README | Ferrari F40 1987, objetivo, los 10 elementos y sus categorías |
| 2 Arquitectura | Abrir `logic/estado.py`, `ui/presentacion.py`, `ui/tablero.py` | Separación modelo / presentación / interfaz; flujo de un valor |
| 3 Operación normal | `abrir_cluster.bat`; encender el motor, mover velocidad y RPM | Se actualiza sin reiniciar, cada 100 ms |
| 4 Advertencias | Direccional IZQ (informativo) y falla de frenos (seguridad); RPM a 8000 | Parpadeo de 500 y 300 ms; histéresis al bajar de 7800 |
| 5 Error controlado | Prueba CP-77 o el CSV con `mucho` | Se rechaza, se avisa y se conserva el último valor |
| 6 Evidencia | `docs/evidencias/pytest.txt`, `aceptacion.txt`, capturas | ⚠️ Faltan las bitácoras `eventos.log` y `errores.log` |
| 7 Conocimientos | Esta guía, sección 3 | Comunicación, memoria, seguridad |
| 8 Cierre | `03_cumplimiento_de_la_guia.md` | Limitaciones y mejoras futuras |

## 6. Glosario rápido

- **Histéresis:** dos umbrales distintos para entrar y salir de un estado.
- **Partición de equivalencia:** dividir las entradas en grupos que el sistema trata igual y probar uno de cada
  grupo.
- **Valores límite:** probar justo en el borde de cada rango (0, 360, 7799, 8000, ...).
- **Cobertura de ramas:** porcentaje de caminos `if`/`else` ejecutados por las pruebas.
- **Xvfb:** servidor gráfico virtual; permite abrir ventanas en un servidor sin pantalla.
- **Escritura atómica:** escribir en un temporal y renombrar, para que nadie lea un archivo a medias.
- **Productor/consumidor:** una actividad genera datos y otra los usa, comunicadas por una cola.
- **Espera activa:** un bucle que pregunta sin parar (`while True`); se evita con temporizadores.

## 7. Para practicar

Sin ver las respuestas, expliquen en voz alta:
1. Qué pasa, paso a paso, desde que muevo el deslizador de RPM hasta que la aguja se pone roja.
2. Por qué `set_motor(1)` falla y `set_motor(True)` no.
3. Qué ve el usuario si la presión de aceite oscila entre 0.9 y 1.1 bar, y por qué.
4. Cómo saben que el oráculo de aceptación sí detecta errores (pista: CP-90).
5. Qué cambiarían para leer los valores de un archivo sin lecturas parciales.
