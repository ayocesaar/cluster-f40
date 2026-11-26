"""Interfaz Tkinter del cluster F40 simulado.

Inspirada en el cuadro del F40 (1987): capota negra mate sobre un tablero forrado
de fieltro gris, esferas negras con numerales en blanco calido de la epoca, el
tacometro grande al centro, el velocimetro a su derecha con el odometro de tambor,
el turbo a la izquierda y los medidores chicos de aceite y agua a un lado. Los
testigos van en una barra aparte, con su simbolo. No usa logotipos de la marca.

Solo dibuja lo que entrega ui.presentacion.vista(estado) y envia los valores de
los controles a EstadoCluster; no contiene reglas de negocio. Lo que las pruebas
observan se conserva: items[n]["aguja"] y ["valor"] (1-5), items[n]["forma"]
(6-10; ovalos 6-8 y rectangulos 9-10) e items[11] (odometro de 6 digitos).
Los elementos adicionales de las Etapas 18 y 20 van en una franja inferior aparte (extras[12-16]):
llave, combustible con su reserva, puerta, cinturon, proteccion del motor y carga de bateria."""

import math
import tkinter as tk
import tkinter.font as tkfont

from ui.presentacion import (COLOR_AMBAR, COLOR_APAGADO, COLOR_NORMAL, COLOR_ROJO, CRITICA, ELEMENTOS,
                             ELEMENTOS_EXTRA, vista, vista_extra, vista_odometro)

PERIODO_REFRESCO_MS = 50
ANCHO, ALTO = 1120, 572
FUENTE = "Helvetica"
FUENTE_TAMBOR = "Courier New"

FONDO = "#1b1b1d"            # ventana
FIELTRO = "#3a3a3c"          # tablero forrado de fieltro gris
CAPOTA = "#101011"           # capota negra mate del cuadro
CAPOTA_BORDE = "#232326"
COPA = "#060606"             # hueco donde se asienta cada esfera
CARA = "#0b0b0b"
NUMERO = "#ece6d2"           # blanco calido de los numerales de epoca
MARCA_MENOR = "#8f8a7c"
ZONA_ROJA = "#c62828"
ZONA_AMBAR = "#d98c1a"
BISEL = "#2c2c2f"
BISEL_LUZ = "#55555a"
COLOR_TEXTO = "#c9c9c4"
ICONO_APAGADO = "#4b4b55"
ICONO_ENCENDIDO = "#101010"
VERDE_TEXTO = "#4fd06b"
# Nombre usado por versiones anteriores para el color del contorno normal del turbo.
CARCASA = CAPOTA

FORMATOS = {1: "{:.1f} km/h", 2: "{:.2f} bar", 3: "{:.0f} RPM", 4: "{:.1f} C", 5: "{:.2f} bar"}
BARRIDO = 270                 # grados de la escala: de las 7:30 a las 4:30, como las esferas de epoca

# Medidores 1-5: centro, radio, marcas, numerales, zona pintada en la escala (decorativa: el
# color de la aguja lo decide ui.presentacion) y rotulo dentro de la esfera.
MEDIDORES = {
    3: {"cx": 565, "cy": 228, "r": 165, "mayor": 1000, "menor": 250, "divisor": 1000, "letra": 18,
        "zonas": [(8000, 9000, ZONA_ROJA)], "rotulo": "RPM x 1000"},
    1: {"cx": 900, "cy": 238, "r": 140, "mayor": 40, "menor": 10, "divisor": 1, "letra": 13,
        "zonas": [], "rotulo": "km/h"},
    5: {"cx": 275, "cy": 238, "r": 98, "mayor": 0.5, "menor": 0.1, "divisor": 1, "letra": 11,
        "zonas": [(1.5, 2.0, ZONA_AMBAR)], "rotulo": "TURBO  bar"},
    2: {"cx": 90, "cy": 150, "r": 64, "mayor": 2, "menor": 1, "divisor": 1, "letra": 9,
        "zonas": [(0, 1, ZONA_AMBAR)], "rotulo": "ACEITE bar"},
    4: {"cx": 90, "cy": 322, "r": 64, "mayor": 30, "menor": 10, "divisor": 1, "letra": 9,
        "zonas": [(110, 130, ZONA_ROJA)], "rotulo": "AGUA  C"},
}

# Testigos 6-10 en la barra de testigos: centro, ancho y alto. 6-8 lentes redondas;
# 9 y 10 (criticos) rectangulos con marco rojo.
BARRA = (400, 436, 1040, 490)
TESTIGOS = {6: (445, 463, 34, 34), 7: (525, 463, 34, 34), 8: (605, 463, 34, 34),
            9: (725, 463, 74, 38), 10: (865, 463, 74, 38)}
NOMBRES_TESTIGO = {6: "DIRECC.", 7: "ALTAS", 8: "EMERG.", 9: "PRES. ACEITE", 10: "FRENOS"}

# Franja inferior con los elementos adicionales de la Etapa 18 (los diez aprobados no se mueven).
FRANJA = (22, 500, 1100, 564)
FILA_EXTRA = 534                     # centro vertical de los testigos de la franja
EXTRA = {12: (648, 32, 30, "12 PUERTA"), 13: (722, 50, 30, "13 CINTURON"), 15: (808, 64, 30, "15 PROTECCION"),
         16: (890, 46, 30, "16 CARGA")}
COMBUSTIBLE = (150, 528, 420, 542)   # barra del elemento 14: x0, y0, x1, y1
ACEITE = (190, 392, 360, 402)        # barra del elemento 17 bajo el turbo (Etapa 21)
INERCIA = 0.35                       # agujas: fraccion del camino que recorren en cada refresco (50 ms)

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


def _angulo(fraccion):
    """Angulo en radianes (antihorario desde las 3) para una fraccion de la escala."""
    return math.radians(225 - BARRIDO * fraccion)


def _mezclar(a, b, t):
    """Color intermedio entre a y b (#rrggbb)."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


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
        # Ganchos opcionales del ciclo (los usa main.py): antes del tick se consumen
        # los datos externos; despues, el monitor registra los eventos.
        self.antes_del_tick = None
        self.despues_del_tick = None
        self.periodo_ms = PERIODO_REFRESCO_MS
        self._controles = []
        self.canvas = tk.Canvas(raiz, width=ANCHO, height=ALTO, bg=FIELTRO, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self._dibujar_carcasa()
        self._dibujar_medidores()
        self._dibujar_testigos()
        self._dibujar_estado()
        self._dibujar_extras()
        self._dibujar_aceite()
        self.inercia = INERCIA
        self._mostrada = {n: 0.0 for n in range(1, 6)}
        self._crear_controles()
        self.mensaje = tk.Label(raiz, text="", fg=COLOR_AMBAR, bg=FONDO, font=(FUENTE, 10, "bold"))
        self.mensaje.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))
        # Avisos del sistema (por ejemplo, un odometro restaurado); no los borra la siguiente entrada valida.
        self.aviso = tk.Label(raiz, text="", fg=COLOR_AMBAR, bg=FONDO, font=(FUENTE, 10, "bold"))
        self.aviso.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        # Los digitos del odometro quedan sobre la aguja del velocimetro (DEF-12).
        self.canvas.tag_raise(self.items[11]["caja"])
        self.canvas.tag_raise("tambor")
        self.canvas.tag_raise(self.items[11]["valor"])
        self._programar()

    # ------------------------------------------------------------------ dibujo fijo

    def _dibujar_carcasa(self):
        c = self.canvas
        c.create_text(22, 16, text="F40", anchor="w", fill=NUMERO, font=(FUENTE, 15, "bold italic"))
        c.create_text(70, 17, text="CUADRO DE INSTRUMENTOS  ·  SIMULACION DIDACTICA", anchor="w",
                      fill=COLOR_TEXTO, font=(FUENTE, 8, "bold"))
        c.create_text(ANCHO - 20, 17, text="FERRARI F40 (1987)  ·  R01-R14  ·  ELEMENTOS 1-17", anchor="e",
                      fill=COLOR_TEXTO, font=(FUENTE, 8, "bold"))
        # Capota negra mate: una sola pieza curva, mas alta sobre el tacometro, como en el F40.
        contorno = (14, 410, 14, 100, 34, 74, 170, 64, 372, 60, 400, 34, 565, 22, 735, 30, 765, 52,
                    1040, 62, 1092, 80, 1108, 118, 1108, 404, 1080, 424, 44, 424)
        c.create_polygon(contorno, smooth=True, splinesteps=24, fill=CAPOTA, outline=CAPOTA_BORDE, width=3)
        c.create_polygon(contorno, smooth=True, splinesteps=24, fill="", outline="#18181a", width=1)

    def _escala(self, numero, m):
        c, e = self.canvas, ELEMENTOS[numero]
        cx, cy, r = m["cx"], m["cy"], m["r"]
        rango = e["maximo"] - e["minimo"]
        grande = r > 120
        # Zonas pintadas en la escala (rojo en el tacometro y el agua, ambar en turbo y aceite).
        for desde, hasta, color in m["zonas"]:
            f0, f1 = (desde - e["minimo"]) / rango, (hasta - e["minimo"]) / rango
            radio = r - (14 if grande else 9)
            c.create_arc(cx - radio, cy - radio, cx + radio, cy + radio, start=225 - BARRIDO * f1,
                         extent=BARRIDO * (f1 - f0), style="arc", outline=color, width=7 if grande else 5)
        pasos = round(rango / m["menor"])
        for i in range(pasos + 1):
            v = e["minimo"] + i * m["menor"]
            relativo = (v - e["minimo"]) / m["mayor"]
            mayor = abs(relativo - round(relativo)) < 1e-6
            a = _angulo((v - e["minimo"]) / rango)
            largo = (16 if mayor else 8) if grande else (10 if mayor else 5)
            r1, r2 = r - 7, r - 7 - largo
            en_zona = any(d <= v <= h for d, h, _ in m["zonas"])
            color = NUMERO if mayor else MARCA_MENOR
            if en_zona and mayor:
                color = next(col for d, h, col in m["zonas"] if d <= v <= h)
            c.create_line(cx + r1 * math.cos(a), cy - r1 * math.sin(a), cx + r2 * math.cos(a), cy - r2 * math.sin(a),
                          fill=color, width=(3 if grande else 2) if mayor else 1)
            if mayor:
                rn = r - (40 if grande else 25)
                texto = f"{v / m['divisor']:g}"
                c.create_text(cx + rn * math.cos(a), cy - rn * math.sin(a), text=texto, fill=color,
                              font=(FUENTE, m["letra"], "bold"))

    def _dibujar_medidores(self):
        c = self.canvas
        for numero, m in MEDIDORES.items():
            e = ELEMENTOS[numero]
            cx, cy, r = m["cx"], m["cy"], m["r"]
            grande = r > 120
            # Copa hundida en la capota, bisel delgado y esfera negra con un leve degradado al centro.
            c.create_oval(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10, fill=COPA, outline="#2a2a2d", width=2)
            anillo = c.create_oval(cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3, fill=BISEL, outline=BISEL_LUZ,
                                   width=2)
            for k in range(6):
                rr = r - k * r / 7
                c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=_mezclar(CARA, "#161616", k / 6), outline="")
            self._escala(numero, m)
            c.create_text(cx, cy - r * 0.34, text=m["rotulo"], fill=MARCA_MENOR,
                          font=(FUENTE, 9 if grande else 7, "bold"))
            if numero == 1:
                # Elemento 11: odometro de tambor de 6 digitos en la esfera del velocimetro, como en el F40.
                letra = tkfont.Font(root=self.raiz, family=FUENTE_TAMBOR, size=15, weight="bold")
                celda = letra.measure("0")
                ancho, alto, y0 = 6 * celda, 24, cy + 40
                caja = c.create_rectangle(cx - ancho / 2 - 3, y0 - 3, cx + ancho / 2 + 3, y0 + alto + 3, fill="#000000",
                                          outline="#3a3a3e", width=2)
                for k in range(6):
                    x0 = cx - ancho / 2 + k * ancho / 6
                    c.create_rectangle(x0 + 1, y0, x0 + ancho / 6 - 1, y0 + alto,
                                       fill="#1c1c1c" if k % 2 else "#161616", outline="", tags="tambor")
                # Un solo texto de 6 digitos (lo leen las pruebas); el tambor dibuja una celda por digito.
                texto = c.create_text(cx, y0 + alto / 2 + 1, text="000000", fill=NUMERO, font=letra)
                c.create_text(cx + ancho / 2 + 16, y0 + alto / 2, text="km", fill=MARCA_MENOR, font=(FUENTE, 8, "bold"))
                c.create_text(cx, y0 + alto + 12, text="11 ODOMETRO", fill=MARCA_MENOR, font=(FUENTE, 7, "bold"))
                self.items[11] = {"caja": caja, "valor": texto}
            valor = c.create_text(cx, cy + r * (0.68 if grande else 0.62), text="", fill=COLOR_NORMAL,
                                  font=(FUENTE, 11 if grande else 8, "bold"))

            # Aguja conica con contrapeso; se dibuja despues de la escala y antes de la tapa central.
            aguja = c.create_polygon(0, 0, 0, 0, 0, 0, fill=COLOR_NORMAL, outline="#1a1a1a", width=1)
            tapa = r * (0.09 if grande else 0.13)
            c.create_oval(cx - tapa, cy - tapa, cx + tapa, cy + tapa, fill="#1d1d1f", outline="#5a5a5f", width=2)
            c.create_oval(cx - tapa / 2.5, cy - tapa / 2.5, cx + tapa / 2.5, cy + tapa / 2.5, fill="#2c2c30", outline="")
            c.create_text(cx, cy + r + (17 if grande else 15), text=f"{numero} · {e['nombre'].upper()}",
                          fill=COLOR_TEXTO, font=(FUENTE, 9 if grande else 7, "bold"))
            self.items[numero] = {"aguja": aguja, "bloques": [aguja], "valor": valor, "anillo": [anillo],
                                  "arco": anillo, "centro": (cx, cy), "radio": r, "ultimo": None}

    def _simbolo(self, clave, cx, cy):
        """Simbolo de un testigo con primitivas. Devuelve [(item, atributo que toma el color)]."""
        c, piezas = self.canvas, []
        if clave in ("IZQ", "DER"):
            d = -1 if clave == "IZQ" else 1
            piezas.append((c.create_polygon(cx + d * 11, cy, cx - d, cy - 10, cx - d, cy - 4, cx - d * 11, cy - 4,
                                            cx - d * 11, cy + 4, cx - d, cy + 4, cx - d, cy + 10, outline=""), "fill"))
        elif clave == 7:        # luces altas: faro con rayos horizontales
            piezas.append((c.create_arc(cx - 4, cy - 8, cx + 12, cy + 8, start=90, extent=180, style="chord",
                                        outline=""), "fill"))
            piezas += [(c.create_line(cx - 12, cy + dy, cx - 5, cy + dy, width=2), "fill") for dy in (-6, -2, 2, 6)]
        elif clave == 8:        # intermitentes: doble triangulo
            piezas.append((c.create_line(cx, cy - 11, cx + 11, cy + 8, cx - 11, cy + 8, cx, cy - 11, width=3,
                                         joinstyle="miter"), "fill"))
            piezas.append((c.create_line(cx, cy - 4, cx + 5, cy + 4, cx - 5, cy + 4, cx, cy - 4, width=2), "fill"))
        elif clave == 9:        # presion de aceite: aceitera con gota
            piezas.append((c.create_polygon(cx - 14, cy - 2, cx + 4, cy - 2, cx + 8, cy + 6, cx - 14, cy + 6,
                                            outline=""), "fill"))
            piezas.append((c.create_line(cx + 4, cy - 2, cx + 14, cy - 6, width=3), "fill"))
            piezas.append((c.create_rectangle(cx - 9, cy - 6, cx - 3, cy - 2, outline=""), "fill"))
            piezas.append((c.create_oval(cx + 13, cy + 1, cx + 17, cy + 7, outline=""), "fill"))
        elif clave == 10:       # frenos: circulo con signo de admiracion entre parentesis
            piezas.append((c.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, width=2), "outline"))
            piezas.append((c.create_arc(cx - 15, cy - 13, cx + 15, cy + 13, start=120, extent=120, style="arc",
                                        width=2), "outline"))
            piezas.append((c.create_arc(cx - 15, cy - 13, cx + 15, cy + 13, start=-60, extent=120, style="arc",
                                        width=2), "outline"))
            piezas.append((c.create_text(cx, cy, text="!", font=(FUENTE, 11, "bold")), "fill"))
        return piezas

    def _dibujar_testigos(self):
        c = self.canvas
        x0, y0, x1, y1 = BARRA
        c.create_rectangle(x0, y0, x1, y1, fill="#0c0c0d", outline=CAPOTA_BORDE, width=2)
        for numero, (cx, cy, ancho, alto) in TESTIGOS.items():
            critica = ELEMENTOS[numero]["categoria"] == CRITICA
            if critica:
                forma = c.create_rectangle(cx - ancho / 2, cy - alto / 2 - 4, cx + ancho / 2, cy + alto / 2 - 4,
                                           fill=COLOR_APAGADO, outline=COLOR_ROJO, width=3)
            else:
                forma = c.create_oval(cx - ancho / 2, cy - alto / 2 - 4, cx + ancho / 2, cy + alto / 2 - 4,
                                      fill=COLOR_APAGADO, outline=BISEL_LUZ, width=2)
            iconos = {clave: self._simbolo(clave, cx, cy - 4)
                      for clave in (("IZQ", "DER") if numero == 6 else (numero,))}
            c.create_text(cx, cy + alto / 2 + 5, text=f"{numero} {NOMBRES_TESTIGO[numero]}", fill=MARCA_MENOR,
                          font=(FUENTE, 7, "bold"))
            self.items[numero] = {"forma": forma, "iconos": iconos, "ultimo": None}

    def _dibujar_estado(self):
        c = self.canvas
        c.create_rectangle(22, 436, 380, 490, fill="#0c0c0d", outline=CAPOTA_BORDE, width=2)
        c.create_text(36, 451, text="MOTOR", anchor="w", fill=MARCA_MENOR, font=(FUENTE, 8, "bold"))
        self._txt_motor = c.create_text(36, 472, text="", anchor="w", font=(FUENTE, 15, "bold"))
        c.create_text(120, 451, text="RELOJ", anchor="w", fill=MARCA_MENOR, font=(FUENTE, 8, "bold"))
        self._txt_reloj = c.create_text(120, 472, text="", anchor="w", fill=VERDE_TEXTO, font=(FUENTE, 13, "bold"))
        self._txt_fuente = c.create_text(232, 462, text="FUENTE: MANUAL", anchor="w", fill=COLOR_TEXTO,
                                         font=(FUENTE, 8, "bold"))

    def _icono_extra(self, clave, cx, cy):
        """Simbolos de los testigos adicionales. Devuelve [(item, atributo que toma el color)]."""
        c, piezas = self.canvas, []
        if clave == 12:         # puerta: contorno de la puerta con su manija
            piezas.append((c.create_polygon(cx - 9, cy - 9, cx + 5, cy - 9, cx + 10, cy - 3, cx + 10, cy + 10,
                                            cx - 9, cy + 10, fill="", width=2), "outline"))
            piezas.append((c.create_line(cx + 1, cy + 1, cx + 7, cy + 1, width=2), "fill"))
        elif clave == 13:       # cinturon: persona sentada con la banda cruzada
            piezas.append((c.create_oval(cx - 4, cy - 12, cx + 2, cy - 6, outline=""), "fill"))
            piezas.append((c.create_line(cx - 1, cy - 5, cx - 1, cy + 5, cx + 6, cy + 5, cx + 6, cy + 11, width=3),
                           "fill"))
            piezas.append((c.create_line(cx - 7, cy - 6, cx + 6, cy + 3, width=2), "fill"))
        elif clave == 15:       # proteccion del motor
            piezas.append((c.create_text(cx, cy, text="STOP", font=(FUENTE, 11, "bold")), "fill"))
        elif clave == 16:       # bateria con sus bornes + y -
            piezas.append((c.create_rectangle(cx - 12, cy - 6, cx + 12, cy + 8, width=2), "outline"))
            piezas.append((c.create_rectangle(cx - 9, cy - 10, cx - 4, cy - 6, outline=""), "fill"))
            piezas.append((c.create_rectangle(cx + 4, cy - 10, cx + 9, cy - 6, outline=""), "fill"))
            piezas.append((c.create_text(cx - 6, cy + 1, text="-", font=(FUENTE, 9, "bold")), "fill"))
            piezas.append((c.create_text(cx + 6, cy + 1, text="+", font=(FUENTE, 9, "bold")), "fill"))
        else:                   # reserva de combustible: surtidor
            piezas.append((c.create_rectangle(cx - 6, cy - 7, cx + 2, cy + 7, outline=""), "fill"))
            piezas.append((c.create_line(cx + 2, cy - 5, cx + 6, cy - 2, cx + 6, cy + 5, width=2), "fill"))
        return piezas

    def _dibujar_extras(self):
        """Franja de los elementos 12-15 (Etapa 18): llave, combustible, puerta, cinturon y proteccion."""
        c = self.canvas
        x0, y0, x1, y1 = FRANJA
        c.create_rectangle(x0, y0, x1, y1, fill="#0c0c0d", outline=CAPOTA_BORDE, width=2)
        c.create_text(36, 511, text="LLAVE", anchor="w", fill=MARCA_MENOR, font=(FUENTE, 8, "bold"))
        self._txt_llave = c.create_text(36, 538, text="", anchor="w", font=(FUENTE, 12, "bold"))
        # Elemento 14: medidor de barra, con la zona de reserva pintada y marcas E, 1/2 y F.
        bx0, by0, bx1, by1 = COMBUSTIBLE
        c.create_text(bx0, 511, text="14 COMBUSTIBLE", anchor="w", fill=MARCA_MENOR, font=(FUENTE, 8, "bold"))
        c.create_rectangle(bx0, by0, bx1, by1, fill="#161616", outline=BISEL_LUZ, width=1)
        c.create_rectangle(bx0, by1 + 2, bx0 + (bx1 - bx0) * 0.12, by1 + 4, fill=ZONA_AMBAR, outline="")
        for fraccion, texto in ((0, "E"), (0.25, ""), (0.5, "1/2"), (0.75, ""), (1, "F")):
            x = bx0 + (bx1 - bx0) * fraccion
            c.create_line(x, by1 + 2, x, by1 + 7, fill=NUMERO if texto else MARCA_MENOR)
            if texto:
                c.create_text(x, by1 + 14, text=texto, fill=NUMERO, font=(FUENTE, 7, "bold"))
        barra = c.create_rectangle(bx0 + 1, by0 + 1, bx0 + 1, by1 - 1, fill=COLOR_NORMAL, outline="")
        valor = c.create_text(bx1 + 10, 535, text="", anchor="w", fill=COLOR_TEXTO, font=(FUENTE, 9, "bold"))
        rx, ry = 566, FILA_EXTRA
        reserva = c.create_rectangle(rx - 15, ry - 12, rx + 15, ry + 12, fill=COLOR_APAGADO, outline=BISEL_LUZ, width=1)
        c.create_text(rx, ry + 20, text="RESERVA", fill=MARCA_MENOR, font=(FUENTE, 6, "bold"))
        self.extras = {14: {"barra": barra, "valor": valor, "reserva": reserva,
                            "iconos": self._icono_extra("reserva", rx, ry), "ultimo": None}}
        for numero, (cx, ancho, alto, nombre) in EXTRA.items():
            cy = FILA_EXTRA
            if ELEMENTOS_EXTRA[numero]["categoria"] == CRITICA:
                forma = c.create_rectangle(cx - ancho / 2, cy - alto / 2, cx + ancho / 2, cy + alto / 2,
                                           fill=COLOR_APAGADO, outline=COLOR_ROJO, width=3)
            else:
                forma = c.create_oval(cx - ancho / 2, cy - alto / 2, cx + ancho / 2, cy + alto / 2,
                                      fill=COLOR_APAGADO, outline=BISEL_LUZ, width=2)
            etiqueta = c.create_text(cx, cy + alto / 2 + 9, text=nombre, fill=MARCA_MENOR, font=(FUENTE, 6, "bold"))
            self.extras[numero] = {"forma": forma, "iconos": self._icono_extra(numero, cx, cy), "etiqueta": etiqueta,
                                   "ultimo": None}
        self._txt_detalle = c.create_text(922, FILA_EXTRA, text="", anchor="w", fill=COLOR_ROJO,
                                          font=(FUENTE, 10, "bold"))

    # ------------------------------------------------------------------ controles

    def _crear_controles(self):
        estilo = {"bg": FONDO, "fg": COLOR_TEXTO, "font": (FUENTE, 9, "bold")}
        deslizadores = tk.Frame(self.raiz, bg=FONDO)
        deslizadores.grid(row=1, column=0, sticky="nw", padx=10)
        for i, (setter, etiqueta, minimo, maximo, resolucion, convertir) in enumerate(DESLIZADORES):
            var = tk.DoubleVar(value=minimo)
            manejador = (lambda s=setter, c=convertir, v=var: self.enviar(s, c(v.get())))
            control = tk.Scale(deslizadores, label=etiqueta, from_=minimo, to=maximo, resolution=resolucion,
                               orient="horizontal", length=290, variable=var, command=lambda _v, m=manejador: m(),
                               troughcolor="#2e2e33", activebackground=ZONA_AMBAR, sliderrelief="raised", bd=0,
                               highlightthickness=0, **estilo)
            control.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 14), pady=2)
            self._controles.append(control)
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        interruptores = tk.Frame(self.raiz, bg=FONDO)
        interruptores.grid(row=1, column=1, sticky="nw", padx=10)
        botones = {"selectcolor": "#2e2e33", "activebackground": FONDO, "activeforeground": COLOR_TEXTO,
                   "highlightthickness": 0, "bd": 0, **estilo}
        for i, (setter, texto) in enumerate(INTERRUPTORES):
            var = tk.BooleanVar(value=False)
            manejador = (lambda s=setter, v=var: self.enviar(s, bool(v.get())))
            control = tk.Checkbutton(interruptores, text=texto, variable=var, command=manejador, **botones)
            control.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 12), pady=4)
            self._controles.append(control)
            self.variables[setter] = var
            self._manejadores[setter] = manejador

        var = tk.StringVar(value="OFF")
        manejador = (lambda v=var: self.enviar("set_direccional", v.get()))
        fila = tk.Frame(interruptores, bg=FONDO)
        fila.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        tk.Label(fila, text="6 Direccional", **estilo).pack(side="left", padx=(0, 10))
        for opcion in ("IZQ", "OFF", "DER"):
            control = tk.Radiobutton(fila, text=opcion, value=opcion, variable=var, command=manejador, **botones)
            control.pack(side="left", padx=(0, 8))
            self._controles.append(control)
        self.variables["set_direccional"] = var
        self._manejadores["set_direccional"] = manejador

    def _dibujar_aceite(self):
        """Elemento 17: temperatura de aceite en barra, bajo el turbo, con la zona roja desde 130 C."""
        c = self.canvas
        x0, y0, x1, y1 = ACEITE
        escala = lambda t: x0 + (x1 - x0) * (t - 40) / 120  # noqa: E731
        c.create_rectangle(x0, y0, x1, y1, fill="#161616", outline=BISEL_LUZ, width=1)
        c.create_rectangle(escala(130), y1 + 2, x1, y1 + 4, fill=ZONA_ROJA, outline="")
        for t in (40, 100, 160):
            c.create_line(escala(t), y1 + 2, escala(t), y1 + 6, fill=NUMERO)
            c.create_text(escala(t), y1 + 12, text=str(t), fill=MARCA_MENOR, font=(FUENTE, 6, "bold"))
        barra = c.create_rectangle(x0 + 1, y0 + 1, x0 + 1, y1 - 1, fill=COLOR_NORMAL, outline="")
        etiqueta = c.create_text((x0 + x1) / 2, y0 - 8, text="17 TEMP. ACEITE", fill=MARCA_MENOR,
                                 font=(FUENTE, 7, "bold"))
        self.extras[17] = {"barra": barra, "etiqueta": etiqueta, "ultimo": None}

    def avisar(self, texto):
        """Muestra un aviso del sistema que permanece hasta que se reemplace."""
        self.aviso.configure(text=texto)

    def modo_externo(self, origen):
        """Los valores llegan de un archivo: los controles solo muestran lo leido."""
        for control in self._controles:
            control.configure(state="disabled")
        self.canvas.itemconfigure(self._txt_fuente, text=f"FUENTE: {origen}"[:30])

    def enviar(self, setter, valor):
        """Envia un valor a EstadoCluster; si se rechaza, lo muestra en pantalla."""
        try:
            getattr(self.estado, setter)(valor)
        except (TypeError, ValueError) as error:
            self.mensaje.configure(text=f"Entrada rechazada: {error}")
            return False
        self.mensaje.configure(text="")
        return True

    def aplicar_externo(self, setter, valor):
        """Aplica un valor ya validado del archivo de datos directamente al modelo
        (sin pasar por la resolucion de los deslizadores) y lo refleja en el control."""
        getattr(self.estado, setter)(valor)
        if setter in self.variables:      # las claves opcionales (12-15, contacto) no tienen control manual
            self.variables[setter].set(valor)
        return True

    def ajustar(self, setter, valor):
        """Mueve un control como lo haria el usuario (usado por las pruebas)."""
        self.variables[setter].set(valor)
        return self._manejadores[setter]()

    # ------------------------------------------------------------------ refresco

    def _puntos_aguja(self, it, fraccion):
        cx, cy = it["centro"]
        r = it["radio"]
        a = _angulo(min(1.0, max(0.0, fraccion)))
        largo, cola = r * 0.86, r * 0.20
        base = max(3.0, r * 0.035)
        ux, uy = math.cos(a), -math.sin(a)          # direccion de la punta (y de pantalla hacia abajo)
        px, py = -uy, ux                            # perpendicular
        return (cx + ux * largo, cy + uy * largo,
                cx + px * base, cy + py * base,
                cx - ux * cola + px * base * 1.6, cy - uy * cola + py * base * 1.6,
                cx - ux * cola - px * base * 1.6, cy - uy * cola - py * base * 1.6,
                cx - px * base, cy - py * base)

    def refrescar(self):
        v = vista(self.estado)
        for numero in range(1, 6):
            d, it = v[numero], self.items[numero]
            self.canvas.itemconfigure(it["valor"], text=FORMATOS[numero].format(d["valor"]), fill=d["color"])
            # Inercia de instrumento analogico: la aguja recorre una parte del camino en cada refresco
            # (la cifra si se muestra exacta). El color cambia de inmediato.
            objetivo = d["fraccion"]
            mostrada = self._mostrada[numero] + (objetivo - self._mostrada[numero]) * self.inercia
            if abs(objetivo - mostrada) < 0.002:
                mostrada = objetivo
            self._mostrada[numero] = mostrada
            clave = (round(mostrada, 4), d["color"])
            if it["ultimo"] == clave:
                continue
            it["ultimo"] = clave
            self.canvas.coords(it["aguja"], *self._puntos_aguja(it, mostrada))
            self.canvas.itemconfigure(it["aguja"], fill=d["color"])
            if numero == 5:
                # R05: el contorno del turbo se pinta ambar mientras la presion supera 1.5 bar.
                ambar = d["color"] != COLOR_NORMAL
                self.canvas.itemconfigure(it["arco"], outline=d["color"] if ambar else BISEL_LUZ,
                                          width=5 if ambar else 2)

        for numero in range(6, 11):
            d, it = v[numero], self.items[numero]
            self.canvas.itemconfigure(it["forma"], fill=d["color"])
            lado = d.get("lado") if numero == 6 else numero
            clave = (d["encendido"], lado)
            if it["ultimo"] == clave:
                continue
            it["ultimo"] = clave
            visible = "DER" if lado == "DER" else ("IZQ" if numero == 6 else numero)
            color = ICONO_ENCENDIDO if d["encendido"] else ICONO_APAGADO
            for nombre, piezas in it["iconos"].items():
                for pieza, atributo in piezas:
                    self.canvas.itemconfigure(pieza, state="normal" if nombre == visible else "hidden",
                                              **{atributo: color})
        motor = self.estado.motor_activo
        self.canvas.itemconfigure(self._txt_motor, text="ON" if motor else "OFF",
                                  fill=VERDE_TEXTO if motor else COLOR_TEXTO)
        self.canvas.itemconfigure(self._txt_reloj, text=f"{self.estado.reloj.ahora_ms() / 1000:.1f} s")
        self.canvas.itemconfigure(self.items[11]["valor"], text=vista_odometro(self.estado)["texto"])
        self._refrescar_extras()
        return v

    def _refrescar_extras(self):
        """Elementos 12-15: solo se redibuja lo que cambio, como en los testigos 6-10."""
        c, v = self.canvas, vista_extra(self.estado)
        for numero in (12, 13, 15, 16):
            d, it = v[numero], self.extras[numero]
            voltaje = d.get("voltaje")
            clave = (d["encendido"], d["color"], d["sin_dato"], None if voltaje is None else round(voltaje, 1))
            if it["ultimo"] == clave:
                continue
            it["ultimo"] = clave
            c.itemconfigure(it["forma"], fill=d["color"])
            for pieza, atributo in it["iconos"]:
                c.itemconfigure(pieza, **{atributo: ICONO_ENCENDIDO if d["encendido"] else ICONO_APAGADO})
            c.itemconfigure(it["etiqueta"], fill=ICONO_APAGADO if d["sin_dato"] else MARCA_MENOR)
            if numero == 16:      # el voltimetro va en la etiqueta del testigo
                c.itemconfigure(it["etiqueta"], text="16 CARGA" if voltaje is None else f"16 CARGA {voltaje:.1f} V")
        d, it = v[14], self.extras[14]
        clave = (None if d["sin_dato"] else round(d["valor"], 1), d["color"], d["reserva"]["encendido"])
        if it["ultimo"] != clave:
            it["ultimo"] = clave
            bx0, by0, bx1, by1 = COMBUSTIBLE
            c.coords(it["barra"], bx0 + 1, by0 + 1, bx0 + 1 + (bx1 - bx0 - 2) * d["fraccion"], by1 - 1)
            c.itemconfigure(it["barra"], fill=d["color"])
            c.itemconfigure(it["valor"], fill=d["color"] if not d["sin_dato"] else ICONO_APAGADO,
                            text="sin dato" if d["sin_dato"] else f"{d['valor']:.0f} %  {d['litros']:.0f} L")
            c.itemconfigure(it["reserva"], fill=d["reserva"]["color"])
            for pieza, atributo in it["iconos"]:
                c.itemconfigure(pieza, **{atributo: ICONO_ENCENDIDO if d["reserva"]["encendido"] else ICONO_APAGADO})
        d, it = v[17], self.extras[17]
        clave = (None if d["sin_dato"] else round(d["valor"]), d["color"])
        if it["ultimo"] != clave:
            it["ultimo"] = clave
            x0, y0, x1, y1 = ACEITE
            c.coords(it["barra"], x0 + 1, y0 + 1, x0 + 1 + (x1 - x0 - 2) * d["fraccion"], y1 - 1)
            c.itemconfigure(it["barra"], fill=d["color"])
            c.itemconfigure(it["etiqueta"], text="17 TEMP. ACEITE" if d["sin_dato"] else f"17 TEMP. ACEITE {d['valor']:.0f} C",
                            fill=ICONO_APAGADO if d["sin_dato"] else (d["color"] if d["color"] == COLOR_ROJO else MARCA_MENOR))
        if v[15]["texto"]:
            detalle, color = v[15]["texto"], COLOR_ROJO
        elif v[12]["encendido"] and v[12]["detalle"]:
            detalle, color = f"PUERTA {v[12]['detalle']}", v[12]["color"]
        else:
            detalle, color = "", COLOR_TEXTO
        c.itemconfigure(self._txt_detalle, text=detalle, fill=color)
        llave = v["llave"]["estado"]
        c.itemconfigure(self._txt_llave, text=llave,
                        fill={"MOTOR": VERDE_TEXTO, "CONTACTO": COLOR_AMBAR}.get(llave, COLOR_TEXTO))

    def ciclo(self):
        if self.antes_del_tick is not None:
            self.antes_del_tick()
        self.estado.tick()
        if self.despues_del_tick is not None:
            self.despues_del_tick(self.estado)
        return self.refrescar()

    def _programar(self):
        # El siguiente ciclo se programa aunque este falle: un error de un ciclo se
        # registra (report_callback_exception) pero no congela el tablero (DEF-06).
        try:
            self.ciclo()
        finally:
            self._id_after = self.raiz.after(self.periodo_ms, self._programar)

    def detener(self):
        if self._id_after is not None:
            self.raiz.after_cancel(self._id_after)
            self._id_after = None
