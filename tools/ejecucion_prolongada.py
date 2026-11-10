"""Prueba P12 con metricas reales: ejecuta la aplicacion completa durante un
periodo definido mientras un proceso simulador escribe el archivo de datos.

Mide: intervalo real entre actualizaciones del tablero, datos procesados,
eventos y errores registrados, memoria (RSS) al inicio y al final, y el tamano
de las bitacoras antes y despues. Trabaja en una carpeta temporal para no
tocar los datos ni las bitacoras del proyecto.

Uso (en la VM): xvfb-run -a python tools/ejecucion_prolongada.py --duracion-s 60"""

import argparse
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tkinter as tk

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main as principal  # noqa: E402

CONFIG = """[rutas]
datos = datos/vehiculo.conf
logs = logs
[intervalos]
lectura_ms = 100
refresco_ms = 50
[bitacora]
max_bytes = 16384
respaldos = 2
"""


def memoria_kb():
    """RSS actual del proceso en KB (Linux: /proc; otros: pico de getrusage)."""
    estado = pathlib.Path("/proc/self/status")
    if estado.exists():
        for linea in estado.read_text().splitlines():
            if linea.startswith("VmRSS:"):
                return int(linea.split()[1])
    import resource  # pragma: no cover
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # pragma: no cover


def ps():
    """Salida de ps para este proceso (lista de argumentos, sin shell)."""
    if shutil.which("ps") is None:
        return "ps no disponible"
    resultado = subprocess.run(["ps", "-o", "pid,ppid,stat,%cpu,%mem,rss,vsz,cmd", "-p", str(os.getpid())],
                               capture_output=True, text=True, check=False)
    return resultado.stdout.strip()


def tamanos(dir_logs):
    return {a.name: a.stat().st_size for a in sorted(dir_logs.glob("*.log*"))}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ejecucion prolongada con metricas (P12)")
    parser.add_argument("--duracion-s", type=float, default=60.0)
    parser.add_argument("--salida", default=str(RAIZ / "docs" / "evidencias" / "metricas.txt"))
    args = parser.parse_args(argv)

    trabajo = pathlib.Path(tempfile.mkdtemp(prefix="cluster_p12_"))
    (trabajo / "config").mkdir()
    (trabajo / "datos").mkdir()
    (trabajo / "config" / "cluster.ini").write_text(CONFIG, encoding="utf-8")
    datos = trabajo / "datos" / "vehiculo.conf"
    shutil.copy(RAIZ / "datos" / "vehiculo.conf", datos)

    simulador = subprocess.Popen([sys.executable, str(RAIZ / "tools" / "simulador.py"), "--archivo", str(datos),
                                  "--periodo-ms", "100", "--duracion-s", str(args.duracion_s + 3)],
                                 stdout=subprocess.PIPE, text=True)
    raiz = tk.Tk()
    app = principal.Aplicacion(raiz, ruta_config=trabajo / "config" / "cluster.ini", proyecto=trabajo)
    marcas = []
    revisar = app.tablero.despues_del_tick

    def medir(estado):
        marcas.append(time.monotonic())
        revisar(estado)

    app.tablero.despues_del_tick = medir
    medidas = {}

    def tomar_inicio():
        medidas["rss_inicio"] = memoria_kb()
        medidas["ps_inicio"] = ps()
        medidas["logs_inicio"] = tamanos(app.cfg.dir_logs)
        medidas["eventos_inicio"] = dict(app.bitacora.contadores)

    def terminar():
        medidas["rss_fin"] = memoria_kb()
        medidas["ps_fin"] = ps()
        medidas["logs_fin"] = tamanos(app.cfg.dir_logs)
        medidas["eventos_fin"] = dict(app.bitacora.contadores)
        medidas["lecturas"] = app.lector.lecturas
        medidas["snapshots"] = app.tablero.antes_del_tick.snapshots
        app.cerrar()

    raiz.after(2000, tomar_inicio)                       # se mide despues de 2 s de arranque
    raiz.after(int(args.duracion_s * 1000), terminar)
    inicio = time.monotonic()
    raiz.mainloop()
    duracion = time.monotonic() - inicio
    simulador.terminate()
    salida_sim = simulador.communicate(timeout=10)[0].strip()

    intervalos = [(b - a) * 1000 for a, b in zip(marcas, marcas[1:])]
    errores_log = (trabajo / "logs" / "errores.log")
    lineas_eventos = sum(len(a.read_text(encoding="utf-8").splitlines()) for a in (trabajo / "logs").glob("eventos.log*"))
    lineas_errores = len(errores_log.read_text(encoding="utf-8").splitlines()) if errores_log.exists() else 0
    total_fin = sum(medidas["logs_fin"].values())
    limite = 3 * 16384

    reporte = [
        "Prueba P12 - ejecucion prolongada con metricas reales",
        f"Duracion medida: {duracion:.1f} s (solicitada {args.duracion_s:g} s)",
        "Configuracion: lectura cada 100 ms, refresco cada 50 ms, bitacoras de 16384 bytes con 2 respaldos",
        "Productor: proceso tools/simulador.py escribiendo el archivo de datos cada 100 ms (escritura atomica)",
        "",
        "Intervalo real de actualizacion del tablero (ms):",
        f"  ciclos={len(marcas)} promedio={statistics.mean(intervalos):.1f} mediana={statistics.median(intervalos):.1f} "
        f"p95={sorted(intervalos)[int(len(intervalos) * 0.95)]:.1f} maximo={max(intervalos):.1f}",
        "",
        "Datos procesados:",
        f"  lecturas completas del archivo={medidas['lecturas']} snapshots aplicados por la interfaz={medidas['snapshots']}",
        f"  {salida_sim}",
        f"  eventos registrados: INFO={medidas['eventos_fin']['INFO']} WARN={medidas['eventos_fin']['WARN']} "
        f"ERROR={medidas['eventos_fin']['ERROR']}",
        f"  lineas presentes en bitacoras: eventos={lineas_eventos} errores={lineas_errores} (las antiguas se descartan al rotar)",
        "",
        "Memoria (RSS):",
        f"  inicio={medidas['rss_inicio']} KB fin={medidas['rss_fin']} KB diferencia={medidas['rss_fin'] - medidas['rss_inicio']} KB",
        "",
        "Bitacoras (bytes):",
        f"  inicio={medidas['logs_inicio']}",
        f"  fin={medidas['logs_fin']}",
        f"  total final={total_fin} limite teorico={limite} acotado={'si' if total_fin <= limite + 1024 else 'NO'}",
        "",
        "ps al inicio:",
        medidas["ps_inicio"],
        "ps al final:",
        medidas["ps_fin"],
    ]
    pathlib.Path(args.salida).write_text("\n".join(reporte) + "\n", encoding="utf-8")
    shutil.rmtree(trabajo, ignore_errors=True)
    print("\n".join(reporte))
    return 0 if total_fin <= limite + 1024 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
