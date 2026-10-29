"""Pruebas de la capa de presentacion: lo que el usuario veria en pantalla
para cada uno de los 10 elementos, sin abrir una ventana."""

from ui.presentacion import (COLOR_AMBAR, COLOR_APAGADO, COLOR_AZUL, COLOR_NORMAL, COLOR_ROJO,
                             COLOR_VERDE, CRITICA, ELEMENTOS, INFORMATIVA, LECTURA, vista)


def test_cp67_diez_elementos_con_numeracion_y_categoria(estado):
    """CP-67: la vista expone los 10 elementos con la numeracion y categorias oficiales."""
    v = vista(estado)
    assert sorted(v) == list(range(1, 11))
    assert [ELEMENTOS[n]["categoria"] for n in range(1, 11)] == [LECTURA] * 5 + [INFORMATIVA] * 3 + [CRITICA] * 2


def test_cp68_estado_inicial_seguro(estado):
    """CP-68: al iniciar, agujas en su minimo, colores normales y testigos apagados (R01)."""
    v = vista(estado)
    assert [v[n]["valor"] for n in range(1, 6)] == [0, 0, 0, 40, 0]
    assert all(v[n]["fraccion"] == 0 and v[n]["color"] == COLOR_NORMAL for n in range(1, 6))
    assert all(v[n]["encendido"] is False and v[n]["color"] == COLOR_APAGADO for n in range(6, 11))


def test_cp69_colores_de_advertencia_de_lecturas(estado_encendido, reloj):
    """CP-69: 2 ambar (<1 bar), 3 rojo (>=8000), 4 rojo (>110), 5 ambar (>1.5) (R03, R04, R05)."""
    estado_encendido.set_presion_aceite(0.5)
    estado_encendido.set_rpm(8000)
    estado_encendido.set_temp_agua(115)
    estado_encendido.set_presion_turbo(1.6)
    reloj.avanzar(500)
    estado_encendido.tick()
    v = vista(estado_encendido)
    assert (v[2]["color"], v[3]["color"], v[4]["color"], v[5]["color"]) == (
        COLOR_AMBAR, COLOR_ROJO, COLOR_ROJO, COLOR_AMBAR)


def test_cp70_testigo_9_distinto_del_medidor_2(estado_encendido, reloj):
    """CP-70: el medidor 2 cambia a ambar de inmediato y el testigo 9 solo tras 1 s (R02)."""
    estado_encendido.set_presion_aceite(0.5)
    reloj.avanzar(100)
    estado_encendido.tick()
    v = vista(estado_encendido)
    assert v[2]["color"] == COLOR_AMBAR and v[9]["encendido"] is False

    reloj.avanzar(1000)
    estado_encendido.tick()
    v = vista(estado_encendido)
    assert v[9]["encendido"] is True and v[9]["color"] == COLOR_ROJO


def test_cp71_emergencia_tiene_precedencia_visual_sobre_giro(estado_encendido):
    """CP-71: con emergencia activa el testigo 6 no se dibuja y el 8 si; sin ella, el 6 vuelve (R06, R07)."""
    estado_encendido.set_direccional("IZQ")
    estado_encendido.set_emergencia(True)
    v = vista(estado_encendido)
    assert v[6]["encendido"] is False and v[8]["encendido"] is True and v[8]["color"] == COLOR_AMBAR

    estado_encendido.set_emergencia(False)
    v = vista(estado_encendido)
    assert v[6]["encendido"] is True and v[6]["color"] == COLOR_VERDE and v[6]["lado"] == "IZQ"


def test_cp72_luces_altas_azul_y_frenos_rojo(estado_encendido):
    """CP-72: el testigo 7 se dibuja azul y el 10 rojo (R07, R08)."""
    estado_encendido.set_luces_altas(True)
    estado_encendido.set_falla_frenos(True)
    v = vista(estado_encendido)
    assert v[7]["color"] == COLOR_AZUL and v[10]["color"] == COLOR_ROJO


def test_cp73_posicion_de_aguja_proporcional(estado_encendido, reloj):
    """CP-73: la aguja se ubica en proporcion al rango (180 km/h = mitad, 9000 RPM = tope) (R01)."""
    estado_encendido.set_velocidad(180)
    estado_encendido.set_rpm(9000)
    reloj.avanzar(100)
    estado_encendido.tick()
    v = vista(estado_encendido)
    assert v[1]["fraccion"] == 0.5 and v[3]["fraccion"] == 1.0
