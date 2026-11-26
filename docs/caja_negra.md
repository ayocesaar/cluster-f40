# Caja negra del clúster (Etapa 20)

Un registrador de datos guarda los últimos 60 segundos del vehículo, 10 muestras por segundo, en
`datos/caja_negra.bin`. Cuando se enciende un testigo crítico, exporta a CSV los 10 segundos
anteriores, como el registrador de datos de una prueba de desarrollo. El F40 de 1987 no tenía este
equipo: es una herramienta de diagnóstico del simulador.

Cubre puntos de la guía que antes solo se respondían con acceso secuencial:

- **4.4:** "justificar si el acceso es secuencial o directo".
- **4.5:** "¿existe historial, cuántos registros conserva y cómo limita su crecimiento?" y
  "justificar formato y política de escritura considerando rendimiento, durabilidad y
  recuperación".
- **4.1:** "tamaño, signo y precisión".

## Formato (binario, little endian)

**Cabecera: 64 bytes** (`struct` `<8sHHIQQ30xH`)

| Byte | Campo | Tipo | Significado |
|---|---|---|---|
| 0 | firma | 8 bytes | `F40CNEG1` |
| 8 | versión | uint16 | 1 |
| 10 | tamaño de registro | uint16 | 32 |
| 12 | capacidad | uint32 | 600 registros (60 s × 10 Hz, en `config/cluster.ini`) |
| 16 | total | uint64 | registros escritos desde que se creó; el siguiente va en `total mod capacidad` |
| 24 | creada | uint64 | fecha de creación en ms |
| 32 | relleno | 30 bytes | reservado |
| 62 | CRC | uint16 | CRC-16 de los 62 bytes anteriores |

**Registro: 32 bytes** (`struct` `<QIHHHhHBBHBB2xH`)

| Byte | Campo | Tipo | Escala | Rango | Por qué ese tipo |
|---|---|---|---|---|---|
| 0 | fecha | uint64 | ms desde 1970 | — | no se desborda en siglos |
| 8 | secuencia | uint32 | — | 0 a 4 294 967 295 | detecta registros viejos del anillo |
| 12 | velocidad | uint16 | 0.1 km/h | 0 a 3600 | 360.0 km/h cabe en 16 bits con una décima |
| 14 | rpm | uint16 | 1 rpm | 0 a 9000 | entero, como el elemento 3 |
| 16 | presión de aceite | uint16 | 0.01 bar | 0 a 1000 | los umbrales usan centésimas |
| 18 | temperatura del agua | **int16** | 0.1 °C | −400 a 1500 | **con signo**: admite temperaturas bajo cero |
| 20 | presión de turbo | uint16 | 0.01 bar | 0 a 200 | |
| 22 | combustible | uint8 | 1 % | 0 a 100; **255 = sin dato** | un byte alcanza |
| 23 | voltaje | uint8 | 0.1 V | 0 a 200; **255 = sin dato** | 14.2 V = 142 |
| 24 | testigos | uint16 | bits | — | un bit por testigo: 6, 7, 8, 9, 10, 12, 13, 14 (reserva), 15, 16 |
| 26 | causa | uint8 | índice | 0 a 5; 255 = sin dato | ninguna, sobretemperatura, turbo, aceite, combustible, eléctrica |
| 27 | estado | uint8 | bits | — | motor, cuadro energizado, prueba de testigos |
| 28 | relleno | 2 bytes | | | alinea el CRC al final |
| 30 | CRC | uint16 | CRC-16 | | detecta un registro dañado |

## Cómo funciona

- **Tamaño fijo:** el archivo nace de su tamaño final, 64 + 600 × 32 = 19 264 bytes, y nunca crece.
  Es un anillo: el registro 600 sobrescribe al 0.
- **Acceso directo:** el registro número *k* está en el byte `64 + (k mod 600) × 32` y se escribe con
  `pwrite` en ese desplazamiento. Para leer los últimos *N* no se recorre el archivo: se calcula
  dónde está cada uno.
- **Política de escritura:**
  - La interfaz solo empaqueta la muestra y la deja en una cola acotada de 50 elementos. Nunca
    espera al disco; si la cola se llena, descarta la muestra y la cuenta.
  - Un hilo escritor la graba y hace `fsync` una vez por segundo. Si se va la luz se pierde a lo más
    el último segundo, a cambio de no sincronizar 10 veces por segundo.
  - Los eventos van por una lista aparte y nunca se descartan.
- **Recuperación:**
  - Cada registro lleva su CRC: uno dañado se detecta y se salta.
  - Si la cabecera está dañada, el archivo se aparta como `.invalido`, se crea otro y se registra
    ERROR `caja_negra_invalida`.
  - Si cambia la capacidad en la configuración, se reinicia con WARN.
- **Un solo escritor:** solo la ventana del tablero que tiene el candado de instancia única la
  escribe, igual que el odómetro.
- **Permisos:** 640 para el archivo y los CSV; 750 para `logs/caja_negra/`.
- **Eventos:** cuando se enciende el testigo 9, el 10 o el 15, cuando falla la carga (testigo 16 con el
  motor en marcha) o cuando se abre la puerta en movimiento, se sincroniza y se exportan los 10 s previos a `logs/caja_negra/evento_..._causa.csv`.
  Se conservan los 20 más recientes, con INFO `caja_negra_evento`.

## Herramienta

```
python3 tools/caja_negra.py                       # cabecera y últimos registros (solo lectura)
python3 tools/caja_negra.py --hex 1               # el último registro byte por byte, con cada campo
python3 tools/caja_negra.py --ultimos 100 --csv salida.csv
python3 tools/caja_negra.py --demo docs/evidencias/caja_negra   # 70 s simulados con sobrecalentamiento
```

## Evidencia y pruebas

- `docs/evidencias/caja_negra/reporte.txt`: tamaño del archivo, registros escritos, CRC revisados, el
  evento del sobrecalentamiento, la cabecera en hexadecimal y un registro decodificado campo por campo.
- CP-191 a CP-196 (`tests/test_caja_negra.py`): formato, anillo y acceso directo, persistencia, CRC y
  recuperación, eventos, hilo escritor, aplicación real y herramienta.
