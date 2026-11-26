# Registro de defectos - Cluster F40

## DEF-01 - El testigo de falla de frenos (10) parpadea con el motor apagado

| Campo | Valor |
|-------|-------|
| ID | DEF-01 |
| Estado | Rechazado (no es defecto segun R08) |
| Severidad asignada al reportarlo | Media |
| Requisitos relacionados | R01 (encendido/apagado), R08 (testigo de falla de frenos) |
| Componente | `logic/estado.py`, propiedad `testigo_falla_frenos_encendido` (testigo 10) |
| Detectado en | Etapa 4 (revision de codigo durante pruebas de caja blanca) |
| Caso de prueba | CP-66 (`tests/test_requisitos.py`) |

**Reporte original**

1. Crear `EstadoCluster` con el motor apagado (estado inicial).
2. Llamar `set_falla_frenos(True)`.
3. Leer `testigo_falla_frenos_encendido` en t = 0 ms y cada 300 ms.

Se esperaba `False` con el motor apagado, interpretando R01 como un apagado
general de todos los testigos. Se obtuvo `True` en t = 0 ms, alternando cada 300 ms.

**Historial**

1. Etapa 6 (commit `daad491`): registrado como Abierto; CP-66 se marco `xfail`.
2. Etapa 7 (commit `382a8d9`): se agrego una condicion de motor al testigo 10 y
   el defecto se marco Cerrado.
3. Etapa 8a.1: al revisar la especificacion completa se comprobo que:
   - R08 dice "falla_frenos=1 -> testigo 10 rojo parpadeante cada 300 ms hasta
     falla_frenos=0", sin ninguna condicion de motor;
   - R01 solo regula las lecturas continuas (velocidad, RPM, temperatura,
     presion de aceite y turbo);
   - el elemento 10 esta clasificado como alerta CRITICA.

   El comportamiento original cumplia R08. Se rechazo el defecto, se revirtio el
   cambio de la Etapa 7 y CP-66 ahora verifica que el testigo 10 parpadea con el
   motor apagado y se apaga con falla_frenos=0.

**Leccion aprendida:** la expectativa de un caso de prueba debe salir de la
especificacion, no de la consistencia interna del codigo.

## DEF-02 - Error de permiso falso al leer durante una escritura concurrente en Windows

| Campo | Valor |
|-------|-------|
| ID | DEF-02 |
| Estado | Cerrado |
| Severidad / prioridad | Media / alta |
| Requisitos relacionados | Entrada externa (datos/vehiculo.conf), bitacoras |
| Componente | `sistema/lector.py`, lectura del archivo de datos |
| Detectado en | Etapa 11 (prueba P08 en Windows 11, Python 3.11) |
| Caso de prueba | CP-98 (`tests/test_sistema.py`) |

**Reporte**

1. Escribir el archivo de datos 300 veces con escritura atomica.
2. Leerlo cada 1 ms en otro hilo.
3. Revisar `logs/errores.log`.

Se esperaba `errores.log` vacio; se observaron registros `ERROR permiso_denegado`.
Los datos leidos si eran consistentes: en Windows, abrir un archivo justo cuando
otro proceso lo reemplaza con `os.replace` da un `PermissionError` momentaneo.

**Correccion:** el lector reintenta la apertura 5 veces en Windows antes de
declarar un error de permisos (commit `efc89ad`). CP-98 aprobado en Windows y en la VM.

## DEF-03 - El cluster no implementa el odometro

| Campo | Valor |
|-------|-------|
| ID | DEF-03 |
| Estado | Cerrado (Etapa 13) |
| Severidad / prioridad | Media / alta: no afecta la seguridad, pero falta una funcion de informacion en linea |
| Requisitos relacionados | REQ-ODO-01 (elemento 11, odometro) |
| Componente | No existia; ahora `logic/odometro.py`, `sistema/odometro_archivo.py`, `ui/tablero.py`, `main.py` |
| Detectado en | Practica en clase "Diseno y ejecucion supervisada de pruebas" (18-nov-2026), version `749d580` |
| Caso de prueba | CP-ODO-01 y CP-ODO-02 (fallidos), CP-ODO-03 (bloqueado); ahora CT-26 a CT-28 y CP-120 a CP-137 |

**Reporte**

1. Abrir el cluster en modo archivo.
2. Escribir `motor=1` y `velocidad=120` en `datos/vehiculo.conf`.
3. Esperar 30 s y buscar el odometro en el tablero.
4. Agregar `odometro=999999` a `datos/vehiculo.conf` y revisar `errores.log`.

Se esperaba un contador de 6 digitos que subiera 1 km. No habia contador y la
clave `odometro` se rechazaba como `clave_desconocida`. Evidencia:
`practica/evidencia_antes/`.

**Correccion:** se implemento el elemento 11. Calcula la distancia con la
velocidad mostrada por el tiempo y la muestra con 6 digitos y vuelta a cero. El
kilometraje se guarda en `datos/odometro.txt` con respaldo `.bak` y escritura
atomica. Un archivo invalido o escribible por cualquiera se rechaza, con aviso y
ERROR. `odometro=` en el archivo de datos se rechaza (`clave_no_permitida`).
Las pruebas anteriores no se modificaron. Los tres casos se repitieron como
regresion: `practica/evidencia_despues/`.

**Leccion aprendida:** un caso que espera exactamente 1 km en tiempo real queda
en el borde del cambio de digito. Los casos se corrigieron a 1.5 km (45 s y 15 s).

## DEF-04 - Los decimales del archivo se redondeaban al pasar por los controles y apagaban alertas

| Campo | Valor |
|-------|-------|
| ID | DEF-04 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Alta / alta |
| Requisitos relacionados | R02, R04, R05 (testigo 9, temperatura, turbo) |
| Componente | sistema/lector.py (Consumidor), ui/tablero.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-138 (tests/test_robustez.py) |

**Observado:** 0.9999 bar, 110.01 C y 1.5001 bar llegaban al modelo como 1.0, 110.0 y 1.5: el testigo 9, el rojo de temperatura y el contorno del turbo no se encendian.

**Correccion:** El Consumidor aplica el valor validado directo al modelo (Tablero.aplicar_externo); el control solo lo muestra. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-05 - Un dato rechazado del archivo no se avisaba en la ventana

| Campo | Valor |
|-------|-------|
| ID | DEF-05 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / alta |
| Requisitos relacionados | P04 de la guia |
| Componente | sistema/lector.py, main.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-139 (tests/test_robustez.py) |

**Observado:** Fuera de rango en datos/vehiculo.conf: ERROR en la bitacora pero ningun aviso en pantalla.

**Correccion:** El lector expone sus rechazos y el Consumidor los muestra; el aviso se retira al corregir el dato. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-06 - Un error de un ciclo congelaba el tablero; un refresco lento ocultaba los parpadeos

| Campo | Valor |
|-------|-------|
| ID | DEF-06 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Alta / alta |
| Requisitos relacionados | R06, R07, R08 |
| Componente | ui/tablero.py, sistema/config.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-140, CP-141 (tests/test_robustez.py) |

**Observado:** Una excepcion en un ciclo dejaba de programar el siguiente; con refresco_ms=1000 el direccional se veia fijo.

**Correccion:** El siguiente ciclo se programa en finally; refresco_ms se limita a 10-100 ms. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-07 - El odometro aplicaba la velocidad nueva a un intervalo ya transcurrido

| Campo | Valor |
|-------|-------|
| ID | DEF-07 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / media |
| Requisitos relacionados | REQ-ODO-01 |
| Componente | logic/estado.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-142 (tests/test_robustez.py) |

**Observado:** Con un refresco retrasado 10 s, 0 -> 360 km/h sumaba 1 km de un intervalo en reposo.

**Correccion:** Si la velocidad cambia, la nueva solo cuenta para el ultimo ciclo de lectura; el resto usa la anterior. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-08 - Dos ventanas con la misma carpeta perdian kilometraje

| Campo | Valor |
|-------|-------|
| ID | DEF-08 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / media |
| Requisitos relacionados | REQ-ODO-01 |
| Componente | main.py, sistema/odometro_archivo.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-143 (tests/test_robustez.py) |

**Observado:** La segunda ventana sobrescribia el principal y el respaldo con un valor menor.

**Correccion:** Candado de instancia unica (flock / msvcrt); la segunda ventana no guarda, avisa y registra odometro_en_uso. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-09 - Una configuracion defectuosa impedia arrancar

| Campo | Valor |
|-------|-------|
| ID | DEF-09 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / alta |
| Requisitos relacionados | Configuracion externa |
| Componente | sistema/config.py, main.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-144 (tests/test_robustez.py) |

**Observado:** refresco_ms=50% lanzaba InterpolationSyntaxError; logs apuntando a un archivo detenia el arranque.

**Correccion:** configparser sin interpolacion; si la carpeta de bitacoras no sirve se usa logs/ y se registra logs_invalido. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-10 - Cambios del archivo podian perderse o no detectarse

| Campo | Valor |
|-------|-------|
| ID | DEF-10 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / media |
| Requisitos relacionados | Entrada externa |
| Componente | sistema/lector.py, tools/escribir_dato.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-145, CP-146 (tests/test_robustez.py) |

**Observado:** Un reemplazo con igual tamano y fecha no se releia; dos escribir_dato.py simultaneos se pisaban los cambios.

**Correccion:** La firma del lector incluye el inodo; escribir_dato.py serializa con un candado de escritura. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-11 - La evidencia podia declarar aprobado lo que no lo estaba

| Campo | Valor |
|-------|-------|
| ID | DEF-11 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Media / alta |
| Requisitos relacionados | P12, informes |
| Componente | tools/ejecucion_prolongada.py, informe/generar_informe.py, tools/informe.py, practica/ejecutar_casos.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-147 (tests/test_robustez.py) |

**Observado:** P12 aprobaba con el simulador caido; los informes contaban omitidas como aprobadas; la practica salia con 0 con casos fallidos.

**Correccion:** P12 exige productor valido y mide la latencia archivo -> tablero; las conclusiones exigen 0 omitidas; la practica sale con 1 si falla un caso vigente. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-12 - Ejecutor de aceptacion y dibujo del odometro

| Campo | Valor |
|-------|-------|
| ID | DEF-12 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Baja / media |
| Requisitos relacionados | Aceptacion, elemento 11 |
| Componente | aceptacion/escenarios.py, ui/tablero.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-148, CP-149 (tests/test_robustez.py) |

**Observado:** El CSV aceptaba 361 km/h (el deslizador lo recortaba a 360) y no admitia el elemento 11; la aguja tapaba los digitos del odometro.

**Correccion:** Rango validado al cargar el CSV; elemento 11 con valor=NNNNNN; el odometro se dibuja sobre la aguja. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-13 - El modelo aceptaba NaN

| Campo | Valor |
|-------|-------|
| ID | DEF-13 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Alta / alta |
| Requisitos relacionados | R01-R05 |
| Componente | logic/estado.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-150 (tests/test_robustez.py) |

**Observado:** set_velocidad(nan) y set_temp_agua(nan) pasaban la validacion porque toda comparacion con NaN es falsa.

**Correccion:** La validacion usa not minimo <= valor <= maximo, que rechaza NaN e infinito. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-14 - Se aceptaban digitos no ASCII

| Campo | Valor |
|-------|-------|
| ID | DEF-14 |
| Estado | Cerrado (Etapa 14) |
| Severidad / prioridad | Baja / media |
| Requisitos relacionados | Entrada externa, REQ-ODO-01 |
| Componente | sistema/lector.py, sistema/odometro_archivo.py |
| Detectado en | Auditoria de robustez del 23-nov-2026 (DEF-04 a DEF-12: auditoria externa; DEF-13 y DEF-14: fuzzing propio) |
| Caso de prueba | CP-151 (tests/test_robustez.py) |

**Observado:** velocidad=５ o un odometro.txt con ６２ se aceptaban como numeros.

**Correccion:** Solo digitos ASCII en el archivo de datos y en el del odometro. La prueba fallaba en 5e9506b (docs/evidencias/robustez_antes.txt) y pasa despues.

## DEF-15 - kill PID o Ctrl+C terminaban el cluster sin cierre ordenado

| Campo | Valor |
|-------|-------|
| ID | DEF-15 |
| Estado | Cerrado (Etapa 15) |
| Severidad / prioridad | Media / alta |
| Requisitos relacionados | REQ-ODO-01 (persistencia), REQ-SIS-02 (bitacoras); tema 3.2 de la materia |
| Componente | main.py |
| Detectado en | Revision del proyecto contra el contenido de la materia (23-nov-2026) |
| Caso de prueba | CP-152 (tests/test_materia.py) |

**Observado:** en fd55f73, kill -TERM al cluster devolvia -15 (muerto por la senal), no registraba "sistema fin" y perdia el kilometraje recorrido desde el ultimo guardado (docs/evidencias/senales_antes.txt).

**Correccion:** SIGTERM y SIGINT agendan el cierre ordenado en el hilo de Tkinter (guarda el kilometraje, detiene el hilo lector, libera el candado y registra el fin); los manejadores anteriores se restauran al salir.

## DEF-16 - El sensor de velocidad del panel podia indicar menos que la velocidad real

| Campo | Valor |
|-------|-------|
| ID | DEF-16 |
| Estado | Cerrado (Etapa 18) |
| Severidad / prioridad | Baja / media |
| Requisitos relacionados | UN R39 5.3 (la velocidad indicada nunca es menor que la real); elemento 1 |
| Componente | panel/fisica.py (Vehiculo.lecturas) |
| Detectado en | Revision del codigo al implementar la prueba L05 del banco de liberacion (25-nov-2026) |
| Caso de prueba | CP-181 y CP-182 (tests/test_liberacion.py, prueba L05) |

**Observado:** en b1d4fad el panel escribia la velocidad con round(v, 1): una velocidad real de 80.04 km/h se enviaba como 80.0 km/h, es decir, el tablero indicaba menos que la velocidad real. UN R39 5.3 exige 0 <= V1 - V2.

**Correccion:** el sensor del panel redondea hacia arriba a la decima (Vehiculo.velocidad_indicada); la diferencia queda entre 0 y 0.1 km/h, dentro de 0.1 V2 + 4 km/h. La falla simulada "velocimetro" (indica 5 % menos) hace que L05 y L06 rechacen la unidad.
