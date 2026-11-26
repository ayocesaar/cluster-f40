# Cumplimiento de la guía del proyecto final

Comparación entre la guía del profesor (`Guia_Proyecto_Final_Cluster_Vehicular.pdf`) y el repositorio.
Estado: ✅ hecho · ⚠️ requiere confirmación o tiene una limitación documentada.

Los resultados reales de cada prueba están en `docs/evidencias/` y en los dos informes de `informe/`.

## Condiciones obligatorias (sección 1)

| Condición | Estado | Evidencia |
|---|---|---|
| Vehículo: marca, modelo y año | ✅ | Ferrari F40 (1987): README, informes y el encabezado del propio tablero. Debe coincidir con la tarea 2. |
| Diez elementos funcionales | ✅ | Pruebas CP-01 a CP-90, CA-01 a CA-10 |
| Elemento 11 (odómetro), agregado tras la práctica | ✅ | tests/test_odometro.py, CP-120 a CP-137 |
| Elementos adicionales 12-15 (puerta, cinturón, combustible, protección) | ✅ | Claves opcionales; no sustituyen a los diez aprobados; CP-163 a CP-178 |
| Entrada sin editar ni recompilar | ✅ | `datos/vehiculo.conf`, `tools/escribir_dato.py`, `tools/simulador.py` |
| Actualización sin reiniciar | ✅ | CP-115: con la app abierta se cambia el archivo y el tablero cambia |
| Persistencia en archivos separados | ✅ | `config/cluster.ini`, `datos/vehiculo.conf`, `logs/eventos.log`, `logs/errores.log` |
| Validación sin detener el sistema | ✅ | P04–P07 y P10 (CP-94 a CP-97, CP-100); consistencia entre claves (dato_inconsistente, CP-164) |
| Código, documentación y pruebas de la misma versión | ✅ | Los informes indican el commit probado |

## Categorías de los elementos (sección 2)

| Categoría de la guía | Elementos | Estado |
|---|---|---|
| Indicadores principales (2) | 1 velocímetro, 4 temperatura de agua | ✅ |
| Información en línea (3) | 3 tacómetro, 2 presión de aceite, 5 presión de turbo | ⚠️ Confirmar con el profesor: sus ejemplos son odómetro, autonomía, consumo, marcha o temperatura exterior |
| Información en línea (agregado) | 11 odómetro (tests/test_odometro.py, CP-120 a CP-137) | ✅ |
| Testigos informativos (3) | 6 direccionales, 7 luces altas, 8 emergencia | ✅ |
| Testigos de seguridad (2) | 9 baja presión de aceite, 10 falla de frenos | ⚠️ Confirmar que el medidor 2 y el testigo 9 (mismo sensor) no cuentan como "mismo componente en dos categorías" |
| Adicionales (Etapa 18) | 12 puerta abierta (informativo, ejemplo de la guía), 13 cinturón (seguridad, ejemplo de la guía), 14 combustible (información en línea; la guía lo usa en su archivo de ejemplo), 15 protección del motor (seguridad) | ✅ Si el profesor no acepta la categoría de 2, 3 o 5, el 14 cubre información en línea y el 13 un testigo de seguridad |

La ficha obligatoria de cada elemento está completa en el **informe técnico, sección 3**.

## Conocimientos del curso (sección 4)

| Bloque | Estado | Dónde |
|---|---|---|
| 4.1 Representación de datos | ✅ | Informe técnico §5; `sistema/lector.py` (`convertir`, `formatear`); CP-109; bits de estado (`puertas`) y enumeración (`falla_motor`), CP-163 |
| 4.2 Procesos y calendarización | ✅ | Informe técnico §6; hilo lector + `after()`; prioridad del monitor de seguridad |
| 4.3 Comunicación y sincronización | ✅ | Escritura atómica + buzón `queue.Queue(maxsize=1)`; prueba concurrente CP-98 |
| 4.4 Sistema de archivos | ✅ | Carpetas separadas, rutas relativas, permisos 640/750; CP-101 a CP-103, CP-106 |
| 4.5 Memoria y almacenamiento | ✅ | Informe técnico §7; métricas reales de memoria en `docs/evidencias/metricas.txt` |
| 4.6 Seguridad | ✅ | Informe técnico §8: seis amenazas con controles; CP-107 |
| 4.7 Errores y bitácoras | ✅ | `sistema/bitacora.py`; ejemplos en `docs/evidencias/bitacoras/`; CP-105, CP-110 |

## Pruebas obligatorias P01–P12 (sección 6)

| ID | Caso | Prueba |
|---|---|---|
| P01 | Valor normal | CP-91 |
| P02 | Límite inferior | CP-92 |
| P03 | Límite superior | CP-93 |
| P04 | Fuera de rango | CP-94 (+ aviso en pantalla CP-77) |
| P05 | Formato incorrecto | CP-95 |
| P06 | Dato ausente | CP-96 |
| P07 | Archivo inexistente | CP-97 |
| P08 | Actualización concurrente | CP-98 |
| P09 | Advertencia | CP-99 |
| P10 | Recuperación | CP-100 |
| P11 | Permisos | CP-101, CP-102, CP-103 (solo Linux; en Windows se omiten) |
| P12 | Ejecución prolongada | CP-104 + `tools/ejecucion_prolongada.py` → `docs/evidencias/metricas.txt` |

Comandos de observación de la sección 6 (`ps`, `watch du`, `tail -f`, `wc -l`): README, hoja de comandos §5 y el atajo "ps du wc" del panel.

Pruebas de liberación de producción (adicionales, normas de la época): `tools/banco_liberacion.py`, 9 pruebas L01–L09 (UN R13-H, UN R39, ECE-15); evidencia en `docs/evidencias/banco_liberacion.txt`; CP-179 a CP-183.

Métricas mínimas (intervalo real, eventos y errores, memoria inicial y final, tamaño de bitácoras):
`docs/evidencias/metricas.txt`.

## Entregables (sección 7)

| # | Entregable | Dónde |
|---|---|---|
| 1 | Código fuente | `logic/`, `sistema/`, `ui/`, `main.py`; panel, ECU y banco en `panel/` |
| 2 | README | `README.md` (requisitos, instalación, estructura, ejecución, solución de problemas) |
| 3 | Informe técnico en PDF | `informe/Informe_Tecnico_Cluster_F40.pdf` |
| 4 | Tabla de los elementos (10 aprobados + odómetro + 4 adicionales) | Informe técnico §3 |
| 5 | Diagramas | `docs/diagramas/arquitectura.png`, `docs/diagramas/flujo_actualizacion.png` |
| 6 | Configuración y entradas | `config/cluster.ini`, `datos/vehiculo.conf`, `tests/datos/` |
| 7 | Bitácoras | `docs/evidencias/bitacoras/exitosa/` y `docs/evidencias/bitacoras/con_errores/` |
| 8 | Matriz de pruebas | Informe técnico §10, `docs/matriz_trazabilidad.md` |
| 9 | Script de inicio | `iniciar.sh` (Linux/macOS), `abrir_cluster.bat` (Windows) |
| 10 | Demostración | Guion en `06_guia_de_defensa.md` y `02_guia_de_estudio.md`, sección 5 |

Reglas de entrega: dependencias y licencias en el README y en `docs/evidencias/licencias.txt` (de los metadatos reales); sin recursos gráficos ni sonidos de terceros.

## Lo único pendiente

1. Confirmar con el profesor las categorías de los elementos 2, 3, 5 y 9 (ver arriba) y que acepta los adicionales 12-15.
2. Ensayar la demostración con el guion de `02_guia_de_estudio.md`.
3. Revisión cruzada, escenario sorpresa y observaciones del profesor de la práctica del odómetro: pendientes (no han ocurrido).
4. Fuentes pendientes de verificar del banco de liberación (Directiva 71/320/CEE de 1987, versión de R39 y FMVSS 208 de 1987, tolerancia del ECE-15, cifras reales del F40): `docs/realismo_y_liberacion.md`, sección 6.
