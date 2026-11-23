"""Pruebas de robustez (Etapa 14): cada una reproduce un defecto encontrado en la
auditoria externa del 23-nov-2026 (DEF-04 a DEF-12) y queda como regresion.

Se escribieron ANTES de corregir; en la version 5e9506b fallan (evidencia en
docs/evidencias/robustez_antes.txt)."""

import gc
import os
import pathlib
import queue
import sys
import threading

import pytest

from logic.estado import EstadoCluster
from sistema import config as configuracion
from sistema import odometro_archivo
from sistema.bitacora import Bitacora
from sistema.lector import Consumidor, Lector, escribir_texto_atomico

tk = pytest.importorskip("tkinter")
RAIZ = pathlib.Path(__file__).resolve().parent.parent
RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)
BASE = {"motor": "1", "velocidad": "0", "rpm": "1000", "presion_aceite": "5", "temp_agua": "90",
        "presion_turbo": "0.5", "direccional": "off", "luces_altas": "0", "emergencia": "0", "falla_frenos": "0"}


@pytest.fixture(autouse=True)
def _recolectar():
    gc.collect()
    yield


@pytest.fixture
def bitacora(tmp_path):
    b = Bitacora(tmp_path / "logs")
    yield b
    b.cerrar()


def _texto(**cambios):
    datos = dict(BASE, **cambios)
    return "".join(f"{k}={v}\n" for k, v in datos.items())


def _requiere_display():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")


def _tablero(reloj):
    from ui.tablero import Tablero
    raiz = tk.Tk()
    return raiz, Tablero(raiz, EstadoCluster(reloj))


def test_cp138_decimales_del_archivo_llegan_sin_redondear(tmp_path, bitacora, reloj):
    """CP-138: 0.9999 bar, 110.01 C y 1.5001 bar del archivo encienden sus advertencias (R02, R04, R05; DEF-04)."""
    _requiere_display()
    datos = tmp_path / "vehiculo.conf"
    datos.write_text(_texto(presion_aceite="0.9999", temp_agua="110.01", presion_turbo="1.5001"), encoding="utf-8")
    lector = Lector(datos, RANGOS, bitacora)
    raiz, tablero = _tablero(reloj)
    try:
        buzon = queue.Queue(maxsize=1)
        tablero.antes_del_tick = Consumidor(buzon, tablero)
        buzon.put(lector.leer())
        for _ in range(15):
            reloj.avanzar(100)
            tablero.ciclo()
        estado = tablero.estado
        assert (estado.p_aceite, estado.temp_agua, estado.p_turbo) == (0.9999, 110.01, 1.5001)
        assert estado.testigo_baja_presion_aceite is True
        assert estado.color_temp == "rojo" and estado.contorno_turbo == "ambar"
    finally:
        tablero.detener()
        raiz.destroy()


def test_cp139_dato_rechazado_del_archivo_se_avisa_en_pantalla(tmp_path, bitacora, reloj):
    """CP-139: un valor fuera de rango en el archivo muestra aviso en la ventana y se retira al corregirlo (P04; DEF-05)."""
    _requiere_display()
    datos = tmp_path / "vehiculo.conf"
    lector = Lector(datos, RANGOS, bitacora)
    raiz, tablero = _tablero(reloj)
    try:
        buzon = queue.Queue(maxsize=1)
        tablero.antes_del_tick = Consumidor(buzon, tablero, lector=lector)
        datos.write_text(_texto(velocidad="50"), encoding="utf-8")
        buzon.put(lector.leer())
        tablero.ciclo()
        escribir_texto_atomico(datos, _texto(velocidad="400"))
        buzon.put(lector.leer())
        tablero.ciclo()
        assert "velocidad" in tablero.mensaje.cget("text")
        assert tablero.estado._obj_velocidad == 50.0
        escribir_texto_atomico(datos, _texto(velocidad="60"))
        buzon.put(lector.leer())
        tablero.ciclo()
        assert tablero.mensaje.cget("text") == ""
    finally:
        tablero.detener()
        raiz.destroy()


def test_cp140_un_error_en_un_ciclo_no_congela_el_tablero(reloj):
    """CP-140: si un ciclo de refresco lanza una excepcion, el siguiente ciclo queda programado (DEF-06)."""
    _requiere_display()
    raiz, tablero = _tablero(reloj)
    try:
        fallas = iter([RuntimeError("falla de un ciclo")])

        def una_vez():
            error = next(fallas, None)
            if error:
                raise error
        tablero.antes_del_tick = una_vez
        tablero.detener()
        with pytest.raises(RuntimeError):
            tablero._programar()
        assert tablero._id_after is not None
    finally:
        tablero.detener()
        raiz.destroy()


def test_cp141_refresco_no_puede_ocultar_los_parpadeos(tmp_path):
    """CP-141: refresco_ms mayor a 100 se rechaza: con 1000 ms todas las muestras caen en la misma fase del parpadeo (R06; DEF-06)."""
    ini = tmp_path / "cluster.ini"
    ini.write_text("[intervalos]\nrefresco_ms = 1000\n", encoding="utf-8")
    cfg = configuracion.cargar(ini, raiz=tmp_path)
    assert cfg.refresco_ms == 50 and cfg.errores[0][0] == "valor_invalido"


def test_cp142_odometro_integra_cada_tramo_con_su_velocidad(reloj):
    """CP-142: tras un retraso de 10 s, el cambio de velocidad no se aplica al tiempo anterior (DEF-07)."""
    estado = EstadoCluster(reloj)
    estado.set_motor(True)
    reloj.avanzar(100)
    estado.tick()
    estado.set_velocidad(360)
    reloj.avanzar(10_000)
    estado.tick()
    assert estado.odometro.km < 0.011          # solo el ultimo ciclo de 100 ms a 360 km/h
    for _ in range(10):
        reloj.avanzar(100)
        estado.tick()
    antes = estado.odometro.km
    estado.set_velocidad(0)
    reloj.avanzar(10_000)
    estado.tick()
    assert estado.odometro.km - antes == pytest.approx(360 * 9.9 / 3600)


def test_cp143_dos_instancias_no_pierden_kilometraje(tmp_path, monkeypatch):
    """CP-143: una segunda ventana con la misma carpeta no guarda el odometro y lo avisa; el kilometraje de la primera se conserva (DEF-08)."""
    _requiere_display()
    import main as principal
    (tmp_path / "datos").mkdir()
    ruta = tmp_path / "datos" / "odometro.txt"
    ruta.write_text("100.25\n", encoding="utf-8")
    r1, r2 = tk.Tk(), None
    a1 = principal.Aplicacion(r1, manual=True, ruta_config=tmp_path / "no.ini", proyecto=tmp_path)
    try:
        r2 = tk.Tk()
        a2 = principal.Aplicacion(r2, manual=True, ruta_config=tmp_path / "no.ini", proyecto=tmp_path)
        assert "otra ventana" in a2.tablero.aviso.cget("text")
        a1.estado.odometro.avanzar(120, 60_000)      # 2 km en la primera
        a1.guardar_odometro()
        a2.estado.odometro.avanzar(120, 30_000)      # 1 km en la segunda
        a2.cerrar()
    finally:
        a1.cerrar()
    assert ruta.read_text(encoding="utf-8") == "102.250000\n"
    errores = (tmp_path / "logs" / "errores.log").read_text(encoding="utf-8")
    assert "odometro_en_uso" in errores


def test_cp144_configuracion_defectuosa_no_impide_arrancar(tmp_path):
    """CP-144: refresco_ms=50% y una ruta de bitacoras que es un archivo no detienen el arranque (DEF-09)."""
    _requiere_display()
    import main as principal
    (tmp_path / "config").mkdir()
    (tmp_path / "ocupado").write_text("no soy carpeta", encoding="utf-8")
    ini = tmp_path / "config" / "cluster.ini"
    ini.write_text("[rutas]\nlogs = ocupado\n[intervalos]\nrefresco_ms = 50%\n", encoding="utf-8")
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, manual=True, ruta_config=ini, proyecto=tmp_path)
    try:
        assert app.cfg.refresco_ms == 50
        assert app.bitacora.dir_logs == tmp_path / "logs"
    finally:
        app.cerrar()
    errores = (tmp_path / "logs" / "errores.log").read_text(encoding="utf-8")
    assert "refresco_ms='50%'" in errores and "logs_invalido" in errores


def test_cp145_reemplazo_con_igual_tamano_y_fecha_se_detecta(tmp_path, bitacora):
    """CP-145: un archivo reemplazado con el mismo tamano y la misma fecha se vuelve a leer (DEF-10)."""
    datos = tmp_path / "vehiculo.conf"
    escribir_texto_atomico(datos, _texto(velocidad="50"))
    lector = Lector(datos, RANGOS, bitacora)
    assert lector.leer()["velocidad"] == 50.0
    fecha = datos.stat().st_mtime_ns
    escribir_texto_atomico(datos, _texto(velocidad="60"))
    os.utime(datos, ns=(fecha, fecha))
    nuevo = lector.leer()
    assert nuevo is not None and nuevo["velocidad"] == 60.0


@pytest.mark.skipif(os.name != "posix", reason="usa fcntl")
def test_cp146_escrituras_simultaneas_no_se_pierden(tmp_path):
    """CP-146: dos escritores simultaneos con escribir_dato.py no se pisan los cambios (DEF-10)."""
    sys.path.insert(0, str(RAIZ / "tools"))
    import escribir_dato
    datos = tmp_path / "vehiculo.conf"
    escribir_dato.main(["--archivo", str(datos), "motor=1"])

    def escribir(clave, valores):
        for v in valores:
            assert escribir_dato.main(["--archivo", str(datos), f"{clave}={v}"]) == 0

    hilos = [threading.Thread(target=escribir, args=("rpm", range(1000, 1040))),
             threading.Thread(target=escribir, args=("velocidad", range(10, 50)))]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    texto = datos.read_text(encoding="utf-8")
    assert "rpm=1039" in texto and "velocidad=49" in texto and "motor=1" in texto


def test_cp147_p12_falla_si_el_productor_falla():
    """CP-147: P12 no puede aprobar si el simulador termina con error o casi no escribe (DEF-11)."""
    sys.path.insert(0, str(RAIZ / "tools"))
    import ejecucion_prolongada as p12
    assert p12.verificar_productor(42, "simulador: 1 escrituras atomicas en vehiculo.conf", 60)[0] is False
    assert p12.verificar_productor(0, "simulador: 3 escrituras atomicas en vehiculo.conf", 60)[0] is False
    assert p12.verificar_productor(0, "simulador: 590 escrituras atomicas en vehiculo.conf", 60)[0] is True


def test_cp148_aceptacion_rechaza_valores_fuera_de_rango_y_acepta_el_11(tmp_path):
    """CP-148: el CSV de aceptacion rechaza 361 km/h (no lo recorta) y admite pasos del odometro (elemento 11) (DEF-12)."""
    from aceptacion.escenarios import ErrorEscenarios, cargar
    encabezado = "escenario,paso,accion,valor,avanzar_ms,elemento,esperado,descripcion\n"
    malo = tmp_path / "malo.csv"
    malo.write_text(encabezado + "X,1,velocidad,361,100,1,valor=360.0 km/h,recortado\n", encoding="utf-8")
    with pytest.raises(ErrorEscenarios, match="fuera de rango"):
        cargar(malo)
    bueno = tmp_path / "bueno.csv"
    bueno.write_text(encabezado + "X,1,-,,0,11,valor=000000,odometro inicial\n", encoding="utf-8")
    assert cargar(bueno)["X"][0].elemento == 11


@pytest.mark.parametrize("setter", ["set_velocidad", "set_presion_aceite", "set_temp_agua", "set_presion_turbo"])
@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_cp150_el_modelo_rechaza_nan_e_infinito(estado, setter, valor):
    """CP-150: NaN e infinito se rechazan con ValueError; un NaN pasaba la validacion de rango (DEF-13)."""
    with pytest.raises(ValueError):
        getattr(estado, setter)(valor)


@pytest.mark.parametrize("texto", ["５", "٣", "１２０"])
def test_cp151_solo_digitos_ascii(tmp_path, texto):
    """CP-151: digitos no ASCII se rechazan en el archivo de datos y en el del odometro (DEF-14)."""
    from sistema.lector import DatoInvalido, convertir
    with pytest.raises(DatoInvalido):
        convertir("velocidad", texto, RANGOS)
    ruta = tmp_path / "odometro.txt"
    ruta.write_text(texto, encoding="utf-8")
    with pytest.raises(odometro_archivo.OdometroInvalido):
        odometro_archivo.leer_km(ruta)


def test_cp149_aguja_no_tapa_el_odometro(reloj):
    """CP-149: los digitos del odometro quedan por encima de la aguja del velocimetro (DEF-12)."""
    _requiere_display()
    raiz, tablero = _tablero(reloj)
    try:
        orden = tablero.canvas.find_all()
        assert orden.index(tablero.items[11]["valor"]) > max(orden.index(b) for b in tablero.items[1]["bloques"])
    finally:
        tablero.detener()
        raiz.destroy()
