"""Sonido del motor sintetizado por codigo (Etapa 19).

No usa grabaciones: cada muestra se calcula. Modelo de pulsos de combustion de un V8 de
cuatro tiempos con ciguenal plano, como el del F40: 8 cilindros en 2 vueltas = 4 explosiones
por vuelta, asi que la frecuencia de encendido es rpm / 60 * 4 (67 Hz en ralenti, 547 Hz en el
limitador). Cada explosion excita tres resonadores (cuerpo del escape, aspereza y tono agudo) y
una rafaga de ruido; cada cilindro suena un poco distinto y en ralenti el ritmo varia un poco,
como un motor real. Encima van el ruido de admision con la carga, el viento con la velocidad,
el silbido del turbo con la presion, la descarga del turbo al soltar el acelerador, el corte del
limitador (sin combustion a ratos), petardeos al soltar en altas, el motor de arranque y la
alarma del cinturon (4 a 8 s al dar contacto sin abrochar, como pide FMVSS 208 S7.3).
Etapa 20: un banco sin encendido (falla de una unidad Weber-Marelli) suena cojo porque falta una
de cada dos explosiones; el motor de arranque gira lento con la bateria descargada; el relevador
de las direccionales hace tic-tac cada 500 ms; las llantas chirrian al frenar a fondo o al
arrancar patinando; y se oye el ventilador del radiador.
El sonido es aproximado: no es una grabacion del F40 ni se calibro contra uno.

Tiempo real blando: un hilo genera bloques de 30 ms y los entrega a la salida de audio, que
bloquea cuando su cola esta llena; ademas el hilo nunca se adelanta mas de 120 ms al reloj, asi
la latencia queda acotada. El estado del motor llega por un buzon de tamano 1 (siempre el mas
reciente), el mismo patron productor-consumidor del lector del tablero.

Salidas: Windows (waveOut de winmm con ctypes), Linux (proceso hijo aplay con una tuberia) y
archivo WAV. Como el panel corre en la maquina virtual y las bocinas estan en Windows, el panel
puede enviar el estado por un socket (tunel SSH) a tools/bocina.py, que sintetiza en Windows."""

import array
import json
import math
import os
import pathlib
import queue
import random
import shutil
import socket
import subprocess
import sys
import threading
import time
import wave
from dataclasses import asdict, dataclass

from sistema.lector import publicar

FS = 22050                    # muestras por segundo (alcanza para el silbido del turbo, hasta 5 kHz)
BLOQUE = 660                  # muestras por bloque: 30 ms
ADELANTO_MAX_S = 0.12         # el generador nunca va mas de 120 ms adelante del reloj
PUERTO = 5055
EXPLOSIONES_POR_VUELTA = 4    # V8 de cuatro tiempos
DESBALANCE = (0.07, -0.05, 0.05, -0.08, 0.06, -0.04, 0.09, -0.07)   # cada cilindro suena un poco distinto
ARRANQUE_S = 0.55             # motor de arranque antes de que prenda
CAMPANA_S = 6.0               # alarma del cinturon: FMVSS 208 S7.3 pide de 4 a 8 s
LIMITADOR_RPM = 8100
CORTE_S = 0.045               # el limitador corta la inyeccion en ventanas de 45 ms
LARGO_MAXIMO = 512            # bytes por mensaje en el socket


@dataclass
class EstadoSonoro:
    motor: bool = False
    rpm: float = 0.0
    acel: float = 0.0          # acelerador efectivo, 0 a 1
    turbo: float = 0.0         # bar
    vel: float = 0.0           # km/h
    contacto: bool = False
    cinturon: bool = True
    vol: float = 0.8
    # Etapa 20
    crank: float = 0.0         # motor de arranque girando sin prender (0 a 1: velocidad de giro)
    banco: bool = False        # un banco sin encendido: suena cojo
    intermitente: bool = False  # direccional o emergencia: relevador tic-tac
    chirrido: float = 0.0      # llantas, 0 a 1
    ventilador: bool = False


LIMITES = {"rpm": (0.0, 9000.0), "acel": (0.0, 1.0), "turbo": (0.0, 2.0), "vel": (0.0, 360.0), "vol": (0.0, 1.0),
           "crank": (0.0, 1.0), "chirrido": (0.0, 1.0)}
BOOLEANOS = ("motor", "contacto", "cinturon", "banco", "intermitente", "ventilador")


def chirrido_de(vehiculo):
    """Intensidad del chirrido de llantas: bloqueadas (sin ABS), patinando (sin control de traccion),
    frenada a fondo o arranque fuerte en primera."""
    if getattr(vehiculo, "bloqueado", False):
        return 1.0
    if getattr(vehiculo, "patinando", False):
        return 0.8
    if vehiculo.freno > 0.8 and vehiculo.velocidad > 20:
        return round(min(1.0, (vehiculo.freno - 0.8) / 0.2) * min(1.0, vehiculo.velocidad / 60), 3)
    if (vehiculo.motor and vehiculo.acoplado and vehiculo.marcha == "1" and vehiculo.acelerador > 0.9
            and vehiculo.velocidad < 35 and not vehiculo.traccion_bloqueada):
        return 0.7
    return 0.0


def estado_de(vehiculo, volumen=0.8, crank=0.0):
    """Estado sonoro del modelo fisico del panel (con la traccion bloqueada el pedal no carga el motor)."""
    acel = 0.0 if vehiculo.traccion_bloqueada else max(0.0, min(1.0, vehiculo.acelerador))
    energizado = bool(vehiculo.contacto or vehiculo.motor)
    return EstadoSonoro(motor=bool(vehiculo.motor), rpm=max(0.0, min(9000.0, float(vehiculo.rpm))), acel=acel,
                        turbo=max(0.0, min(2.0, float(vehiculo.presion_turbo))),
                        vel=max(0.0, min(360.0, float(vehiculo.velocidad))), contacto=energizado,
                        cinturon=bool(vehiculo.cinturon), vol=volumen, crank=max(0.0, min(1.0, crank)),
                        banco=bool(vehiculo.motor and vehiculo.fallas.ecu_banco),
                        intermitente=energizado and (vehiculo.direccional != "OFF" or vehiculo.emergencia),
                        chirrido=chirrido_de(vehiculo), ventilador=bool(vehiculo.ventilador))


# ------------------------------------------------------------------ protocolo del socket
def a_mensaje(estado):
    datos = {k: (int(v) if isinstance(v, bool) else round(v, 3)) for k, v in asdict(estado).items()}
    return (json.dumps(datos, separators=(",", ":")) + "\n").encode("ascii")


def _sin_constantes(texto):
    raise ValueError(f"constante no permitida: {texto}")


def de_mensaje(linea):
    """Convierte una linea recibida en EstadoSonoro; ValueError si no es valida (nada se usa sin validar)."""
    if len(linea) > LARGO_MAXIMO:
        raise ValueError("mensaje demasiado largo")
    datos = json.loads(linea.decode("ascii"), parse_constant=_sin_constantes)
    if not isinstance(datos, dict) or not set(datos) <= set(LIMITES) | set(BOOLEANOS):
        raise ValueError("claves desconocidas")
    estado = EstadoSonoro()
    for clave, valor in datos.items():
        if clave in BOOLEANOS:
            if valor not in (0, 1) or isinstance(valor, float):
                raise ValueError(f"{clave} debe ser 0 o 1")
            setattr(estado, clave, bool(valor))
        else:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise ValueError(f"{clave} no es numero")
            minimo, maximo = LIMITES[clave]
            if not minimo <= valor <= maximo:
                raise ValueError(f"{clave}={valor} fuera de rango")
            setattr(estado, clave, float(valor))
    return estado


# ------------------------------------------------------------------ sintetizador
class SintetizadorMotor:
    def __init__(self, fs=FS, semilla=7):
        self.fs = fs
        self.azar = random.Random(semilla)
        self.seno = [math.sin(2 * math.pi * i / 1024) for i in range(1024)]
        self.ding = [0.24 * (math.sin(2 * math.pi * 1046 * i / fs) * math.exp(-i / (0.18 * fs))
                            + 0.5 * math.sin(2 * math.pi * 1568 * i / fs) * math.exp(-i / (0.12 * fs)))
                     for i in range(int(0.9 * fs))]
        self.rpm = self.acel = self.turbo = 0.0
        self.fase = self.fase_turbo = self.fase_arranque = 0.0
        self.fase_chirrido = self.fase_vibrato = self.fase_ventilador = 0.0
        self.clic = 0.0
        self.cilindro = 0
        self.y = [0.0] * 6
        self.bajo = self.grave = self.envolvente = self.descarga = self.llamarada = 0.0
        self.arranque = self.campana = self.campana_pos = 0
        self.motor_previo = self.contacto_previo = False
        self.muestras = 0
        self.explosiones = 0          # contadores para las pruebas y el reporte
        self.cortes = 0
        self.petardeos = 0
        self.saltadas = 0             # explosiones que faltan por el banco sin encendido
        self.clics = 0

    def _resonador(self, frecuencia, ancho):
        w = 2 * math.pi * min(frecuencia, 0.45 * self.fs) / self.fs
        r = math.exp(-math.pi * ancho / self.fs)
        return 2 * r * math.cos(w), r * r, math.sin(w)      # la entrada se escala por sin(w): pico ~ amplitud

    def _transiciones(self, e):
        if e.motor and not self.motor_previo:
            self.arranque = int(ARRANQUE_S * self.fs)
        if not e.motor:
            self.arranque = 0
        if e.contacto and not self.contacto_previo and not e.cinturon:
            self.campana, self.campana_pos = int(CAMPANA_S * self.fs), 0
        if e.cinturon or not e.contacto:
            self.campana = 0
        if self.turbo > 0.4 and self.acel - e.acel > 0.35:      # se solto el acelerador con presion
            self.descarga = 0.55 * min(1.0, self.turbo / 1.1)
        self.motor_previo, self.contacto_previo = e.motor, e.contacto

    def generar(self, e, n):
        """n muestras PCM de 16 bits (array 'h') con el estado e; las rpm se interpolan muestra a muestra."""
        salida = array.array("h", bytes(2 * max(0, n)))
        if n <= 0:
            return salida
        self._transiciones(e)
        fs = self.fs
        rpm, rpm_final = self.rpm, e.rpm
        paso_rpm = (rpm_final - rpm) / n
        media = (rpm + rpm_final) / 2
        carga = e.acel
        a1, b1, g1 = self._resonador(85 + 0.012 * media, 55)
        a2, b2, g2 = self._resonador(330 + 0.06 * media, 170)
        a3, b3, g3 = self._resonador(1300 + 0.12 * media, 450)
        m3 = 0.08 + 0.17 * carga
        amp = (0.30 + 0.55 * carga) * (0.55 + 0.45 * min(1.0, media / 8000))
        suelto = carga < 0.05 and media > 2500 and e.motor
        if suelto:
            amp *= 0.45
        corte = e.motor and media >= LIMITADOR_RPM and carga > 0.5
        periodo_corte = int(CORTE_S * fs)
        vaiven = 0.04 * (1.0 - carga) if media < 2000 else 0.0       # ralenti irregular
        c_bajo = 1 - math.exp(-2 * math.pi * (300 + 0.25 * media) / fs)
        c_grave = 1 - math.exp(-2 * math.pi * 120 / fs)
        rugido_base = (0.03 + 0.20 * carga * min(1.0, media / 8000)) if e.motor else 0.0
        viento = 0.10 * min(1.0, e.vel / 250) ** 2
        turbo = e.turbo
        silbido = 0.045 * min(1.0, turbo / 1.1)
        siseo = 0.03 * min(1.0, turbo / 1.1)
        paso_turbo = (2200 + 2600 * min(1.0, turbo / 1.2)) / fs
        k_fase = EXPLOSIONES_POR_VUELTA / 60.0 / fs
        dec_env = math.exp(-1 / (0.0025 * fs))
        dec_descarga = math.exp(-1 / (0.085 * fs))
        dec_llamarada = math.exp(-1 / (0.15 * fs))
        vol = e.vol
        motor = e.motor
        forzado = (not motor) and e.crank > 0.0       # motor de arranque girando sin prender
        crank = e.crank
        banco = e.banco
        medio_segundo = fs // 2
        intermitente = e.intermitente
        chirrido = 0.12 * e.chirrido
        ventilador = 0.03 if e.ventilador else 0.0
        dec_clic = math.exp(-1 / (0.0015 * fs))
        rnd = self.azar.random
        seno, ding, largo_ding = self.seno, self.ding, len(self.ding)
        y1a, y1b, y2a, y2b, y3a, y3b = self.y
        fase, cil, t = self.fase, self.cilindro, self.muestras
        bajo, grave, env = self.bajo, self.grave, self.envolvente
        descarga, llamarada = self.descarga, self.llamarada
        arranque, fase_arr, fase_t = self.arranque, self.fase_arranque, self.fase_turbo
        campana, campana_pos = self.campana, self.campana_pos
        fase_ch, fase_vib, fase_ven, clic = self.fase_chirrido, self.fase_vibrato, self.fase_ventilador, self.clic
        explosiones = cortes = petardeos = saltadas = clics = 0
        for i in range(n):
            rpm += paso_rpm
            x = extra = 0.0
            quema = 1.0
            if arranque > 0 or forzado:                          # motor de arranque: zumbido y compresiones
                giro = 1.0
                if arranque > 0:
                    arranque -= 1
                    if arranque == 0:
                        llamarada = 0.35                         # al prender sube un poco y se asienta
                else:
                    giro = crank                                 # bateria debil: gira lento
                fase_arr += 190.0 * giro / fs
                extra = 0.09 * (seno[int(fase_arr * 1024) & 1023] + 0.5 * seno[int(fase_arr * 2048) & 1023])
                fase += 250.0 * giro * k_fase
                quema = 0.0
                if fase >= 1.0:
                    fase -= 1.0
                    x = 0.22
            elif rpm > 30.0:
                fase += rpm * k_fase
                if fase >= 1.0:
                    fase -= 1.0 + vaiven * (rnd() - 0.5)
                    cil = (cil + 1) & 7
                    if not motor:
                        x = 0.02 * rpm / 8000                    # gira sin combustion
                    elif corte and (t // periodo_corte) & 1:
                        cortes += 1
                    elif banco and cil & 1:                      # el banco sin encendido no explota
                        saltadas += 1
                        x = 0.03
                    else:
                        x = amp * (1.0 + DESBALANCE[cil] + 0.12 * (rnd() - 0.5)) * (1.0 + llamarada)
                        explosiones += 1
                        if suelto and rnd() < 0.008:             # petardeo al soltar en altas
                            x += 1.4
                            petardeos += 1
                    if x > env:
                        env = x
            if motor and corte and (t // periodo_corte) & 1:
                quema = 0.0
            y1 = a1 * y1a - b1 * y1b + g1 * x
            y1b, y1a = y1a, y1
            y2 = a2 * y2a - b2 * y2b + g2 * x
            y2b, y2a = y2a, y2
            y3 = a3 * y3a - b3 * y3b + g3 * x
            y3b, y3a = y3a, y3
            ruido = rnd() * 2.0 - 1.0
            bajo += c_bajo * (ruido - bajo)
            grave += c_grave * (ruido - grave)
            agudo = ruido - bajo
            env *= dec_env
            llamarada *= dec_llamarada
            s = (0.55 * y1 + 0.35 * y2 + m3 * y3 + 0.9 * env * bajo + rugido_base * quema * bajo + viento * grave
                 + extra)
            if silbido:
                fase_t += paso_turbo
                s += silbido * seno[int(fase_t * 1024) & 1023] + siseo * agudo
            if descarga > 0.0005:
                s += descarga * agudo
                descarga *= dec_descarga
            if intermitente and t % medio_segundo == 0:         # relevador: tic al encender, tac al apagar
                clic = 0.35 if (t // medio_segundo) & 1 == 0 else 0.22
                clics += 1
            if clic > 0.001:
                s += clic * agudo
                clic *= dec_clic
            if chirrido:
                fase_vib += 7.0 / fs
                fase_ch += (1100.0 + 10.0 * seno[int(fase_vib * 1024) & 1023]) / fs
                s += chirrido * (seno[int(fase_ch * 1024) & 1023] + 0.4 * agudo)
            if ventilador:
                fase_ven += 45.0 / fs
                s += ventilador * seno[int(fase_ven * 1024) & 1023] + 1.5 * ventilador * grave
            if campana > 0:
                posicion = campana_pos % fs
                if posicion < largo_ding:
                    s += ding[posicion]
                campana_pos += 1
                campana -= 1
            s *= vol
            s = 1.5 * s / (1.0 + (s if s > 0 else -s))
            if s > 0.99:
                s = 0.99
            elif s < -0.99:
                s = -0.99
            salida[i] = int(s * 32000)
            t += 1
        self.rpm, self.acel, self.turbo = rpm_final, e.acel, e.turbo
        self.y = [y1a, y1b, y2a, y2b, y3a, y3b]
        self.fase, self.cilindro, self.muestras = fase, cil, t
        self.bajo, self.grave, self.envolvente = bajo, grave, env
        self.descarga, self.llamarada = descarga, llamarada
        self.arranque, self.fase_arranque, self.fase_turbo = arranque, fase_arr % 1.0, fase_t % 1.0
        self.campana, self.campana_pos = campana, campana_pos
        self.fase_chirrido, self.fase_vibrato, self.fase_ventilador = fase_ch % 1.0, fase_vib % 1.0, fase_ven % 1.0
        self.clic = clic
        self.saltadas += saltadas
        self.clics += clics
        self.explosiones += explosiones
        self.cortes += cortes
        self.petardeos += petardeos
        if sys.byteorder == "big":                               # pragma: no cover - el formato es little endian
            salida.byteswap()
        return salida


# ------------------------------------------------------------------ salidas de audio
class SalidaWav:
    """Escribe el audio en un archivo WAV (evidencia y pruebas)."""

    def __init__(self, ruta, fs=FS):
        pathlib.Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.archivo = wave.open(str(ruta), "wb")
        self.archivo.setnchannels(1)
        self.archivo.setsampwidth(2)
        self.archivo.setframerate(fs)
        self.bytes = 0

    def escribir(self, datos):
        self.archivo.writeframes(datos)
        self.bytes += len(datos)

    def cerrar(self):
        self.archivo.close()


class SalidaAplay:  # pragma: no cover - requiere aplay y una tarjeta de sonido
    """Linux: proceso hijo aplay; el audio viaja por una tuberia y aplay lo entrega a ALSA."""

    def __init__(self, fs=FS):
        self.proceso = subprocess.Popen(["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(fs), "-c", "1",
                                         "--buffer-time=100000", "--period-time=25000"],
                                        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def escribir(self, datos):
        self.proceso.stdin.write(datos)
        self.proceso.stdin.flush()

    def cerrar(self):
        try:
            self.proceso.stdin.close()
        except OSError:
            pass
        self.proceso.terminate()


class SalidaWinmm:  # pragma: no cover - solo existe en Windows
    """Windows: waveOut de winmm con 4 buferes de 30 ms. Cuando todos estan en uso, espera el evento
    que winmm senala al terminar uno (WaitForSingleObject): no hay espera activa."""

    BUFERES = 4

    def __init__(self, fs=FS, bloque=BLOQUE):
        import ctypes
        from ctypes import wintypes
        self.ct = ctypes

        class FormatoOnda(ctypes.Structure):
            _fields_ = [("wFormatTag", wintypes.WORD), ("nChannels", wintypes.WORD),
                        ("nSamplesPerSec", wintypes.DWORD), ("nAvgBytesPerSec", wintypes.DWORD),
                        ("nBlockAlign", wintypes.WORD), ("wBitsPerSample", wintypes.WORD), ("cbSize", wintypes.WORD)]

        class Cabecera(ctypes.Structure):
            _fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
                        ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_size_t), ("dwFlags", wintypes.DWORD),
                        ("dwLoops", wintypes.DWORD), ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_size_t)]

        self.winmm = ctypes.WinDLL("winmm")
        self.kernel = ctypes.WinDLL("kernel32")
        self.winmm.waveOutOpen.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.UINT, ctypes.POINTER(FormatoOnda),
                                           ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
        for nombre in ("waveOutPrepareHeader", "waveOutUnprepareHeader", "waveOutWrite"):
            getattr(self.winmm, nombre).argtypes = [wintypes.HANDLE, ctypes.POINTER(Cabecera), wintypes.UINT]
        self.winmm.waveOutReset.argtypes = [wintypes.HANDLE]
        self.winmm.waveOutClose.argtypes = [wintypes.HANDLE]
        self.kernel.CreateEventW.restype = wintypes.HANDLE
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, ctypes.c_wchar_p]
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        formato = FormatoOnda(1, 1, fs, fs * 2, 2, 16, 0)
        self.evento = self.kernel.CreateEventW(None, False, False, None)
        self.manija = wintypes.HANDLE()
        codigo = self.winmm.waveOutOpen(ctypes.byref(self.manija), 0xFFFFFFFF, ctypes.byref(formato), self.evento,
                                        0, 0x00050000)        # WAVE_MAPPER, CALLBACK_EVENT
        if codigo != 0:
            raise OSError(f"waveOutOpen devolvio {codigo}")
        self.tamano = ctypes.sizeof(Cabecera)
        self.datos = [ctypes.create_string_buffer(bloque * 2 * 2) for _ in range(self.BUFERES)]
        self.cabeceras = [Cabecera() for _ in range(self.BUFERES)]
        self.en_uso = [False] * self.BUFERES

    def _libre(self):
        for i, cabecera in enumerate(self.cabeceras):
            if not self.en_uso[i]:
                return i
            if cabecera.dwFlags & 1:                       # WHDR_DONE
                self.winmm.waveOutUnprepareHeader(self.manija, self.ct.byref(cabecera), self.tamano)
                self.en_uso[i] = False
                return i
        return None

    def escribir(self, datos):
        i = self._libre()
        while i is None:
            self.kernel.WaitForSingleObject(self.evento, 200)
            i = self._libre()
        datos = datos[:len(self.datos[i])]
        self.ct.memmove(self.datos[i], datos, len(datos))
        cabecera = self.cabeceras[i]
        cabecera.lpData = self.ct.cast(self.datos[i], self.ct.c_void_p)
        cabecera.dwBufferLength = len(datos)
        cabecera.dwFlags = 0
        self.winmm.waveOutPrepareHeader(self.manija, self.ct.byref(cabecera), self.tamano)
        self.winmm.waveOutWrite(self.manija, self.ct.byref(cabecera), self.tamano)
        self.en_uso[i] = True

    def cerrar(self):
        self.winmm.waveOutReset(self.manija)
        for i, cabecera in enumerate(self.cabeceras):
            if self.en_uso[i]:
                self.winmm.waveOutUnprepareHeader(self.manija, self.ct.byref(cabecera), self.tamano)
        self.winmm.waveOutClose(self.manija)
        self.kernel.CloseHandle(self.evento)


def abrir_salida_local(fs=FS):
    """(salida, descripcion) o (None, motivo). Nunca lanza: sin audio el panel sigue sin sonido."""
    if os.name == "nt":  # pragma: no cover - solo Windows
        try:
            return SalidaWinmm(fs), "Windows (waveOut)"
        except OSError as error:
            return None, f"waveOut no disponible: {error}"
    if not shutil.which("aplay"):
        return None, "falta aplay (sudo apt-get install alsa-utils)"
    dispositivos = sorted(pathlib.Path("/dev/snd").glob("pcmC*D*p")) if pathlib.Path("/dev/snd").is_dir() else []
    if not dispositivos:
        return None, "no hay tarjeta de sonido"
    if not os.access(dispositivos[0], os.W_OK):
        return None, "sin permiso en /dev/snd (sudo usermod -aG audio $USER)"
    try:  # pragma: no cover - requiere tarjeta de sonido y permisos
        return SalidaAplay(fs), "ALSA (aplay)"
    except OSError as error:  # pragma: no cover
        return None, f"aplay no arranco: {error}"


# ------------------------------------------------------------------ hilos
class HiloSonido(threading.Thread):
    """Consumidor de tiempo real: toma el estado mas reciente del buzon y genera bloques de 30 ms."""

    def __init__(self, salida, sintetizador=None, bloque=BLOQUE, adelanto_max_s=ADELANTO_MAX_S, reloj=time.monotonic):
        super().__init__(name="sonido_motor", daemon=True)
        self.salida = salida
        self.sint = sintetizador or SintetizadorMotor()
        self.bloque = bloque
        self.adelanto_max_s = adelanto_max_s
        self.reloj = reloj
        self.buzon = queue.Queue(maxsize=1)
        self.estado = EstadoSonoro()
        self._detener = threading.Event()
        self.bloques = 0
        self.atrasos = 0
        self.adelanto_maximo = 0.0
        self.error = None

    def publicar(self, estado):
        publicar(self.buzon, estado)

    def run(self):
        inicio, producidas = self.reloj(), 0
        try:
            while not self._detener.is_set():
                try:
                    self.estado = self.buzon.get_nowait()
                except queue.Empty:
                    pass
                adelanto = producidas / self.sint.fs - (self.reloj() - inicio)
                if adelanto > self.adelanto_max_s:
                    self._detener.wait(adelanto - self.adelanto_max_s + 0.002)   # duerme, no gira
                    continue
                if adelanto < -0.25:                       # la maquina se trabo: se resincroniza
                    inicio = self.reloj() - producidas / self.sint.fs
                    self.atrasos += 1
                self.adelanto_maximo = max(self.adelanto_maximo, adelanto)
                self.salida.escribir(self.sint.generar(self.estado, self.bloque).tobytes())
                producidas += self.bloque
                self.bloques += 1
        except Exception as error:  # noqa: BLE001 - un fallo de audio no debe tumbar el panel
            self.error = error
        finally:
            self.salida.cerrar()

    def detener(self, espera_s=2.0):
        self._detener.set()
        self.join(espera_s)


class SonidoApagado:
    activo = False

    def __init__(self, descripcion="apagado"):
        self.descripcion = descripcion

    def publicar(self, estado):
        pass

    def detener(self):
        pass


class SonidoLocal:
    activo = True

    def __init__(self, salida, descripcion):
        self.descripcion = descripcion
        self.hilo = HiloSonido(salida)
        self.hilo.start()

    def publicar(self, estado):
        self.hilo.publicar(estado)

    def detener(self):
        self.hilo.detener()


class SonidoRemoto:
    """Envia el estado a una bocina por TCP (por ejemplo, por un tunel SSH hacia Windows). Un hilo
    propio conecta y reintenta cada 2 s: el panel nunca se bloquea si la bocina no esta."""

    activo = True

    def __init__(self, host, puerto):
        self.destino = (host, puerto)
        self.descripcion = f"bocina en {host}:{puerto}"
        self.buzon = queue.Queue(maxsize=1)
        self.enviados = 0
        self.conectado = False
        self._detener = threading.Event()
        self.hilo = threading.Thread(target=self._correr, name="sonido_remoto", daemon=True)
        self.hilo.start()

    def publicar(self, estado):
        publicar(self.buzon, estado)

    def _correr(self):
        conexion, proximo_intento = None, 0.0
        while not self._detener.is_set():
            try:
                estado = self.buzon.get(timeout=0.2)      # bloquea hasta que hay un estado nuevo
            except queue.Empty:
                continue
            if conexion is None:
                if time.monotonic() < proximo_intento:
                    continue
                try:
                    conexion = socket.create_connection(self.destino, timeout=0.5)
                    conexion.settimeout(1.0)
                    self.conectado = True
                except OSError:
                    proximo_intento = time.monotonic() + 2.0
                    continue
            try:
                conexion.sendall(a_mensaje(estado))
                self.enviados += 1
            except OSError:
                conexion.close()
                conexion, self.conectado = None, False
        if conexion is not None:
            conexion.close()

    def detener(self):
        self._detener.set()
        self.hilo.join(2.0)


def crear(modo="no", salida=None):
    """modo: "no", "auto" (salida local si existe), o "host:puerto" (bocina remota)."""
    if salida is not None:
        return SonidoLocal(salida, "salida de prueba")
    if modo in (None, "", "no"):
        return SonidoApagado("apagado")
    if modo in ("auto", "local"):
        salida, texto = abrir_salida_local()
        return SonidoLocal(salida, texto) if salida is not None else SonidoApagado(f"sin audio: {texto}")
    host, _, puerto = modo.rpartition(":")
    if not puerto.isdigit() or not 0 < int(puerto) < 65536:
        return SonidoApagado(f"modo de sonido invalido: {modo!r}")
    return SonidoRemoto(host or "127.0.0.1", int(puerto))


# ------------------------------------------------------------------ analisis (pruebas y reporte)
def potencia(muestras, frecuencia, fs=FS):
    """Potencia de una frecuencia con el algoritmo de Goertzel (una sola linea de la DFT)."""
    coef = 2 * math.cos(2 * math.pi * frecuencia / fs)
    s1 = s2 = 0.0
    for x in muestras:
        s1, s2 = x + coef * s1 - s2, s1
    return (s1 * s1 + s2 * s2 - coef * s1 * s2) / max(1, len(muestras)) ** 2


def envolvente(muestras, ventana):
    """Raiz cuadratica media por ventanas de `ventana` muestras."""
    return [math.sqrt(sum(x * x for x in muestras[i:i + ventana]) / ventana)
            for i in range(0, len(muestras) - ventana + 1, ventana)]


def periodo_dominante_ms(muestras, fs=FS, minimo_ms=5.0, maximo_ms=40.0):
    """Periodo (ms) de la repeticion mas fuerte de la envolvente: el ritmo de las explosiones."""
    env = envolvente(muestras, max(1, fs // 2000))            # ventanas de 0.5 ms
    media = sum(env) / len(env)
    env = [v - media for v in env]
    mejor, retardo_mejor = None, None
    for retardo in range(int(minimo_ms * 2), int(maximo_ms * 2) + 1):
        valor = sum(a * b for a, b in zip(env, env[retardo:]))
        if mejor is None or valor > mejor:
            mejor, retardo_mejor = valor, retardo
    return retardo_mejor / 2
