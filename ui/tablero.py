"""Interfaz Tkinter del cluster F40 simulado.

Solo dibuja lo que entrega ui.presentacion.vista(estado) y envia los valores
de los controles a EstadoCluster; no contiene reglas de negocio."""

import math
import tkinter as tk

from ui.presentacion import COLOR_AMBAR, COLOR_APAGADO, COLOR_NORMAL, COLOR_ROJO, CRITICA, ELEMENTOS, vista

PERIODO_REFRESCO_MS = 50
FONDO = "#121212"
COLOR_TEXTO = "#bdbdbd"
ANCHO, ALTO = 900, 440
RADIO = 70
LARGO_AGUJA = 58

FORMATOS = {1: "{:.1f} km/h", 2: "{:.2f} bar", 3: "{:.0f} RPM", 4: "{:.1f} C", 5: "{:.2f} bar"}

# (setter de EstadoCluster, etiqueta, minimo, maximo, resolucion, conversion)
DESLIZADORES = (
    ("set_velocidad", "1 Velocidad (km/h)", 0, 360, 0.1, lambda v: round(float(v), 1)),
    ("set_presion_aceite", "2 Presion de aceite (bar)", 0, 10, 0.01, lambda v: round(float(v), 2)),
    ("set_rpm", "3 RPM", 0, 9000, 1, lambda v: int(round(float(v)))),
    ("set_temp_agua", "4 Temp. agua (C)", 40, 130, 0.1, lambda v: round(float(v), 1)),
    ("set_presion_turbo", "5 Presion turbo (bar)", 0, 2, 0.01, lambda v: round(float(v), 2)),
)

INTERRUPTORES = (
    ("set_motor", "Motor"),
    ("set_luces_altas", "7 Luces altas"),
    ("set_emergencia", "8 Emergencia"),
    ("set_falla_frenos", "10 Falla de frenos"),
)


class Tablero:
    def __init__(self, raiz, estado):
        self.raiz = raiz
        self.estado = estado
        self.items = {}
        self.variables = {}
        self._manejadores = {}
        self._id_after = None

        raiz.title("Cluster F40 (simulado)")
        raiz.configure(bg=FONDO)
        self.canvas = tk.Canvas(raiz, width=ANCHO, height=ALTO, bg=FONDO, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self._dibujar_medidores()
        self._dibujar_testigos()
        self._crear_controles()
        self.mensaje = tk.Label(raiz, text="", fg=COLOR_AMBAR, bg=FONDO)
        self.mensaje.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
        self._programar()

    def _dibujar_medidores(self):
        for i, numero in enumerate(range(1, 6)):
            cx, cy = 90 + i * 180, 120
            arco = self.canvas.create_arc(cx - RADIO, cy - RADIO, cx + RADIO, cy + RADIO,
                                          start=-45, extent=270, style="arc",
                                          outline=COLOR_NORMAL, width=4)
            aguja = self.canvas.create_line(cx, cy, cx, cy - LARGO_AGUJA, fill=COLOR_NORMAL, width=3)
            self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=COLOR_NORMAL, outline="")
            valor = self.canvas.create_text(cx, cy + 58, text="", fill=COLOR_NORMAL,
                                            font=("DejaVu Sans Mono", 11, "bold"))
            self.canvas.create_text(cx, cy + RADIO + 28, text=f"{numero}  {ELEMENTOS[numero]['nombre']}",
                                    fill=COLOR_TEXTO, font=("DejaVu Sans", 10, "bold"))
            self.items[numero] = {"arco": arco, "aguja": aguja, "valor": valor, "centro": (cx, cy)}

    def _dibujar_testigos(self):
        for i, numero in enumerate(range(6, 11)):
            cx, cy = 90 + i * 180, 330
            if ELEMENTOS[numero]["categoria"] == CRITICA:
                forma = self.canvas.create_rectangle(cx - 40, cy - 28, cx + 40, cy + 28, fill=COLOR_APAGADO,
                                                     outline=COLOR_ROJO, width=5)
                self.canvas.create_text(cx, cy - 42, text="CRITICA", fill=COLOR_ROJO,
                                        font=("DejaVu Sans", 9, "bold"))
            else:
                forma = self.canvas.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, fill=COLOR_APAGADO,
                                                outline=COLOR_NORMAL, width=2)
            simbolo = self.canvas.create_text(cx, cy, text=str(numero), fill=COLOR_TEXTO,
                                              font=("DejaVu Sans", 14, "bold"))
            self.canvas.create_text(cx, cy + 48, text=ELEMENTOS[numero]["nombre"], fill=COLOR_TEXTO,
                                    font=("DejaVu Sans", 10, "bold"))
            self.items[numero] = {"forma": forma, "simbolo": simbolo}

    def _crear_controles(self):
        deslizadores = tk.Frame(self.raiz, bg=FONDO)
        deslizadores.grid(row=1, column=0, sticky="nw", padx=10)
        for fila, (setter, etiqueta, minimo, maximo, resolucion, convertir) in enumerate(DESLIZADORES):
            var = tk.DoubleVar(value=minimo)
            manejador = (lambda s=setter, c=convertir, v=var: self.enviar(s, c(v.get())))
            tk.Scale(deslizadores, label=etiqueta, from_=minimo, to=maximo, resolution=resolucion,
                     orient="horizontal", length=420, variable=var, command=lambda _v, m=manejador: m(),
                     bg=FONDO, fg=COLOR_TEXTO, troughcolor="#2a2a2a",
                     highlightthickness=0).grid(row=fila, column=0, sticky="w")
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        interruptores = tk.Frame(self.raiz, bg=FONDO)
        interruptores.grid(row=1, column=1, sticky="nw", padx=10)
        for fila, (setter, texto) in enumerate(INTERRUPTORES):
            var = tk.BooleanVar(value=False)
            manejador = (lambda s=setter, v=var: self.enviar(s, bool(v.get())))
            tk.Checkbutton(interruptores, text=texto, variable=var, command=manejador, bg=FONDO,
                           fg=COLOR_TEXTO, selectcolor="#2a2a2a", activebackground=FONDO, activeforeground=COLOR_TEXTO, highlightthickness=0, bd=0,
                           font=("DejaVu Sans", 11)).grid(row=fila, column=0, sticky="w", pady=4)
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        var = tk.StringVar(value="OFF")
        manejador = (lambda v=var: self.enviar("set_direccional", v.get()))
        tk.Label(interruptores, text="6 Direccional", bg=FONDO, fg=COLOR_TEXTO,
                 font=("DejaVu Sans", 11)).grid(row=len(INTERRUPTORES), column=0, sticky="w", pady=(12, 0))
        for col, opcion in enumerate(("IZQ", "OFF", "DER")):
            tk.Radiobutton(interruptores, text=opcion, value=opcion, variable=var, command=manejador,
                           bg=FONDO, fg=COLOR_TEXTO, selectcolor="#2a2a2a", activebackground=FONDO, activeforeground=COLOR_TEXTO, highlightthickness=0, bd=0,
                           font=("DejaVu Sans", 11)).grid(row=len(INTERRUPTORES) + 1 + col, column=0, sticky="w")
        self.variables["set_direccional"] = var
        self._manejadores["set_direccional"] = manejador

    def enviar(self, setter, valor):
        """Envia un valor a EstadoCluster; si se rechaza, lo muestra en pantalla."""
        try:
            getattr(self.estado, setter)(valor)
        except (TypeError, ValueError) as error:
            self.mensaje.configure(text=f"Entrada rechazada: {error}")
            return False
        self.mensaje.configure(text="")
        return True

    def ajustar(self, setter, valor):
        """Mueve un control como lo haria el usuario (usado por las pruebas)."""
        self.variables[setter].set(valor)
        return self._manejadores[setter]()

    def refrescar(self):
        v = vista(self.estado)
        for numero in range(1, 6):
            d, it = v[numero], self.items[numero]
            cx, cy = it["centro"]
            angulo = math.radians(225 - 270 * d["fraccion"])
            self.canvas.coords(it["aguja"], cx, cy,
                               cx + LARGO_AGUJA * math.cos(angulo), cy - LARGO_AGUJA * math.sin(angulo))
            self.canvas.itemconfigure(it["aguja"], fill=d["color"])
            self.canvas.itemconfigure(it["arco"], outline=d["color"])
            self.canvas.itemconfigure(it["valor"], text=FORMATOS[numero].format(d["valor"]), fill=d["color"])
        for numero in range(6, 11):
            d, it = v[numero], self.items[numero]
            texto = str(numero)
            if numero == 6:
                texto = {"IZQ": "◀ 6", "DER": "6 ▶"}.get(d["lado"], "6")
            self.canvas.itemconfigure(it["forma"], fill=d["color"])
            self.canvas.itemconfigure(it["simbolo"], text=texto,
                                      fill="#000000" if d["encendido"] else COLOR_TEXTO)
        return v

    def ciclo(self):
        self.estado.tick()
        return self.refrescar()

    def _programar(self):
        self.ciclo()
        self._id_after = self.raiz.after(PERIODO_REFRESCO_MS, self._programar)

    def detener(self):
        if self._id_after is not None:
            self.raiz.after_cancel(self._id_after)
            self._id_after = None
