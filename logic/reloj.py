"""Reloj inyectable para el clúster de instrumentos del Ferrari F40.

Provee una interfaz común (ahora_ms) para que logic/estado.py pueda leer el
tiempo transcurrido sin importar si la fuente es el reloj real del sistema
operativo o un reloj simulado controlado manualmente desde las pruebas.
"""

import time


class RelojReal:
    """Reloj basado en time.monotonic(). Usado por la aplicacion en ejecucion normal."""

    def __init__(self):
        self._inicio = time.monotonic()

    def ahora_ms(self):
        """Milisegundos transcurridos desde que se creo este reloj."""
        return (time.monotonic() - self._inicio) * 1000.0


class RelojSimulado:
    """Reloj controlado manualmente. Usado en las pruebas para simular el paso
    del tiempo sin depender de sleeps reales (histeresis, parpadeos, etc.)."""

    def __init__(self):
        self._ms_acumulados = 0.0

    def avanzar(self, ms):
        """Avanza el reloj simulado `ms` milisegundos."""
        if not isinstance(ms, (int, float)) or isinstance(ms, bool):
            raise TypeError("ms debe ser int o float")
        if ms < 0:
            raise ValueError("ms no puede ser negativo")
        self._ms_acumulados += ms
        return self._ms_acumulados

    def ahora_ms(self):
        """Milisegundos simulados transcurridos desde la creacion del reloj."""
        return self._ms_acumulados
