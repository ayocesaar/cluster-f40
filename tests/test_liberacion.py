"""Pruebas del banco de liberacion de produccion (panel/liberacion.py y tools/banco_liberacion.py):
formulas de las normas, perfil del ciclo ECE-15, dictamen de la unidad sana y matriz falla -> prueba."""

import pathlib
import sys

import pytest

from panel import liberacion as L

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def test_cp179_formulas_de_las_normas():
    """CP-179: las formulas de R13-H y R39 dan los valores del texto de la norma: tipo 0 a 100 km/h <= 70 m, dm de un caso calculado a mano, v1 = 120 y v2 = 60 km/h en el tipo I y los limites del velocimetro a 40, 80 y 120 km/h."""
    assert L.distancia_tipo0(100) == pytest.approx(70.0)
    assert L.desaceleracion_media(80, 10, 5.0, 35.0) == pytest.approx(6300 / (25.92 * 30))
    assert L.desaceleracion_media(80, 10, 5.0, 35.0) == pytest.approx(8.102, abs=0.001)
    assert L.velocidades_tipo1(343.0) == (120.0, 60.0) and L.velocidades_tipo1(100.0) == (80.0, 40.0)
    assert [L.limite_r39(v) for v in L.R39_VELOCIDADES] == pytest.approx([8.0, 12.0, 16.0])
    assert L.limite_r39(100.0, produccion=True) == pytest.approx(16.0)


def test_cp180_perfil_del_ciclo_ece15():
    """CP-180: el perfil del ciclo urbano ECE-15 dura 195 s, llega a 50 km/h y su distancia integrada es 994.03 m."""
    assert L.ECE15[-1][0] == L.DURACION_ECE15_S == 195
    assert max(v for _, v in L.ECE15) == 50
    distancia = sum((t1 - t0) * (v0 + v1) / 2 for (t0, v0), (t1, v1) in zip(L.ECE15, L.ECE15[1:])) / 3600
    assert distancia == pytest.approx(L.DISTANCIA_ECE15_KM, abs=1e-5)
    assert L.interpolar(L.ECE15, 13) == pytest.approx(7.5) and L.interpolar(L.ECE15, 300) == 0


def test_cp181_unidad_sana_apta_para_produccion():
    """CP-181: la unidad sin fallas aprueba las 9 pruebas del banco y el odometro del cuadro mide el ciclo ECE-15 con menos de 1 % de error: APTO PARA PRODUCCION."""
    resultados = L.ejecutar_banco({})
    assert [r.clave for r in resultados] == [f"L0{i}" for i in range(1, 10)]
    assert all(r.aprobado for r in resultados), [(r.clave, r.medido) for r in resultados if not r.aprobado]
    assert L.dictamen(resultados).startswith("APTO PARA PRODUCCION")
    _, cuadro, error, km, avisos = L.recorrer_ece15({}, odometro_km=62.0)
    assert abs(cuadro.estado.odometro.km - 62.0 - km) / km < 0.01 and error <= 2.0 and not avisos
    assert cuadro.estado.odometro.texto == "000062"


@pytest.mark.parametrize("falla, detectan", [
    ("fuga_aceite", {"L01"}), ("radiador", {"L07"}), ("sobrepresion_turbo", {"L08"}),
    ("frenos", {"L02", "L03", "L04"}), ("velocimetro", {"L05", "L06"})])
def test_cp182_cada_falla_la_rechaza_la_prueba_de_su_sistema(falla, detectan):
    """CP-182: cada falla del panel deja la unidad RECHAZADA y la detecta la prueba de su sistema: aceite en el arranque, radiador en el enfriamiento, turbo a plena carga, frenos en testigos, tipo 0 y tipo I, y velocimetro en R39 y el odometro."""
    resultados = L.ejecutar_banco({falla: True})
    fallidas = {r.clave for r in resultados if not r.aprobado}
    assert detectan <= fallidas and L.dictamen(resultados).startswith("RECHAZADO")


def test_cp183_herramienta_del_banco_deja_evidencia(tmp_path):
    """CP-183: tools/banco_liberacion.py --evidencia escribe el reporte con la matriz falla -> prueba y termina con 0 porque el banco distingue la unidad sana de cada falla; con una falla termina con 1."""
    sys.path.insert(0, str(RAIZ / "tools"))
    import banco_liberacion
    salida = tmp_path / "banco.txt"
    assert banco_liberacion.main(["--evidencia", "--salida", str(salida)]) == 0
    texto = salida.read_text(encoding="utf-8")
    assert "MATRIZ" in texto and "el banco distingue" in texto
    assert texto.count("DICTAMEN: RECHAZADO") == len(L.FALLAS) and texto.count("DICTAMEN: APTO") == 1
    assert banco_liberacion.main(["--falla", "frenos"]) == 1
    assert banco_liberacion.main([]) == 0
