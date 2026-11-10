# Clúster F40 simulado

Simulador del clúster de instrumentos del **Ferrari F40 (1987)**, con interfaz de estética 8-bit, para el proyecto
final de Sistemas Operativos (UAG), Equipo 3. Los diez elementos se controlan con **datos externos** (un archivo que
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
├── logs/                   # eventos.log y errores.log (se crean al ejecutar)
├── logic/                  # modelo: estado.py (reglas R01-R08) y reloj.py
├── sistema/                # config.py, lector.py (hilo + buzón), bitacora.py, monitor.py
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

El motor se enciende con `motor=1`.

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

## Material de estudio

La carpeta [estudio/](estudio/) tiene la guía del profesor, cómo abrir el proyecto en la máquina virtual, la guía de
estudio para la demostración y el estado de cumplimiento de la guía.
