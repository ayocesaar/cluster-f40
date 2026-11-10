# Guía de estudio para la demostración

Para cada pregunta: la **respuesta corta** (lo que se dice), **dónde está** en el código (para enseñarlo) y **cómo
demostrarlo** en vivo. Los números reales de cada prueba están en `docs/evidencias/` y en los informes de
`informe/`.

---

## 1. El proyecto en dos minutos

- **Qué es:** un simulador del clúster de instrumentos del **Ferrari F40 (1987)** con 10 elementos. Los valores
  llegan de un **archivo externo** (`datos/vehiculo.conf`) que el tablero relee cada 100 ms sin reiniciar.
- **Componentes** (la separación que pide la guía):

| Componente | Archivo | Qué hace | Qué no hace |
|---|---|---|---|
| Configuración | `config/cluster.ini`, `sistema/config.py` | Rutas, intervalos, rangos y rotación de bitácoras | Obligar a recompilar |
| Entrada de datos | `sistema/lector.py` (`Lector`, `HiloLector`) | Lee y convierte el archivo en un hilo propio | Dibujar |
| Validador | `sistema/lector.py` (`convertir`) y `logic/estado.py` (`set_*`) | Tipo, formato, rango y largo; dos capas | Aceptar datos inválidos |
| Modelo | `logic/estado.py` (`EstadoCluster`) | Último estado válido y reglas R01–R08 | Saber cómo se dibuja |
| Interfaz | `ui/presentacion.py`, `ui/tablero.py` | Dibuja los 10 elementos | Modificar la configuración |
| Registrador | `sistema/bitacora.py`, `sistema/monitor.py` | `eventos.log` y `errores.log` con fecha, nivel y componente | Mezclar niveles |
| Arranque | `main.py`, `iniciar.sh`, `abrir_cluster.bat` | Arma y conecta todo | Reglas de negocio |

- **Flujo de un valor:**
  1. Alguien escribe `datos/vehiculo.conf`, de preferencia con `tools/escribir_dato.py` (atómico).
  2. El hilo lector lo lee, valida cada clave y registra INFO o ERROR.
  3. El hilo lector publica una copia en el buzón.
  4. La interfaz (cada 50 ms) toma la copia y la aplica con `set_*`.
  5. `tick()` aplica ciclos y reglas.
  6. El monitor registra las advertencias.
  7. `refrescar()` dibuja.

Los diagramas están en `docs/diagramas/`.

## 2. Los diez elementos

| N.º | Elemento | Categoría | Clave | Tipo | Rango | Regla |
|---|---|---|---|---|---|---|
| 1 | Velocímetro | Principal | `velocidad` | decimal | 0–360 km/h | R01: a 0 al apagar |
| 2 | Presión de aceite | En línea | `presion_aceite` | decimal | 0–10 bar | ámbar inmediato < 1 bar |
| 3 | Tacómetro | En línea | `rpm` | entero | 0–9000 | R03: rojo ≥ 8000, normal < 7800 |
| 4 | Temperatura de agua | Principal | `temp_agua` | decimal | 40–130 °C | R04: rojo > 110, normal ≤ 105; ciclo 500 ms |
| 5 | Presión de turbo | En línea | `presion_turbo` | decimal | 0–2 bar | R05: ámbar > 1.5, normal ≤ 1.4 |
| 6 | Direccionales | Informativo | `direccional` | enumeración | off/izquierda/derecha | R06: verde cada 500 ms |
| 7 | Luces altas | Informativo | `luces_altas` | booleano 0/1 | — | R07: azul fijo |
| 8 | Emergencia | Informativo | `emergencia` | booleano 0/1 | — | R07: ámbar cada 500 ms, tapa al 6 |
| 9 | Baja presión de aceite | Seguridad | calculado | booleano | — | R02: rojo tras 1 s < 1 bar; apaga tras 1 s ≥ 1.2 |
| 10 | Falla de frenos | Seguridad | `falla_frenos` | booleano 0/1 | — | R08: rojo cada 300 ms, aun con motor apagado |

## 3. Las preguntas de la guía (sección 9)

### 3.1 ¿Por qué eligió ese tipo de dato para cada elemento?

**Respuesta.**
- Velocidad, presiones y temperatura son **decimales**, porque la especificación usa fracciones (120.5 km/h,
  0.99 bar, 110.1 °C). Python usa IEEE-754 de 64 bits: sobra precisión para una centésima.
- Las **RPM son enteras**: no existen 4500.5 rpm. Un decimal se **rechaza**, no se redondea en silencio.
- Los interruptores son **booleanos** codificados `0`/`1` en el archivo. Hay un detalle: en Python `bool` es subclase
  de `int` (`True == 1`), por eso la validación revisa primero si es booleano.
- El direccional es una **enumeración cerrada**, que impide estados imposibles.

**Dónde.** `sistema/lector.py`: `CLAVES`, `convertir`, `formatear`. `logic/estado.py`: `_validar_numero`,
`_validar_bool`.

**Demostrarlo.** `python3 tools/escribir_dato.py rpm=4500.5`. Lo rechaza con un mensaje y código 2.

### 3.2 ¿Qué ocurre si el archivo cambia mientras está siendo leído?

**Respuesta.** No se leen datos parciales, por dos defensas:
1. Quien escribe usa **escritura atómica**. Escribe un archivo temporal en la misma carpeta, hace `fsync` y lo
   renombra con `os.replace`, que es atómico. El lector ve el archivo viejo completo o el nuevo completo.
2. El lector lee el archivo **completo de una vez** y **valida cada clave**. Si alguien guarda con un editor común y
   el lector alcanza a ver algo incompleto, la clave se rechaza, se conserva el último valor válido y en la
   siguiente lectura llega el dato completo.

En Windows, abrir el archivo justo en el instante del reemplazo da un "permiso denegado" momentáneo. El lector
reintenta 5 veces antes de considerarlo un error real; lo encontramos en la prueba P08.

**Dónde.** `sistema/lector.py`: `escribir_texto_atomico`, `Lector._leer_texto`.

**Demostrarlo.** Prueba P08 (CP-98): 300 escrituras mientras el hilo lee cada 1 ms. Cada dato leído cumple
`rpm == velocidad × 10`, así que nunca hubo mezcla. En vivo: `python3 tools/simulador.py` con el tablero abierto.

### 3.3 ¿Cuál tarea tiene mayor prioridad y por qué?

**Respuesta.** El **monitor de seguridad**: la evaluación y el registro de los testigos 9 y 10. Va primero en
`MonitorEventos.revisar` y se registra como WARN. Si el ciclo se retrasa, la pantalla se actualiza tarde, pero las
reglas no se equivocan:
- El retardo de 1 s del testigo 9 se mide con **marcas de tiempo**.
- Los parpadeos se calculan con el **reloj absoluto** (`int(ahora // periodo) % 2`).

**Frecuencias:**
- Lectura cada 100 ms: es el ciclo más rápido de la especificación.
- Refresco cada 50 ms: la mitad, para no perder cambios.

Ninguna tarea hace espera activa: el lector duerme con `Event.wait` y la interfaz usa `after()`. El intervalo real
medido está en `docs/evidencias/metricas.txt`.

### 3.4 ¿Qué información permanece en memoria y cuál se almacena?

**En memoria** (tamaño fijo, sin historial):
- El objeto `EstadoCluster`.
- El diccionario `ultimo_valido` del lector (10 claves).
- El buzón de capacidad 1.
- Las figuras de la ventana, creadas una vez y reutilizadas.

**En disco**, en archivos separados:
- Configuración: `config/cluster.ini`.
- Datos de entrada: `datos/vehiculo.conf`, que se sobrescribe completo.
- Eventos y errores: `logs/eventos.log` y `logs/errores.log`, que solo agregan líneas al final y rotan.

**Demostrarlo.** `docs/evidencias/metricas.txt` muestra la memoria (RSS) al inicio y al final de la ejecución
prolongada.

### 3.5 ¿Cómo evita que las bitácoras crezcan indefinidamente?

**Respuesta.** Rotación por tamaño con `RotatingFileHandler`. Cada archivo llega como máximo a `max_bytes`; entonces
se renombra (`.1`, `.2`) y se borra el más viejo. El espacio total queda acotado a `max_bytes × (respaldos + 1)` por
archivo. Además, un mismo error se registra **una sola vez** mientras dura, y el monitor registra **transiciones**,
no cada parpadeo.

**Dónde.** `sistema/bitacora.py`; `config/cluster.ini`, sección `[bitacora]`.

**Demostrarlo.** P12:
- CP-104: 3000 ciclos y los archivos no pasan del límite.
- `metricas.txt`: tamaño de las bitácoras antes y después.

En vivo: `watch -n 1 "du -h logs/*.log"`.

### 3.6 ¿Qué amenaza considera más probable y qué control la reduce?

**La más probable:** datos de entrada inválidos o manipulados.
- **Preventivo:** validación de tipo, formato, rango y largo (máximo 32 caracteres por valor, 4 KB por archivo).
- **Detección:** ERROR en `errores.log` con el texto recibido.
- **Recuperación:** se conserva el último valor válido.

**Otras amenazas** (están en el informe técnico §8):
- Otro usuario modifica el archivo de datos: se rechaza un archivo escribible por cualquiera y las bitácoras quedan
  con permisos 640.
- Lectura parcial: escritura atómica.
- Llenado del disco: rotación.
- Rutas fuera del proyecto en la configuración: solo se aceptan rutas relativas.
- Inyección de comandos: no se arma ningún comando con datos de entrada.

**Demostrarlo.**
- `chmod 666 datos/vehiculo.conf`: aparece ERROR `permisos_inseguros`.
- `chmod 640 datos/vehiculo.conf`: se recupera solo.

### 3.7 ¿Qué alternativa técnica evaluó y por qué la descartó?

- **Variables globales compartidas frente a una cola.** Las variables compartidas permiten condiciones de carrera.
  Se eligió `queue.Queue(maxsize=1)`, que ya trae candados y guarda solo el dato más reciente.
- **Candados en el modelo frente a un solo dueño.** Tkinter no es seguro entre hilos, así que solo el hilo de la
  interfaz modifica el modelo y la ventana; el lector únicamente produce copias. Sin candados no hay interbloqueos.
- **JSON frente a `clave=valor`.** Se eligió `clave=valor`: es el formato del ejemplo de la guía, se edita a mano y se
  valida línea por línea.
- **`time.sleep` en las pruebas frente a un reloj inyectable.** Con el reloj simulado, las pruebas de tiempo son
  rápidas y siempre dan lo mismo.

### 3.8 ¿Cómo demostraría que el sistema se recupera de un error?

Con la aplicación abierta (`./iniciar.sh`):
1. `python3 tools/escribir_dato.py --sin-validar temp_agua=abc`: en `errores.log` aparece
   `dato_invalido temp_agua entrada="abc"` y el tablero sigue con el último valor válido.
2. `python3 tools/escribir_dato.py temp_agua=95`: en `eventos.log` aparece `valor_actualizado temp_agua=95`, sin
   reiniciar.
3. `mv datos/vehiculo.conf /tmp/`: aparece ERROR `archivo_inexistente` y el tablero sigue.
4. `mv /tmp/vehiculo.conf datos/`: aparece INFO `archivo_recuperado`.

Pruebas que lo respaldan: P05, P07 y P10 (CP-95, CP-97, CP-100). Ejemplo real:
`docs/evidencias/bitacoras/con_errores/`.

## 4. Otras preguntas probables

- **Productor y consumidor.**
  - Productor externo: el simulador o quien escribe el archivo (otro proceso).
  - Productor interno: el hilo lector.
  - Consumidor: el hilo de la interfaz.
  - Datos que viajan: una copia completa de los 10 valores.
  - Dirección: archivo → lector → buzón → interfaz.
- **¿Por qué un buzón de tamaño 1?** Al tablero solo le importa el dato más reciente. Si la interfaz se atrasa, se
  descarta el viejo, así la memoria no crece.
- **¿Qué es la histéresis?** Dos umbrales distintos para encender y apagar una advertencia. Evitan el parpadeo cuando
  el valor oscila en el límite. Pruebas: CP-14, CP-15, CP-27.
- **¿Por qué el testigo 10 parpadea con el motor apagado?** R08 no lo condiciona al motor y es crítico (decisión D1).
  Se rechazó el defecto DEF-01 al revisar la especificación (`docs/registro_defectos.md`).
- **¿Cómo prueban la interfaz sin pantalla?** Con Xvfb, una pantalla virtual. Las pruebas abren la ventana real y leen
  el color del dibujo.
- **¿Qué permisos usan?** 640 para bitácoras y datos (dueño lee y escribe, grupo lee, otros nada) y 750 para la carpeta
  de logs. Es mínimo privilegio.
- **¿Qué pasa si la configuración está mal?** Se usa el valor por defecto y se registra el error
  (`configuracion valor_invalido`); la aplicación sigue (CP-106).

## 5. Guion de la demostración (sección 9 de la guía, 20–25 min)

| Momento | Qué hacer | Qué decir |
|---|---|---|
| 1 Contexto | README; tabla de elementos | Ferrari F40 1987; los 10 elementos y sus categorías |
| 2 Arquitectura | `docs/diagramas/arquitectura.png` | Entrada, validación, modelo, interfaz, registro; hilo + buzón |
| 3 Operación normal | `./iniciar.sh`; luego `tools/escribir_dato.py motor=1 velocidad=120 rpm=3000` | Se actualiza sin reiniciar; `tail -f logs/eventos.log` |
| 4 Advertencias | `escribir_dato.py direccional=izquierda` (informativo) y `falla_frenos=1` (seguridad) | WARN prioritario en `eventos.log` |
| 5 Error controlado | `--sin-validar temp_agua=abc`; mover el archivo | Se rechaza, se registra y se conserva el último valor |
| 6 Evidencia | `tail logs/errores.log`, `wc -l logs/*.log` | Bitácoras separadas con fecha, nivel y componente |
| 7 Conocimientos | Sección 3 de esta guía | Comunicación, sincronización, memoria, seguridad |
| 8 Cierre | Informe técnico §10 | Limitaciones y mejoras |

Como alternativa, `python3 tools/simulador.py` en otra terminal muestra el recorrido completo.

## 6. Glosario

- **Escritura atómica:** escribir en un temporal y renombrar; nadie ve el archivo a medias.
- **Productor/consumidor:** una actividad genera datos y otra los usa, comunicadas por una cola.
- **Condición de carrera:** el resultado depende de qué hilo llega primero; se evita con un solo dueño por recurso.
- **Espera activa:** un bucle que pregunta sin parar; se evita con `Event.wait` y `after()`.
- **Rotación de bitácoras:** renombrar y descartar archivos viejos al llegar a un tamaño.
- **Mínimo privilegio:** dar solo los permisos necesarios.
- **Histéresis:** umbrales distintos para entrar y salir de un estado.
- **Xvfb:** servidor gráfico virtual.

## 7. Para practicar

Expliquen en voz alta, sin ver las respuestas:
1. Qué pasa, paso a paso, desde que se escribe `rpm=8200` hasta que la aguja se pone roja y aparece el WARN.
2. Por qué el buzón tiene tamaño 1 y qué pasaría con una lista que crece.
3. Qué ve el usuario si la presión de aceite oscila entre 0.9 y 1.1 bar.
4. Qué pasa si alguien hace `chmod 666 datos/vehiculo.conf`.
5. Cómo saben que la prueba concurrente sí detectaría una lectura parcial.
