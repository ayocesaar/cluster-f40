# Informe de pruebas - Cluster F40

## 1. Objetivo

Verificar que la logica del cluster de instrumentos simulado del Ferrari F40
(`logic/estado.py` y `logic/reloj.py`) cumple las reglas R01 a R08, mediante
pruebas automatizadas con pytest y medicion de cobertura con coverage.

## 2. Alcance

- Incluido: `logic/estado.py` (EstadoCluster, reglas R01-R08) y `logic/reloj.py`
  (RelojReal, RelojSimulado).
- Incluido: `ui/presentacion.py` (lo que se dibuja de cada elemento),
  `ui/tablero.py` y `main.py` (interfaz Tkinter), probados con Tkinter real
  sobre una pantalla virtual (Xvfb).
- Incluido: pruebas de aceptacion CA-01 a CA-10 sobre la interfaz real,
  dirigidas por `tests/datos/escenarios_aceptacion.csv` (`aceptacion/escenarios.py`).
- Evidencia visual: capturas reales de la interfaz en `docs/evidencias/capturas/`
  (generadas con `tools/capturas.py` sobre Xvfb).
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
| Aceptacion (dirigida por datos) | 27 | 27 | 0 | 0 |
| Caja blanca (cobertura) | 13 | 13 | 0 | 0 |
| Entradas invalidas | 15 | 15 | 0 | 0 |
| Valores limite | 16 | 16 | 0 | 0 |
| Particion de equivalencia | 10 | 10 | 0 | 0 |
| Presentacion (caja negra) | 7 | 7 | 0 | 0 |
| Basada en requisitos | 3 | 3 | 0 | 0 |
| Integracion UI (Tkinter) | 6 | 6 | 0 | 0 |
| Transicion de estados | 11 | 11 | 0 | 0 |
| **Total** | **108** | **108** | **0** | **0** |

Las ejecuciones cuentan cada variante parametrizada por separado; la matriz de
trazabilidad agrupa por caso de prueba (CP).

## 5. Cobertura (lineas y ramas)

| Modulo | Lineas | Ramas | Cobertura |
|--------|--------|-------|-----------|
| `logic/estado.py` | 185/185 | 64/64 | 100.0% |
| `logic/reloj.py` | 18/18 | 4/4 | 100.0% |
| `ui/presentacion.py` | 19/19 | 0/0 | 100.0% |
| `ui/tablero.py` | 211/211 | 54/54 | 100.0% |
| `main.py` | 15/15 | 1/2 | 94.1% |
| `aceptacion/escenarios.py` | 131/131 | 40/40 | 100.0% |

## 6. Trazabilidad

Cada caso de prueba esta asociado a los requisitos que verifica en
`docs/matriz_trazabilidad.md`, generada automaticamente desde los docstrings
de las pruebas y el resultado de junit.

- Requisitos sin casos: ninguno

## 7. Defectos

- Defectos registrados: 1
- Defectos abiertos: 0
- DEF-01 (testigo 10 parpadeando con el motor apagado) fue rechazado: R08
  no condiciona el testigo al motor. Se revirtio la correccion de la Etapa 7
  y CP-66 verifica el comportamiento correcto. Detalle en
  `docs/registro_defectos.md`.

## 8. Decisiones de diseno y observaciones

- Al apagar el motor (R01) se apagan tambien el testigo 9 y el ambar del
  elemento 2, reiniciando sus temporizadores; de lo contrario se encenderian
  falsamente porque R01 fuerza p_aceite a 0 (nota de diseno en `estado.py`).
- Los testigos informativos 6, 7 y 8 solo se muestran con el motor encendido;
  es el estado definido que R01 deja abierto (decision D2).
- El testigo 10 (critico) parpadea mientras falla_frenos=1 aunque el motor
  este apagado, porque R08 no lo condiciona al motor (decision D1).
- La especificacion distingue Encendido (elementos 1 y 4) y Motor activo
  (elementos 2, 3 y 5); el sistema usa un solo interruptor motor que
  representa ambas senales (decision D3).
- R02 se interpreta como tiempo continuo: entre 1.0 y 1.2 bar se reinician
  ambos temporizadores, asi que una presion que oscila entre 0.9 y 1.1 bar
  no enciende el testigo 9.
- La velocidad no tiene una regla especifica en R01-R08; se valida como entrada
  (rangos, tipos y valores limite).
- Los casos CP-60 a CP-63 prueban la infraestructura de tiempo (reloj) y no
  se asocian a un requisito funcional.

## 9. Evidencias

- `docs/evidencias/pytest.txt`: salida completa de pytest -v.
- `docs/evidencias/junit.xml`: resultados en formato JUnit.
- `docs/evidencias/aceptacion.txt`: salida paso a paso de CA-01 a CA-10.
- `docs/evidencias/capturas/` e indice `docs/evidencias/capturas.txt`.
- `docs/evidencias/coverage.txt` y `coverage.json`: reporte de cobertura.
- `docs/evidencias/htmlcov/index.html`: reporte de cobertura navegable.
- `docs/matriz_trazabilidad.md` y `docs/registro_defectos.md`.

## 10. Conclusion

Las 108 ejecuciones pasan, la cobertura de la logica es completa y no quedan defectos abiertos: la logica cumple R01-R08 segun las pruebas definidas.
