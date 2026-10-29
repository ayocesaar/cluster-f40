"""Pruebas de transicion de estados: histeresis, parpadeos y encendido/apagado."""


def test_cp27_rpm_histeresis_sube_y_baja(estado_encendido, reloj):
    """CP-27: el indicador de rpm sube a rojo en 8000 y baja a normal en 7799."""
    estado_encendido.set_rpm(8000)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "rojo"

    estado_encendido.set_rpm(7900)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "rojo"

    estado_encendido.set_rpm(7799)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.color_rpm == "normal"


def test_cp28_temp_histeresis_sube_y_baja(estado_encendido, reloj):
    """CP-28: histeresis de temperatura de agua (R04)."""
    estado_encendido.set_temp_agua(115)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.color_temp == "rojo"

    estado_encendido.set_temp_agua(104)
    reloj.avanzar(500)
    estado_encendido.tick()
    assert estado_encendido.color_temp == "normal"


def test_cp29_turbo_histeresis_sube_y_baja(estado_encendido, reloj):
    """CP-29: histeresis de presion de turbo (R05)."""
    estado_encendido.set_presion_turbo(1.6)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.contorno_turbo == "ambar"

    estado_encendido.set_presion_turbo(1.3)
    reloj.avanzar(100)
    estado_encendido.tick()
    assert estado_encendido.contorno_turbo == "normal"


def test_cp30_parpadeo_direccional_500ms(estado_encendido, reloj):
    """CP-30: el testigo de direccional alterna cada 500 ms (R06)."""
    estado_encendido.set_direccional("IZQ")
    estados = []
    for _ in range(4):
        estados.append(estado_encendido.testigo_direccional_encendido)
        reloj.avanzar(500)
    assert estados[0] != estados[1]
    assert estados[1] != estados[2]
    assert estados[2] != estados[3]


def test_cp31_parpadeo_emergencia_500ms(estado_encendido, reloj):
    """CP-31: el testigo de emergencia alterna cada 500 ms (R07)."""
    estado_encendido.set_emergencia(True)
    estados = []
    for _ in range(4):
        estados.append(estado_encendido.testigo_emergencia_encendido)
        reloj.avanzar(500)
    assert estados[0] != estados[1]
    assert estados[1] != estados[2]
    assert estados[2] != estados[3]


def test_cp32_parpadeo_frenos_300ms(estado_encendido, reloj):
    """CP-32: el testigo de falla de frenos alterna cada 300 ms (R08)."""
    estado_encendido.set_falla_frenos(True)
    estados = []
    for _ in range(4):
        estados.append(estado_encendido.testigo_falla_frenos_encendido)
        reloj.avanzar(300)
    assert estados[0] != estados[1]
    assert estados[1] != estados[2]
    assert estados[2] != estados[3]


def test_cp33_emergencia_tiene_precedencia_sobre_direccional(estado_encendido):
    """CP-33: con direccional puesto y emergencia activa, hay precedencia visual (R07)."""
    estado_encendido.set_direccional("IZQ")
    estado_encendido.set_emergencia(True)
    assert estado_encendido.emergencia_tiene_precedencia is True


def test_cp34_sin_emergencia_no_hay_precedencia(estado_encendido):
    """CP-34: sin emergencia activa, no hay precedencia aunque haya direccional."""
    estado_encendido.set_direccional("IZQ")
    estado_encendido.set_emergencia(False)
    assert estado_encendido.emergencia_tiene_precedencia is False


def test_cp35_encender_motor_desde_apagado(estado, reloj):
    """CP-35: al encender el motor, las lecturas empiezan a actualizarse segun su ciclo."""
    estado.set_velocidad(50)
    estado.tick()
    assert estado.velocidad == 0

    estado.set_motor(True)
    reloj.avanzar(100)
    estado.tick()
    assert estado.velocidad == 50


def test_cp36_apagar_motor_fuerza_valores_seguros(estado_encendido, reloj):
    """CP-36: al apagar el motor, todas las lecturas vuelven de inmediato a su valor seguro."""
    estado_encendido.set_velocidad(200)
    estado_encendido.set_rpm(5000)
    estado_encendido.set_presion_aceite(5)
    estado_encendido.set_presion_turbo(1)
    estado_encendido.set_temp_agua(90)
    reloj.avanzar(500)
    estado_encendido.tick()

    estado_encendido.set_motor(False)
    estado_encendido.tick()

    assert estado_encendido.velocidad == 0
    assert estado_encendido.rpm == 0
    assert estado_encendido.p_aceite == 0
    assert estado_encendido.p_turbo == 0
    assert estado_encendido.temp_agua == 40
    assert estado_encendido.testigo_direccional_encendido is False
    assert estado_encendido.testigo_emergencia_encendido is False


def test_cp37_apagar_motor_apaga_testigo_aceite(estado_encendido, reloj):
    """CP-37: al apagar el motor se apaga el testigo 9 y se reinicia su temporizador."""
    estado_encendido.set_presion_aceite(0.2)
    reloj.avanzar(100)
    estado_encendido.tick()
    reloj.avanzar(1000)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is True

    estado_encendido.set_motor(False)
    estado_encendido.tick()
    assert estado_encendido.testigo_baja_presion_aceite is False
