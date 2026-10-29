"""Pruebas basadas en requisitos: cierran los huecos detectados en la matriz
de trazabilidad (Etapa 5) para R01, R07 y R08."""


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


def test_cp66_frenos_parpadea_aun_con_motor_apagado(estado, reloj):
    """CP-66: el testigo 10 (critico) parpadea cada 300 ms aunque el motor este apagado y se apaga con falla_frenos=0 (R01, R08)."""
    estado.set_falla_frenos(True)
    estados = []
    for _ in range(4):
        estados.append(estado.testigo_falla_frenos_encendido)
        reloj.avanzar(300)
    assert estados == [True, False, True, False]

    estado.set_falla_frenos(False)
    assert estado.testigo_falla_frenos_encendido is False
