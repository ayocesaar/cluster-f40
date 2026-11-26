"""Practicas de fallas automaticas (Etapa 21).

Cada practica es un guion que maneja el auto como lo haria una persona: pisa y suelta los
pedales con la misma rapidez que el panel, pisa el embrague para cambiar de marcha, inyecta la
falla, espera a que pase lo que debe pasar y repara en el taller. Al final verifica con una copia
en memoria del cuadro real (CadenaCuadro: el mismo formato del archivo, la misma validacion del
lector, EstadoCluster y el monitor de eventos) que se encendieron los testigos y advertencias
correctos. Desde el panel se ven en vivo en el tablero; en las pruebas y en tools/practicas.py
corren en tiempo simulado.

Cada guion es una corrutina (un generador de Python): cede el control al ciclo del panel cada 50 ms
o mientras espera algo (calendarizacion cooperativa), asi la interfaz nunca se bloquea. Lo que el
guion cede significa: None = esperar un ciclo; un numero = esperar esos segundos; una funcion =
esperar a que devuelva verdadero."""

from dataclasses import dataclass

from panel.ecu import Ecu
from panel.fisica import TANQUE_L, Fallas, Vehiculo
from panel.liberacion import CadenaCuadro
from sistema.monitor import MonitorEventos

PEDAL_SUBIDA, PEDAL_BAJADA = 5.0, 7.0     # unidades de pedal por segundo, las mismas del panel
LECTURA_S = 0.1                            # el cuadro lee cada 100 ms


class BitacoraMemoria:
    """Bitacora en memoria para el monitor del cuadro copiado (no escribe archivos)."""

    def __init__(self):
        self.lineas = []

    def info(self, componente, evento, detalle=""):
        self.lineas.append(("INFO", evento, detalle))

    def warn(self, componente, evento, detalle=""):
        self.lineas.append(("WARN", evento, detalle))

    def error(self, componente, evento, detalle=""):
        self.lineas.append(("ERROR", evento, detalle))

    def eventos(self, nivel=None):
        return [e for n, e, _ in self.lineas if nivel is None or n == nivel]


class Mando:
    """El vehiculo, su ECU, los pedales que mueve el robot y lo que mostraria el tablero."""

    def __init__(self, vehiculo=None, ecu=None, avisar=None):
        self.v = vehiculo or Vehiculo()
        self.ecu = ecu or Ecu()
        self.avisar = avisar or (lambda texto, etiqueta=None: None)
        self.t = 0.0
        self.objetivos = {"acelerador": 0.0, "freno": 0.0, "embrague": 0.0}
        self.cuadro = CadenaCuadro()
        self.bitacora = BitacoraMemoria()
        self.monitor = MonitorEventos(self.bitacora)
        self.vistos, self.encendidos, self.causas = set(), set(), set()
        self.resultados = []
        self.giro_arranque = (0.0, 0.0)
        self.distancia_km = 0.0
        self._proxima_lectura = 0.0
        self.vio_bloqueo = self.vio_patinaje = False
        self.marchas_vistas = set()
        self.real_en_lectura = 0.0       # velocidad real cuando el cuadro leyo por ultima vez

    # ------------------------------------------------------------ mandos de cabina
    def llave(self, puesta=True):
        self.v.contacto = puesta
        if not puesta:
            self.v.motor, self.v.marcha = False, "N"
        self.avisar("Llave en contacto: prueba de testigos" if puesta else "Llave en OFF")

    def arrancar(self):
        self.v.contacto = True
        motivo = self.ecu.motivo_sin_arranque(self.v)
        if motivo:
            fuerza = {"electrica": 0.35, "combustible": 1.0}.get(self.ecu.proteccion, 0.0)
            self.giro_arranque = (self.t + 1.5, fuerza)
            self.avisar(f"No arranca: {motivo}", "mal")
            return False
        self.v.motor = True
        self.avisar("Motor ENCENDIDO")
        return True

    def apagar(self):
        self.v.motor, self.v.marcha = False, "N"
        self.avisar("Motor APAGADO")

    def falla(self, nombre, activa=True):
        setattr(self.v.fallas, nombre, activa)
        self.avisar(f"{'Se inyecta' if activa else 'Se quita'} la falla: {nombre}", "mal" if activa else "ok")

    def reparar(self):
        self.v.fallas = Fallas()
        self.avisar("Taller: fallas reparadas", "ok")

    def taller(self, accion):
        if accion == "aceite":
            self.v.nivel_aceite = 100.0
        elif accion == "tanque":
            self.v.combustible_l = TANQUE_L
        elif accion == "reserva":
            self.v.combustible_l = 10.0
        elif accion == "bateria":
            self.v.bateria = 1.0
        elif accion == "bateria_debil":
            self.v.bateria = 0.06
        else:
            raise ValueError(f"accion de taller desconocida: {accion}")
        self.avisar(f"Taller: {accion}", "ok")

    def pedales(self, acelerador=None, freno=None, embrague=None):
        for nombre, valor in (("acelerador", acelerador), ("freno", freno), ("embrague", embrague)):
            if valor is not None:
                self.objetivos[nombre] = max(0.0, min(1.0, valor))

    def cambiar(self, marcha):
        """Como una persona: suelta el acelerador, pisa el embrague, mueve la palanca y suelta el embrague."""
        self.pedales(acelerador=0.0, embrague=1.0)
        yield 0.27              # 0.2 s para llegar al fondo y la palanca se mueve con el embrague a fondo (DEF-17)
        try:
            self.v.cambiar(marcha)
        except ValueError as error:
            self.avisar(f"Cambio rechazado: {error}", "mal")
        self.pedales(embrague=0.0)
        yield 0.18

    # ------------------------------------------------------------ ciclo
    def paso(self, dt):
        for nombre, objetivo in self.objetivos.items():
            actual = getattr(self.v, nombre)
            ritmo = (PEDAL_SUBIDA if objetivo > actual else PEDAL_BAJADA) * dt
            setattr(self.v, nombre, actual + max(-ritmo, min(ritmo, objetivo - actual)))
        for aviso in self.ecu.vigilar(self.v, dt):
            self.avisar(aviso, "mal" if "detenido" in aviso or "Interbloqueo" in aviso else "ok")
        self.v.avanzar(dt)
        self.vio_bloqueo = self.vio_bloqueo or self.v.bloqueado
        self.vio_patinaje = self.vio_patinaje or self.v.patinando
        self.marchas_vistas.add(self.v.marcha)
        self.t += dt
        self.distancia_km += self.v.velocidad * dt / 3600
        if self.t >= self._proxima_lectura - 1e-9:
            self._proxima_lectura = self.t + LECTURA_S
            self.observar()

    def observar(self):
        """Lo que el tablero real mostraria: misma conversion, mismo modelo y mismo monitor."""
        self.real_en_lectura = self.v.velocidad
        base, extra = self.cuadro.aplicar(self.v.lecturas(), self.v.lecturas_extra(self.ecu.proteccion))
        e = self.cuadro.estado
        self.monitor.revisar(e)
        encendidos = {n for n in range(6, 11) if base[n]["encendido"]}
        encendidos |= {n for n in (12, 13, 15, 16) if extra[n]["encendido"]}
        encendidos |= {"reserva"} if extra[14]["reserva"]["encendido"] else set()
        for marca, activo in (("3rojo", e.color_rpm == "rojo"), ("4rojo", e.color_temp == "rojo"),
                              ("5ambar", e.contorno_turbo == "ambar"), ("17rojo", e.color_aceite_temp == "rojo"),
                              ("prueba", e.prueba_testigos_activa)):
            if activo:
                encendidos.add(marca)
        self.encendidos = encendidos
        self.vistos |= encendidos
        if e.falla_motor not in (None, "ninguna"):
            self.causas.add(e.falla_motor)

    # ------------------------------------------------------------ verificacion
    def verificar(self, criterio, ok, medido=""):
        self.resultados.append((criterio, bool(ok), medido))
        self.avisar(f"  {'OK ' if ok else 'MAL'} {criterio}{f': {medido}' if medido else ''}", "ok" if ok else "mal")
        return ok

    def avisos_del_cuadro(self, nivel="WARN"):
        return self.bitacora.eventos(nivel)


# ------------------------------------------------------------ ayudas de manejo (corrutinas)
def hasta(m, condicion, limite_s, criterio):
    """Espera una condicion; si no llega a tiempo, lo deja como verificacion fallida."""
    inicio = m.t
    while not condicion():
        if m.t - inicio > limite_s:
            m.verificar(criterio, False, f"no ocurrio en {limite_s:g} s")
            return False
        yield None
    return True


def arrancar_y_calentar(m, temperatura=None):
    m.llave(True)
    m.v.cinturon = True
    yield 2.3                                     # prueba de testigos
    if temperatura is not None:
        m.v.temp_agua = m.v.temp_aceite = temperatura    # motor ya caliente para no esperar
    ok = m.arrancar()
    yield 1.0
    return ok


def conducir_hasta(m, velocidad, acelerador=1.0, cambio_rpm=7000, marcha_maxima="5", limite_s=40):
    """Acelera con cambios; los pedales y la palanca se mueven como los moveria un piloto."""
    inicio = m.t
    if m.v.marcha in ("N", "R"):
        yield from m.cambiar("1")
    while m.v.velocidad < velocidad:
        if m.t - inicio > limite_s or not m.v.motor:
            return False
        if m.v.rpm >= cambio_rpm and m.v.marcha in "1234" and m.v.marcha < marcha_maxima:
            yield from m.cambiar(str(int(m.v.marcha) + 1))
        m.pedales(acelerador=acelerador, freno=0.0)
        yield None
    return True


def crucero(m, velocidad, segundos):
    inicio = m.t
    while m.t - inicio < segundos and m.v.motor:
        error = velocidad - m.v.velocidad
        m.pedales(acelerador=max(0.0, min(1.0, 0.3 + 0.08 * error)), freno=0.0 if error > -4 else 0.3)
        yield None


def frenar_hasta_parar(m, freno=0.7, limite_s=40):
    """Frena (sin tocar el acelerador) hasta detenerse; devuelve la distancia en metros."""
    m.pedales(acelerador=0.0, freno=freno)
    inicio, km = m.t, m.distancia_km
    while m.v.velocidad > 0.3 and m.t - inicio < limite_s:
        yield None
    metros = (m.distancia_km - km) * 1000
    yield from m.cambiar("N")
    m.pedales(freno=0.0)
    return metros


# ------------------------------------------------------------ las practicas
def practica_normal(m):
    yield from arrancar_y_calentar(m)
    m.verificar("prueba de testigos al dar contacto", "prueba" in m.vistos and {6, 9, 10, 15, 16} <= m.vistos)
    m.verificar("el motor arranca", m.v.motor)
    yield from conducir_hasta(m, 80, acelerador=0.7, cambio_rpm=4000)      # manejo tranquilo: cambia a 4000 rpm
    yield from crucero(m, 80, 3)
    maxima = m.v.velocidad
    metros = yield from frenar_hasta_parar(m, 0.5)
    m.verificar("manejo en 1a, 2a y 3a hasta 80 km/h", maxima >= 75 and {"1", "2", "3"} <= m.marchas_vistas,
                f"{maxima:.0f} km/h en {'-'.join(sorted(m.marchas_vistas - {'N'}))}; frenada de {metros:.0f} m")
    m.verificar("sin advertencias criticas", not m.causas and "testigo_9_encendido" not in m.avisos_del_cuadro())
    m.apagar()


def practica_aceite(m):
    yield from arrancar_y_calentar(m)
    m.falla("fuga_aceite")
    yield from hasta(m, lambda: 9 in m.encendidos, 5, "testigo 9 de presion de aceite")
    m.verificar("testigo 9 encendido y WARN prioritario", 9 in m.vistos and "testigo_9_encendido" in m.avisos_del_cuadro())
    m.apagar()
    yield 1.0
    m.verificar("con fuga no arranca", not m.arrancar(), m.ecu.proteccion)
    yield 1.0
    m.verificar("el tablero muestra STOP · ACEITE", "aceite" in m.causas)
    m.reparar()
    m.taller("aceite")
    yield 0.5
    m.verificar("reparado, arranca", m.arrancar())
    yield 1.0
    m.apagar()


def practica_temperatura(m):
    yield from arrancar_y_calentar(m, temperatura=88.0)
    m.falla("radiador")
    yield from conducir_hasta(m, 60, acelerador=0.6, marcha_maxima="3")
    inicio = m.t
    while m.v.motor and m.t - inicio < 90:
        yield from crucero(m, 60, 1)
    m.verificar("la ECU detiene el motor por sobretemperatura", "sobretemperatura" in m.causas,
                f"agua a {m.v.temp_agua:.0f} C")
    m.verificar("aguja del agua en rojo y WARN (R04)", "4rojo" in m.vistos and "temperatura_rojo" in m.avisos_del_cuadro())
    yield from frenar_hasta_parar(m, 0.5)
    m.verificar("caliente no arranca", not m.arrancar())
    m.reparar()
    yield from hasta(m, lambda: m.v.temp_agua <= 100, 40, "el motor se enfria")
    m.verificar("reparado y frio, arranca", m.arrancar(), f"agua a {m.v.temp_agua:.0f} C")
    yield 1.0
    m.apagar()


def practica_turbo(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    yield from conducir_hasta(m, 100, marcha_maxima="3")
    m.falla("sobrepresion_turbo")
    m.pedales(acelerador=1.0)
    yield from hasta(m, lambda: not m.v.motor, 10, "corte del motor por sobrepresion")
    yield 0.3                                    # el cuadro lee cada 100 ms
    m.verificar("contorno del turbo en ambar (R05) y corte por sobrepresion", "5ambar" in m.vistos
                and "sobrepresion_turbo" in m.causas)
    yield from frenar_hasta_parar(m, 0.6)
    m.verificar("con la proteccion enclavada no arranca", not m.arrancar())
    m.reparar()
    m.verificar("reparado, arranca", m.arrancar())
    yield 1.0
    m.apagar()


def practica_frenos(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    yield from conducir_hasta(m, 100)
    sano = yield from frenar_hasta_parar(m, 1.0)
    yield from conducir_hasta(m, 100)
    m.falla("frenos")
    yield 0.5
    con_falla = yield from frenar_hasta_parar(m, 1.0)
    m.verificar("testigo 10 parpadeando (R08)", 10 in m.vistos and "testigo_10_encendido" in m.avisos_del_cuadro())
    m.verificar("con la falla frena mucho peor", con_falla > 2.5 * sano, f"{sano:.0f} m sano contra {con_falla:.0f} m")
    m.reparar()
    m.apagar()


def practica_puertas(m):
    yield from arrancar_y_calentar(m)
    m.v.puertas = 1
    yield from m.cambiar("1")
    m.pedales(acelerador=1.0)
    yield 2.0
    m.verificar("con la puerta abierta no avanza aunque se acelere", m.v.velocidad < 1.0,
                f"{m.v.velocidad:.1f} km/h; testigo 12 {'encendido' if 12 in m.vistos else 'apagado'}")
    m.pedales(acelerador=0.0)
    m.v.puertas = 0
    yield from conducir_hasta(m, 40)
    m.v.puertas = 1
    yield from hasta(m, lambda: "puerta_abierta_en_movimiento" in m.avisos_del_cuadro(), 2,
                     "WARN de puerta abierta en movimiento")
    m.verificar("puerta abierta en movimiento: WARN prioritario (R09)",
                "puerta_abierta_en_movimiento" in m.avisos_del_cuadro())
    m.v.puertas = 0
    yield from frenar_hasta_parar(m, 0.6)
    m.apagar()


def practica_cinturon(m):
    m.llave(True)
    m.v.cinturon = False
    yield 3.0
    m.verificar("testigo 13 con contacto y sin cinturon", 13 in m.encendidos)
    m.arrancar()
    yield from conducir_hasta(m, 40)
    yield 1.0
    m.verificar("WARN de cinturon sin abrochar en movimiento (R10)",
                "cinturon_desabrochado_en_movimiento" in m.avisos_del_cuadro())
    m.v.cinturon = True
    yield 1.0
    m.verificar("al abrochar se apaga", 13 not in m.encendidos)
    yield from frenar_hasta_parar(m, 0.6)
    m.apagar()


def practica_combustible(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    m.taller("reserva")
    yield from hasta(m, lambda: "reserva" in m.encendidos, 3, "testigo de reserva")
    m.verificar("reserva de combustible y WARN (R11)", "combustible_reserva" in m.avisos_del_cuadro())
    m.v.combustible_l = 0.08
    m.avisar("Quedan 80 mL en el tanque")
    yield from conducir_hasta(m, 120)
    yield from hasta(m, lambda: not m.v.motor, 30, "el motor se apaga sin combustible")
    yield from frenar_hasta_parar(m, 0.6)
    m.verificar("sin combustible el motor se apaga y no arranca", "combustible" in m.causas and not m.arrancar())
    m.taller("tanque")
    m.verificar("con el tanque lleno arranca", m.arrancar())
    yield 1.0
    m.apagar()


def practica_alternador(m):
    yield from arrancar_y_calentar(m)
    m.v.luces_altas = True
    m.v.bateria = 0.25
    m.avisar("Bateria a 25 % para que la descarga se vea rapido")
    m.falla("alternador")
    yield from hasta(m, lambda: "falla_de_carga" in m.avisos_del_cuadro(), 3, "WARN de falla de carga")
    m.verificar("testigo 16 y WARN falla_de_carga (R13)", 16 in m.vistos and "falla_de_carga" in m.avisos_del_cuadro())
    yield from hasta(m, lambda: not m.v.motor, 60, "la gestion electronica se apaga")
    yield 0.3
    m.verificar("bajo 10.5 V la ECU apaga el motor", "electrica" in m.causas, f"{m.v.voltaje:.1f} V")
    m.reparar()
    m.taller("bateria")
    m.v.luces_altas = False
    m.verificar("reparado y con la bateria cargada, arranca", m.arrancar())
    yield 1.0
    m.apagar()


def practica_bateria(m):
    m.taller("bateria_debil")
    m.llave(True)
    yield 2.3
    m.verificar("con la bateria debil no arranca", not m.arrancar(), f"{m.v.voltaje_reposo:.1f} V en reposo")
    m.verificar("el motor de arranque gira lento", m.giro_arranque[1] < 0.5)
    yield 1.5
    m.taller("bateria")
    m.verificar("con la bateria cargada arranca", m.arrancar())
    yield 1.0
    m.apagar()


def _segunda_40_a_80(m):
    yield from conducir_hasta(m, 40, marcha_maxima="2", cambio_rpm=4000)
    if m.v.marcha != "2":
        yield from m.cambiar("2")
    inicio = m.t
    m.pedales(acelerador=1.0)
    yield from hasta(m, lambda: m.v.velocidad >= 80, 20, "llegar a 80 km/h")
    return m.t - inicio


def practica_weber(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    sano = yield from _segunda_40_a_80(m)
    yield from frenar_hasta_parar(m, 0.7)
    m.falla("ecu_banco")
    rpms = []
    for _ in range(80):                          # 4 s de ralenti
        rpms.append(m.v.rpm)
        yield None
    m.verificar("ralenti irregular (sin testigo, como en 1987)", max(rpms) - min(rpms) > 150,
                f"{min(rpms):.0f} a {max(rpms):.0f} rpm")
    con_falla = yield from _segunda_40_a_80(m)
    m.verificar("con 4 cilindros acelera mucho mas lento", con_falla > 1.5 * sano,
                f"40-80 km/h en 2a: {sano:.1f} s sano contra {con_falla:.1f} s")
    yield from frenar_hasta_parar(m, 0.7)
    m.reparar()
    m.apagar()


def practica_limitador(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    yield from m.cambiar("1")
    m.pedales(acelerador=1.0)
    yield from hasta(m, lambda: m.v.rpm >= 8000, 10, "llegar al limitador")
    maxima = 0.0
    for _ in range(40):                          # 2 s en el limitador
        maxima = max(maxima, m.v.rpm)
        yield None
    m.verificar("tacometro en rojo (R03) y el limitador no deja pasar de 8200 rpm",
                "3rojo" in m.vistos and maxima <= 8200, f"maximo {maxima:.0f} rpm")
    yield from frenar_hasta_parar(m, 0.7)
    m.apagar()


def practica_lluvia(m):
    m.v.mojado = True
    m.avisar("Pista mojada: 55 % de adherencia; el F40 no tiene ABS ni control de traccion")
    yield from arrancar_y_calentar(m, temperatura=85.0)
    yield from m.cambiar("1")
    m.vio_patinaje = False
    m.pedales(acelerador=1.0)
    yield 3.0
    m.verificar("a fondo en 1a las llantas traseras patinan (sin control de traccion)", m.vio_patinaje)
    yield from conducir_hasta(m, 100)
    m.vio_bloqueo = False
    a_fondo = yield from frenar_hasta_parar(m, 1.0)
    bloqueo = m.vio_bloqueo
    yield from conducir_hasta(m, 100)
    m.vio_bloqueo = False
    dosificado = yield from frenar_hasta_parar(m, 0.7)       # justo bajo el limite de adherencia en mojado
    m.verificar("frenando a fondo se bloquean las llantas (sin ABS)", bloqueo)
    m.verificar("dosificando no se bloquean", not m.vio_bloqueo)
    m.verificar("frenar sin bloquear detiene antes (por eso existe el ABS)", dosificado < a_fondo,
                f"bloqueadas {a_fondo:.0f} m contra dosificado {dosificado:.0f} m")
    m.v.mojado = False
    m.apagar()


def practica_cero_cien(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    m.pedales(acelerador=0.5)
    yield 1.5                                    # en neutral: el turbo toma presion
    yield from m.cambiar("1")
    inicio = m.t
    patino = False
    m.pedales(acelerador=1.0)
    while m.v.velocidad < 100 and m.t - inicio < 15:
        patino = patino or m.v.patinando
        if m.v.rpm >= 7600 and m.v.marcha in "1234":
            yield from m.cambiar(str(int(m.v.marcha) + 1))
            m.pedales(acelerador=1.0)
        yield None
    tiempo = m.t - inicio
    m.verificar("0-100 km/h dentro del rango publicado (3.5 a 5.0 s; la cifra mas citada es 4.1 s)",
                3.5 <= tiempo <= 5.0, f"{tiempo:.2f} s{'; las llantas patinaron al salir' if patino else ''}")
    yield from frenar_hasta_parar(m, 0.8)
    m.apagar()


def practica_velocimetro(m):
    yield from arrancar_y_calentar(m, temperatura=85.0)
    yield from conducir_hasta(m, 80, marcha_maxima="4")
    yield from crucero(m, 80, 2)
    sano = m.cuadro.estado.velocidad - m.real_en_lectura
    m.falla("velocimetro")
    yield from crucero(m, 80, 2)
    con_falla = m.cuadro.estado.velocidad - m.real_en_lectura
    m.verificar("sano: el tablero nunca indica menos que la velocidad real (UN R39)", sano >= 0, f"{sano:+.1f} km/h")
    m.verificar("descalibrado: indica menos (ilegal segun UN R39)", con_falla < -2, f"{con_falla:+.1f} km/h")
    m.reparar()
    yield from frenar_hasta_parar(m, 0.6)
    m.apagar()


@dataclass
class Practica:
    clave: str
    nombre: str
    descripcion: str
    guion: object
    limite_s: float = 240.0


CATALOGO = {p.clave: p for p in (
    Practica("normal", "Manejo normal", "Prueba de testigos, arranque, 1a a 3a hasta 80 km/h y frenada", practica_normal),
    Practica("aceite", "Fuga de aceite", "Testigo 9, no arranca, taller y vuelve a arrancar", practica_aceite),
    Practica("temperatura", "Sobrecalentamiento", "Radiador danado: la ECU corta a 120 C y no arranca hasta enfriar",
             practica_temperatura),
    Practica("turbo", "Turbo", "Sobrepresion sobre 1.5 bar: corte del motor enclavado hasta reparar", practica_turbo),
    Practica("frenos", "Frenos", "Frenada desde 100 km/h sana y con un circuito perdido (testigo 10)", practica_frenos),
    Practica("puertas", "Puertas", "Interbloqueo con la puerta abierta y WARN en movimiento", practica_puertas),
    Practica("cinturon", "Cinturon", "Testigo 13, alarma y WARN sobre 10 km/h", practica_cinturon),
    Practica("combustible", "Combustible", "Reserva, se apaga sin combustible y no arranca hasta cargar",
             practica_combustible),
    Practica("alternador", "Alternador", "No carga: testigo 16 y la gestion electronica se apaga bajo 10.5 V",
             practica_alternador),
    Practica("bateria", "Bateria debil", "El motor de arranque gira lento y no prende", practica_bateria),
    Practica("weber", "Weber-Marelli", "Un banco sin encendido: ralenti irregular y medio motor", practica_weber),
    Practica("limitador", "Limitador", "1a a fondo hasta 8200 rpm: tacometro en rojo y cortes", practica_limitador),
    Practica("lluvia", "Lluvia sin ABS", "Patinamiento y llantas bloqueadas; frenar dosificado detiene antes",
             practica_lluvia),
    Practica("cero_cien", "0-100 km/h", "Salida con el turbo cargado, cambios a 7600 rpm y tiempo medido",
             practica_cero_cien),
    Practica("velocimetro", "Velocimetro", "A 80 km/h: sano indica de mas (R39); descalibrado indica de menos",
             practica_velocimetro),
)}


class Ejecucion:
    """Avanza una practica: primero el vehiculo un paso, despues el guion si ya no esta esperando."""

    def __init__(self, practica, mando):
        self.practica = practica
        self.m = mando
        self.guion = practica.guion(mando)
        self.espera = None
        self.inicio = mando.t
        self.terminada = False

    def avanzar(self, dt):
        self.m.paso(dt)
        if self.terminada:
            return
        if self.m.t - self.inicio > self.practica.limite_s:
            self.m.verificar("la practica termina a tiempo", False, f"mas de {self.practica.limite_s:g} s")
            self._terminar()
            return
        if isinstance(self.espera, (int, float)):
            self.espera -= dt
            if self.espera > 1e-9:
                return
        elif callable(self.espera) and not self.espera():
            return
        try:
            self.espera = next(self.guion)
        except StopIteration:
            self._terminar()

    def _terminar(self):
        self.terminada = True
        self.m.pedales(acelerador=0.0, freno=0.0, embrague=0.0)

    @property
    def aprobada(self):
        return self.terminada and bool(self.m.resultados) and all(ok for _, ok, _ in self.m.resultados)


def correr(clave, dt=0.05, avisar=None):
    """Corre una practica completa en tiempo simulado (pruebas y evidencia)."""
    mando = Mando(avisar=avisar)
    ejecucion = Ejecucion(CATALOGO[clave], mando)
    while not ejecucion.terminada:
        ejecucion.avanzar(dt)
    return ejecucion
