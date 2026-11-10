"""Genera los ejemplos de bitacoras que pide la guia (entregable 7): una
ejecucion exitosa y una con errores. Usa los componentes reales (lector,
estado, monitor y bitacora) con el reloj simulado, sin ventana.

Uso: python tools/demo_bitacoras.py   ->  docs/evidencias/bitacoras/{exitosa,con_errores}/"""

import os
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from logic.estado import EstadoCluster  # noqa: E402
from logic.reloj import RelojSimulado  # noqa: E402
from sistema.bitacora import Bitacora  # noqa: E402
from sistema.config import RANGOS_ESPECIFICACION  # noqa: E402
from sistema.lector import CLAVES, VALORES_INICIALES, Lector, escribir_atomico, escribir_texto_atomico  # noqa: E402
from sistema.monitor import MonitorEventos  # noqa: E402

DESTINO = RAIZ / "docs" / "evidencias" / "bitacoras"


class Escenario:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        shutil.rmtree(carpeta, ignore_errors=True)
        (carpeta / "datos").mkdir(parents=True)
        self.datos = carpeta / "datos" / "vehiculo.conf"
        self.bitacora = Bitacora(carpeta, max_bytes=262144, respaldos=1)
        self.reloj = RelojSimulado()
        self.estado = EstadoCluster(self.reloj)
        self.lector = Lector(self.datos, dict(RANGOS_ESPECIFICACION), self.bitacora)
        self.monitor = MonitorEventos(self.bitacora)
        self.valores = dict(VALORES_INICIALES)
        self.bitacora.info("sistema", "inicio", f"modo=archivo={self.datos.name}")

    def escribir(self, **cambios):
        self.valores.update(cambios)
        escribir_atomico(self.datos, self.valores)

    def correr(self, ms):
        for _ in range(ms // 100):
            snapshot = self.lector.leer()
            if snapshot:
                for clave, valor in snapshot.items():
                    getattr(self.estado, CLAVES[clave][0])(valor)
            self.reloj.avanzar(100)
            self.estado.tick()
            self.monitor.revisar(self.estado)

    def cerrar(self):
        c = self.bitacora.contadores
        self.bitacora.info("sistema", "fin", f"info={c['INFO']} warn={c['WARN']} error={c['ERROR']}")
        self.bitacora.cerrar()
        shutil.rmtree(self.carpeta / "datos")


def exitosa():
    e = Escenario(DESTINO / "exitosa")
    e.escribir()
    e.correr(300)
    e.escribir(motor=True, presion_aceite=5.0, temp_agua=85.0)
    e.correr(600)
    e.escribir(velocidad=72.0, rpm=2450, presion_turbo=0.8)
    e.correr(600)
    e.escribir(velocidad=180.0, rpm=8100, presion_turbo=1.6, luces_altas=True)
    e.correr(600)
    e.escribir(rpm=6000, presion_turbo=0.9, direccional="IZQ")
    e.correr(1000)
    e.escribir(direccional="OFF", falla_frenos=True)
    e.correr(900)
    e.escribir(falla_frenos=False, velocidad=0.0, rpm=0, motor=False)
    e.correr(300)
    e.cerrar()


def con_errores():
    e = Escenario(DESTINO / "con_errores")
    e.correr(300)                                         # el archivo todavia no existe
    e.escribir(motor=True, presion_aceite=5.0)
    e.correr(300)
    texto = e.datos.read_text(encoding="utf-8")
    escribir_texto_atomico(e.datos, texto.replace("temp_agua=40.0", "temp_agua=abc"))
    e.correr(300)                                         # formato incorrecto
    escribir_texto_atomico(e.datos, texto.replace("velocidad=0.0", "velocidad=500"))
    e.correr(300)                                         # fuera de rango
    escribir_texto_atomico(e.datos, "\n".join(l for l in texto.splitlines() if not l.startswith("rpm=")) + "\n")
    e.correr(300)                                         # clave faltante
    if os.name == "posix":
        os.chmod(e.datos, 0o666)
        e.correr(300)                                     # permisos inseguros
        os.chmod(e.datos, 0o640)
    e.escribir(presion_aceite=0.4)
    e.correr(1300)                                        # advertencia critica: testigo 9
    e.escribir(presion_aceite=5.0)
    e.correr(1300)                                        # recuperacion
    e.cerrar()


def main():
    exitosa()
    con_errores()
    for carpeta in ("exitosa", "con_errores"):
        for nombre in ("eventos.log", "errores.log"):
            ruta = DESTINO / carpeta / nombre
            lineas = len(ruta.read_text(encoding="utf-8").splitlines()) if ruta.exists() else 0
            print(f"{carpeta}/{nombre}: {lineas} lineas")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
