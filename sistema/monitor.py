"""Monitor de eventos: registra en la bitacora los cambios de estado del cluster.

Se ejecuta despues de cada tick, en el hilo de la interfaz. Solo registra
TRANSICIONES (un testigo que se enciende o se apaga), no cada parpadeo, para que
la bitacora refleje lo ocurrido sin crecer en cada ciclo. Los testigos de
seguridad (9 y 10) se revisan primero y se registran como WARN: es su
tratamiento prioritario. El odometro (elemento 11) se registra una vez por
kilometro completo, no en cada ciclo."""

COMPONENTE_SEGURIDAD = "monitor_seguridad"
COMPONENTE_MODELO = "modelo_vehiculo"
COMPONENTE_ODOMETRO = "odometro"


class MonitorEventos:
    def __init__(self, bitacora):
        self.bitacora = bitacora
        # Se parte del estado seguro inicial: asi un testigo que ya llega encendido
        # en la primera lectura tambien queda registrado.
        self._previo = {"t9": False, "t10": False, "rpm": "normal", "agua": "normal", "turbo": "normal",
                        "motor": False, "emergencia": False}
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
        # Prioridad 3: informacion en linea (odometro, elemento 11).
        km, anterior = estado.odometro.valor, self._km_previo
        self._km_previo = km
        if anterior is not None and km != anterior:
            detalle = f"km={estado.odometro.texto}"
            if km < anterior:
                detalle += f" vuelta_a_cero vueltas={estado.odometro.vueltas}"
            b.info(COMPONENTE_ODOMETRO, "odometro_actualizado", f"{detalle} resultado=aceptado")
