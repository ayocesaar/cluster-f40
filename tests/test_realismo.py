"""Pruebas de la Etapa 18: claves opcionales, llave de contacto, prueba de testigos, elementos
adicionales 12-15 (R09-R12), ECU simulada (interbloqueos y protecciones) y las consecuencias
fisicas de las fallas del panel."""

import gc
import sys
import time

import pytest

from logic.estado import CAUSAS_MOTOR as CAUSAS_MODELO
from logic.estado import EstadoCluster
from panel import comandos
from panel.ecu import Ecu
from panel.fisica import TANQUE_L, Fallas, Vehiculo
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import (CAUSAS_MOTOR, CLAVES, CLAVES_EXTRA, VALORES_INICIALES, DatoInvalido, Lector, convertir,
                            describir_puertas, escribir_atomico, escribir_texto_atomico, formatear)
from sistema.monitor import MonitorEventos
from ui.presentacion import COLOR_AMBAR, COLOR_APAGADO, COLOR_ROJO, vista, vista_extra

RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)
DT = 0.05


def _log(bitacora, cual):
    for manejador in bitacora._logger.handlers:
        manejador.flush()
    ruta = bitacora.ruta_eventos if cual == "eventos" else bitacora.ruta_errores
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _linea(texto, evento):
    return next((linea for linea in texto.splitlines() if evento in linea), "")


@pytest.fixture
def entorno(tmp_path):
    datos = tmp_path / "datos" / "vehiculo.conf"
    datos.parent.mkdir()
    bitacora = Bitacora(tmp_path / "logs", max_bytes=65536, respaldos=2)
    yield datos, bitacora, Lector(datos, RANGOS, bitacora)
    bitacora.cerrar()


@pytest.fixture
def vigilado(tmp_path, reloj):
    """EstadoCluster con su monitor y bitacora, como en main.py."""
    bitacora = Bitacora(tmp_path / "logs_monitor", max_bytes=65536, respaldos=2)
    yield EstadoCluster(reloj), MonitorEventos(bitacora), bitacora
    bitacora.cerrar()


def _avanzar(estado, reloj, ms, monitor=None, paso=50):
    for _ in range(int(ms / paso)):
        reloj.avanzar(paso)
        estado.tick()
        if monitor is not None:
            monitor.revisar(estado)


def _muestras(estado, reloj, cuantas, cada_ms, funcion, monitor=None):
    resultado = []
    for _ in range(cuantas):
        _avanzar(estado, reloj, cada_ms, monitor)
        resultado.append(funcion(estado))
    return resultado


def _conducir(v, ecu, segundos, avisos=None):
    for _ in range(int(segundos / DT)):
        nuevos = ecu.vigilar(v, DT)
        if avisos is not None:
            avisos += nuevos
        v.avanzar(DT)


# ------------------------------------------------------------------ lector y formato
def test_cp163_claves_opcionales_tipos_y_rangos():
    """CP-163: las claves opcionales se codifican y decodifican sin perdida (booleano, bits de estado, decimal y causa) y se rechazan fuera de tipo o de rango."""
    ejemplos = {"contacto": True, "puertas": 3, "cinturon": False, "combustible": 48.5, "falla_motor": "aceite"}
    for clave, valor in ejemplos.items():
        assert convertir(clave, formatear(clave, valor), RANGOS) == valor
    for clave, texto, evento in (("puertas", "4", "fuera_de_rango"), ("puertas", "-1", "fuera_de_rango"),
                                  ("puertas", "1.5", "dato_invalido"), ("combustible", "100.1", "fuera_de_rango"),
                                  ("combustible", "abc", "dato_invalido"), ("combustible", "５０", "dato_invalido"),
                                  ("cinturon", "2", "dato_invalido"), ("contacto", "si", "dato_invalido"),
                                  ("falla_motor", "explota", "dato_invalido"), ("falla_motor", "ACEITE", "dato_invalido")):
        with pytest.raises(DatoInvalido) as error:
            convertir(clave, texto, RANGOS)
        assert error.value.evento == evento, (clave, texto)
    assert (describir_puertas(0), describir_puertas(1), describir_puertas(3)) == (
        "cerradas", "conductor", "conductor+pasajero")
    assert CAUSAS_MOTOR == CAUSAS_MODELO and not set(CLAVES) & set(CLAVES_EXTRA)


def test_cp164_formato_de_diez_claves_compatible_y_consistencia(entorno):
    """CP-164: un archivo de diez claves no genera errores ni claves opcionales; una opcional invalida conserva su ultimo valor (ERROR); la que deja de llegar vuelve a sin dato (INFO); motor=1 con contacto=0 es un dato_inconsistente."""
    datos, bitacora, lector = entorno
    base = dict(VALORES_INICIALES, motor=True, rpm=900)
    escribir_atomico(datos, base)
    assert set(lector.leer()) == set(CLAVES) and _log(bitacora, "errores") == ""
    escribir_atomico(datos, dict(base, contacto=True, puertas=1, combustible=40.0))
    snapshot = lector.leer()
    assert (snapshot["contacto"], snapshot["puertas"], snapshot["combustible"]) == (True, 1, 40.0)
    escribir_texto_atomico(datos, datos.read_text(encoding="utf-8").replace("combustible=40.0", "combustible=abc"))
    assert lector.leer()["combustible"] == 40.0 and 'combustible entrada="abc"' in _log(bitacora, "errores")
    escribir_atomico(datos, dict(base, contacto=True))
    snapshot = lector.leer()
    assert "puertas" not in snapshot and "combustible" not in snapshot
    assert _log(bitacora, "eventos").count("clave_opcional_retirada") == 2
    escribir_atomico(datos, dict(base, contacto=False))
    snapshot = lector.leer()
    assert "contacto" not in snapshot and "dato_inconsistente" in _log(bitacora, "errores")
    assert any("contacto=0 con motor=1" in r for r in lector.rechazos)
    escribir_atomico(datos, dict(base, motor=False, rpm=0, contacto=False))
    assert lector.leer()["contacto"] is False                  # sin motor, contacto=0 es consistente


# ------------------------------------------------------------------ modelo y presentacion
def test_cp165_contacto_separa_encendido_de_motor_activo(estado, reloj):
    """CP-165: con contacto y motor apagado, velocidad y temperatura se actualizan y el odometro avanza; RPM, aceite y turbo quedan en 0 y el testigo 9 apagado (D3, R01, R02); sin dato de contacto el cuadro sigue al motor como antes."""
    estado.set_velocidad(72.0)
    estado.set_temp_agua(118.0)
    estado.set_rpm(3000)
    estado.set_presion_aceite(0.2)
    estado.set_presion_turbo(1.2)
    _avanzar(estado, reloj, 1000)
    assert not estado.encendido and estado.velocidad == 0.0 and estado.odometro.km == 0.0
    estado.set_contacto(True)
    _avanzar(estado, reloj, 50_000)
    assert estado.encendido and not estado.motor_activo
    assert estado.velocidad == 72.0 and estado.temp_agua == 118.0 and estado.color_temp == "rojo"
    assert (estado.rpm, estado.p_aceite, estado.p_turbo) == (0, 0.0, 0.0)
    assert not estado.testigo_baja_presion_aceite and estado.color_aceite == "normal"
    assert estado.odometro.km == pytest.approx(1.0, abs=0.005)
    estado.set_motor(True)
    _avanzar(estado, reloj, 1500)
    assert estado.rpm == 3000 and estado.testigo_baja_presion_aceite       # con motor, R02 vuelve a aplicar
    estado.set_contacto(None)
    estado.set_motor(False)
    _avanzar(estado, reloj, 100)
    assert not estado.encendido and estado.velocidad == 0.0


def test_cp166_prueba_de_testigos_al_dar_contacto(vigilado, reloj):
    """CP-166: al pasar la llave a contacto todos los testigos encienden 2 s y despues solo queda el de una falla real (R08); el monitor registra la prueba y ningun WARN por ella (R13-H 5.2.21.4)."""
    estado, monitor, bitacora = vigilado
    estado.set_contacto(True)
    _avanzar(estado, reloj, 500, monitor)
    v, e = vista(estado), vista_extra(estado)
    assert all(v[n]["encendido"] for n in range(6, 11))
    assert all(e[n]["encendido"] for n in (12, 13, 15)) and e[14]["reserva"]["encendido"]
    assert e["llave"] == {"estado": "CONTACTO", "prueba": True}
    _avanzar(estado, reloj, 2000, monitor)
    v, e = vista(estado), vista_extra(estado)
    assert not any(v[n]["encendido"] for n in range(6, 11)) and v[9]["color"] == COLOR_APAGADO
    assert not any(e[n]["encendido"] for n in (12, 13, 15)) and not e[14]["reserva"]["encendido"]
    eventos = _log(bitacora, "eventos")
    assert eventos.count("prueba_de_testigos") == 1 and "contacto_puesto" in eventos and " WARN " not in eventos
    estado.set_falla_frenos(True)
    estado.set_contacto(False)
    _avanzar(estado, reloj, 100, monitor)
    estado.set_contacto(True)
    _avanzar(estado, reloj, 2100, monitor)
    muestras = _muestras(estado, reloj, 6, 100, vista)
    assert any(m[10]["encendido"] for m in muestras) and not any(m[n]["encendido"] for m in muestras for n in (6, 7, 8, 9))
    eventos = _log(bitacora, "eventos")
    assert eventos.count("prueba_de_testigos") == 2 and "contacto_quitado" in eventos


def test_cp167_puerta_abierta_fija_detenido_y_critica_en_movimiento(vigilado, reloj):
    """CP-167: puertas=1 enciende el testigo 12 ambar fijo con el auto detenido; en movimiento parpadea en rojo y se registra WARN prioritario puerta_abierta_en_movimiento (R09); los bits 1 y 2 nombran las puertas."""
    estado, monitor, bitacora = vigilado
    estado.set_motor(True)
    estado.set_puertas(1)
    detenido = _muestras(estado, reloj, 6, 100, lambda e: vista_extra(e)[12], monitor)
    assert all(m["encendido"] and m["color"] == COLOR_AMBAR for m in detenido) and detenido[0]["detalle"] == "CONDUCTOR"
    estado.set_velocidad(30.0)
    andando = _muestras(estado, reloj, 12, 100, lambda e: vista_extra(e)[12], monitor)
    assert any(m["encendido"] for m in andando) and not all(m["encendido"] for m in andando)
    assert all(m["color"] == COLOR_ROJO for m in andando if m["encendido"])
    estado.set_puertas(3)
    assert vista_extra(estado)[12]["detalle"] == "CONDUCTOR+PASAJERO"
    estado.set_puertas(0)
    _avanzar(estado, reloj, 200, monitor)
    eventos = _log(bitacora, "eventos")
    assert "WARN" in _linea(eventos, "puerta_abierta_en_movimiento") and "R09" in _linea(eventos, "puerta_abierta_en")
    assert "INFO" in _linea(eventos, "puerta_abierta puertas=1") and "puertas_cerradas" in eventos


def test_cp168_cinturon_desabrochado(vigilado, reloj):
    """CP-168: con contacto y cinturon sin abrochar el testigo 13 enciende fijo; sobre 10 km/h parpadea y se registra WARN cinturon_desabrochado_en_movimiento (R10); sin dato o abrochado queda apagado."""
    estado, monitor, bitacora = vigilado
    estado.set_contacto(True)
    _avanzar(estado, reloj, 2100, monitor)                       # termina la prueba de testigos
    assert not vista_extra(estado)[13]["encendido"] and vista_extra(estado)[13]["sin_dato"]
    estado.set_cinturon(False)
    assert all(_muestras(estado, reloj, 6, 100, lambda e: vista_extra(e)[13]["encendido"], monitor))
    estado.set_motor(True)
    estado.set_velocidad(40.0)
    andando = _muestras(estado, reloj, 12, 100, lambda e: vista_extra(e)[13]["encendido"], monitor)
    assert any(andando) and not all(andando)
    estado.set_cinturon(True)
    assert not any(_muestras(estado, reloj, 6, 100, lambda e: vista_extra(e)[13]["encendido"], monitor))
    eventos = _log(bitacora, "eventos")
    assert "WARN" in _linea(eventos, "cinturon_desabrochado_en_movimiento")
    assert "cinturon_desabrochado con contacto" in eventos and "cinturon_abrochado" in eventos


def test_cp169_combustible_y_reserva_con_histeresis(vigilado, reloj):
    """CP-169: el combustible se muestra con el ciclo de 500 ms y en litros del tanque de 120 L; la reserva enciende con <= 12 % y se apaga con >= 15 % (histeresis) y se registra WARN combustible_reserva (R11)."""
    estado, monitor, bitacora = vigilado
    estado.set_motor(True)
    estado.set_combustible(50.0)
    _avanzar(estado, reloj, 100, monitor)
    assert estado.combustible == 50.0 and vista_extra(estado)[14]["litros"] == pytest.approx(60.0)
    estado.set_combustible(12.0)
    _avanzar(estado, reloj, 100, monitor)
    assert estado.combustible == 50.0                            # ciclo lento: todavia no se refresca
    _avanzar(estado, reloj, 500, monitor)
    assert estado.combustible == 12.0 and estado.reserva_combustible
    assert vista_extra(estado)[14]["color"] == COLOR_AMBAR
    estado.set_combustible(14.0)
    _avanzar(estado, reloj, 600, monitor)
    assert estado.reserva_combustible                            # histeresis: entre 12 y 15 % no cambia
    estado.set_combustible(15.0)
    _avanzar(estado, reloj, 600, monitor)
    assert not estado.reserva_combustible
    estado.set_combustible(None)
    assert vista_extra(estado)[14]["sin_dato"] and estado.combustible is None
    eventos = _log(bitacora, "eventos")
    assert "WARN" in _linea(eventos, "combustible_reserva nivel=12") and "combustible_sobre_reserva nivel=15" in eventos


def test_cp170_proteccion_del_motor_y_validacion_del_modelo(vigilado, reloj):
    """CP-170: falla_motor con una causa enciende el testigo 15 con su texto y registra WARN motor_detenido_por_proteccion; al volver a ninguna se registra INFO proteccion_motor_liberada (R12); el modelo rechaza tipos y rangos invalidos."""
    estado, monitor, bitacora = vigilado
    estado.set_contacto(True)
    estado.set_falla_motor("sobretemperatura")
    _avanzar(estado, reloj, 2100, monitor)
    e = vista_extra(estado)[15]
    assert e["encendido"] and e["color"] == COLOR_ROJO and e["texto"] == "SOBRETEMPERATURA"
    estado.set_falla_motor("ninguna")
    _avanzar(estado, reloj, 100, monitor)
    assert not vista_extra(estado)[15]["encendido"]
    eventos = _log(bitacora, "eventos")
    assert "WARN" in _linea(eventos, "motor_detenido_por_proteccion causa=sobretemperatura")
    assert "proteccion_motor_liberada" in eventos
    for setter, valor, error in (("set_falla_motor", "explota", ValueError), ("set_falla_motor", 3, TypeError),
                                 ("set_puertas", 4, ValueError), ("set_puertas", True, TypeError),
                                 ("set_cinturon", 1, TypeError), ("set_combustible", 100.5, ValueError),
                                 ("set_combustible", float("nan"), ValueError), ("set_contacto", "1", TypeError)):
        with pytest.raises(error):
            getattr(estado, setter)(valor)


def test_cp171_tablero_dibuja_los_elementos_adicionales(reloj):
    """CP-171: la franja inferior del tablero dibuja la llave, el combustible con su reserva, la puerta, el cinturon y la proteccion; sin dato quedan apagados; aplicar_externo acepta claves sin control manual y None."""
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
        c = t.canvas
        t.ciclo()
        assert c.itemcget(t._txt_llave, "text") == "OFF" and c.itemcget(t.extras[14]["valor"], "text") == "sin dato"
        assert all(c.itemcget(t.extras[n]["forma"], "fill") == COLOR_APAGADO for n in (12, 13, 15))
        assert [c.type(t.extras[n]["forma"]) for n in (12, 13, 15)] == ["oval", "rectangle", "rectangle"]
        for setter, valor in (("set_contacto", True), ("set_motor", True), ("set_puertas", 1), ("set_cinturon", True),
                              ("set_combustible", 8.0), ("set_falla_motor", "aceite")):
            t.aplicar_externo(setter, valor)
        reloj.avanzar(2500)
        t.ciclo()
        assert c.itemcget(t._txt_llave, "text") == "MOTOR"
        assert c.itemcget(t.extras[12]["forma"], "fill") == COLOR_AMBAR
        assert c.itemcget(t.extras[13]["forma"], "fill") == COLOR_APAGADO
        assert c.itemcget(t.extras[15]["forma"], "fill") == COLOR_ROJO and c.itemcget(t._txt_detalle, "text") == "ACEITE"
        assert c.itemcget(t.extras[14]["reserva"], "fill") == COLOR_AMBAR
        assert c.itemcget(t.extras[14]["valor"], "text").startswith("8 %")
        t.aplicar_externo("set_combustible", None)
        t.ciclo()
        assert c.itemcget(t.extras[14]["valor"], "text") == "sin dato"
    finally:
        raiz.destroy()


# ------------------------------------------------------------------ ECU y fisica de las fallas
def test_cp172_fuga_de_aceite_no_deja_arrancar():
    """CP-172: con fuga de aceite la ECU no deja arrancar y enclava la causa aceite (R02, R12); reparar no basta si el deposito quedo bajo 50 %; una fuga en marcha vacia el deposito y la ECU detiene el motor por falta de presion."""
    v, ecu = Vehiculo(contacto=True), Ecu()
    v.fallas.fuga_aceite = True
    assert "aceite" in ecu.motivo_sin_arranque(v) and ecu.proteccion == "aceite"
    assert v.lecturas_extra(ecu.proteccion)["falla_motor"] == "aceite"
    v.fallas.fuga_aceite = False
    v.nivel_aceite = 40.0
    assert "enclavada" in ecu.motivo_sin_arranque(v)
    v.nivel_aceite = 100.0
    assert ecu.motivo_sin_arranque(v) is None and ecu.proteccion == "ninguna"
    v.motor = True
    v.fallas.fuga_aceite = True
    for _ in range(int(240 / DT)):
        ecu.vigilar(v, DT)
        v.avanzar(DT)
        if not v.motor:
            break
    assert not v.motor and ecu.proteccion == "aceite" and v.nivel_aceite < 30


def test_cp173_sobrecalentamiento_detiene_el_motor_y_no_deja_moverse():
    """CP-173: con el radiador danado el agua llega a 120 C, la ECU detiene el motor (R04, R12) y no deja arrancar hasta reparar y enfriar bajo 100 C; sin motor el auto no avanza aunque se acelere."""
    v, ecu = Vehiculo(motor=True, contacto=True), Ecu()
    v.fallas.radiador = True
    maxima = v.temp_agua
    for _ in range(int(120 / DT)):
        ecu.vigilar(v, DT)
        v.avanzar(DT)
        maxima = max(maxima, v.temp_agua)
        if not v.motor:
            break
    assert not v.motor and ecu.proteccion == "sobretemperatura" and maxima >= 120
    assert ecu.motivo_sin_arranque(v) is not None
    v.cambiar("1")
    v.acelerador = 1.0
    _conducir(v, ecu, 2)
    assert v.velocidad == 0.0
    v.fallas.radiador = False
    assert v.temp_agua > 100 and ecu.motivo_sin_arranque(v) is not None      # todavia caliente
    avisos = []
    _conducir(v, ecu, 15, avisos)
    assert v.temp_agua <= 100 and ecu.proteccion == "ninguna" and any("liberada" in a for a in avisos)
    assert ecu.motivo_sin_arranque(v) is None


def test_cp174_sobrepresion_del_turbo_corta_el_motor():
    """CP-174: con la valvula de descarga fallando el turbo pasa de 1.5 bar; tras 1 s la ECU corta el motor y la proteccion queda enclavada hasta reparar (R05, R12)."""
    v, ecu = Vehiculo(motor=True, contacto=True), Ecu()
    v.cambiar("3")
    v.velocidad, v.acelerador = 150.0, 1.0
    v.fallas.sobrepresion_turbo = True
    sobre = 0.0
    for _ in range(int(10 / DT)):
        ecu.vigilar(v, DT)
        v.avanzar(DT)
        sobre += DT if v.presion_turbo > 1.5 else 0.0
        if not v.motor:
            break
    assert not v.motor and ecu.proteccion == "sobrepresion_turbo" and 0.9 <= sobre <= 1.3
    assert "turbo" in ecu.motivo_sin_arranque(v)
    v.fallas.sobrepresion_turbo = False
    assert ecu.motivo_sin_arranque(v) is None


def test_cp175_falla_de_frenos_frena_mal_y_los_frenos_calientes_pierden_eficiencia():
    """CP-175: con falla de frenos la eficiencia baja al 30 % y desde 100 km/h el auto tarda mas de 2.5 veces en detenerse (R08); cada frenada calienta los discos y en caliente la eficiencia baja hasta 60 % (fading)."""
    def detener(fallas):
        v = Vehiculo(motor=True, velocidad=100.0, fallas=fallas)
        v.freno, t = 1.0, 0.0
        while v.velocidad > 0:
            v.avanzar(DT)
            t += DT
        return t, v.temp_frenos
    sano, falla = detener(Fallas()), detener(Fallas(frenos=True))
    assert falla[0] > 2.5 * sano[0] and sano[1] > 80
    assert Vehiculo(fallas=Fallas(frenos=True)).eficiencia_frenos == pytest.approx(0.30)
    caliente = Vehiculo()
    caliente.temp_frenos = 750.0
    assert caliente.eficiencia_frenos == pytest.approx(0.60)
    caliente.temp_frenos = 300.0
    assert caliente.eficiencia_frenos == 1.0


def test_cp176_puerta_abierta_impide_avanzar():
    """CP-176: con una puerta abierta la ECU bloquea la traccion: el auto no avanza aunque se acelere y se avisa una vez; al cerrar la puerta avanza (R09)."""
    v, ecu = Vehiculo(motor=True, contacto=True, puertas=2), Ecu()
    v.cambiar("1")
    v.acelerador = 1.0
    avisos = []
    _conducir(v, ecu, 3, avisos)
    assert v.velocidad == 0.0 and v.traccion_bloqueada and len(avisos) == 1 and "puerta" in avisos[0]
    v.puertas = 0
    _conducir(v, ecu, 3)
    assert v.velocidad > 20 and not v.traccion_bloqueada


def test_cp177_sin_combustible_el_motor_se_apaga_y_no_arranca():
    """CP-177: el consumo vacia el tanque (2 L/h en ralenti); sin combustible el motor se apaga, la ECU informa la causa combustible y no arranca hasta cargar (R11, R12)."""
    v, ecu = Vehiculo(motor=True, contacto=True), Ecu()
    inicial = v.combustible_l
    _conducir(v, ecu, 60)
    assert inicial - v.combustible_l == pytest.approx(2.0 / 60, rel=0.05)
    v.combustible_l = 0.02
    v.cambiar("3")
    v.velocidad, v.acelerador = 100.0, 1.0
    avisos = []
    _conducir(v, ecu, 10, avisos)
    assert not v.motor and v.combustible_l == 0.0 and ecu.proteccion == "combustible"
    assert any("sin combustible" in a for a in avisos) and v.lecturas_extra(ecu.proteccion)["combustible"] == 0.0
    assert ecu.motivo_sin_arranque(v) is not None
    v.combustible_l = TANQUE_L
    assert ecu.motivo_sin_arranque(v) is None


def test_cp178_panel_llave_arranque_puertas_y_taller(tmp_path):
    """CP-178: el panel separa llave y arranque, no arranca con fuga de aceite y lo avisa, escribe las claves opcionales que acepta el lector, la puerta abierta impide avanzar, el taller repara y el banco y el ciclo ECE-15 corren desde el panel."""
    tk = pytest.importorskip("tkinter")
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from panel.ventana import Panel
    reloj = [0.0]
    p = Panel(raiz, ruta_datos=tmp_path / "vehiculo.conf", dir_logs=tmp_path / "logs", reloj=lambda: reloj[0])
    p.raiz.after_cancel(p._id_after)

    def avanzar(segundos):
        for _ in range(int(segundos / DT)):
            reloj[0] += DT
            p.paso(DT)

    def leer():
        bitacora = Bitacora(tmp_path / "logs_lector")
        try:
            return Lector(p.ruta, RANGOS, bitacora).leer()
        finally:
            bitacora.cerrar()

    try:
        assert p.alternar_contacto() is True and p.vehiculo.contacto and not p.vehiculo.motor
        p.var_fallas["fuga_aceite"].set(True)
        p._fallas()
        assert p.alternar_motor() is False and "No arranca" in p.texto_consola()
        avanzar(0.3)
        datos = leer()
        assert datos["contacto"] is True and datos["motor"] is False and datos["falla_motor"] == "aceite"
        assert set(p.valores_extra()) == set(CLAVES_EXTRA) and set(p.valores_actuales()) == set(CLAVES)
        p.taller("reparar")
        assert not p.vehiculo.fallas.fuga_aceite
        p.var_puertas[1].set(True)
        p._seguridad()
        assert p.alternar_motor() is True and p.cambiar("1")
        p.pisando["acelerador"] = True
        avanzar(1.5)
        assert p.vehiculo.velocidad == 0.0 and "Interbloqueo" in p.texto_consola() and leer()["puertas"] == 1
        p.var_puertas[1].set(False)
        p._seguridad()
        avanzar(1.5)
        assert p.vehiculo.velocidad > 10
        p.pisando["acelerador"] = False
        for accion in ("reserva", "aceite", "tanque"):
            assert p.taller(accion)
        assert p.vehiculo.combustible_l == TANQUE_L and p.vehiculo.nivel_aceite == 100.0
        with pytest.raises(ValueError):
            p.taller("pintar")
        p.dibujar()
        assert p.lbl_extra["falla_motor"].cget("text") == "ninguna"
        assert p.ciclo_ece15() and p.modo == "ciclo"
        avanzar(15)
        assert p.vehiculo.velocidad > 5                  # de 11 a 23 s el ciclo pide 15 km/h
        p.detener_todo()
        assert p.modo == "fisica" and p.vehiculo.acelerador == 0.0
        assert p.reproducir_escenario("CA-01") and p.valores_extra() == {}
        p.detener_todo()
        assert p.banco_actual()
        mensajes, fin = [], time.monotonic() + 120
        while time.monotonic() < fin and not any(tipo == "fin" for tipo, _ in mensajes):
            mensajes += p.ejecutor.pendientes()
            time.sleep(0.05)
        assert ("fin", 0) in mensajes and any("APTO PARA PRODUCCION" in str(m) for _, m in mensajes)
        assert callable(comandos.observar_proceso) and "ps" in comandos.observar_proceso() or sys.platform == "win32"
    finally:
        p.ejecutor.detener()
        raiz.destroy()
