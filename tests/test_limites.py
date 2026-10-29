"""Pruebas de valores limite segun la especificacion."""


def test_cp11_velocidad_limite_inferior_0(estado_encendido, reloj):
    """CP-11: 0 km/h es el limite inferior valido."""
    estado_encendido.set_velocidad(0)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.velocidad == 0


def test_cp12_velocidad_limite_superior_360(estado_encendido, reloj):
    """CP-12: 360 km/h es el limite superior valido."""
    estado_encendido.set_velocidad(360)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.velocidad == 360


def test_cp13_rpm_7799_no_activa_rojo(estado_encendido, reloj):
    """CP-13: 7799 rpm no activa rojo. [R03]"""
    estado_encendido.set_rpm(7799)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "normal"


def test_cp14_rpm_7800_zona_muerta_conserva_normal(estado_encendido, reloj):
    """CP-14: 7800 rpm (zona muerta) conserva el estado previo (normal). [R03]"""
    estado_encendido.set_rpm(7800)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "normal"


def test_cp15_rpm_7999_conserva_rojo_si_ya_estaba_rojo(estado_encendido, reloj):
    """CP-15: en zona muerta (7999) se conserva el estado previo, partiendo de rojo. [R03]"""
    estado_encendido.set_rpm(8000)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "rojo"

    estado_encendido.set_rpm(7999)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "rojo"


def test_cp16_rpm_8000_activa_rojo(estado_encendido, reloj):
    """CP-16: 8000 rpm activa el indicador rojo (R03)."""
    estado_encendido.set_rpm(8000)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "rojo"


def test_cp17_aceite_099_bar_999ms_no_activa_testigo(estado_encendido, reloj):
    """CP-17: 0.99 bar sostenido 999 ms NO activa el testigo 9 todavia. [R02]"""
    estado_encendido.set_presion_aceite(0.99)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(899)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is False


def test_cp18_aceite_099_bar_1000ms_activa_testigo(estado_encendido, reloj):
    """CP-18: 0.99 bar sostenido >= 1000 ms SI activa el testigo 9 (R02)."""
    estado_encendido.set_presion_aceite(0.99)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(900)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is True


def test_cp19_aceite_10_bar_zona_muerta_no_activa(estado_encendido, reloj):
    """CP-19: 1.0 bar esta en zona muerta: no activa el testigo aunque pase tiempo. [R02]"""
    estado_encendido.set_presion_aceite(1.0)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(2000)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is False


def test_cp20_aceite_12_bar_1000ms_apaga_testigo(estado_encendido, reloj):
    """CP-20: 1.2 bar sostenido >= 1 s apaga el testigo 9 (histeresis, R02)."""
    estado_encendido.set_presion_aceite(0.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(1000)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is True

    estado_encendido.set_presion_aceite(1.2)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(1000)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is False


def test_cp21_temp_105_normal(estado_encendido, reloj):
    """CP-21: 105 C: limite donde regresa a normal. [R04]"""
    estado_encendido.set_temp_agua(105)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.color_temp == "normal"


def test_cp22_temp_110_zona_muerta_conserva_previo(estado_encendido, reloj):
    """CP-22: 110 C esta en zona muerta: conserva estado previo (normal). [R04]"""
    estado_encendido.set_temp_agua(110)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.color_temp == "normal"


def test_cp23_temp_1101_activa_rojo(estado_encendido, reloj):
    """CP-23: 110.1 C activa el indicador rojo (R04)."""
    estado_encendido.set_temp_agua(110.1)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.color_temp == "rojo"


def test_cp24_turbo_14_normal(estado_encendido, reloj):
    """CP-24: 1.4 bar: limite donde el contorno regresa a normal. [R05]"""
    estado_encendido.set_presion_turbo(1.4)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.contorno_turbo == "normal"


def test_cp25_turbo_15_zona_muerta_conserva_previo(estado_encendido, reloj):
    """CP-25: 1.5 bar esta en zona muerta: conserva estado previo (normal). [R05]"""
    estado_encendido.set_presion_turbo(1.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.contorno_turbo == "normal"


def test_cp26_turbo_151_activa_ambar(estado_encendido, reloj):
    """CP-26: 1.51 bar activa el contorno ambar (R05)."""
    estado_encendido.set_presion_turbo(1.51)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.contorno_turbo == "ambar"
