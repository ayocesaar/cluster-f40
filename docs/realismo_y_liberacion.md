# Realismo, seguridad y banco de liberación de producción (Etapa 18)

El equipo pidió que el proyecto dejara de parecer imaginario: abrir y cerrar puertas con su testigo y sin poder
avanzar, fallas con consecuencias físicas (frenos que no frenan bien, un motor que se protege ante sobrecalentamiento
o sobrepresión, que no arranca con fuga de aceite) y pruebas reales de la época para "mandar el auto a producción".
Este documento explica qué se agregó, cómo se relaciona con la materia, de dónde salen los criterios y qué queda
pendiente de verificar.

Regla del proyecto: ningún resultado se escribe a mano. Los números del banco salen de
`docs/evidencias/banco_liberacion.txt`, que genera `tools/banco_liberacion.py --evidencia` en la corrida oficial.

## 1. Qué cambió en el cuadro (el tablero)

| Elemento | Clave opcional | Tipo | Regla | Qué se ve |
|---|---|---|---|---|
| Llave | `contacto` | booleano | R01 y D3 | OFF, CONTACTO o MOTOR; prueba de testigos de 2 s al dar contacto |
| 12 Puerta abierta | `puertas` | bits de estado (0–3) | R09 | ámbar fija detenido; roja parpadeante desde 3 km/h |
| 13 Cinturón | `cinturon` | booleano | R10 | roja fija con contacto; parpadea sobre 10 km/h |
| 14 Combustible | `combustible` | decimal (%) | R11 | barra E–1/2–F, % y litros; reserva con ≤ 12 % y se apaga con ≥ 15 % |
| 15 Protección del motor | `falla_motor` | enumeración | R12 | STOP rojo y la causa (SOBRETEMPERATURA, ACEITE...) |

- **Los diez elementos aprobados no cambian.** Los nuevos son adicionales y llegan en claves opcionales (D8): un
  archivo de diez claves (simulador, escenarios de aceptación, versiones anteriores) funciona exactamente igual.
  Las 208 pruebas anteriores pasan sin cambios (huella sha256 en la corrida oficial).
- **Encendido y Motor activo (D3).** La especificación distingue Encendido (elementos 1 y 4) de Motor activo (2, 3
  y 5); antes un solo interruptor representaba ambas señales. Con `contacto=1` y `motor=0` el velocímetro, el agua y
  el odómetro siguen midiendo (por ejemplo, el auto que rueda después de que la ECU cortó el motor) y RPM, aceite y
  turbo quedan en 0. Sin la clave `contacto` el cuadro sigue al motor, como antes.
- **Validador con consistencia (D9).** La guía pide al validador "tipo, rango, unidad y consistencia". `motor=1`
  con `contacto=0` es imposible: se registra ERROR `dato_inconsistente` y se descarta el contacto.
- **Bits de estado (bloque 4.1).** `puertas` codifica dos puertas en un entero: bit 0 conductor, bit 1 pasajero
  (`puertas=3` = las dos abiertas).
- **Prueba de testigos (D10).** Al dar contacto todos los testigos encienden 2 s y solo se apagan si no hay falla.
  Es solo de presentación: no cambia reglas ni registra advertencias falsas.

## 2. Qué cambió en el panel (el lado del vehículo)

El cuadro **muestra**; quien **decide** es la ECU simulada del panel (`panel/ecu.py`, decisión D11), igual que en un
auto real, donde la unidad de control del motor y el cuadro son equipos distintos. La ECU no existe en el proceso del
tablero: es otro proceso que se comunica por el mismo archivo.

| Falla en el panel | Consecuencia física (`panel/fisica.py`) | Decisión de la ECU | Qué muestra el cuadro |
|---|---|---|---|
| Fuga de aceite | La presión cae al 45 % y el depósito se vacía (0.5 %/s en marcha); bajo 30 % la presión se desploma | No arranca con fuga o depósito < 50 %; en marcha corta con < 0.5 bar durante 3 s | Testigo 9 (R02) y 15 ACEITE |
| Radiador | El agua tiende a 125 °C | Corta el motor a 120 °C; no arranca hasta reparar y enfriar bajo 100 °C | Elemento 4 rojo desde 110 °C (R04) y 15 |
| Turbo (válvula de descarga) | La presión sube 65 % más | Corta con más de 1.5 bar durante 1 s; queda enclavada hasta reparar | Contorno ámbar (R05) y 15 |
| Frenos | El frenado baja al 30 % (un circuito perdido) | Ninguna: el conductor debe detenerse | Testigo 10 (R08) |
| Velocímetro | El sensor indica 5 % menos | Ninguna | La velocidad mostrada es menor que la real |
| Sin combustible | El motor se apaga solo | No arranca hasta cargar | Reserva (R11) y 15 |
| Puerta abierta | — | Bloquea la tracción: el acelerador no tiene efecto | Testigo 12 (R09) |

Otros cambios físicos: la temperatura del agua sube con la carga (90 °C en ralentí, hasta 102 °C a plena carga);
el consumo va de 2 L/h en ralentí a unos 140 L/h a plena carga; los frenos se calientan con cada frenada y entre
350 y 750 °C pierden eficiencia hasta 60 % (fading). Todas estas cifras son **aproximadas** y están marcadas así en
el código.

## 3. Banco de liberación de producción

`tools/banco_liberacion.py` (y el botón del panel) corre 9 pruebas sobre el modelo del vehículo con la misma ECU.
Las pruebas que tocan al cuadro usan su código real: cada lectura pasa por el formato del archivo y la validación del
lector (`formatear` → `convertir`) y llega a `EstadoCluster` en ciclos de 100 ms.

| Prueba | Norma o criterio | Criterio de aprobación |
|---|---|---|
| L01 Arranque, ralentí, aceite y carga | Fin de línea (criterio del equipo) | Arranca; en los últimos 5 s de 30 s: 950–1050 rpm estables, aceite ≥ 1.2 bar y carga ≥ 13.5 V (Etapa 20) |
| L02 Prueba de testigos | UN R13-H 5.2.21.4 | Todos encienden 2 s; 9, 10, 13 y 15 se apagan si no hay falla |
| L03 Frenado tipo 0 | UN R13-H anexo 3, 2.1.1 A | Desde 100 km/h, motor desembragado: s ≤ 0.1 v + 0.0060 v² (70 m) y dm ≥ 6.43 m/s² |
| L04 Frenado tipo I (fading) | UN R13-H anexo 3, 1.5 | 15 frenadas de 120 a 60 km/h cada 45 s a 3 m/s²; en caliente dm ≥ 75 % de 6.43 y ≥ 60 % del valor en frío |
| L05 Velocímetro | UN R39 5.2.5, 5.3 y anexo 3 | A 40, 80 y 120 km/h: 0 ≤ V1 − V2 ≤ 0.1 V2 + 4 km/h (nunca indica menos) |
| L06 Ciclo urbano y odómetro | Ciclo ECE-15 (prueba tipo I de emisiones) | 195 s y 0.994 km (± 2 %); seguimiento ≤ 2 km/h (criterio del equipo); odómetro del cuadro a ≤ 1 % |
| L07 Enfriamiento | Criterio del equipo (no es una norma) | 300 s a 250 km/h sin pasar de 110 °C ni detener el motor |
| L08 Turbo | Criterio del equipo (umbral de R05) | 6 s a fondo en 3a: presión ≤ 1.5 bar sin corte |
| L09 Puertas | Medida agregada por el equipo | Con la puerta abierta no avanza y el testigo 12 enciende; al cerrar avanza |

`dm` es la desaceleración media totalmente desarrollada, `dm = (vb² − ve²) / (25.92 (se − sb))`, con vb = 0.8 v0
y ve = 0.1 v0. El dictamen es **APTO PARA PRODUCCIÓN** si las 9 aprueban; si no, **RECHAZADO** con la lista de
pruebas que fallaron. Con `--evidencia` el banco prueba la unidad sana y cada falla por separado y comprueba que
**distingue**: la sana sale apta y cada falla sale rechazada por la prueba de su sistema (CP-182).

El banco también encontró un defecto real: el sensor de velocidad del panel redondeaba al décimo más cercano y
podía indicar menos que la velocidad real, lo que R39 prohíbe (DEF-16, corregido).

## 4. Relación con la materia

- **Formato de datos que evoluciona sin romper a los productores** (claves opcionales, D8): compatibilidad hacia
  atrás de un protocolo entre procesos.
- **Bits de estado** (puertas) y **enumeraciones cerradas** (falla_motor): bloque 4.1.
- **Validación de consistencia entre claves** (D9): componente "Validador" de la arquitectura de la guía.
- **Procesos:** el panel y su ECU son un proceso; el tablero otro; el banco corre como proceso hijo del panel con
  su salida por una tubería (Ejecutor); el ciclo ECE-15 en vivo produce datos mientras el tablero los consume.
- **Separación de responsabilidades:** el cuadro no decide si el motor puede funcionar (D11).
- **Observación** (guía, sección 6): atajo "ps du wc" en el panel y comandos en el README y la hoja de comandos.

## 5. Fuentes verificadas

| Dato | Fuente | Estado |
|---|---|---|
| R13-H anexo 3: tipo 0 (2.1.1 A), tipo I (1.5), recuperación, 5.2.21.4 (testigos) y 5.2.12 (líquido bajo) | ADR 31/01, apéndice A (texto de UN R13-H), https://www.legislation.gov.au/F2005L03852/asmade/2005-12-13/text/original/epub/OEBPS/document_1/document_1.html | Verificado (texto leído) |
| Fórmula de dm | Texto de UN R13 en EUR-Lex (2016/194) | Verificado |
| R39 5.2.5 (velocidades de prueba), 5.3 (0 ≤ V1 − V2 ≤ 0.1 V2 + 4) y anexo 3 (+ 6 km/h en producción) | ADR 18/03, apéndice (texto de UN R39), https://www.legislation.gov.au/F2006L01392/asmade/2006-05-10/text/original/epub/OEBPS/document_1/document_1.html | Verificado (texto leído) |
| Perfil ECE-15: fases, 195 s, máximo 50 km/h, 994.03 m | Wikipedia, New European Driving Cycle; DieselNet, ciclo ECE-15 | Verificado; la integral del perfil da 994.03 m (CP-180) |
| Tanque del F40: 120 L; motor 2.9 L V8 biturbo, 478 hp a 7000 rpm | Fichas de cararac.com y auto-data.net | Verificado en dos fichas |
| El F40 tenía medidores de temperatura de aceite, presión de aceite y combustible y una luz de advertencia | Catálogos de refacciones (eurospares, diagrama 119; ricambiamerica) | Verificado |
| Gestión Weber-Marelli IAW con encendido e inyección separados por banco de cilindros; dos turbos IHI a 1.1 bar; 577 Nm a 4000 rpm | Wikipedia (Ferrari F40), supercars.net, ultimatespecs, cararac | Verificado en varias fuentes (Etapa 20) |
| Sin ABS, sin control de tracción, sin dirección asistida ni servofreno | Revista de Ferrari (ferrari.com), Top Gear, Octane | Verificado (Etapa 21) |
| Cinturón: luz de al menos 60 s y señal audible de 4 a 8 s al dar contacto | FMVSS 208 S7.3 (texto vigente; interpretaciones de NHTSA) | Verificado el texto vigente |

## 6. Pendiente de verificar (no se presenta como dato)

- Los valores de la **Directiva 71/320/CEE** vigentes en 1987: el texto no se pudo descargar. Se usan los de UN R13-H.
- La versión de **UN R39** vigente en 1987 (se leyó el texto adoptado en la ADR 18/03 de 2006).
- La tolerancia oficial de velocidad del ciclo ECE-15: se usa ± 2 km/h como criterio del equipo.
- La versión de **FMVSS 208 S7.3** vigente en 1987.
- Presión de turbo nominal, línea roja, distancia de frenado y consumo reales del F40: el modelo usa cifras aproximadas.
- Si el F40 de 1987 tenía testigo de puerta o de cinturón: los elementos 12 y 13 se presentan como adicionales.
- El interbloqueo de puertas y las protecciones de la ECU son medidas del equipo, no del auto original.
- Etapa 20: las cifras eléctricas (batería de 40 Ah, alternador de 70 A, cargas, 10.5 V de corte) son genéricas de un
  sistema de 12 V, no del F40; la lista exacta de testigos del cuadro original (el manual técnico no se pudo consultar),
  las rpm del limitador y las relaciones de marcha (una sola fuente) quedan pendientes de verificar.

## 7. Cómo demostrarlo en la exposición (3 minutos)

1. `K`: llave a contacto → todos los testigos encienden 2 s (prueba de testigos) y la llave dice CONTACTO.
2. Marcar "Fuga de aceite" y pulsar `M`: **no arranca**; el cuadro muestra STOP · ACEITE; `logs/eventos.log` tiene
   WARN `motor_detenido_por_proteccion causa=aceite`. Taller → Reparar fallas → `M`: arranca.
3. `P` (puerta del conductor) y acelerar: el auto **no avanza** y el testigo 12 enciende; `P` otra vez: avanza.
4. A 100 km/h marcar "Frenos" y frenar: tarda unas tres veces más en detenerse y el testigo 10 parpadea.
5. "Banco con las fallas actuales": con la falla de frenos sale **RECHAZADO (L02, L03, L04)**; Reparar fallas y
   repetir: **APTO PARA PRODUCCIÓN**.
6. Opcional: "Ciclo ECE-15 en vivo" (195 s): el robot conduce el ciclo normalizado y el odómetro suma 0.994 km.
