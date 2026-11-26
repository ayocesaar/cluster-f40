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
  Elemento 11 - Odometro: integra la velocidad en el tiempo (logic/odometro.py).

Elementos adicionales de seguridad y consumo (Etapa 18, reglas agregadas por el equipo;
llegan en claves opcionales y quedan "sin dato" si el productor no las envia):
  Contacto - separa Encendido (elementos 1 y 4, odometro y testigos) de Motor activo
        (2, 3 y 5), como distingue la especificacion (decision D3). Al dar contacto se
        hace la prueba de testigos de 2 s (R13-H 5.2.21.4 la exige para los de frenos).
  R09 - Elemento 12, puerta abierta: ambar fijo detenido; rojo parpadeante en movimiento.
  R10 - Elemento 13, cinturon: rojo con contacto y cinturon sin abrochar; parpadea sobre 10 km/h.
  R11 - Elemento 14, combustible: porcentaje del tanque, ciclo de 500 ms y reserva con
        histeresis (enciende con <= 12 %, se apaga con >= 15 %).
  R12 - Elemento 15, proteccion del motor: rojo mientras la ECU informe una causa.
  R13 - Elemento 16, carga de bateria (Etapa 20): rojo con contacto y motor apagado (normal, como
        en un auto real) y con el motor en marcha si el voltaje baja de 13.0 V: el alternador no
        carga (advertencia critica).

Nota de diseno (resuelve una ambiguedad de la guia original, documentada
tambien en el informe): al apagar el motor (R01, encendido=0) se apaga
tambien el testigo 9 (baja presion de aceite) y el amber inmediato del
elemento 2, reiniciando los temporizadores de histeresis. De lo contrario,
ambos indicadores se encenderian falsamente al apagar el motor, porque R01
fuerza p_aceite a 0.
"""

from logic.odometro import Odometro

CICLO_RAPIDO_MS = 100.0   # velocidad, p_aceite, rpm, p_turbo
CICLO_LENTO_MS = 500.0    # temp_agua, direccionales, emergencia
CICLO_FRENOS_MS = 300.0   # falla de frenos
RETARDO_HISTERESIS_ACEITE_MS = 1000.0
PRUEBA_TESTIGOS_MS = 2000.0      # todos los testigos encienden al dar contacto
VELOCIDAD_EN_MOVIMIENTO = 3.0    # km/h: desde aqui la puerta abierta es una advertencia critica (R09)
VELOCIDAD_CINTURON = 10.0        # km/h: desde aqui el testigo del cinturon parpadea (R10)
RESERVA_ENCIENDE, RESERVA_APAGA = 12.0, 15.0   # % del tanque (R11)
VOLTAJE_DE_CARGA = 13.0          # V: con el motor en marcha y menos que esto, el alternador no carga (R13)

DIRECCIONALES_VALIDAS = ("OFF", "IZQ", "DER")
CAUSAS_MOTOR = ("ninguna", "sobretemperatura", "sobrepresion_turbo", "aceite", "combustible", "electrica")


def _validar_numero(valor, nombre, minimo, maximo, *, tipo="float"):
    if isinstance(valor, bool):
        raise TypeError(f"{nombre} no puede ser booleano")
    if tipo == "int":
        if not isinstance(valor, int):
            raise TypeError(f"{nombre} debe ser int")
    else:
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{nombre} debe ser int o float")
    # "not minimo <= valor <= maximo" tambien rechaza NaN: con "valor < minimo or valor > maximo"
    # un NaN pasaba porque toda comparacion con NaN es falsa (DEF-13).
    if not minimo <= valor <= maximo:
        raise ValueError(f"{nombre} fuera de rango [{minimo}, {maximo}]: {valor}")


def _validar_bool(valor, nombre):
    if not isinstance(valor, bool):
        raise TypeError(f"{nombre} debe ser bool")


class EstadoCluster:
    """Estado central del cluster de instrumentos. Sin dependencias de UI."""

    def __init__(self, reloj, odometro_km=0.0):
        self.reloj = reloj
        self.odometro = Odometro(odometro_km)

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

        # Claves opcionales (Etapa 18). None = sin dato: el productor no las envia.
        self._contacto = None
        self._puertas = None
        self._cinturon = None
        self._obj_combustible = None
        self._falla_motor = None
        self._voltaje = None
        self.combustible = None
        self.reserva_combustible = False
        self._t_combustible = ahora
        self._prueba_hasta_ms = None
        self.pruebas_de_testigos = 0     # cuantas veces se hizo la prueba (la registra el monitor)

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

    # ------------------------------------------------ claves opcionales (None = sin dato)
    def set_contacto(self, valor):
        if valor is not None:
            _validar_bool(valor, "contacto")
        if valor is True and self._contacto is not True:
            # Llave a contacto: prueba de testigos (solo de presentacion; no cambia ninguna regla).
            self._prueba_hasta_ms = self.reloj.ahora_ms() + PRUEBA_TESTIGOS_MS
            self.pruebas_de_testigos += 1
        self._contacto = valor

    def set_puertas(self, valor):
        if valor is not None:
            _validar_numero(valor, "puertas", 0, 3, tipo="int")
        self._puertas = valor

    def set_cinturon(self, valor):
        if valor is not None:
            _validar_bool(valor, "cinturon")
        self._cinturon = valor

    def set_combustible(self, valor):
        if valor is not None:
            _validar_numero(valor, "combustible", 0, 100)
            valor = float(valor)
        self._obj_combustible = valor
        if valor is None:
            self.combustible = None
            self.reserva_combustible = False

    def set_falla_motor(self, valor):
        if valor is not None:
            if not isinstance(valor, str):
                raise TypeError("falla_motor debe ser str")
            if valor not in CAUSAS_MOTOR:
                raise ValueError(f"falla_motor desconocida: {valor!r}")
        self._falla_motor = valor

    def set_voltaje(self, valor):
        if valor is not None:
            _validar_numero(valor, "voltaje", 0, 20)
            valor = float(valor)
        self._voltaje = valor

    @property
    def voltaje(self):
        """Voltaje del sistema electrico mostrado (None sin dato o con el cuadro sin energia)."""
        return self._voltaje if self.encendido else None

    @property
    def testigo_carga_encendido(self):
        """Elemento 16 (R13): con contacto y motor apagado se enciende (el alternador no gira); con
        el motor en marcha solo si el voltaje no llega a 13.0 V."""
        if self.voltaje is None:
            return False
        return not self._motor or self.voltaje < VOLTAJE_DE_CARGA

    @property
    def falla_de_carga(self):
        """El motor ya gira (800 rpm o mas) y el alternador no carga: advertencia critica. Mientras
        el motor arranca el testigo se ve encendido, pero eso es normal y no se registra."""
        return bool(self._motor and self.rpm >= 800 and self.voltaje is not None and self.voltaje < VOLTAJE_DE_CARGA)

    @property
    def contacto(self):
        """Contacto tal como llego; None si el productor no lo envia."""
        return self._contacto

    @property
    def encendido(self):
        """Cuadro energizado: llave en contacto o, sin dato de contacto, el motor (R01, como antes)."""
        if self._contacto is None:
            return self._motor
        return self._contacto or self._motor

    @property
    def prueba_testigos_activa(self):
        return (self._prueba_hasta_ms is not None and self.encendido
                and self.reloj.ahora_ms() < self._prueba_hasta_ms)

    @property
    def puertas(self):
        return self._puertas

    @property
    def puerta_abierta(self):
        """True o False con dato; None sin dato."""
        return None if self._puertas is None else self._puertas != 0

    @property
    def en_movimiento(self):
        return self.velocidad >= VELOCIDAD_EN_MOVIMIENTO

    @property
    def puerta_abierta_en_movimiento(self):
        return bool(self.encendido and self.puerta_abierta and self.en_movimiento)

    @property
    def testigo_puerta_encendido(self):
        """Elemento 12 (R09): fijo con el auto detenido, parpadeo de 500 ms en movimiento."""
        if not self.encendido or not self.puerta_abierta:
            return False
        return self._parpadeo(CICLO_LENTO_MS) if self.en_movimiento else True

    @property
    def cinturon_desabrochado(self):
        """True o False con dato; None sin dato."""
        return None if self._cinturon is None else not self._cinturon

    @property
    def cinturon_desabrochado_en_movimiento(self):
        return bool(self.encendido and self.cinturon_desabrochado and self.velocidad > VELOCIDAD_CINTURON)

    @property
    def testigo_cinturon_encendido(self):
        """Elemento 13 (R10): fijo con contacto y cinturon sin abrochar; parpadea sobre 10 km/h."""
        if not self.encendido or not self.cinturon_desabrochado:
            return False
        return self._parpadeo(CICLO_LENTO_MS) if self.velocidad > VELOCIDAD_CINTURON else True

    @property
    def falla_motor(self):
        return self._falla_motor

    @property
    def proteccion_motor_activa(self):
        """Elemento 15 (R12): la ECU informa que detuvo o no deja arrancar el motor."""
        return bool(self.encendido and self._falla_motor not in (None, "ninguna"))

    @property
    def motor_activo(self):
        return self._motor

    @property
    def direccional(self):
        return self._direccional

    @property
    def falla_frenos_activa(self):
        """Entrada falla_frenos tal como llego (el testigo 10 parpadea a partir de ella)."""
        return self._falla_frenos

    @property
    def emergencia_activa(self):
        return self._emergencia

    def tick(self):
        """Avanza un paso del estado segun el tiempo transcurrido en el reloj
        inyectado. Debe llamarse periodicamente (UI real: con after(); en
        pruebas: tras avanzar un RelojSimulado)."""
        ahora = self.reloj.ahora_ms()

        if not self.encendido:
            self._aplicar_estado_apagado(ahora)
        else:
            velocidad_previa = self.velocidad
            self._actualizar_lecturas(ahora)
            if self._motor:
                self._actualizar_histeresis_aceite(ahora)
            else:
                # Contacto sin motor (D3): 1 y 4 siguen midiendo; 2, 3 y 5 en reposo porque el
                # motor no gira. El testigo 9 queda apagado: sin giro no hay falla de lubricacion.
                self._aplicar_motor_detenido()
            self._actualizar_combustible(ahora)
            # Elemento 11: la distancia avanza con la velocidad mostrada durante el tiempo transcurrido.
            # Si la velocidad cambio en este tick, la nueva solo cuenta para el ultimo ciclo de lectura;
            # el resto del intervalo (por ejemplo, un refresco retrasado) se integra con la anterior (DEF-07).
            transcurrido = ahora - self._ultimo_tick_ms
            tramo_nuevo = transcurrido if self.velocidad == velocidad_previa else min(transcurrido, CICLO_RAPIDO_MS)
            self.odometro.avanzar(velocidad_previa, transcurrido - tramo_nuevo)
            self.odometro.avanzar(self.velocidad, tramo_nuevo)

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

        self.combustible = None          # el medidor sin energia no indica
        self.reserva_combustible = False

    def _aplicar_motor_detenido(self):
        self.rpm = 0
        self.p_aceite = 0.0
        self.p_turbo = 0.0
        self.color_rpm = "normal"
        self.contorno_turbo = "normal"
        self.testigo_baja_presion_aceite = False
        self._inicio_bajo_ms = None
        self._inicio_alto_ms = None

    def _actualizar_combustible(self, ahora):
        """R11: el nivel se muestra con el ciclo lento (cambia despacio) y la reserva tiene histeresis."""
        if self._obj_combustible is None:
            return
        if self.combustible is None or ahora - self._t_combustible >= CICLO_LENTO_MS:
            self.combustible = self._obj_combustible
            self._t_combustible = ahora
        if self.combustible <= RESERVA_ENCIENDE:
            self.reserva_combustible = True
        elif self.combustible >= RESERVA_APAGA:
            self.reserva_combustible = False

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

    # Los testigos informativos dependen de que el cuadro este energizado: sin dato de
    # contacto es el motor, como en la decision D2; con contacto basta la llave.
    @property
    def testigo_direccional_encendido(self):
        if not self.encendido:
            return False
        if self._direccional == "OFF":
            return False
        return self._parpadeo(CICLO_LENTO_MS)

    @property
    def testigo_luces_altas_encendido(self):
        return self.encendido and self._luces_altas

    @property
    def testigo_emergencia_encendido(self):
        if not self.encendido:
            return False
        if not self._emergencia:
            return False
        return self._parpadeo(CICLO_LENTO_MS)

    @property
    def emergencia_tiene_precedencia(self):
        """True si la emergencia esta activa mientras hay un direccional
        puesto: el testigo 8 tiene precedencia visual sobre el testigo 6
        (R07). La UI usa esta bandera para decidir que dibujar primero."""
        return self.encendido and self._emergencia and self._direccional != "OFF"

    @property
    def testigo_falla_frenos_encendido(self):
        """Testigo 10 (CRITICO, R08): parpadea cada 300 ms mientras
        falla_frenos=1, aunque el motor este apagado (R08 no lo condiciona)."""
        if not self._falla_frenos:
            return False
        return self._parpadeo(CICLO_FRENOS_MS)
