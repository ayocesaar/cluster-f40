"""Pruebas del odometro (elemento 11), agregado tras la practica en clase.

CP-120, CP-122 y CP-125 automatizan los tres casos de la practica (CP-ODO-01,
02 y 03) con la correccion de duraciones (45 s y 15 s); el resto cubre limites,
persistencia, respaldo, seguridad e integracion con la interfaz."""

import gc
import os

import pytest

from logic.estado import EstadoCluster
from logic.odometro import MAXIMO_KM, Odometro
from sistema import config as configuracion
from sistema import odometro_archivo
from sistema.bitacora import Bitacora
from sistema.lector import Lector
from sistema.monitor import MonitorEventos

tk = pytest.importorskip("tkinter")
RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)


@pytest.fixture(autouse=True)
def _recolectar_en_hilo_principal():
    gc.collect()
    yield


@pytest.fixture
def bitacora(tmp_path):
    b = Bitacora(tmp_path / "logs")
    yield b
    b.cerrar()


def _log(bitacora, cual):
    for manejador in bitacora._logger.handlers:
        manejador.flush()
    ruta = bitacora.ruta_eventos if cual == "eventos" else bitacora.ruta_errores
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _manejar(estado, reloj, velocidad, segundos):
    estado.set_motor(True)
    estado.set_velocidad(velocidad)
    for _ in range(int(segundos * 10)):
        reloj.avanzar(100)
        estado.tick()


def _requiere_display():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")


def test_cp120_odo01_acumula_la_distancia_recorrida(reloj):
    """CP-120: CP-ODO-01 a 120 km/h durante 45 s el odometro pasa de 000062 a 000063 (1.5 km)."""
    estado = EstadoCluster(reloj, odometro_km=62.0)
    estado.tick()
    assert estado.odometro.texto == "000062"
    _manejar(estado, reloj, 120, 45)
    assert estado.odometro.texto == "000063"
    assert estado.odometro.km == pytest.approx(63.5)


def test_cp121_odo01_un_kilometro_exacto_sin_error_de_redondeo(reloj):
    """CP-121: 300 ciclos de 100 ms a 120 km/h suman exactamente 1 km; el redondeo no deja 62.999."""
    estado = EstadoCluster(reloj, odometro_km=62.0)
    _manejar(estado, reloj, 120, 30)
    assert estado.odometro.valor == 63


def test_cp122_odo02_vuelve_a_cero_al_pasar_del_maximo(reloj):
    """CP-122: CP-ODO-02 desde 999999, a 360 km/h durante 15 s (1.5 km) el contador vuelve a 000000."""
    estado = EstadoCluster(reloj, odometro_km=999_999.0)
    _manejar(estado, reloj, 360, 15)
    assert estado.odometro.texto == "000000"
    assert estado.odometro.vueltas == 1
    assert estado.odometro.km == pytest.approx(0.5)


def test_cp123_no_avanza_detenido_ni_con_motor_apagado(reloj):
    """CP-123: con velocidad 0 o con el motor apagado (R01) el odometro no avanza."""
    estado = EstadoCluster(reloj, odometro_km=10.0)
    _manejar(estado, reloj, 0, 60)
    assert estado.odometro.km == 10.0
    estado.set_velocidad(120)
    estado.set_motor(False)
    for _ in range(100):
        reloj.avanzar(100)
        estado.tick()
    assert estado.odometro.km == 10.0


def test_cp124_odometro_valida_sus_entradas_y_nunca_retrocede():
    """CP-124: el valor inicial debe ser numerico y estar en 0-999999; velocidades o tiempos negativos no restan."""
    for invalido, error in ((-1, ValueError), (MAXIMO_KM, ValueError), (True, TypeError), ("62", TypeError)):
        with pytest.raises(error):
            Odometro(invalido)
    o = Odometro(5.0)
    o.avanzar(-100, 1000)
    o.avanzar(100, -1000)
    o.avanzar(100, 0)
    assert o.km == 5.0
    assert Odometro(999_999.9999999).valor == 999_999


def test_cp125_odo03_archivo_corrupto_inicia_en_cero_con_aviso(tmp_path, bitacora):
    """CP-125: CP-ODO-03 si datos/odometro.txt contiene abc, se inicia en 000000, se avisa y se registra ERROR."""
    ruta = tmp_path / "odometro.txt"
    ruta.write_text("abc\n", encoding="utf-8")
    km, aviso = odometro_archivo.cargar(ruta, bitacora)
    assert km == 0.0 and aviso.startswith("Odometro: archivo invalido")
    assert 'odometro_invalido archivo=odometro.txt contenido="abc"' in _log(bitacora, "errores")


def test_cp126_respaldo_recupera_el_kilometraje(tmp_path, bitacora):
    """CP-126: si el archivo principal esta corrupto o falta, se recupera del respaldo .bak."""
    ruta = tmp_path / "odometro.txt"
    odometro_archivo.respaldo(ruta).write_text("62.5\n", encoding="utf-8")
    ruta.write_text("xx", encoding="utf-8")
    km, aviso = odometro_archivo.cargar(ruta, bitacora)
    assert km == 62.5 and aviso == "Odometro restaurado del respaldo: 000062 km"
    ruta.unlink()
    km, _ = odometro_archivo.cargar(ruta, bitacora)
    assert km == 62.5
    eventos, errores = _log(bitacora, "eventos"), _log(bitacora, "errores")
    assert eventos.count("odometro_restaurado") == 2 and "odometro_inexistente archivo=odometro.txt" in errores


def test_cp127_persistencia_atomica_con_respaldo(tmp_path, bitacora):
    """CP-127: guardar escribe el principal y el respaldo; al cargar se recupera el mismo kilometraje."""
    ruta = tmp_path / "odometro.txt"
    odometro_archivo.guardar(ruta, 1234.5678)
    assert ruta.read_text(encoding="utf-8") == "1234.567800\n"
    assert odometro_archivo.respaldo(ruta).read_text(encoding="utf-8") == "1234.567800\n"
    assert odometro_archivo.cargar(ruta, bitacora) == (1234.5678, None)
    assert "odometro_cargado km=1234.568" in _log(bitacora, "eventos")
    assert not list(tmp_path.glob(".vehiculo.*.tmp"))
    with pytest.raises(ValueError):
        odometro_archivo.guardar(ruta, MAXIMO_KM)
    if os.name == "posix":
        assert oct(ruta.stat().st_mode & 0o777) == "0o640"


def test_cp128_primer_arranque_sin_archivos(tmp_path, bitacora):
    """CP-128: la primera vez, sin archivo ni respaldo, se inicia en 000000 sin error."""
    assert odometro_archivo.cargar(tmp_path / "odometro.txt", bitacora) == (0.0, None)
    assert "odometro_nuevo" in _log(bitacora, "eventos") and _log(bitacora, "errores") == ""


@pytest.mark.parametrize("contenido, motivo", [("1000000", "contenido="), ("-5", "contenido="), ("12" * 40, "demasiado grande")])
def test_cp129_valores_invalidos_del_archivo(tmp_path, bitacora, contenido, motivo):
    """CP-129: un valor fuera de rango, negativo o un archivo demasiado grande se rechazan."""
    ruta = tmp_path / "odometro.txt"
    ruta.write_text(contenido, encoding="utf-8")
    assert odometro_archivo.cargar(ruta, bitacora)[0] == 0.0
    assert motivo in _log(bitacora, "errores")


def test_cp130_archivo_ilegible_o_con_codificacion_invalida(tmp_path, bitacora):
    """CP-130: un archivo con bytes que no son UTF-8 se rechaza sin detener el sistema."""
    ruta = tmp_path / "odometro.txt"
    ruta.write_bytes(b"\xff\xfe")
    assert odometro_archivo.cargar(ruta, bitacora)[0] == 0.0
    assert "codificacion no valida" in _log(bitacora, "errores")


@pytest.mark.skipif(os.name != "posix", reason="los bits de permiso son de POSIX")
def test_cp131_kilometraje_manipulable_por_otros_se_rechaza(tmp_path, bitacora):
    """CP-131: un odometro.txt escribible por cualquiera se rechaza: nadie mas que el dueno puede alterar el kilometraje."""
    ruta = tmp_path / "odometro.txt"
    ruta.write_text("500\n", encoding="utf-8")
    os.chmod(ruta, 0o666)
    assert odometro_archivo.cargar(ruta, bitacora)[0] == 0.0
    assert "permisos inseguros modo=0o666" in _log(bitacora, "errores")


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="requiere permisos POSIX y un usuario que no sea root")
def test_cp132_kilometraje_sin_permiso_de_lectura(tmp_path, bitacora):
    """CP-132: un odometro.txt sin permiso de lectura se rechaza y se registra."""
    ruta = tmp_path / "odometro.txt"
    ruta.write_text("500\n", encoding="utf-8")
    os.chmod(ruta, 0o200)
    try:
        assert odometro_archivo.cargar(ruta, bitacora)[0] == 0.0
    finally:
        os.chmod(ruta, 0o640)
    assert "sin permiso de lectura" in _log(bitacora, "errores")


def test_cp133_el_odometro_no_se_escribe_desde_el_archivo_de_datos(tmp_path, bitacora):
    """CP-133: odometro=999999 en datos/vehiculo.conf se rechaza (clave_no_permitida) y lo demas se aplica."""
    datos = tmp_path / "vehiculo.conf"
    datos.write_text("motor=1\nvelocidad=50\nodometro=999999\n", encoding="utf-8")
    snapshot = Lector(datos, RANGOS, bitacora).leer()
    assert snapshot["velocidad"] == 50.0 and "odometro" not in snapshot
    assert "clave_no_permitida linea 3 clave=odometro" in _log(bitacora, "errores")


def test_cp134_configuracion_del_odometro(tmp_path):
    """CP-134: la ruta y la frecuencia de guardado del odometro se leen de la configuracion y se validan."""
    ini = tmp_path / "cluster.ini"
    ini.write_text("[rutas]\nodometro = otro/km.txt\n[odometro]\nguardar_cada_s = 0\n", encoding="utf-8")
    cfg = configuracion.cargar(ini, raiz=tmp_path)
    assert cfg.archivo_odometro == tmp_path / "otro" / "km.txt"
    assert cfg.guardar_cada_s == 5
    assert ("valor_invalido", "odometro.guardar_cada_s='0' (rango 1-3600; se usa 5)") in cfg.errores
    defecto = configuracion.cargar(tmp_path / "no_existe.ini", raiz=tmp_path)
    assert defecto.archivo_odometro == tmp_path / "datos" / "odometro.txt"


def test_cp137_el_monitor_registra_cada_kilometro(bitacora, reloj):
    """CP-137: eventos.log registra INFO odometro_actualizado al cambiar el kilometro mostrado, incluida la vuelta a 000000."""
    estado = EstadoCluster(reloj, odometro_km=999_998.5)
    monitor = MonitorEventos(bitacora)
    _manejar(estado, reloj, 0, 0.1)
    monitor.revisar(estado)
    estado.set_velocidad(360)
    for _ in range(200):  # 20 s a 360 km/h = 2 km
        reloj.avanzar(100)
        estado.tick()
        monitor.revisar(estado)
    eventos = _log(bitacora, "eventos")
    assert eventos.count(" odometro_actualizado ") == 2
    assert "odometro_actualizado km=999999 resultado=aceptado" in eventos
    assert "odometro_actualizado km=000000 vuelta_a_cero vueltas=1 resultado=aceptado" in eventos


def test_cp135_el_tablero_muestra_el_odometro(reloj):
    """CP-135: la ventana dibuja el odometro de 6 digitos en el velocimetro y lo actualiza con la marcha."""
    _requiere_display()
    from ui.tablero import Tablero
    raiz = tk.Tk()
    estado = EstadoCluster(reloj, odometro_km=62.0)
    tablero = Tablero(raiz, estado)
    try:
        assert tablero.canvas.itemcget(tablero.items[11]["valor"], "text") == "000062"
        tablero.ajustar("set_motor", True)
        tablero.ajustar("set_velocidad", 120)
        for _ in range(450):
            reloj.avanzar(100)
            tablero.ciclo()
        assert tablero.canvas.itemcget(tablero.items[11]["valor"], "text") == "000063"
        tablero.avisar("Odometro restaurado del respaldo: 000062 km")
        assert tablero.aviso.cget("text").startswith("Odometro restaurado")
    finally:
        tablero.detener()
        raiz.destroy()


def test_cp136_la_aplicacion_carga_y_guarda_el_kilometraje(tmp_path, monkeypatch):
    """CP-136: la aplicacion recupera el kilometraje al iniciar, lo guarda al cerrar y avisa si el archivo es invalido."""
    _requiere_display()
    import main as principal
    (tmp_path / "datos").mkdir()
    ruta = tmp_path / "datos" / "odometro.txt"
    ruta.write_text("100.25\n", encoding="utf-8")
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, manual=True, ruta_config=tmp_path / "no.ini", proyecto=tmp_path)
    try:
        assert app.estado.odometro.km == 100.25
        assert app.guardar_odometro() is False             # sin cambios no reescribe
        app.estado.odometro.avanzar(120, 30_000)            # 1 km
        raiz.after_cancel(app._id_guardado)                 # se simula que vencio el temporizador
        app._guardar_periodico()

        def sin_espacio(*_):
            raise OSError("disco lleno")
        monkeypatch.setattr(odometro_archivo, "guardar", sin_espacio)
        app.estado.odometro.avanzar(120, 30_000)
        assert app.guardar_odometro() is False
    finally:
        monkeypatch.undo()
        app.cerrar()
    assert ruta.read_text(encoding="utf-8") == "102.250000\n"
    eventos = (tmp_path / "logs" / "eventos.log").read_text(encoding="utf-8")
    errores = (tmp_path / "logs" / "errores.log").read_text(encoding="utf-8")
    assert "odometro_cargado km=100.250" in eventos and "odometro_guardado km=101.250" in eventos
    assert "odometro_guardado km=102.250" in eventos and "odometro_no_guardado OSError: disco lleno" in errores

    ruta.write_text("abc", encoding="utf-8")
    odometro_archivo.respaldo(ruta).unlink()
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, manual=True, ruta_config=tmp_path / "no.ini", proyecto=tmp_path)
    try:
        assert app.estado.odometro.texto == "000000"
        assert app.tablero.aviso.cget("text") == "Odometro: archivo invalido, se inicio en 000000"
    finally:
        app.cerrar()
