"""Pruebas de la caja negra (Etapa 20): formato binario de tamano fijo, anillo con acceso
directo, persistencia y recuperacion, eventos exportados, hilo escritor y la herramienta."""

import gc
import os
import pathlib
import struct
import sys
import time

import pytest

from logic.estado import EstadoCluster
from logic.reloj import RelojSimulado
from sistema.bitacora import Bitacora
from sistema.caja_negra import (CABECERA, REGISTRO, SIN_DATO, CajaNegra, Registrador, desempaquetar, empaquetar,
                                muestra)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
POSIX = os.name == "posix"


def _log(bitacora, cual):
    for manejador in bitacora._logger.handlers:
        manejador.flush()
    ruta = bitacora.ruta_eventos if cual == "eventos" else bitacora.ruta_errores
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _valores(k=0, **cambios):
    base = {"fecha": 1_700_000_000_000 + k * 100, "velocidad_kmh": 123.4, "rpm": 4500, "presion_aceite_bar": 3.25,
            "temp_agua_c": 92.5, "presion_turbo_bar": 1.07, "combustible_pct": 48.0, "voltaje_v": 14.2,
            "testigos": 0b1000010001, "causa": "ninguna", "motor": True, "encendido": True, "prueba_de_testigos": False}
    base.update(cambios)
    return base


@pytest.fixture
def bitacora(tmp_path):
    b = Bitacora(tmp_path / "logs", max_bytes=65536, respaldos=2)
    yield b
    b.cerrar()


def test_cp191_formato_binario_de_tamano_fijo():
    """CP-191: cada registro mide 32 bytes y la cabecera 64; un registro se codifica y decodifica con la resolucion declarada (decimas de km/h y de C, centesimas de bar, decimas de V); sin dato es 255 y la temperatura lleva signo."""
    assert REGISTRO.size == 32 and CABECERA.size == 64
    datos = empaquetar(_valores(), 7)
    assert len(datos) == 32
    r = desempaquetar(datos)
    assert (r["secuencia"], r["velocidad_kmh"], r["rpm"], r["presion_aceite_bar"]) == (7, 123.4, 4500, 3.25)
    assert (r["temp_agua_c"], r["presion_turbo_bar"], r["combustible_pct"], r["voltaje_v"]) == (92.5, 1.07, 48, 14.2)
    assert r["testigos"] == [6, 10, 16] and r["causa"] == "ninguna" and r["motor"] and not r["prueba_de_testigos"]
    sin = desempaquetar(empaquetar(_valores(combustible_pct=None, voltaje_v=None, causa=None, temp_agua_c=-12.5), 0))
    assert sin["combustible_pct"] is None and sin["voltaje_v"] is None and sin["causa"] is None
    assert sin["temp_agua_c"] == -12.5
    assert struct.unpack_from("<B", empaquetar(_valores(combustible_pct=None), 0), 22)[0] == SIN_DATO
    reloj = RelojSimulado()
    e = EstadoCluster(reloj)
    e.set_motor(True)
    e.set_velocidad(80.0)
    e.set_voltaje(14.2)
    reloj.avanzar(200)
    e.tick()
    m = muestra(e, 1000)
    assert m["velocidad_kmh"] == 80.0 and m["voltaje_v"] == 14.2 and m["motor"] and m["combustible_pct"] is None


def test_cp192_anillo_con_acceso_directo(tmp_path, bitacora):
    """CP-192: el archivo nace de su tamano final (64 + 600 x 32 bytes) y no crece; al pasar de 600 registros el anillo sobrescribe los mas viejos; el registro k esta en el byte 64 + (k mod 600) x 32 y los ultimos se leen en orden."""
    caja = CajaNegra(tmp_path / "caja.bin", capacidad=600, bitacora=bitacora)
    assert (tmp_path / "caja.bin").stat().st_size == 64 + 600 * 32
    for k in range(650):
        caja.escribir(_valores(k, rpm=k))
    caja.sincronizar()
    assert (tmp_path / "caja.bin").stat().st_size == 64 + 600 * 32 and caja.total == 650
    ultimos = caja.ultimos(10)
    assert [r["secuencia"] for r in ultimos] == list(range(640, 650)) and ultimos[-1]["rpm"] == 649
    crudo = (tmp_path / "caja.bin").read_bytes()
    k = 645
    assert desempaquetar(crudo[64 + (k % 600) * 32:64 + (k % 600) * 32 + 32])["secuencia"] == k
    assert desempaquetar(crudo[64 + 49 * 32:64 + 50 * 32])["secuencia"] == 649       # 649 mod 600 = 49
    assert len(caja.ultimos()) == 600 and caja.ultimos()[0]["secuencia"] == 50
    caja.cerrar()
    if POSIX:
        assert (tmp_path / "caja.bin").stat().st_mode & 0o777 == 0o640
    assert "caja_negra_creada" in _log(bitacora, "eventos")


def test_cp193_persistencia_crc_y_recuperacion(tmp_path, bitacora):
    """CP-193: al reabrir sigue donde quedo; un registro alterado se detecta por su CRC y se omite; una cabecera corrupta se aparta (.invalido) y se crea otra con ERROR caja_negra_invalida; otra capacidad reinicia con WARN."""
    ruta = tmp_path / "caja.bin"
    caja = CajaNegra(ruta, capacidad=100, bitacora=bitacora)
    for k in range(30):
        caja.escribir(_valores(k))
    caja.cerrar()
    caja = CajaNegra(ruta, capacidad=100, bitacora=bitacora)
    assert caja.total == 30
    caja.escribir(_valores(30))
    caja.cerrar()
    datos = bytearray(ruta.read_bytes())
    datos[64 + 10 * 32 + 12] ^= 0xFF                          # altera la velocidad del registro 10
    ruta.write_bytes(bytes(datos))
    caja = CajaNegra(ruta, capacidad=100, bitacora=bitacora)
    leidos = caja.ultimos()
    assert caja.total == 31 and len(leidos) == 30 and caja.danados == 1 and 10 not in [r["secuencia"] for r in leidos]
    caja.cerrar()
    datos = bytearray(ruta.read_bytes())
    datos[0:8] = b"BASURA!!"
    ruta.write_bytes(bytes(datos))
    caja = CajaNegra(ruta, capacidad=100, bitacora=bitacora)
    assert caja.total == 0 and (tmp_path / "caja.bin.invalido").exists()
    assert "caja_negra_invalida" in _log(bitacora, "errores")
    caja.cerrar()
    caja = CajaNegra(ruta, capacidad=200, bitacora=bitacora)
    assert ruta.stat().st_size == 64 + 200 * 32 and "caja_negra_reiniciada" in _log(bitacora, "eventos")
    caja.cerrar()


def test_cp194_evento_exporta_los_10_s_previos(tmp_path, bitacora):
    """CP-194: al encenderse un testigo critico la caja negra exporta a CSV los 10 s anteriores con la causa, registra INFO caja_negra_evento y conserva solo los eventos mas recientes."""
    reloj = RelojSimulado()
    estado = EstadoCluster(reloj)
    caja = CajaNegra(tmp_path / "caja.bin", capacidad=600, bitacora=bitacora)
    reg = Registrador(caja, tmp_path / "eventos", eventos_max=2, bitacora=bitacora, reloj=lambda: reloj.ahora_ms() / 1000)
    estado.set_motor(True)
    estado.set_velocidad(60.0)
    estado.set_presion_aceite(3.0)
    for paso in range(300):                                   # 15 s a 20 ciclos por segundo
        if paso in (200, 240, 280):
            estado.set_falla_frenos(paso != 240)
        reloj.avanzar(50)
        estado.tick()
        reg.muestrear(estado)
        time.sleep(0.001)                                     # como el tablero: deja correr al escritor
    estado.set_contacto(True)
    estado.set_falla_motor("sobretemperatura")
    reloj.avanzar(50)
    estado.tick()
    reg.muestrear(estado)
    reg.cerrar()
    archivos = sorted((tmp_path / "eventos").glob("evento_*.csv"))
    assert len(archivos) == 2 and len(reg.eventos) == 3              # se conservan los 2 mas recientes
    assert archivos[-1].name.endswith("_proteccion_motor.csv")
    filas = archivos[0].read_text(encoding="utf-8").splitlines()
    assert filas[0].startswith("fecha,secuencia,velocidad_kmh") and 95 <= len(filas) - 1 <= 101
    assert _log(bitacora, "eventos").count("caja_negra_evento") == 3
    if POSIX:
        assert archivos[0].stat().st_mode & 0o777 == 0o640


def test_cp195_hilo_escritor_no_bloquea_y_aplicacion_real(tmp_path):
    """CP-195: si el disco se atrasa la interfaz no espera (la muestra se descarta y se cuenta); al cerrar se vacia la cola; con la aplicacion real, falla_frenos=1 deja un CSV de evento y el binario conserva su tamano fijo."""
    class CajaLenta:
        def __init__(self):
            self.escritos = 0

        def escribir(self, valores):
            time.sleep(0.02)
            self.escritos += 1

        def sincronizar(self):
            pass

        def ultimos(self, n):
            return []

        def cerrar(self):
            self.cerrada = True

    reloj = [0.0]
    lenta = CajaLenta()
    reg = Registrador(lenta, tmp_path / "ev", reloj=lambda: reloj[0])
    estado = EstadoCluster(RelojSimulado())
    inicio = time.monotonic()
    for _ in range(300):
        reloj[0] += 0.1
        reg.muestrear(estado)
    assert time.monotonic() - inicio < 0.5 and reg.descartados > 0
    reg.cerrar(espera_s=5)
    assert lenta.cerrada and lenta.escritos + reg.descartados == 300

    tk = pytest.importorskip("tkinter")
    gc.collect()
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    import main as principal
    from sistema.lector import VALORES_INICIALES, escribir_atomico
    (tmp_path / "config").mkdir()
    (tmp_path / "datos").mkdir()
    ini = tmp_path / "config" / "cluster.ini"
    ini.write_text("[intervalos]\nlectura_ms = 20\n[caja_negra]\nsegundos = 10\n", encoding="utf-8")
    datos = tmp_path / "datos" / "vehiculo.conf"
    escribir_atomico(datos, dict(VALORES_INICIALES, motor=True, velocidad=50.0))
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, ruta_config=ini, proyecto=tmp_path)
    try:
        fin = time.monotonic() + 1.0
        while time.monotonic() < fin:
            raiz.update()
            time.sleep(0.01)
        escribir_atomico(datos, dict(VALORES_INICIALES, motor=True, velocidad=50.0, falla_frenos=True))
        fin = time.monotonic() + 5.0
        while time.monotonic() < fin and not list((tmp_path / "logs" / "caja_negra").glob("evento_*testigo_10.csv")):
            raiz.update()
            time.sleep(0.01)
    finally:
        app.cerrar()
    assert list((tmp_path / "logs" / "caja_negra").glob("evento_*testigo_10.csv"))
    assert (tmp_path / "datos" / "caja_negra.bin").stat().st_size == 64 + 100 * 32
    caja = CajaNegra(tmp_path / "datos" / "caja_negra.bin", capacidad=100)
    assert caja.total >= 5 and caja.ultimos(1)[0]["velocidad_kmh"] == 50.0
    caja.cerrar()


def test_cp196_herramienta_de_la_caja_negra(tmp_path, capsys):
    """CP-196: tools/caja_negra.py lee sin modificar (resumen, CSV y un registro byte por byte con sus campos) y --demo deja la evidencia: 70 s simulados, el anillo lleno, ningun registro danado y el evento del sobrecalentamiento."""
    sys.path.insert(0, str(RAIZ / "tools"))
    import caja_negra as herramienta
    assert herramienta.demo(tmp_path / "demo") == 0
    reporte = (tmp_path / "demo" / "reporte.txt").read_text(encoding="utf-8")
    assert "19264 bytes" in reporte and "0 danados" in reporte and "proteccion_motor" in reporte
    ruta = tmp_path / "demo" / "caja_negra.bin"
    antes = ruta.read_bytes()
    assert herramienta.main(["--archivo", str(ruta), "--hex", "1"]) == 0
    salida = capsys.readouterr().out
    assert "hex:" in salida and "crc (H, CRC-16)" in salida and "decodificado" in salida
    assert herramienta.main(["--archivo", str(ruta), "--ultimos", "50", "--csv", str(tmp_path / "s.csv")]) == 0
    assert len((tmp_path / "s.csv").read_text(encoding="utf-8").splitlines()) == 51
    assert ruta.read_bytes() == antes                          # solo lectura
    assert herramienta.main(["--archivo", str(tmp_path / "no_existe.bin")]) == 1
