"""Modelo fisico simplificado del vehiculo para el panel de control.

Convierte pedales, marcha y contacto en las lecturas que el cluster espera en
datos/vehiculo.conf. Es didactico, no una simulacion del F40 real: las cifras de
abajo son APROXIMADAS y quedan pendientes de verificar contra una ficha tecnica
oficial. Lo que si se garantiza (CP-159) es que todo valor producido esta dentro
de los rangos de la especificacion, para que el panel nunca genere un dato invalido.

Unidades: velocidad en km/h, rpm, presiones en bar, temperatura en C, tiempo en s."""

from dataclasses import dataclass, field

RALENTI = 1000
CORTE = 7750                 # rpm de referencia para las velocidades por marcha (aprox.)
LIMITADOR = 8200             # permite ver el tacometro en rojo (R03: >= 8000)
# Velocidad aproximada al llegar a CORTE en cada marcha (pendiente de verificar).
VELOCIDAD_AL_CORTE = {"1": 90.0, "2": 135.0, "3": 190.0, "4": 255.0, "5": 324.0, "R": 50.0}
# Empuje maximo por marcha en km/h por segundo (aprox.; da un 0-100 de unos 4 s).
EMPUJE = {"1": 30.0, "2": 22.0, "3": 15.0, "4": 10.0, "5": 6.5, "R": 12.0}
FRENADO = 45.0               # km/h por segundo con el freno a fondo
FRENO_MOTOR = 2.0            # km/h por segundo en marcha sin acelerar
TURBO_MAXIMO = 1.1           # bar de sobrepresion normal (aprox.)
TURBO_RETRASO_S = 0.5        # constante de tiempo del turbo (retraso perceptible)
TEMPERATURA_NORMAL = 90.0
TEMPERATURA_SOBRECALENTADO = 125.0
CALENTAMIENTO_S = 20.0       # constante de tiempo del motor (acelerada para la demostracion)
MARCHAS = ("R", "N", "1", "2", "3", "4", "5")
RANGOS = {"velocidad": (0.0, 360.0), "rpm": (0, 9000), "presion_aceite": (0.0, 10.0),
          "temp_agua": (40.0, 130.0), "presion_turbo": (0.0, 2.0)}


def _limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def velocidad_maxima(marcha):
    """Velocidad a la que esa marcha llega al limitador."""
    return VELOCIDAD_AL_CORTE[marcha] * LIMITADOR / CORTE


@dataclass
class Fallas:
    fuga_aceite: bool = False          # R02: la presion cae bajo 1 bar en ralenti
    radiador: bool = False             # R04: la temperatura sube a 125 C
    sobrepresion_turbo: bool = False   # R05: el turbo pasa de 1.5 bar
    frenos: bool = False               # R08: testigo de falla de frenos


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
        acelerador = _limitar(self.acelerador, 0.0, 1.0)
        freno = _limitar(self.freno, 0.0, 1.0)

        if not self.motor:
            self.rpm = max(0.0, self.rpm - 4000 * dt)
            empuje = 0.0
        elif self.acoplado:
            relacion = CORTE / VELOCIDAD_AL_CORTE[self.marcha]       # rpm por km/h
            corte = self.rpm >= LIMITADOR - 1                        # el limitador corta la inyeccion
            empuje = 0.0 if corte else acelerador * EMPUJE[self.marcha]
            if acelerador == 0:
                empuje -= FRENO_MOTOR
        else:
            objetivo = RALENTI + acelerador * (LIMITADOR - RALENTI)  # revoluciones en vacio
            paso = (6000 if objetivo > self.rpm else 3000) * dt
            self.rpm += _limitar(objetivo - self.rpm, -paso, paso)
            empuje = 0.0

        resistencia = 0.8 + 0.00005 * self.velocidad ** 2
        decel = resistencia + FRENADO * freno
        self.velocidad = max(0.0, self.velocidad + (empuje - decel) * dt)
        if self.motor and self.acoplado:
            self.velocidad = min(self.velocidad, LIMITADOR / relacion)
            self.rpm = max(RALENTI, self.velocidad * relacion)

        # Turbo: sigue al acelerador con retraso y solo da presion por encima de 2500 rpm.
        carga = acelerador * _limitar((self.rpm - 2500) / 2500, 0.0, 1.0) if self.motor else 0.0
        maximo = TURBO_MAXIMO * (1.65 if self.fallas.sobrepresion_turbo else 1.0)
        objetivo_turbo = maximo * carga
        self.presion_turbo += (objetivo_turbo - self.presion_turbo) * min(1.0, dt / TURBO_RETRASO_S)

        # Temperatura: se acerca a la de operacion con el motor encendido y se enfria apagado.
        if self.motor:
            objetivo_t = TEMPERATURA_SOBRECALENTADO if self.fallas.radiador else TEMPERATURA_NORMAL
        else:
            objetivo_t = 40.0
        self.temp_agua += (objetivo_t - self.temp_agua) * min(1.0, dt / CALENTAMIENTO_S)

    @property
    def presion_aceite(self):
        """Sube con las rpm (1.5 bar en ralenti, 5.5 bar arriba); una fuga la reduce."""
        if not self.motor or self.rpm <= 0:
            return 0.0
        presion = 1.5 + 4.0 * _limitar((self.rpm - RALENTI) / (CORTE - RALENTI), 0.0, 1.0)
        return presion * (0.45 if self.fallas.fuga_aceite else 1.0)

    # ----------------------------------------------------------------- salida
    def lecturas(self):
        """Valores ya tipados y dentro de rango, en el formato que espera escribir_atomico."""
        def limitado(clave, valor):
            minimo, maximo = RANGOS[clave]
            return _limitar(valor, minimo, maximo)
        return {
            "motor": self.motor,
            "velocidad": round(limitado("velocidad", self.velocidad), 1),
            "rpm": int(round(limitado("rpm", self.rpm))),
            "presion_aceite": round(limitado("presion_aceite", self.presion_aceite), 2),
            "temp_agua": round(limitado("temp_agua", self.temp_agua), 1),
            "presion_turbo": round(limitado("presion_turbo", self.presion_turbo), 2),
            "direccional": self.direccional,
            "luces_altas": self.luces_altas,
            "emergencia": self.emergencia,
            "falla_frenos": self.fallas.frenos,
        }
