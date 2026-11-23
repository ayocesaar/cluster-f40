"""Caos con la aplicacion real (no forma parte de la suite).
Uso (desde la raiz del proyecto): xvfb-run -a python tools/qa/caos.py"""
import gc
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk

sys.path.insert(0, os.getcwd())
import main as principal  # noqa: E402
from sistema.lector import escribir_texto_atomico  # noqa: E402

trabajo = pathlib.Path(tempfile.mkdtemp(prefix="caos_"))
(trabajo / "config").mkdir()
(trabajo / "datos").mkdir()
(trabajo / "config" / "cluster.ini").write_text("[intervalos]\nlectura_ms = 20\nrefresco_ms = 10\n", encoding="utf-8")
datos = trabajo / "datos" / "vehiculo.conf"
BASE = "motor=1\nvelocidad={v}\nrpm={r}\npresion_aceite={a}\ntemp_agua={t}\npresion_turbo={b}\ndireccional={d}\nluces_altas=0\nemergencia={e}\nfalla_frenos={f}\n"
escribir_texto_atomico(datos, BASE.format(v=100, r=3000, a=5, t=90, b=0.5, d="off", e=0, f=0))
alto = threading.Event()
acciones = {}


def caos():
    random.seed(11)
    while not alto.is_set():
        op = random.choice(["valido", "valido", "valido", "basura", "borrar", "666", "000", "grande", "fuera", "vacio"])
        acciones[op] = acciones.get(op, 0) + 1
        try:
            if op == "valido":
                escribir_texto_atomico(datos, BASE.format(
                    v=random.uniform(0, 360), r=random.randint(0, 9000), a=random.choice([0.5, 0.9999, 1.2, 5]),
                    t=random.choice([90, 110.01, 120]), b=random.choice([0.5, 1.5001, 1.9]),
                    d=random.choice(["off", "izquierda", "derecha"]), e=random.randint(0, 1), f=random.randint(0, 1)))
            elif op == "basura":
                datos.write_bytes(os.urandom(random.randint(1, 200)))
            elif op == "borrar":
                datos.unlink(missing_ok=True)
            elif op == "666" and datos.exists():
                os.chmod(datos, 0o666)
            elif op == "000" and datos.exists():
                os.chmod(datos, 0o000)
            elif op == "grande":
                datos.write_text("x=" + "9" * 9000, encoding="utf-8")
            elif op == "fuera":
                escribir_texto_atomico(datos, BASE.format(v=999, r=-5, a=50, t=10, b=9, d="arriba", e=3, f=7))
            elif op == "vacio":
                datos.write_text("", encoding="utf-8")
        except OSError:
            pass
        time.sleep(random.uniform(0.005, 0.05))


errores_tk = []
raiz = tk.Tk()
app = principal.Aplicacion(raiz, ruta_config=trabajo / "config" / "cluster.ini", proyecto=trabajo)
original = app._error_interfaz
app._error_interfaz = lambda *a: (errores_tk.append(a[1]), original(*a))
raiz.report_callback_exception = app._error_interfaz
hilo = threading.Thread(target=caos, daemon=True)
hilo.start()
# Segunda instancia en otro proceso con la misma carpeta (debe quedar sin guardar kilometraje)
segunda = subprocess.Popen([sys.executable, "-c",
    "import sys,tkinter as tk;sys.path.insert(0,'.');import main;r=tk.Tk();"
    f"a=main.Aplicacion(r,manual=True,proyecto=r'{trabajo}');"
    "r.after(3000,a.cerrar);r.mainloop()"])
ciclos_antes = [0]
fin = time.monotonic() + 40
vivo = []
while time.monotonic() < fin:
    raiz.update()
    vivo.append(app.tablero._id_after is not None)
    time.sleep(0.005)
alto.set()
hilo.join()
os.chmod(datos, 0o640) if datos.exists() else None
escribir_texto_atomico(datos, BASE.format(v=77, r=1234, a=5, t=90, b=0.5, d="off", e=0, f=0))
recuperado = False
fin = time.monotonic() + 2
while time.monotonic() < fin:
    raiz.update()
    time.sleep(0.01)
    if app.estado._obj_velocidad == 77.0 and app.estado._obj_rpm == 1234:
        recuperado = True
km = app.estado.odometro.km
app.cerrar()
segunda.wait(timeout=20)
eventos = "".join(p.read_text(encoding="utf-8") for p in (trabajo / "logs").glob("eventos.log*"))
errores = "".join(p.read_text(encoding="utf-8") for p in (trabajo / "logs").glob("errores.log*"))
guardado = (trabajo / "datos" / "odometro.txt").read_text().strip()
print("acciones de caos:", acciones)
print("excepciones en la interfaz:", len(errores_tk), errores_tk[:3])
print("tablero siempre programado:", all(vivo), "muestras", len(vivo))
print("se recupero con un dato valido al final:", recuperado)
print("odometro en memoria / guardado:", f"{km:.3f}", guardado)
print("segunda instancia codigo:", segunda.returncode, "| odometro_en_uso registrado:", "odometro_en_uso" in errores)
print("tipos de error registrados:", sorted({l.split()[3] for l in errores.splitlines() if len(l.split()) > 3}))
ok = (not errores_tk and all(vivo) and recuperado and abs(float(guardado) - km) < 0.001
      and segunda.returncode == 0 and "odometro_en_uso" in errores)
print("RESULTADO CAOS:", "APROBADO" if ok else "FALLIDO")
shutil.rmtree(trabajo, ignore_errors=True)
sys.exit(0 if ok else 1)
