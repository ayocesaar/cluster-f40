# Registro de defectos - Cluster F40

## DEF-01 - El testigo de falla de frenos (10) parpadea con el motor apagado

| Campo | Valor |
|-------|-------|
| ID | DEF-01 |
| Estado | Rechazado (no es defecto segun R08) |
| Severidad asignada al reportarlo | Media |
| Requisitos relacionados | R01 (encendido/apagado), R08 (testigo de falla de frenos) |
| Componente | `logic/estado.py`, propiedad `testigo_falla_frenos_encendido` (testigo 10) |
| Detectado en | Etapa 4 (revision de codigo durante pruebas de caja blanca) |
| Caso de prueba | CP-66 (`tests/test_requisitos.py`) |

**Reporte original**

1. Crear `EstadoCluster` con el motor apagado (estado inicial).
2. Llamar `set_falla_frenos(True)`.
3. Leer `testigo_falla_frenos_encendido` en t = 0 ms y cada 300 ms.

Se esperaba `False` con el motor apagado, interpretando R01 como un apagado
general de todos los testigos. Se obtuvo `True` en t = 0 ms, alternando cada 300 ms.

**Historial**

1. Etapa 6 (commit `daad491`): registrado como Abierto; CP-66 se marco `xfail`.
2. Etapa 7 (commit `382a8d9`): se agrego una condicion de motor al testigo 10 y
   el defecto se marco Cerrado.
3. Etapa 8a.1: al revisar la especificacion completa se comprobo que:
   - R08 dice "falla_frenos=1 -> testigo 10 rojo parpadeante cada 300 ms hasta
     falla_frenos=0", sin ninguna condicion de motor;
   - R01 solo regula las lecturas continuas (velocidad, RPM, temperatura,
     presion de aceite y turbo);
   - el elemento 10 esta clasificado como alerta CRITICA.

   El comportamiento original cumplia R08. Se rechazo el defecto, se revirtio el
   cambio de la Etapa 7 y CP-66 ahora verifica que el testigo 10 parpadea con el
   motor apagado y se apaga con falla_frenos=0.

**Leccion aprendida:** la expectativa de un caso de prueba debe salir de la
especificacion, no de la consistencia interna del codigo.
