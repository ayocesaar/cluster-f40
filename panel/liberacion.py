"""Banco de liberacion de produccion (fin de linea) del F40 simulado.

Antes de mandar un auto a produccion, y despues a cada unidad al final de la linea, se
corren pruebas normalizadas. Este banco las reproduce sobre el modelo fisico del panel
(panel/fisica.py) con la misma ECU (panel/ecu.py); las que tocan al cuadro usan el codigo
real del tablero (la conversion del lector, EstadoCluster y la presentacion).

Normas (texto verificado; citas y limites en docs/realismo_y_liberacion.md):
- UN R13-H, anexo 3: frenado tipo 0 desde 100 km/h con el motor desembragado,
  s <= 0.1 v + 0.0060 v^2 y dm >= 6.43 m/s^2 (2.1.1 A); tipo I (fading, 1.5): 15 frenadas
  de v1 = 80 % vmax (maximo 120 km/h) a v1/2, una cada 45 s, a 3 m/s^2, en la marcha mas
  alta; en caliente >= 75 % de lo prescrito y >= 60 % de lo medido en frio.
  5.2.21.4: los testigos se encienden al energizar y solo se apagan si no hay falla.
- UN R39, 5.2.5 y 5.3 (velocimetro): para vmax > 150 km/h se prueba a 40, 80 y 120 km/h;
  la velocidad indicada nunca es menor que la real y 0 <= V1 - V2 <= 0.1 V2 + 4 km/h
  (+ 6 km/h en la conformidad de la produccion, anexo 3).
- Ciclo urbano ECE-15 de la prueba tipo I de emisiones: 195 s, 994.03 m, maximo 50 km/h.
Las cifras del vehiculo son aproximadas. Los valores de la Directiva 71/320/CEE vigentes en
1987 quedan pendientes de verificar: se usan los de R13-H. El enfriamiento, el turbo y el
interbloqueo de puertas son criterios del equipo, no de una norma."""

from dataclasses import dataclass

from logic.estado import EstadoCluster
from logic.reloj import RelojSimulado
from panel.ecu import Ecu
from panel.fisica import (COMBUSTIBLE_INICIAL_L, FRENADO, FRENO_MOTOR, Fallas, Vehiculo, resistencia_al_avance,
                          velocidad_maxima)
from sistema.config import RANGOS_ESPECIFICACION
from sistema.lector import CLAVES, CLAVES_EXTRA, convertir, formatear
from ui.presentacion import vista, vista_extra

DT = 0.05                     # s, el mismo paso que el panel
VMAX = velocidad_maxima("5")    # velocidad maxima del modelo (aprox. 343 km/h)

# ------------------------------------------------------------ R13-H, anexo 3
V_TIPO0 = 100.0               # km/h, motor desembragado (2.1.1 A)
DM_TIPO0 = 6.43               # m/s^2


def distancia_tipo0(v):
    """Distancia maxima de frenado tipo 0 (m) para v en km/h: 0.1 v + 0.0060 v^2."""
    return 0.1 * v + 0.0060 * v ** 2


def desaceleracion_media(vb, ve, sb, se):
    """Desaceleracion media totalmente desarrollada (m/s^2): (vb^2 - ve^2) / (25.92 (se - sb)),
    con vb = 0.8 v0 y ve = 0.1 v0 en km/h y sb, se en metros."""
    return (vb ** 2 - ve ** 2) / (25.92 * (se - sb))


TIPO1_CICLOS, TIPO1_CICLO_S, TIPO1_DECEL = 15, 45.0, 3.0
TIPO1_PRESCRITO, TIPO1_MEDIDO = 0.75, 0.60


def velocidades_tipo1(vmax):
    v1 = min(0.8 * vmax, 120.0)
    return v1, v1 / 2

# ------------------------------------------------------------ R39
R39_VELOCIDADES = (40.0, 80.0, 120.0)      # vmax > 150 km/h (5.2.5)
R39_MARCHA = {40.0: "3", 80.0: "4", 120.0: "5"}


def limite_r39(v2, produccion=False):
    """Maximo de V1 - V2 (km/h): 0.1 V2 + 4 (5.3) o + 6 en la conformidad de la produccion (anexo 3)."""
    return 0.1 * v2 + (6.0 if produccion else 4.0)

# ------------------------------------------------------------ ECE-15
ECE15 = ((0, 0), (11, 0), (15, 15), (23, 15), (28, 0), (49, 0), (61, 32), (85, 32), (96, 0), (117, 0),
         (143, 50), (155, 50), (163, 35), (176, 35), (188, 0), (195, 0))
DURACION_ECE15_S = 195.0
DISTANCIA_ECE15_KM = 0.99403
TOLERANCIA_SEGUIMIENTO_KMH = 2.0     # criterio del equipo (la tolerancia oficial queda pendiente de verificar)
TOLERANCIA_ODOMETRO = 0.01           # el odometro del cuadro contra la distancia real: 1 %


def interpolar(perfil, t):
    for (t0, v0), (t1, v1) in zip(perfil, perfil[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 > t0 else v1
    return perfil[-1][1]


def marcha_ece15(v, objetivo):
    """Cambios del ciclo urbano: 1a hasta 15 km/h, 2a hasta 35, 3a arriba; neutral para detenerse."""
    if objetivo <= 0.0 and v.velocidad < 5.0:
        return "N"
    if v.velocidad < 14.0 or (v.marcha in ("N", "1") and v.velocidad < 15.5):
        return "1"
    if v.velocidad < 34.0 or (v.marcha == "2" and v.velocidad < 35.5):
        return "2"
    return "3"


class Conductor:
    """Robot conductor del banco: sigue un perfil de velocidad con acelerador y freno.

    Calcula la aceleracion que necesita (pendiente del perfil mas una correccion proporcional
    al error) y la convierte en pedal con el mismo modelo del vehiculo."""

    def __init__(self, perfil, elegir_marcha=None, anticipacion_s=0.6, ganancia=1.2):
        self.perfil = perfil
        self.elegir_marcha = elegir_marcha
        self.anticipacion_s = anticipacion_s
        self.ganancia = ganancia

    def objetivo(self, t):
        return self.perfil(t) if callable(self.perfil) else interpolar(self.perfil, t)

    def aplicar(self, v, t):
        objetivo = self.objetivo(t)
        if self.elegir_marcha is not None:
            marcha = self.elegir_marcha(v, objetivo)
            if marcha != v.marcha:
                try:
                    v.cambiar(marcha)
                except ValueError:
                    pass
        v.embrague = 0.0
        pendiente = (self.objetivo(t + self.anticipacion_s) - objetivo) / self.anticipacion_s
        deseada = pendiente + self.ganancia * (objetivo - v.velocidad)        # km/h por segundo
        necesario = deseada + resistencia_al_avance(v.velocidad)
        acelerador = freno = 0.0
        if v.acoplado and necesario > 0:
            acelerador = necesario / max(1.0, v.empuje_maximo())      # el par cambia con rpm y turbo
        else:
            ayuda = FRENO_MOTOR if v.acoplado else 0.0
            if -necesario > ayuda:
                freno = (-necesario - ayuda) / (FRENADO * max(0.05, v.eficiencia_frenos))
        v.acelerador = max(0.0, min(1.0, acelerador))
        v.freno = max(0.0, min(1.0, freno))
        return objetivo


class CadenaCuadro:
    """El cuadro real sin ventana: cada lectura pasa por el formato del archivo y la validacion
    del lector (formatear -> convertir) y llega a EstadoCluster, que avanza un ciclo de 100 ms."""

    CICLO_MS = 100

    def __init__(self, odometro_km=0.0):
        self.reloj = RelojSimulado()
        self.estado = EstadoCluster(self.reloj, odometro_km)

    def aplicar(self, lecturas, extras=None, con_vista=True):
        for clave, valor in {**lecturas, **(extras or {})}.items():
            setter = (CLAVES.get(clave) or CLAVES_EXTRA[clave])[0]
            getattr(self.estado, setter)(convertir(clave, formatear(clave, valor), RANGOS_ESPECIFICACION))
        self.reloj.avanzar(self.CICLO_MS)
        self.estado.tick()
        return (vista(self.estado), vista_extra(self.estado)) if con_vista else None


@dataclass
class Resultado:
    clave: str
    nombre: str
    norma: str
    criterio: str
    medido: str
    aprobado: bool


def _vehiculo(fallas, motor=True, marcha="N", velocidad=0.0):
    """Unidad bajo prueba: puertas cerradas y cinturon abrochado por el inspector. Salvo L01, el
    banco arranca el motor directamente para probar cada subsistema por separado."""
    v = Vehiculo(motor=motor, contacto=motor, cinturon=True, fallas=Fallas(**(fallas or {})))
    v.temp_agua = 90.0 if motor else 40.0
    if marcha != "N":
        v.cambiar(marcha)
    v.velocidad = velocidad
    return v


def _paso(v, ecu, avisos):
    avisos += ecu.vigilar(v, DT)
    v.avanzar(DT)


# ------------------------------------------------------------ pruebas
def prueba_arranque(fallas):
    v, ecu = _vehiculo(fallas, motor=False), Ecu()
    v.contacto = True
    criterio = ("Arranca; en los ultimos 5 s de 30 s de ralenti: 950-1050 rpm estables, aceite >= 1.2 bar "
                "(testigo 9 apagado, R02) y carga >= 13.5 V (R13)")
    motivo = ecu.motivo_sin_arranque(v)
    if motivo:
        return Resultado("L01", "Arranque, ralenti y presion de aceite", "Fin de linea (criterio del equipo)",
                         criterio, f"no arranca: {motivo}", False)
    v.motor = True
    avisos, rpms, voltajes = [], [], []
    for n in range(int(30 / DT)):
        _paso(v, ecu, avisos)
        if n * DT >= 25:
            rpms.append(v.rpm)
            voltajes.append(v.voltaje)
    ok = (v.motor and 950 <= min(rpms) and max(rpms) <= 1050 and v.presion_aceite >= 1.2
          and min(voltajes) >= 13.5)
    medido = (f"{min(rpms):.0f}-{max(rpms):.0f} rpm, aceite {v.presion_aceite:.2f} bar, carga {min(voltajes):.1f} V"
              + (f"; {avisos[-1]}" if avisos else ""))
    return Resultado("L01", "Arranque, ralenti y presion de aceite", "Fin de linea (criterio del equipo)",
                     criterio, medido, ok)


def prueba_testigos(fallas):
    v = _vehiculo(fallas, motor=False)
    cuadro = CadenaCuadro()
    v.contacto = True
    vistos_en_prueba, encendidos_despues = set(), set()
    for n in range(28):                      # 2.8 s en ciclos de 100 ms
        base, extra = cuadro.aplicar(v.lecturas(), v.lecturas_extra("ninguna"))
        if n == 5:
            vistos_en_prueba = {k for k in range(6, 11) if base[k]["encendido"]}
            vistos_en_prueba |= {k for k in (12, 13, 15, 16) if extra[k]["encendido"]}
            vistos_en_prueba |= {14} if extra[14]["reserva"]["encendido"] else set()
        if n >= 22:                          # medio segundo: alcanza a ver un testigo que parpadea
            encendidos_despues |= {k for k in (9, 10) if base[k]["encendido"]}
            encendidos_despues |= {k for k in (13, 15) if extra[k]["encendido"]}
    todos = {6, 7, 8, 9, 10, 12, 13, 14, 15, 16}
    ok = vistos_en_prueba == todos and not encendidos_despues
    medido = (f"encendidos en la prueba: {len(vistos_en_prueba)}/{len(todos)}; despues de 2 s: "
              + (", ".join(f"testigo {k}" for k in sorted(encendidos_despues)) or "ninguno"))
    return Resultado("L02", "Prueba de testigos al dar contacto", "UN R13-H 5.2.21.4",
                     "Todos encienden 2 s y se apagan si no hay falla (9, 10, 13 y 15 apagados)", medido, ok)


def _frenada_tipo0(v, v0=V_TIPO0):
    """Frenada a fondo con el motor desembragado; devuelve (distancia m, dm m/s^2)."""
    v.cambiar("N")
    v.velocidad, v.acelerador, v.freno = v0, 0.0, 1.0
    vb, ve = 0.8 * v0, 0.1 * v0
    s, sb, se = 0.0, None, None
    for _ in range(int(60 / DT)):
        antes = v.velocidad
        v.avanzar(DT)
        tramo = (antes + v.velocidad) / 2 / 3.6 * DT
        for limite, nombre in ((vb, "sb"), (ve, "se")):
            if (sb if nombre == "sb" else se) is None and antes > limite >= v.velocidad:
                cruce = s + tramo * (antes - limite) / (antes - v.velocidad)
                sb, se = (cruce, se) if nombre == "sb" else (sb, cruce)
        s += tramo
        if v.velocidad <= 0.0:
            break
    v.freno = 0.0
    return s, desaceleracion_media(vb, ve, sb, se)


def prueba_tipo0(fallas):
    s, dm = _frenada_tipo0(_vehiculo(fallas))
    maximo = distancia_tipo0(V_TIPO0)
    return Resultado("L03", "Frenado tipo 0 (en frio)", "UN R13-H anexo 3, 2.1.1 A",
                     f"Desde {V_TIPO0:g} km/h: s <= {maximo:g} m y dm >= {DM_TIPO0:g} m/s2",
                     f"s = {s:.1f} m, dm = {dm:.2f} m/s2", s <= maximo and dm >= DM_TIPO0)


def prueba_tipo1(fallas):
    _, dm_frio = _frenada_tipo0(_vehiculo(fallas))
    v1, v2 = velocidades_tipo1(VMAX)
    v = _vehiculo(fallas, marcha="5", velocidad=v1)
    for ciclo in range(1, TIPO1_CICLOS + 1):
        t = 0.0
        while t < TIPO1_CICLO_S:
            if t < 1e-9 or v.freno > 0 and v.velocidad > v2:        # frenada de v1 a v2 a 3 m/s^2
                v.acelerador = 0.0
                falta = TIPO1_DECEL * 3.6 - resistencia_al_avance(v.velocidad) - FRENO_MOTOR
                v.freno = max(0.01, min(1.0, falta / (FRENADO * max(0.05, v.eficiencia_frenos))))
            elif ciclo == TIPO1_CICLOS:                            # tras la ultima frenada: prueba en caliente
                break
            else:                                                  # volver a v1 y sostenerla
                v.freno = 0.0
                v.acelerador = 1.0 if v.velocidad < v1 else resistencia_al_avance(v1) / max(1.0, v.empuje_maximo())
            v.avanzar(DT)
            t += DT
    caliente = v.temp_frenos
    _, dm_caliente = _frenada_tipo0(v)
    minimo = max(TIPO1_PRESCRITO * DM_TIPO0, TIPO1_MEDIDO * dm_frio)
    return Resultado("L04", "Frenado tipo I (perdida de eficiencia en caliente)", "UN R13-H anexo 3, 1.5",
                     f"{TIPO1_CICLOS} frenadas {v1:g}->{v2:g} km/h cada {TIPO1_CICLO_S:g} s; en caliente dm >= "
                     f"75 % de {DM_TIPO0:g} y >= 60 % del valor en frio",
                     f"frenos a {caliente:.0f} C; dm caliente {dm_caliente:.2f} m/s2 (frio {dm_frio:.2f}; minimo "
                     f"{minimo:.2f})", dm_caliente >= minimo)


def prueba_velocimetro(fallas):
    detalle, ok = [], True
    for objetivo in R39_VELOCIDADES:
        v, ecu, avisos = _vehiculo(fallas, marcha=R39_MARCHA[objetivo], velocidad=objetivo), Ecu(), []
        conductor, cuadro = Conductor(lambda _t, o=objetivo: o), CadenaCuadro()
        diferencias = []
        for n in range(int(20 / DT)):
            conductor.aplicar(v, n * DT)
            _paso(v, ecu, avisos)
            if n % 2 == 0:                        # el cuadro lee cada 100 ms
                base, _ = cuadro.aplicar(v.lecturas(), v.lecturas_extra(ecu.proteccion))
                if n * DT >= 10:                  # se mide ya estabilizado
                    diferencias.append(base[1]["valor"] - v.velocidad)
        menor, mayor = min(diferencias), max(diferencias)
        ok = ok and menor >= 0.0 and mayor <= limite_r39(objetivo)
        detalle.append(f"{objetivo:g}: {menor:+.2f} a {mayor:+.2f}")
    return Resultado("L05", "Exactitud del velocimetro", "UN R39 5.2.5, 5.3 y anexo 3",
                     "A 40, 80 y 120 km/h: 0 <= V1 - V2 <= 0.1 V2 + 4 km/h (nunca indica menos)",
                     "V1 - V2 en km/h: " + "; ".join(detalle), ok)


def recorrer_ece15(fallas=None, odometro_km=0.0):
    """Conduce el ciclo urbano completo; devuelve (vehiculo, cuadro, error maximo, km reales, avisos)."""
    v, ecu, avisos = _vehiculo(fallas), Ecu(), []
    v.temp_agua = 40.0                       # el ciclo empieza con el motor frio
    conductor, cuadro = Conductor(ECE15, marcha_ece15), CadenaCuadro(odometro_km)
    error, km, t, n = 0.0, 0.0, 0.0, 0
    while t < DURACION_ECE15_S - 1e-9:
        conductor.aplicar(v, t)
        _paso(v, ecu, avisos)
        t, n = t + DT, n + 1
        km += v.velocidad * DT / 3600
        error = max(error, abs(v.velocidad - conductor.objetivo(t)))
        if n % 2 == 0:
            cuadro.aplicar(v.lecturas(), v.lecturas_extra(ecu.proteccion), con_vista=False)
    return v, cuadro, error, km, avisos


def prueba_ece15(fallas):
    v, cuadro, error, km, avisos = recorrer_ece15(fallas)
    odometro = cuadro.estado.odometro.km
    desvio_ciclo = abs(km - DISTANCIA_ECE15_KM) / DISTANCIA_ECE15_KM
    desvio_odometro = abs(odometro - km) / km if km > 0 else 1.0
    ok = error <= TOLERANCIA_SEGUIMIENTO_KMH and desvio_ciclo <= 0.02 and desvio_odometro <= TOLERANCIA_ODOMETRO
    consumo = (COMBUSTIBLE_INICIAL_L - v.combustible_l) / km * 100 if km > 0 else 0.0
    medido = (f"error maximo {error:.2f} km/h; distancia real {km:.4f} km; odometro del cuadro {odometro:.4f} km "
              f"({desvio_odometro * 100:.2f} %); consumo {consumo:.1f} L/100 km (informativo)")
    if avisos:
        medido += f"; {avisos[-1]}"
    return Resultado("L06", "Ciclo urbano ECE-15 y odometro", "ECE-15 (prueba tipo I de emisiones)",
                     f"195 s y {DISTANCIA_ECE15_KM:g} km (+-2 %); seguimiento <= {TOLERANCIA_SEGUIMIENTO_KMH:g} "
                     f"km/h; odometro del cuadro a <= 1 % de la distancia real", medido, ok)


def prueba_enfriamiento(fallas):
    v, ecu, avisos = _vehiculo(fallas, marcha="5", velocidad=250.0), Ecu(), []
    conductor, maxima = Conductor(lambda _t: 250.0), v.temp_agua
    for n in range(int(300 / DT)):
        conductor.aplicar(v, n * DT)
        _paso(v, ecu, avisos)
        maxima = max(maxima, v.temp_agua)
        if not v.motor:
            break
    ok = v.motor and maxima <= 110.0
    medido = f"agua maxima {maxima:.1f} C en {n * DT:.0f} s a 250 km/h" + (f"; {avisos[-1]}" if avisos else "")
    return Resultado("L07", "Enfriamiento a carga sostenida", "Criterio del equipo (no es una norma)",
                     "300 s a 250 km/h sin pasar de 110 C (R04) ni detener el motor", medido, ok)


def prueba_turbo(fallas):
    v, ecu, avisos = _vehiculo(fallas, marcha="3", velocidad=100.0), Ecu(), []
    maxima = 0.0
    v.acelerador = 1.0
    for _ in range(int(6 / DT)):
        _paso(v, ecu, avisos)
        maxima = max(maxima, v.presion_turbo)
        if not v.motor:
            break
    ok = v.motor and maxima <= 1.5
    medido = f"presion maxima {maxima:.2f} bar" + (f"; {avisos[-1]}" if avisos else "")
    return Resultado("L08", "Turbo y valvula de descarga a plena carga", "Criterio del equipo (umbral de R05)",
                     "6 s a fondo en 3a desde 100 km/h: presion <= 1.5 bar sin corte", medido, ok)


def prueba_puertas(fallas):
    v, ecu, avisos = _vehiculo(fallas, marcha="1"), Ecu(), []
    cuadro = CadenaCuadro()
    v.puertas, v.acelerador = 1, 1.0
    testigo = False
    for n in range(int(3 / DT)):
        _paso(v, ecu, avisos)
        if n % 2 == 0:
            _, extra = cuadro.aplicar(v.lecturas(), v.lecturas_extra(ecu.proteccion))
            testigo = testigo or extra[12]["encendido"]
    abierta = v.velocidad
    v.puertas = 0
    for _ in range(int(3 / DT)):
        _paso(v, ecu, avisos)
    ok = abierta < 1.0 and testigo and v.velocidad > 10.0
    return Resultado("L09", "Interbloqueo de puertas", "Medida de seguridad agregada (el F40 de 1987 no la tenia)",
                     "Con la puerta abierta no avanza aunque se acelere y el testigo 12 enciende; al cerrar avanza",
                     f"puerta abierta: {abierta:.1f} km/h, testigo {'encendido' if testigo else 'apagado'}; "
                     f"cerrada: {v.velocidad:.1f} km/h en 3 s", ok)


PRUEBAS = (prueba_arranque, prueba_testigos, prueba_tipo0, prueba_tipo1, prueba_velocimetro, prueba_ece15,
           prueba_enfriamiento, prueba_turbo, prueba_puertas)
FALLAS = ("fuga_aceite", "radiador", "sobrepresion_turbo", "frenos", "velocimetro", "alternador", "ecu_banco")


def ejecutar_banco(fallas=None):
    """Corre las 9 pruebas sobre una unidad con las fallas dadas ({nombre: True})."""
    return [prueba(fallas or {}) for prueba in PRUEBAS]


def dictamen(resultados):
    rechazadas = [r.clave for r in resultados if not r.aprobado]
    if not rechazadas:
        return f"APTO PARA PRODUCCION ({len(resultados)}/{len(resultados)} pruebas aprobadas)"
    return f"RECHAZADO: fallaron {', '.join(rechazadas)} ({len(resultados) - len(rechazadas)}/{len(resultados)} aprobadas)"
