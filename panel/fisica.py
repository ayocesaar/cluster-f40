"""Modelo fisico simplificado del vehiculo para el panel de control.

Convierte pedales, marcha y contacto en las lecturas que el cluster espera en
datos/vehiculo.conf. Es didactico, no una simulacion del F40 real: las cifras de
abajo son APROXIMADAS y quedan pendientes de verificar contra una ficha tecnica
oficial. Lo que si se garantiza (CP-159) es que todo valor producido esta dentro
de los rangos de la especificacion, para que el panel nunca genere un dato invalido.

Unidades: velocidad en km/h, rpm, presiones en bar, temperatura en C, tiempo en s.

Etapa 18 (realismo): las fallas tienen consecuencias fisicas. Con falla de frenos el auto
frena al 30 % (un circuito hidraulico perdido) y los frenos calientes pierden eficiencia
(fading); la fuga de aceite vacia el deposito y, bajo 30 %, la presion se desploma; el
consumo vacia el tanque de 120 L y sin combustible el motor se apaga; la temperatura sube
con la carga. Las decisiones de proteccion (no arrancar, cortar el motor, bloquear la
traccion con una puerta abierta) no estan aqui: las toma panel/ecu.py.

Etapa 20: sistema electrico (bateria de 40 Ah, alternador regulado a 14.2 V y cargas de
encendido, luces y ventilador; la descarga va 60 veces mas rapido para que se vea en la
demostracion), ventilador del radiador con histeresis (98/92 C) y la falla de una de las dos
unidades Weber-Marelli del F40 (una por banco de cilindros): el motor sigue con 4 cilindros,
con la mitad del empuje, un solo turbo y el ralenti irregular.

Etapa 21: el empuje sigue una curva de par aproximada que pasa por los dos datos verificados del
F40 (577 Nm a 4000 rpm y 478 CV a 7000 rpm, unos 480 Nm) y depende de la presion del turbo: bajo
2500 rpm, o mientras el turbo carga, el motor empuja como uno atmosferico (se siente el retraso del
turbo). Las llantas tienen un limite de adherencia y el F40 no tenia ABS ni control de traccion
(revista de Ferrari): si se pide mas, las traseras patinan al acelerar o las cuatro se bloquean al
frenar, y en pista mojada el limite baja a 55 %. El aceite tiene su propia temperatura: sigue a la
del agua, mas lento, y sube con la carga."""

import math
from dataclasses import dataclass, field

RALENTI = 1000
CORTE = 7750                 # rpm de referencia para las velocidades por marcha (aprox.)
LIMITADOR = 8200             # permite ver el tacometro en rojo (R03: >= 8000)
# Velocidad aproximada al llegar a CORTE en cada marcha (pendiente de verificar).
VELOCIDAD_AL_CORTE = {"1": 90.0, "2": 135.0, "3": 190.0, "4": 255.0, "5": 324.0, "R": 50.0}
# Empuje por marcha en km/h por segundo con el par maximo (Etapa 21: se multiplica por el factor de
# par). Calibrado para que el 0-100 de unos 4.2 s y la maxima unos 326 km/h; datos publicados del
# F40: 4.1 s (la cifra mas citada; hay pruebas de 3.5 a 5.0 s) y 324 km/h.
EMPUJE = {"1": 48.0, "2": 35.2, "3": 24.0, "4": 16.0, "5": 10.4, "R": 19.2}
RESISTENCIA_BASE = 0.8           # km/h por segundo: rodadura y transmision (aprox.)
RESISTENCIA_AIRE = 0.000065      # por (km/h)^2: calibrada con la maxima publicada de 324 km/h
FRENADO = 45.0               # km/h por segundo con el freno a fondo
FRENO_MOTOR = 2.0            # km/h por segundo en marcha sin acelerar
TURBO_MAXIMO = 1.1           # bar de sobrepresion normal (aprox.)
TURBO_RETRASO_S = 0.5        # constante de tiempo del turbo (retraso perceptible)
TEMPERATURA_NORMAL = 90.0
TEMPERATURA_SOBRECALENTADO = 125.0
CALENTAMIENTO_S = 20.0       # constante de tiempo del motor (acelerada para la demostracion)
CARGA_TERMICA = 12.0         # C adicionales a plena carga sobre la temperatura normal (aprox.)
TANQUE_L = 120.0             # capacidad del tanque del F40 (cararac.com y auto-data.net)
COMBUSTIBLE_INICIAL_L = 60.0
CONSUMO_RALENTI_LH = 2.0     # litros por hora en ralenti (aprox.)
CONSUMO_PLENA_LH = 140.0     # litros por hora a plena carga (aprox.: unos 350 kW con 300 g/kWh)
FRENADO_CON_FALLA = 0.30     # fraccion del frenado que queda con un circuito perdido (aprox.)
MASA_KG = 1350.0             # con conductor e instrumentos de prueba (aprox.)
CALOR_FRENOS_J_K = 6000.0    # capacidad termica de discos y pastillas (aprox.)
AMBIENTE_C = 25.0
FADING_DESDE_C, FADING_HASTA_C, FADING_MINIMO = 350.0, 750.0, 0.60   # eficiencia de 1.0 a 0.6 (aprox.)
FUGA_ACEITE_PCT_S = 0.5      # % del deposito por segundo con el motor en marcha (aprox.)
NIVEL_ACEITE_CRITICO = 30.0  # % bajo el cual la bomba toma aire y la presion cae
ERROR_VELOCIMETRO_FALLA = 0.05   # el sensor descalibrado indica 5 % menos que la velocidad real
# Sistema electrico (cifras genericas de un sistema de 12 V, aprox.; no son del F40).
CAPACIDAD_BATERIA_AH = 40.0
ACELERACION_ELECTRICA = 60.0     # la bateria se carga y descarga 60 veces mas rapido (demostracion)
CARGA_BASE_A = 12.0              # encendido, las dos unidades Weber-Marelli y las bombas de combustible
CARGA_LUCES_A = 10.0
CARGA_VENTILADOR_A = 15.0
ALTERNADOR_MAXIMO_A = 70.0
VOLTAJE_REGULADO = 14.2
RESISTENCIA_INTERNA = 0.02       # ohm
VENTILADOR_ENCIENDE, VENTILADOR_APAGA = 98.0, 92.0   # C
ENFRIAMIENTO_VENTILADOR = 6.0    # C menos de temperatura objetivo con el ventilador encendido
RALENTI_IRREGULAR = 130.0        # rpm de vaiven con un banco sin encendido
# Etapa 21: par y adherencia (aprox.; los dos puntos de la curva marcados son datos verificados).
PAR_MAXIMO_NM = 577.0            # verificado: a 4000 rpm
PAR_CURVA = ((0, 180.0), (1000, 230.0), (2500, 330.0), (3000, 450.0), (4000, 577.0), (5000, 565.0),
             (6000, 530.0), (7000, 480.0), (8200, 400.0))      # 7000 rpm: 478 CV = unos 480 Nm (verificado)
PAR_ATMOSFERICO = ((0, 180.0), (1000, 230.0), (2500, 270.0), (4000, 290.0), (7000, 260.0), (8200, 230.0))
TRACCION_MAXIMA = 37.0           # km/h por segundo que aguantan las llantas traseras en seco
FRENADO_ADHERENCIA = 48.0        # km/h por segundo que aguantan las cuatro llantas en seco
ADHERENCIA_MOJADO = 0.55
DESLIZAMIENTO = 0.8              # una llanta que patina o va bloqueada agarra 20 % menos
ACEITE_SOBRE_AGUA = 8.0          # C: el aceite trabaja algo mas caliente que el agua
ACEITE_CARGA = 22.0              # C adicionales a plena carga
ACEITE_CONSTANTE_S = 45.0        # el aceite se calienta mas lento que el agua (CALENTAMIENTO_S)
MARCHAS = ("R", "N", "1", "2", "3", "4", "5")
RANGOS = {"velocidad": (0.0, 360.0), "rpm": (0, 9000), "presion_aceite": (0.0, 10.0),
          "temp_agua": (40.0, 130.0), "presion_turbo": (0.0, 2.0)}


def _limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _interpolar(puntos, x):
    for (x0, y0), (x1, y1) in zip(puntos, puntos[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * _limitar((x - x0) / (x1 - x0), 0.0, 1.0)
    return puntos[-1][1]


def resistencia_al_avance(velocidad):
    """Desaceleracion por rodadura y aire en km/h por segundo."""
    return RESISTENCIA_BASE + RESISTENCIA_AIRE * velocidad ** 2


def velocidad_maxima(marcha):
    """Velocidad a la que esa marcha llega al limitador."""
    return VELOCIDAD_AL_CORTE[marcha] * LIMITADOR / CORTE


@dataclass
class Fallas:
    fuga_aceite: bool = False          # R02: la presion cae bajo 1 bar en ralenti
    radiador: bool = False             # R04: la temperatura sube a 125 C
    sobrepresion_turbo: bool = False   # R05: el turbo pasa de 1.5 bar
    frenos: bool = False               # R08: testigo de falla de frenos y frenado al 30 %
    velocimetro: bool = False          # sensor de velocidad descalibrado: indica 5 % menos (UN R39)
    alternador: bool = False           # R13: no carga; la bateria se descarga
    ecu_banco: bool = False            # una unidad Weber-Marelli sin encendido: el motor anda con 4 cilindros


@dataclass
class Vehiculo:
    motor: bool = False
    marcha: str = "N"
    acelerador: float = 0.0     # 0 a 1
    freno: float = 0.0          # 0 a 1
    embrague: float = 0.0       # 0 a 1 (1 = pisado: motor desacoplado)
    velocidad: float = 0.0
    rpm: float = 0.0
    presion_turbo: float = 0.0
    temp_agua: float = 40.0
    luces_altas: bool = False
    direccional: str = "OFF"
    emergencia: bool = False
    fallas: Fallas = field(default_factory=Fallas)
    # Etapa 18
    contacto: bool = False
    puertas: int = 0            # bits de estado: 1 conductor, 2 pasajero
    cinturon: bool = False      # cinturon del conductor abrochado
    combustible_l: float = COMBUSTIBLE_INICIAL_L
    nivel_aceite: float = 100.0  # % del deposito de aceite
    temp_frenos: float = AMBIENTE_C
    traccion_bloqueada: bool = False   # lo fija la ECU (interbloqueo de puertas)
    # Etapa 20
    bateria: float = 1.0        # carga de la bateria, 0 a 1
    ventilador: bool = False
    tiempo_s: float = 0.0
    # Etapa 21
    mojado: bool = False        # pista mojada: 55 % de adherencia
    patinando: bool = False     # las traseras patinan al acelerar (sin control de traccion)
    bloqueado: bool = False     # las llantas se bloquean al frenar (sin ABS)
    temp_aceite: float = 40.0

    # ----------------------------------------------------------------- mandos
    def cambiar(self, marcha):
        if marcha not in MARCHAS:
            raise ValueError(f"marcha desconocida: {marcha!r}")
        if marcha == "R" and self.velocidad > 5:
            raise ValueError("reversa rechazada: el vehiculo avanza")
        if marcha not in ("N", "R") and self.velocidad > velocidad_maxima(marcha) + 1:
            raise ValueError(f"cambio a {marcha} rechazado: el motor pasaria del limitador")
        self.marcha = marcha

    @property
    def acoplado(self):
        return self.motor and self.marcha != "N" and self.embrague < 0.5

    # ----------------------------------------------------------------- fisica
    def avanzar(self, dt):
        """Avanza dt segundos (se recomienda 0.05)."""
        if dt <= 0:
            return
        self.tiempo_s += dt
        mitad = 0.5 if self.fallas.ecu_banco else 1.0          # un banco sin encendido: medio motor
        # Con la traccion bloqueada por la ECU (puerta abierta) el acelerador no tiene efecto.
        acelerador = 0.0 if self.traccion_bloqueada else _limitar(self.acelerador, 0.0, 1.0)
        freno = _limitar(self.freno, 0.0, 1.0)

        if not self.motor:
            self.rpm = max(0.0, self.rpm - 4000 * dt)
            empuje = 0.0
            self.patinando = False
        elif self.acoplado:
            relacion = CORTE / VELOCIDAD_AL_CORTE[self.marcha]       # rpm por km/h
            corte = self.rpm >= LIMITADOR - 1                        # el limitador corta la inyeccion
            empuje = 0.0 if corte else acelerador * EMPUJE[self.marcha] * mitad * self.factor_par
            limite = TRACCION_MAXIMA * self.adherencia
            self.patinando = empuje > limite                         # sin control de traccion
            if self.patinando:
                empuje = limite * DESLIZAMIENTO
            if acelerador == 0:
                empuje -= FRENO_MOTOR
        else:
            self.patinando = False
            objetivo = RALENTI + acelerador * (LIMITADOR - RALENTI)  # revoluciones en vacio
            if self.fallas.ecu_banco:                                # ralenti irregular
                objetivo += RALENTI_IRREGULAR * math.sin(2 * math.pi * 1.3 * self.tiempo_s) * (1 - acelerador)
            paso = (6000 if objetivo > self.rpm else 3000) * dt
            self.rpm += _limitar(objetivo - self.rpm, -paso, paso)
            empuje = 0.0

        resistencia = resistencia_al_avance(self.velocidad)
        frenado = FRENADO * freno * self.eficiencia_frenos
        limite_freno = FRENADO_ADHERENCIA * self.adherencia
        self.bloqueado = frenado > limite_freno and self.velocidad > 1.0       # sin ABS
        if self.bloqueado:
            frenado = limite_freno * DESLIZAMIENTO
        decel = resistencia + frenado
        antes = self.velocidad
        self.velocidad = max(0.0, self.velocidad + (empuje - decel) * dt)
        if self.motor and self.acoplado:
            self.velocidad = min(self.velocidad, LIMITADOR / relacion)
            self.rpm = max(RALENTI, self.velocidad * relacion)
        self._temperatura_frenos(frenado, antes, dt)

        # Turbo: sigue al acelerador con retraso y solo da presion por encima de 2500 rpm.
        carga = acelerador * _limitar((self.rpm - 2500) / 2500, 0.0, 1.0) if self.motor else 0.0
        maximo = TURBO_MAXIMO * (1.65 if self.fallas.sobrepresion_turbo else 1.0) * (0.55 if mitad < 1 else 1.0)
        objetivo_turbo = maximo * carga
        self.presion_turbo += (objetivo_turbo - self.presion_turbo) * min(1.0, dt / TURBO_RETRASO_S)

        # Temperatura: se acerca a la de operacion con el motor encendido y se enfria apagado.
        carga_motor = acelerador * _limitar(self.rpm / 7000.0, 0.0, 1.0) if self.motor else 0.0
        if self.motor:
            objetivo_t = (TEMPERATURA_SOBRECALENTADO if self.fallas.radiador
                          else TEMPERATURA_NORMAL + CARGA_TERMICA * carga_motor
                          - (ENFRIAMIENTO_VENTILADOR if self.ventilador else 0.0))
        else:
            objetivo_t = 40.0
        self.temp_agua += (objetivo_t - self.temp_agua) * min(1.0, dt / CALENTAMIENTO_S)

        # Aceite: sigue al agua mas lento y se calienta con la carga; con poco aceite, mas.
        if self.motor:
            objetivo_aceite = (self.temp_agua + ACEITE_SOBRE_AGUA + ACEITE_CARGA * carga_motor
                               + (15.0 if self.nivel_aceite < NIVEL_ACEITE_CRITICO else 0.0))
        else:
            objetivo_aceite = 40.0
        self.temp_aceite += (objetivo_aceite - self.temp_aceite) * min(1.0, dt / ACEITE_CONSTANTE_S)

        # Ventilador del radiador con histeresis.
        if self.motor and self.temp_agua >= VENTILADOR_ENCIENDE:
            self.ventilador = True
        elif not self.motor or self.temp_agua <= VENTILADOR_APAGA:
            self.ventilador = False
        # Bateria: el alternador carga lo que sobra de las cargas; si no carga, la bateria las paga.
        cargas, generacion = self._corrientes()
        cambio = (generacion - cargas) * dt * ACELERACION_ELECTRICA / 3600.0 / CAPACIDAD_BATERIA_AH
        self.bateria = _limitar(self.bateria + cambio, 0.0, 1.0)

        # Combustible: sin combustible el motor se apaga solo.
        if self.motor:
            consumo_lh = CONSUMO_RALENTI_LH + CONSUMO_PLENA_LH * carga_motor
            self.combustible_l = max(0.0, self.combustible_l - consumo_lh * dt / 3600.0)
            if self.combustible_l == 0.0:
                self.motor = False
        # Aceite: la fuga vacia el deposito (mas rapido con el motor en marcha, por la presion).
        if self.fallas.fuga_aceite:
            ritmo = FUGA_ACEITE_PCT_S if self.motor else FUGA_ACEITE_PCT_S / 10
            self.nivel_aceite = max(0.0, self.nivel_aceite - ritmo * dt)

    @property
    def adherencia(self):
        return ADHERENCIA_MOJADO if self.mojado else 1.0

    @property
    def factor_par(self):
        """Par disponible / par maximo: atmosferico mas lo que aporta el turbo segun su presion."""
        rpm = self.rpm
        atmosferico = _interpolar(PAR_ATMOSFERICO, rpm)
        con_turbo = _interpolar(PAR_CURVA, rpm)
        soplido = _limitar(self.presion_turbo / TURBO_MAXIMO, 0.0, 1.0)
        return (atmosferico + (con_turbo - atmosferico) * soplido) / PAR_MAXIMO_NM

    def empuje_maximo(self):
        """km/h por segundo que daria el acelerador a fondo ahora (lo usa el robot conductor)."""
        if not self.motor or self.marcha in ("N",):
            return 0.0
        mitad = 0.5 if self.fallas.ecu_banco else 1.0
        return min(EMPUJE[self.marcha] * mitad * self.factor_par, TRACCION_MAXIMA * self.adherencia)

    def _corrientes(self):
        """(cargas, generacion) en amperes."""
        cargas = ((CARGA_BASE_A if self.contacto or self.motor else 0.0) + CARGA_LUCES_A * self.luces_altas
                  + CARGA_VENTILADOR_A * self.ventilador)
        gira = self.motor and not self.fallas.alternador and self.rpm > 300
        return cargas, (min(ALTERNADOR_MAXIMO_A, 25.0 + 0.012 * self.rpm) if gira else 0.0)

    @property
    def voltaje_reposo(self):
        """Voltaje de la bateria sin carga: 12.7 V llena; bajo 10 % se desploma."""
        b = _limitar(self.bateria, 0.0, 1.0)
        return 11.6 + 1.1 * b if b >= 0.1 else 9.0 + 26.0 * b

    @property
    def voltaje(self):
        """Con el alternador al dia, el regulador fija 14.2 V; si no, la bateria cae por su resistencia interna."""
        cargas, generacion = self._corrientes()
        if generacion > 0 and generacion >= cargas:
            return VOLTAJE_REGULADO
        return max(0.0, self.voltaje_reposo - (cargas - generacion) * RESISTENCIA_INTERNA)

    def _temperatura_frenos(self, frenado_kmh_s, antes_kmh, dt):
        """Los frenos convierten la energia del auto en calor y se enfrian con el aire (mas rapido al avanzar)."""
        media_ms = (antes_kmh + self.velocidad) / 2 / 3.6
        energia = MASA_KG * (frenado_kmh_s / 3.6) * media_ms * dt
        energia = min(energia, 0.5 * MASA_KG * (antes_kmh / 3.6) ** 2)
        self.temp_frenos += energia / CALOR_FRENOS_J_K
        enfriamiento = (0.001 + 0.00008 * media_ms) * dt
        self.temp_frenos -= (self.temp_frenos - AMBIENTE_C) * min(1.0, enfriamiento)

    @property
    def eficiencia_frenos(self):
        """1.0 con frenos frios; baja con la temperatura (fading) y queda en 30 % con un circuito perdido."""
        caliente = _limitar((self.temp_frenos - FADING_DESDE_C) / (FADING_HASTA_C - FADING_DESDE_C), 0.0, 1.0)
        eficiencia = 1.0 - (1.0 - FADING_MINIMO) * caliente
        return eficiencia * (FRENADO_CON_FALLA if self.fallas.frenos else 1.0)

    @property
    def presion_aceite(self):
        """Sube con las rpm (1.5 bar en ralenti, 5.5 bar arriba); una fuga la reduce."""
        if not self.motor or self.rpm <= 0:
            return 0.0
        presion = 1.5 + 4.0 * _limitar((self.rpm - RALENTI) / (CORTE - RALENTI), 0.0, 1.0)
        presion *= 0.45 if self.fallas.fuga_aceite else 1.0
        return presion * _limitar(self.nivel_aceite / NIVEL_ACEITE_CRITICO, 0.0, 1.0)

    def velocidad_indicada(self):
        """Lo que mide el sensor de velocidad: decimas de km/h redondeadas hacia arriba, para no
        indicar nunca menos que la velocidad real (UN R39 5.3); descalibrado indica 5 % menos."""
        real = self.velocidad * (1 - ERROR_VELOCIMETRO_FALLA if self.fallas.velocimetro else 1.0)
        return min(360.0, math.ceil(round(_limitar(real, 0.0, 360.0) * 10, 6)) / 10)

    # ----------------------------------------------------------------- salida
    def lecturas(self):
        """Valores ya tipados y dentro de rango, en el formato que espera escribir_atomico."""
        def limitado(clave, valor):
            minimo, maximo = RANGOS[clave]
            return _limitar(valor, minimo, maximo)
        return {
            "motor": self.motor,
            "velocidad": self.velocidad_indicada(),
            "rpm": int(round(limitado("rpm", self.rpm))),
            "presion_aceite": round(limitado("presion_aceite", self.presion_aceite), 2),
            "temp_agua": round(limitado("temp_agua", self.temp_agua), 1),
            "presion_turbo": round(limitado("presion_turbo", self.presion_turbo), 2),
            "direccional": self.direccional,
            "luces_altas": self.luces_altas,
            "emergencia": self.emergencia,
            "falla_frenos": self.fallas.frenos,
        }

    def lecturas_extra(self, falla_motor="ninguna"):
        """Claves opcionales de la Etapa 18 (contacto, puertas, cinturon, combustible y la causa
        de proteccion que informa la ECU), ya tipadas y dentro de rango."""
        return {
            "contacto": bool(self.contacto or self.motor),
            "puertas": int(self.puertas) & 3,
            "cinturon": bool(self.cinturon),
            "combustible": round(_limitar(100.0 * self.combustible_l / TANQUE_L, 0.0, 100.0), 1),
            "falla_motor": falla_motor,
            "voltaje": round(_limitar(self.voltaje, 0.0, 20.0), 1),
            "temp_aceite": round(_limitar(self.temp_aceite, 0.0, 160.0), 1),
        }
