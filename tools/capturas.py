"""Genera capturas de pantalla reales de la interfaz en estados representativos.

Cada captura parte de una ventana nueva en estado seguro, mueve los controles
reales con un reloj simulado (para que los parpadeos queden en una fase
conocida) y fotografia la ventana. Junto a cada imagen se registra en
docs/evidencias/capturas.txt lo que la capa de presentacion indica para los
10 elementos en ese mismo instante.

Uso (en la VM): xvfb-run -a -s "-screen 0 1280x1024x24" python tools/capturas.py"""

import pathlib
import sys
import time
import tkinter as tk

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from PIL import ImageGrab, features

from aceptacion.escenarios import NOMBRES_COLOR
from logic.estado import EstadoCluster
from logic.reloj import RelojSimulado
from ui.presentacion import vista
from ui.tablero import Tablero

DESTINO = pathlib.Path("docs/evidencias/capturas")
INDICE = pathlib.Path("docs/evidencias/capturas.txt")
MIN_COLORES = 10


def _ajustar(tablero, **valores):
    for setter, valor in valores.items():
        tablero.ajustar(setter, valor)


def estado_inicial(tablero, reloj):
    pass


def valores_normales(tablero, reloj):
    _ajustar(tablero, set_motor=True, set_velocidad=120, set_rpm=4500, set_presion_aceite=5,
             set_temp_agua=90, set_presion_turbo=1.0)
    reloj.avanzar(500)
    tablero.ciclo()


def umbrales_de_lecturas(tablero, reloj):
    _ajustar(tablero, set_motor=True, set_velocidad=250, set_rpm=8200, set_presion_aceite=0.8,
             set_temp_agua=115, set_presion_turbo=1.6)
    reloj.avanzar(500)
    tablero.ciclo()


def baja_presion_aceite(tablero, reloj):
    _ajustar(tablero, set_motor=True, set_presion_aceite=0.5, set_temp_agua=90)
    reloj.avanzar(100)
    tablero.ciclo()
    reloj.avanzar(1000)
    tablero.ciclo()


def direccional_y_luces_altas(tablero, reloj):
    _ajustar(tablero, set_motor=True, set_velocidad=60, set_luces_altas=True, set_direccional="IZQ")
    reloj.avanzar(100)
    tablero.ciclo()


def emergencia_con_precedencia(tablero, reloj):
    _ajustar(tablero, set_motor=True, set_direccional="IZQ", set_emergencia=True)
    reloj.avanzar(100)
    tablero.ciclo()


def falla_frenos_motor_apagado(tablero, reloj):
    _ajustar(tablero, set_falla_frenos=True)
    tablero.ciclo()


def entrada_rechazada(tablero, reloj):
    tablero.enviar("set_rpm", 9001)


# (archivo, descripcion, casos relacionados, requisitos, preparacion)
CAPTURAS = (
    ("01_estado_inicial_seguro.png", "Estado inicial seguro: motor apagado, agujas en su minimo y testigos apagados",
     "CA-01 a CA-10 (paso inicial), CP-68, CP-74", "R01", estado_inicial),
    ("02_motor_encendido_valores_normales.png", "Motor encendido con lecturas dentro de rango: sin advertencias",
     "CA-01, CA-03, CA-04, CA-05", "R01", valores_normales),
    ("03_umbrales_de_lecturas.png", "Umbrales cruzados: 2 y 5 en ambar, 3 y 4 en rojo",
     "CA-02, CA-03, CA-04, CA-05, CP-69", "R03, R04, R05", umbrales_de_lecturas),
    ("04_testigo_9_baja_presion_aceite.png", "Presion de aceite bajo 1 bar por 1 s: testigo 9 rojo (critico)",
     "CA-09, CP-70", "R02", baja_presion_aceite),
    ("05_direccional_izq_y_luces_altas.png", "Direccional IZQ (6 verde) y luces altas (7 azul fijo)",
     "CA-06, CA-07", "R06, R07", direccional_y_luces_altas),
    ("06_emergencia_con_precedencia.png", "Emergencia activa con direccional puesto: 8 ambar y 6 oculto (D7)",
     "CA-08, CP-71", "R06, R07", emergencia_con_precedencia),
    ("07_falla_frenos_motor_apagado.png", "Falla de frenos con motor apagado: testigo 10 rojo (critico, D1)",
     "CA-10, CP-76", "R08", falla_frenos_motor_apagado),
    ("08_entrada_rechazada.png", "Valor fuera de rango (9001 RPM) enviado por programa: mensaje en pantalla",
     "CP-77", "-", entrada_rechazada),
)


def _resumen(v):
    partes = [f"{n}={v[n]['valor']:g} {NOMBRES_COLOR[v[n]['color']]}" for n in range(1, 6)]
    partes += [f"{n}={NOMBRES_COLOR[v[n]['color']]}" for n in range(6, 11)]
    return ", ".join(partes)


def capturar(raiz, ruta):
    raiz.update_idletasks()
    raiz.update()
    time.sleep(0.3)
    raiz.update()
    x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
    imagen = ImageGrab.grab(bbox=(x, y, x + raiz.winfo_width(), y + raiz.winfo_height()))
    imagen.save(ruta)
    colores = imagen.convert("RGB").getcolors(maxcolors=1_000_000)
    return imagen.size, len(colores) if colores else MIN_COLORES


def main():
    if not features.check("xcb"):
        print("ERROR: Pillow no tiene soporte XCB para capturar la pantalla", file=sys.stderr)
        return 1
    DESTINO.mkdir(parents=True, exist_ok=True)
    lineas = ["Capturas de pantalla de la interfaz (generadas con tools/capturas.py sobre Xvfb)", ""]
    for archivo, descripcion, casos, requisitos, preparar in CAPTURAS:
        raiz = tk.Tk()
        reloj = RelojSimulado()
        estado = EstadoCluster(reloj)
        tablero = Tablero(raiz, estado)
        try:
            preparar(tablero, reloj)
            tablero.detener()
            tablero.refrescar()
            (ancho, alto), colores = capturar(raiz, DESTINO / archivo)
            resumen = _resumen(vista(estado))
            mensaje = tablero.mensaje.cget("text")
        finally:
            raiz.destroy()
        if colores < MIN_COLORES:
            print(f"ERROR: {archivo} parece vacia ({colores} colores)", file=sys.stderr)
            return 1
        lineas += [f"{archivo} ({ancho}x{alto} px, {colores} colores)",
                   f"  Descripcion: {descripcion}",
                   f"  Casos: {casos} | Requisitos: {requisitos}",
                   f"  Estado dibujado: {resumen}"]
        if mensaje:
            lineas.append(f"  Mensaje en pantalla: {mensaje}")
        lineas.append("")
        print(f"OK {archivo} ({ancho}x{alto} px, {colores} colores)")
    INDICE.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Indice: {INDICE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
