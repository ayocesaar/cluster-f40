"""Estado central del cluster de instrumentos simulado del Ferrari F40.

Esta clase NO importa Tkinter: expone unicamente datos ya calculados (valores
numericos y colores/estados de cada indicador) para que la interfaz grafica
(ui/tablero.py) solo tenga que leerlos y dibujarlos, sin logica de negocio.

Resumen de reglas implementadas:
  R01 - Encendido/apagado general.
  R02 - Testigo de baja presion de aceite, con retardo >=1s e histeresis.
  R03 - Tacometro en rojo (rpm alto) con histeresis.
  R04 - Temperatura de agua en rojo con histeresis.
  R05 - Contorno ambar de presion de turbo con histeresis.
  R06 - Parpadeo de direccionales (verde, 500 ms).
  R07 - Luces altas (azul fijo) e intermitentes de emergencia (ambar, 500 ms,
        con precedencia visual sobre el testigo de giro).
  R08 - Testigo de falla de frenos (rojo, parpadeo 300 ms).

Nota de diseno (resuelve una ambiguedad de la guia original, documentada
tambien en el informe): al apagar el motor (R01, encendido=0) se apaga
tambien el testigo 9 (baja presion de aceite) y el amber inmediato del
elemento 2, reiniciando los temporizadores de histeresis. De lo contrario,
ambos indicadores se encenderian falsamente al apagar el motor, porque R01
fuerza p_aceite a 0.
"""

CICLO_RAPIDO_MS = 100.0   # velocidad, p_aceite, rpm, p_turbo
CICLO_LENTO_MS = 500.0    # temp_agua, direccionales, emergencia
CICLO_FRENOS_MS = 300.0   # falla de frenos
RETARDO_HISTERESIS_ACEITE_MS = 1000.0

DIRECCIONALES_VALIDAS = ("OFF", "IZQ", "DER")


def _validar_numero(valor, nombre, minimo, maximo, *, tipo="float"):
    if isinstance(valor, bool):
        raise TypeError(f"{nombre} no puede ser booleano")
    if tipo == "int":
        if not isinstance(valor, int):
            raise TypeError(f"{nombre} debe ser int")
    else:
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{nombre} debe ser int o float")
    if valor < minimo or valor > maximo:
        raise ValueError(f"{nombre} fuera de rango [{minimo}, {maximo}]: {valor}")


def _validar_bool(valor, nombre):
    if not isinstance(valor, bool):
        raise TypeError(f"{nombre} debe ser bool")


class EstadoCluster:
    """Estado central del cluster de instrumentos. Sin dependencias de UI."""

    def __init__(self, reloj):
        self.reloj = reloj

        self._motor = False
        self._luces_altas = False
        self._emergencia = False
        self._falla_frenos = False
        self._direccional = "OFF"

        self._obj_velocidad = 0.0
        self._obj_rpm = 0
        self._obj_p_aceite = 0.0
        self._obj_temp_agua = 40.0
        self._obj_p_turbo = 0.0

        self.velocidad = 0.0
        self.rpm = 0
        self.p_aceite = 0.0
        self.temp_agua = 40.0
        self.p_turbo = 0.0

        ahora = self.reloj.ahora_ms()
        self._t_vel = ahora
        self._t_rpm = ahora
        self._t_aceite = ahora
        self._t_agua = ahora
        self._t_turbo = ahora

        self.color_rpm = "normal"
        self.color_temp = "normal"
        self.contorno_turbo = "normal"

        self.testigo_baja_presion_aceite = False
        self._inicio_bajo_ms = None
        self._inicio_alto_ms = None

        self._ultimo_tick_ms = ahora

    def set_velocidad(self, valor):
        _validar_numero(valor, "velocidad", 0, 360)
        self._obj_velocidad = float(valor)

    def set_rpm(self, valor):
        _validar_numero(valor, "rpm", 0, 9000, tipo="int")
        self._obj_rpm = valor

    def set_presion_aceite(self, valor):
        _validar_numero(valor, "presion_aceite", 0, 10)
        self._obj_p_aceite = float(valor)

    def set_temp_agua(self, valor):
        _validar_numero(valor, "temp_agua", 40, 130)
        self._obj_temp_agua = float(valor)

    def set_presion_turbo(self, valor):
        _validar_numero(valor, "presion_turbo", 0, 2)
        self._obj_p_turbo = float(valor)

    def set_motor(self, valor):
        _validar_bool(valor, "motor")
        self._motor = valor

    def set_luces_altas(self, valor):
        _validar_bool(valor, "luces_altas")
        self._luces_altas = valor

    def set_emergencia(self, valor):
        _validar_bool(valor, "emergencia")
        self._emergencia = valor

    def set_falla_frenos(self, valor):
        _validar_bool(valor, "falla_frenos")
        self._falla_frenos = valor

    def set_direccional(self, valor):
        if not isinstance(valor, str):
            raise TypeError("direccional debe ser str")
        if valor not in DIRECCIONALES_VALIDAS:
            raise ValueError(f"direccional desconocido: {valor!r}")
        self._direccional = valor

    @property
    def motor_activo(self):
        return self._motor

    @property
    def direccional(self):
        return self._direccional

    def tick(self):
        """Avanza un paso del estado segun el tiempo transcurrido en el reloj
        inyectado. Debe llamarse periodicamente (UI real: con after(); en
        pruebas: tras avanzar un RelojSimulado)."""
        ahora = self.reloj.ahora_ms()

        if not self._motor:
            self._aplicar_estado_apagado(ahora)
        else:
            self._actualizar_lecturas(ahora)
            self._actualizar_histeresis_aceite(ahora)

        self._ultimo_tick_ms = ahora
        return ahora

    def _aplicar_estado_apagado(self, ahora):
        self.velocidad = 0.0
        self.rpm = 0
        self.p_aceite = 0.0
        self.p_turbo = 0.0
        self.temp_agua = 40.0
        self._t_vel = self._t_rpm = self._t_aceite = self._t_turbo = self._t_agua = ahora

        self.color_rpm = "normal"
        self.color_temp = "normal"
        self.contorno_turbo = "normal"

        self.testigo_baja_presion_aceite = False
        self._inicio_bajo_ms = None
        self._inicio_alto_ms = None

    def _actualizar_lecturas(self, ahora):
        if ahora - self._t_vel >= CICLO_RAPIDO_MS:
            self.velocidad = self._obj_velocidad
            self._t_vel = ahora
        if ahora - self._t_rpm >= CICLO_RAPIDO_MS:
            self.rpm = self._obj_rpm
            self._t_rpm = ahora
        if ahora - self._t_aceite >= CICLO_RAPIDO_MS:
            self.p_aceite = self._obj_p_aceite
            self._t_aceite = ahora
        if ahora - self._t_turbo >= CICLO_RAPIDO_MS:
            self.p_turbo = self._obj_p_turbo
            self._t_turbo = ahora
        if ahora - self._t_agua >= CICLO_LENTO_MS:
            self.temp_agua = self._obj_temp_agua
            self._t_agua = ahora

        if self.rpm >= 8000:
            self.color_rpm = "rojo"
        elif self.rpm < 7800:
            self.color_rpm = "normal"

        if self.temp_agua > 110:
            self.color_temp = "rojo"
        elif self.temp_agua <= 105:
            self.color_temp = "normal"

        if self.p_turbo > 1.5:
            self.contorno_turbo = "ambar"
        elif self.p_turbo <= 1.4:
            self.contorno_turbo = "normal"

    def _actualizar_histeresis_aceite(self, ahora):
        if self.p_aceite < 1.0:
            if self._inicio_bajo_ms is None:
                self._inicio_bajo_ms = ahora
            self._inicio_alto_ms = None
            if ahora - self._inicio_bajo_ms >= RETARDO_HISTERESIS_ACEITE_MS:
                self.testigo_baja_presion_aceite = True
        elif self.p_aceite >= 1.2:
            if self._inicio_alto_ms is None:
                self._inicio_alto_ms = ahora
            self._inicio_bajo_ms = None
            if ahora - self._inicio_alto_ms >= RETARDO_HISTERESIS_ACEITE_MS:
                self.testigo_baja_presion_aceite = False
        else:
            self._inicio_bajo_ms = None
            self._inicio_alto_ms = None

    @property
    def color_aceite(self):
        """Elemento 2: ambar inmediato si p_aceite < 1 bar y el motor esta
        encendido (distinto del testigo 9, que tiene retardo e histeresis)."""
        if not self._motor:
            return "normal"
        return "ambar" if self.p_aceite < 1.0 else "normal"

    def _parpadeo(self, periodo_ms):
        ahora = self.reloj.ahora_ms()
        return int(ahora // periodo_ms) % 2 == 0

    @property
    def testigo_direccional_encendido(self):
        if not self._motor:
            return False
        if self._direccional == "OFF":
            return False
        return self._parpadeo(CICLO_LENTO_MS)

    @property
    def testigo_luces_altas_encendido(self):
        return self._motor and self._luces_altas

    @property
    def testigo_emergencia_encendido(self):
        if not self._motor:
            return False
        if not self._emergencia:
            return False
        return self._parpadeo(CICLO_LENTO_MS)

    @property
    def emergencia_tiene_precedencia(self):
        """True si la emergencia esta activa mientras hay un direccional
        puesto: el testigo 8 tiene precedencia visual sobre el testigo 6
        (R07). La UI usa esta bandera para decidir que dibujar primero."""
        return self._motor and self._emergencia and self._direccional != "OFF"

    @property
    def testigo_falla_frenos_encendido(self):
        """Testigo 10 (CRITICO, R08): parpadea cada 300 ms mientras
        falla_frenos=1, aunque el motor este apagado (R08 no lo condiciona)."""
        if not self._falla_frenos:
            return False
        return self._parpadeo(CICLO_FRENOS_MS)
