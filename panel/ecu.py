"""Unidad de control (ECU) simulada del panel: interbloqueos y protecciones del motor.

El cuadro de instrumentos NO decide nada de esto: solo muestra lo que recibe. Aqui, en el
proceso del panel (el lado del vehiculo), se decide si el motor puede arrancar o debe
detenerse, como lo haria la unidad de control del motor; la causa viaja al cuadro en la
clave opcional falla_motor y se dibuja en el testigo 15 (R12).

Reglas (diseno del equipo; las cifras son aproximadas y se justifican en
docs/realismo_y_liberacion.md; el F40 de 1987 no tenia todas estas protecciones):
- No arranca con fuga de aceite, con el deposito bajo 50 %, sin combustible o con una
  proteccion enclavada que todavia no se puede liberar.
- Corta el motor con el agua a 120 C (la aguja ya esta en rojo desde 110, R04), con el
  turbo sobre 1.5 bar durante 1 s (R05) o con menos de 0.5 bar de aceite durante 3 s.
- La proteccion queda enclavada hasta que la causa se repara (TALLER del panel) y la
  condicion fisica vuelve a la normalidad (por ejemplo, el agua bajo 100 C).
- Interbloqueo de puertas: con una puerta abierta el acelerador no tiene efecto."""

TEMP_CORTE_C = 120.0
TEMP_REARME_C = 100.0
TURBO_CORTE_BAR = 1.5
TURBO_CORTE_S = 1.0
ACEITE_MINIMO_BAR = 0.5
ACEITE_MINIMO_S = 3.0
NIVEL_ACEITE_ARRANQUE = 50.0
COMBUSTIBLE_MINIMO_L = 0.5

CAUSAS = ("ninguna", "sobretemperatura", "sobrepresion_turbo", "aceite", "combustible")
DESCRIPCION = {
    "sobretemperatura": f"sobretemperatura del agua (>= {TEMP_CORTE_C:g} C)",
    "sobrepresion_turbo": f"sobrepresion del turbo (> {TURBO_CORTE_BAR:g} bar durante {TURBO_CORTE_S:g} s)",
    "aceite": "falta de aceite (fuga, nivel bajo o presion insuficiente)",
    "combustible": "sin combustible",
}


class Ecu:
    def __init__(self):
        self.proteccion = "ninguna"
        self._t_turbo = 0.0
        self._t_aceite = 0.0
        self._aviso_traccion = False

    # ------------------------------------------------------------ arranque
    def motivo_sin_arranque(self, v):
        """Por que el motor no puede arrancar; None si puede. Un arranque bloqueado deja la
        causa enclavada para que el cuadro la muestre (testigo 15)."""
        if self.proteccion != "ninguna" and not self.rearme_posible(v):
            return f"proteccion enclavada por {DESCRIPCION[self.proteccion]}; repare en TALLER"
        self.proteccion = "ninguna"
        causa = None
        if v.fallas.fuga_aceite or v.nivel_aceite < NIVEL_ACEITE_ARRANQUE:
            causa, texto = "aceite", (f"fuga o nivel bajo de aceite ({v.nivel_aceite:.0f} %; minimo "
                                      f"{NIVEL_ACEITE_ARRANQUE:g} %): arrancar dañaria el motor")
        elif v.combustible_l <= COMBUSTIBLE_MINIMO_L:
            causa, texto = "combustible", "tanque vacio"
        elif v.temp_agua >= TEMP_CORTE_C:
            causa, texto = "sobretemperatura", f"agua a {v.temp_agua:.0f} C"
        if causa is None:
            return None
        self.proteccion = causa
        return texto

    def rearme_posible(self, v):
        """La proteccion se libera cuando la causa esta reparada y la condicion es normal."""
        causa = self.proteccion
        if causa == "sobretemperatura":
            return not v.fallas.radiador and v.temp_agua <= TEMP_REARME_C
        if causa == "sobrepresion_turbo":
            return not v.fallas.sobrepresion_turbo
        if causa == "aceite":
            return not v.fallas.fuga_aceite and v.nivel_aceite >= NIVEL_ACEITE_ARRANQUE
        if causa == "combustible":
            return v.combustible_l > COMBUSTIBLE_MINIMO_L
        return True

    # ------------------------------------------------------------ vigilancia
    def vigilar(self, v, dt):
        """Se llama en cada paso del panel. Devuelve los avisos nuevos para la consola."""
        avisos = []
        v.traccion_bloqueada = bool(v.puertas & 3)
        if v.traccion_bloqueada and v.acelerador > 0.2 and not self._aviso_traccion:
            avisos.append("Interbloqueo: puerta abierta, el acelerador no tiene efecto (R09)")
            self._aviso_traccion = True
        elif not v.traccion_bloqueada:
            self._aviso_traccion = False

        if not v.motor:
            self._t_turbo = self._t_aceite = 0.0
            if self.proteccion == "ninguna" and v.contacto and v.combustible_l <= 0.0:
                self.proteccion = "combustible"
                avisos.append("El motor se apago: sin combustible (R12)")
            elif self.proteccion != "ninguna" and self.rearme_posible(v):
                avisos.append(f"Proteccion liberada: {DESCRIPCION[self.proteccion]} resuelta; ya puede arrancar")
                self.proteccion = "ninguna"
            return avisos

        self._t_turbo = self._t_turbo + dt if v.presion_turbo > TURBO_CORTE_BAR else 0.0
        self._t_aceite = self._t_aceite + dt if v.presion_aceite < ACEITE_MINIMO_BAR else 0.0
        if v.temp_agua >= TEMP_CORTE_C:
            avisos.append(self._detener(v, "sobretemperatura"))
        elif self._t_turbo >= TURBO_CORTE_S:
            avisos.append(self._detener(v, "sobrepresion_turbo"))
        elif self._t_aceite >= ACEITE_MINIMO_S:
            avisos.append(self._detener(v, "aceite"))
        return avisos

    def _detener(self, v, causa):
        v.motor = False
        self.proteccion = causa
        self._t_turbo = self._t_aceite = 0.0
        return f"ECU: motor detenido por {DESCRIPCION[causa]} (R12). No arranca hasta reparar."
