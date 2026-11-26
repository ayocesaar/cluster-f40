"""Pruebas de la Etapa 21: practicas de fallas automaticas (todas), el robot maneja como una persona
(embrague en cada cambio, pedales con la rapidez del panel), el panel muestra la palanca y los pedales
del robot, curva de par y adherencia sin ABS, temperatura de aceite e inercia de las agujas."""

import gc
import pathlib
import sys

import pytest

from logic.estado import EstadoCluster
from panel import practicas
from panel.fisica import (ADHERENCIA_MOJADO, FRENADO_ADHERENCIA, PAR_MAXIMO_NM, TRACCION_MAXIMA, Vehiculo,
                          resistencia_al_avance)
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import convertir, formatear
from sistema.monitor import MonitorEventos
from ui.presentacion import COLOR_NORMAL, COLOR_ROJO, vista_extra

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)
DT = 0.05


@pytest.mark.parametrize("clave", list(practicas.CATALOGO))
def test_cp203_cada_practica_de_fallas_aprueba(clave):
    """CP-203: cada una de las 15 practicas de fallas corre sola de principio a fin y todas sus verificaciones contra la copia del cuadro real aprueban (testigos, WARN, causas de proteccion y mediciones)."""
    ejecucion = practicas.correr(clave)
    assert ejecucion.terminada and ejecucion.m.resultados
    assert ejecucion.aprobada, [r for r in ejecucion.m.resultados if not r[1]]


def test_cp204_el_robot_maneja_como_una_persona():
    """CP-204: en la practica de manejo el robot pisa el embrague antes de cada cambio, mueve los pedales con la rapidez del panel (no salta) y pasa por 1a, 2a y 3a."""
    m = practicas.Mando()
    e = practicas.Ejecucion(practicas.CATALOGO["normal"], m)
    historia = []
    while not e.terminada:
        e.avanzar(DT)
        historia.append((m.v.marcha, m.v.embrague, m.v.acelerador, m.v.freno))
    cambios = [i for i in range(1, len(historia)) if historia[i][0] != historia[i - 1][0]]
    assert cambios and all(historia[i - 1][1] >= 0.9 for i in cambios)
    saltos = max(abs(b[k] - a[k]) for a, b in zip(historia, historia[1:]) for k in (1, 2, 3))
    assert saltos <= 7.0 * DT + 1e-9
    assert {"1", "2", "3"} <= {marcha for marcha, *_ in historia}


def test_cp205_panel_muestra_la_palanca_y_los_pedales_del_robot(tmp_path):
    """CP-205: en el panel una practica corre en vivo: los pedales dibujados, la palanca y las casillas (puerta, fallas) muestran lo que hace el robot; termina APROBADA; Detener la corta; la pista mojada se activa desde el panel."""
    tk = pytest.importorskip("tkinter")
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from panel.ventana import COMPUERTA, Panel
    reloj = [0.0]
    p = Panel(raiz, ruta_datos=tmp_path / "vehiculo.conf", dir_logs=tmp_path / "logs", reloj=lambda: reloj[0])
    p.raiz.after_cancel(p._id_after)
    try:
        assert p.iniciar_practica("puertas") and p.modo == "practica"
        puerta_vista = embrague_visto = False
        for n in range(800):
            reloj[0] += DT
            p.paso(DT)
            if n % 3 == 0:
                p.dibujar()
                v = p.vehiculo
                assert all(p._dibujado[pedal] == round(getattr(v, pedal), 2)
                           for pedal in ("acelerador", "freno", "embrague"))
                x, y = COMPUERTA[v.marcha]
                assert p.cv_cambios.coords(p.pomo) == [x - 14, y - 14, x + 14, y + 14]
                puerta_vista = puerta_vista or p.var_puertas[1].get()
                embrague_visto = embrague_visto or v.embrague > 0.9
            if p.modo != "practica":
                break
        assert p.modo == "fisica" and "PRACTICA Puertas: APROBADA" in p.texto_consola()
        assert puerta_vista and embrague_visto
        p.iniciar_practica("temperatura")
        for _ in range(20):
            reloj[0] += DT
            p.paso(DT)
        p.detener_todo()
        assert p.modo == "fisica" and p.vehiculo.acelerador == 0.0
        p.var_mojado.set(True)
        p._pista()
        assert p.vehiculo.mojado and "Pista mojada" in p.texto_consola()
    finally:
        p.raiz.destroy()


def test_cp206_par_motor_adherencia_y_velocidad_maxima():
    """CP-206: la curva de par pasa por los datos verificados (577 Nm a 4000 rpm y unos 480 Nm a 7000 rpm, 478 CV) con el turbo soplando; sin presion el motor empuja como atmosferico; en seco no se bloquean las llantas, en mojado si (sin ABS) y patinan al acelerar; la maxima queda cerca de los 324 km/h publicados."""
    v = Vehiculo(motor=True)
    v.presion_turbo = 1.1
    v.rpm = 4000.0
    assert v.factor_par * PAR_MAXIMO_NM == pytest.approx(577.0)
    v.rpm = 7000.0
    assert v.factor_par * PAR_MAXIMO_NM == pytest.approx(480.0)
    v.presion_turbo = 0.0
    assert v.factor_par * PAR_MAXIMO_NM < 300
    seco = Vehiculo(motor=True, velocidad=100.0, freno=1.0)
    seco.avanzar(DT)
    assert not seco.bloqueado
    mojado = Vehiculo(motor=True, velocidad=100.0, freno=1.0, mojado=True)
    mojado.avanzar(DT)
    assert mojado.bloqueado and mojado.adherencia == ADHERENCIA_MOJADO
    assert FRENADO_ADHERENCIA * ADHERENCIA_MOJADO < 45.0 < FRENADO_ADHERENCIA
    arranque = Vehiculo(motor=True, mojado=True)
    arranque.cambiar("1")
    arranque.acelerador = 1.0
    patino = False
    for _ in range(60):
        arranque.avanzar(DT)
        patino = patino or arranque.patinando
    assert patino and arranque.empuje_maximo() <= TRACCION_MAXIMA * ADHERENCIA_MOJADO
    rapido = Vehiculo(motor=True, velocidad=250.0)
    rapido.cambiar("5")
    rapido.acelerador = 1.0
    for _ in range(int(120 / DT)):
        rapido.avanzar(DT)
    assert 315 <= rapido.velocidad <= 335
    assert resistencia_al_avance(0) == pytest.approx(0.8)


def test_cp207_temperatura_de_aceite(tmp_path, reloj):
    """CP-207: el aceite sigue al agua mas lento y se calienta con la carga; la clave temp_aceite (0-160 C) llega al elemento 17, que se pone en rojo sobre 130 C y vuelve a normal con 125 C o menos (R14) con WARN e INFO."""
    v = Vehiculo(motor=True)
    for _ in range(int(30 / DT)):
        v.avanzar(DT)
    assert v.temp_aceite < v.temp_agua + 8               # todavia no alcanza al agua: es mas lento
    assert convertir("temp_aceite", formatear("temp_aceite", 98.5), RANGOS) == 98.5
    assert v.lecturas_extra()["temp_aceite"] == round(v.temp_aceite, 1)
    bitacora = Bitacora(tmp_path / "logs", max_bytes=65536, respaldos=2)
    try:
        estado, monitor = EstadoCluster(reloj), MonitorEventos(bitacora)
        estado.set_motor(True)
        estado.set_temp_aceite(120.0)
        for valor, color in ((120.0, COLOR_NORMAL), (131.0, COLOR_ROJO), (127.0, COLOR_ROJO), (125.0, COLOR_NORMAL)):
            estado.set_temp_aceite(valor)
            for _ in range(12):
                reloj.avanzar(50)
                estado.tick()
                monitor.revisar(estado)
            assert vista_extra(estado)[17]["color"] == color, valor
        assert vista_extra(estado)[17]["valor"] == 125.0
        for manejador in bitacora._logger.handlers:
            manejador.flush()
        eventos = bitacora.ruta_eventos.read_text(encoding="utf-8")
        assert "temperatura_aceite_rojo" in eventos and "temperatura_aceite_normal" in eventos
        estado.set_temp_aceite(None)
        assert vista_extra(estado)[17]["sin_dato"]
        with pytest.raises(ValueError):
            estado.set_temp_aceite(170.0)
    finally:
        bitacora.cerrar()


def test_cp208_agujas_con_inercia_y_barra_de_aceite(reloj):
    """CP-208: las agujas se mueven con inercia de instrumento analogico (un refresco recorre solo parte del camino y en unos 15 llegan), pero el color y la cifra cambian de inmediato; la barra del elemento 17 dibuja la temperatura de aceite."""
    tk = pytest.importorskip("tkinter")
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from ui.tablero import Tablero
    t = Tablero(raiz, EstadoCluster(reloj))
    t.detener()
    try:
        t.ajustar("set_motor", True)
        t.ajustar("set_rpm", 8000)
        t.aplicar_externo("set_temp_aceite", 135.0)
        reloj.avanzar(600)
        t.ciclo()
        assert 0.2 < t._mostrada[3] < 0.8                 # a medio camino de 8000/9000
        assert t.canvas.itemcget(t.items[3]["aguja"], "fill") == COLOR_ROJO
        assert t.canvas.itemcget(t.items[3]["valor"], "text") == "8000 RPM"
        for _ in range(15):
            t.refrescar()
        assert t._mostrada[3] == pytest.approx(8000 / 9000)
        assert t.canvas.itemcget(t.extras[17]["etiqueta"], "text") == "17 TEMP. ACEITE 135 C"
        assert t.canvas.itemcget(t.extras[17]["barra"], "fill") == COLOR_ROJO
    finally:
        raiz.destroy()


def test_cp209_herramienta_de_practicas_deja_evidencia(tmp_path):
    """CP-209: tools/practicas.py corre una o todas las practicas, escribe el reporte con cada verificacion y termina con 0 cuando todas aprueban."""
    sys.path.insert(0, str(RAIZ / "tools"))
    import practicas as herramienta
    salida = tmp_path / "practicas.txt"
    assert herramienta.main(["--salida", str(salida)]) == 0
    texto = salida.read_text(encoding="utf-8")
    assert texto.count("APROBADA   ") == len(practicas.CATALOGO) and "15/15 practicas aprobadas" in texto
    assert herramienta.main(["--practica", "bateria"]) == 0
