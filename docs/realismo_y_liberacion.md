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
| L03 Frenado tipo 0 | UN R13-H anexo 3, 2.1.1 A y Directiva 71/320/CEE (texto vigente en 1987) | Desde 100 km/h, motor desembragado: s ≤ 0.1 v + 0.0060 v² (70 m) y dm ≥ 6.43 m/s²; y el criterio de 1987 para M1: desde 80 km/h, s ≤ 0.1 v + v²/150 (50.7 m) y desaceleración media ≥ 5.8 m/s² (Etapa 22) |
| L04 Frenado tipo I (fading) | UN R13-H anexo 3, 1.5 | 15 frenadas de 120 a 60 km/h cada 45 s a 3 m/s²; en caliente dm ≥ 75 % de 6.43 y ≥ 60 % del valor en frío |
| L05 Velocímetro | UN R39 5.2.5, 5.3 y anexo 3; la Directiva 75/443/CEE de la época pide lo mismo | A 40, 80 y 120 km/h: 0 ≤ V1 − V2 ≤ 0.1 V2 + 4 km/h (nunca indica menos) |
| L06 Ciclo urbano y odómetro | Ciclo ECE-15; tolerancias de UN R84, anexo 5 (Etapa 22) | 195 s y 0.994 km (± 2 %); ± 1 km/h con ± 0.5 s de tolerancia de tiempo, fuera a lo más 0.5 s seguidos; odómetro del cuadro a ≤ 1 % |
| L07 Enfriamiento | Criterio del equipo (no es una norma) | 300 s a 250 km/h sin pasar de 110 °C ni detener el motor |
| L08 Turbo | Criterio del equipo (umbral de R05) | 6 s a fondo en 3a: presión ≤ 1.5 bar sin corte |
| L09 Puertas | Medida agregada por el equipo | Con la puerta abierta no avanza y el testigo 12 enciende; al cerrar avanza |

`dm` es la desaceleración media totalmente desarrollada, `dm = (vb² − ve²) / (25.92 (se − sb))`, con vb = 0.8 v0
y ve = 0.1 v0. Para el criterio de 1987 se usa la desaceleración media de toda la frenada, v0² / (25.92 s): el texto
de 1986 liga el segundo término de la fórmula con la desaceleración media (v²/150 equivale a 5.8 m/s²). La fuerza en el
pedal (≤ 500 N) no se representa en el modelo. El dictamen es **APTO PARA PRODUCCIÓN** si las 9 aprueban; si no, **RECHAZADO** con la lista de
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
| Directiva 71/320/CEE vigente en 1987 (versión consolidada del 3-1-1986), anexo II 2.1.1.1.1: M1, tipo O con el motor desembragado a 80 km/h, s ≤ 0.1 v + v²/150, dm ≥ 5.8 m/s² y fuerza ≤ 500 N; con el motor embragado (30 a 80 % de vmax) solo se registra | EUR-Lex, CELEX 01971L0320-19860103, https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:01971L0320-19860103 | Verificado (texto leído, Etapa 22) |
| Directiva 75/443/CEE (velocímetro), 4.3.6 y 4.4: instrumentos a ± 1.0 %, la velocidad indicada nunca es menor que la real y V1 − V2 ≤ V2/10 + 4 km/h | EUR-Lex, CELEX 31975L0443, https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:31975L0443 | Verificado (Etapa 22; el PDF es un escaneo y la fórmula se leyó del texto reconocido) |
| UN R84 (consumo de combustible), anexo 5: ± 1 km/h entre la velocidad y la teórica al acelerar, a velocidad constante y al frenar; más en los cambios de fase si no pasa de 0.5 s cada vez; ± 0.5 s de tiempo, combinadas; 4 ciclos urbanos (4.052 km teóricos); pruebas a 90 y 120 km/h constantes con ± 2 km/h | ONU, E/ECE/324 Rev.1/Add.83, https://digitallibrary.un.org/record/225859/files/E_ECE_324_Rev.1_Add.83_E_ECE_TRANS_505_Rev.1_Add.83-EN.pdf | Verificado (texto leído, Etapa 22) |
| FMVSS 208 S7.3 en el 49 CFR del 1-10-1996: el fabricante elige (1) señal audible de 4 a 8 s y luz de al menos 60 s si el cinturón no está abrochado, o (2) luz de 4 a 8 s al dar contacto y señal audible si no está abrochado | govinfo, https://www.govinfo.gov/content/pkg/CFR-1996-title49-vol5/pdf/CFR-1996-title49-vol5-sec571-208.pdf | Verificado el texto de 1996 (Etapa 22) |
| Datos del fabricante del F40: 1250 kg en orden de marcha (UE), 0-100 km/h en 4.1 s, 324 km/h, tanque de 120 L, consumo ciudad 18.4, 90 km/h 8.6 y 120 km/h 10.3 L/100 km, llantas 245/40 ZR17 y 335/35 ZR17 | ADAC Autokatalog, https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/ferrari/f40/1generation/260875/ | Verificado (Etapa 22) |
| Peso en seco 1100 kg | evo, https://www.evo.co.uk/ferrari/f40/6214/ferrari-f40-review-history-prices-and-specs | Verificado (Etapa 22) |
| Compresión 7.8:1 | Auto Motor und Sport; supercars.net | Verificado en dos fuentes (Etapa 22) |
| Línea roja del tacómetro: 7750 rpm | Hagerty, https://www.hagerty.com/media/archived/fever-dream-of-a-ferrari-f40/ ; supercars.net, https://www.supercars.net/blog/the-ferrari-f40/ | Verificado en dos fuentes (Etapa 22) |
| Relaciones de la caja: 2.769, 1.722, 1.227, 0.963 y 0.767 | Foro GT Planet que cita la prueba de Auto Motor und Sport de 1989, https://www.gtplanet.net/forum/threads/difficult-car-ferrari-f40.310621/ ; cars-data.com da las mismas según el buscador (la página respondió 403) | Dos fuentes secundarias coinciden (Etapa 22) |
| Frenado de 60 a 0 mph en 119 ft (36.3 m) | duPont Registry, https://news.dupontregistry.com/ferrari/ferrari-f40-specs-price-photos-review/ (no nombra la prueba; el buscador la atribuye a Road & Track, pero esa página respondió 403) | Una fuente abierta (Etapa 22) |

## 6. Pendiente de verificar (no se presenta como dato)

En la Etapa 22 se verificó lo que estaba pendiente (sección 5): la Directiva 71/320/CEE vigente en 1987, la Directiva
75/443/CEE del velocímetro (pide lo mismo que R39), la tolerancia del ciclo urbano (UN R84), el texto de FMVSS 208 de
1996 y los datos del fabricante del F40. Lo que queda:

- **FMVSS 208 S7.3 de 1987:** se leyó la edición del CFR de 1996; la de 1987 no se pudo descargar (NHTSA responde 403).
- **Cómo se combinan las tolerancias de UN R84:** el texto remite a una figura que no se encontró; el equipo usa la
  envolvente de ± 1 km/h dentro de ± 0.5 s. UN R84 es de 1990; la Directiva 80/1268/CEE, su equivalente europeo de
  1987, no se leyó.
- **Origen de dos datos del F40:** la frenada de 119 ft (una fuente abierta que no nombra la prueba) y las relaciones de
  marcha (dos fuentes secundarias). El diferencial (3.62 según el foro) no se usa.
- **Las rpm del limitador real:** ninguna fuente las da; el modelo corta a 8200 rpm para que se vea R03.
- **R03 contra el auto real:** la especificación pone el rojo del tacómetro en 8000 rpm y la línea roja real es 7750 rpm.
  Se conserva la especificación (y sus pruebas); queda para decidir con el profesor.
- Si el F40 de 1987 tenía testigo de puerta o de cinturón, y la lista exacta de testigos del cuadro original (el manual
  técnico no se pudo consultar): los elementos 12 y 13 se presentan como adicionales.
- Las cifras eléctricas (batería de 40 Ah, alternador de 70 A, cargas, 10.5 V de corte) son genéricas de un sistema de
  12 V, no del F40. La forma de la curva de par entre los dos puntos verificados es aproximada.
- **Fuentes que se contradicen:** supercars.net da llantas delanteras 235/45 ZR17 y frenos con servo; ADAC (datos del
  fabricante) da 245/40 ZR17 y la revista de Ferrari dice que no tenía servofreno. Se usan ADAC y Ferrari.
- El interbloqueo de puertas y las protecciones de la ECU son medidas del equipo, no del auto original.

## 7. Cómo demostrarlo en la exposición (3 minutos)

1. `K`: llave a contacto → todos los testigos encienden 2 s (prueba de testigos) y la llave dice CONTACTO.
2. Marcar "Fuga de aceite" y pulsar `M`: **no arranca**; el cuadro muestra STOP · ACEITE; `logs/eventos.log` tiene
   WARN `motor_detenido_por_proteccion causa=aceite`. Taller → Reparar fallas → `M`: arranca.
3. `P` (puerta del conductor) y acelerar: el auto **no avanza** y el testigo 12 enciende; `P` otra vez: avanza.
4. A 100 km/h marcar "Frenos" y frenar: tarda unas tres veces más en detenerse y el testigo 10 parpadea.
5. "Banco con las fallas actuales": con la falla de frenos sale **RECHAZADO (L02, L03, L04)**; Reparar fallas y
   repetir: **APTO PARA PRODUCCIÓN**.
6. Opcional: "Ciclo ECE-15 en vivo" (195 s): el robot conduce el ciclo normalizado y el odómetro suma 0.994 km.
