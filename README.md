# Clúster F40 simulado

Simulador del clúster de instrumentos del **Ferrari F40 (1987)**, con interfaz de estética 8-bit, para el proyecto
final de Sistemas Operativos (UAG), Equipo 3. Los once elementos (diez de la especificación original más el odómetro) se controlan con **datos externos** (un archivo que
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
├── ui/                     # presentacion.py y tablero.py (Tkinter 8-bit)
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

El motor se enciende con `motor=1`.

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

## Temas de la materia en el proyecto

- `estudio/05_mapa_de_la_materia.md` (y su PDF): cada tema del programa contra el proyecto, con su evidencia o la razón por la que no aplica.
- `xvfb-run -a bash tools/evidencia_so.sh`: genera en `docs/evidencias/so/` salidas reales de strace, inodos, hexdump, procesos e hilos, `/proc`, señales, candados y permisos.
- `bash tools/diagnostico.sh logs`: analizador de bitácoras en Bash (cuenta eventos, clasifica el estado y escribe un reporte).
- Cerrar con `kill PID` o Ctrl+C también es un cierre ordenado: guarda el kilometraje y registra el fin.

## Material de estudio

La carpeta [estudio/](estudio/) tiene la guía del profesor, cómo abrir el proyecto en la máquina virtual, la guía de
estudio para la demostración y el estado de cumplimiento de la guía.
