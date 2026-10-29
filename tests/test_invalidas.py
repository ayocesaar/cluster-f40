"""Pruebas de entradas invalidas: fuera de rango, tipos incorrectos y
direccional desconocido. En todos los casos el estado no debe cambiar."""

import pytest


def test_cp38_velocidad_fuera_rango_negativa(estado):
    """CP-38: velocidad negativa es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_velocidad(-1)


def test_cp39_velocidad_fuera_rango_superior(estado):
    """CP-39: velocidad > 360 es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_velocidad(361)


def test_cp40_rpm_tipo_float_invalido(estado):
    """CP-40: rpm debe ser entero; un float se rechaza con TypeError."""
    with pytest.raises(TypeError):
        estado.set_rpm(5000.0)


def test_cp41_rpm_tipo_bool_invalido(estado):
    """CP-41: rpm no acepta bool."""
    with pytest.raises(TypeError):
        estado.set_rpm(True)


def test_cp42_rpm_fuera_rango(estado):
    """CP-42: rpm > 9000 es invalido (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_rpm(9001)


def test_cp43_presion_aceite_fuera_rango(estado):
    """CP-43: presion de aceite > 10 es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_presion_aceite(10.1)


def test_cp44_presion_aceite_tipo_invalido(estado):
    """CP-44: presion de aceite no acepta str (TypeError)."""
    with pytest.raises(TypeError):
        estado.set_presion_aceite("alta")


def test_cp45_temp_agua_fuera_rango_inferior(estado):
    """CP-45: temperatura < 40 es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_temp_agua(39.9)


def test_cp46_temp_agua_fuera_rango_superior(estado):
    """CP-46: temperatura > 130 es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_temp_agua(130.1)


def test_cp47_presion_turbo_fuera_rango(estado):
    """CP-47: presion de turbo > 2 es invalida (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_presion_turbo(2.1)


def test_cp48_presion_turbo_bool_invalido(estado):
    """CP-48: presion de turbo no acepta bool (TypeError)."""
    with pytest.raises(TypeError):
        estado.set_presion_turbo(True)


def test_cp49_direccional_desconocido(estado):
    """CP-49: un direccional fuera de OFF/IZQ/DER es invalido (ValueError)."""
    with pytest.raises(ValueError):
        estado.set_direccional("ADELANTE")


def test_cp50_direccional_tipo_invalido(estado):
    """CP-50: direccional debe ser str; un entero se rechaza (TypeError)."""
    with pytest.raises(TypeError):
        estado.set_direccional(1)


def test_cp51_motor_tipo_invalido(estado):
    """CP-51: motor debe ser bool; un int se rechaza (TypeError)."""
    with pytest.raises(TypeError):
        estado.set_motor(1)


def test_cp52_entrada_rechazada_no_cambia_estado(estado):
    """CP-52: una entrada rechazada no modifica el objetivo previo."""
    estado.set_velocidad(100)
    with pytest.raises(ValueError):
        estado.set_velocidad(500)
    estado.set_motor(True)
    estado.tick()
    assert estado._obj_velocidad == 100
