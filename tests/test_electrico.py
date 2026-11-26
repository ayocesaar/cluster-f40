"""Pruebas de la Etapa 20: sistema electrico (testigo 16, bateria y alternador), falla de una
unidad Weber-Marelli (motor con 4 cilindros) y sonidos de cabina (relevador, llantas, ventilador)."""

import gc

import pytest

from logic.estado import EstadoCluster
from panel import liberacion as L
from panel.ecu import Ecu
from panel.fisica import Fallas, Vehiculo
from panel.sonido import (BLOQUE, FS, EstadoSonoro, SintetizadorMotor, a_mensaje, de_mensaje, envolvente,
                          estado_de, periodo_dominante_ms, potencia)
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import DatoInvalido, convertir, formatear
from sistema.monitor import MonitorEventos
from ui.presentacion import COLOR_APAGADO, COLOR_ROJO, vista_extra

RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)
DT = 0.05


def _log(bitacora):
    for manejador in bitacora._logger.handlers:
        manejador.flush()
    return bitacora.ruta_eventos.read_text(encoding="utf-8")


def _avanzar(estado, reloj, ms, monitor=None):
    for _ in range(int(ms / 50)):
        reloj.avanzar(50)
        estado.tick()
        if monitor is not None:
            monitor.revisar(estado)


def _conducir(v, ecu, segundos, avisos=None):
    for _ in range(int(segundos / DT)):
        nuevos = ecu.vigilar(v, DT)
        if avisos is not None:
            avisos += nuevos
        v.avanzar(DT)


def _generar(estado, segundos, arrancado=True):
    sint = SintetizadorMotor()
    sint.motor_previo = arrancado
    datos = []
    for _ in range(int(segundos * FS / BLOQUE)):
        datos += sint.generar(estado, BLOQUE)
    return datos, sint


def test_cp197_testigo_de_carga_y_voltaje(tmp_path, reloj):
    """CP-197: la clave voltaje es un decimal de 0 a 20 V; el testigo 16 se enciende con contacto y motor apagado (normal) y con el motor en marcha bajo 13.0 V, con WARN prioritario falla_de_carga (R13); con 14.2 V se apaga; sin dato queda apagado."""
    assert convertir("voltaje", formatear("voltaje", 14.2), RANGOS) == 14.2
    for texto in ("20.1", "-1", "doce"):
        with pytest.raises(DatoInvalido):
            convertir("voltaje", texto, RANGOS)
    bitacora = Bitacora(tmp_path / "logs", max_bytes=65536, respaldos=2)
    try:
        estado, monitor = EstadoCluster(reloj), MonitorEventos(bitacora)
        estado.set_contacto(True)
        _avanzar(estado, reloj, 2100, monitor)
        assert not estado.testigo_carga_encendido                  # sin dato
        estado.set_voltaje(12.6)
        _avanzar(estado, reloj, 100, monitor)
        assert vista_extra(estado)[16]["encendido"] and vista_extra(estado)[16]["voltaje"] == 12.6
        estado.set_motor(True)
        estado.set_rpm(1000)
        estado.set_voltaje(14.2)
        _avanzar(estado, reloj, 200, monitor)
        assert not estado.testigo_carga_encendido and vista_extra(estado)[16]["color"] == COLOR_APAGADO
        estado.set_voltaje(12.4)
        _avanzar(estado, reloj, 200, monitor)
        assert estado.falla_de_carga and vista_extra(estado)[16]["color"] == COLOR_ROJO
        estado.set_voltaje(14.2)
        _avanzar(estado, reloj, 200, monitor)
        eventos = _log(bitacora)
        assert eventos.count("falla_de_carga") == 1 and "WARN" in next(l for l in eventos.splitlines() if "falla_de_carga" in l)
        assert "carga_normal" in eventos
        with pytest.raises(ValueError):
            estado.set_voltaje(25.0)
    finally:
        bitacora.cerrar()


def test_cp198_bateria_alternador_y_ecu():
    """CP-198: con el alternador sano el regulador da 14.2 V y la bateria se mantiene; con falla del alternador la bateria se descarga (mas rapido con luces altas), el voltaje baja y bajo 10.5 V durante 1 s la ECU apaga el motor (causa electrica); con la bateria debil no arranca hasta cargarla."""
    v, ecu = Vehiculo(motor=True, contacto=True), Ecu()
    _conducir(v, ecu, 5)
    assert v.voltaje == pytest.approx(14.2) and v.bateria == 1.0
    sin_luces = Vehiculo(motor=True, contacto=True, fallas=Fallas(alternador=True))
    con_luces = Vehiculo(motor=True, contacto=True, luces_altas=True, fallas=Fallas(alternador=True))
    for vehiculo in (sin_luces, con_luces):
        _conducir(vehiculo, Ecu(), 20)
    assert con_luces.bateria < sin_luces.bateria < 1.0 and sin_luces.voltaje < 13.0
    avisos = []
    _conducir(con_luces, ecu := Ecu(), 300, avisos)
    assert not con_luces.motor and ecu.proteccion == "electrica" and any("voltaje" in a for a in avisos)
    debil = Vehiculo(contacto=True, bateria=0.05)
    ecu = Ecu()
    assert "bateria descargada" in ecu.motivo_sin_arranque(debil) and ecu.proteccion == "electrica"
    debil.bateria = 1.0
    assert ecu.motivo_sin_arranque(debil) is None
    assert v.lecturas_extra()["voltaje"] == 14.2 and debil.lecturas_extra()["voltaje"] == 12.5


def test_cp199_falla_de_una_unidad_weber_marelli():
    """CP-199: con una unidad Weber-Marelli sin encendido el motor sigue andando con 4 cilindros: la mitad del empuje, un solo turbo, el ralenti oscila mas de 150 rpm de pico a pico y el sonido pierde una de cada dos explosiones (ritmo de 30 ms a 1000 rpm)."""
    def aceleracion(fallas):
        v = Vehiculo(motor=True, fallas=fallas)
        v.cambiar("2")
        v.velocidad, v.acelerador = 60.0, 1.0
        for _ in range(40):
            v.avanzar(DT)
        return v.velocidad - 60.0, v.presion_turbo
    sana, turbo_sano = aceleracion(Fallas())
    falla, turbo_falla = aceleracion(Fallas(ecu_banco=True))
    assert falla < 0.6 * sana and turbo_falla < 0.65 * turbo_sano
    v = Vehiculo(motor=True, fallas=Fallas(ecu_banco=True))
    rpms = []
    for _ in range(int(4 / DT)):
        v.avanzar(DT)
        rpms.append(v.rpm)
    assert max(rpms[40:]) - min(rpms[40:]) > 150 and v.motor
    cojo, sint = _generar(EstadoSonoro(motor=True, rpm=1000, contacto=True, banco=True), 1.5)
    assert periodo_dominante_ms(cojo[FS // 2:]) == pytest.approx(30.0, abs=2.0) and sint.saltadas > 40
    assert estado_de(Vehiculo(motor=True, fallas=Fallas(ecu_banco=True))).banco


def test_cp200_banco_detecta_las_fallas_electricas():
    """CP-200: el arranque de fin de linea (L01) rechaza el alternador que no carga (menos de 13.5 V) y la unidad Weber-Marelli fallida (ralenti inestable); la unidad sana sigue APTA y la prueba de testigos incluye el 16."""
    sana = L.prueba_arranque({})
    assert sana.aprobado and "14.2 V" in sana.medido
    assert not L.prueba_arranque({"alternador": True}).aprobado
    banco = L.prueba_arranque({"ecu_banco": True})
    assert not banco.aprobado and "rpm" in banco.medido
    assert L.prueba_testigos({}).aprobado and "10/10" in L.prueba_testigos({}).medido
    assert {"alternador", "ecu_banco"} <= set(L.FALLAS)


def test_cp201_sonidos_de_cabina():
    """CP-201: el relevador de las direccionales hace un clic cada 500 ms; las llantas chirrian (1100 Hz) al frenar a fondo; se oye el ventilador (45 Hz); con la bateria debil el motor de arranque gira mas lento; los campos nuevos viajan por el socket validados."""
    clics, sint = _generar(EstadoSonoro(contacto=True, intermitente=True), 2.0, arrancado=False)
    env = envolvente(clics, FS // 200)                                # ventanas de 5 ms
    umbral = 0.5 * max(env)
    picos = [i for i in range(len(env)) if env[i] > umbral and (i == 0 or env[i - 1] <= umbral)]
    assert sint.clics == 4 and len(picos) == 4 and all(95 <= b - a <= 105 for a, b in zip(picos, picos[1:]))
    sin, _ = _generar(EstadoSonoro(motor=True, rpm=2000, contacto=True), 1.0)
    con, _ = _generar(EstadoSonoro(motor=True, rpm=2000, contacto=True, chirrido=1.0), 1.0)
    banda = range(1072, 1130, 7)                                    # 1100 Hz con su vibrato de 7 Hz
    assert sum(potencia(con[FS // 4:], f) for f in banda) > 10 * sum(potencia(sin[FS // 4:], f) for f in banda)
    ventilador, _ = _generar(EstadoSonoro(contacto=True, ventilador=True), 1.0, arrancado=False)
    callado, _ = _generar(EstadoSonoro(contacto=True), 1.0, arrancado=False)
    assert potencia(ventilador, 45) > 100 * max(potencia(callado, 45), 1e-9)
    fuerte, _ = _generar(EstadoSonoro(contacto=True, crank=1.0), 1.0, arrancado=False)
    debil, _ = _generar(EstadoSonoro(contacto=True, crank=0.35), 1.0, arrancado=False)
    assert potencia(debil, 190 * 0.35) > potencia(debil, 190) and potencia(fuerte, 190) > potencia(fuerte, 190 * 0.35)
    v = Vehiculo(motor=True, contacto=True, velocidad=100.0, freno=1.0, direccional="IZQ")
    e = estado_de(v, crank=0.0)
    assert e.chirrido > 0.5 and e.intermitente
    assert de_mensaje(a_mensaje(e)) == e
    with pytest.raises(ValueError):
        de_mensaje(b'{"crank": 2}')


def test_cp202_panel_bateria_y_fallas_nuevas(tmp_path):
    """CP-202: el panel tiene las fallas del alternador y de la unidad Weber-Marelli, el taller carga o descarga la bateria, con la bateria debil el arranque falla con el motor de arranque girando lento, y el voltaje llega al archivo de datos."""
    tk = pytest.importorskip("tkinter")
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from panel.ventana import Panel
    from sistema.lector import Lector
    reloj = [0.0]
    p = Panel(raiz, ruta_datos=tmp_path / "vehiculo.conf", dir_logs=tmp_path / "logs", reloj=lambda: reloj[0])
    p.raiz.after_cancel(p._id_after)
    try:
        assert {"alternador", "ecu_banco"} <= set(p.var_fallas)
        assert p.taller("bateria_debil") and p.vehiculo.bateria == pytest.approx(0.06)
        assert p.alternar_motor() is False and "bateria descargada" in p.texto_consola()
        assert p.giro_arranque[1] == pytest.approx(0.35)
        assert p.taller("bateria") and p.alternar_motor() is True
        for _ in range(6):
            reloj[0] += DT
            p.paso(DT)
        bitacora = Bitacora(tmp_path / "logs_lector")
        try:
            datos = Lector(p.ruta, RANGOS, bitacora).leer()
        finally:
            bitacora.cerrar()
        assert datos["voltaje"] == 14.2 and datos["falla_motor"] == "ninguna"
        p.var_fallas["alternador"].set(True)
        p._fallas()
        p.dibujar()
        assert p.vehiculo.fallas.alternador and p.lbl_extra["bateria"].cget("text").endswith("%")
    finally:
        p.raiz.destroy()
