"""Odometro: distancia total recorrida (elemento 11, informacion en linea).

Integra la velocidad en el tiempo: distancia += velocidad (km/h) x tiempo (h).
Se muestra como un entero de 6 digitos (000000 a 999999), como el contador del
F40; al pasar de 999 999 vuelve a 000 000 y nunca disminuye. La fraccion de
kilometro se conserva en un decimal para no perder distancia entre ciclos."""

MAXIMO_KM = 1_000_000
# Sumar muchas fracciones decimales deja errores de redondeo del orden de 1e-12;
# la tolerancia evita que 0.9999999999 km se muestre como 0 cuando son 1 km.
TOLERANCIA_KM = 1e-6
MS_POR_HORA = 3_600_000


class Odometro:
    def __init__(self, km_inicial=0.0):
        if isinstance(km_inicial, bool) or not isinstance(km_inicial, (int, float)):
            raise TypeError("km_inicial debe ser int o float")
        if not 0 <= km_inicial < MAXIMO_KM:
            raise ValueError(f"km_inicial fuera de rango [0, {MAXIMO_KM}): {km_inicial}")
        self._km = float(km_inicial)
        self.vueltas = 0

    def avanzar(self, velocidad_kmh, dt_ms):
        """Suma la distancia recorrida en dt_ms a velocidad_kmh. Valores no positivos no
        suman nada: el contador nunca retrocede."""
        if velocidad_kmh <= 0 or dt_ms <= 0:
            return
        self._km += velocidad_kmh * dt_ms / MS_POR_HORA
        if self._km + TOLERANCIA_KM >= MAXIMO_KM:
            self._km = max(0.0, self._km - MAXIMO_KM)
            self.vueltas += 1

    @property
    def km(self):
        """Distancia acumulada con su fraccion (es lo que se guarda en el archivo)."""
        return self._km

    @property
    def valor(self):
        """Kilometros completos que muestra el tablero."""
        return min(int(self._km + TOLERANCIA_KM), MAXIMO_KM - 1)

    @property
    def texto(self):
        return f"{self.valor:06d}"
