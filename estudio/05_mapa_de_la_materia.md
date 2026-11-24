# Mapa de la materia — Clúster F40

Equipo 3 · Sistemas Operativos (UAG, 2026) · Cada tema del programa contra lo que hace el proyecto, dónde se ve y cómo se comprueba.

Objetivo de la materia: **simular la atención del procesador y los servicios del núcleo** para atender peticiones de usuarios y procesos. En el clúster, las peticiones son los datos del vehículo y los servicios son archivos, hilos, señales, candados, permisos y bitácoras.

Leyenda: **Cubierto** (ya estaba en el proyecto), **Añadido** (se agregó en la Etapa 15 porque aportaba evidencia real con poco costo), **No aplica** (no se agregó; se explica por qué sería pérdida de tiempo).

Las salidas reales están en `docs/evidencias/so/`. Se generan con `xvfb-run -a bash tools/evidencia_so.sh`.

## Unidad 1. Conceptos básicos

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 1.1 Hardware y software | El clúster no toca hardware: pide todo al SO por llamadas al sistema (archivos, hilos, tiempo monotónico). El "embudo de rendimiento" se mide en P12: intervalo, latencia, memoria y bitácoras | `docs/evidencias/metricas.txt`; `so/llamadas_al_sistema.txt` | Cubierto |
| 1.2 Codificación | Archivo de datos en UTF-8 validado; solo dígitos ASCII (DEF-14); velocidad como float IEEE-754 y RPM como entero; volcado hexadecimal del archivo | `so/codificacion_hexdump.txt`; CP-130, CP-151 | Añadido (hexdump) |
| 1.3 Tipos y estructuras | El clúster es un sistema embebido de **tiempo real blando**: un retraso degrada la lectura sin catástrofe; los testigos 9 y 10 son lo más cercano a "duro" y se atienden primero. Plazo de diseño archivo → tablero: 150 ms, medido en P12. Estructura por capas: modelo, sistema, interfaz | `metricas.txt` (latencia); informe técnico §2 | Cubierto (documentado aquí) |

## Unidad 2. El kernel de Linux

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 2.1 Estructura del kernel | Espacio de usuario contra kernel: cada escritura atómica es `flock`, `openat`, `write`, `fsync`, `chmod` y `rename`, vistas con `strace`; `/proc/PID/status` para hilos y memoria | `so/llamadas_al_sistema.txt`, `so/procesos_hilos_memoria.txt` | Añadido (strace, /proc) |
| 2.2 Comandos básicos | Hoja de comandos para operar y probar el clúster desde la terminal | `estudio/Hoja_de_Comandos_F40.pdf` | Cubierto |
| 2.3 Programación del shell | Scripts `iniciar.sh` y `run_NN.sh` de cada etapa. Nuevo `tools/diagnostico.sh`: el script integrador de la clase aplicado a las bitácoras del clúster (parámetros, validación, `if`, funciones, códigos de salida, reporte y rutas con espacios) | CP-153, CP-154; `so/reporte_diagnostico.txt` | Añadido |

## Unidad 3. Gestión de procesos

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 3.1 Calendarización | Hilo principal (Tkinter, cada 50 ms) e hilo lector (cada 100 ms), calendarizados por el kernel (CFS/EEVDF). Dentro de cada ciclo, el monitor atiende primero los testigos de seguridad (prioridad). Ninguna espera activa: `Event.wait` y `after()` | `so/procesos_hilos_memoria.txt` (`ps -L`, cambios de contexto); CP-117 | Cubierto |
| 3.2 Creación y eliminación | El simulador es otro proceso (fork + exec vía `subprocess`); P12 espera su código de salida (`wait`, DEF-11). **Nuevo:** SIGTERM y SIGINT producen un cierre ordenado; antes, `kill PID` mataba el clúster sin guardar (DEF-15) | CP-152; `so/senales.txt`; `docs/evidencias/senales_antes.txt` | Añadido (señales) |
| 3.3 Interbloqueo | Cada proceso toma a lo más un candado y nunca espera otro mientras lo tiene: no hay retención y espera, así que no puede formarse espera circular. El candado de instancia única usa `LOCK_NB` (no espera: si está ocupado, sigue sin guardar). El buzón `Queue(maxsize=1)` nunca bloquea al productor | `sistema/odometro_archivo.py` (Candado); `sistema/lector.py` (publicar); CP-143 | Cubierto (documentado aquí) |
| 3.4 Comunicación entre procesos | Entre procesos: archivo con escritura atómica (temporal + rename). Entre hilos: buzón productor-consumidor. Notificación: señales. Sincronización: `flock` exclusivo. El panel de control es otro productor (proceso aparte, mismo candado), y cada atajo corre un proceso hijo cuya salida llega por una **tubería** (pipe) a un hilo lector y una cola | CP-98, CP-108, CP-146, CP-152, CP-162 | Cubierto (+ panel) |

## Unidad 4. Gestión de archivos

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 4.1 Diseño del sistema de archivos | El inodo cambia en cada reemplazo atómico y el lector lo usa en su firma (DEF-10); `fsync` antes de publicar | `so/inodo.txt`; CP-145 | Añadido (evidencia de inodo) |
| 4.2 Jerarquía | `config/`, `datos/`, `logs/`, `docs/`, `tools/`; rutas solo relativas al proyecto (una ruta absoluta como `/etc` se rechaza) | CP-106 | Cubierto |
| 4.3 Acceso a archivos | Lectura secuencial completa del archivo de datos (máximo 4096 bytes); bitácoras en modo de adición con rotación; descriptores abiertos visibles en `/proc/PID/fd` | `so/procesos_hilos_memoria.txt`; CP-104 | Cubierto |
| 4.4 Archivos compartidos | Las cuatro estrategias de la clase: temporal y renombrado (datos y odómetro), bloqueo exclusivo (`escribir_dato.py`), escritor único (solo el hilo de la interfaz modifica el estado) y candado de instancia (odómetro) | `so/candado.txt`; CP-143, CP-146 | Cubierto |

## Unidad 5. Gestión de almacenamiento

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 5.1 Jerarquías | En RAM: el estado actual, que se pierde al cerrar. En disco: el kilometraje, la configuración y las bitácoras, que deben sobrevivir al apagado ("¿qué datos deben sobrevivir?"). Respaldo `.bak` y escritura atómica ante un corte de energía | `so/senales.txt` (kilometraje guardado al cerrar); CP-127 | Cubierto |
| 5.2 Asignación de memoria | La memoria la administra Python, no el proyecto. Se comprueba que no crece: RSS estable en 60 s | `metricas.txt` | No aplica: implementar First/Best Fit sería un simulador aparte sin relación con el clúster |
| 5.3 Memoria virtual | VmSize (virtual) contra VmRSS (residente) del proceso real | `so/procesos_hilos_memoria.txt` | Añadido (evidencia) |
| 5.4 Acceso a disco | El archivo de datos cabe en un bloque y el SO ordena la E/S | — | No aplica: FCFS/SCAN no se puede observar desde una aplicación sobre SSD virtual |
| 5.5 Asignación de espacio | El espacio en disco está acotado: bitácoras con rotación por tamaño (límite teórico medido en P12) | `metricas.txt` (acotado=si) | Cubierto (lo aplicable) |

## Unidad 6. Seguridad

| Tema | En el proyecto | Evidencia | Estado |
|---|---|---|---|
| 6.1 Seguridad de acceso | Permisos 640 y 750; un archivo de datos o de odómetro escribible por cualquiera se rechaza; corre sin root (privilegio mínimo); auditoría en bitácoras separadas | `so/permisos.txt`; CP-101 a CP-103, CP-131 | Cubierto |
| 6.2 Amenazas externas | Validación de toda entrada (rango, tipo, tamaño, ASCII, NaN); defensa contra DoS: tamaño máximo, rotación de bitácoras, prueba de caos con 1 100 agresiones; el kilometraje no se puede inyectar desde el archivo (`clave_no_permitida`) | `docs/evidencias/qa_caos.txt`, `qa_fuzzing.txt`; CP-107, CP-133, CP-150 | Cubierto |

## Lo que no se añadió y por qué

- **Asignación de memoria (5.2), acceso a disco (5.4) y asignación de espacio (5.5) como algoritmos:** serían simuladores independientes; no mejoran el clúster ni se evalúan con él.
- **Bomba fork y desbordamiento de pila (prácticas de clase):** son demostraciones destructivas; el proyecto demuestra lo contrario (resiste agresiones: prueba de caos).
- **Cambiar la prioridad del proceso (`nice`, `SCHED_FIFO`):** requiere privilegios de root, lo que contradice el privilegio mínimo de 6.1.

## Preguntas probables y dónde está la respuesta

| Pregunta | Respuesta corta | Dónde |
|---|---|---|
| ¿Qué llamadas al sistema usa una escritura? | flock (candado), openat del temporal, write, fsync, chmod 640 y rename (publicación atómica) | `so/llamadas_al_sistema.txt` |
| ¿Por qué cambia el inodo? | rename publica un archivo nuevo; por eso el lector compara inodo, fecha y tamaño | `so/inodo.txt` |
| ¿Cuántos hilos y procesos hay? | 2 procesos (simulador y clúster); el clúster tiene 3 hilos: el principal (Tkinter), el lector y uno interno de la biblioteca Tcl/Tk | `so/procesos_hilos_memoria.txt` |
| ¿Qué pasa con `kill PID`? | SIGTERM → cierre ordenado: guarda el kilometraje, registra "fin", código 0 | `so/senales.txt` |
| ¿Puede haber interbloqueo? | No: nadie retiene un candado mientras espera otro (se rompe "retención y espera") | Unidad 3 de este mapa |
| ¿Es tiempo real? | Blando, con un plazo de diseño de 150 ms medido en P12 | `metricas.txt` |
| ¿Qué sobrevive al apagado? | Kilometraje, configuración y bitácoras; el estado en RAM se reconstruye del archivo | Unidad 5 de este mapa |
