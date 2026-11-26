"""Pruebas de la Etapa 22: datos verificados del F40 y textos de las normas de la epoca. Velocidades por
marcha con las relaciones de la caja, frenado calibrado con la prueba publicada, criterio de frenado de la
Directiva 71/320/CEE vigente en 1987, tolerancia de UN R84 en el ciclo urbano y consumo por potencia
contra el consumo normalizado del fabricante."""

import pathlib
import sys

import pytest

from panel import liberacion as L
from panel.fisica import (CORTE, MASA_KG, RALENTI, RELACIONES, TANQUE_L, VELOCIDAD_AL_CORTE, Fallas, Vehiculo,
                          velocidad_maxima)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DT = 0.05


def test_cp210_velocidades_por_marcha_con_las_relaciones_verificadas():
    """CP-210: la velocidad de cada marcha a la linea roja (7750 rpm) sigue las relaciones verificadas de la caja (2.769, 1.722, 1.227, 0.963 y 0.767): velocidad x relacion es la misma en las cinco; 1a a 90 km/h y 2a y 3a como la prueba citada (144 y 201 km/h entre 7400 y 7700 rpm, a 2 % o menos); 5a cerca de la maxima publicada de 324 km/h."""
    assert CORTE == 7750 and RALENTI == 1000
    producto = {m: VELOCIDAD_AL_CORTE[m] * r for m, r in RELACIONES.items()}
    assert max(producto.values()) - min(producto.values()) < 0.2
    assert VELOCIDAD_AL_CORTE["1"] == 90.0
    assert VELOCIDAD_AL_CORTE["2"] == pytest.approx(144.0, rel=0.02)
    assert VELOCIDAD_AL_CORTE["3"] == pytest.approx(201.0, rel=0.02)
    assert VELOCIDAD_AL_CORTE["5"] == pytest.approx(324.0, abs=1.0)
    assert velocidad_maxima("5") > VELOCIDAD_AL_CORTE["5"]
    v = Vehiculo(motor=True)
    v.cambiar("3")
    v.velocidad = 100.0
    v.avanzar(DT)
    assert v.rpm == pytest.approx(v.velocidad * CORTE / VELOCIDAD_AL_CORTE["3"])


def _detener(v0, fallas=None):
    v = Vehiculo(motor=True, velocidad=v0, fallas=fallas or Fallas())
    v.freno, metros = 1.0, 0.0
    while v.velocidad > 0:
        antes = v.velocidad
        v.avanzar(DT)
        metros += (antes + v.velocidad) / 2 / 3.6 * DT
    return metros


def test_cp211_frenado_calibrado_y_directiva_71_320_de_1987():
    """CP-211: con el freno a fondo el modelo para de 60 mph (96.56 km/h) en 36.3 m +- 1 m, como la prueba publicada (119 ft); la formula de la Directiva 71/320/CEE vigente en 1987 para M1 da 50.7 m a 80 km/h; L03 exige ese criterio y el de R13-H: la unidad sana pasa los dos y con un circuito perdido falla los dos."""
    assert _detener(96.56) == pytest.approx(36.3, abs=1.0)
    assert L.distancia_tipo0_1987(80) == pytest.approx(8 + 6400 / 150)
    assert L.V_TIPO0_1987 == 80.0 and L.DM_TIPO0_1987 == 5.8
    sana = L.prueba_tipo0({})
    assert sana.aprobado and "71/320" in sana.norma and "desde 80 km/h" in sana.medido
    s80 = _detener(80.0)
    assert s80 < L.distancia_tipo0_1987(80) and 80.0 ** 2 / (25.92 * s80) >= 5.8
    con_falla = _detener(80.0, Fallas(frenos=True))
    assert con_falla > L.distancia_tipo0_1987(80) and not L.prueba_tipo0({"frenos": True}).aprobado


def test_cp212_consumo_por_potencia():
    """CP-212: el consumo sale de la potencia entregada: 2 L/h en ralenti, mas con las rpm y mucho mas a plena carga; a velocidad constante gasta mas a 120 que a 90 km/h; la masa sigue el peso en orden de marcha publicado (1250 kg) mas la carga de prueba."""
    v = Vehiculo(motor=True)
    for _ in range(40):
        v.avanzar(DT)
    assert v.rpm == RALENTI and v.potencia_kw == 0.0 and v.consumo_lh() == pytest.approx(2.0)
    v.acelerador = 0.5
    for _ in range(40):
        v.avanzar(DT)
    assert v.potencia_kw == 0.0 and v.consumo_lh() > 2.0           # en neutral: solo las rpm
    plena = Vehiculo(motor=True, velocidad=150.0)
    plena.cambiar("3")
    plena.presion_turbo, plena.acelerador = 1.1, 1.0
    for _ in range(3):                                            # el primer paso fija las rpm de 3a
        plena.avanzar(DT)
    assert plena.potencia_kw > 200 and plena.consumo_lh() > 60
    assert Vehiculo().consumo_lh() == 0.0
    c90, d90 = L.consumo_constante(90.0, segundos=30)
    c120, d120 = L.consumo_constante(120.0, segundos=30)
    assert c120 > c90 > 0 and d90 <= 2.0 and d120 <= 2.0
    assert 1250 <= MASA_KG <= 1400 and TANQUE_L == 120.0


def test_cp213_tolerancia_r84_del_ciclo_urbano():
    """CP-213: la tolerancia de UN R84 (+-1 km/h con +-0.5 s, fuera a lo mas 0.5 s seguidos) acepta seguir el perfil con un retraso de 0.4 s y rechaza ir 1.5 km/h abajo durante 1 s; el robot del banco recorre el ECE-15 sin salir de ella y L06 la exige."""
    perfil = [(t * DT, L.interpolar(L.ECE15, t * DT)) for t in range(int(195 / DT))]
    assert L.fuera_de_tolerancia_r84(perfil, dt=DT) == 0.0
    retrasado = [(t, L.interpolar(L.ECE15, max(0.0, t - 0.4))) for t, _ in perfil]
    assert L.fuera_de_tolerancia_r84(retrasado, dt=DT) == 0.0
    abajo = [(t, v - 1.5 if 70 <= t < 71 else v) for t, v in perfil]
    assert L.fuera_de_tolerancia_r84(abajo, dt=DT) == pytest.approx(1.0, abs=DT + 1e-9)
    historia = []
    L.recorrer_ece15({}, historia=historia)
    assert len(historia) >= 3899 and L.fuera_de_tolerancia_r84(historia, dt=DT) <= L.FUERA_MAXIMO_S
    l06 = L.prueba_ece15({})
    assert l06.aprobado and "R84" in l06.norma and "+-0.5 s" in l06.criterio
    assert L.TOLERANCIA_SEGUIMIENTO_KMH == 1.0 and L.TOLERANCIA_TIEMPO_S == 0.5


def test_cp214_consumo_normalizado_contra_el_fabricante(tmp_path):
    """CP-214: las tres pruebas de consumo de UN R84 sobre el modelo (4 ciclos urbanos, 90 y 120 km/h) quedan a +-10 % del consumo del fabricante que publica ADAC (18.4, 8.6 y 10.3 L/100 km); tools/consumo.py deja la evidencia y termina con 0."""
    resultados = L.consumo_normalizado()
    assert [r[0] for r in resultados] == ["ciudad", "90 km/h", "120 km/h"]
    assert [r[2] for r in resultados] == [18.4, 8.6, 10.3]
    assert all(r[3] for r in resultados), resultados
    assert resultados[0][1] > resultados[2][1] > resultados[1][1]     # la ciudad gasta mas que la carretera
    sys.path.insert(0, str(RAIZ / "tools"))
    import consumo
    salida = tmp_path / "consumo.txt"
    assert consumo.main(["--salida", str(salida)]) == 0
    texto = salida.read_text(encoding="utf-8")
    assert "3/3 pruebas de consumo dentro de la tolerancia" in texto and "ADAC" in texto
