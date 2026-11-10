"""Pruebas obligatorias P01-P12 de la guia y de la capa de sistema: datos
externos, validacion, bitacoras, configuracion, permisos, concurrencia y
ejecucion prolongada. Cada caso usa carpetas temporales propias."""

import gc
import os
import queue
import re
import sys
import threading

import pytest

from logic.estado import EstadoCluster
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import CLAVES, VALORES_INICIALES, HiloLector, Lector, convertir, escribir_atomico, publicar
from sistema.monitor import MonitorEventos

tk = pytest.importorskip("tkinter")

RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)
FORMATO_LINEA = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d (INFO |WARN |ERROR) \S+ \S+")
POSIX_SIN_ROOT = os.name == "posix" and os.geteuid() != 0


@pytest.fixture(autouse=True)
def _recolectar_en_hilo_principal():
    """Libera aqui, en el hilo principal, los objetos de Tk que dejaron pruebas anteriores.
    Si el recolector los liberara dentro del hilo lector, Tk avisaria que no esta en su hilo."""
    gc.collect()
    yield


@pytest.fixture
def entorno(tmp_path):
    datos = tmp_path / "datos" / "vehiculo.conf"
    datos.parent.mkdir()
    bitacora = Bitacora(tmp_path / "logs", max_bytes=65536, respaldos=2)
    lector = Lector(datos, RANGOS, bitacora)
    yield datos, bitacora, lector
    bitacora.cerrar()


def _texto(**valores):
    base = {clave: None for clave in CLAVES}
    base.update({"motor": "1", "velocidad": "0", "rpm": "0", "presion_aceite": "5", "temp_agua": "40",
                 "presion_turbo": "0", "direccional": "off", "luces_altas": "0", "emergencia": "0",
                 "falla_frenos": "0"})
    base.update(valores)
    return "".join(f"{clave}={valor}\n" for clave, valor in base.items() if valor is not None)


def _log(bitacora, cual):
    for manejador in bitacora._logger.handlers:
        manejador.flush()
    ruta = bitacora.ruta_eventos if cual == "eventos" else bitacora.ruta_errores
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _aplicar(datos, estado):
    for clave, valor in datos.items():
        getattr(estado, CLAVES[clave][0])(valor)


def test_cp91_p01_valor_normal_actualiza_y_registra_info(entorno, reloj):
    """CP-91: P01 un valor valido del archivo actualiza el indicador y deja un evento INFO (R01)."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(velocidad="72"), encoding="utf-8")
    snapshot = lector.leer()
    estado = EstadoCluster(reloj)
    _aplicar(snapshot, estado)
    reloj.avanzar(100)
    estado.tick()
    assert estado.velocidad == 72.0
    assert "INFO  lector_datos valor_actualizado velocidad=72 resultado=aceptado" in _log(bitacora, "eventos")
    assert _log(bitacora, "errores") == ""


def test_cp92_p02_limites_inferiores_aceptados(entorno):
    """CP-92: P02 los valores minimos permitidos se aceptan sin error (R01, R02, R03, R04, R05)."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(velocidad="0", rpm="0", presion_aceite="0", temp_agua="40", presion_turbo="0"), encoding="utf-8")
    snapshot = lector.leer()
    assert (snapshot["velocidad"], snapshot["rpm"], snapshot["presion_aceite"], snapshot["temp_agua"],
            snapshot["presion_turbo"]) == (0.0, 0, 0.0, 40.0, 0.0)
    assert _log(bitacora, "errores") == ""


def test_cp93_p03_limites_superiores_aceptados(entorno):
    """CP-93: P03 los valores maximos permitidos se aceptan sin error (R01, R02, R03, R04, R05)."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(velocidad="360", rpm="9000", presion_aceite="10", temp_agua="130", presion_turbo="2"),
                     encoding="utf-8")
    snapshot = lector.leer()
    assert (snapshot["velocidad"], snapshot["rpm"], snapshot["presion_aceite"], snapshot["temp_agua"],
            snapshot["presion_turbo"]) == (360.0, 9000, 10.0, 130.0, 2.0)
    assert _log(bitacora, "errores") == ""


@pytest.mark.parametrize("clave, texto", [("velocidad", "361"), ("velocidad", "-1"), ("rpm", "9001"),
                                          ("temp_agua", "39.9"), ("presion_turbo", "2.01")])
def test_cp94_p04_fuera_de_rango_se_rechaza(entorno, clave, texto):
    """CP-94: P04 un valor fuera de rango se rechaza, se conserva el ultimo valido y se registra ERROR (R01, R03, R04, R05)."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(), encoding="utf-8")
    previo = lector.leer()[clave]
    datos.write_text(_texto(**{clave: texto}) + "# cambio\n", encoding="utf-8")
    snapshot = lector.leer()
    assert snapshot[clave] == previo
    assert f"ERROR lector_datos fuera_de_rango {clave}={texto}" in _log(bitacora, "errores")
    assert "fuera_de_rango" not in _log(bitacora, "eventos")


@pytest.mark.parametrize("clave, texto", [("temp_agua", "abc"), ("rpm", "4500.5"), ("motor", "si"),
                                          ("direccional", "arriba"), ("velocidad", "nan")])
def test_cp95_p05_formato_incorrecto_conserva_ultimo_valido(entorno, clave, texto):
    """CP-95: P05 texto donde se espera otro tipo: continua con el ultimo valor valido y registra ERROR."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(), encoding="utf-8")
    previo = lector.leer()[clave]
    datos.write_text(_texto(**{clave: texto}) + "# cambio\n", encoding="utf-8")
    assert lector.leer()[clave] == previo
    assert f'dato_invalido {clave} entrada="{texto}"' in _log(bitacora, "errores")


def test_cp96_p06_dato_ausente_estado_definido(entorno):
    """CP-96: P06 archivo vacio o clave faltante: se conserva el estado definido y se registra el error (R01)."""
    datos, bitacora, lector = entorno
    datos.write_text("", encoding="utf-8")
    snapshot = lector.leer()
    assert snapshot == VALORES_INICIALES
    assert _log(bitacora, "errores").count("clave_faltante") == len(CLAVES)

    datos.write_text(_texto(velocidad="50"), encoding="utf-8")
    assert lector.leer()["velocidad"] == 50.0
    datos.write_text(_texto(velocidad=None) + "# sin velocidad\n", encoding="utf-8")
    assert lector.leer()["velocidad"] == 50.0
    assert "clave_faltante velocidad se conserva 50.0" in _log(bitacora, "errores")


def test_cp97_p07_archivo_inexistente_no_termina(entorno):
    """CP-97: P07 si el archivo se retira el sistema no termina; al volver se recupera y lo registra."""
    datos, bitacora, lector = entorno
    assert lector.leer() is None
    assert lector.leer() is None
    errores = _log(bitacora, "errores")
    assert errores.count("archivo_inexistente") == 1
    datos.write_text(_texto(rpm="3000"), encoding="utf-8")
    assert lector.leer()["rpm"] == 3000
    assert "archivo_recuperado ruta=vehiculo.conf" in _log(bitacora, "eventos")


def test_cp98_p08_actualizacion_concurrente_sin_lecturas_parciales(entorno):
    """CP-98: P08 un escritor y el hilo lector trabajan a la vez: nunca se lee un valor parcial ni corrupto."""
    datos, bitacora, lector = entorno
    escribir_atomico(datos, dict(VALORES_INICIALES, velocidad=0.0, rpm=0))
    buzon = queue.Queue(maxsize=1)
    hilo = HiloLector(lector, 0.001, buzon)
    vistos = []
    terminado = threading.Event()

    def escritor():
        for k in range(1, 301):
            escribir_atomico(datos, dict(VALORES_INICIALES, velocidad=float(k), rpm=k * 10))
        terminado.set()

    hilo.start()
    productor = threading.Thread(target=escritor)
    productor.start()
    while not terminado.is_set() or not buzon.empty():
        try:
            vistos.append(buzon.get(timeout=0.05))
        except queue.Empty:
            pass
    productor.join()
    hilo.detener()
    assert vistos, "el consumidor no recibio ningun dato"
    assert all(d["rpm"] == int(d["velocidad"]) * 10 for d in vistos)
    assert _log(bitacora, "errores") == ""
    assert not list(datos.parent.glob(".vehiculo.*.tmp"))


def test_cp99_p09_advertencia_testigo_y_evento_prioritario(entorno, estado_encendido, reloj):
    """CP-99: P09 al superar un umbral critico se enciende el testigo y se registra un WARN prioritario (R02, R08)."""
    _, bitacora, _ = entorno
    monitor = MonitorEventos(bitacora)
    estado_encendido.set_presion_aceite(0.5)
    estado_encendido.set_falla_frenos(True)
    for _ in range(12):
        reloj.avanzar(100)
        estado_encendido.tick()
        monitor.revisar(estado_encendido)
    assert estado_encendido.testigo_baja_presion_aceite is True
    eventos = _log(bitacora, "eventos")
    assert "WARN  monitor_seguridad testigo_9_encendido" in eventos
    assert eventos.count("testigo_10_encendido") == 1


def test_cp100_p10_recuperacion_sin_reinicio(entorno):
    """CP-100: P10 tras una entrada invalida, al corregirla se retoma la operacion sin reiniciar."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(rpm="abc"), encoding="utf-8")
    assert lector.leer()["rpm"] == 0
    datos.write_text(_texto(rpm="2500") + "# corregido\n", encoding="utf-8")
    assert lector.leer()["rpm"] == 2500
    assert "valor_actualizado rpm=2500" in _log(bitacora, "eventos")


@pytest.mark.skipif(not POSIX_SIN_ROOT, reason="requiere permisos POSIX y un usuario que no sea root")
def test_cp101_p11_lectura_no_autorizada(entorno):
    """CP-101: P11 un archivo sin permiso de lectura se rechaza y se registra; al restaurar el permiso se recupera."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(velocidad="10"), encoding="utf-8")
    os.chmod(datos, 0o000)
    try:
        assert lector.leer() is None
        assert "permiso_denegado ruta=vehiculo.conf" in _log(bitacora, "errores")
    finally:
        os.chmod(datos, 0o640)
    assert lector.leer()["velocidad"] == 10.0


@pytest.mark.skipif(os.name != "posix", reason="los bits de permiso son de POSIX")
def test_cp102_p11_archivo_escribible_por_cualquiera_se_rechaza(entorno):
    """CP-102: P11 un archivo de datos que cualquiera puede escribir no se usa y se registra el error."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto(velocidad="99"), encoding="utf-8")
    os.chmod(datos, 0o666)
    assert lector.leer() is None
    assert "permisos_inseguros ruta=vehiculo.conf modo=0o666" in _log(bitacora, "errores")
    os.chmod(datos, 0o640)
    assert lector.leer()["velocidad"] == 99.0


@pytest.mark.skipif(os.name != "posix", reason="los bits de permiso son de POSIX")
def test_cp103_p11_bitacoras_con_minimo_privilegio(entorno):
    """CP-103: P11 las bitacoras se crean solo para el dueno y su grupo (640) y la carpeta con 750."""
    _, bitacora, _ = entorno
    bitacora.info("prueba", "evento")
    bitacora.error("prueba", "error")
    assert oct(bitacora.ruta_eventos.stat().st_mode & 0o777) == "0o640"
    assert oct(bitacora.ruta_errores.stat().st_mode & 0o777) == "0o640"
    assert oct(bitacora.dir_logs.stat().st_mode & 0o777) == "0o750"


def test_cp104_p12_ejecucion_prolongada_acotada(tmp_path, reloj):
    """CP-104: P12 3000 ciclos con datos cambiantes: las bitacoras rotan y no crecen sin limite."""
    datos = tmp_path / "vehiculo.conf"
    bitacora = Bitacora(tmp_path / "logs", max_bytes=4096, respaldos=2)
    lector = Lector(datos, RANGOS, bitacora)
    estado = EstadoCluster(reloj)
    monitor = MonitorEventos(bitacora)
    try:
        for k in range(3000):
            datos.write_text(_texto(velocidad=str(k % 361), rpm=str((k * 37) % 9001)), encoding="utf-8")
            snapshot = lector.leer()
            if snapshot:
                _aplicar(snapshot, estado)
            reloj.avanzar(50)
            estado.tick()
            monitor.revisar(estado)
    finally:
        bitacora.cerrar()
    archivos = list((tmp_path / "logs").glob("eventos.log*"))
    assert len(archivos) == 3
    assert sum(a.stat().st_size for a in archivos) <= 3 * 4096 + 512
    assert bitacora.contadores["INFO"] > 1000


def test_cp105_bitacoras_separadas_y_con_formato(entorno):
    """CP-105: eventos.log lleva INFO y WARN, errores.log solo ERROR; cada linea tiene fecha, nivel, componente y evento."""
    _, bitacora, _ = entorno
    bitacora.info("lector_velocidad", "valor_actualizado", "valor=72")
    bitacora.warn("monitor_seguridad", "testigo_9_encendido")
    bitacora.error("lector_temperatura", "dato_invalido", 'entrada="abc"')
    eventos, errores = _log(bitacora, "eventos").splitlines(), _log(bitacora, "errores").splitlines()
    assert len(eventos) == 2 and len(errores) == 1
    assert all(FORMATO_LINEA.match(linea) for linea in eventos + errores)
    assert "ERROR" not in "".join(eventos) and errores[0].split()[1] == "ERROR"


def test_cp106_configuracion_externa_y_valores_por_defecto(tmp_path):
    """CP-106: la configuracion se lee del archivo; si falta o es invalida se usan valores por defecto y se informa."""
    (tmp_path / "config").mkdir()
    ini = tmp_path / "config" / "cluster.ini"
    ini.write_text("[rutas]\ndatos = otra/datos.conf\nlogs = /etc\n[intervalos]\nlectura_ms = 250\nrefresco_ms = 0\n"
                   "[rangos]\nvelocidad = 0, 200\nrpm = 0, 99999\n", encoding="utf-8")
    cfg = configuracion.cargar(ini, raiz=tmp_path)
    assert cfg.archivo_datos == tmp_path / "otra" / "datos.conf"
    assert cfg.dir_logs == tmp_path / "logs"
    assert (cfg.lectura_ms, cfg.refresco_ms) == (250, 50)
    assert cfg.rangos["velocidad"] == (0.0, 200.0) and cfg.rangos["rpm"] == (0.0, 9000.0)
    eventos = [evento for evento, _ in cfg.errores]
    assert eventos == ["ruta_rechazada", "valor_invalido", "rango_invalido"]

    sin_archivo = configuracion.cargar(tmp_path / "no_existe.ini", raiz=tmp_path)
    assert sin_archivo.lectura_ms == 100 and sin_archivo.errores[0][0] == "archivo_inexistente"
    assert cfg.relativa(cfg.archivo_datos) == "otra/datos.conf"
    assert cfg.relativa(tmp_path.parent / "fuera.conf") == "fuera.conf"


def test_cp107_entrada_maliciosa_no_se_usa(entorno):
    """CP-107: lineas sin formato, claves desconocidas, duplicadas, valores enormes y archivos grandes se rechazan."""
    datos, bitacora, lector = entorno
    datos.write_text(_texto() + "basura sin igual\nrm -rf=1\nvelocidad=10\nvelocidad=20\nrpm=" + "9" * 40 + "\n",
                     encoding="utf-8")
    snapshot = lector.leer()
    errores = _log(bitacora, "errores")
    assert "linea_invalida" in errores and "clave_desconocida" in errores and "clave_duplicada" in errores
    assert "entrada demasiado larga" in errores
    assert snapshot["velocidad"] == 20.0 and snapshot["rpm"] == 0
    datos.write_text("x" * 5000, encoding="utf-8")
    assert lector.leer() is None
    assert "archivo_demasiado_grande" in _log(bitacora, "errores")


def test_cp108_buzon_conserva_solo_el_dato_mas_reciente():
    """CP-108: el buzon productor-consumidor nunca acumula: guarda solo el snapshot mas reciente."""
    buzon = queue.Queue(maxsize=1)
    for k in range(100):
        publicar(buzon, {"velocidad": float(k)})
    assert buzon.qsize() == 1 and buzon.get_nowait() == {"velocidad": 99.0}


def test_cp109_conversion_y_formato_son_inversos():
    """CP-109: cada tipo se codifica en el archivo y se decodifica sin perdida (booleano, entero, decimal, enumeracion)."""
    from sistema.lector import formatear
    ejemplos = {"motor": True, "rpm": 7800, "velocidad": 120.5, "direccional": "IZQ", "falla_frenos": False}
    for clave, valor in ejemplos.items():
        assert convertir(clave, formatear(clave, valor), RANGOS) == valor


def test_cp110_errores_repetidos_no_inundan_la_bitacora(entorno):
    """CP-110: el mismo dato invalido o el mismo archivo ausente se registran una sola vez mientras duran."""
    datos, bitacora, lector = entorno
    for _ in range(5):
        lector.leer()
    datos.write_text(_texto(temp_agua="abc"), encoding="utf-8")
    lector.leer()
    for k in range(5):
        datos.write_text(_texto(temp_agua="abc") + f"# {k}\n", encoding="utf-8")
        lector.leer()
    errores = _log(bitacora, "errores")
    assert errores.count("archivo_inexistente") == 1 and errores.count('entrada="abc"') == 1


def test_cp111_hilo_lector_registra_fallos_inesperados_y_sigue(entorno):
    """CP-111: si la lectura falla de forma inesperada, el hilo lo registra y sigue funcionando."""
    _, bitacora, lector = entorno
    llamadas = []

    def lectura_que_falla():
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("fallo simulado")
        return {"velocidad": 5.0}

    lector.leer = lectura_que_falla
    buzon = queue.Queue(maxsize=1)
    hilo = HiloLector(lector, 0.001, buzon)
    hilo.start()
    assert buzon.get(timeout=2) == {"velocidad": 5.0}
    hilo.detener()
    assert "error_inesperado RuntimeError: fallo simulado" in _log(bitacora, "errores")


def test_cp112_escritura_atomica_limpia_temporales_si_falla(tmp_path, monkeypatch):
    """CP-112: si el renombrado falla, el archivo original queda intacto y no quedan temporales."""
    datos = tmp_path / "vehiculo.conf"
    escribir_atomico(datos, VALORES_INICIALES)
    original = datos.read_text(encoding="utf-8")

    def reemplazo_fallido(origen, destino):
        raise PermissionError("bloqueado")

    monkeypatch.setattr(os, "replace", reemplazo_fallido)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    with pytest.raises(PermissionError):
        escribir_atomico(datos, dict(VALORES_INICIALES, velocidad=1.0))
    assert datos.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob(".vehiculo.*.tmp"))


def test_cp113_herramienta_escribir_dato(tmp_path, capsys):
    """CP-113: tools/escribir_dato.py valida y escribe de forma atomica; con --sin-validar permite provocar errores."""
    sys.path.insert(0, str(configuracion.RAIZ / "tools"))
    import escribir_dato
    datos = tmp_path / "vehiculo.conf"
    assert escribir_dato.main(["--archivo", str(datos), "motor=1", "velocidad=120"]) == 0
    texto = datos.read_text(encoding="utf-8")
    assert "motor=1" in texto and "velocidad=120" in texto and "rpm=0" in texto
    assert escribir_dato.main(["--archivo", str(datos), "velocidad=999"]) == 2
    assert escribir_dato.main(["--archivo", str(datos), "turbo=1"]) == 2
    assert escribir_dato.main(["--archivo", str(datos), "--sin-validar", "temp_agua=abc"]) == 0
    assert "temp_agua=abc" in datos.read_text(encoding="utf-8")
    assert "velocidad=120" in datos.read_text(encoding="utf-8")


def test_cp114_simulador_produce_datos_validos(tmp_path):
    """CP-114: el proceso simulador escribe valores siempre validos para todo el recorrido."""
    sys.path.insert(0, str(configuracion.RAIZ / "tools"))
    import simulador
    for t in range(0, 22000, 50):
        valores = simulador.valores_en(t)
        for clave in CLAVES:
            from sistema.lector import formatear
            assert convertir(clave, formatear(clave, valores[clave]), RANGOS) == valores[clave]
    assert simulador.main(["--archivo", str(tmp_path / "v.conf"), "--duracion-s", "0.2", "--periodo-ms", "20"]) == 0
    assert (tmp_path / "v.conf").exists()


def _requiere_display():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")


def _esperar(raiz, condicion, segundos=5.0):
    import time
    fin = time.monotonic() + segundos
    while time.monotonic() < fin and not condicion():
        raiz.update()
        time.sleep(0.01)
    return condicion()


def test_cp115_aplicacion_lee_el_archivo_y_actualiza_sin_reiniciar(tmp_path):
    """CP-115: con la aplicacion abierta, cambiar el archivo de datos actualiza el tablero sin reiniciar (R01, R03, R08)."""
    _requiere_display()
    import main as principal
    (tmp_path / "config").mkdir()
    (tmp_path / "datos").mkdir()
    ini = tmp_path / "config" / "cluster.ini"
    ini.write_text("[intervalos]\nlectura_ms = 20\n", encoding="utf-8")
    datos = tmp_path / "datos" / "vehiculo.conf"
    escribir_atomico(datos, dict(VALORES_INICIALES, motor=True, rpm=8000, falla_frenos=True))
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, ruta_config=ini, proyecto=tmp_path)
    try:
        assert _esperar(raiz, lambda: app.estado.rpm == 8000)
        assert app.tablero.canvas.itemcget(app.tablero.items[3]["valor"], "text") == "8000 RPM"
        assert all(str(c.cget("state")) == "disabled" for c in app.tablero._controles)
        escribir_atomico(datos, dict(VALORES_INICIALES, motor=True, rpm=1500))
        assert _esperar(raiz, lambda: app.estado.rpm == 1500)
    finally:
        app.cerrar()
    eventos = (tmp_path / "logs" / "eventos.log").read_text(encoding="utf-8")
    assert "sistema inicio modo=archivo=datos/vehiculo.conf" in eventos
    assert "testigo_10_encendido" in eventos and "tacometro_rojo" in eventos and "sistema fin" in eventos


def test_cp116_modo_manual_y_errores_de_configuracion_e_interfaz(tmp_path):
    """CP-116: sin archivo de configuracion se usan valores por defecto y se registra; un error de la interfaz se registra y no termina la aplicacion."""
    _requiere_display()
    import main as principal
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, manual=True, ruta_config=tmp_path / "no_existe.ini", proyecto=tmp_path)
    try:
        assert app.hilo is None
        assert all(str(c.cget("state")) == "normal" for c in app.tablero._controles)
        app._error_interfaz(ValueError, ValueError("simulado"), None)
        assert app.tablero.ajustar("set_rpm", 3000) is True
    finally:
        app.cerrar()
    errores = (tmp_path / "logs" / "errores.log").read_text(encoding="utf-8")
    assert "configuracion archivo_inexistente" in errores
    assert "interfaz error_de_ejecucion ValueError: simulado" in errores


def test_cp117_monitor_registra_cada_transicion_una_vez(entorno, estado_encendido, reloj):
    """CP-117: el monitor registra encendido y apagado de cada advertencia una sola vez (R01, R02, R03, R04, R05, R07, R08)."""
    _, bitacora, _ = entorno
    monitor = MonitorEventos(bitacora)

    def correr(ms):
        for _ in range(ms // 100):
            reloj.avanzar(100)
            estado_encendido.tick()
            monitor.revisar(estado_encendido)

    for setter, valor in (("set_rpm", 8500), ("set_temp_agua", 120), ("set_presion_turbo", 1.8),
                          ("set_presion_aceite", 0.3), ("set_emergencia", True), ("set_falla_frenos", True)):
        getattr(estado_encendido, setter)(valor)
    correr(1500)
    for setter, valor in (("set_rpm", 2000), ("set_temp_agua", 90), ("set_presion_turbo", 0.5),
                          ("set_presion_aceite", 5), ("set_emergencia", False), ("set_falla_frenos", False)):
        getattr(estado_encendido, setter)(valor)
    correr(1500)
    estado_encendido.set_motor(False)
    correr(200)
    eventos = _log(bitacora, "eventos")
    for evento in ("tacometro_rojo", "tacometro_normal", "temperatura_rojo", "temperatura_normal", "turbo_ambar",
                   "turbo_normal", "testigo_9_encendido", "testigo_9_apagado", "emergencia_activada",
                   "emergencia_desactivada", "testigo_10_encendido", "testigo_10_apagado", "motor_encendido",
                   "motor_apagado"):
        assert eventos.count(f" {evento} ") == 1, evento


def test_cp118_archivos_corruptos_no_detienen_el_sistema(entorno, tmp_path):
    """CP-118: un archivo de datos con codificacion invalida y una configuracion sin secciones se rechazan sin detenerse."""
    datos, bitacora, lector = entorno
    datos.write_bytes(b"velocidad=\xff\xfe\n")
    assert lector.leer() is None
    assert "dato_invalido ruta=vehiculo.conf codificacion no valida" in _log(bitacora, "errores")
    ini = tmp_path / "roto.ini"
    ini.write_text("lectura_ms = 5\n", encoding="utf-8")
    cfg = configuracion.cargar(ini, raiz=tmp_path)
    assert cfg.lectura_ms == 100 and cfg.errores[0][0] == "configuracion_invalida"


def test_cp119_simulador_se_detiene_limpio_con_ctrl_c(tmp_path, monkeypatch):
    """CP-119: el proceso simulador termina limpio al recibir Ctrl+C."""
    sys.path.insert(0, str(configuracion.RAIZ / "tools"))
    import simulador

    def interrumpir(_ruta, _valores):
        raise KeyboardInterrupt

    monkeypatch.setattr(simulador, "escribir_atomico", interrumpir)
    assert simulador.main(["--archivo", str(tmp_path / "v.conf")]) == 0
    assert simulador.interpolar([(0, 0), (10, 5)], 99) == 5