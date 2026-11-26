# Hoja de comandos — Clúster F40

Equipo 3 · Sistemas Operativos (UAG) · Máquina virtual `ubuntuserver` (Ubuntu 22.04), usuario `ayocesaar`, proyecto en `~/cluster-f40`.

**(VM)** se escribe en la terminal de la VM (`ayocesaar@ubuntuserver:~/cluster-f40$`). **(Windows)** se escribe en una PowerShell de Windows (`PS C:\Users\W11>`).

## 0. Panel de control (todo lo de esta hoja con botones)

**(Windows)** Abrir el panel desde la VM (con el servidor de ventanas abierto, sección 1):

```
$env:DISPLAY = "127.0.0.1:0.0"
ssh -Y -p 2222 ayocesaar@127.0.0.1 "cd ~/cluster-f40 && ./abrir_panel.sh"
```

En el panel: **Abrir tablero**, **LLAVE** (K: contacto y prueba de testigos), **ARRANQUE** (M), marcha (1-5), acelerador (W) y freno (S). Puertas (P y O), cinturón (B), fallas, **TALLER**, entradas inválidas, escenarios CA-01 a CA-10, el **banco de liberación**, el **ciclo ECE-15 en vivo** y las pruebas también tienen botones.

**Con sonido del motor** (Windows, dos PowerShell): en la primera, la bocina; en la segunda, el panel con el túnel de sonido.

```
cd C:\Users\W11\cluster-f40
python tools\bocina.py
```

```
$env:DISPLAY = "127.0.0.1:0.0"
ssh -Y -R 5055:127.0.0.1:5055 -p 2222 ayocesaar@127.0.0.1 "cd ~/cluster-f40 && ./abrir_panel.sh --sonido 127.0.0.1:5055"
```

La barra del panel dice "bocina ... (conectada)". `U` silencia. Para oírlo sin la VM: `docs\evidencias\sonido\motor_demo.wav`.

## 1. Conexión y arranque

**(Windows)** Encender la VM, solo si está apagada:

```
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm ubuntuserver --type headless
```

**(Windows)** Abrir el servidor de ventanas. Hace falta para ver el tablero y basta una vez por sesión:

```
& "C:\Program Files\VcXsrv\vcxsrv.exe" :0 -multiwindow -clipboard -wgl
```

**(Windows)** Abrir el tablero desde la VM, que se ve en Windows:

```
$env:DISPLAY = "127.0.0.1:0.0"
ssh -Y -p 2222 ayocesaar@127.0.0.1 "cd ~/cluster-f40 && ./iniciar.sh"            # modo archivo (normal)
ssh -Y -p 2222 ayocesaar@127.0.0.1 "cd ~/cluster-f40 && ./iniciar.sh --manual"   # con los controles de la ventana
```

**(Windows)** Abrir una terminal en la VM:

```
ssh -p 2222 ayocesaar@127.0.0.1
```

**(VM)** Entrar al proyecto y activar el entorno, siempre al empezar:

```
cd ~/cluster-f40
source .venv/bin/activate
```

## 2. Pruebas automatizadas (VM)

```
xvfb-run -a python -m pytest -q                         # todas las pruebas
xvfb-run -a python -m pytest -v                         # todas, con el nombre de cada una
xvfb-run -a python -m pytest tests/test_odometro.py -v  # solo el odómetro (CP-120 a CP-137)
xvfb-run -a python -m pytest -k cp98 -v                 # una prueba por su número (ej. CP-98)
xvfb-run -a python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv   # aceptación
```

Cobertura de líneas y ramas:

```
xvfb-run -a python -m coverage run --branch -m pytest -q
python -m coverage report -m
```

## 3. Cambiar datos en vivo con el tablero abierto (VM)

| Clave | Valores válidos |
|---|---|
| motor, luces_altas, emergencia, falla_frenos | 0 o 1 |
| velocidad | 0 a 360 km/h |
| rpm | 0 a 9000, entero |
| presion_aceite | 0 a 10 bar |
| temp_agua | 40 a 130 °C |
| presion_turbo | 0 a 2 bar |
| direccional | off, izquierda, derecha |

```
# Encender y manejar (R01); el odómetro empieza a contar
python tools/escribir_dato.py motor=1 velocidad=120 rpm=3000 presion_aceite=5 temp_agua=90 presion_turbo=0.8

# R03 tacómetro: rojo desde 8000; sigue rojo en 7900 (histéresis); normal en 7799
python tools/escribir_dato.py rpm=8200
python tools/escribir_dato.py rpm=7900
python tools/escribir_dato.py rpm=7799

# R04 temperatura: rojo arriba de 110; normal en 105 o menos
python tools/escribir_dato.py temp_agua=115
python tools/escribir_dato.py temp_agua=105

# R05 turbo: contorno ámbar arriba de 1.5; normal en 1.4 o menos
python tools/escribir_dato.py presion_turbo=1.6
python tools/escribir_dato.py presion_turbo=1.4

# R02 aceite: medidor ámbar al instante y testigo 9 rojo tras 1 s; se apaga 1 s después de 1.2 bar
python tools/escribir_dato.py presion_aceite=0.5
python tools/escribir_dato.py presion_aceite=1.2

# R06 y R07: direccional verde, luces altas azul, emergencia ámbar con prioridad sobre el direccional
python tools/escribir_dato.py direccional=izquierda
python tools/escribir_dato.py luces_altas=1
python tools/escribir_dato.py emergencia=1
python tools/escribir_dato.py emergencia=0 direccional=off luces_altas=0

# R08 frenos: rojo parpadeando cada 300 ms, también con el motor apagado
python tools/escribir_dato.py falla_frenos=1
python tools/escribir_dato.py motor=0
python tools/escribir_dato.py falla_frenos=0

# Recorrido automático
python tools/simulador.py --duracion-s 30
```

## 4. Errores controlados (VM)

El tablero no se detiene, conserva el último valor válido y registra el error en logs/errores.log.

```
python tools/escribir_dato.py --sin-validar temp_agua=abc    # formato inválido
python tools/escribir_dato.py --sin-validar velocidad=400    # fuera de rango
python tools/escribir_dato.py --sin-validar rpm=4500.5       # rpm con decimales

echo "odometro=999999" >> datos/vehiculo.conf                # se rechaza con clave_no_permitida
sed -i '/^odometro=/d' datos/vehiculo.conf                   # quitarlo

mv datos/vehiculo.conf /tmp/                                 # archivo inexistente
mv /tmp/vehiculo.conf datos/                                 # se recupera sin reiniciar

chmod 666 datos/vehiculo.conf                                # permisos inseguros: se rechaza
chmod 640 datos/vehiculo.conf                                # restaurar
```

## 5. Bitácoras (VM)

```
tail -f logs/eventos.log logs/errores.log    # en vivo (Ctrl+C para salir)
tail -n 20 logs/eventos.log                  # últimos eventos
cat logs/errores.log                         # errores
grep odometro logs/eventos.log               # solo el odómetro
ls -l logs/                                  # permisos 640 y rotación
```

Comandos de observación de la guía (sección 6), con el tablero abierto:

```
ps -o pid,ppid,stat,%cpu,%mem,rss,vsz,cmd -p $(pgrep -f main.py)   # proceso: estado, CPU, memoria
watch -n 1 "du -h logs/*.log"                                         # tamaño de bitácoras cada segundo
wc -l logs/eventos.log logs/errores.log                               # líneas de eventos y de errores
grep WARN logs/eventos.log                                            # advertencias prioritarias
```

## 5a. Caja negra (VM)

```
python tools/caja_negra.py                       # cabecera y últimos registros (solo lectura)
python tools/caja_negra.py --hex 1               # el último registro byte por byte con sus campos
python tools/caja_negra.py --ultimos 100 --csv /tmp/ultimos.csv
ls -l datos/caja_negra.bin logs/caja_negra/      # 19264 bytes fijos; eventos CSV (640)
xxd -l 64 datos/caja_negra.bin                   # la cabecera en hexadecimal
python tools/escribir_dato.py voltaje=12.3       # con el motor en marcha: WARN falla_de_carga (R13)
```

## 5c. Prácticas de fallas (VM)

En el panel, los 15 botones de **PRACTICAS DE FALLAS** corren cada caso solo. Desde la terminal:

```
python tools/practicas.py                        # las 15 en tiempo simulado (docs/evidencias/practicas.txt)
python tools/practicas.py --practica lluvia      # una sola
python tools/escribir_dato.py temp_aceite=135    # elemento 17 en rojo (R14)
```

## 5b. Realismo, seguridad y banco de liberación (VM)

```
python tools/escribir_dato.py contacto=1                     # llave: prueba de testigos de 2 s
python tools/escribir_dato.py motor=1 puertas=1              # testigo 12 (puerta del conductor)
python tools/escribir_dato.py velocidad=40                   # puerta abierta en movimiento: WARN
python tools/escribir_dato.py puertas=0 cinturon=0           # testigo 13 (cinturón sin abrochar)
python tools/escribir_dato.py combustible=8                  # reserva (R11): WARN combustible_reserva
python tools/escribir_dato.py falla_motor=sobretemperatura   # testigo 15 STOP (R12)
python tools/escribir_dato.py motor=1 contacto=0             # dato_inconsistente en errores.log
python tools/banco_liberacion.py                             # 9 pruebas: APTO PARA PRODUCCION
python tools/banco_liberacion.py --falla frenos              # RECHAZADO: L02, L03 y L04
python tools/banco_liberacion.py --evidencia                 # matriz falla -> prueba (docs/evidencias)
xvfb-run -a python -m pytest -q tests/test_realismo.py tests/test_liberacion.py   # CP-163 a CP-183
```

## 6. Odómetro (VM)

Estas pruebas se hacen con el tablero cerrado, porque al cerrarse guarda el kilometraje. Después se vuelve a abrir con el comando de la sección 1.

```
cat datos/odometro.txt                                  # kilometraje guardado (respaldo: datos/odometro.txt.bak)

echo 62 > datos/odometro.txt                            # iniciar en 000062, como el F40 real
#   abrir el tablero y: python tools/escribir_dato.py motor=1 velocidad=120
#   en unos 30 s cambia a 000063 y eventos.log registra odometro_actualizado

echo 999999.5 > datos/odometro.txt                      # vuelta a cero
#   abrir el tablero y: python tools/escribir_dato.py motor=1 velocidad=360
#   en unos 5 s pasa a 000000 (vuelta_a_cero en eventos.log)

echo abc > datos/odometro.txt; rm -f datos/odometro.txt.bak   # archivo corrupto
#   al abrir: 000000, aviso en pantalla y ERROR odometro_invalido
```

Casos de la práctica con la aplicación completa (unos 2 minutos):

```
xvfb-run -a -s "-screen 0 1280x1024x24" python practica/ejecutar_casos.py --version despues
cat practica/evidencia_despues/resumen.txt
```

## 7. Evidencias y documentos (VM)

Estos comandos regeneran archivos que están en el repositorio. Para regresar a lo que está guardado en git: git restore .

```
xvfb-run -a -s "-screen 0 1280x1024x24" python tools/capturas.py              # 8 capturas del tablero
python tools/demo_bitacoras.py                                                 # bitácoras de ejemplo
xvfb-run -a python tools/ejecucion_prolongada.py --duracion-s 60 --salida /tmp/metricas.txt   # P12 (no toca el repo)
python tools/trazabilidad.py                                                   # matriz de trazabilidad
python informe/generar_documento_pruebas.py                                    # Documento de Pruebas (PDF y DOCX)
python informe/generar_catalogo_pruebas.py                                     # catálogo con todas las pruebas
python informe/generar_informe_tecnico.py                                      # informe técnico
python informe/generar_informe.py                                              # informe de pruebas
```

## 8. Repositorio y apagado (VM)

```
git log --oneline | head -5     # últimos commits
git status                      # cambios sin guardar
sudo shutdown now               # apagar la VM (pide contraseña)
```

Para cerrar el tablero basta con cerrar su ventana: registra "sistema fin" y guarda el kilometraje.
