"""Punto de entrada del cluster de instrumentos simulado del Ferrari F40 (1987).

Por defecto los valores llegan del archivo externo datos/vehiculo.conf (rutas,
intervalos y rangos en config/cluster.ini); con --manual se usan los controles
de la ventana. Los eventos van a logs/eventos.log y los errores a
logs/errores.log."""

import argparse
import queue
import tkinter as tk

from logic.estado import EstadoCluster
from logic.reloj import RelojReal
from sistema import config as configuracion
from sistema.bitacora import Bitacora
from sistema.lector import Consumidor, HiloLector, Lector
from sistema.monitor import MonitorEventos
from ui.tablero import Tablero


class Aplicacion:
    """Arma los componentes y los conecta; no contiene reglas de negocio."""

    def __init__(self, raiz, manual=False, ruta_config=None, proyecto=None):
        self.raiz = raiz
        self.cfg = configuracion.cargar(ruta_config, raiz=proyecto or configuracion.RAIZ)
        self.bitacora = Bitacora(self.cfg.dir_logs, self.cfg.max_bytes, self.cfg.respaldos)
        for evento, detalle in self.cfg.errores:
            self.bitacora.error("configuracion", evento, detalle)
        modo = "manual" if manual else f"archivo={self.cfg.relativa(self.cfg.archivo_datos)}"
        self.bitacora.info("sistema", "inicio", f"modo={modo} lectura_ms={self.cfg.lectura_ms} refresco_ms={self.cfg.refresco_ms}")

        self.estado = EstadoCluster(RelojReal())
        self.tablero = Tablero(raiz, self.estado)
        self.tablero.periodo_ms = self.cfg.refresco_ms
        self.monitor = MonitorEventos(self.bitacora)
        self.tablero.despues_del_tick = self.monitor.revisar
        raiz.report_callback_exception = self._error_interfaz
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.hilo = None
        if not manual:
            buzon = queue.Queue(maxsize=1)
            self.lector = Lector(self.cfg.archivo_datos, self.cfg.rangos, self.bitacora)
            self.hilo = HiloLector(self.lector, self.cfg.lectura_ms / 1000, buzon)
            self.tablero.antes_del_tick = Consumidor(buzon, self.tablero)
            self.tablero.modo_externo(self.cfg.relativa(self.cfg.archivo_datos))
            self.hilo.start()

    def _error_interfaz(self, tipo, valor, _traza):
        """Un error dentro de la interfaz se registra y la aplicacion sigue."""
        self.bitacora.error("interfaz", "error_de_ejecucion", f"{tipo.__name__}: {valor}")

    def cerrar(self):
        self.tablero.detener()
        if self.hilo is not None:
            self.hilo.detener()
        c = self.bitacora.contadores
        self.bitacora.info("sistema", "fin", f"info={c['INFO']} warn={c['WARN']} error={c['ERROR']}")
        self.bitacora.cerrar()
        self.raiz.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cluster de instrumentos simulado del Ferrari F40 (1987)")
    parser.add_argument("--manual", action="store_true", help="usar los controles de la ventana en lugar del archivo de datos")
    parser.add_argument("--config", default=None, help="ruta del archivo de configuracion (por defecto config/cluster.ini)")
    parser.add_argument("--salir-tras-ms", type=int, default=None, help="cierra la ventana tras N ms (prueba de humo)")
    args = parser.parse_args(argv)

    raiz = tk.Tk()
    app = Aplicacion(raiz, manual=args.manual, ruta_config=args.config)
    if args.salir_tras_ms is not None:
        raiz.after(args.salir_tras_ms, app.cerrar)
    raiz.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
