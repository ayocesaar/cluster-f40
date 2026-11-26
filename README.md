# Clúster F40 simulado

Simulador del clúster de instrumentos del **Ferrari F40 (1987)**, con una interfaz inspirada en el cuadro del F40 (capota negra, esferas negras con numerales de época, odómetro de tambor), para el proyecto
final de Sistemas Operativos (UAG), Equipo 3. Los diecisiete elementos (diez de la especificación original, el odómetro y seis adicionales) se controlan con **datos externos** (un archivo que
el tablero relee sin reiniciar); los eventos y los errores se registran en **bitácoras separadas**. Los rangos y
umbrales son parámetros didácticos, no calibraciones oficiales del F40.

## Requisitos

- Python 3.10 o superior con Tkinter. La aplicación solo usa la biblioteca estándar.
- Para las pruebas y los informes: `pip install -r requirements.txt`. En Linux sin pantalla también `xvfb`, y para el
  PDF `libreoffice-writer-nogui`.

**Windows:** instala Python desde https://www.python.org/downloads/ (marca "Add python.exe to PATH"). Evita el de
Microsoft Store: su Tcl/Tk a veces no puede leer sus propios archivos.
**Ubuntu:** `sudo apt-get install -y python3-tk python3-venv`.

## Ejecución

| Sistema | Orden |
|---|---|
| Linux / macOS | `./iniciar.sh` (o `bash abrir_cluster.sh`) |
| Windows | doble clic en `abrir_cluster.bat` |
| Modo manual (controles de la ventana) | `./iniciar.sh --manual` |

Con la aplicación abierta, cambia los valores **sin reiniciar**:

```bash
python3 tools/escribir_dato.py motor=1 velocidad=120 rpm=8200 direccional=izquierda   # escritura atómica
python3 tools/simulador.py                                                            # recorrido automático (otro proceso)
python3 tools/escribir_dato.py --sin-validar temp_agua=abc                            # provocar un error a propósito
```

También puedes editar `datos/vehiculo.conf` con cualquier editor; el tablero lo relee cada 100 ms.

Mira lo que pasa en las bitácoras:

```bash
tail -f logs/eventos.log
tail -f logs/errores.log
wc -l logs/eventos.log logs/errores.log
```

## Estructura

```
cluster-f40/
├── main.py, iniciar.sh, abrir_cluster.sh, abrir_cluster.bat   # arranque
├── config/cluster.ini      # rutas, intervalos, rangos y rotación de bitácoras
├── datos/vehiculo.conf     # entrada modificable (clave=valor)
├── datos/odometro.txt      # generado: kilometraje; su respaldo es odometro.txt.bak
├── logs/                   # eventos.log y errores.log (se crean al ejecutar)
├── logic/                  # modelo: estado.py (reglas R01-R08), reloj.py y odometro.py
├── sistema/                # config.py, lector.py (hilo + buzón), bitacora.py, monitor.py, odometro_archivo.py
├── ui/                     # presentacion.py y tablero.py (Tkinter, cuadro estilo F40)
├── aceptacion/             # ejecutor de escenarios de aceptación
├── tests/                  # pruebas (P01-P12 en test_sistema.py) y datos de prueba
├── tools/                  # simulador, escribir_dato, métricas, capturas, trazabilidad
├── docs/                   # evidencias, bitácoras de ejemplo, diagramas, matriz, registro de defectos
├── informe/                # Informe técnico e Informe de pruebas (PDF y Word) y sus generadores
└── estudio/                # material de estudio para la demostración
```

## Elementos del tablero

| N.º | Elemento | Categoría | Clave en `datos/vehiculo.conf` |
|---|---|---|---|
| 1 | Velocímetro | Indicador principal | `velocidad` (0–360 km/h) |
| 2 | Presión de aceite | Información en línea | `presion_aceite` (0–10 bar) |
| 3 | Tacómetro | Información en línea | `rpm` (0–9000, entero) |
| 4 | Temperatura de agua | Indicador principal | `temp_agua` (40–130 °C) |
| 5 | Presión de turbo | Información en línea | `presion_turbo` (0–2 bar) |
| 6 | Direccionales | Testigo informativo | `direccional` (off, izquierda, derecha) |
| 7 | Luces altas | Testigo informativo | `luces_altas` (0/1) |
| 8 | Intermitentes | Testigo informativo | `emergencia` (0/1) |
| 9 | Baja presión de aceite | Testigo de seguridad | calculado de `presion_aceite` |
| 10 | Falla de frenos | Testigo de seguridad | `falla_frenos` (0/1) |
| 11 | Odómetro | Información en línea | calculado (`odometro=` se rechaza) |
| 12 | Puerta abierta (adicional) | Testigo informativo | `puertas` (bits: 1 conductor, 2 pasajero; 0–3) |
| 13 | Cinturón (adicional) | Testigo de seguridad | `cinturon` (1 = abrochado) |
| 14 | Combustible (adicional) | Información en línea | `combustible` (0–100 % de 120 L) |
| 15 | Protección del motor (adicional) | Testigo de seguridad | `falla_motor` (ninguna, sobretemperatura, sobrepresion_turbo, aceite, combustible, electrica) |
| 16 | Carga de batería (adicional) | Testigo de seguridad | `voltaje` (0–20 V) |
| 17 | Temperatura de aceite (adicional) | Información en línea | `temp_aceite` (0–160 °C) |

El motor se enciende con `motor=1`. Las claves de los elementos 12–15 y `contacto` (llave) son **opcionales**: un
archivo con solo las diez claves originales funciona igual que antes (decisión D8). Ver
[docs/realismo_y_liberacion.md](docs/realismo_y_liberacion.md).

## Odómetro (elemento 11)

Se agregó tras la práctica "Diseño y ejecución supervisada de pruebas" (categoría: información en línea, lectura
continua). Su defecto, DEF-03, se cerró en la Etapa 13.

- **Muestra:** entero de 6 dígitos, de 000000 a 999999 km. Tras 999999 vuelve a 000000 (el sistema cuenta las
  vueltas) y nunca disminuye. Internamente guarda la fracción de km.
- **Cálculo:** en cada tick (50 ms) suma velocidad (km/h) × tiempo transcurrido (h). Solo avanza con motor encendido
  y velocidad mayor que 0; con motor apagado (R01) no avanza.
- **Pantalla:** caja de 6 dígitos dentro del velocímetro, con la etiqueta "11 ODOMETRO KM".
- **Persistencia:** `datos/odometro.txt`, con respaldo en `datos/odometro.txt.bak`. Escritura atómica (temporal,
  `fsync` y `os.replace`) y permisos 640. Se guarda cada 5 s y al cerrar la aplicación. Ambos archivos están en
  `.gitignore`.
- **Configuración:** `config/cluster.ini`, sección `[odometro]`, clave `guardar_cada_s` (rango 1–3600).
- **Al iniciar:** si `odometro.txt` es válido, se usa (INFO `odometro_cargado`). Si no, se usa el respaldo (WARN
  `odometro_restaurado` y el aviso "Odometro restaurado del respaldo: 000062 km"). Si ninguno sirve, inicia en 000000
  con ERROR `odometro_invalido` u `odometro_inexistente` y el aviso "Odometro: archivo invalido, se inicio en 000000".
  En el primer arranque, sin archivos, solo registra INFO `odometro_nuevo`.
- **Archivo inválido:** se rechaza si es escribible por cualquiera (o+w), pesa más de 64 bytes, no es UTF-8 o no es un
  número (hasta 6 dígitos y hasta 6 decimales).
- **Clave `odometro=`:** en `datos/vehiculo.conf` se rechaza con ERROR `clave_no_permitida`, porque el kilometraje lo
  calcula el sistema. El resto de las claves sí se aplican.
- **Si no se puede guardar** (disco lleno, por ejemplo): ERROR `odometro_no_guardado` y el sistema sigue.
- **Pruebas:** `tests/test_odometro.py` (CP-120 a CP-137).

## Pruebas

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
xvfb-run -a python -m pytest -v                       # todas las pruebas (en Windows: python -m pytest -v)
xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv
xvfb-run -a python tools/ejecucion_prolongada.py --duracion-s 60    # P12 con métricas reales
```

Evidencias: `docs/evidencias/` (resultados, cobertura, capturas, bitácoras de ejemplo y métricas). Informes:
`informe/Informe_Tecnico_Cluster_F40.pdf` e `informe/Informe_Pruebas_Cluster_F40.pdf`.

## Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| El tablero no cambia al editar el archivo | Se abrió con `--manual`, o el valor es inválido | Revisa `logs/errores.log`; abre sin `--manual` |
| `permisos_inseguros` en `errores.log` | `datos/vehiculo.conf` es escribible por cualquiera | `chmod 640 datos/vehiculo.conf` |
| `archivo_inexistente` en `errores.log` | Se borró o movió el archivo de datos | Restáuralo; el tablero se recupera solo |
| `no display name and no $DISPLAY` | Linux sin pantalla | Antepón `xvfb-run -a` |
| En Windows: `Can't find a usable init.tcl` | Python de Microsoft Store | Instala Python de python.org |

## Panel de control (atajo de la terminal)

`./abrir_panel.sh` (o `python panel_admin.py`) abre un panel administrador que sustituye los comandos de la terminal:

- **Cabina austera estilo F40:** pedales de aluminio perforado (embrague, freno, acelerador), compuerta de cambios y llave de contacto. Una física simplificada (`panel/fisica.py`) convierte pedales y marcha en velocidad, RPM, turbo con retraso, presión de aceite y temperatura coherentes. Las cifras son aproximadas y no oficiales.
- **Luces y fallas de sensores:** altas, direccionales, intermitentes; fuga de aceite (R02), radiador (R04), sobrepresión (R05), falla de frenos (R08).
- **Entradas inválidas:** dato corrupto, fuera de rango, archivo borrado y permisos 666; el panel restaura datos válidos a los 3 s.
- **Atajos:** pruebas, aceptación, fuzzing, caos, P12, diagnóstico, hilos y memoria del tablero, con la salida en una consola.
- **Escenarios en vivo:** reproduce CA-01 a CA-10 (el mismo CSV de las pruebas de aceptación) sobre el tablero real, paso a paso.
- **Abrir/cerrar tablero:** lanza `main.py` y lo cierra con SIGTERM (cierre ordenado).

El panel es un proceso aparte que escribe `datos/vehiculo.conf` con el mismo candado y la escritura atómica de `tools/escribir_dato.py`: el tablero no cambia. Pruebas: `tests/test_panel.py` (CP-155 a CP-162).

## Realismo y seguridad (Etapa 18)

- **Llave y arranque separados:** `K` pone o quita el contacto (el tablero hace la prueba de testigos de 2 s) y `M`
  arranca o apaga. Con contacto y motor apagado, el velocímetro, el agua y el odómetro siguen midiendo; RPM, aceite
  y turbo quedan en 0 (D3).
- **Puertas y cinturón:** `P`/`O` abren las puertas y `B` abrocha el cinturón. Con una puerta abierta el auto **no
  avanza** aunque se acelere (interbloqueo) y en movimiento el testigo 12 parpadea en rojo.
- **Fallas con consecuencias reales** (las decide la ECU simulada, `panel/ecu.py`):

| Falla | Consecuencia | Se repara en TALLER con |
|---|---|---|
| Fuga de aceite | Testigo 9; **no arranca**; en marcha vacía el depósito y la ECU corta el motor | Reparar fallas + Rellenar aceite |
| Radiador | Agua en rojo; a 120 °C la ECU **detiene el motor** y no deja arrancar hasta enfriar bajo 100 °C | Reparar fallas |
| Turbo (válvula de descarga) | Más de 1.5 bar durante 1 s: **corte del motor** enclavado | Reparar fallas |
| Frenos | Testigo 10 y el auto **frena al 30 %**; los frenos calientes pierden eficiencia | Reparar fallas |
| Velocímetro | Indica 5 % menos que la velocidad real (ilegal según UN R39) | Reparar fallas |
| Sin combustible | El motor se apaga y no arranca | Llenar tanque |

- **Banco de liberación de producción** (pruebas de la época): `python3 tools/banco_liberacion.py` corre 9 pruebas
  (frenado tipo 0 y tipo I de UN R13-H, velocímetro UN R39, ciclo urbano ECE-15 con el odómetro, prueba de
  testigos, arranque, enfriamiento, turbo y puertas) y da el dictamen **APTO PARA PRODUCCIÓN** o **RECHAZADO**.
  `--falla frenos` inyecta una falla; `--evidencia` guarda la matriz falla → prueba en
  `docs/evidencias/banco_liberacion.txt`. Desde el panel: "Banco con las fallas actuales" y "Ciclo ECE-15 en vivo".
- Pruebas: `tests/test_realismo.py` y `tests/test_liberacion.py` (CP-163 a CP-183). Fuentes y lo que queda
  pendiente de verificar: [docs/realismo_y_liberacion.md](docs/realismo_y_liberacion.md).

## Sonido del motor (Etapa 19)

El panel genera por código el sonido del motor (`panel/sonido.py`: pulsos de combustión de un V8, 4 por vuelta).
El sonido sigue las rpm, la carga, el turbo (silbido y descarga), el limitador, el arranque y la alarma del cinturón
(4 a 8 s, FMVSS 208 S7.3). No usa grabaciones ni audio de terceros.

- En el mismo equipo: `./abrir_panel.sh --sonido auto` (Windows: waveOut; Linux: `aplay`, que en la VM requiere
  `sudo apt-get install -y alsa-utils` y `sudo usermod -aG audio $USER`).
- Panel en la VM y bocinas en Windows: en Windows `python tools\bocina.py`, y el panel con un túnel inverso:
  `ssh -Y -R 5055:127.0.0.1:5055 -p 2222 USUARIO@127.0.0.1 "cd ~/cluster-f40 && ./abrir_panel.sh --sonido 127.0.0.1:5055"`.
- `U` silencia. Demostración sin VM: `docs/evidencias/sonido/motor_demo.wav` (la genera `tools/sonido_demo.py`).
- Detalle, latencia y seguridad: [docs/sonido_motor.md](docs/sonido_motor.md). Pruebas: `tests/test_sonido.py`
  (CP-184 a CP-190).

## Caja negra, sistema eléctrico y Weber-Marelli (Etapa 20)

- **Caja negra** (`sistema/caja_negra.py`): `datos/caja_negra.bin` guarda los últimos 60 s a 10 Hz en un anillo
  binario de tamaño fijo (19 264 bytes) con **acceso directo** (registro k en el byte 64 + (k mod 600) × 32) y CRC por
  registro. Ante un testigo crítico exporta los 10 s previos a `logs/caja_negra/`. Leerla:
  `python3 tools/caja_negra.py --hex 1`. Formato completo: [docs/caja_negra.md](docs/caja_negra.md).
- **Batería y alternador:** testigo 16 con voltímetro. Con la falla del alternador la batería se descarga (60 veces
  más rápido, para la demostración) y bajo 10.5 V la gestión electrónica se apaga; con la batería débil el motor de
  arranque gira lento y no prende. TALLER: "Cargar batería" y "Batería débil 6 %".
- **Falla de una unidad Weber-Marelli:** el F40 tiene una por banco de cilindros; con una fallando el motor sigue con
  4 cilindros (medio empuje, un turbo, ralentí irregular) y suena cojo. Sin testigo, como en 1987.
- **Sonidos de cabina:** relevador de las direccionales, chirrido de llantas y ventilador del radiador.
- Pruebas: `tests/test_caja_negra.py` y `tests/test_electrico.py` (CP-191 a CP-202).

## Prácticas de fallas y física del F40 (Etapa 21)

- **15 botones de prácticas** en el panel (manejo normal, fuga de aceite, sobrecalentamiento, turbo, frenos, puertas,
  cinturón, combustible, alternador, batería débil, Weber-Marelli, limitador, lluvia sin ABS, 0-100 km/h y
  velocímetro). Cada una corre sola: la palanca, los pedales y las casillas se mueven como los movería una persona,
  el tablero lo muestra en vivo y la consola dice si aprobó. En la terminal: `python3 tools/practicas.py`.
- **Física:** curva de par con los datos verificados (577 Nm a 4000 rpm, 478 CV a 7000 rpm) y retraso del turbo;
  calibrada con el 0-100 y la velocidad máxima publicados. Sin ABS ni control de tracción, como el F40 original:
  las llantas patinan y se bloquean, sobre todo con **Pista mojada [Y]**.
- **Elemento 17, temperatura de aceite** (el F40 tiene este medidor) y **agujas con inercia** de instrumento analógico.
- Detalle y fuentes: [docs/practicas_de_fallas.md](docs/practicas_de_fallas.md). Pruebas: `tests/test_practicas.py`
  (CP-203 a CP-209).

## Observación del sistema (guía, sección 6)

```bash
ps -o pid,ppid,stat,%cpu,%mem,rss,vsz,cmd -p $(pgrep -f main.py)
watch -n 1 "du -h logs/*.log"
tail -f logs/eventos.log
wc -l logs/eventos.log logs/errores.log
```

En el panel, el atajo "ps du wc" corre `ps`, `du` y `wc` sobre el tablero en ejecución (lista de argumentos, sin shell).

## Dependencias y licencias

La aplicación solo usa la biblioteca estándar de Python y Tkinter (Tcl/Tk 8.6). Las pruebas y los informes usan los
paquetes de `requirements.txt`; su licencia, tomada de los metadatos instalados, queda en
`docs/evidencias/licencias.txt` (la genera `tools/licencias.py`). Herramientas del sistema: Xvfb (pantalla virtual
para las pruebas) y LibreOffice (conversión a PDF). El proyecto no usa imágenes, fuentes ni sonidos de terceros: todo
el dibujo se hace con primitivas de Tkinter y no hay logotipos de la marca.

## Temas de la materia en el proyecto

- `estudio/05_mapa_de_la_materia.md` (y su PDF): cada tema del programa contra el proyecto, con su evidencia o la razón por la que no aplica.
- `xvfb-run -a bash tools/evidencia_so.sh`: genera en `docs/evidencias/so/` salidas reales de strace, inodos, hexdump, procesos e hilos, `/proc`, señales, candados y permisos.
- `bash tools/diagnostico.sh logs`: analizador de bitácoras en Bash (cuenta eventos, clasifica el estado y escribe un reporte).
- Cerrar con `kill PID` o Ctrl+C también es un cierre ordenado: guarda el kilometraje y registra el fin.

## Material de estudio

La carpeta [estudio/](estudio/) tiene la guía del profesor, cómo abrir el proyecto en la máquina virtual, la guía de
estudio para la demostración y el estado de cumplimiento de la guía.
