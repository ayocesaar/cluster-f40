"""Interfaz Tkinter del cluster F40 simulado, con estetica 8-bit.

Sigue la distribucion del tablero del F40: velocimetro y tacometro grandes al
centro, medidores chicos a los lados y los testigos criticos arriba, entre las
dos esferas. Todo se dibuja con bloques de pixeles. Solo dibuja lo que entrega
ui.presentacion.vista(estado) y envia los valores de los controles a
EstadoCluster; no contiene reglas de negocio."""

import math
import tkinter as tk

from ui.presentacion import COLOR_AMBAR, COLOR_APAGADO, COLOR_NORMAL, COLOR_ROJO, CRITICA, ELEMENTOS, vista

PERIODO_REFRESCO_MS = 50
ANCHO, ALTO = 1040, 470
FUENTE = "Courier New"

FONDO = "#0d0d17"
CARCASA = "#171724"
CARA = "#0a0a12"
BISEL = "#34344c"
COLOR_TEXTO = "#c8c8dc"
MARCA = "#d8d8e8"
MARCA_MENOR = "#6e6e8c"
ICONO_APAGADO = "#4a4a66"
ICONO_ENCENDIDO = "#0d0d17"
VERDE_TEXTO = "#4fd06b"

FORMATOS = {1: "{:.1f} km/h", 2: "{:.2f} bar", 3: "{:.0f} RPM", 4: "{:.1f} C", 5: "{:.2f} bar"}

# Medidores 1-5: centro, radio, paso de marcas menores y mayores, y la zona de
# advertencia que se pinta en la escala (solo decorativa; el color de la aguja
# lo decide ui.presentacion).
MEDIDORES = {
    1: {"cx": 355, "cy": 262, "r": 150, "menor": 20, "mayor": 40, "zona": lambda v: None},
    3: {"cx": 685, "cy": 262, "r": 150, "menor": 500, "mayor": 1000,
        "zona": lambda v: COLOR_ROJO if v >= 8000 else None},
    2: {"cx": 110, "cy": 158, "r": 62, "menor": 1, "mayor": 5,
        "zona": lambda v: COLOR_AMBAR if v < 1 else None},
    4: {"cx": 110, "cy": 360, "r": 62, "menor": 15, "mayor": 45,
        "zona": lambda v: COLOR_ROJO if v > 110 else None},
    5: {"cx": 930, "cy": 158, "r": 62, "menor": 0.25, "mayor": 1,
        "zona": lambda v: COLOR_AMBAR if v > 1.5 else None},
}

# Testigos 6-10: centro y lado. El 6 y el 8 van dentro del velocimetro, el 7
# dentro del tacometro y los criticos 9 y 10 arriba, entre las esferas.
TESTIGOS = {
    6: (297, 354, 44), 8: (413, 354, 44), 7: (685, 354, 44),
    9: (485, 78, 56), 10: (555, 78, 56),
}

ICONOS = {
    "IZQ": ("...X....", "..XX....", ".XXXXXXX", "XXXXXXXX", "XXXXXXXX", ".XXXXXXX", "..XX....", "...X...."),
    "DER": ("....X...", "....XX..", "XXXXXXX.", "XXXXXXXX", "XXXXXXXX", "XXXXXXX.", "....XX..", "....X..."),
    7: ("XX..XXX.", "...X...X", "XX.X...X", "...X...X", "XX.X...X", "...X...X", "XX..XXX.", "........"),
    8: ("...XX...", "...XX...", "..X..X..", "..X..X..", ".X.XX.X.", ".X....X.", "X......X", "XXXXXXXX"),
    9: ("........", ".XX.....", ".XX....X", "XXXXXXX.", "XXXXXX..", ".XXXXX.X", ".XXXXX..", "........"),
    10: ("..XXXX..", ".X....X.", "X..XX..X", "X..XX..X", "X..XX..X", "X......X", ".X.XX.X.", "..XXXX.."),
}

# Letras de 5x7 pixeles para el titulo.
LETRAS = {
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    " ": ("00000",) * 7,
}

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


def _rejilla(v):
    """Ajusta una coordenada a la rejilla de 3 px: da el escalonado de 8 bits."""
    return round(v / 3) * 3


def _angulo(fraccion):
    return math.radians(210 - 240 * fraccion)


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
        self._dibujar_carcasa()
        self._dibujar_medidores()
        self._dibujar_testigos()
        self._dibujar_estado()
        self._crear_controles()
        self.mensaje = tk.Label(raiz, text="", fg=COLOR_AMBAR, bg=FONDO, font=(FUENTE, 10, "bold"))
        self.mensaje.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
        self._programar()

    # ------------------------------------------------------------------ dibujo fijo

    def _pixel(self, x, y, lado, color):
        return self.canvas.create_rectangle(x, y, x + lado, y + lado, fill=color, outline="")

    def _texto_pixel(self, x, y, texto, lado, color):
        for letra in texto:
            for fila, renglon in enumerate(LETRAS.get(letra, LETRAS[" "])):
                for col, bit in enumerate(renglon):
                    if bit == "1":
                        self._pixel(x + col * lado, y + fila * lado, lado, color)
            x += 6 * lado

    def _dibujar_carcasa(self):
        self._texto_pixel(20, 10, "F40 CLUSTER 8-BIT", 3, COLOR_ROJO)
        self.canvas.create_text(ANCHO - 20, 20, text="SIMULACION DIDACTICA  R01-R08", anchor="e",
                                fill=COLOR_TEXTO, font=(FUENTE, 9, "bold"))
        x0, y0, x1, y1, p = 8, 42, ANCHO - 8, ALTO - 6, 6
        self.canvas.create_polygon(
            x0, y0 + 3 * p, x0 + p, y0 + 3 * p, x0 + p, y0 + 2 * p, x0 + 2 * p, y0 + 2 * p, x0 + 2 * p, y0 + p,
            x0 + 3 * p, y0 + p, x0 + 3 * p, y0, x1 - 3 * p, y0, x1 - 3 * p, y0 + p, x1 - 2 * p, y0 + p,
            x1 - 2 * p, y0 + 2 * p, x1 - p, y0 + 2 * p, x1 - p, y0 + 3 * p, x1, y0 + 3 * p,
            x1, y1 - 3 * p, x1 - p, y1 - 3 * p, x1 - p, y1 - 2 * p, x1 - 2 * p, y1 - 2 * p, x1 - 2 * p, y1 - p,
            x1 - 3 * p, y1 - p, x1 - 3 * p, y1, x0 + 3 * p, y1, x0 + 3 * p, y1 - p, x0 + 2 * p, y1 - p,
            x0 + 2 * p, y1 - 2 * p, x0 + p, y1 - 2 * p, x0 + p, y1 - 3 * p, x0, y1 - 3 * p,
            fill=CARCASA, outline="")

    def _dibujar_medidores(self):
        for numero, m in MEDIDORES.items():
            e = ELEMENTOS[numero]
            cx, cy, r = m["cx"], m["cy"], m["r"]
            grande = r > 100
            g = 5 if grande else 4

            # Esfera: renglones de pixeles que forman un disco escalonado.
            for dy in range(-r, r, g):
                medio = int(math.sqrt(max(0, r * r - (dy + g / 2) ** 2)) // g) * g
                self.canvas.create_rectangle(cx - medio, cy + dy, cx + medio, cy + dy + g, fill=CARA, outline="")

            # Bisel: anillo de bloques (el del turbo cambia de color con R05).
            anillo = []
            cuenta = round(2 * math.pi * r / 8)
            for i in range(cuenta):
                a = 2 * math.pi * i / cuenta
                x, y = _rejilla(cx + (r - 3) * math.cos(a)), _rejilla(cy - (r - 3) * math.sin(a))
                anillo.append(self._pixel(x - 2, y - 2, 5, BISEL))

            # Escala: marcas menores y mayores, y numeros en las mayores.
            pasos = round((e["maximo"] - e["minimo"]) / m["menor"])
            for i in range(pasos + 1):
                v = e["minimo"] + i * m["menor"]
                mayor = abs((v - e["minimo"]) / m["mayor"] - round((v - e["minimo"]) / m["mayor"])) < 1e-6
                a = _angulo((v - e["minimo"]) / (e["maximo"] - e["minimo"]))
                lado = (8 if mayor else 4) if grande else (6 if mayor else 3)
                rr = r - (15 if grande else 11)
                x, y = _rejilla(cx + rr * math.cos(a)), _rejilla(cy - rr * math.sin(a))
                zona = m["zona"](v)
                self._pixel(x - lado // 2, y - lado // 2, lado, zona or (MARCA if mayor else MARCA_MENOR))
                if mayor:
                    rn = r - (36 if grande else 24)
                    etiqueta = v / 1000 if numero == 3 else v
                    self.canvas.create_text(cx + rn * math.cos(a), cy - rn * math.sin(a), text=f"{etiqueta:g}",
                                            fill=zona or MARCA, font=(FUENTE, 12 if grande else 8, "bold"))

            # Aguja: bloques en linea recta que saltan de casilla en casilla.
            paso = 5 if grande else 4
            inicio, fin = (10, r - 22) if grande else (6, r - 15)
            bloques = [self._pixel(cx, cy, paso, COLOR_NORMAL) for _ in range(inicio, fin, paso)]
            self._pixel(cx - 6, cy - 6, 12, MARCA)

            valor = self.canvas.create_text(cx, cy + (36 if grande else 44), text="", fill=COLOR_NORMAL,
                                            font=(FUENTE, 18 if grande else 10, "bold"))
            if grande:
                self.canvas.create_text(cx, cy + 58, text="KM/H" if numero == 1 else "x1000 RPM",
                                        fill=COLOR_TEXTO, font=(FUENTE, 9, "bold"))
            self.canvas.create_text(cx, cy + r + (16 if grande else 13), text=f"{numero}  {e['nombre'].upper()}",
                                    fill=COLOR_TEXTO, font=(FUENTE, 11 if grande else 8, "bold"))
            self.items[numero] = {"arco": anillo[0], "anillo": anillo, "aguja": bloques[0], "bloques": bloques,
                                  "valor": valor, "centro": (cx, cy), "inicio": inicio, "paso": paso,
                                  "ultimo": None}

    def _dibujar_testigos(self):
        for numero, (cx, cy, lado) in TESTIGOS.items():
            media = lado // 2
            critica = ELEMENTOS[numero]["categoria"] == CRITICA
            if critica:
                forma = self.canvas.create_rectangle(cx - media, cy - media, cx + media, cy + media,
                                                     fill=COLOR_APAGADO, outline=COLOR_ROJO, width=4)
                self.canvas.create_text(cx, cy - media - 12, text="CRITICA", fill=COLOR_ROJO,
                                        font=(FUENTE, 8, "bold"))
                px = 5
            else:
                forma = self.canvas.create_oval(cx - media, cy - media, cx + media, cy + media,
                                                fill=COLOR_APAGADO, outline=BISEL, width=3)
                px = 3
            iconos = {}
            for clave in (("IZQ", "DER") if numero == 6 else (numero,)):
                origen_x, origen_y = cx - 4 * px, cy - 4 * px
                iconos[clave] = [self._pixel(origen_x + col * px, origen_y + fila * px, px, ICONO_APAGADO)
                                 for fila, renglon in enumerate(ICONOS[clave])
                                 for col, bit in enumerate(renglon) if bit == "X"]
            simbolo = self.canvas.create_text(cx - media - 8, cy - media + 4, text=str(numero), fill=COLOR_TEXTO,
                                              font=(FUENTE, 9, "bold"))
            self.items[numero] = {"forma": forma, "simbolo": simbolo, "iconos": iconos, "ultimo": None}

    def _dibujar_estado(self):
        x0, y0, x1, y1 = 872, 282, 988, 412
        self.canvas.create_rectangle(x0, y0, x1, y1, fill=CARA, outline=BISEL, width=4)
        self.canvas.create_text(x0 + 12, y0 + 16, text="MOTOR", anchor="w", fill=COLOR_TEXTO, font=(FUENTE, 9, "bold"))
        self._txt_motor = self.canvas.create_text(x0 + 12, y0 + 40, text="", anchor="w", font=(FUENTE, 18, "bold"))
        self.canvas.create_text(x0 + 12, y0 + 70, text="RELOJ", anchor="w", fill=COLOR_TEXTO, font=(FUENTE, 9, "bold"))
        self._txt_reloj = self.canvas.create_text(x0 + 12, y0 + 94, text="", anchor="w", fill=VERDE_TEXTO,
                                                  font=(FUENTE, 14, "bold"))

    # ------------------------------------------------------------------ controles

    def _crear_controles(self):
        estilo = {"bg": FONDO, "fg": COLOR_TEXTO, "font": (FUENTE, 10, "bold")}
        deslizadores = tk.Frame(self.raiz, bg=FONDO)
        deslizadores.grid(row=1, column=0, sticky="nw", padx=10)
        for i, (setter, etiqueta, minimo, maximo, resolucion, convertir) in enumerate(DESLIZADORES):
            var = tk.DoubleVar(value=minimo)
            manejador = (lambda s=setter, c=convertir, v=var: self.enviar(s, c(v.get())))
            tk.Scale(deslizadores, label=etiqueta, from_=minimo, to=maximo, resolution=resolucion,
                     orient="horizontal", length=300, variable=var, command=lambda _v, m=manejador: m(),
                     troughcolor=BISEL, activebackground=COLOR_AMBAR, sliderrelief="flat", bd=0,
                     highlightthickness=0, **estilo).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 16), pady=2)
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        interruptores = tk.Frame(self.raiz, bg=FONDO)
        interruptores.grid(row=1, column=1, sticky="nw", padx=10)
        botones = {"selectcolor": CARCASA, "activebackground": FONDO, "activeforeground": COLOR_TEXTO,
                   "highlightthickness": 0, "bd": 0, **estilo}
        for i, (setter, texto) in enumerate(INTERRUPTORES):
            var = tk.BooleanVar(value=False)
            manejador = (lambda s=setter, v=var: self.enviar(s, bool(v.get())))
            tk.Checkbutton(interruptores, text=texto, variable=var, command=manejador,
                           **botones).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 12), pady=4)
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        var = tk.StringVar(value="OFF")
        manejador = (lambda v=var: self.enviar("set_direccional", v.get()))
        fila = tk.Frame(interruptores, bg=FONDO)
        fila.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        tk.Label(fila, text="6 Direccional", **estilo).pack(side="left", padx=(0, 10))
        for opcion in ("IZQ", "OFF", "DER"):
            tk.Radiobutton(fila, text=opcion, value=opcion, variable=var, command=manejador,
                           **botones).pack(side="left", padx=(0, 8))
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

    # ------------------------------------------------------------------ refresco

    def refrescar(self):
        v = vista(self.estado)
        for numero in range(1, 6):
            d, it = v[numero], self.items[numero]
            self.canvas.itemconfigure(it["valor"], text=FORMATOS[numero].format(d["valor"]), fill=d["color"])
            clave = (round(d["fraccion"], 4), d["color"])
            if it["ultimo"] == clave:
                continue
            it["ultimo"] = clave
            cx, cy = it["centro"]
            a = _angulo(min(1.0, max(0.0, d["fraccion"])))
            media = it["paso"] // 2
            for k, bloque in enumerate(it["bloques"]):
                r = it["inicio"] + k * it["paso"]
                x, y = _rejilla(cx + r * math.cos(a)), _rejilla(cy - r * math.sin(a))
                self.canvas.coords(bloque, x - media, y - media, x - media + it["paso"], y - media + it["paso"])
                self.canvas.itemconfigure(bloque, fill=d["color"])
            if numero == 5:
                contorno = BISEL if d["color"] == COLOR_NORMAL else d["color"]
                for bloque in it["anillo"]:
                    self.canvas.itemconfigure(bloque, fill=contorno)

        for numero in range(6, 11):
            d, it = v[numero], self.items[numero]
            self.canvas.itemconfigure(it["forma"], fill=d["color"])
            lado = d.get("lado") if numero == 6 else numero
            clave = (d["encendido"], lado)
            if it["ultimo"] == clave:
                continue
            it["ultimo"] = clave
            visible = "DER" if lado == "DER" else ("IZQ" if numero == 6 else numero)
            for nombre, pixeles in it["iconos"].items():
                estado = "normal" if nombre == visible else "hidden"
                for p in pixeles:
                    self.canvas.itemconfigure(p, state=estado,
                                              fill=ICONO_ENCENDIDO if d["encendido"] else ICONO_APAGADO)

        motor = self.estado.motor_activo
        self.canvas.itemconfigure(self._txt_motor, text="ON" if motor else "OFF",
                                  fill=VERDE_TEXTO if motor else COLOR_TEXTO)
        self.canvas.itemconfigure(self._txt_reloj, text=f"{self.estado.reloj.ahora_ms() / 1000:.1f} s")
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
