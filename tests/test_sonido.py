"""Pruebas del sonido del motor (Etapa 19): el audio se mide, no solo se genera. Ritmo de las
explosiones, frecuencia de encendido, limitador, turbo, alarma del cinturon, motor de arranque,
hilo de tiempo real, protocolo del socket, bocina remota y panel."""

import gc
import pathlib
import socket
import sys
import threading
import time
import wave

import pytest

from panel import sonido
from panel.fisica import Vehiculo
from panel.sonido import (BLOQUE, FS, EstadoSonoro, HiloSonido, SintetizadorMotor, a_mensaje, de_mensaje, envolvente,
                          estado_de, periodo_dominante_ms, potencia)

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _generar(estado, segundos, arrancado=True, sint=None):
    sint = sint or SintetizadorMotor()
    if arrancado:
        sint.motor_previo = True
    datos = []
    for _ in range(int(segundos * FS / BLOQUE)):
        datos += sint.generar(estado, BLOQUE)
    return datos, sint


class SalidaFalsa:
    def __init__(self):
        self.bloques, self.tiempos, self.cerrada = [], [], False

    def escribir(self, datos):
        self.bloques.append(datos)
        self.tiempos.append(time.monotonic())

    def cerrar(self):
        self.cerrada = True


def _esperar(condicion, segundos=3.0):
    fin = time.monotonic() + segundos
    while time.monotonic() < fin and not condicion():
        time.sleep(0.02)
    return condicion()


def test_cp184_sintetizador_silencio_rango_y_determinismo():
    """CP-184: con el motor apagado hay silencio exacto; con el motor el PCM queda en 16 bits sin saturar; la misma semilla da el mismo audio y n=0 no falla."""
    apagado, _ = _generar(EstadoSonoro(), 0.5, arrancado=False)
    assert max(abs(x) for x in apagado) == 0
    encendido, _ = _generar(EstadoSonoro(motor=True, rpm=7000, acel=1.0, turbo=1.2, contacto=True), 0.5)
    assert 1000 < max(abs(x) for x in encendido) <= 32000
    otra, _ = _generar(EstadoSonoro(motor=True, rpm=7000, acel=1.0, turbo=1.2, contacto=True), 0.5)
    assert otra == encendido
    assert len(SintetizadorMotor().generar(EstadoSonoro(), 0)) == 0


def test_cp185_ritmo_de_explosiones_de_un_v8():
    """CP-185: en ralenti (1000 rpm) la envolvente se repite cada 15 ms, 4 explosiones por vuelta de un V8 de cuatro tiempos; a 6000 rpm domina la frecuencia de encendido (400 Hz) sobre 425 Hz."""
    ralenti, _ = _generar(EstadoSonoro(motor=True, rpm=1000, contacto=True), 1.5)
    assert periodo_dominante_ms(ralenti[FS // 2:]) == pytest.approx(60000 / 1000 / 4, abs=1.0)
    alto, _ = _generar(EstadoSonoro(motor=True, rpm=6000, acel=1.0, contacto=True), 1.0)
    assert potencia(alto[FS // 4:], 400) > 8 * potencia(alto[FS // 4:], 425)


def test_cp186_limitador_turbo_y_descarga():
    """CP-186: a fondo en el limitador (8200 rpm) la combustion se corta a ratos y la envolvente cae casi a cero; a 7000 rpm no hay cortes; el silbido del turbo aparece con la presion y al soltar el acelerador con presion hay descarga."""
    limitador, sint = _generar(EstadoSonoro(motor=True, rpm=8200, acel=1.0, contacto=True), 1.0)
    env = sorted(envolvente(limitador[FS // 4:], FS // 100))
    assert sint.cortes > 100 and env[len(env) // 10] < 0.1 * env[9 * len(env) // 10]
    normal, sint = _generar(EstadoSonoro(motor=True, rpm=7000, acel=1.0, contacto=True), 1.0)
    env = sorted(envolvente(normal[FS // 4:], FS // 100))
    assert sint.cortes == 0 and env[len(env) // 10] > 0.5 * env[9 * len(env) // 10]
    frecuencia = 2200 + 2600 * 1.1 / 1.2
    sin_turbo, _ = _generar(EstadoSonoro(motor=True, rpm=5000, acel=1.0, contacto=True), 1.0)
    con_turbo, _ = _generar(EstadoSonoro(motor=True, rpm=5000, acel=1.0, turbo=1.1, contacto=True), 1.0)
    assert potencia(con_turbo[FS // 4:], frecuencia) > 20 * potencia(sin_turbo[FS // 4:], frecuencia)
    _, sint = _generar(EstadoSonoro(motor=True, rpm=6000, acel=1.0, turbo=1.0, contacto=True), 0.3)
    sint.generar(EstadoSonoro(motor=True, rpm=6000, acel=0.0, turbo=1.0, contacto=True), BLOQUE)
    assert sint.descarga > 0.1


def test_cp187_alarma_del_cinturon_y_motor_de_arranque():
    """CP-187: con contacto y el cinturon sin abrochar la alarma suena entre 4 y 8 s (FMVSS 208 S7.3) y se calla al abrochar; al arrancar, 0.55 s de motor de arranque sin explosiones y despues el motor prende."""
    campana, _ = _generar(EstadoSonoro(contacto=True, cinturon=False), 9.0, arrancado=False)
    ventanas = [potencia(campana[i:i + FS // 4], 1046) for i in range(0, len(campana) - FS // 4, FS // 4)]
    sonando = [i * 0.25 for i, p in enumerate(ventanas) if p > max(ventanas) * 0.01]
    assert 4.0 <= sonando[-1] + 0.25 - sonando[0] <= 8.0
    sint = SintetizadorMotor()
    sint.generar(EstadoSonoro(contacto=True, cinturon=False), BLOQUE)
    sint.generar(EstadoSonoro(contacto=True, cinturon=True), BLOQUE)
    assert sint.campana == 0
    sint = SintetizadorMotor()
    _generar(EstadoSonoro(motor=True, rpm=1000, contacto=True), 0.5, arrancado=False, sint=sint)
    assert sint.explosiones == 0
    _generar(EstadoSonoro(motor=True, rpm=1000, contacto=True), 0.5, arrancado=False, sint=sint)
    assert sint.explosiones > 20


def test_cp188_hilo_de_tiempo_real():
    """CP-188: el hilo de audio produce al ritmo del reloj (bloques de 30 ms, nunca mas de 150 ms adelantado, sin espera activa), toma el estado mas reciente del buzon y se detiene cerrando la salida."""
    salida = SalidaFalsa()
    hilo = HiloSonido(salida)
    hilo.start()
    hilo.publicar(EstadoSonoro(motor=True, rpm=3000, contacto=True))
    hilo.publicar(EstadoSonoro(motor=True, rpm=5000, contacto=True))
    time.sleep(1.0)
    hilo.detener()
    assert not hilo.is_alive() and salida.cerrada and hilo.error is None
    assert hilo.estado.rpm == 5000
    assert 30 <= hilo.bloques <= 42 and hilo.adelanto_maximo <= 0.15
    assert all(len(b) == 2 * BLOQUE for b in salida.bloques)


def test_cp189_protocolo_y_bocina_por_socket(tmp_path):
    """CP-189: los mensajes del socket se validan (rango, tipo, claves, largo, NaN) antes de usarse; la bocina escucha solo en 127.0.0.1, aplica los validos, cuenta los rechazados y graba el audio; el panel remoto no se bloquea sin bocina."""
    estado = EstadoSonoro(motor=True, rpm=4500.5, acel=0.4, turbo=0.8, vel=120.0, contacto=True, cinturon=False)
    assert de_mensaje(a_mensaje(estado)) == estado
    for malo in (b'{"rpm": 99999}', b'{"rpm": NaN}', b'{"rpm": true}', b'{"x": 1}', b"basura", b"[1, 2]",
                 b'{"motor": 2}', b'{"motor": 0.5}', b"{" + b" " * 600 + b"}", '{"rpm": "ñ"}'.encode()):
        with pytest.raises(ValueError):
            de_mensaje(malo)
    sys.path.insert(0, str(RAIZ / "tools"))
    import bocina
    puerto, resultado = [], {}
    listo = threading.Event()
    hilo = threading.Thread(target=lambda: resultado.update(bocina.servir(
        sonido.SalidaWav(tmp_path / "bocina.wav"), puerto=0, duracion_s=4.0,
        listo=lambda p: (puerto.append(p), listo.set()))))
    hilo.start()
    assert listo.wait(5)
    with socket.create_connection(("127.0.0.1", puerto[0]), timeout=2) as crudo:
        crudo.sendall(b'{"rpm": 99999}\nbasura\n' + b"x" * 700 + b"\n" + a_mensaje(EstadoSonoro(motor=True, rpm=2000)))
    remoto = sonido.crear(f"127.0.0.1:{puerto[0]}")
    for _ in range(20):
        remoto.publicar(EstadoSonoro(motor=True, rpm=3000, acel=0.5, contacto=True))
        time.sleep(0.05)
    assert _esperar(lambda: remoto.enviados > 5) and remoto.conectado
    remoto.detener()
    hilo.join(10)
    assert resultado["invalidos"] >= 3 and resultado["mensajes"] >= 6 and resultado["conexiones"] == 2
    assert resultado["ultimo"].rpm == 3000 and resultado["error"] is None
    with wave.open(str(tmp_path / "bocina.wav")) as w:
        assert w.getframerate() == FS and w.getnframes() > FS
    sin_bocina = sonido.crear("127.0.0.1:9")
    inicio = time.monotonic()
    for _ in range(10):
        sin_bocina.publicar(EstadoSonoro())
    assert time.monotonic() - inicio < 0.1 and not sin_bocina.conectado
    sin_bocina.detener()


def test_cp190_panel_con_sonido_y_modos(tmp_path):
    """CP-190: el panel publica el estado del motor al hilo de audio (arranque y rpm), la tecla U silencia, los modos invalidos quedan apagados y sin tarjeta de sonido el panel sigue sin sonido explicando el motivo."""
    tk = pytest.importorskip("tkinter")
    assert sonido.crear("no").activo is False and "invalido" in sonido.crear("bocina").descripcion
    assert "invalido" in sonido.crear("127.0.0.1:0").descripcion
    salida, texto = sonido.abrir_salida_local()
    assert isinstance(texto, str) and texto
    if salida is not None:
        salida.cerrar()
    v = Vehiculo(motor=True, contacto=True, rpm=3000.0, acelerador=0.7, puertas=1, traccion_bloqueada=True)
    assert estado_de(v).acel == 0.0 and estado_de(v, 0.0).vol == 0.0 and estado_de(v).rpm == 3000.0
    gc.collect()
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")
    from panel.ventana import Panel
    reloj = [0.0]
    falsa = SalidaFalsa()
    p = Panel(raiz, ruta_datos=tmp_path / "vehiculo.conf", dir_logs=tmp_path / "logs", reloj=lambda: reloj[0],
              salida_sonido=falsa)
    p.raiz.after_cancel(p._id_after)
    try:
        assert p.sonido.activo and "salida de prueba" in p.texto_sonido()
        p.alternar_motor()
        for _ in range(10):
            reloj[0] += 0.05
            p.paso(0.05)
        assert _esperar(lambda: p.sonido.hilo.estado.motor and p.sonido.hilo.estado.rpm > 0)
        assert p.alternar_silencio() is True
        p.paso(0.05)
        assert _esperar(lambda: p.sonido.hilo.estado.vol == 0.0) and "SILENCIO" in p.texto_sonido()
    finally:
        p.cerrar()
    assert falsa.cerrada and len(falsa.bloques) > 0
