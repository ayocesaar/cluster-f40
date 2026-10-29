"""Pruebas de integracion de la interfaz Tkinter real. Requieren un servidor
grafico (en la VM: xvfb-run); sin el, se omiten en lugar de fallar."""

import pytest

tk = pytest.importorskip("tkinter")

from ui.presentacion import COLOR_APAGADO, COLOR_ROJO
from ui.tablero import Tablero


def _requiere_display():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")


@pytest.fixture
def tablero(estado):
    _requiere_display()
    raiz = tk.Tk()
    t = Tablero(raiz, estado)
    yield t
    t.detener()
    raiz.destroy()


def test_cp74_ventana_arranca_en_estado_seguro(tablero):
    """CP-74: los controles inician en estado seguro y los testigos se dibujan apagados (R01)."""
    v = tablero.variables
    assert (v["set_velocidad"].get(), v["set_rpm"].get(), v["set_temp_agua"].get()) == (0, 0, 40)
    assert v["set_motor"].get() is False and v["set_direccional"].get() == "OFF"
    assert all(tablero.canvas.itemcget(tablero.items[n]["forma"], "fill") == COLOR_APAGADO
               for n in range(6, 11))


def test_cp75_mover_controles_actualiza_el_dibujo(tablero, reloj):
    """CP-75: encender el motor y llevar RPM a 8000 dibuja el tacometro en rojo (R03)."""
    tablero.ajustar("set_motor", True)
    tablero.ajustar("set_rpm", 8000)
    reloj.avanzar(100)
    tablero.ciclo()
    it = tablero.items[3]
    assert tablero.canvas.itemcget(it["aguja"], "fill") == COLOR_ROJO
    assert tablero.canvas.itemcget(it["valor"], "text") == "8000 RPM"


def test_cp76_testigos_criticos_visualmente_distintos(tablero):
    """CP-76: 9 y 10 son rectangulos con borde rojo; 6-8 son circulos; el 10 se enciende rojo (R08)."""
    tipos = [tablero.canvas.type(tablero.items[n]["forma"]) for n in range(6, 11)]
    assert tipos == ["oval", "oval", "oval", "rectangle", "rectangle"]
    tablero.ajustar("set_falla_frenos", True)
    tablero.ciclo()
    assert tablero.canvas.itemcget(tablero.items[10]["forma"], "fill") == COLOR_ROJO


def test_cp77_entrada_rechazada_se_informa_y_no_cambia_estado(tablero, estado):
    """CP-77: un valor invalido muestra un mensaje en pantalla y no modifica el estado."""
    assert tablero.enviar("set_rpm", 9001) is False
    assert tablero.mensaje.cget("text").startswith("Entrada rechazada")
    assert estado._obj_rpm == 0
    assert tablero.enviar("set_rpm", 100) is True
    assert tablero.mensaje.cget("text") == ""


def test_cp78_main_arranca_y_cierra(estado):
    """CP-78: main.py abre la aplicacion con el reloj real y se cierra sola (prueba de humo)."""
    _requiere_display()
    from main import main
    assert main(["--salir-tras-ms", "300"]) == 0


def test_cp86_detener_dos_veces_no_falla(tablero):
    """CP-86: detener el refresco dos veces no produce error (cierre seguro de la ventana)."""
    tablero.detener()
    tablero.detener()
    assert tablero._id_after is None
