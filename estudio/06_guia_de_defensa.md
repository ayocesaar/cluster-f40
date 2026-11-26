# Guía de defensa — Clúster F40

Equipo 3 · César Saúl Vázquez Preciado e Ian Josué Cota Flores · Sistemas Operativos (UAG) · Ferrari F40 (1987)

Este documento sigue el orden de la guía del proyecto. Para cada pregunta trae una **respuesta corta** (para decirla en voz alta), el detalle si el profesor pide más y la **evidencia** que se puede mostrar. Todos los números salen de la última corrida oficial en la VM (Etapa 19, commit 4988ccc, 26-nov-2026): `docs/evidencias/`.

## Números clave (memorizar)

| Dato | Valor real |
|---|---|
| Pruebas automatizadas | 240 de 240 aprobadas (pytest, Xvfb): las 208 originales sin cambios, 25 de realismo (CP-163 a CP-183) y 7 de sonido (CP-184 a CP-190) |
| Aceptación sobre la interfaz | 10 de 10 escenarios, 72 pasos (CA-01 a CA-10) |
| Pruebas de la guía P01–P12 | 12 de 12 aprobadas |
| Casos del documento de pruebas | 28 de 28 (CT-01 a CT-28) |
| Cobertura | total 94 %; logic 99–100 %, ui 99–100 %, sistema 96–100 %, main 96 %, panel/liberacion 99 %, panel/sonido 94 % |
| Refresco real del tablero (P12, 60 s) | promedio 51.1 ms, p95 52.1 ms (objetivo 50 ms) |
| Latencia archivo → tablero | promedio 86.6 ms, p95 140.0 ms (cota de diseño 150 ms); máximo 154.2 ms |
| Memoria en 60 s | 29 148 KB → 29 468 KB (+320 KB, estable) |
| Bitácoras en 60 s | 39 976 bytes de un límite de 49 152 (acotadas) |
| Datos procesados en P12 | 595 escrituras del simulador, 566 lecturas aplicadas, 0 errores |
| Defectos | 16 registrados: DEF-01 rechazado, 15 cerrados (DEF-16 lo encontró el banco), 0 abiertos |
| Ataque QA | fuzzing 0 hallazgos; caos: 1 320 acciones, 0 excepciones |
| Sonido del motor | ralentí: una explosión cada 15.0 ms (4 por vuelta); limitador: envolvente p10/p90 = 0.001; alarma del cinturón 5.5 s; síntesis: 5 % de un núcleo |
| Banco de liberación | unidad sana APTA 9/9; cada una de las 5 fallas RECHAZADA por la prueba de su sistema |
| Frenado tipo 0 (modelo) | 30.2 m y 12.77 m/s² (límites: 70 m y 6.43 m/s²); en caliente 10.99 m/s² con frenos a 438 °C |
| Ciclo ECE-15 | distancia real 0.9860 km; odómetro del cuadro 0.9875 km (0.15 %) |

## 1. Guion de la demostración (20 a 25 minutos)

Preparación: VM encendida, VcXsrv abierto, panel abierto (`./abrir_panel.sh` por `ssh -Y`) y una terminal en `~/cluster-f40`.

| Momento | Qué hacer | Qué decir |
|---|---|---|
| 1 Contexto (2 min) | Mostrar el tablero (el encabezado dice FERRARI F40 (1987)) | Ferrari F40 1987. Diez elementos de la especificación más el odómetro: 2 principales, 3 de información en línea, 3 testigos informativos y 2 de seguridad. Abajo, cuatro adicionales de seguridad y consumo (12-15) |
| 2 Arquitectura (4 min) | Diagrama `docs/diagramas/arquitectura.png` | Entrada (lector), validación, modelo, interfaz, registrador y configuración separados; un hilo lector y el hilo de la interfaz unidos por un buzón |
| 3 Operación normal (3 min) | Panel: Abrir tablero, LLAVE (K: prueba de testigos), ARRANQUE (M), cinturón (B), marcha 1, acelerar (W) | El panel solo escribe `datos/vehiculo.conf`; el tablero lo lee cada 100 ms y cambia sin reiniciar |
| 4 Advertencias (3 min) | Luces altas o puerta abierta (informativo) y "Fuga de aceite" (seguridad) | El testigo 9 se enciende tras 1 s bajo 1 bar (R02) y queda un WARN prioritario en eventos.log. Con la puerta abierta el auto no avanza; con la fuga, al apagar ya no arranca (STOP · ACEITE) |
| 5 Error controlado (3 min) | "Dato corrupto" o "Borrar archivo" | El tablero no se detiene: conserva el último valor válido, avisa y registra ERROR; a los 3 s se recupera solo |
| 6 Evidencia (2 min) | Recuadro de bitácoras del panel, o `tail -f logs/eventos.log logs/errores.log` | Dos archivos separados con fecha ISO, nivel, componente, evento, detalle y resultado |
| 7 Conocimientos (5 min) | Respuestas de las secciones 2 a 4 de esta guía; si sobra tiempo, el banco de liberación (sección 10) | Comunicación, sincronización, memoria, almacenamiento y seguridad, con la prueba de cada uno |
| 8 Cierre (2 min) | Sección 9 de esta guía | Limitaciones reales y mejoras futuras |

## 2. Las ocho preguntas obligatorias (guía, sección 9)

**1. ¿Por qué eligió ese tipo de dato para cada elemento?**

Respuesta corta: cada tipo es el más pequeño que representa la medida sin perder precisión ni permitir estados imposibles.

- Velocidad, presiones y temperatura: decimal (float de 64 bits), porque los umbrales necesitan décimas o centésimas (0.99 / 1.0 bar, 110.1 °C, 1.5 / 1.51 bar).
- RPM: entero. No hay fracciones de revolución y el rango 0–9000 cabe en 16 bits; un "4500.5" se rechaza, no se redondea en silencio.
- Motor, luces altas, emergencia y frenos: booleano codificado 0/1 (dos estados).
- Direccional: enumeración cerrada off/izquierda/derecha, que impide estados imposibles como "izquierda y derecha a la vez".
- Testigo 9: booleano calculado de la presión con tiempo (no viene del archivo).
- Odómetro: decimal interno (conserva la fracción de km) y se muestra como entero de 6 dígitos.
- Evidencia: fichas del informe técnico §3; `sistema/lector.py` (función `convertir`); CP-95 y CP-151 (solo dígitos ASCII); CP-150 (rechazo de NaN e infinito).

**2. ¿Qué ocurre si el archivo cambia mientras está siendo leído?**

Respuesta corta: nunca se lee un archivo a medias, porque el escritor no modifica el archivo: escribe uno nuevo y lo publica de forma atómica.

- El escritor escribe un temporal en la misma carpeta, hace `fsync` y lo publica con `os.replace` (la llamada `rename`, que es atómica). El lector ve la versión vieja completa o la nueva completa.
- Si dos escritores coinciden, `escribir_dato.py` y el panel toman un candado exclusivo (`flock`), así ninguno borra el cambio del otro (CP-146).
- El lector detecta el cambio por una firma (inodo, fecha y tamaño). El inodo cambia en cada reemplazo, así que un cambio con el mismo tamaño y fecha también se detecta (CP-145, DEF-10).
- Evidencia: CP-98 (300 escrituras concurrentes mientras el hilo lee cada 1 ms, ningún valor parcial); `docs/evidencias/so/llamadas_al_sistema.txt` (strace: flock, openat, write, fsync, chmod, rename) y `so/inodo.txt`.

**3. ¿Cuál tarea tiene mayor prioridad y por qué?**

Respuesta corta: el monitor de seguridad (testigos 9 y 10), porque una advertencia crítica que no aparece o aparece tarde es el peor fallo posible en un tablero.

- En cada ciclo, el monitor revisa primero los testigos de seguridad y los registra como WARN; después revisa las demás advertencias.
- El retardo de 1 s del testigo 9 se mide con marcas de tiempo, no contando ciclos: si la interfaz se atrasa, el segundo de espera no cambia.
- Si se retrasara: el conductor vería tarde la baja presión de aceite o la falla de frenos. Por eso el refresco es de 50 ms y la lectura de 100 ms.
- Evidencia: `sistema/monitor.py`; CP-99 (P09) y CP-117.

**4. ¿Qué información permanece en memoria y cuál se almacena?**

Respuesta corta: en memoria solo el estado actual; en disco lo que debe sobrevivir al apagado.

- Memoria: un `EstadoCluster` de tamaño fijo, el último valor válido de las 10 claves (más las opcionales que lleguen) y un buzón de capacidad 1. No hay historial en RAM.
- Disco: `config/cluster.ini` (parámetros), `datos/vehiculo.conf` (entrada), `datos/odometro.txt` con su respaldo `.bak` (kilometraje) y `logs/` (eventos y errores por separado).
- Evidencia: P12 (+320 KB en 60 s); `so/procesos_hilos_memoria.txt` (VmSize contra VmRSS); `so/senales.txt` (el kilometraje se guarda al cerrar).

**5. ¿Cómo evita que las bitácoras crezcan indefinidamente?**

Respuesta corta: rotación por tamaño y registro solo de cambios, no de cada ciclo.

- `RotatingFileHandler`: cada archivo tiene un tamaño máximo (`max_bytes`, 256 KB por defecto) y un número fijo de respaldos (3). El espacio total queda acotado.
- El monitor registra transiciones (un testigo que se enciende o se apaga), no cada parpadeo. El lector no repite el mismo error mientras dura.
- Evidencia: P12 con bitácoras de 16 KB: 39 976 bytes de un límite de 49 152; CP-104 (3000 ciclos con rotación).

**6. ¿Qué amenaza considera más probable y qué control la reduce?**

Respuesta corta: la más probable es un dato inválido en el archivo de datos (error humano o un productor defectuoso). Se controla validando toda entrada antes de usarla.

- Prevención: tipo, rango, formato, tamaño máximo (4096 bytes), solo dígitos ASCII y claves conocidas; `odometro=` se rechaza (`clave_no_permitida`).
- Detección: ERROR en `errores.log` y aviso en la ventana (P04, DEF-05).
- Recuperación: se conserva el último valor válido y se retoma sin reiniciar.
- Otras amenazas: un archivo modificable por otros usuarios (se rechaza un archivo 666; bitácoras 640, carpeta 750); rutas fuera del proyecto (se rechaza `/etc`); inyección de comandos (el panel ejecuta listas de argumentos, nunca concatena texto en un shell); dos instancias pisándose el kilometraje (candado de instancia única).
- Evidencia: CP-101 a CP-103, CP-106, CP-107, CP-131, CP-133, CP-143; `qa_fuzzing.txt`, `qa_caos.txt`.

**7. ¿Qué alternativa técnica evaluó y por qué la descartó?**

Respuesta corta: descartamos variables globales compartidas entre hilos y elegimos una cola (buzón) de tamaño 1.

- Variables globales: hay condiciones de carrera y obligan a poner candados en todo el modelo. La `queue.Queue` ya trae sus candados y, con tamaño 1, guarda solo el dato más reciente.
- Formato de entrada: se compararon JSON, CSV y clave=valor. Ganó clave=valor porque se edita a mano y cada línea se valida por separado.
- Lectura con candado contra escritura atómica: se eligió temporal + rename, porque el lector nunca espera ni ve datos parciales.
- Evidencia: informe técnico, sección de justificaciones; CP-108.

**8. ¿Cómo demostraría que el sistema se recupera de un error?**

Respuesta corta: en vivo, con el panel: "Dato corrupto" o "Borrar archivo". El tablero no se cierra, avisa y registra ERROR; a los 3 s el panel restaura datos válidos y el tablero vuelve a actualizarse solo.

- En las bitácoras se ve `dato_invalido` o `archivo_inexistente` en errores.log, y después `archivo_recuperado` y `valor_actualizado` en eventos.log.
- Ante una interrupción: `kill -TERM` produce un cierre ordenado (guarda el kilometraje, código 0). Si el archivo del odómetro se corrompe, se restaura del respaldo `.bak`.
- Evidencia: CP-100 (P10), CP-110, CP-126, CP-152; prueba de caos.

## 3. Decisiones técnicas (guía, sección 5)

| Decisión | Alternativas | Elegido y por qué | Evidencia |
|---|---|---|---|
| Formato de entrada | JSON, CSV, clave=valor | clave=valor: se edita a mano y cada línea se valida sola | CP-91 a CP-96 |
| Frecuencia | Por evento, 10 ms, 100/50 ms | Lectura 100 ms (el ciclo más rápido de la especificación) y refresco 50 ms (la mitad, para no perder cambios); el refresco se limita a 100 ms para no ocultar parpadeos | P12, CP-141 |
| Comunicación | Globales, tubería, cola | Procesos: archivo con escritura atómica. Hilos: cola de tamaño 1 | CP-98, CP-108 |
| Recurso compartido | Candados en el modelo, un solo dueño | Un solo dueño: solo el hilo de la interfaz modifica el estado y la ventana; el lector produce copias | CP-115 |
| Memoria contra disco | Todo en disco, todo en memoria | Estado en RAM; historia en bitácoras rotativas; kilometraje persistido | P12, CP-127 |
| Permisos | Permisos por defecto o restringidos | 640 y 750; rechazo de archivos escribibles por cualquiera; sin root | CP-101 a CP-103 |
| Recuperación | Detener, ignorar, último válido | Último valor válido, aviso, ERROR y recuperación sin reinicio | CP-97, CP-100 |

## 4. Conocimientos del curso (guía, sección 4)

**4.1 Representación de datos.** Tipos de la pregunta 1. Caso de codificación: el booleano viaja como texto "0"/"1" y la enumeración como texto que se traduce a OFF/IZQ/DER. En UTF-8, "５" ocupa 3 bytes (ef bc 95) y se rechaza (`so/codificacion_hexdump.txt`). Se comprueba la pérdida de precisión (DEF-04: los controles redondeaban 0.9999 a 1.0; ahora el valor validado llega directo al modelo).

**4.2 Procesos y calendarización.** Lectura (hilo lector), validación (lector), actualización visual (hilo de Tkinter con `after()`) y registro (bitácora) separados. Sin espera activa: `Event.wait` y `after()`. El simulador o el panel es otro proceso (fork + exec). Hay 3 hilos en el clúster: el principal, el lector y uno interno de Tcl/Tk (`so/procesos_hilos_memoria.txt`).

**4.3 Comunicación y sincronización.** Productor: el panel, el simulador o `escribir_dato.py` (otros procesos). Consumidor: el hilo lector, y después el hilo de la interfaz. Dato: el snapshot de las 10 claves y de las opcionales presentes. Dirección: archivo → lector → buzón → interfaz. Sin carreras: escritura atómica, `flock` entre escritores y un solo dueño del estado. Concurrencia probada: CP-98, CP-146. Además, señales (SIGTERM → cierre ordenado) y tuberías en los atajos del panel.

**4.4 Sistema de archivos.** Rutas relativas al proyecto (las absolutas se rechazan). Archivo de datos: se sobrescribe completo y se lee secuencial. Bitácoras: solo se agrega al final (modo adición). Persisten configuración, kilometraje y bitácoras.

**4.5 Memoria y almacenamiento.** Estructuras de tamaño fijo, sin historial en RAM. La ventana crea sus figuras una sola vez (menos de 300) y solo mueve agujas o recolorea (localidad). Durabilidad: `fsync` antes de `rename` y respaldo `.bak` del kilometraje.

**4.6 Seguridad.** Validación total, mínimo privilegio (640/750, sin root), ningún comando armado con texto externo, ninguna contraseña en el código, y amenazas con prevención, detección y recuperación (pregunta 6).

**4.7 Errores y bitácoras.** `eventos.log` (INFO/WARN) y `errores.log` (ERROR) separados, con fecha ISO 8601, nivel, componente, evento, detalle y resultado. Ejemplo real: `ERROR lector_datos fuera_de_rango velocidad=400 (rango 0-360) resultado=rechazado`.

## 5. Pruebas obligatorias P01–P12

| P | Qué demuestra | Prueba |
|---|---|---|
| P01 Valor normal | Indicador actualizado y evento INFO | CP-91 |
| P02 / P03 Límites | Mínimos y máximos aceptados sin error | CP-92, CP-93 |
| P04 Fuera de rango | Rechazo, aviso en la ventana y ERROR | CP-94, CP-139 |
| P05 Formato | Continúa con el último valor válido | CP-95 |
| P06 Dato ausente | Estado definido y error registrado | CP-96 |
| P07 Archivo inexistente | No termina | CP-97 |
| P08 Concurrencia | Sin valores parciales | CP-98, CP-146 |
| P09 Advertencia | Testigo visible y WARN prioritario | CP-99 |
| P10 Recuperación | Retoma sin reinicio | CP-100 |
| P11 Permisos | Rechazo registrado; bitácoras 640 | CP-101 a CP-103 |
| P12 Prolongada | Memoria y bitácoras acotadas, intervalo medido | CP-104 y `metricas.txt` |

## 6. Rúbrica: qué mostrar por criterio

| Criterio | Qué mostrar |
|---|---|
| 1 Definición y diseño | F40 1987, fichas de los 15 elementos (10 aprobados, odómetro y 4 adicionales), diagramas |
| 2 Diez elementos | Los 10 funcionando en vivo; aceptación 10/10 |
| 3 Datos y validación | Tipos y rangos; bits de estado (puertas); consistencia motor/contacto (`dato_inconsistente`); dato corrupto en vivo; CP-150, CP-151 y CP-164 |
| 4 Archivos y persistencia | Estructura de carpetas; escritura atómica; kilometraje que sobrevive al cierre |
| 5 Procesos y actualización | Hilo lector y hilo de la interfaz; 50/100 ms; P12 |
| 6 Comunicación y sincronización | Buzón, flock, rename; CP-98 y CP-146 |
| 7 Memoria y almacenamiento | Sin historial en RAM, rotación, +320 KB en 60 s |
| 8 Seguridad | Validación, 640/750, amenazas, fuzzing y caos; seguridad del vehículo: interbloqueo de puertas y protecciones de la ECU |
| 9 Errores y registros | Dos bitácoras con formato completo; recuperación en vivo |
| 10 Documentación y defensa | Informe técnico, documento de pruebas, este documento |

## 7. Mapa del código (para "explique este archivo")

| Archivo | Qué hace en una frase |
|---|---|
| `logic/estado.py` | El modelo: reglas R01–R08 y R09–R12, llave (Encendido contra Motor activo), validación de entradas y el reloj de cada ciclo |
| `logic/odometro.py` | Integra velocidad × tiempo; 6 dígitos con vuelta a cero |
| `sistema/lector.py` | Lee y valida el archivo de datos; hilo lector, buzón y consumidor; escritura atómica |
| `sistema/bitacora.py` | Dos bitácoras rotativas con permisos 640 |
| `sistema/monitor.py` | Registra transiciones; los testigos de seguridad van primero |
| `sistema/config.py` | Lee `config/cluster.ini` y valida rutas, intervalos y rangos |
| `sistema/odometro_archivo.py` | Kilometraje con respaldo, escritura atómica y candado de instancia única |
| `ui/presentacion.py` | Traduce el estado a lo que se dibuja (colores y posiciones), sin Tkinter |
| `ui/tablero.py` | Dibuja el cuadro estilo F40; no contiene reglas |
| `main.py` | Une todo; maneja las señales SIGTERM y SIGINT para un cierre ordenado |
| `panel/ventana.py`, `panel/fisica.py` | Panel de control: cabina, llave, puertas, taller y una física simplificada con fallas reales |
| `panel/ecu.py` | ECU simulada: decide si el motor puede arrancar o debe detenerse y bloquea la tracción con una puerta abierta |
| `panel/liberacion.py` | Banco de liberación: 9 pruebas de la época (R13-H, R39, ECE-15) con dictamen APTO o RECHAZADO |
| `tools/` | Simulador, escritor, P12, capturas, diagnóstico en Bash, evidencia del SO, ataque QA |

## 8. Preguntas difíciles probables

**¿Qué pasó con el odómetro de la práctica?** El profesor lo asignó en la práctica. Los tres casos fallaron o quedaron bloqueados porque no existía (DEF-03). Se implementó sin modificar ninguna prueba anterior y se repitieron. Además se corrigieron nuestros propios casos: con 30 s y 10 s el resultado quedaba en el borde del cambio de dígito (62.997 km), así que se pasaron a 45 s y 15 s, y ahora aprueban.

**¿Puede haber interbloqueo?** No. Ningún proceso retiene un candado mientras espera otro, así que se rompe la condición de "retención y espera" y no puede formarse una espera circular. El candado de instancia ni siquiera espera (`LOCK_NB`).

**¿Es un sistema de tiempo real?** Blando: un retraso degrada la lectura, pero no causa una catástrofe. El plazo de diseño archivo → tablero es de 150 ms; el promedio medido es de 86.6 ms (p95 140.0 ms).

**¿Qué hace un `kill PID`?** Envía SIGTERM. El clúster lo atrapa, agenda el cierre en el hilo de Tkinter, guarda el kilometraje, detiene el hilo lector, libera el candado y registra "sistema fin" (código 0). Antes se cerraba sin guardar (DEF-15, código -15).

**¿Cómo prueban la interfaz sin pantalla?** Con Xvfb, una pantalla virtual: las pruebas abren la ventana real y leen lo que se dibujó (colores y textos).

**¿Por qué Python y Tkinter?** Tkinter viene con Python, no hay dependencias para correr el tablero y funciona en Linux y Windows. Lo importante del proyecto (archivos, hilos, señales, permisos) son servicios del sistema operativo que se usan igual desde cualquier lenguaje.

**¿Usaron inteligencia artificial?** Sí, y está documentado (anexo D del documento de pruebas y `docs/bitacora_ia.md`). Cada resultado sale de ejecuciones reales y se rechazaron propuestas de la IA cuando contradecían la especificación (DEF-01 contra R08) o la evidencia (las duraciones de 30 s y 10 s del odómetro).

**¿Cómo saben que las pruebas no se ajustaron para pasar?** El script de cada etapa compara una huella sha256 de las pruebas anteriores antes de guardar y aborta si alguna cambió. Además, las pruebas de robustez se escribieron primero y fallaron con el código anterior (`robustez_antes.txt`).

**¿Por qué el testigo 10 parpadea con el motor apagado?** Porque R08 no lo condiciona al motor y es una alerta crítica (decisión D1). El defecto DEF-01, que decía lo contrario, se rechazó.

## 9. Cierre: limitaciones y mejoras

**Limitaciones (decirlas antes de que las pregunten):**

- La latencia promedio (86.6 ms) y el p95 (140.0 ms) cumplen la cota de 150 ms; el máximo fue 154.2 ms. Entre corridas varía con la carga de la VM (en la Etapa 17 el p95 fue 233.4 ms y en la Etapa 18 hubo un máximo aislado de 1098.7 ms).
- Probado a fondo en Linux. En Windows, el Python de Microsoft Store falla a veces al cargar Tcl/Tk.
- En pantallas de 1024×768, parte de los controles no cabe.
- Las categorías de los elementos 2, 3 y 5 están por confirmar con el profesor.
- Las cifras del motor del panel son aproximadas, no oficiales.
- El banco usa los criterios de UN R13-H y UN R39 leídos en su texto moderno; los valores de la Directiva 71/320/CEE de 1987 quedan pendientes de verificar. Las protecciones y el interbloqueo de puertas son del equipo, no del F40 original.
- Siguen pendientes la revisión cruzada, el escenario sorpresa y el acceso por Wi-Fi.

**Mejoras futuras:** avisar los cambios del archivo con inotify en lugar de revisar cada 100 ms (menor latencia y consumo); vista de solo lectura por red para otros dispositivos; pruebas nativas en Windows y macOS.

**Aprendizaje:** las pruebas deben salir de la especificación, no del código; atacar el propio sistema encuentra lo que las pruebas "felices" no ven (DEF-04 a DEF-15).

## 10. Realismo, seguridad y banco de liberación (Etapa 18)

**Qué se agregó (respuesta corta):** llave de contacto separada del arranque, cuatro elementos adicionales (12 puerta, 13 cinturón, 14 combustible, 15 protección del motor), una ECU simulada en el panel que decide cuándo el motor no puede arrancar o debe detenerse, fallas con consecuencias físicas y un banco de pruebas de liberación de producción con normas de la época.

**Demostración corta (3 min):** K (prueba de testigos) → marcar "Fuga de aceite" y M: no arranca, STOP · ACEITE → Taller: Reparar fallas y M: arranca → P y acelerar: no avanza (interbloqueo) → "Banco con las fallas actuales" con "Frenos": RECHAZADO (L02, L03, L04) → Reparar fallas y repetir: APTO PARA PRODUCCIÓN. Guion completo: `docs/realismo_y_liberacion.md`, sección 7.

**¿Por qué el cuadro no decide si el motor se apaga?** Porque en un auto real la unidad de control del motor y el cuadro son equipos distintos: el cuadro solo muestra. Aquí la ECU vive en el proceso del panel (`panel/ecu.py`) y la causa viaja al tablero en la clave `falla_motor` (decisión D11).

**¿Qué pasa con un archivo de diez claves?** Funciona igual que antes: las claves nuevas son opcionales (D8). Si una opcional nunca llega, su elemento queda "sin dato" sin error; si deja de llegar, se registra INFO `clave_opcional_retirada`; si llega inválida, ERROR y se conserva el último valor válido, igual que las diez.

**¿Qué es la consistencia del validador?** La guía pide al validador "tipo, rango, unidad y consistencia". `motor=1` con `contacto=0` es imposible: ERROR `dato_inconsistente` y el cuadro sigue al motor (D9, CP-164).

**¿Qué es un dato de bits de estado?** `puertas` guarda dos puertas en un entero: bit 0 conductor y bit 1 pasajero; `puertas=3` son las dos abiertas (bloque 4.1, CP-163).

**¿Qué normas usa el banco y son reales?** UN R13-H anexo 3 (frenado tipo 0: desde 100 km/h, distancia ≤ 70 m y desaceleración ≥ 6.43 m/s²; tipo I: 15 frenadas de 120 a 60 km/h cada 45 s), UN R39 (velocímetro: nunca indica menos que la velocidad real y 0 ≤ V1 − V2 ≤ 0.1 V2 + 4 km/h a 40, 80 y 120 km/h) y el ciclo urbano ECE-15 (195 s, 0.994 km). Los textos se leyeron en las ADR 31/01 y 18/03 de Australia, que adoptan esos reglamentos. Lo que no se pudo verificar (los valores de 1987 de la Directiva 71/320/CEE) está marcado como pendiente.

**¿Encontró algo el banco?** Sí: DEF-16. El sensor de velocidad del panel redondeaba al décimo más cercano y podía indicar 80.0 km/h a 80.04 km/h reales, lo que R39 prohíbe. Ahora redondea hacia arriba.

**¿Cómo se relaciona con Sistemas Operativos?** El banco corre como proceso hijo del panel con su salida por una tubería; el ciclo ECE-15 en vivo es un productor que escribe mientras el tablero consume; el formato evoluciona sin romper a los productores anteriores; y el odómetro del cuadro se compara contra la distancia real del ciclo (prueba L06).


## 11. Sonido del motor (Etapa 19)

**Qué es (respuesta corta):** el sonido no es una grabación: se calcula muestra por muestra. Cada explosión del motor es un pulso que hace sonar tres resonadores; un V8 de cuatro tiempos tiene 4 explosiones por vuelta, así que en ralentí (1000 rpm) suena una cada 15 ms y en el limitador 547 por segundo. Encima van el turbo (silbido y descarga), el limitador (cortes de combustión), el motor de arranque y la alarma del cinturón.

**¿Por qué no usaron el audio de un video?** Porque YouTube no permite descargar sus videos y la guía pide la procedencia y la licencia de todo recurso de terceros. Sintetizado no hay terceros y el sonido sigue exactamente al modelo físico.

**¿Cómo llega el sonido de la VM a las bocinas?** Es un tercer proceso: el panel (en la VM) manda el estado del motor, 20 veces por segundo, por un socket TCP dentro de un túnel SSH inverso a `tools/bocina.py` en Windows, que sintetiza y reproduce con waveOut. Es el mecanismo "sockets" de la sección 4.3 de la guía.

**¿Es tiempo real?** Blando: el hilo de audio genera bloques de 30 ms y nunca va más de 120 ms adelante del reloj. Si se atrasa, se oye un hueco pero nada falla, y se resincroniza. No hay espera activa: el hilo duerme con `Event.wait` y waveOut lo despierta con un evento cuando termina un búfer.

**¿Cómo saben que suena a V8 si no se puede "ver" un sonido?** Las pruebas miden el audio: en ralentí la envolvente se repite cada 15 ms (4 explosiones por vuelta), a 6000 rpm domina la frecuencia de encendido (400 Hz), en el limitador la envolvente cae casi a cero a ratos, el silbido del turbo aparece con la presión y la alarma dura entre 4 y 8 s (CP-184 a CP-190; `docs/evidencias/sonido/reporte.txt`).

**¿Qué pasa si alguien manda basura a la bocina?** Escucha solo en 127.0.0.1, valida cada línea (claves, tipos, rangos, sin NaN, máximo 512 bytes), descarta y cuenta lo inválido, y si el panel deja de hablar 1 s se calla (CP-189).

**Demostración (1 min):** con la bocina abierta, `M` (motor de arranque y ralentí), `W` en neutral (acelerones y petardeos al soltar), primera a fondo hasta el limitador (cortes), segunda con el turbo y soltar (descarga). Sin VM: reproducir `docs/evidencias/sonido/motor_demo.wav`.
