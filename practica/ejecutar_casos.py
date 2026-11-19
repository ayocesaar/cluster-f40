"""Ejecuta de verdad los casos de la practica en clase (odometro) con la aplicacion completa.

Cada caso crea un proyecto temporal con su datos/vehiculo.conf (y datos/odometro.txt
si el caso lo pide), abre la aplicacion en modo archivo, la deja correr el tiempo
del caso, toma una captura y lee lo que realmente muestra el tablero y las
bitacoras. El veredicto se calcula aqui mismo a partir de lo observado.

Uso en la VM, desde la raiz del proyecto:
  xvfb-run -a -s "-screen 0 1280x1024x24" python practica/ejecutar_casos.py --version despues
  xvfb-run -a -s "-screen 0 1280x1024x24" python practica/ejecutar_casos.py --version antes --codigo /tmp/v749d580

Escribe practica/evidencia_<version>/: captura, bitacoras y odometro.txt final de
cada caso, resultado_ejecucion.txt con el detalle y resumen.txt
(caso|duracion_s|esperado|obtenido|estado), que lee el Documento de Pruebas."""

import argparse
import gc
import pathlib
import re
import shutil
import sys
import tempfile
import time
import tkinter as tk

AQUI = pathlib.Path(__file__).resolve().parent
BASE = ("motor=1\nvelocidad={v}\nrpm=3000\npresion_aceite=5\ntemp_agua=90\npresion_turbo=0.8\n"
        "direccional=off\nluces_altas=0\nemergencia=0\nfalla_frenos=0\n")

# (caso, archivo, velocidad, segundos, odometro.txt inicial, linea extra en vehiculo.conf, esperado)
CASOS = (
    ("CP-ODO-01", "CP-ODO-01_normal_30s", 120, 30, "62\n", "",
     "000062 -> 000063 (1 km) e INFO odometro_actualizado"),
    ("CP-ODO-01 v2", "CP-ODO-01_v2_normal_45s", 120, 45, "62\n", "",
     "000062 -> 000063 (1.5 km) e INFO odometro_actualizado"),
    ("CP-ODO-02", "CP-ODO-02_limite_10s", 360, 10, "999999\n", "",
     "999999 -> 000000 (1 km) y la vuelta registrada"),
    ("CP-ODO-02 v2", "CP-ODO-02_v2_limite_15s", 360, 15, "999999\n", "",
     "999999 -> 000000 (1.5 km) y la vuelta registrada"),
    ("CP-ODO-03", "CP-ODO-03_archivo_corrupto", 120, 5, "abc\n", "",
     "000000, aviso en pantalla y ERROR odometro_invalido"),
    ("SONDA", "SONDA_odometro_en_vehiculo_conf", 360, 3, None, "odometro=999999\n",
     "odometro= rechazado por el lector; el resto se aplica"),
)


def proyecto(velocidad, odometro, extra):
    raiz = pathlib.Path(tempfile.mkdtemp(prefix="odo_"))
    (raiz / "config").mkdir()
    (raiz / "datos").mkdir()
    (raiz / "config" / "cluster.ini").write_text("[intervalos]\nlectura_ms = 100\n", encoding="utf-8")
    (raiz / "datos" / "vehiculo.conf").write_text(BASE.format(v=velocidad) + extra, encoding="utf-8")
    if odometro is not None:
        (raiz / "datos" / "odometro.txt").write_text(odometro, encoding="utf-8")
    return raiz


def veredicto(caso, existe, pantalla, eventos, errores, aviso):
    if caso == "SONDA":
        if "clave_no_permitida" in errores and "clave=odometro" in errores:
            return "Aprobado"
        return "Rechazado como clave_desconocida" if "clave_desconocida" in errores else "Fallido"
    if not existe:
        # Sin odometro el caso 03 ni siquiera puede ocurrir (nunca se lee odometro.txt).
        return "Bloqueado (DEF-03)" if caso.startswith("CP-ODO-03") else "Fallido"
    if caso.startswith("CP-ODO-01"):
        ok = pantalla == "000063" and "odometro_actualizado km=000063" in eventos
    elif caso.startswith("CP-ODO-02"):
        ok = pantalla == "000000" and "vuelta_a_cero" in eventos
    else:
        ok = pantalla == "000000" and "archivo invalido" in aviso and "odometro_invalido" in errores
    return "Aprobado" if ok else "Fallido"


def correr(principal, salida, caso, archivo, velocidad, segundos, odometro, extra, esperado):
    from PIL import ImageGrab

    raiz = proyecto(velocidad, odometro, extra)
    gc.collect()  # libera aqui, en el hilo principal, los objetos de Tk de la corrida anterior
    tk_raiz = tk.Tk()
    app = principal.Aplicacion(tk_raiz, ruta_config=raiz / "config" / "cluster.ini", proyecto=raiz)
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        tk_raiz.update()
        time.sleep(0.02)
    x, y = tk_raiz.winfo_rootx(), tk_raiz.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + tk_raiz.winfo_width(), y + tk_raiz.winfo_height())).save(salida / f"{archivo}.png")

    canvas = app.tablero.canvas
    textos = [canvas.itemcget(i, "text") for i in canvas.find_all() if canvas.type(i) == "text"]
    seis = [t.strip() for t in textos if re.fullmatch(r"\d{6}", t.strip())]
    existe = hasattr(app.estado, "odometro")
    km = app.estado.odometro.km if existe else None
    aviso_widget = getattr(app.tablero, "aviso", None)
    aviso = aviso_widget.cget("text") if aviso_widget is not None else ""
    velocidad_aplicada = app.estado.velocidad
    app.cerrar()

    logs = raiz / "logs"
    eventos = (logs / "eventos.log").read_text(encoding="utf-8")
    errores = (logs / "errores.log").read_text(encoding="utf-8") if (logs / "errores.log").exists() else ""
    (salida / f"{archivo}_eventos.log").write_text(eventos, encoding="utf-8")
    (salida / f"{archivo}_errores.log").write_text(errores, encoding="utf-8")
    final = raiz / "datos" / "odometro.txt"
    guardado = final.read_text(encoding="utf-8").strip() if final.exists() else "(no existe)"
    shutil.rmtree(raiz, ignore_errors=True)

    pantalla = seis[0] if seis else ""
    estado = veredicto(caso, existe, pantalla, eventos, errores, aviso)
    lineas_odo = [linea for linea in (eventos + errores).splitlines() if "odometr" in linea.lower()]
    if caso == "SONDA":
        rechazo = [linea for linea in errores.splitlines() if "clave=" in linea and "odometro" in linea]
        obtenido = (f"velocidad aplicada {velocidad_aplicada:g} km/h; lector: "
                    + (re.sub(r"^\S+ ", "", rechazo[0]) if rechazo else "sin rechazo registrado"))
    else:
        obtenido = f"tablero {pantalla or 'sin contador de 6 digitos'}"
        if km is not None:
            obtenido += f" (km internos {km:.3f})"
        if aviso:
            obtenido += f"; aviso: {aviso}"
        obtenido += f"; {len(lineas_odo)} lineas de bitacora del odometro"
    detalle = [f"== {caso} ({archivo}) ==", f"segundos ejecutados: {segundos}",
               f"velocidad aplicada: {velocidad_aplicada:g} km/h", f"esperado: {esperado}",
               f"textos del tablero con 6 digitos: {seis or 'ninguno'}",
               f"km internos: {'no existe el odometro' if km is None else f'{km:.6f}'}",
               f"aviso en pantalla: {aviso or '(ninguno)'}", f"odometro.txt al cerrar: {guardado}",
               f"lineas de bitacora que mencionan el odometro: {len(lineas_odo)}"]
    detalle += [f"  {linea}" for linea in lineas_odo]
    detalle += [f"estado: {estado}", ""]
    print("\n".join(detalle), flush=True)
    return detalle, "|".join((caso, str(segundos), esperado, obtenido.replace("|", "/"), estado))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Casos de la practica del odometro")
    parser.add_argument("--version", choices=("antes", "despues"), required=True)
    parser.add_argument("--codigo", default=str(AQUI.parent), help="raiz del codigo a probar")
    args = parser.parse_args(argv)
    codigo = pathlib.Path(args.codigo).resolve()
    sys.path.insert(0, str(codigo))
    import main as principal

    salida = AQUI / f"evidencia_{args.version}"
    salida.mkdir(parents=True, exist_ok=True)
    commit = (codigo / ".git").exists() and __import__("subprocess").run(
        ["git", "-C", str(codigo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    reporte = [f"Casos de la practica del odometro - version {args.version} (codigo: {commit or codigo})",
               f"fecha: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}", ""]
    resumen = []
    for c in CASOS:
        detalle, fila = correr(principal, salida, *c)
        reporte += detalle
        resumen.append(fila)
    (salida / "resultado_ejecucion.txt").write_text("\n".join(reporte), encoding="utf-8")
    (salida / "resumen.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
    print(f"OK {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
