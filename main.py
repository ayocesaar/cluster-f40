"""Punto de entrada del cluster de instrumentos simulado del Ferrari F40 (1987).

Por defecto los valores llegan del archivo externo datos/vehiculo.conf (rutas,
intervalos y rangos en config/cluster.ini); con --manual se usan los controles
de la ventana. Los eventos van a logs/eventos.log y los errores a
logs/errores.log. El kilometraje del odometro se conserva en datos/odometro.txt."""

import argparse
import queue
import signal
import tkinter as tk

from logic.estado import EstadoCluster
from logic.reloj import RelojReal
from sistema import config as configuracion
from sistema import odometro_archivo
from sistema.bitacora import Bitacora
from sistema.lector import Consumidor, HiloLector, Lector
from sistema.monitor import MonitorEventos
from ui.tablero import Tablero


class Aplicacion:
    """Arma los componentes y los conecta; no contiene reglas de negocio."""

    def __init__(self, raiz, manual=False, ruta_config=None, proyecto=None):
        self.raiz = raiz
        self.cfg = configuracion.cargar(ruta_config, raiz=proyecto or configuracion.RAIZ)
        try:
            self.bitacora = Bitacora(self.cfg.dir_logs, self.cfg.max_bytes, self.cfg.respaldos)
        except OSError as error:
            # Una ruta de bitacoras inutilizable (por ejemplo, un archivo) no impide arrancar (DEF-09).
            self.cfg.errores.append(("logs_invalido", f"logs={self.cfg.relativa(self.cfg.dir_logs)} "
                                                      f"{type(error).__name__}; se usa logs/"))
            self.cfg.dir_logs = self.cfg.raiz / "logs"
            self.bitacora = Bitacora(self.cfg.dir_logs, self.cfg.max_bytes, self.cfg.respaldos)
        for evento, detalle in self.cfg.errores:
            self.bitacora.error("configuracion", evento, detalle)
        modo = "manual" if manual else f"archivo={self.cfg.relativa(self.cfg.archivo_datos)}"
        self.bitacora.info("sistema", "inicio", f"modo={modo} lectura_ms={self.cfg.lectura_ms} refresco_ms={self.cfg.refresco_ms}")

        # Elemento 11: el kilometraje se recupera del archivo antes de crear el estado.
        km, aviso = odometro_archivo.cargar(self.cfg.archivo_odometro, self.bitacora)
        self.estado = EstadoCluster(RelojReal(), odometro_km=km)
        self.tablero = Tablero(raiz, self.estado)
        self.tablero.periodo_ms = self.cfg.refresco_ms
        self._candado = odometro_archivo.Candado(self.cfg.archivo_odometro)
        if not self._candado.adquirir():
            # Otra ventana usa la misma carpeta: esta no guarda el kilometraje (DEF-08).
            self.bitacora.error("odometro", "odometro_en_uso",
                                f"archivo={self.cfg.archivo_odometro.name} esta ventana no guardara el kilometraje")
            aviso = "Odometro en uso por otra ventana: esta no guardara el kilometraje"
        if aviso:
            self.tablero.avisar(aviso)
        self._km_guardado = round(km, 3)
        self._id_guardado = raiz.after(self.cfg.guardar_cada_s * 1000, self._guardar_periodico)
        self.monitor = MonitorEventos(self.bitacora)
        self.tablero.despues_del_tick = self.monitor.revisar
        raiz.report_callback_exception = self._error_interfaz
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.hilo = None
        if not manual:
            buzon = queue.Queue(maxsize=1)
            self.lector = Lector(self.cfg.archivo_datos, self.cfg.rangos, self.bitacora)
            self.hilo = HiloLector(self.lector, self.cfg.lectura_ms / 1000, buzon)
            self.tablero.antes_del_tick = Consumidor(buzon, self.tablero, lector=self.lector)
            self.tablero.modo_externo(self.cfg.relativa(self.cfg.archivo_datos))
            self.hilo.start()

    def _error_interfaz(self, tipo, valor, _traza):
        """Un error dentro de la interfaz se registra y la aplicacion sigue."""
        self.bitacora.error("interfaz", "error_de_ejecucion", f"{tipo.__name__}: {valor}")

    def guardar_odometro(self):
        """Guarda el kilometraje si cambio desde la ultima vez; un fallo se registra y no detiene nada."""
        km = self.estado.odometro.km
        if not self._candado.adquirido or round(km, 3) == self._km_guardado:
            return False
        try:
            odometro_archivo.guardar(self.cfg.archivo_odometro, km)
        except (OSError, ValueError) as error:
            self.bitacora.error("odometro", "odometro_no_guardado", f"{type(error).__name__}: {error}")
            return False
        self._km_guardado = round(km, 3)
        self.bitacora.info("odometro", "odometro_guardado", f"km={km:.3f} resultado=aceptado")
        return True

    def _guardar_periodico(self):
        self.guardar_odometro()
        self._id_guardado = self.raiz.after(self.cfg.guardar_cada_s * 1000, self._guardar_periodico)

    def cerrar(self):
        if getattr(self, "_cerrado", False):   # una senal y el boton de cerrar pueden coincidir
            return
        self._cerrado = True
        self.tablero.detener()
        self.raiz.after_cancel(self._id_guardado)
        if self.hilo is not None:
            self.hilo.detener()
        self.guardar_odometro()
        self._candado.liberar()
        c = self.bitacora.contadores
        self.bitacora.info("sistema", "fin", f"info={c['INFO']} warn={c['WARN']} error={c['ERROR']}")
        self.bitacora.cerrar()
        self.raiz.destroy()


def instalar_senales(app):
    """SIGTERM (kill PID) y SIGINT (Ctrl+C) producen un cierre ordenado (tema 3.2, DEF-15).

    Sin esto, la accion por defecto de SIGTERM terminaba el proceso sin guardar el
    kilometraje ni registrar 'sistema fin'. El manejador solo agenda el cierre en el
    hilo de Tkinter: la interfaz no es segura entre hilos ni dentro de un manejador."""
    def manejar(numero, _marco):
        app.bitacora.info("sistema", "senal_recibida", f"{signal.Signals(numero).name} cierre ordenado")
        app.raiz.after(0, app.cerrar)
    return {senal: signal.signal(senal, manejar) for senal in (signal.SIGTERM, signal.SIGINT)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cluster de instrumentos simulado del Ferrari F40 (1987)")
    parser.add_argument("--manual", action="store_true", help="usar los controles de la ventana en lugar del archivo de datos")
    parser.add_argument("--config", default=None, help="ruta del archivo de configuracion (por defecto config/cluster.ini)")
    parser.add_argument("--salir-tras-ms", type=int, default=None, help="cierra la ventana tras N ms (prueba de humo)")
    parser.add_argument("--proyecto", default=None, help="carpeta del proyecto (datos/, config/, logs/); por defecto esta")
    args = parser.parse_args(argv)

    raiz = tk.Tk()
    app = Aplicacion(raiz, manual=args.manual, ruta_config=args.config, proyecto=args.proyecto)
    previos = instalar_senales(app)
    if args.salir_tras_ms is not None:
        raiz.after(args.salir_tras_ms, app.cerrar)
    try:
        raiz.mainloop()
    finally:
        for senal, manejador in previos.items():
            signal.signal(senal, manejador)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
