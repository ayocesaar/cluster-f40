"""Entrada de datos externos: datos/vehiculo.conf en formato clave=valor.

Productor: un hilo (`HiloLector`) relee el archivo cada `lectura_ms`, valida
cada clave y publica una copia completa del ultimo estado valido en un buzon
(`queue.Queue` de tamano 1). Consumidor: la interfaz, en su propio hilo, toma
el snapshot mas reciente y lo aplica. Asi ningun objeto se modifica desde dos
hilos a la vez y la memoria queda acotada (el buzon nunca guarda mas de uno).

Para evitar lecturas parciales, quien escribe usa `escribir_atomico`: escribe
en un archivo temporal del mismo directorio y lo renombra con os.replace, que
es atomico. El lector ve el archivo viejo completo o el nuevo completo. Si aun
asi llega algo incompleto o invalido (por ejemplo, un editor que guarda en el
mismo archivo), la validacion lo rechaza y se conserva el ultimo valor valido."""

import os
import pathlib
import queue
import re
import tempfile
import threading
import time

COMPONENTE = "lector_datos"
TAMANO_MAXIMO = 4096          # bytes: un archivo mas grande se rechaza sin leerlo
LARGO_MAXIMO_VALOR = 32
REINTENTOS_WINDOWS = 5

# clave -> (setter de EstadoCluster, tipo)
CLAVES = {
    "motor": ("set_motor", "booleano"),
    "velocidad": ("set_velocidad", "decimal"),
    "rpm": ("set_rpm", "entero"),
    "presion_aceite": ("set_presion_aceite", "decimal"),
    "temp_agua": ("set_temp_agua", "decimal"),
    "presion_turbo": ("set_presion_turbo", "decimal"),
    "direccional": ("set_direccional", "enumeracion"),
    "luces_altas": ("set_luces_altas", "booleano"),
    "emergencia": ("set_emergencia", "booleano"),
    "falla_frenos": ("set_falla_frenos", "booleano"),
}
DIRECCIONALES = {"off": "OFF", "izquierda": "IZQ", "derecha": "DER"}
DIRECCIONALES_TEXTO = {v: k for k, v in DIRECCIONALES.items()}

# Estado seguro: es el valor que toma una clave que nunca llego valida.
VALORES_INICIALES = {
    "motor": False, "velocidad": 0.0, "rpm": 0, "presion_aceite": 0.0, "temp_agua": 40.0,
    "presion_turbo": 0.0, "direccional": "OFF", "luces_altas": False, "emergencia": False,
    "falla_frenos": False,
}

_ENTERO = re.compile(r"[+-]?\d{1,6}")
_DECIMAL = re.compile(r"[+-]?\d{1,6}(\.\d{1,4})?")


class DatoInvalido(ValueError):
    def __init__(self, evento, detalle):
        super().__init__(detalle)
        self.evento = evento
        self.detalle = detalle


def convertir(clave, texto, rangos):
    """Convierte el texto de una clave a su tipo y valida su rango; si no, DatoInvalido."""
    _, tipo = CLAVES[clave]
    if len(texto) > LARGO_MAXIMO_VALOR:
        raise DatoInvalido("dato_invalido", f"{clave} entrada demasiado larga ({len(texto)} caracteres)")
    if tipo == "booleano":
        if texto not in ("0", "1"):
            raise DatoInvalido("dato_invalido", f'{clave} entrada="{texto}" (se espera 0 o 1)')
        return texto == "1"
    if tipo == "enumeracion":
        valor = DIRECCIONALES.get(texto.lower())
        if valor is None:
            raise DatoInvalido("dato_invalido", f'{clave} entrada="{texto}" (se espera off, izquierda o derecha)')
        return valor
    patron = _ENTERO if tipo == "entero" else _DECIMAL
    if not patron.fullmatch(texto):
        raise DatoInvalido("dato_invalido", f'{clave} entrada="{texto}" (se espera un numero {tipo})')
    valor = int(texto) if tipo == "entero" else float(texto)
    minimo, maximo = rangos[clave]
    if not minimo <= valor <= maximo:
        raise DatoInvalido("fuera_de_rango", f"{clave}={texto} (rango {minimo:g}-{maximo:g})")
    return valor


def formatear(clave, valor):
    """Texto de un valor en el formato del archivo (inverso de convertir)."""
    _, tipo = CLAVES[clave]
    if tipo == "booleano":
        return "1" if valor else "0"
    if tipo == "enumeracion":
        return DIRECCIONALES_TEXTO[valor]
    return str(valor)


def parsear(texto):
    """Separa clave=valor; devuelve (pares, problemas). Ignora vacias y comentarios #."""
    pares, problemas = {}, []
    for numero, linea in enumerate(texto.splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        clave, signo, valor = linea.partition("=")
        clave, valor = clave.strip().lower(), valor.strip()
        if not signo or not clave:
            problemas.append(("linea_invalida", f"linea {numero} sin formato clave=valor"))
        elif clave not in CLAVES:
            problemas.append(("clave_desconocida", f"linea {numero} clave={clave[:LARGO_MAXIMO_VALOR]!r}"))
        elif clave in pares:
            problemas.append(("clave_duplicada", f"linea {numero} clave={clave} (se usa la ultima)"))
            pares[clave] = valor
        else:
            pares[clave] = valor
    return pares, problemas


def escribir_atomico(ruta, valores):
    """Escribe todas las claves (valores ya tipados) de forma atomica."""
    lineas = ["# Datos de entrada del cluster F40 (clave=valor). Escrito de forma atomica."]
    lineas += [f"{clave}={formatear(clave, valores[clave])}" for clave in CLAVES if clave in valores]
    escribir_texto_atomico(ruta, "\n".join(lineas) + "\n")


def escribir_texto_atomico(ruta, texto):
    """Escribe en un temporal del mismo directorio y lo renombra con os.replace (atomico)."""
    ruta = pathlib.Path(ruta)
    descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=".vehiculo.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as archivo:
            archivo.write(texto)
            archivo.flush()
            os.fsync(archivo.fileno())
        if os.name == "posix":
            os.chmod(temporal, 0o640)
        for intento in range(20):  # en Windows el reemplazo falla si el lector tiene el archivo abierto
            try:
                os.replace(temporal, ruta)
                break
            except PermissionError:
                if intento == 19:
                    raise
                time.sleep(0.005)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


class Lector:
    """Lee y valida el archivo de datos; conserva el ultimo valor valido de cada clave."""

    def __init__(self, ruta, rangos, bitacora):
        self.ruta = pathlib.Path(ruta)
        self.rangos = rangos
        self.bitacora = bitacora
        self.ultimo_valido = dict(VALORES_INICIALES)
        self._firma = None          # (mtime, tamano) de la ultima lectura completa
        self._problema_archivo = None
        self._ultimo_error = {}     # clave -> texto rechazado (para no repetir el mismo error)
        self.lecturas = 0

    def _fallo_archivo(self, evento, detalle):
        """Registra un problema del archivo una sola vez mientras dure."""
        if self._problema_archivo != evento:
            self.bitacora.error(COMPONENTE, evento, f"{detalle} resultado=rechazado")
            self._problema_archivo = evento
        self._firma = None
        return None

    def leer(self):
        """Devuelve el snapshot completo si hubo cambios, o None si no hay nada nuevo."""
        nombre = self.ruta.name
        try:
            info = self.ruta.stat()
        except FileNotFoundError:
            return self._fallo_archivo("archivo_inexistente", f"ruta={nombre} se conserva el ultimo valor valido")
        if os.name == "posix" and info.st_mode & 0o002:
            return self._fallo_archivo("permisos_inseguros", f"ruta={nombre} modo={oct(info.st_mode & 0o777)} escribible por cualquiera")
        if info.st_size > TAMANO_MAXIMO:
            return self._fallo_archivo("archivo_demasiado_grande", f"ruta={nombre} bytes={info.st_size}")
        firma = (info.st_mtime_ns, info.st_size)
        if firma == self._firma:
            return None
        try:
            texto = self._leer_texto()
        except PermissionError:
            return self._fallo_archivo("permiso_denegado", f"ruta={nombre} sin permiso de lectura")
        except FileNotFoundError:
            return self._fallo_archivo("archivo_inexistente", f"ruta={nombre} se conserva el ultimo valor valido")
        except UnicodeDecodeError:
            return self._fallo_archivo("dato_invalido", f"ruta={nombre} codificacion no valida (se espera UTF-8)")

        if self._problema_archivo is not None:
            self.bitacora.info(COMPONENTE, "archivo_recuperado", f"ruta={nombre} resultado=aceptado")
            self._problema_archivo = None
        self._firma = firma
        self.lecturas += 1
        return self._procesar(texto)

    def _leer_texto(self):
        """Lee el archivo completo de una vez. En Windows, abrir un archivo justo cuando otro
        proceso lo reemplaza da un PermissionError momentaneo: se reintenta antes de
        considerarlo un problema real de permisos."""
        intentos = REINTENTOS_WINDOWS if os.name == "nt" else 1
        for intento in range(intentos):
            try:
                with open(self.ruta, encoding="utf-8") as archivo:
                    return archivo.read(TAMANO_MAXIMO + 1)
            except PermissionError:
                if intento == intentos - 1:
                    raise
                time.sleep(0.002)

    def _procesar(self, texto):
        pares, problemas = parsear(texto)
        for evento, detalle in problemas:
            self.bitacora.error(COMPONENTE, evento, f"{detalle} resultado=rechazado")
        for clave in CLAVES:
            if clave not in pares:
                if self._ultimo_error.get(clave) != "<ausente>":
                    self.bitacora.error(COMPONENTE, "clave_faltante",
                                        f"{clave} se conserva {formatear(clave, self.ultimo_valido[clave])} resultado=rechazado")
                    self._ultimo_error[clave] = "<ausente>"
                continue
            try:
                valor = convertir(clave, pares[clave], self.rangos)
            except DatoInvalido as error:
                if self._ultimo_error.get(clave) != pares[clave]:
                    self.bitacora.error(COMPONENTE, error.evento, f"{error.detalle} resultado=rechazado")
                    self._ultimo_error[clave] = pares[clave]
                continue
            self._ultimo_error.pop(clave, None)
            if valor != self.ultimo_valido[clave]:
                self.bitacora.info(COMPONENTE, "valor_actualizado", f"{clave}={pares[clave]} resultado=aceptado")
                self.ultimo_valido[clave] = valor
        return dict(self.ultimo_valido)


def publicar(buzon, datos):
    """Deja en el buzon solo el snapshot mas reciente (descarta el anterior si no se consumio)."""
    while True:
        try:
            buzon.put_nowait(datos)
            return
        except queue.Full:
            try:
                buzon.get_nowait()
            except queue.Empty:
                pass


class HiloLector(threading.Thread):
    """Productor: relee el archivo periodicamente sin espera activa (Event.wait)."""

    def __init__(self, lector, intervalo_s, buzon):
        super().__init__(name=COMPONENTE, daemon=True)
        self.lector = lector
        self.intervalo_s = intervalo_s
        self.buzon = buzon
        self._detener = threading.Event()

    def run(self):
        while not self._detener.is_set():
            try:
                datos = self.lector.leer()
                if datos is not None:
                    publicar(self.buzon, datos)
            except Exception as error:  # un fallo inesperado no debe matar al lector
                self.lector.bitacora.error(COMPONENTE, "error_inesperado", f"{type(error).__name__}: {error}")
            self._detener.wait(self.intervalo_s)

    def detener(self, espera_s=2.0):
        self._detener.set()
        self.join(espera_s)


class Consumidor:
    """Lado de la interfaz: toma el ultimo snapshot y lo aplica a los controles."""

    def __init__(self, buzon, tablero):
        self.buzon = buzon
        self.tablero = tablero
        self.aplicado = {}
        self.snapshots = 0

    def __call__(self):
        try:
            datos = self.buzon.get_nowait()
        except queue.Empty:
            return False
        self.snapshots += 1
        for clave, valor in datos.items():
            if self.aplicado.get(clave) != valor:
                self.tablero.ajustar(CLAVES[clave][0], valor)
                self.aplicado[clave] = valor
        return True
