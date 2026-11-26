# Sonido del motor (Etapa 19)

El equipo pidió el sonido del motor junto con la acción. Se decidió **generarlo por código** en
lugar de cortar audio de videos: YouTube no permite descargar sus videos y la guía pide indicar la
procedencia y la licencia de los recursos de terceros. Con la síntesis no hay recursos de terceros y
el sonido responde exactamente a lo que hace el modelo físico del panel.

El sonido es **aproximado**: no es una grabación del F40 ni se calibró contra uno.

## Cómo se genera (`panel/sonido.py`)

| Parte | Modelo | De qué depende |
|---|---|---|
| Explosiones | Un pulso por explosión: 4 por vuelta (V8 de cuatro tiempos), es decir rpm / 60 × 4 por segundo (67 Hz en ralentí, 547 Hz en el limitador). Cada pulso excita tres resonadores (cuerpo del escape, aspereza y tono agudo) y una ráfaga de ruido | rpm y acelerador |
| Carácter | Cada cilindro suena un poco distinto (desbalance fijo) y en ralentí el ritmo varía un poco | cilindro y carga |
| Admisión y escape | Ruido filtrado que crece con la carga y las rpm | acelerador y rpm |
| Viento | Ruido grave que crece con la velocidad al cuadrado | velocidad |
| Turbo | Silbido de 2.2 a 4.8 kHz y siseo que crecen con la presión; descarga al soltar el acelerador con presión | presión de turbo |
| Limitador | Desde 8100 rpm a fondo, la combustión se corta en ventanas de 45 ms | rpm y acelerador |
| Petardeos | Al soltar el acelerador en altas, alguna explosión fuerte al azar | acelerador y rpm |
| Arranque | 0.55 s de motor de arranque (zumbido y compresiones) antes de que prenda | encendido |
| Banco sin encendido (Etapa 20) | Falla de una unidad Weber-Marelli: falta una de cada dos explosiones (suena cojo, ritmo de 30 ms en ralentí) | falla del panel |
| Motor de arranque débil (Etapa 20) | Con la batería descargada el motor de arranque gira a 35 % de su velocidad y no prende | batería |
| Relevador (Etapa 20) | Clic cada 500 ms con las direccionales o las intermitentes | direccional y emergencia |
| Llantas (Etapa 20) | Chirrido de 1100 Hz al frenar a fondo o al arrancar patinando en primera | freno, acelerador y marcha |
| Ventilador (Etapa 20) | Zumbido de 45 Hz y aire cuando el agua pasa de 98 °C (se apaga a 92 °C) | temperatura |
| Alarma del cinturón | Campana de 1046 Hz cada segundo durante 6 s al dar contacto sin abrochar (FMVSS 208 S7.3 pide de 4 a 8 s); se calla al abrochar | contacto y cinturón |

Formato: PCM de 16 bits con signo, 22 050 muestras por segundo, mono. Se genera en bloques de 30 ms.

## Cómo llega a las bocinas

El panel corre en la máquina virtual y las bocinas están en Windows, así que el sonido es un **tercer
proceso**:

```
panel (VM)  --estado JSON, 20 por s-->  túnel SSH (-R 5055)  -->  tools/bocina.py (Windows)  -->  waveOut  -->  bocinas
```

- **Productor:** el panel, que en cada paso (50 ms) deja el estado del motor en un buzón de tamaño 1.
- **Envío:** un hilo del panel toma el estado más reciente y lo manda por TCP. Si la bocina no está,
  reintenta cada 2 s sin bloquear el panel.
- **Consumidor:** la bocina valida cada línea (claves, tipos, rangos, sin NaN, máximo 512 bytes),
  la deja en el buzón de su hilo de audio y descarta las inválidas, que cuenta.
- **Tiempo real blando:** el hilo de audio genera bloques de 30 ms y los entrega a waveOut con 4
  búferes. Cuando los 4 están ocupados, espera el evento de winmm (WaitForSingleObject), así que no
  hay espera activa. Además, nunca va más de 120 ms adelante del reloj, y eso acota la latencia. Si
  se atrasa (por ejemplo, porque la máquina se trabó), se resincroniza.
- **Seguridad:** la bocina escucha solo en 127.0.0.1 y la conexión viaja dentro de SSH.
- **Otras salidas:** con `--sonido auto` el panel suena en las bocinas de su propio equipo. En
  Windows usa waveOut; en Linux, un proceso hijo `aplay` alimentado por una tubería. Para eso la VM
  necesita, una sola vez, `sudo apt-get install -y alsa-utils` y `sudo usermod -aG audio $USER`.
  Sin salida de audio, el panel funciona igual y dice por qué no suena.

## Cómo usarlo

En Windows, en dos terminales PowerShell:

```
cd RUTA\DEL\PROYECTO
python tools\bocina.py
```

```
$env:DISPLAY = "127.0.0.1:0.0"
ssh -Y -R 5055:127.0.0.1:5055 -p 2222 USUARIO@127.0.0.1 "cd ~/cluster-f40 && ./abrir_panel.sh --sonido 127.0.0.1:5055"
```

En el panel, la barra superior dice si la bocina está conectada. La tecla `U` (o el botón
"Silencio") silencia el sonido.

Sin la VM se puede escuchar `docs/evidencias/sonido/motor_demo.wav`: un guion de 22 s con
contacto, alarma del cinturón, arranque, acelerones, primera hasta el limitador, segunda con el
turbo, descarga, frenada y apagado.

## Evidencia y pruebas

- `docs/evidencias/sonido/reporte.txt`: mediciones reales del audio generado. Las mide el mismo
  código de las pruebas: el ritmo de explosiones en ralentí, la frecuencia de encendido, los cortes
  del limitador, el silbido del turbo, la duración de la alarma, el arranque y el costo de CPU.
- CP-184 a CP-190 (`tests/test_sonido.py`): silencio y rango, ritmo de un V8, limitador, turbo y
  descarga, alarma y arranque, hilo de tiempo real, protocolo y bocina por socket, y el panel.

## Fuentes y límites

- La frecuencia de encendido de un motor de cuatro tiempos (rpm / 60 × cilindros / 2) es física
  básica del motor.
- FMVSS 208 S7.3 (texto vigente consultado): señal audible de 4 a 8 s al dar contacto con el
  cinturón del conductor sin abrochar. La versión de 1987 queda **pendiente de verificar**.
- El timbre, las frecuencias de los resonadores, el silbido del turbo y los petardeos son
  aproximados y elegidos por diseño; no se midieron en un F40.
