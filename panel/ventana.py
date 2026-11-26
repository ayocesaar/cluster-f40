"""Panel de control (administrador) del cluster F40.

Es un proceso aparte que escribe datos/vehiculo.conf, igual que tools/escribir_dato.py
y tools/simulador.py: el cluster no cambia y sigue recibiendo sus datos como entrada
externa. El panel reemplaza los comandos de la terminal por mandos de cabina:

- Cabina austera inspirada en el F40: piso de fibra al descubierto, pedales de aluminio
  perforado, compuerta metalica de cambios y llave de contacto.
- Fisica simplificada (panel/fisica.py): pedales y marcha -> velocidad, rpm, turbo,
  aceite y temperatura coherentes entre si.
- Interruptores de luces, fallas de sensores y entradas invalidas para probar R01-R08.
- Atajos de comandos (pruebas, aceptacion, ataque QA, P12, diagnostico) con su salida
  en una consola, y los escenarios de aceptacion reproducidos en vivo sobre el tablero.

- Etapa 18: llave de contacto y arranque separados, puertas y cinturon, una ECU simulada
  (panel/ecu.py) que no deja arrancar con fuga de aceite y detiene el motor ante
  sobretemperatura, sobrepresion o falta de aceite, un TALLER para reparar, y el banco de
  liberacion de produccion (panel/liberacion.py) con el ciclo ECE-15 en vivo.

Teclas: W/flecha arriba acelerador, S/flecha abajo freno, C embrague, 1-5/R/N marchas,
K llave (contacto), M arranque/paro, P/O puerta conductor/pasajero, B cinturon,
L luces altas, Z/X direccional, H intermitentes, U silencio.

Etapa 19: sonido del motor sintetizado por codigo (panel/sonido.py). Con --sonido auto suena
en las bocinas del equipo; con --sonido HOST:PUERTO el estado viaja por un socket a
tools/bocina.py (por ejemplo, en Windows a traves de un tunel SSH)."""

import os
import pathlib
import subprocess
import sys
import time
import tkinter as tk

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))

from aceptacion.escenarios import cargar as cargar_escenarios  # noqa: E402
from escribir_dato import exclusivo  # noqa: E402
from panel import comandos, liberacion  # noqa: E402
from panel import sonido as sonido_motor  # noqa: E402
from panel.ecu import Ecu  # noqa: E402
from panel.fisica import TANQUE_L, Vehiculo, velocidad_maxima  # noqa: E402
from sistema import config as configuracion  # noqa: E402
from sistema.lector import CLAVES, CLAVES_EXTRA, escribir_atomico, escribir_texto_atomico, formatear  # noqa: E402

FUENTE = "Courier New"
FONDO = "#121214"
SECCION = "#1b1b1f"
ROJO_TELA = "#b3191e"
TEXTO = "#dcdce2"
TENUE = "#8a8a96"
VERDE = "#4fd06b"
AMBAR = "#ffb02e"
ROJO = "#ff4d4d"
FIBRA_A = "#26251f"
FIBRA_B = "#302e26"
ALUMINIO = "#aeb2b7"
ALUMINIO_LUZ = "#d9dce0"
ALUMINIO_SOMBRA = "#6b6f74"
BOTON = "#2a2a31"
BOTON_ACTIVO = "#3b3b45"

PEDALES = (  # nombre, centro x, ancho, alto, tecla
    ("embrague", 105, 88, 104, "C"),
    ("freno", 245, 112, 96, "S / abajo"),
    ("acelerador", 375, 62, 146, "W / arriba"),
)
SUBIDA, BAJADA = 5.0, 7.0          # pedal: unidades por segundo al pisar y al soltar
COMPUERTA = {"R": (40, 38), "1": (40, 152), "2": (110, 38), "3": (110, 152), "4": (180, 38),
             "5": (180, 152), "N": (110, 95)}
SEGURO = {"motor": False, "velocidad": 0.0, "rpm": 0, "presion_aceite": 0.0, "temp_agua": 40.0,
          "presion_turbo": 0.0, "direccional": "OFF", "luces_altas": False, "emergencia": False,
          "falla_frenos": False}
CSV_ACEPTACION = RAIZ / "tests" / "datos" / "escenarios_aceptacion.csv"


def _boton(padre, texto, comando, ancho=None, color=BOTON, **extra):
    b = tk.Button(padre, text=texto, command=comando, bg=color, fg=TEXTO, activebackground=BOTON_ACTIVO,
                  activeforeground="#ffffff", relief="flat", bd=0, highlightthickness=1,
                  highlightbackground="#3a3a42", font=(FUENTE, 9, "bold"), padx=6, pady=3, **extra)
    if ancho:
        b.configure(width=ancho)
    return b


def _seccion(padre, titulo):
    marco = tk.Frame(padre, bg=SECCION, highlightthickness=1, highlightbackground="#2c2c34")
    tk.Label(marco, text=f" {titulo} ", bg=ROJO_TELA, fg="#ffffff", font=(FUENTE, 10, "bold"),
             anchor="w").pack(fill="x")
    return marco


class Panel:
    PERIODO_MS = 50
    ESCRITURA_S = 0.1          # el cluster lee cada 100 ms
    PAUSA_INYECCION_S = 3.0    # tiempo que una entrada invalida queda en el archivo
    PASO_ESCENARIO_MIN_S = 1.2  # para que el profesor vea cada paso del escenario

    def __init__(self, raiz, ruta_datos=None, dir_logs=None, reloj=time.monotonic, sonido="no", salida_sonido=None):
        self.raiz = raiz
        self.reloj = reloj
        self.sonido = sonido_motor.crear(sonido, salida_sonido)
        self.silencio = False
        cfg = configuracion.cargar()
        self.ruta = pathlib.Path(ruta_datos) if ruta_datos else cfg.archivo_datos
        self.dir_logs = pathlib.Path(dir_logs) if dir_logs else cfg.dir_logs
        self.vehiculo = Vehiculo()
        self.ecu = Ecu()
        self.conductor = None                # robot del ciclo ECE-15 en vivo
        self.t_ciclo = 0.0
        self.km_ciclo = 0.0
        self.pisando = {"embrague": False, "freno": False, "acelerador": False}
        self.modo = "fisica"                 # fisica | escenario | recorrido | ciclo
        self.ultimo_escrito = None
        self.escrituras = 0
        self._proxima_escritura = 0.0
        self.pausa_hasta = 0.0
        self.valores_escenario = dict(SEGURO)
        self.pasos_pendientes = []
        self._proximo_paso = 0.0
        self.recorrido = None
        self.tablero_lanzado = None
        self.ejecutor = comandos.Ejecutor()
        self._dibujado = {}
        self._proxima_bitacora = 0.0
        try:
            self.escenarios = cargar_escenarios(CSV_ACEPTACION)
        except Exception:  # noqa: BLE001 - sin CSV el panel funciona sin escenarios
            self.escenarios = {}

        raiz.title("Panel de control - Cluster F40 (simulado)")
        raiz.configure(bg=FONDO)
        raiz.geometry("1420x830")
        raiz.minsize(1240, 760)
        self._construir()
        raiz.bind_all("<KeyPress>", self._tecla_abajo)
        raiz.bind_all("<KeyRelease>", self._tecla_arriba)
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.registrar(f"Panel listo. Escribe en {self.ruta}. Teclas: W acelerador, S freno, C embrague, "
                       "1-5/R/N marchas, K llave, M arranque, P/O puertas, B cinturon.")
        self.registrar(f"Sonido del motor: {self.sonido.descripcion}" + (" (U silencia)" if self.sonido.activo else ""))
        self._id_after = raiz.after(self.PERIODO_MS, self._ciclo)

    # ================================================================ construccion
    def _construir(self):
        r = self.raiz
        barra = tk.Frame(r, bg="#0b0b0d")
        barra.pack(fill="x")
        tk.Label(barra, text="  PANEL DE CONTROL  ·  CLUSTER F40 (1987)", bg="#0b0b0d", fg=TEXTO,
                 font=(FUENTE, 13, "bold")).pack(side="left", pady=6)
        self.lbl_tablero = tk.Label(barra, text="", bg="#0b0b0d", fg=TENUE, font=(FUENTE, 10, "bold"))
        self.lbl_tablero.pack(side="right", padx=10)
        self.lbl_sonido = tk.Label(barra, text="", bg="#0b0b0d", fg=TENUE, font=(FUENTE, 9, "bold"))
        self.lbl_sonido.pack(side="right", padx=8)
        _boton(barra, "Silencio [U]", self.alternar_silencio).pack(side="right", padx=3)
        _boton(barra, "Cerrar tablero", self.cerrar_tablero).pack(side="right", padx=3)
        _boton(barra, "Abrir tablero", self.abrir_tablero, color="#1f3d27").pack(side="right", padx=3)

        cuerpo = tk.Frame(r, bg=FONDO)
        cuerpo.pack(fill="both", expand=True, padx=8, pady=6)
        izquierda = tk.Frame(cuerpo, bg=FONDO)
        centro = tk.Frame(cuerpo, bg=FONDO)
        derecha = tk.Frame(cuerpo, bg=FONDO)
        izquierda.pack(side="left", fill="y")
        centro.pack(side="left", fill="y", padx=8)
        derecha.pack(side="left", fill="both", expand=True)
        self._cabina(izquierda)
        self._mandos(centro)
        self._consola(derecha)

        self.lbl_estado = tk.Label(r, text="", bg="#0b0b0d", fg=TENUE, font=(FUENTE, 9), anchor="w")
        self.lbl_estado.pack(fill="x", side="bottom")

    def _cabina(self, padre):
        s = _seccion(padre, "CABINA · pedales (mantener pulsado)")
        s.pack(fill="x")
        self.cv = tk.Canvas(s, width=480, height=300, bg=FIBRA_A, highlightthickness=0)
        self.cv.pack()
        for y in range(0, 300, 6):                       # piso de fibra al descubierto (tejido en sarga)
            for x in range(0, 480, 6):
                if ((x // 6) + (y // 6)) % 4 < 2:
                    self.cv.create_rectangle(x, y, x + 6, y + 6, fill=FIBRA_B, outline="")
        self.cv.create_rectangle(0, 0, 480, 18, fill="#0e0e0e", outline="")    # borde del tablero
        for nombre, cx, *_ in PEDALES:
            self.cv.tag_bind(nombre, "<ButtonPress-1>", lambda _e, n=nombre: self._pisar_raton(n, True))
        self.cv.bind("<ButtonRelease-1>", lambda _e: [self._pisar_raton(n, False) for n in self.pisando])

        abajo = tk.Frame(s, bg=SECCION)
        abajo.pack(fill="x", pady=4)
        self.cv_cambios = tk.Canvas(abajo, width=220, height=190, bg=SECCION, highlightthickness=0)
        self.cv_cambios.pack(side="left", padx=6)
        self._dibujar_compuerta()
        lado = tk.Frame(abajo, bg=SECCION)
        lado.pack(side="left", fill="both", expand=True)
        self.btn_llave = tk.Button(lado, text="LLAVE\n[K]", command=self.alternar_contacto, width=12, height=2,
                                   bg="#2b1414", fg=TEXTO, activebackground="#4a1c1c", relief="ridge", bd=3,
                                   font=(FUENTE, 10, "bold"))
        self.btn_llave.pack(pady=(6, 3))
        self.btn_contacto = tk.Button(lado, text="ARRANQUE\n[M]", command=self.alternar_motor, width=12, height=2,
                                      bg="#2b1414", fg=TEXTO, activebackground="#4a1c1c", relief="ridge", bd=3,
                                      font=(FUENTE, 10, "bold"))
        self.btn_contacto.pack(pady=(0, 4))
        self.var_embrague_auto = tk.BooleanVar(value=True)
        tk.Checkbutton(lado, text="Embrague automatico\nal cambiar", variable=self.var_embrague_auto, bg=SECCION,
                       fg=TEXTO, selectcolor=BOTON, activebackground=SECCION, activeforeground=TEXTO,
                       font=(FUENTE, 9), justify="left").pack()

        seguridad = _seccion(padre, "SEGURIDAD Y TALLER")
        seguridad.pack(fill="x", pady=6)
        fila = tk.Frame(seguridad, bg=SECCION)
        fila.pack(fill="x", pady=3)
        estilo = dict(bg=BOTON, fg=TEXTO, selectcolor="#7a3b10", activebackground=BOTON_ACTIVO, indicatoron=False,
                      font=(FUENTE, 9, "bold"), relief="raised", bd=2, padx=5, pady=3)
        self.var_puertas = {1: tk.BooleanVar(), 2: tk.BooleanVar()}
        self.var_cinturon = tk.BooleanVar()
        tk.Checkbutton(fila, text="Puerta cond. [P]", variable=self.var_puertas[1], command=self._seguridad,
                       **estilo).pack(side="left", padx=2)
        tk.Checkbutton(fila, text="Puerta pas. [O]", variable=self.var_puertas[2], command=self._seguridad,
                       **estilo).pack(side="left", padx=2)
        tk.Checkbutton(fila, text="Cinturon [B]", variable=self.var_cinturon, command=self._seguridad,
                       **dict(estilo, selectcolor="#1f5a2c")).pack(side="left", padx=2)
        fila = tk.Frame(seguridad, bg=SECCION)
        fila.pack(fill="x", pady=(0, 4))
        for texto, accion in (("Reparar fallas", "reparar"), ("Rellenar aceite", "aceite"),
                              ("Llenar tanque", "tanque"), ("Reserva 10 L", "reserva")):
            _boton(fila, texto, lambda a=accion: self.taller(a)).pack(side="left", padx=2)

        teclas = _seccion(padre, "TECLAS")
        teclas.pack(fill="x")
        for linea in ("W/arriba acelerador  S/abajo freno  C embrague  1-5 R N",
                      "K llave  M arranque  P/O puertas  B cinturon  L altas",
                      "Z/X direccional  H intermitentes (pedales: tambien raton)"):
            tk.Label(teclas, text=linea, bg=SECCION, fg=TEXTO, font=(FUENTE, 9), anchor="w").pack(fill="x", padx=6)

    def _dibujar_compuerta(self):
        c = self.cv_cambios
        c.create_rectangle(6, 6, 214, 184, fill="#9a9ea3", outline="#d0d3d6", width=2)   # placa metalica
        for x, y in ((14, 14), (206, 14), (14, 176), (206, 176)):
            c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#6b6f74", outline="")       # tornillos
        for x in (40, 110, 180):
            c.create_line(x, 38, x, 152, width=14, fill="#1a1a1a", capstyle="round")
        c.create_line(40, 95, 180, 95, width=14, fill="#1a1a1a", capstyle="round")
        for marcha, (x, y) in COMPUERTA.items():
            if marcha != "N":
                dy = -24 if y < 95 else 24
                c.create_text(x, y + dy, text=marcha, font=(FUENTE, 12, "bold"), fill="#111111")
            c.create_oval(x - 16, y - 16, x + 16, y + 16, outline="", fill="", tags=("zona", f"m_{marcha}"))
            c.tag_bind(f"m_{marcha}", "<Button-1>", lambda _e, m=marcha: self.cambiar(m))
        self.pomo = c.create_oval(0, 0, 0, 0, fill="#0c0c0c", outline="#4a4a4a", width=2)
        self.pomo_txt = c.create_text(0, 0, text="", fill="#e8e8e8", font=(FUENTE, 10, "bold"))

    def _mandos(self, padre):
        luces = _seccion(padre, "LUCES")
        luces.pack(fill="x")
        fila = tk.Frame(luces, bg=SECCION)
        fila.pack(fill="x", pady=4)
        self.var_altas = tk.BooleanVar()
        self.var_emergencia = tk.BooleanVar()
        self.var_direccional = tk.StringVar(value="OFF")
        estilo = dict(bg=BOTON, fg=TEXTO, selectcolor="#55506a", activebackground=BOTON_ACTIVO, indicatoron=False,
                      font=(FUENTE, 9, "bold"), relief="raised", bd=2, padx=6, pady=4)
        tk.Checkbutton(fila, text="Altas [L]", variable=self.var_altas, command=self._luces, **estilo).pack(
            side="left", padx=3)
        tk.Checkbutton(fila, text="Intermit. [H]", variable=self.var_emergencia, command=self._luces,
                       **dict(estilo, selectcolor="#7a3b10")).pack(side="left", padx=3)
        fila2 = tk.Frame(luces, bg=SECCION)
        fila2.pack(fill="x", pady=(0, 6))
        tk.Label(fila2, text="Direccional:", bg=SECCION, fg=TEXTO, font=(FUENTE, 9)).pack(side="left", padx=3)
        for texto, valor in (("< IZQ [Z]", "IZQ"), ("OFF", "OFF"), ("DER [X] >", "DER")):
            tk.Radiobutton(fila2, text=texto, value=valor, variable=self.var_direccional, command=self._luces,
                           **dict(estilo, selectcolor="#1f5a2c")).pack(side="left", padx=2)

        fallas = _seccion(padre, "FALLAS (con su consecuencia real)")
        fallas.pack(fill="x", pady=6)
        self.var_fallas = {}
        for clave, texto in (("fuga_aceite", "Fuga de aceite: testigo 9 y no arranca"),
                             ("radiador", "Radiador: se calienta y la ECU lo detiene"),
                             ("sobrepresion_turbo", "Turbo: > 1.5 bar y corte del motor"),
                             ("frenos", "Frenos: testigo 10 y frena al 30 %"),
                             ("velocimetro", "Velocimetro: indica 5 % menos (R39)")):
            var = tk.BooleanVar()
            self.var_fallas[clave] = var
            tk.Checkbutton(fallas, text=texto, variable=var, command=self._fallas, bg=SECCION, fg=TEXTO,
                           selectcolor=BOTON, activebackground=SECCION, activeforeground=TEXTO, anchor="w",
                           font=(FUENTE, 9)).pack(fill="x", padx=4)

        invalidas = _seccion(padre, "ENTRADAS INVALIDAS (se restauran en 3 s)")
        invalidas.pack(fill="x")
        rejilla = tk.Frame(invalidas, bg=SECCION)
        rejilla.pack(fill="x", pady=4)
        for i, (texto, tipo) in enumerate((("Dato corrupto", "corrupto"), ("Fuera de rango", "fuera"),
                                           ("Borrar archivo", "borrar"), ("Permisos 666", "permisos"))):
            _boton(rejilla, texto, lambda t=tipo: self.inyectar(t), ancho=15).grid(row=i // 2, column=i % 2,
                                                                                   padx=3, pady=2)
        _boton(invalidas, "ESTADO SEGURO (todo apagado)", self.estado_seguro, color="#3a2a12").pack(
            fill="x", padx=4, pady=(2, 6))

        lecturas = _seccion(padre, "LECTURAS ENVIADAS AL TABLERO")
        lecturas.pack(fill="x", pady=6)
        self.lbl_lecturas = {}
        for clave in CLAVES:
            fila = tk.Frame(lecturas, bg=SECCION)
            fila.pack(fill="x", padx=4)
            tk.Label(fila, text=f"{clave}", bg=SECCION, fg=TENUE, font=(FUENTE, 9), width=15, anchor="w").pack(
                side="left")
            lbl = tk.Label(fila, text="-", bg=SECCION, fg=TEXTO, font=(FUENTE, 10, "bold"), anchor="w")
            lbl.pack(side="left")
            self.lbl_lecturas[clave] = lbl
        self.lbl_extra = {}
        for clave in (*CLAVES_EXTRA, "nivel_aceite", "temp_frenos"):
            fila = tk.Frame(lecturas, bg=SECCION)
            fila.pack(fill="x", padx=4)
            tk.Label(fila, text=clave, bg=SECCION, fg=TENUE, font=(FUENTE, 9), width=15, anchor="w").pack(side="left")
            lbl = tk.Label(fila, text="-", bg=SECCION, fg=TEXTO, font=(FUENTE, 10, "bold"), anchor="w")
            lbl.pack(side="left")
            self.lbl_extra[clave] = lbl
        self.lbl_escritura = tk.Label(lecturas, text="", bg=SECCION, fg=TENUE, font=(FUENTE, 8), anchor="w",
                                      justify="left")
        self.lbl_escritura.pack(fill="x", padx=4, pady=(2, 4))

    def _consola(self, padre):
        atajos = _seccion(padre, "ATAJOS DE COMANDOS (en lugar de la terminal)")
        atajos.pack(fill="x")
        for grupo, lista in comandos.ATAJOS:
            tk.Label(atajos, text=grupo, bg=SECCION, fg=TENUE, font=(FUENTE, 8, "bold"), anchor="w").pack(
                fill="x", padx=4, pady=(3, 0))
            fila = tk.Frame(atajos, bg=SECCION)
            fila.pack(fill="x", padx=4)
            for etiqueta, ayuda, comando in lista:
                b = _boton(fila, etiqueta, lambda c=comando, e=etiqueta: self.ejecutar(c, e))
                if not comandos.disponible(comando):
                    b.configure(state="disabled")
                b.pack(side="left", padx=2)
        tk.Label(atajos, text="Escenarios de aceptacion en vivo (mismo CSV que CA-01 a CA-10)", bg=SECCION, fg=TENUE,
                 font=(FUENTE, 8, "bold"), anchor="w").pack(fill="x", padx=4, pady=(3, 0))
        fila = tk.Frame(atajos, bg=SECCION)
        fila.pack(fill="x", padx=4, pady=(0, 6))
        nombres = list(self.escenarios) or ["(sin CSV)"]
        self.var_escenario = tk.StringVar(value=nombres[0])
        menu = tk.OptionMenu(fila, self.var_escenario, *nombres)
        menu.configure(bg=BOTON, fg=TEXTO, activebackground=BOTON_ACTIVO, highlightthickness=0, relief="flat",
                       font=(FUENTE, 9, "bold"))
        menu.pack(side="left", padx=2)
        _boton(fila, "Reproducir en el tablero", self.reproducir_escenario, color="#1f3d27").pack(side="left", padx=2)
        _boton(fila, "Recorrido 22 s", self.recorrido_automatico).pack(side="left", padx=2)
        _boton(fila, "Detener", self.detener_todo, color="#4a1c1c").pack(side="left", padx=2)
        tk.Label(atajos, text="Liberacion de produccion: pruebas de la epoca (R13-H, R39, ECE-15)", bg=SECCION,
                 fg=TENUE, font=(FUENTE, 8, "bold"), anchor="w").pack(fill="x", padx=4, pady=(3, 0))
        fila = tk.Frame(atajos, bg=SECCION)
        fila.pack(fill="x", padx=4, pady=(0, 6))
        _boton(fila, "Banco con las fallas actuales", self.banco_actual, color="#1f3d27").pack(side="left", padx=2)
        _boton(fila, "Ciclo ECE-15 en vivo (195 s)", self.ciclo_ece15).pack(side="left", padx=2)

        salida = _seccion(padre, "CONSOLA")
        salida.pack(fill="both", expand=True, pady=6)
        self.txt = tk.Text(salida, bg="#07070a", fg="#cfd2d8", insertbackground=TEXTO, font=(FUENTE, 9),
                           relief="flat", wrap="word", height=20)
        self.txt.pack(fill="both", expand=True, padx=2, pady=2)
        self.txt.tag_configure("ok", foreground=VERDE)
        self.txt.tag_configure("mal", foreground=ROJO)
        self.txt.tag_configure("cmd", foreground=AMBAR)
        self.txt.configure(state="disabled")

        bitacoras = _seccion(padre, "BITACORAS DEL TABLERO (en vivo)")
        bitacoras.pack(fill="x")
        self.txt_log = tk.Text(bitacoras, bg="#07070a", fg="#9fa3ab", font=(FUENTE, 8), relief="flat", height=9,
                               wrap="none")
        self.txt_log.pack(fill="x", padx=2, pady=2)
        self.txt_log.tag_configure("error", foreground=ROJO)
        self.txt_log.tag_configure("warn", foreground=AMBAR)
        self.txt_log.configure(state="disabled")

    # ================================================================ mandos
    def pisar(self, nombre, valor):
        """Fija un pedal (0 a 1); lo usan las pruebas."""
        setattr(self.vehiculo, nombre, max(0.0, min(1.0, float(valor))))

    def _pisar_raton(self, nombre, activo):
        self.pisando[nombre] = activo

    TECLAS = {"w": "acelerador", "up": "acelerador", "s": "freno", "down": "freno", "c": "embrague"}

    def _tecla_abajo(self, evento):
        k = evento.keysym.lower()
        if k in self.TECLAS:
            self.pisando[self.TECLAS[k]] = True
        elif k in ("1", "2", "3", "4", "5", "r", "n"):
            self.cambiar(k.upper())
        elif k == "m":
            self.alternar_motor()
        elif k == "k":
            self.alternar_contacto()
        elif k in ("p", "o"):
            var = self.var_puertas[1 if k == "p" else 2]
            var.set(not var.get())
            self._seguridad()
        elif k == "b":
            self.var_cinturon.set(not self.var_cinturon.get())
            self._seguridad()
        elif k == "u":
            self.alternar_silencio()
        elif k == "l":
            self.var_altas.set(not self.var_altas.get())
            self._luces()
        elif k == "h":
            self.var_emergencia.set(not self.var_emergencia.get())
            self._luces()
        elif k in ("z", "x"):
            lado = "IZQ" if k == "z" else "DER"
            self.var_direccional.set("OFF" if self.var_direccional.get() == lado else lado)
            self._luces()

    def _tecla_arriba(self, evento):
        k = evento.keysym.lower()
        if k in self.TECLAS:
            self.pisando[self.TECLAS[k]] = False

    def cambiar(self, marcha):
        if self.var_embrague_auto.get():
            self.vehiculo.embrague = 1.0          # se suelta solo en unos 150 ms
        elif self.vehiculo.motor and self.vehiculo.embrague < 0.5 and marcha != "N":
            self.estado("Pise el embrague (C) para cambiar de marcha")
            return False
        try:
            self.vehiculo.cambiar(marcha)
        except ValueError as error:
            self.estado(f"Cambio rechazado: {error}")
            return False
        self.estado(f"Marcha {marcha}")
        return True

    def alternar_motor(self):
        """M: arranca (pone la llave en contacto si hacia falta) o apaga el motor y quita la llave.
        La ECU decide si puede arrancar: con fuga de aceite, sin combustible o con una proteccion
        enclavada no arranca y la causa llega al tablero (testigo 15)."""
        v = self.vehiculo
        if v.motor:
            v.motor, v.contacto, v.marcha = False, False, "N"     # al apagar, la caja queda en neutral
            self.registrar("Contacto: motor APAGADO (R01)")
            return True
        v.contacto = True
        motivo = self.ecu.motivo_sin_arranque(v)
        if motivo:
            self.registrar(f"No arranca: {motivo}", "mal")
            return False
        v.motor = True
        self.registrar("Contacto: motor ENCENDIDO (R01)")
        return True

    def alternar_contacto(self):
        """K: llave entre OFF y contacto. Con contacto el tablero hace la prueba de testigos (2 s)."""
        v = self.vehiculo
        if v.contacto or v.motor:
            v.motor, v.contacto, v.marcha = False, False, "N"
            self.registrar("Llave en OFF: sin contacto (R01)")
        else:
            v.contacto = True
            self.registrar("Llave en contacto: el tablero hace la prueba de testigos (2 s); M para arrancar")
        return v.contacto

    def alternar_silencio(self):
        self.silencio = not self.silencio
        self.registrar(f"Sonido {'en silencio' if self.silencio else 'activo'}")
        return self.silencio

    def _seguridad(self):
        self.vehiculo.puertas = sum(bit for bit, var in self.var_puertas.items() if var.get())
        self.vehiculo.cinturon = self.var_cinturon.get()

    def taller(self, accion):
        """Reparaciones del TALLER: la ECU libera su proteccion cuando la causa esta resuelta."""
        v = self.vehiculo
        if accion == "reparar":
            for var in self.var_fallas.values():
                var.set(False)
            self._fallas()
            texto = "fallas reparadas (aceite, radiador, turbo, frenos y velocimetro)"
        elif accion == "aceite":
            v.nivel_aceite = 100.0
            texto = "deposito de aceite al 100 %"
        elif accion == "tanque":
            v.combustible_l = TANQUE_L
            texto = f"tanque lleno ({TANQUE_L:g} L)"
        elif accion == "reserva":
            v.combustible_l = 10.0
            texto = "combustible en reserva (10 L, 8 %)"
        else:
            raise ValueError(f"accion de taller desconocida: {accion}")
        self.registrar(f"Taller: {texto}", "ok")
        return True

    def _luces(self):
        self.vehiculo.luces_altas = self.var_altas.get()
        self.vehiculo.emergencia = self.var_emergencia.get()
        self.vehiculo.direccional = self.var_direccional.get()

    def _fallas(self):
        for clave, var in self.var_fallas.items():
            setattr(self.vehiculo.fallas, clave, var.get())

    def estado_seguro(self):
        self.detener_todo()
        self.vehiculo = Vehiculo()
        self.ecu = Ecu()
        self.var_altas.set(False)
        self.var_emergencia.set(False)
        self.var_direccional.set("OFF")
        for var in (*self.var_fallas.values(), *self.var_puertas.values(), self.var_cinturon):
            var.set(False)
        self.pausa_hasta = 0.0
        self.ultimo_escrito = None
        self.registrar("Estado seguro: motor apagado, luces y fallas desactivadas", "ok")

    # ================================================================ entradas invalidas
    def inyectar(self, tipo):
        """Escribe una entrada invalida y deja de escribir unos segundos para que el tablero la vea."""
        todos = dict(self.valores_actuales(), **self.valores_extra())
        valores = {c: formatear(c, v) for c, v in todos.items()}
        try:
            with exclusivo(self.ruta):
                if tipo == "corrupto":
                    valores["temp_agua"] = "abc"
                    escribir_texto_atomico(self.ruta, "".join(f"{c}={v}\n" for c, v in valores.items()))
                    texto = "temp_agua=abc: el tablero conserva el ultimo valor y registra dato_invalido"
                elif tipo == "fuera":
                    valores["velocidad"] = "400"
                    escribir_texto_atomico(self.ruta, "".join(f"{c}={v}\n" for c, v in valores.items()))
                    texto = "velocidad=400: rechazo fuera_de_rango y aviso en la ventana (P04)"
                elif tipo == "borrar":
                    self.ruta.unlink(missing_ok=True)
                    texto = "archivo borrado: el tablero sigue y registra archivo_inexistente"
                elif tipo == "permisos":
                    if os.name != "posix":
                        self.registrar("Permisos POSIX: solo en Linux", "mal")
                        return False
                    os.chmod(self.ruta, 0o666)
                    texto = "archivo 666: se rechaza por permisos_inseguros"
                else:
                    raise ValueError(f"tipo desconocido: {tipo}")
        except OSError as error:
            self.registrar(f"No se pudo inyectar: {error}", "mal")
            return False
        self.pausa_hasta = self.reloj() + self.PAUSA_INYECCION_S
        self.ultimo_escrito = None
        self.registrar(f"Inyectado: {texto}. El panel restaura datos validos en {self.PAUSA_INYECCION_S:g} s.",
                       "cmd")
        return True

    # ================================================================ escenarios y recorrido
    def reproducir_escenario(self, nombre=None):
        nombre = nombre or self.var_escenario.get()
        if nombre not in self.escenarios:
            self.registrar("No hay escenarios cargados", "mal")
            return False
        self.detener_todo()
        self.modo = "escenario"
        self.valores_escenario = dict(SEGURO)
        self.pasos_pendientes = list(self.escenarios[nombre])
        self._proximo_paso = self.reloj()
        self.ultimo_escrito = None
        self.registrar(f"Escenario {nombre} (del mismo CSV que las pruebas de aceptacion) en el tablero real:", "cmd")
        return True

    def _avanzar_escenario(self, ahora):
        if self.modo != "escenario" or ahora < self._proximo_paso:
            return
        if not self.pasos_pendientes:
            self.modo = "fisica"
            self.vehiculo = Vehiculo()
            self.ecu = Ecu()
            self._luces()
            self._fallas()
            self._seguridad()
            self.registrar("Escenario terminado; el panel vuelve a los pedales.", "ok")
            return
        paso = self.pasos_pendientes.pop(0)
        if paso.accion != "-":
            valor = paso.valor
            if paso.accion == "rpm":
                valor = int(round(valor))
            self.valores_escenario[paso.accion] = valor
        accion = "sin cambio" if paso.accion == "-" else f"{paso.accion}={paso.valor}"
        self.registrar(f"  paso {paso.numero}: {accion} -> esperar en el elemento {paso.elemento}: {paso.esperado}"
                       f"  ({paso.descripcion})")
        self._proximo_paso = ahora + max(self.PASO_ESCENARIO_MIN_S, paso.avanzar_ms / 1000)

    def recorrido_automatico(self):
        """tools/simulador.py como productor; mientras corre, el panel no escribe."""
        self.detener_todo()
        self.recorrido = subprocess.Popen([comandos.PY, str(RAIZ / "tools" / "simulador.py"), "--archivo",
                                           str(self.ruta), "--duracion-s", "22"], cwd=RAIZ,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.modo = "recorrido"
        self.registrar("Recorrido automatico de 22 s (tools/simulador.py) en curso...", "cmd")

    def banco_actual(self):
        """Corre el banco de liberacion (proceso hijo) con las fallas marcadas en el panel."""
        argv = [comandos.PY, "tools/banco_liberacion.py"]
        for clave, var in self.var_fallas.items():
            if var.get():
                argv += ["--falla", clave]          # nombres fijos del panel, no texto del usuario
        return self.ejecutar(argv, "banco de liberacion " + " ".join(argv[2:]))

    def ciclo_ece15(self):
        """El robot del banco conduce el ciclo urbano ECE-15 en el tablero real (195 s, 0.994 km)."""
        self.detener_todo()
        if not self.vehiculo.motor and not self.alternar_motor():
            self.registrar("El ciclo ECE-15 necesita el motor en marcha.", "mal")
            return False
        self.modo = "ciclo"
        self.conductor = liberacion.Conductor(liberacion.ECE15, liberacion.marcha_ece15)
        self.t_ciclo = self.km_ciclo = 0.0
        self.registrar("Ciclo urbano ECE-15 en vivo: 195 s, 0.994 km y maximo 50 km/h. Mira el velocimetro "
                       "y el odometro del tablero.", "cmd")
        return True

    def _avanzar_ciclo(self, dt):
        self.conductor.aplicar(self.vehiculo, self.t_ciclo)
        self.t_ciclo += dt
        self.km_ciclo += self.vehiculo.velocidad * dt / 3600
        if self.t_ciclo >= liberacion.DURACION_ECE15_S or not self.vehiculo.motor:
            v = self.vehiculo
            v.acelerador = v.freno = 0.0
            self.modo = "fisica"
            completo = self.t_ciclo >= liberacion.DURACION_ECE15_S
            self.registrar(f"Ciclo ECE-15 {'terminado' if completo else 'interrumpido: el motor se detuvo'}: "
                           f"{self.km_ciclo:.3f} km en {self.t_ciclo:.0f} s (norma: "
                           f"{liberacion.DISTANCIA_ECE15_KM:g} km en 195 s).", "ok" if completo else "mal")

    def detener_todo(self):
        if self.recorrido is not None and self.recorrido.poll() is None:
            self.recorrido.terminate()
        self.recorrido = None
        if self.modo == "ciclo":
            self.vehiculo.acelerador = self.vehiculo.freno = 0.0
        if self.modo != "fisica":
            self.registrar("Detenido; el panel vuelve a los pedales.")
        self.modo = "fisica"
        self.pasos_pendientes = []
        self.ultimo_escrito = None

    # ================================================================ tablero
    def abrir_tablero(self):
        pid = comandos.pid_tablero()
        if pid is not None or (self.tablero_lanzado is not None and self.tablero_lanzado.poll() is None):
            self.registrar(f"El tablero ya esta abierto{f' (PID {pid})' if pid else ''}.")
            return False
        self.tablero_lanzado = subprocess.Popen([comandos.PY, str(RAIZ / "main.py")], cwd=RAIZ)
        self.registrar(f"Tablero abierto (PID {self.tablero_lanzado.pid}): fork + exec de main.py.", "ok")
        return True

    def cerrar_tablero(self):
        pid = comandos.pid_tablero()
        if pid is None and self.tablero_lanzado is not None and self.tablero_lanzado.poll() is None:
            pid = self.tablero_lanzado.pid
        if pid is None:
            self.registrar("No hay un tablero abierto.")
            return False
        import signal
        os.kill(pid, signal.SIGTERM)
        self.registrar(f"kill -TERM {pid}: cierre ordenado (guarda el kilometraje y registra 'sistema fin').", "ok")
        return True

    # ================================================================ comandos
    def ejecutar(self, comando, nombre):
        if self.ejecutor.ocupado:
            self.registrar("Ya hay un comando en curso; espera o pulsa Detener.", "mal")
            return False
        return self.ejecutor.iniciar(comando, nombre)

    def _drenar_consola(self):
        for tipo, contenido in self.ejecutor.pendientes():
            if tipo == "inicio":
                self.registrar(contenido, "cmd")
            elif tipo == "linea":
                etiqueta = "mal" if any(p in contenido for p in ("FAILED", "ERROR", "FALLIDO", "Traceback")) else None
                self.registrar(contenido, etiqueta)
            else:
                self.registrar(f"[fin del comando: codigo {contenido}] {'APROBADO' if contenido == 0 else 'CON FALLAS'}",
                               "ok" if contenido == 0 else "mal")

    # ================================================================ ciclo
    def valores_actuales(self):
        return dict(self.valores_escenario) if self.modo == "escenario" else self.vehiculo.lecturas()

    def valores_extra(self):
        """Claves opcionales (Etapa 18). Los escenarios de aceptacion usan el formato de diez claves."""
        if self.modo == "escenario":
            return {}
        return self.vehiculo.lecturas_extra(self.ecu.proteccion)

    def escribir(self):
        """Publica las lecturas con escritura atomica bajo el candado de escritura (como escribir_dato.py)."""
        if self.modo == "recorrido" or self.reloj() < self.pausa_hasta:
            return False
        valores = dict(self.valores_actuales(), **self.valores_extra())
        if valores == self.ultimo_escrito:
            return False
        try:
            with exclusivo(self.ruta):
                escribir_atomico(self.ruta, valores)
        except OSError as error:
            self.estado(f"No se pudo escribir {self.ruta.name}: {error}")
            return False
        self.ultimo_escrito = valores
        self.escrituras += 1
        return True

    def paso(self, dt):
        ahora = self.reloj()
        if self.modo == "ciclo":                  # el robot del banco maneja los pedales
            self._avanzar_ciclo(dt)
        else:
            for nombre, pisado in self.pisando.items():
                actual = getattr(self.vehiculo, nombre)
                objetivo = 1.0 if pisado else 0.0
                ritmo = (SUBIDA if objetivo > actual else BAJADA) * dt
                setattr(self.vehiculo, nombre, actual + max(-ritmo, min(ritmo, objetivo - actual)))
        if self.modo in ("fisica", "ciclo"):
            for aviso in self.ecu.vigilar(self.vehiculo, dt):
                self.registrar(aviso, "mal" if "detenido" in aviso or "Interbloqueo" in aviso else "ok")
            self.vehiculo.avanzar(dt)
        elif self.modo == "recorrido" and (self.recorrido is None or self.recorrido.poll() is not None):
            self.registrar("Recorrido terminado.", "ok")
            self.modo, self.recorrido, self.ultimo_escrito = "fisica", None, None
        self._avanzar_escenario(ahora)
        # Productor del sonido: deja el estado mas reciente en el buzon del hilo de audio (no bloquea).
        self.sonido.publicar(sonido_motor.estado_de(self.vehiculo, 0.0 if self.silencio else 0.8))
        if ahora >= self._proxima_escritura:
            self.escribir()
            self._proxima_escritura = ahora + self.ESCRITURA_S
        self._drenar_consola()

    def _ciclo(self):
        try:
            self.paso(self.PERIODO_MS / 1000)
            self.dibujar()
        finally:
            self._id_after = self.raiz.after(self.PERIODO_MS, self._ciclo)

    # ================================================================ dibujo
    def dibujar(self):
        v = self.vehiculo
        for nombre, cx, ancho, alto, tecla in PEDALES:
            valor = round(getattr(v, nombre), 2)
            if self._dibujado.get(nombre) != valor:
                self._dibujado[nombre] = valor
                self._dibujar_pedal(nombre, cx, ancho, alto, tecla, valor)
        x, y = COMPUERTA[v.marcha]
        self.cv_cambios.coords(self.pomo, x - 14, y - 14, x + 14, y + 14)
        self.cv_cambios.coords(self.pomo_txt, x, y)
        self.cv_cambios.itemconfigure(self.pomo_txt, text=v.marcha)
        self.btn_contacto.configure(bg="#1f5a2c" if v.motor else "#2b1414",
                                    text=f"ARRANQUE [M]\n{'MOTOR ON' if v.motor else 'MOTOR OFF'}")
        llave = "MOTOR" if v.motor else ("CONTACTO" if v.contacto else "OFF")
        self.btn_llave.configure(bg="#5a4a12" if llave == "CONTACTO" else ("#1f5a2c" if v.motor else "#2b1414"),
                                 text=f"LLAVE [K]\n{llave}")
        extra = self.valores_extra() or v.lecturas_extra(self.ecu.proteccion)
        for clave, lbl in self.lbl_extra.items():
            if clave == "nivel_aceite":
                texto, color = f"{v.nivel_aceite:.0f} %", ROJO if v.nivel_aceite < 50 else TEXTO
            elif clave == "temp_frenos":
                texto = f"{v.temp_frenos:.0f} C  (eficiencia {v.eficiencia_frenos * 100:.0f} %)"
                color = ROJO if v.eficiencia_frenos < 0.9 else TEXTO
            else:
                valor = extra[clave]
                texto = formatear(clave, valor)
                malo = (clave == "falla_motor" and valor != "ninguna" or clave == "puertas" and valor
                        or clave == "cinturon" and not valor and v.contacto or clave == "combustible" and valor <= 12)
                color = AMBAR if malo else TEXTO
            lbl.configure(text=texto, fg=color)

        valores = self.valores_actuales()
        for clave, lbl in self.lbl_lecturas.items():
            valor = valores[clave]
            color = TEXTO
            if clave == "rpm" and valor >= 8000 or clave == "temp_agua" and valor > 110:
                color = ROJO
            elif clave == "presion_turbo" and valor > 1.5 or clave == "presion_aceite" and valores["motor"] and valor < 1:
                color = AMBAR
            elif clave == "falla_frenos" and valor:
                color = ROJO
            lbl.configure(text=formatear(clave, valor), fg=color)
        pausa = max(0.0, self.pausa_hasta - self.reloj())
        self.lbl_escritura.configure(
            text=f"modo: {self.modo}  ·  escrituras: {self.escrituras}"
                 + (f"  ·  pausa por inyeccion: {pausa:.1f} s" if pausa else "")
                 + (f"\nmarcha {v.marcha}: maximo {velocidad_maxima(v.marcha):.0f} km/h"
                    if v.marcha not in ("N",) else "\nmarcha N (motor desacoplado)"))
        if self.reloj() >= self._proxima_bitacora:
            self._proxima_bitacora = self.reloj() + 1.0
            self._actualizar_bitacoras()
            pid = comandos.pid_tablero()
            self.lbl_tablero.configure(text=f"tablero: ABIERTO (PID {pid})" if pid else "tablero: cerrado",
                                       fg=VERDE if pid else TENUE)
            self.lbl_sonido.configure(text=self.texto_sonido(), fg=VERDE if self.sonido.activo and not self.silencio
                                      else TENUE)

    def _dibujar_pedal(self, nombre, cx, ancho, alto, tecla, valor):
        c = self.cv
        c.delete(f"dib_{nombre}")
        etiqueta = ("dib_" + nombre, nombre)
        hundido = 46 * valor
        top = 40 + hundido
        alto_vis = alto * (1 - 0.18 * valor)                 # escorzo: el pedal pisado se ve mas corto
        c.create_rectangle(cx - 6, 18, cx + 6, top + 8, fill="#3c3c3c", outline="#1a1a1a", tags=etiqueta)  # brazo
        x0, x1, y0, y1 = cx - ancho / 2, cx + ancho / 2, top, top + alto_vis
        r = 10
        puntos = [x0 + r, y0, x1 - r, y0, x1, y0 + r, x1, y1 - r, x1 - r, y1, x0 + r, y1, x0, y1 - r, x0, y0 + r]
        c.create_polygon(puntos, fill=ALUMINIO, outline=ALUMINIO_SOMBRA, width=2, tags=etiqueta)
        c.create_line(x0 + r, y0 + 2, x1 - r, y0 + 2, fill=ALUMINIO_LUZ, width=2, tags=etiqueta)
        paso = 15
        filas = int((alto_vis - 18) // paso)
        columnas = int((ancho - 18) // paso)
        ox = cx - (columnas - 1) * paso / 2
        oy = y0 + (alto_vis - (filas - 1) * paso) / 2
        for i in range(columnas):                            # aluminio perforado
            for j in range(filas):
                hx, hy = ox + i * paso, oy + j * paso
                c.create_oval(hx - 4.5, hy - 4.5, hx + 4.5, hy + 4.5, fill="#1b1a16", outline=ALUMINIO_SOMBRA,
                              tags=etiqueta)
        base = 262
        c.create_text(cx, base, text=nombre.upper(), fill=TEXTO, font=(FUENTE, 9, "bold"), tags=etiqueta)
        c.create_text(cx, base + 13, text=f"[{tecla}]", fill=TENUE, font=(FUENTE, 8), tags=etiqueta)
        c.create_rectangle(cx - 40, base + 22, cx + 40, base + 30, outline="#555", fill="#111", tags=etiqueta)
        color = {"acelerador": VERDE, "freno": ROJO, "embrague": AMBAR}[nombre]
        c.create_rectangle(cx - 40, base + 22, cx - 40 + 80 * valor, base + 30, outline="", fill=color, tags=etiqueta)

    def _actualizar_bitacoras(self):
        lineas = []
        for archivo, etiqueta in (("eventos.log", None), ("errores.log", "error")):
            ruta = self.dir_logs / archivo
            try:
                texto = ruta.read_text(encoding="utf-8", errors="replace").splitlines()[-6:]
            except OSError:
                continue
            lineas += [(l, etiqueta or ("warn" if " WARN " in l else None)) for l in texto]
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        for linea, etiqueta in lineas:
            self.txt_log.insert("end", linea[11:] + "\n", etiqueta or ())   # sin la fecha: solo la hora
        if not lineas:
            self.txt_log.insert("end", "(sin bitacoras todavia: abre el tablero)\n")
        self.txt_log.configure(state="disabled")

    # ================================================================ mensajes y cierre
    def registrar(self, texto, etiqueta=None):
        self.txt.configure(state="normal")
        self.txt.insert("end", texto + "\n", etiqueta or ())
        if int(self.txt.index("end-1c").split(".")[0]) > 2000:
            self.txt.delete("1.0", "500.0")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def estado(self, texto):
        self.lbl_estado.configure(text=f"  {texto}")

    def texto_consola(self):
        return self.txt.get("1.0", "end")

    def texto_sonido(self):
        texto = f"sonido: {self.sonido.descripcion}"
        if getattr(self.sonido, "destino", None) is not None:
            texto += " (conectada)" if self.sonido.conectado else " (esperando la bocina)"
        return texto + (" · SILENCIO" if self.silencio else "")

    def cerrar(self):
        """Cierra el panel (el tablero sigue abierto: son procesos independientes)."""
        self.raiz.after_cancel(self._id_after)
        self.sonido.detener()
        self.ejecutor.detener()
        if self.recorrido is not None and self.recorrido.poll() is None:
            self.recorrido.terminate()
        self.raiz.destroy()
