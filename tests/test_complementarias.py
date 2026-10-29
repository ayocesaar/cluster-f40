"""Pruebas complementarias de caja blanca: cubren las ramas que la suite
de caja negra (CP-01 a CP-52) no ejercia, segun el reporte de coverage."""

import pytest
from logic.reloj import RelojReal


def test_cp53_motor_activo_refleja_set_motor(estado):
    """CP-53: motor_activo refleja el ultimo valor de set_motor."""
    assert estado.motor_activo is False
    estado.set_motor(True)
    assert estado.motor_activo is True
    estado.set_motor(False)
    assert estado.motor_activo is False


def test_cp54_color_aceite_motor_apagado_normal(estado):
    """CP-54: con el motor apagado el elemento 2 siempre es normal."""
    assert estado.color_aceite == "normal"


def test_cp55_color_aceite_bajo_1_bar_ambar_inmediato(estado_encendido, reloj):
    """CP-55: p_aceite < 1 bar pone el elemento 2 en ambar sin esperar 1 s."""
    estado_encendido.set_presion_aceite(0.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_aceite == "ambar"


def test_cp56_color_aceite_1_bar_normal(estado_encendido, reloj):
    """CP-56: p_aceite = 1.0 bar deja el elemento 2 en normal."""
    estado_encendido.set_presion_aceite(1.0)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_aceite == "normal"


def test_cp57_direccional_off_no_parpadea(estado_encendido, reloj):
    """CP-57: con direccional OFF y motor encendido el testigo 6 nunca enciende (R06)."""
    estado_encendido.set_direccional("OFF")
    for _ in range(4):
        assert estado_encendido.testigo_direccional_encendido is False
        reloj.avanzar(500)


def test_cp58_emergencia_desactivada_no_parpadea(estado_encendido, reloj):
    """CP-58: con emergencia desactivada y motor encendido el testigo 8 nunca enciende (R07)."""
    estado_encendido.set_emergencia(False)
    for _ in range(4):
        assert estado_encendido.testigo_emergencia_encendido is False
        reloj.avanzar(500)


def test_cp59_falla_frenos_desactivada_no_parpadea(estado_encendido, reloj):
    """CP-59: sin falla de frenos el testigo nunca enciende (R08)."""
    estado_encendido.set_falla_frenos(False)
    for _ in range(4):
        assert estado_encendido.testigo_falla_frenos_encendido is False
        reloj.avanzar(300)


def test_cp60_reloj_real_arranca_en_cero_y_no_retrocede():
    """CP-60: RelojReal arranca cerca de 0 ms y es monotono."""
    r = RelojReal()
    t1 = r.ahora_ms()
    t2 = r.ahora_ms()
    assert 0 <= t1 < 1000
    assert t2 >= t1


@pytest.mark.parametrize("valor", ["100", None, True])
def test_cp61_reloj_simulado_rechaza_tipo_invalido(reloj, valor):
    """CP-61: avanzar() rechaza str, None y bool con TypeError."""
    with pytest.raises(TypeError):
        reloj.avanzar(valor)


def test_cp62_reloj_simulado_rechaza_negativo(reloj):
    """CP-62: avanzar() rechaza milisegundos negativos con ValueError."""
    with pytest.raises(ValueError):
        reloj.avanzar(-1)
    assert reloj.ahora_ms() == 0


def test_cp63_reloj_simulado_acumula(reloj):
    """CP-63: avanzar() acumula y devuelve el total (int y float)."""
    assert reloj.avanzar(100) == 100
    assert reloj.avanzar(50.5) == 150.5
    assert reloj.ahora_ms() == 150.5
