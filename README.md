# Clúster F40 simulado

Clúster de instrumentos simulado del Ferrari F40 (1987), con interfaz de estética 8-bit, para la materia de
Sistemas Operativos (UAG), Equipo 3. Los rangos y umbrales son parámetros didácticos de la especificación del
curso, no calibraciones oficiales del F40.

## Abrir la aplicación

Solo necesita Python 3.10 o superior con Tkinter; la aplicación no usa otras bibliotecas.

**Windows**
1. Instala Python desde https://www.python.org/downloads/ (marca "Add python.exe to PATH"). El instalador ya
   incluye Tkinter. Se recomienda este instalador y no el de Microsoft Store, cuya versión de Tcl/Tk a veces no
   puede leer sus propios archivos.
2. Doble clic en `abrir_cluster.bat` (o, en una terminal dentro de esta carpeta: `py main.py`).

**Ubuntu / Linux**
1. `sudo apt-get install -y python3-tk`
2. `bash abrir_cluster.sh` (o `python3 main.py`).

**macOS**
1. Instala Python desde https://www.python.org/downloads/ (incluye Tkinter).
2. `bash abrir_cluster.sh`.

## Controles

- 5 deslizadores: velocidad, presión de aceite, RPM, temperatura de agua y presión de turbo.
- 4 interruptores: motor, luces altas, emergencia y falla de frenos.
- Selector de direccional: IZQ / OFF / DER.

## Elementos del tablero

| N.º | Elemento | Dónde está |
|---|---|---|
| 1 | Velocímetro | Esfera grande izquierda |
| 2 | Presión de aceite | Medidor chico superior izquierdo |
| 3 | Tacómetro | Esfera grande derecha |
| 4 | Temperatura de agua | Medidor chico inferior izquierdo |
| 5 | Presión de turbo | Medidor chico derecho (contorno ámbar sobre 1.5 bar) |
| 6 | Direccionales | Dentro del velocímetro, a la izquierda |
| 7 | Luces altas | Dentro del tacómetro |
| 8 | Intermitentes | Dentro del velocímetro, a la derecha |
| 9 | Baja presión de aceite (crítico) | Arriba, entre las esferas |
| 10 | Falla de frenos (crítico) | Arriba, entre las esferas |

## Pruebas

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
xvfb-run -a python -m pytest -v                  # Linux sin pantalla (en Windows: python -m pytest -v)
xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv
```

Las evidencias de cada ejecución, la matriz de trazabilidad, el registro de defectos y el informe
(`informe/Informe_Pruebas_Cluster_F40.pdf`) están en `docs/` e `informe/`.

## Material de estudio

La carpeta [estudio/](estudio/) tiene la guía del profesor, cómo abrir el proyecto en la máquina virtual, la guía de estudio para la demostración y el estado de cumplimiento de la guía.
