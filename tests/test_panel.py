"""Pruebas del panel de control (Etapa 16): modelo fisico, escritura del archivo de
datos, mandos, entradas invalidas, escenarios en vivo y atajos de comandos."""

import gc
import os
import random
import sys
import time

import pytest

from panel import comandos
from panel.fisica import LIMITADOR, RALENTI, Vehiculo, velocidad_maxima
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import CLAVES, Lector, convertir, formatear

tk = pytest.importorskip("tkinter")
RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)


def _conducir(v, segundos, dt=0.05):
    for _ in range(int(segundos / dt)):
        v.avanzar(dt)


def test_cp155_arranque_en_reposo_y_ralenti():
    """CP-155: apagado todo queda en reposo; al dar contacto: ralenti 1000 rpm, aceite 1.5 bar y el agua se calienta (R01)."""
    v = Vehiculo()
    _conducir(v, 2)
    assert v.lecturas()["rpm"] == 0 and v.presion_aceite == 0 and v.velocidad == 0
    v.motor = True
    _conducir(v, 2)
    assert v.lecturas()["rpm"] == RALENTI and v.presion_aceite == pytest.approx(1.5)
    _conducir(v, 120)
    assert 85 <= v.temp_agua <= 90 and v.velocidad == 0


def test_cp156_marchas_acoplan_rpm_y_limitador():
    """CP-156: en marcha las rpm siguen a la velocidad; el limitador nunca deja pasar de 8200; al subir de marcha bajan las rpm."""
    v = Vehiculo(motor=True)
    v.cambiar("1")
    v.acelerador = 1.0
    maximo = 0
    for _ in range(400):
        v.avanzar(0.05)
        maximo = max(maximo, v.rpm)
    assert maximo <= LIMITADOR and v.lecturas()["rpm"] >= 8000          # el tacometro llega a rojo (R03)
    assert v.velocidad == pytest.approx(velocidad_maxima("1"), abs=1)
    antes = v.rpm
    v.cambiar("2")
    v.avanzar(0.05)
    assert v.rpm < antes
    with pytest.raises(ValueError, match="limitador"):
        Vehiculo(motor=True, velocidad=200.0).cambiar("1")
    with pytest.raises(ValueError, match="reversa"):
        Vehiculo(motor=True, velocidad=50.0).cambiar("R")


def test_cp157_freno_y_revoluciones_en_vacio():
    """CP-157: el freno detiene el auto sin velocidades negativas; en neutral el acelerador solo sube las rpm."""
    v = Vehiculo(motor=True, velocidad=150.0)
    v.freno = 1.0
    _conducir(v, 6)
    assert v.velocidad == 0.0
    v.freno = 0.0
    v.acelerador = 1.0
    _conducir(v, 3)
    assert v.velocidad == 0.0 and v.rpm >= 8000


def test_cp158_fallas_producen_cada_advertencia():
    """CP-158: turbo con retraso (max 1.1 bar); las fallas llevan el turbo a > 1.5 (R05), el aceite < 1 (R02) y el agua > 110 (R04)."""
    v = Vehiculo(motor=True)
    v.cambiar("3")
    v.velocidad = 150.0
    v.acelerador = 1.0
    v.avanzar(0.05)
    assert v.presion_turbo < 0.3                     # el turbo no responde de golpe
    _conducir(v, 3)
    assert 0.9 <= v.presion_turbo <= 1.1
    v.fallas.sobrepresion_turbo = True
    _conducir(v, 3)
    assert v.presion_turbo > 1.5
    reposo = Vehiculo(motor=True)
    reposo.fallas.fuga_aceite = True
    _conducir(reposo, 1)
    assert reposo.presion_aceite < 1.0
    reposo.fallas.radiador = True
    _conducir(reposo, 120)
    assert reposo.temp_agua > 110


def test_cp159_el_panel_nunca_produce_un_dato_invalido():
    """CP-159: 20 000 pasos con pedales, marchas, fallas y contacto al azar: cada lectura pasa la validacion del lector."""
    random.seed(16)
    v = Vehiculo()
    for _ in range(20_000):
        r = random.random()
        if r < 0.02:
            v.motor = not v.motor
        elif r < 0.06:
            try:
                v.cambiar(random.choice(["R", "N", "1", "2", "3", "4", "5"]))
            except ValueError:
                pass
        elif r < 0.07:
            setattr(v.fallas, random.choice(["fuga_aceite", "radiador", "sobrepresion_turbo", "frenos"]),
                    random.random() < 0.5)
        v.acelerador, v.freno, v.embrague = (random.choice([0, 0.3, 1]) for _ in range(3))
        v.avanzar(random.choice([0.01, 0.05, 0.2, 1.0]))
        for clave, valor in v.lecturas().items():
            convertir(clave, formatear(clave, valor), RANGOS)       # lanza DatoInvalido si no es valido


@pytest.fixture
def panel(tmp_path):
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from panel.ventana import Panel
    reloj = [0.0]
    p = Panel(raiz, ruta_datos=tmp_path / "vehiculo.conf", dir_logs=tmp_path / "logs", reloj=lambda: reloj[0])
    p.raiz.after_cancel(p._id_after)                 # las pruebas avanzan el ciclo a mano
    p.reloj_falso = reloj
    yield p
    p.raiz.destroy()


def _avanzar(p, segundos):
    for _ in range(int(segundos / 0.05)):
        p.reloj_falso[0] += 0.05
        p.paso(0.05)


def _esperar_fin(ejecutor, limite_s=10):
    mensajes = []
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        mensajes += ejecutor.pendientes()
        if any(tipo == "fin" for tipo, _ in mensajes):
            return mensajes
        time.sleep(0.05)
    raise AssertionError(f"el comando no termino: {mensajes}")


def _leer(p, tmp_path):
    bitacora = Bitacora(tmp_path / "logs_lector")
    try:
        return Lector(p.ruta, RANGOS, bitacora).leer()
    finally:
        bitacora.cerrar()


def test_cp160_pedales_y_luces_llegan_al_archivo(panel, tmp_path):
    """CP-160: contacto, marcha, acelerador y luces del panel quedan en datos/vehiculo.conf y el lector del tablero los acepta."""
    panel.alternar_motor()
    assert panel.cambiar("1")
    panel.pisando["acelerador"] = True
    panel.var_altas.set(True)
    panel.var_direccional.set("IZQ")
    panel._luces()
    _avanzar(panel, 2)
    panel.dibujar()
    datos = _leer(panel, tmp_path)
    assert datos["motor"] is True and datos["velocidad"] > 20 and datos["rpm"] > RALENTI
    assert datos["luces_altas"] is True and datos["direccional"] == "IZQ"
    assert panel.escrituras > 5 and "Contacto: motor ENCENDIDO" in panel.texto_consola()
    panel.vehiculo.embrague = 0.0
    panel.var_embrague_auto.set(False)
    assert panel.cambiar("2") is False                          # sin embrague no entra la marcha


@pytest.mark.parametrize("tipo, esperado", [("corrupto", "temp_agua=abc"), ("fuera", "velocidad=400"),
                                            ("borrar", None)])
def test_cp161_entradas_invalidas_y_restauracion(panel, tmp_path, tipo, esperado):
    """CP-161: el panel escribe la entrada invalida, deja de escribir 3 s y luego restaura datos validos."""
    _avanzar(panel, 0.2)
    assert panel.inyectar(tipo)
    if esperado:
        assert esperado in panel.ruta.read_text(encoding="utf-8")
    else:
        assert not panel.ruta.exists()
    _avanzar(panel, 2)
    assert not panel.ruta.exists() or esperado in panel.ruta.read_text(encoding="utf-8")
    _avanzar(panel, 1.5)
    texto = panel.ruta.read_text(encoding="utf-8")
    assert "abc" not in texto and "velocidad=400" not in texto
    assert _leer(panel, tmp_path)["temp_agua"] == 40.0


def test_cp162_escenarios_en_vivo_y_atajos(panel, tmp_path):
    """CP-162: un escenario de aceptacion se reproduce en el archivo paso a paso; los atajos existen y el ejecutor reporta su codigo."""
    assert len(panel.escenarios) == 10
    panel.PASO_ESCENARIO_MIN_S = 0.0
    assert panel.reproducir_escenario("CA-10")
    _avanzar(panel, 0.1)
    vistos = []
    for _ in range(200):
        _avanzar(panel, 0.1)
        vistos.append(_leer(panel, tmp_path)["falla_frenos"] if panel.ruta.exists() else None)
        if panel.modo == "fisica":
            break
    assert True in vistos and panel.modo == "fisica"
    assert "Escenario terminado" in panel.texto_consola() and "CA-10" in panel.texto_consola()

    for _grupo, lista in comandos.ATAJOS:
        for _etiqueta, _ayuda, comando in lista:
            if not callable(comando):
                for arg in comando:
                    if arg.endswith((".py", ".sh", ".csv")) and not arg.startswith("-"):
                        assert (comandos.RAIZ / arg).exists() or os.path.isabs(arg), arg
    ejecutor = comandos.Ejecutor()
    assert ejecutor.iniciar([sys.executable, "-c", "print('hola panel')"], "prueba")
    assert ("linea", "hola panel") in _esperar_fin(ejecutor)
    malo = comandos.Ejecutor()
    malo.iniciar([sys.executable, "-c", "raise SystemExit(3)"])
    assert ("fin", 3) in _esperar_fin(malo)
    assert "Hilos" in comandos.estado_tablero() or "no esta en ejecucion" in comandos.estado_tablero()
    assert set(CLAVES) == set(panel.valores_actuales())
