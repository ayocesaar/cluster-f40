# Registro de defectos - Cluster F40

## DEF-01 - El testigo de falla de frenos parpadea con el motor apagado

| Campo | Valor |
|-------|-------|
| ID | DEF-01 |
| Estado | Cerrado (corregido en Etapa 7) |
| Severidad | Media |
| Prioridad | Media |
| Requisitos afectados | R01 (encendido/apagado general), R08 (testigo de falla de frenos) |
| Componente | `logic/estado.py`, propiedad `testigo_falla_frenos_encendido` |
| Detectado en | Etapa 4 (revision de codigo durante pruebas de caja blanca) |
| Caso de prueba | CP-66 (`tests/test_requisitos.py`), marcado `xfail` hasta la correccion; hoy funciona como prueba de regresion |

**Pasos para reproducir**

1. Crear `EstadoCluster` con el motor apagado (estado inicial).
2. Llamar `set_falla_frenos(True)`.
3. Leer `testigo_falla_frenos_encendido` en t = 0 ms y cada 300 ms.

**Resultado esperado:** `False` en todo momento. R01 define un apagado general y
el resto de los testigos (direccionales, emergencia, luces altas, aceite)
se apaga con el motor apagado.

**Resultado obtenido:** `True` en t = 0 ms; el testigo alterna cada 300 ms
aunque el motor este apagado.

**Causa raiz:** la propiedad `testigo_falla_frenos_encendido` no verifica
`self._motor`, a diferencia de los demas testigos.

**Correccion propuesta:** agregar `if not self._motor: return False` al inicio
de la propiedad y quitar la marca `xfail` de CP-66 para que funcione como
prueba de regresion.

## Resolucion de DEF-01

- Cambio: se agrego `if not self._motor: return False` al inicio de
  `testigo_falla_frenos_encendido` en `logic/estado.py`.
- Verificacion: se retiro la marca `xfail` de CP-66; CP-66 pasa y la suite
  completa (CP-01 a CP-66) pasa sin regresiones.
- Evidencia antes de la correccion: commit `daad491` (67 passed, 1 xfailed).
- Evidencia despues de la correccion: `docs/evidencias/pytest.txt` y
  `docs/evidencias/junit.xml` del commit de la Etapa 7.
