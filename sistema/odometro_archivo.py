"""Persistencia del odometro en datos/odometro.txt, con un respaldo .bak.

El kilometraje debe sobrevivir al cierre de la aplicacion. Se guarda con
escritura atomica (temporal + os.replace) primero en el archivo principal y
luego en el respaldo; asi, si algo se interrumpe, al menos uno queda completo.
Al iniciar se usa el principal si es valido, si no el respaldo, y si ninguno
sirve se empieza en 000000 registrando el error. Un archivo que cualquiera puede
escribir se rechaza: nadie mas que el dueno debe poder alterar el kilometraje."""

import os
import pathlib
import re

from logic.odometro import MAXIMO_KM
from sistema.lector import escribir_texto_atomico

COMPONENTE = "odometro"
TAMANO_MAXIMO = 64
_FORMATO = re.compile(r"\d{1,6}(\.\d{1,6})?")


class OdometroInvalido(ValueError):
    """El archivo existe pero su contenido o sus permisos no son aceptables."""


def respaldo(ruta):
    ruta = pathlib.Path(ruta)
    return ruta.with_name(ruta.name + ".bak")


def leer_km(ruta):
    """Lee y valida un archivo de odometro. FileNotFoundError si no existe."""
    ruta = pathlib.Path(ruta)
    info = ruta.stat()
    if os.name == "posix" and info.st_mode & 0o002:
        raise OdometroInvalido(f"permisos inseguros modo={oct(info.st_mode & 0o777)}")
    if info.st_size > TAMANO_MAXIMO:
        raise OdometroInvalido(f"archivo demasiado grande ({info.st_size} bytes)")
    try:
        texto = ruta.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        raise OdometroInvalido("codificacion no valida (se espera UTF-8)") from None
    except PermissionError:
        raise OdometroInvalido("sin permiso de lectura") from None
    if not _FORMATO.fullmatch(texto):
        raise OdometroInvalido(f'contenido="{texto[:20]}" (se espera un numero de km, por ejemplo 62.5)')
    return float(texto)


def cargar(ruta, bitacora):
    """Devuelve (km, aviso). aviso es None o un texto para mostrar en pantalla."""
    ruta = pathlib.Path(ruta)
    if not ruta.exists() and not respaldo(ruta).exists():
        bitacora.info(COMPONENTE, "odometro_nuevo", "sin archivo previo: se inicia en 000000")
        return 0.0, None
    for candidato in (ruta, respaldo(ruta)):
        try:
            km = leer_km(candidato)
        except FileNotFoundError:
            if candidato == ruta:
                bitacora.error(COMPONENTE, "odometro_inexistente", f"archivo={candidato.name} resultado=rechazado")
            continue
        except OdometroInvalido as error:
            bitacora.error(COMPONENTE, "odometro_invalido", f"archivo={candidato.name} {error} resultado=rechazado")
            continue
        if candidato == ruta:
            bitacora.info(COMPONENTE, "odometro_cargado", f"km={km:.3f} resultado=aceptado")
            return km, None
        bitacora.warn(COMPONENTE, "odometro_restaurado", f"desde {candidato.name} km={km:.3f}")
        return km, f"Odometro restaurado del respaldo: {int(km):06d} km"
    return 0.0, "Odometro: archivo invalido, se inicio en 000000"


def guardar(ruta, km):
    """Guarda el kilometraje en el principal y en el respaldo, cada uno de forma atomica."""
    if not 0 <= km < MAXIMO_KM:
        raise ValueError(f"km fuera de rango: {km}")
    texto = f"{km:.6f}\n"
    escribir_texto_atomico(ruta, texto)
    escribir_texto_atomico(respaldo(ruta), texto)
