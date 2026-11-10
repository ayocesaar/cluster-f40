"""Bitacoras del sistema: logs/eventos.log (INFO y WARN) y logs/errores.log (ERROR).

Cada linea permite reconstruir lo ocurrido, con el formato de la guia:

    2026-11-20T18:42:15-06:00 INFO  lector_datos valor_actualizado velocidad=72 resultado=aceptado

Los dos archivos rotan por tamano (max_bytes y un numero fijo de respaldos), asi
que el espacio total queda acotado aunque la aplicacion corra mucho tiempo. El
modulo logging usa candados internos: el hilo lector y la interfaz pueden
registrar al mismo tiempo sin mezclar lineas."""

import datetime
import logging
import logging.handlers
import os
import pathlib
import threading

PERMISO_ARCHIVO = 0o640
PERMISO_DIRECTORIO = 0o750
NIVELES = {"WARNING": "WARN"}


class _Formato(logging.Formatter):
    def format(self, registro):
        fecha = datetime.datetime.fromtimestamp(registro.created).astimezone().isoformat(timespec="seconds")
        nivel = NIVELES.get(registro.levelname, registro.levelname)
        return f"{fecha} {nivel:<5} {registro.componente} {registro.evento} {registro.getMessage()}".rstrip()


class _HastaNivel(logging.Filter):
    """Deja pasar solo registros por debajo de un nivel (eventos.log no lleva errores)."""

    def __init__(self, nivel):
        super().__init__()
        self.nivel = nivel

    def filter(self, registro):
        return registro.levelno < self.nivel


class _ArchivoRotativo(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler que deja cada archivo nuevo con permisos 640 (minimo privilegio)."""

    def _open(self):
        flujo = super()._open()
        if os.name == "posix":
            os.chmod(self.baseFilename, PERMISO_ARCHIVO)
        return flujo


class Bitacora:
    def __init__(self, dir_logs, max_bytes=262_144, respaldos=3):
        self.dir_logs = pathlib.Path(dir_logs)
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.dir_logs, PERMISO_DIRECTORIO)
        self.ruta_eventos = self.dir_logs / "eventos.log"
        self.ruta_errores = self.dir_logs / "errores.log"

        self._logger = logging.getLogger(f"cluster_f40.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        formato = _Formato()
        eventos = _ArchivoRotativo(self.ruta_eventos, maxBytes=max_bytes, backupCount=respaldos, encoding="utf-8")
        eventos.setLevel(logging.INFO)
        eventos.addFilter(_HastaNivel(logging.ERROR))
        errores = _ArchivoRotativo(self.ruta_errores, maxBytes=max_bytes, backupCount=respaldos, encoding="utf-8")
        errores.setLevel(logging.ERROR)
        for manejador in (eventos, errores):
            manejador.setFormatter(formato)
            self._logger.addHandler(manejador)
        self.contadores = {"INFO": 0, "WARN": 0, "ERROR": 0}
        self._candado = threading.Lock()

    def _registrar(self, nivel, nombre, componente, evento, detalle):
        with self._candado:  # el hilo lector y la interfaz cuentan eventos al mismo tiempo
            self.contadores[nombre] += 1
        self._logger.log(nivel, "%s", detalle, extra={"componente": componente, "evento": evento})

    def info(self, componente, evento, detalle=""):
        self._registrar(logging.INFO, "INFO", componente, evento, detalle)

    def warn(self, componente, evento, detalle=""):
        self._registrar(logging.WARNING, "WARN", componente, evento, detalle)

    def error(self, componente, evento, detalle=""):
        self._registrar(logging.ERROR, "ERROR", componente, evento, detalle)

    def cerrar(self):
        for manejador in list(self._logger.handlers):
            manejador.close()
            self._logger.removeHandler(manejador)
