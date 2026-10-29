"""Pruebas de particion de equivalencia para las lecturas continuas.

Cada caso valida que un valor tipico dentro del rango valido se aplique
correctamente tras transcurrir el ciclo correspondiente. Las particiones
invalidas se cubren en test_invalidas.py.
"""


def test_cp01_velocidad_valida_se_aplica(estado_encendido, reloj):
    """CP-01: velocidad dentro de 0-360 se aplica tras su ciclo (100 ms)."""
    estado_encendido.set_velocidad(120.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.velocidad == 120.5


def test_cp02_rpm_valido_se_aplica(estado_encendido, reloj):
    """CP-02: rpm entero dentro de 0-9000 se aplica tras su ciclo (100 ms). [R03]"""
    estado_encendido.set_rpm(4500)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.rpm == 4500


def test_cp03_presion_aceite_valida_se_aplica(estado_encendido, reloj):
    """CP-03: presion de aceite dentro de 0-10 se aplica tras su ciclo (100 ms). [R02]"""
    estado_encendido.set_presion_aceite(5.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.p_aceite == 5.5


def test_cp04_temp_agua_valida_se_aplica(estado_encendido, reloj):
    """CP-04: temperatura de agua dentro de 40-130 se aplica tras su ciclo (500 ms). [R04]"""
    estado_encendido.set_temp_agua(90.0)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.temp_agua == 90.0


def test_cp05_presion_turbo_valida_se_aplica(estado_encendido, reloj):
    """CP-05: presion de turbo dentro de 0-2 se aplica tras su ciclo (100 ms). [R05]"""
    estado_encendido.set_presion_turbo(1.0)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.p_turbo == 1.0


def test_cp06_direccional_izq_valida(estado_encendido):
    """CP-06: direccional IZQ es un valor valido. [R06]"""
    estado_encendido.set_direccional("IZQ")
    assert estado_encendido.direccional == "IZQ"


def test_cp07_direccional_der_valida(estado_encendido):
    """CP-07: direccional DER es un valor valido. [R06]"""
    estado_encendido.set_direccional("DER")
    assert estado_encendido.direccional == "DER"


def test_cp08_direccional_off_valida(estado_encendido):
    """CP-08: direccional OFF es un valor valido (estado seguro). [R06]"""
    estado_encendido.set_direccional("OFF")
    assert estado_encendido.direccional == "OFF"


def test_cp09_interruptores_booleanos_validos(estado_encendido):
    """CP-09: los interruptores aceptan True/False. [R07, R08]"""
    estado_encendido.set_luces_altas(True)
    estado_encendido.set_emergencia(False)
    estado_encendido.set_falla_frenos(True)
    assert estado_encendido.testigo_luces_altas_encendido is True
    assert estado_encendido.testigo_emergencia_encendido is False
    assert estado_encendido.testigo_falla_frenos_encendido is True


def test_cp10_velocidad_cero_particion_valida(estado_encendido, reloj):
    """CP-10: 0 km/h es parte de la particion valida."""
    estado_encendido.set_velocidad(0)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.velocidad == 0
