"""Configuracion del cluster: rutas, intervalos, rangos y opciones de bitacora.

Se lee de config/cluster.ini con configparser, sin recompilar nada. Las rutas
son relativas a la raiz del proyecto y no pueden salir de ella, para que el
proyecto funcione en cualquier equipo. Si el archivo falta o un valor es
invalido se usa el valor por defecto y el problema queda en `errores`, para
que quien carga la configuracion lo registre: la aplicacion nunca se detiene
por la configuracion."""

import configparser
import pathlib
from dataclasses import dataclass, field

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RUTA_POR_DEFECTO = RAIZ / "config" / "cluster.ini"

# Rangos de la especificacion: el archivo de configuracion puede estrecharlos,
# nunca ampliarlos (EstadoCluster rechaza lo que quede fuera de estos).
RANGOS_ESPECIFICACION = {
    "velocidad": (0.0, 360.0),
    "rpm": (0.0, 9000.0),
    "presion_aceite": (0.0, 10.0),
    "temp_agua": (40.0, 130.0),
    "presion_turbo": (0.0, 2.0),
}

# (seccion, clave, minimo, maximo, valor por defecto)
ENTEROS = (
    ("intervalos", "lectura_ms", 10, 5000, 100),
    ("intervalos", "refresco_ms", 10, 1000, 50),
    ("bitacora", "max_bytes", 1024, 10_485_760, 262_144),
    ("bitacora", "respaldos", 1, 10, 3),
)


@dataclass
class Configuracion:
    raiz: pathlib.Path
    archivo_datos: pathlib.Path
    dir_logs: pathlib.Path
    lectura_ms: int = 100
    refresco_ms: int = 50
    max_bytes: int = 262_144
    respaldos: int = 3
    rangos: dict = field(default_factory=lambda: dict(RANGOS_ESPECIFICACION))
    errores: list = field(default_factory=list)

    def relativa(self, ruta):
        """Ruta legible relativa a la raiz, para mensajes y bitacoras."""
        try:
            return ruta.relative_to(self.raiz).as_posix()
        except ValueError:
            return ruta.name


def _ruta_segura(raiz, texto, por_defecto, nombre, errores):
    """Acepta solo rutas relativas que queden dentro de la raiz del proyecto."""
    candidata = pathlib.PurePath(texto)
    resuelta = (raiz / texto).resolve()
    if candidata.is_absolute() or not resuelta.is_relative_to(raiz.resolve()):
        errores.append(("ruta_rechazada", f"{nombre}={texto!r} (debe ser relativa al proyecto)"))
        return raiz / por_defecto
    return raiz / texto


def cargar(ruta=None, raiz=RAIZ):
    """Carga la configuracion; nunca lanza excepcion por datos del archivo."""
    raiz = pathlib.Path(raiz)
    ruta = pathlib.Path(ruta) if ruta else raiz / "config" / "cluster.ini"
    errores = []
    ini = configparser.ConfigParser()
    if not ruta.is_file():
        errores.append(("archivo_inexistente", f"ruta={ruta.name} (se usan valores por defecto)"))
    else:
        try:
            ini.read(ruta, encoding="utf-8")
        except (configparser.Error, UnicodeDecodeError) as error:
            errores.append(("configuracion_invalida", f"{type(error).__name__} (se usan valores por defecto)"))
            ini = configparser.ConfigParser()

    datos = _ruta_segura(raiz, ini.get("rutas", "datos", fallback="datos/vehiculo.conf"),
                         "datos/vehiculo.conf", "datos", errores)
    logs = _ruta_segura(raiz, ini.get("rutas", "logs", fallback="logs"), "logs", "logs", errores)
    cfg = Configuracion(raiz=raiz, archivo_datos=datos, dir_logs=logs, errores=errores)

    for seccion, clave, minimo, maximo, defecto in ENTEROS:
        texto = ini.get(seccion, clave, fallback=None)
        valor = defecto
        if texto is not None:
            try:
                valor = int(texto)
                if not minimo <= valor <= maximo:
                    raise ValueError
            except ValueError:
                errores.append(("valor_invalido", f"{seccion}.{clave}={texto!r} (rango {minimo}-{maximo}; se usa {defecto})"))
                valor = defecto
        setattr(cfg, clave, valor)

    for clave, (esp_min, esp_max) in RANGOS_ESPECIFICACION.items():
        texto = ini.get("rangos", clave, fallback=None)
        if texto is None:
            continue
        try:
            minimo, maximo = (float(p) for p in texto.split(","))
            if not esp_min <= minimo < maximo <= esp_max:
                raise ValueError
            cfg.rangos[clave] = (minimo, maximo)
        except ValueError:
            errores.append(("rango_invalido", f"rangos.{clave}={texto!r} (debe estar dentro de {esp_min:g}-{esp_max:g})"))
    return cfg
