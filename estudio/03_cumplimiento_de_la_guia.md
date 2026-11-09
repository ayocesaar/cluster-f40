# Cumplimiento de la guía del proyecto final

Comparación entre la guía del profesor (`Guia_Proyecto_Final_Cluster_Vehicular.pdf`) y lo que hay en el
repositorio. Estado: ✅ hecho · ⚠️ parcial · ❌ pendiente.

> **Resumen honesto.** El tablero, sus reglas, la validación y las pruebas automatizadas están completos y
> verificados (108 ejecuciones, 10 escenarios de aceptación). Lo que la guía pide y **todavía no existe** es la
> parte de sistema operativo alrededor del tablero: datos leídos de **archivos externos**, **configuración** en
> archivo, **bitácoras** `eventos.log` y `errores.log`, **comunicación y sincronización** entre actividades
> concurrentes, **permisos**, la **prueba de ejecución prolongada con métricas** y un **informe técnico** con las
> secciones 4.1–4.7. El informe actual es un informe de **pruebas**. Estos puntos pesan en los criterios 4, 5, 6,
> 7, 8 y 9 de la rúbrica.

## Condiciones obligatorias (sección 1)

| Condición | Estado | Detalle |
|---|---|---|
| Vehículo: marca, modelo y año | ✅ | Ferrari F40 (1987), en el informe y el README. Debe coincidir con la tarea 2. |
| Diez elementos funcionales | ✅ | Los 10 funcionan y tienen pruebas (ver 02_guia_de_estudio.md). |
| Entrada sin editar ni recompilar | ⚠️ | Los valores se cambian con los controles de la ventana. La guía pide que cada elemento se controle con **datos externos a la interfaz** (archivo o proceso). |
| Actualización sin reiniciar | ✅ | El tablero se refresca cada 50 ms con `after()` de Tkinter. |
| Persistencia en archivos separados | ❌ | No hay `config/`, `datos/` ni `logs/`. |
| Validación sin detener el sistema | ⚠️ | Los valores inválidos se rechazan, se avisa en pantalla y se conserva el último válido (CP-52, CP-77). Falta registrarlos en `errores.log`. |
| Código, documentación y pruebas de la misma versión | ✅ | El informe indica el commit probado. |

## Categorías de los elementos (sección 2)

La guía pide **2 indicadores principales, 3 de información en línea, 3 testigos informativos y 2 testigos de
seguridad**, y que un mismo componente no cuente en dos categorías.

| Categoría de la guía | Elementos del proyecto | Estado |
|---|---|---|
| Indicadores principales (2) | 1 velocímetro, 4 temperatura de agua | ✅ |
| Información en línea (3) | 3 tacómetro, 2 presión de aceite, 5 presión de turbo | ⚠️ Los ejemplos de la guía son odómetro, autonomía, consumo, marcha o temperatura exterior. Confirmar con el profesor que estos tres cuentan. |
| Testigos informativos (3) | 6 direccionales, 7 luces altas, 8 emergencia | ✅ |
| Testigos de seguridad (2) | 9 baja presión de aceite, 10 falla de frenos | ⚠️ El 2 (medidor) y el 9 (testigo) vienen del mismo sensor de presión de aceite. Confirmar que no cuenta como "mismo componente en dos categorías". |

La **ficha obligatoria por elemento** está incompleta: faltan la fuente del dato (archivo o proceso), el
comportamiento ante dato ausente, y el evento a registrar con su archivo de destino.

## Conocimientos del curso (sección 4)

| Bloque | Estado | Qué hay / qué falta |
|---|---|---|
| 4.1 Representación de datos | ⚠️ | Hay tipos y rangos validados (float, int, bool, enumeración). Falta documentarlos con tamaño, signo y precisión. |
| 4.2 Procesos y calendarización | ⚠️ | Hay ciclos de 100/500/300 ms y un bucle con temporizador, sin espera activa. Falta separar lectura y bitácora, y justificar la prioridad por escrito. |
| 4.3 Comunicación y sincronización | ❌ | No hay productor/consumidor entre actividades ni prueba concurrente. |
| 4.4 Sistema de archivos | ❌ | No hay archivos de datos, configuración ni bitácoras; tampoco permisos. |
| 4.5 Memoria y almacenamiento | ⚠️ | El estado vive en un objeto de tamaño fijo y no hay historial que crezca. Falta documentarlo y definir la persistencia. |
| 4.6 Seguridad | ⚠️ | Toda entrada se valida. Faltan permisos y el análisis de tres amenazas con sus controles. |
| 4.7 Errores y bitácoras | ❌ | Los errores se muestran en pantalla, pero no hay `eventos.log` ni `errores.log` con fecha, nivel y componente. |

## Pruebas obligatorias P01–P12 (sección 6)

| ID | Caso | Estado | Cobertura actual |
|---|---|---|---|
| P01 | Valor normal | ⚠️ | CP-01 a CP-05. Falta el evento INFO. |
| P02 | Límite inferior | ✅ | CP-11, CP-21, CP-24 |
| P03 | Límite superior | ✅ | CP-12, CP-16 |
| P04 | Fuera de rango | ⚠️ | CP-38, CP-39, CP-42 y siguientes; aviso en pantalla (CP-77). Falta ERROR/WARN en bitácora. |
| P05 | Formato incorrecto | ✅ | CP-44, CP-83; conserva el último valor válido (CP-52) |
| P06 | Dato ausente | ⚠️ | Solo para el archivo de escenarios (CP-80, CP-81). |
| P07 | Archivo inexistente | ⚠️ | Solo para el archivo de escenarios (CP-79, CP-88). |
| P08 | Actualización concurrente | ❌ | — |
| P09 | Advertencia | ⚠️ | CP-18, CP-32, CA-09, CA-10. Falta el evento prioritario en bitácora. |
| P10 | Recuperación | ✅ | CP-77: valor inválido, aviso, valor válido y el aviso desaparece |
| P11 | Permisos | ❌ | — |
| P12 | Ejecución prolongada | ❌ | Faltan las métricas de memoria, intervalo real y tamaño de bitácoras. |

## Entregables (sección 7)

| # | Entregable | Estado |
|---|---|---|
| 1 | Código fuente | ✅ |
| 2 | README | ⚠️ Falta una sección de solución de problemas más completa |
| 3 | Informe técnico PDF | ⚠️ El actual es de pruebas; faltan arquitectura, conceptos 4.1–4.7, decisiones y conclusiones |
| 4 | Tabla de los 10 elementos | ⚠️ Falta la ficha completa |
| 5 | Diagramas | ❌ |
| 6 | Configuración y entradas | ⚠️ Solo el CSV de escenarios |
| 7 | Bitácoras | ❌ |
| 8 | Matriz de pruebas | ✅ `docs/matriz_trazabilidad.md` |
| 9 | Script de inicio | ✅ `abrir_cluster.sh` / `abrir_cluster.bat` (la guía lo llama `iniciar.sh`) |
| 10 | Demostración | ⚠️ Ver el guion en 02_guia_de_estudio.md |

## Qué falta construir (propuesta)

1. Datos externos: `datos/vehiculo.conf` (formato `clave=valor`, como el ejemplo de la guía) leído por un hilo
   lector que valida cada valor y conserva el último válido.
2. Configuración: `config/cluster.ini` con rutas, intervalos y rangos.
3. Bitácoras: `logs/eventos.log` y `logs/errores.log` con el formato de la guía, con rotación por tamaño.
4. Comunicación: lector → cola (`queue.Queue`) → interfaz (productor/consumidor). El escritor de datos usa
   archivo temporal + renombrado atómico para evitar lecturas parciales.
5. Seguridad: permisos de archivos, análisis de amenazas.
6. Pruebas nuevas P01–P12, incluida la concurrente y la de ejecución prolongada con métricas, **sin cambiar las
   108 actuales**.
7. Informe técnico con las 10 secciones sugeridas, fichas y diagramas.
