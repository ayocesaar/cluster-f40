# Cómo abrir el proyecto en la máquina virtual

## Datos de la máquina virtual de César

| Dato | Valor |
|---|---|
| Programa | VirtualBox |
| Nombre de la VM | `ubuntuserver` |
| Sistema | Ubuntu 22.04 Server (sin escritorio gráfico) |
| Usuario | `ayocesaar` |
| Carpeta del proyecto | `/home/ayocesaar/cluster-f40` |
| Acceso desde Windows | SSH por el puerto 2222 (regla NAT de VirtualBox: 2222 de Windows → 22 de la VM) |

## 1. Encender la VM

- Desde VirtualBox: selecciona `ubuntuserver` y pulsa **Iniciar**.
- O desde PowerShell, sin abrir la ventana de la VM:

```powershell
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm ubuntuserver --type headless
```

Espera alrededor de un minuto a que arranque Ubuntu.

## 2. Entrar por SSH

```powershell
ssh -p 2222 ayocesaar@127.0.0.1
```

- Usa `127.0.0.1` y no `localhost`: en este equipo `localhost` a veces se resuelve por IPv6 y la conexión se
  rechaza.
- Si dice **Connection refused**, la VM sigue arrancando: espera unos segundos y repite.

## 3. Entrar al proyecto y activar el entorno

```bash
cd ~/cluster-f40
source .venv/bin/activate
```

## 4. Correr las pruebas

La VM no tiene pantalla. `xvfb-run` crea una pantalla virtual para que las pruebas de la interfaz usen Tkinter
real.

```bash
xvfb-run -a python -m pytest -v                                          # 108 pruebas
xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv   # 10 escenarios
python -m coverage run --branch -m pytest -q && python -m coverage report -m        # cobertura (con xvfb-run delante)
```

Resultado esperado: todas las pruebas aprobadas (el número exacto está en `docs/evidencias/pytest.txt`) y
`Resumen: 10/10 escenarios aprobados`.

Evidencias que se pueden regenerar en la VM:

```bash
python tools/demo_bitacoras.py                                  # ejemplos de bitácoras (exitosa y con errores)
xvfb-run -a python tools/ejecucion_prolongada.py --duracion-s 60 # P12: métricas de memoria, intervalo y bitácoras
```

## 4b. Datos externos y bitácoras (para la demostración)

El tablero lee `datos/vehiculo.conf` cada 100 ms. Abre **dos terminales SSH**:

```bash
# Terminal 1: bitácoras en vivo
cd ~/cluster-f40 && tail -f logs/eventos.log logs/errores.log

# Terminal 2: cambiar datos sin reiniciar
cd ~/cluster-f40 && source .venv/bin/activate
python tools/escribir_dato.py motor=1 velocidad=120 rpm=8200
python tools/escribir_dato.py --sin-validar temp_agua=abc     # error controlado
python tools/simulador.py --duracion-s 30                      # recorrido automático
```

Para que esto haga algo, el tablero debe estar corriendo: `./iniciar.sh` en Windows o con X11 (sección 5).

## 5. Ver la ventana del tablero

Como la VM es Ubuntu **Server**, no puede mostrar ventanas por sí sola. Hay tres formas de ver el tablero:

**A. En Windows (probado).** Es la forma más simple para la demostración. En la copia del repositorio en
Windows, doble clic en `abrir_cluster.bat`. Necesita Python 3.10+ de python.org.

**B. Capturas desde la VM (probado).** Genera imágenes reales de la ventana en 8 estados:

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" python tools/capturas.py
ls docs/evidencias/capturas/
```

**C. La ventana de la VM mostrada en Windows por X11 (no probado en este equipo).**
1. En Windows instala **VcXsrv** y abre **XLaunch** con "Multiple windows", "Start no client" y marca
   "Disable access control".
2. En PowerShell:
   ```powershell
   $env:DISPLAY = "127.0.0.1:0.0"
   ssh -Y -p 2222 ayocesaar@127.0.0.1
   ```
3. Ya en la VM: `cd ~/cluster-f40 && ./iniciar.sh`.

## 6. Montar el proyecto en otra VM (la de Ian)

En una VM con Ubuntu 22.04 o más reciente:

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv python3-tk xvfb
git clone https://github.com/ayocesaar/cluster-f40.git
cd cluster-f40
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
xvfb-run -a python -m pytest -v
```

- El repositorio es **privado**: Ian necesita que César lo agregue como colaborador en GitHub (Settings →
  Collaborators) y, al clonar, iniciar sesión con su cuenta.
- Para generar el informe PDF también hace falta LibreOffice:
  `sudo apt-get install -y --no-install-recommends libreoffice-writer-nogui fonts-liberation`.

## 7. Apagar la VM

```bash
sudo shutdown now
```

## Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `Connection refused` al hacer SSH | La VM no termina de arrancar, o `localhost` se resolvió por IPv6 | Espera y usa `127.0.0.1` |
| `no display name and no $DISPLAY` | Se corrió algo gráfico sin pantalla | Antepón `xvfb-run -a` |
| Pruebas de interfaz `SKIPPED` | No hay servidor gráfico | Antepón `xvfb-run -a` |
| `ModuleNotFoundError: docx` | No se activó el entorno | `source .venv/bin/activate` |
| En Windows: `Can't find a usable init.tcl` | Python de Microsoft Store | Instalar Python desde python.org |
