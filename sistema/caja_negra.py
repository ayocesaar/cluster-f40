"""Caja negra del cluster: registrador de datos de tamano fijo con acceso directo (Etapa 20).

Guarda los ultimos 60 s del vehiculo (10 muestras por segundo) en datos/caja_negra.bin.

Formato binario (little endian; ver docs/caja_negra.md):
- Cabecera de 64 bytes: firma "F40CNEG1", version, tamano de registro, capacidad, total de
  registros escritos, fecha de creacion y CRC-16.
- 600 registros de 32 bytes: fecha en ms, secuencia, velocidad, rpm, presiones, temperatura,
  combustible, voltaje, testigos (bits), causa de proteccion, estado (bits) y CRC-16.
El archivo se crea de su tamano final (64 + 600 x 32 = 19 264 bytes) y nunca crece: es un
anillo. El registro numero k va en la posicion 64 + (k mod 600) x 32 y se escribe con
pwrite en ese desplazamiento (acceso directo); para leer los ultimos N no se recorre el
archivo: se calcula donde estan.

Politica de escritura: la interfaz solo empaqueta la muestra y la deja en una cola acotada
(nunca espera al disco; si la cola se llena, la muestra se descarta y se cuenta; los eventos
van en una lista aparte y nunca se pierden). Un hilo
escritor la graba y hace fsync una vez por segundo: se pierde a lo mas el ultimo segundo si
se va la luz, a cambio de no sincronizar 10 veces por segundo. Cada registro lleva su CRC:
uno danado se detecta y se salta.

Evento: cuando se enciende un testigo critico (9, 10, 15, 16 o la puerta en movimiento) la
caja negra sincroniza y exporta a CSV los 10 s anteriores en logs/caja_negra/ (se conservan
los 20 mas recientes)."""

import binascii
import collections
import csv
import datetime
import os
import pathlib
import queue
import struct
import threading
import time

from logic.estado import CAUSAS_MOTOR

COMPONENTE = "caja_negra"
FIRMA = b"F40CNEG1"
VERSION = 1
CABECERA = struct.Struct("<8sHHIQQ30xH")        # 64 bytes
REGISTRO = struct.Struct("<QIHHHhHBBHBB2xH")    # 32 bytes
SIN_DATO = 255
# Bit de cada testigo en el campo "testigos" (14 = reserva de combustible).
TESTIGOS = (6, 7, 8, 9, 10, 12, 13, 14, 15, 16)
ESTADOS = ("motor", "encendido", "prueba_de_testigos")
CAMPOS = ("fecha", "secuencia", "velocidad_kmh", "rpm", "presion_aceite_bar", "temp_agua_c", "presion_turbo_bar",
          "combustible_pct", "voltaje_v", "testigos", "causa", "motor", "encendido", "prueba_de_testigos")


def _crc(datos):
    return binascii.crc_hqx(datos, 0xFFFF)


def _entero(valor, escala, minimo, maximo):
    return max(minimo, min(maximo, int(round(valor * escala))))


def muestra(estado, ahora_ms):
    """Valores del instante (sin la secuencia) a partir de EstadoCluster."""
    activos = {
        6: estado.encendido and estado.direccional != "OFF", 7: estado.testigo_luces_altas_encendido,
        8: estado.encendido and estado.emergencia_activa, 9: estado.testigo_baja_presion_aceite,
        10: estado.falla_frenos_activa, 12: bool(estado.encendido and estado.puerta_abierta),
        13: bool(estado.encendido and estado.cinturon_desabrochado), 14: estado.reserva_combustible,
        15: estado.proteccion_motor_activa, 16: estado.testigo_carga_encendido,
    }
    causa = estado.falla_motor
    return {
        "fecha": int(ahora_ms), "velocidad_kmh": estado.velocidad, "rpm": estado.rpm,
        "presion_aceite_bar": estado.p_aceite, "temp_agua_c": estado.temp_agua, "presion_turbo_bar": estado.p_turbo,
        "combustible_pct": estado.combustible, "voltaje_v": estado.voltaje,
        "testigos": sum(1 << i for i, n in enumerate(TESTIGOS) if activos[n]),
        "causa": causa, "motor": estado.motor_activo, "encendido": estado.encendido,
        "prueba_de_testigos": estado.prueba_testigos_activa,
    }


def empaquetar(valores, secuencia):
    """Diccionario -> 32 bytes. Escalas: decimas de km/h y de C, centesimas de bar, decimas de V."""
    causa = valores["causa"]
    estado = sum(1 << i for i, nombre in enumerate(ESTADOS) if valores[nombre])
    cuerpo = REGISTRO.pack(
        valores["fecha"], secuencia & 0xFFFFFFFF,
        _entero(valores["velocidad_kmh"], 10, 0, 3600), _entero(valores["rpm"], 1, 0, 9000),
        _entero(valores["presion_aceite_bar"], 100, 0, 1000), _entero(valores["temp_agua_c"], 10, -400, 1500),
        _entero(valores["presion_turbo_bar"], 100, 0, 200),
        SIN_DATO if valores["combustible_pct"] is None else _entero(valores["combustible_pct"], 1, 0, 100),
        SIN_DATO if valores["voltaje_v"] is None else _entero(valores["voltaje_v"], 10, 0, 200),
        valores["testigos"], SIN_DATO if causa is None else CAUSAS_MOTOR.index(causa), estado, 0)
    return cuerpo[:-2] + struct.pack("<H", _crc(cuerpo[:-2]))


def desempaquetar(datos):
    """32 bytes -> diccionario; ValueError si el CRC no coincide (registro danado)."""
    campos = REGISTRO.unpack(datos)
    if _crc(datos[:-2]) != campos[-1]:
        raise ValueError("crc invalido")
    fecha, secuencia, vel, rpm, aceite, agua, turbo, comb, volt, testigos, causa, estado, _ = campos
    return {
        "fecha": fecha, "secuencia": secuencia, "velocidad_kmh": vel / 10, "rpm": rpm,
        "presion_aceite_bar": aceite / 100, "temp_agua_c": agua / 10, "presion_turbo_bar": turbo / 100,
        "combustible_pct": None if comb == SIN_DATO else comb, "voltaje_v": None if volt == SIN_DATO else volt / 10,
        "testigos": [n for i, n in enumerate(TESTIGOS) if testigos >> i & 1],
        "causa": None if causa == SIN_DATO else CAUSAS_MOTOR[causa],
        **{nombre: bool(estado >> i & 1) for i, nombre in enumerate(ESTADOS)},
    }


class CajaNegra:
    """El archivo: anillo de registros de tamano fijo con acceso directo."""

    def __init__(self, ruta, capacidad=600, bitacora=None):
        self.ruta = pathlib.Path(ruta)
        self.capacidad = capacidad
        self.bitacora = bitacora
        self.total = 0
        self.creada_ms = 0
        self.danados = 0
        self.fd = None
        self._abrir()

    def _registrar(self, nivel, evento, detalle):
        if self.bitacora is not None:
            getattr(self.bitacora, nivel)(COMPONENTE, evento, detalle)

    def _tamano(self):
        return CABECERA.size + self.capacidad * REGISTRO.size

    def _abrir(self):
        problema = None
        if self.ruta.exists():
            try:
                with open(self.ruta, "rb") as archivo:
                    cabecera = archivo.read(CABECERA.size)
                firma, version, tamano, capacidad, total, creada, crc = CABECERA.unpack(cabecera)
                if firma != FIRMA or version != VERSION or tamano != REGISTRO.size or _crc(cabecera[:-2]) != crc:
                    problema = "cabecera_invalida"
                elif capacidad != self.capacidad:
                    problema = "capacidad_distinta"
                elif self.ruta.stat().st_size != self._tamano():
                    problema = "tamano_invalido"
                else:
                    self.total, self.creada_ms = total, creada
            except (OSError, struct.error):
                problema = "cabecera_invalida"
            if problema:
                # El archivo danado no se borra: se aparta para revisarlo y se empieza uno nuevo.
                apartado = self.ruta.with_name(self.ruta.name + ".invalido")
                os.replace(self.ruta, apartado)
                (self._registrar("warn", "caja_negra_reiniciada", f"{problema}: capacidad {capacidad} -> {self.capacidad}")
                 if problema == "capacidad_distinta" else
                 self._registrar("error", "caja_negra_invalida", f"{problema}; se aparto en {apartado.name} y se "
                                                                  "creo una nueva resultado=recuperado"))
        nueva = not self.ruta.exists()
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.ruta, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o640)
        if nueva:
            self.creada_ms = int(time.time() * 1000)
            os.ftruncate(self.fd, self._tamano())          # tamano final desde el principio
            self._escribir_cabecera()
            os.fsync(self.fd)
            self._registrar("info", "caja_negra_creada", f"capacidad={self.capacidad} registros de {REGISTRO.size} "
                                                          f"bytes ({self._tamano()} bytes)")
        if os.name == "posix":
            os.chmod(self.ruta, 0o640)

    def _escribir_cabecera(self):
        cuerpo = CABECERA.pack(FIRMA, VERSION, REGISTRO.size, self.capacidad, self.total, self.creada_ms, 0)
        self._en(0, cuerpo[:-2] + struct.pack("<H", _crc(cuerpo[:-2])))

    def _en(self, desplazamiento, datos):
        if hasattr(os, "pwrite"):
            os.pwrite(self.fd, datos, desplazamiento)
        else:  # pragma: no cover - Windows no tiene pwrite
            os.lseek(self.fd, desplazamiento, os.SEEK_SET)
            os.write(self.fd, datos)

    def _de(self, desplazamiento, n):
        if hasattr(os, "pread"):
            return os.pread(self.fd, n, desplazamiento)
        os.lseek(self.fd, desplazamiento, os.SEEK_SET)  # pragma: no cover - Windows no tiene pread
        return os.read(self.fd, n)  # pragma: no cover

    def desplazamiento(self, secuencia):
        return CABECERA.size + (secuencia % self.capacidad) * REGISTRO.size

    def escribir(self, valores):
        self._en(self.desplazamiento(self.total), empaquetar(valores, self.total))
        self.total += 1
        self._escribir_cabecera()

    def sincronizar(self):
        os.fsync(self.fd)

    def ultimos(self, n=None):
        """Los ultimos n registros validos, del mas viejo al mas nuevo (acceso directo a cada uno)."""
        n = min(self.capacidad, self.total) if n is None else min(n, self.capacidad, self.total)
        registros = []
        for secuencia in range(self.total - n, self.total):
            try:
                registro = desempaquetar(self._de(self.desplazamiento(secuencia), REGISTRO.size))
            except ValueError:
                self.danados += 1
                continue
            if registro["secuencia"] == secuencia & 0xFFFFFFFF:
                registros.append(registro)
        return registros

    def cerrar(self):
        if self.fd is not None:
            os.fsync(self.fd)
            os.close(self.fd)
            self.fd = None


def exportar_csv(registros, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(CAMPOS)
        for r in registros:
            fila = [r[c] for c in CAMPOS]
            fila[CAMPOS.index("testigos")] = " ".join(str(t) for t in r["testigos"])
            escritor.writerow(["" if v is None else v for v in fila])
    if os.name == "posix":
        os.chmod(ruta, 0o640)


class Registrador:
    """Lado de la interfaz: muestrea a 10 Hz, detecta eventos y entrega todo al hilo escritor."""

    def __init__(self, caja, dir_eventos, hz=10, segundos_evento=10, eventos_max=20, bitacora=None,
                 reloj=time.monotonic, sincronizar_cada_s=1.0):
        self.caja = caja
        self.dir_eventos = pathlib.Path(dir_eventos)
        self.periodo_s = 1.0 / hz
        self.registros_evento = int(segundos_evento * hz)
        self.eventos_max = eventos_max
        self.bitacora = bitacora
        self.reloj = reloj
        self.sincronizar_cada_s = sincronizar_cada_s
        self.cola = queue.Queue(maxsize=50)
        self.pendientes = collections.deque(maxlen=100)   # eventos: nunca se descartan por cola llena
        self.descartados = 0
        self.eventos = []
        self._proxima = 0.0
        self._previo = {}
        self._hilo = threading.Thread(target=self._escribir, name=COMPONENTE, daemon=True)
        self._hilo.start()

    def _poner(self, mensaje):
        try:
            self.cola.put_nowait(mensaje)
            return True
        except queue.Full:                 # la interfaz nunca espera al disco
            self.descartados += 1
            return False

    def muestrear(self, estado):
        ahora = self.reloj()
        criticos = {"testigo_9": estado.testigo_baja_presion_aceite, "testigo_10": estado.falla_frenos_activa,
                    "proteccion_motor": estado.proteccion_motor_activa, "falla_de_carga": estado.falla_de_carga,
                    "puerta_en_movimiento": estado.puerta_abierta_en_movimiento}
        nuevos = [nombre for nombre, activo in criticos.items() if activo and not self._previo.get(nombre)]
        self._previo = criticos
        if ahora >= self._proxima - 1e-6 or nuevos:          # tolerancia: 0.1 + 0.2 no es 0.3 exacto
            self._proxima = ahora + self.periodo_s
            self._poner(("registro", muestra(estado, time.time() * 1000)))
        for nombre in nuevos:
            self.pendientes.append(nombre)
            self._poner(("aviso", None))         # despierta al escritor; si no cabe, igual lo atiende

    def _escribir(self):
        ultima_sincronizacion = self.reloj()
        while True:
            try:
                tipo, dato = self.cola.get(timeout=self.sincronizar_cada_s)
            except queue.Empty:
                tipo, dato = None, None
            if tipo == "fin":
                while self.pendientes:
                    self._exportar(self.pendientes.popleft())
                break
            if tipo == "registro":
                self.caja.escribir(dato)
            while self.pendientes:
                self._exportar(self.pendientes.popleft())
            if self.reloj() - ultima_sincronizacion >= self.sincronizar_cada_s:
                self.caja.sincronizar()
                ultima_sincronizacion = self.reloj()

    def _exportar(self, causa):
        self.caja.sincronizar()
        registros = self.caja.ultimos(self.registros_evento)
        self.dir_eventos.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.dir_eventos, 0o750)
        sello = datetime.datetime.now().strftime("%Y%m%dT%H%M%S_%f")[:-3]
        numero = getattr(self.caja, "total", 0)
        ruta = self.dir_eventos / f"evento_{sello}_{numero:08d}_{causa}.csv"
        exportar_csv(registros, ruta)
        self.eventos.append(ruta)
        for viejo in sorted(self.dir_eventos.glob("evento_*.csv"))[:-self.eventos_max]:
            viejo.unlink(missing_ok=True)   # se conservan solo los mas recientes
        if self.bitacora is not None:
            self.bitacora.info(COMPONENTE, "caja_negra_evento",
                               f"causa={causa} registros={len(registros)} archivo={ruta.name} resultado=aceptado")

    def cerrar(self, espera_s=3.0):
        try:
            self.cola.put(("fin", None), timeout=espera_s)
        except queue.Full:  # pragma: no cover - solo si el disco se trabo
            pass
        self._hilo.join(espera_s)
        self.caja.cerrar()
