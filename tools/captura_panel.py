"""Captura real del panel de control en un estado representativo.
Uso (desde la raiz): xvfb-run -a -s "-screen 0 1600x1000x24" python tools/captura_panel.py"""
import pathlib, sys, tempfile, time, tkinter as tk
sys.path.insert(0, ".")
from PIL import ImageGrab
from panel.ventana import Panel

salida = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "docs/evidencias/capturas/09_panel_de_control.png")
salida.parent.mkdir(parents=True, exist_ok=True)
t = pathlib.Path(tempfile.mkdtemp())
raiz = tk.Tk()
p = Panel(raiz, ruta_datos=t / "vehiculo.conf", dir_logs=t / "logs")
p.alternar_motor()
p.cambiar("3")
p.vehiculo.velocidad = 120.0
p.pisando["acelerador"] = True
p.var_altas.set(True); p.var_direccional.set("IZQ"); p._luces()
p.var_fallas["fuga_aceite"].set(True); p._fallas()
p.registrar("$ Todas las pruebas (ejemplo de consola)", "cmd")
fin = time.monotonic() + 2.5
while time.monotonic() < fin:
    raiz.update(); time.sleep(0.02)
p.pisando["acelerador"] = False
p.pisando["freno"] = True
fin = time.monotonic() + 0.15
while time.monotonic() < fin:
    raiz.update(); time.sleep(0.02)
raiz.update()
x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x + raiz.winfo_width(), y + raiz.winfo_height())).save(salida)
print("OK", salida, raiz.winfo_width(), raiz.winfo_height())
p.cerrar()
