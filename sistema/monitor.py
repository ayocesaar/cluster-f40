"""Monitor de eventos: registra en la bitacora los cambios de estado del cluster.

Se ejecuta despues de cada tick, en el hilo de la interfaz. Solo registra
TRANSICIONES (un testigo que se enciende o se apaga), no cada parpadeo, para que
la bitacora refleje lo ocurrido sin crecer en cada ciclo. Los testigos de
seguridad (9 y 10) se revisan primero y se registran como WARN: es su
tratamiento prioritario. El odometro (elemento 11) se registra una vez por
kilometro completo, no en cada ciclo. Los elementos adicionales 12-15 (Etapa 18) solo
registran eventos si el productor envia sus claves; la proteccion del motor, la puerta
abierta en movimiento y el cinturon sin abrochar en movimiento son WARN prioritarios."""

COMPONENTE_SEGURIDAD = "monitor_seguridad"
COMPONENTE_MODELO = "modelo_vehiculo"
COMPONENTE_ODOMETRO = "odometro"


class MonitorEventos:
    def __init__(self, bitacora):
        self.bitacora = bitacora
        # Se parte del estado seguro inicial: asi un testigo que ya llega encendido
        # en la primera lectura tambien queda registrado.
        self._previo = {"t9": False, "t10": False, "rpm": "normal", "agua": "normal", "turbo": "normal",
                        "motor": False, "emergencia": False,
                        # Etapa 18: elementos adicionales; None = el productor no envia la clave.
                        "proteccion": None, "puerta_mov": False, "cinturon_mov": False, "contacto": None,
                        "pruebas": 0, "puerta": None, "cinturon": None, "reserva": False, "carga": False,
                        "aceite_temp": "normal"}
        self._km_previo = None  # el valor inicial ya lo registra odometro_cargado

    def _cambio(self, clave, valor):
        anterior = self._previo[clave]
        self._previo[clave] = valor
        return anterior != valor

    def revisar(self, estado):
        b = self.bitacora
        # Prioridad 1: testigos de seguridad.
        if self._cambio("t9", estado.testigo_baja_presion_aceite):
            if estado.testigo_baja_presion_aceite:
                b.warn(COMPONENTE_SEGURIDAD, "testigo_9_encendido", f"presion_aceite={estado.p_aceite:g} bar durante >= 1 s (R02)")
            else:
                b.info(COMPONENTE_SEGURIDAD, "testigo_9_apagado", f"presion_aceite={estado.p_aceite:g} bar")
        if self._cambio("t10", estado.falla_frenos_activa):
            if estado.falla_frenos_activa:
                b.warn(COMPONENTE_SEGURIDAD, "testigo_10_encendido", "falla_frenos=1 parpadeo cada 300 ms (R08)")
            else:
                b.info(COMPONENTE_SEGURIDAD, "testigo_10_apagado", "falla_frenos=0")
        self._revisar_seguridad_adicional(estado)
        # Prioridad 2: advertencias de las lecturas y estado general.
        if self._cambio("rpm", estado.color_rpm):
            (b.warn if estado.color_rpm == "rojo" else b.info)(
                COMPONENTE_MODELO, f"tacometro_{estado.color_rpm}", f"rpm={estado.rpm} (R03)")
        if self._cambio("agua", estado.color_temp):
            (b.warn if estado.color_temp == "rojo" else b.info)(
                COMPONENTE_MODELO, f"temperatura_{estado.color_temp}", f"temp_agua={estado.temp_agua:g} C (R04)")
        if self._cambio("turbo", estado.contorno_turbo):
            (b.warn if estado.contorno_turbo == "ambar" else b.info)(
                COMPONENTE_MODELO, f"turbo_{estado.contorno_turbo}", f"presion_turbo={estado.p_turbo:g} bar (R05)")
        if self._cambio("motor", estado.motor_activo):
            b.info(COMPONENTE_MODELO, "motor_encendido" if estado.motor_activo else "motor_apagado", "(R01)")
        if self._cambio("emergencia", estado.emergencia_activa):
            b.info(COMPONENTE_MODELO, "emergencia_activada" if estado.emergencia_activa else "emergencia_desactivada", "(R07)")
        self._revisar_informacion_adicional(estado)
        # Prioridad 3: informacion en linea (odometro, elemento 11).
        km, anterior = estado.odometro.valor, self._km_previo
        self._km_previo = km
        if anterior is not None and km != anterior:
            detalle = f"km={estado.odometro.texto}"
            if km < anterior:
                detalle += f" vuelta_a_cero vueltas={estado.odometro.vueltas}"
            b.info(COMPONENTE_ODOMETRO, "odometro_actualizado", f"{detalle} resultado=aceptado")

    # ------------------------------------------------ Etapa 18: elementos adicionales 12-15
    def _revisar_seguridad_adicional(self, estado):
        """Prioridad 1 (despues de 9 y 10): proteccion del motor, puerta y cinturon en movimiento."""
        b = self.bitacora
        causa = estado.falla_motor
        anterior = self._previo["proteccion"]
        if self._cambio("proteccion", causa):
            if causa not in (None, "ninguna"):
                b.warn(COMPONENTE_SEGURIDAD, "motor_detenido_por_proteccion", f"causa={causa} testigo 15 (R12)")
            elif anterior not in (None, "ninguna"):
                b.info(COMPONENTE_SEGURIDAD, "proteccion_motor_liberada", f"causa_anterior={anterior} (R12)")
        if self._cambio("puerta_mov", estado.puerta_abierta_en_movimiento) and estado.puerta_abierta_en_movimiento:
            b.warn(COMPONENTE_SEGURIDAD, "puerta_abierta_en_movimiento",
                   f"puertas={estado.puertas} velocidad={estado.velocidad:g} km/h (R09)")
        if self._cambio("carga", estado.falla_de_carga):
            if estado.falla_de_carga:
                b.warn(COMPONENTE_SEGURIDAD, "falla_de_carga", f"voltaje={estado.voltaje:g} V con el motor en marcha (R13)")
            else:
                b.info(COMPONENTE_SEGURIDAD, "carga_normal", "(R13)")
        en_movimiento = estado.cinturon_desabrochado_en_movimiento
        if self._cambio("cinturon_mov", en_movimiento) and en_movimiento:
            b.warn(COMPONENTE_SEGURIDAD, "cinturon_desabrochado_en_movimiento",
                   f"velocidad={estado.velocidad:g} km/h (R10)")

    def _revisar_informacion_adicional(self, estado):
        """Prioridad 2: llave, prueba de testigos, puertas, cinturon y reserva de combustible."""
        b = self.bitacora
        if self._cambio("contacto", estado.contacto) and estado.contacto is not None:
            b.info(COMPONENTE_MODELO, "contacto_puesto" if estado.contacto else "contacto_quitado", "(R01)")
        if self._cambio("pruebas", estado.pruebas_de_testigos):
            b.info(COMPONENTE_MODELO, "prueba_de_testigos", "todos los testigos encendidos 2 s al dar contacto")
        anterior = self._previo["puerta"]
        if self._cambio("puerta", estado.puerta_abierta) and estado.puerta_abierta is not None:
            if estado.puerta_abierta:
                b.info(COMPONENTE_MODELO, "puerta_abierta", f"puertas={estado.puertas} (R09)")
            elif anterior:
                b.info(COMPONENTE_MODELO, "puertas_cerradas", "puertas=0 (R09)")
        desabrochado = estado.cinturon_desabrochado if estado.encendido else None
        anterior = self._previo["cinturon"]
        if self._cambio("cinturon", desabrochado) and desabrochado is not None:
            if desabrochado:
                b.info(COMPONENTE_MODELO, "cinturon_desabrochado", "con contacto (R10)")
            elif anterior:
                b.info(COMPONENTE_MODELO, "cinturon_abrochado", "(R10)")
        if self._cambio("aceite_temp", estado.color_aceite_temp):
            (b.warn if estado.color_aceite_temp == "rojo" else b.info)(
                COMPONENTE_MODELO, f"temperatura_aceite_{estado.color_aceite_temp}",
                f"temp_aceite={estado.temp_aceite:g} C (R14)")
        if self._cambio("reserva", estado.reserva_combustible):
            nivel = estado.combustible if estado.combustible is not None else 0.0
            if estado.reserva_combustible:
                b.warn(COMPONENTE_MODELO, "combustible_reserva", f"nivel={nivel:g} % (R11)")
            elif estado.combustible is not None:
                b.info(COMPONENTE_MODELO, "combustible_sobre_reserva", f"nivel={nivel:g} % (R11)")
