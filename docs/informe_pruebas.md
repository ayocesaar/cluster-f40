# Informe de pruebas - Cluster F40

## 1. Objetivo

Verificar que la logica del cluster de instrumentos simulado del Ferrari F40
(`logic/estado.py` y `logic/reloj.py`) cumple las reglas R01 a R08, mediante
pruebas automatizadas con pytest y medicion de cobertura con coverage.

## 2. Alcance

- Incluido: `logic/estado.py` (EstadoCluster, reglas R01-R08) y `logic/reloj.py`
  (RelojReal, RelojSimulado).
- Pendiente: la interfaz grafica (`ui/tablero.py`) y `main.py` aun no existen;
  sus pruebas (incluidas las de aceptacion) se agregaran al implementarlas.
- El tiempo se controla con `RelojSimulado`, de modo que las pruebas de ciclos,
  parpadeos e histeresis son deterministas y no dependen de esperas reales.

## 3. Entorno

- Sistema: Linux 5.15.0-190-generic
- Python: 3.10.12
- pytest: 9.2.0
- coverage: 7.16.2

## 4. Tecnicas y resultados

| Tecnica | Ejecuciones | Pasaron | Fallaron | XFAIL |
|---------|-------------|---------|----------|-------|
| Caja blanca (cobertura) | 13 | 13 | 0 | 0 |
| Entradas invalidas | 15 | 15 | 0 | 0 |
| Valores limite | 16 | 16 | 0 | 0 |
| Particion de equivalencia | 10 | 10 | 0 | 0 |
| Basada en requisitos | 3 | 3 | 0 | 0 |
| Transicion de estados | 11 | 11 | 0 | 0 |
| **Total** | **68** | **68** | **0** | **0** |

Las ejecuciones cuentan cada variante parametrizada por separado; la matriz de
trazabilidad agrupa por caso de prueba (CP).

## 5. Cobertura (lineas y ramas)

| Modulo | Lineas | Ramas | Cobertura |
|--------|--------|-------|-----------|
| `logic/estado.py` | 187/187 | 66/66 | 100.0% |
| `logic/reloj.py` | 18/18 | 4/4 | 100.0% |

## 6. Trazabilidad

Cada caso de prueba esta asociado a los requisitos que verifica en
`docs/matriz_trazabilidad.md`, generada automaticamente desde los docstrings
de las pruebas y el resultado de junit.

- Requisitos sin casos: ninguno

## 7. Defectos

- Defectos registrados: 1
- Defectos cerrados: 1
- DEF-01: el testigo de falla de frenos parpadeaba con el motor apagado
  (R01/R08). Se corrigio en `logic/estado.py` y CP-66 queda como prueba de
  regresion. Detalle en `docs/registro_defectos.md`.

## 8. Decisiones de diseno y observaciones

- Al apagar el motor (R01) se apagan tambien el testigo 9 y el ambar del
  elemento 2, reiniciando sus temporizadores; de lo contrario se encenderian
  falsamente porque R01 fuerza p_aceite a 0 (nota de diseno en `estado.py`).
- La velocidad no tiene una regla especifica en R01-R08; se valida como entrada
  (rangos, tipos y valores limite).
- Los casos CP-60 a CP-63 prueban la infraestructura de tiempo (reloj) y no
  se asocian a un requisito funcional.

## 9. Evidencias

- `docs/evidencias/pytest.txt`: salida completa de pytest -v.
- `docs/evidencias/junit.xml`: resultados en formato JUnit.
- `docs/evidencias/coverage.txt` y `coverage.json`: reporte de cobertura.
- `htmlcov/index.html`: reporte de cobertura navegable.
- `docs/matriz_trazabilidad.md` y `docs/registro_defectos.md`.

## 10. Conclusion

Las 68 ejecuciones pasan, la cobertura de la logica es completa y no quedan defectos abiertos: la logica cumple R01-R08 segun las pruebas definidas.
