"""Pruebas basadas en requisitos: cierran los huecos detectados en la matriz
de trazabilidad (Etapa 5) para R01, R07 y R08."""

import pytest


def test_cp64_luces_altas_fijas_sin_parpadeo(estado_encendido, reloj):
    """CP-64: con motor encendido las luces altas quedan fijas, sin parpadeo (R07)."""
    estado_encendido.set_luces_altas(True)
    for _ in range(4):
        assert estado_encendido.testigo_luces_altas_encendido is True
        reloj.avanzar(250)


def test_cp65_luces_altas_apagadas_con_motor_apagado(estado):
    """CP-65: con el motor apagado el testigo de luces altas no enciende (R01, R07)."""
    estado.set_luces_altas(True)
    assert estado.testigo_luces_altas_encendido is False


@pytest.mark.xfail(strict=True, reason="DEF-01: el testigo de frenos no considera el motor apagado")
def test_cp66_frenos_apagado_con_motor_apagado(estado, reloj):
    """CP-66: con el motor apagado el testigo de falla de frenos no enciende (R01, R08)."""
    estado.set_falla_frenos(True)
    for _ in range(4):
        assert estado.testigo_falla_frenos_encendido is False
        reloj.avanzar(300)
