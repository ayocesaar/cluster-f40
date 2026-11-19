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
