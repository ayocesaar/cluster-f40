# Prácticas de fallas automáticas y física del F40 (Etapa 21)

## Prácticas de fallas (botones del panel)

El panel tiene 15 botones de prácticas. Cada uno corre solo un caso completo, que antes había que
provocar a mano. Mientras corre, **la palanca de cambios, los tres pedales y las casillas del panel
muestran lo que hace el robot**:

- pisa y suelta los pedales con la misma rapidez que el panel;
- en cada cambio suelta el acelerador, pisa el embrague, mueve la palanca y suelta el embrague;
- las casillas de fallas, puertas, cinturón, luces y pista mojada se marcan solas.

El tablero lo muestra en vivo, la consola narra cada paso y al final dice APROBADA o NO APROBADA.

| Botón | Qué hace | Qué verifica |
|---|---|---|
| Manejo normal | Contacto, arranque, 1a a 3a hasta 80 km/h y frenada | Prueba de testigos, sin advertencias críticas |
| Fuga de aceite | Inyecta la fuga con el motor en ralentí, apaga e intenta arrancar | Testigo 9 y WARN; no arranca; STOP · ACEITE; tras el taller arranca |
| Sobrecalentamiento | Radiador dañado manejando a 60 km/h | Agua en rojo (R04); la ECU corta a 120 °C; caliente no arranca; reparado y frío arranca |
| Turbo | Sobrepresión a fondo en 2a | Contorno ámbar (R05); corte enclavado; tras reparar arranca |
| Frenos | Frenada a fondo desde 100 km/h sana y con la falla | Testigo 10; distancia más de 2.5 veces mayor (por ejemplo 31 m contra 113 m) |
| Puertas | Acelera con la puerta abierta; la abre a 40 km/h | No avanza (interbloqueo); WARN de puerta en movimiento (R09) |
| Cinturón | Contacto y manejo sin abrochar | Testigo 13; WARN sobre 10 km/h (R10); al abrochar se apaga |
| Combustible | Reserva y luego 80 mL | Reserva y WARN (R11); se apaga; no arranca hasta llenar |
| Alternador | Falla con luces altas y batería al 25 % | Testigo 16 y WARN (R13); bajo 10.5 V la ECU apaga el motor |
| Batería débil | Intenta arrancar al 6 % | No arranca; el motor de arranque gira lento; cargada arranca |
| Weber-Marelli | Un banco sin encendido | Ralentí irregular sin testigo; 40–80 km/h en 2a mucho más lento |
| Limitador | 1a a fondo | Tacómetro en rojo (R03); nunca pasa de 8200 rpm |
| Lluvia sin ABS | Pista mojada | Patina al acelerar; se bloquea al frenar a fondo; dosificando frena en menos distancia |
| 0-100 km/h | Salida con el turbo cargado y cambios a 7600 rpm | Tiempo dentro del rango publicado (3.5 a 5.0 s; la cifra más citada es 4.1 s) |
| Velocímetro | Velocidad constante a 80 km/h, sano y descalibrado | Sano nunca indica menos (R39); descalibrado indica menos |

**Cómo funciona.** Cada práctica es una **corrutina**: un generador de Python que hace un paso y
cede el control. Puede ceder `None` (esperar un ciclo de 50 ms), un número (esperar esos segundos) o
una función (esperar a que se cumpla). El ciclo del panel la avanza sin bloquear la interfaz:
calendarización cooperativa, como en el tema 3.1.

Las verificaciones usan una **copia en memoria del cuadro real**: el mismo formato del archivo, la
misma validación del lector, `EstadoCluster` y el monitor de eventos. Así se comprueba lo que el
tablero mostraría y registraría.

**Evidencia:** `python3 tools/practicas.py` corre las 15 en tiempo simulado y deja en
`docs/evidencias/practicas.txt` cada verificación con lo medido. Pruebas: CP-203 (las 15 prácticas), CP-204 (el robot maneja como una persona) y CP-205 (el
panel muestra la palanca y los pedales del robot).

## Física con datos del F40

| Dato | Valor | Fuente | Uso |
|---|---|---|---|
| Par máximo | 577 Nm a 4000 rpm | Varias fichas (ultimatespecs, cararac, fastestlaps) | Punto de la curva de par |
| Potencia | 478 CV a 7000 rpm (unos 480 Nm) | Wikipedia, cararac | Punto de la curva de par |
| Turbos | Dos IHI a 1.1 bar | Wikipedia, supercars.net | Presión nominal del modelo |
| Sin ABS, sin control de tracción, sin dirección asistida ni servofreno | — | Revista de Ferrari, Top Gear, Octane | Las llantas patinan y se bloquean |
| 0–100 km/h | 4.1 s (la más citada; hay pruebas de 3.5 a 5.0 s) | auto-data, fastestlaps | Calibración del empuje: el modelo da unos 4.7 s en la práctica |
| Velocidad máxima | 324 km/h | Fichas publicadas | Calibración de la resistencia del aire: el modelo da unos 326 km/h |

- **Curva de par:** entre los dos puntos verificados la curva es aproximada. Bajo 2500 rpm, o
  mientras el turbo carga, el motor empuja como uno atmosférico, así que se siente el retraso del
  turbo.
- **Adherencia:** en seco las llantas aguantan hasta frenar a fondo, pero en primera a plena carga
  patinan. En mojado (55 %) se bloquean al frenar a fondo y una llanta bloqueada agarra 20 % menos.
  Por eso dosificar el freno detiene antes, y para eso existe el ABS.
- **Temperatura de aceite (elemento 17, R14):** el F40 tiene este medidor (catálogo de refacciones).
  El aceite sigue a la temperatura del agua más lento y sube con la carga. Se pone en rojo sobre
  130 °C y vuelve a normal con 125 °C o menos.
- **Agujas con inercia:** en cada refresco de 50 ms la aguja recorre el 35 % del camino que le falta,
  como un instrumento analógico. El color y la cifra cambian de inmediato.
- **Pendiente de verificar:** las relaciones de marcha (una sola fuente), el peso (de 1100 a
  1235 kg según la fuente), las rpm del limitador y la forma exacta de la curva entre los puntos
  verificados.
