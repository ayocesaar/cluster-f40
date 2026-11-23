"""Ataque QA adicional (no forma parte de la suite): fuzzing y casos limite de borde.
Uso (desde la raiz del proyecto): python tools/qa/fuzzing.py"""
import math
import os
import pathlib
import random
import sys
import tempfile

sys.path.insert(0, os.getcwd())
from logic.estado import EstadoCluster  # noqa: E402
from logic.odometro import Odometro  # noqa: E402
from logic.reloj import RelojSimulado  # noqa: E402
from sistema import config as configuracion  # noqa: E402
from sistema import odometro_archivo  # noqa: E402
from sistema.bitacora import Bitacora  # noqa: E402
from sistema.lector import CLAVES, Lector, convertir, DatoInvalido  # noqa: E402

hallazgos = []
tmp = pathlib.Path(tempfile.mkdtemp())
bit = Bitacora(tmp / "logs")
RANGOS = dict(configuracion.RANGOS_ESPECIFICACION)

# 1. convertir: valores raros nunca deben pasar fuera de rango ni como nan/inf
raros = ["nan", "NaN", "inf", "-inf", "1e309", "-0", "+5", " 5 ", "5_0", "0x10", "1e2", "٣", "５", "",
         "1.0e-400", "360.0000000001", "9000.0", "True", "None", "0b1", "  ", "1,5"]
for clave in ("velocidad", "rpm", "presion_aceite", "temp_agua", "presion_turbo"):
    mn, mx = RANGOS[clave]
    for texto in raros:
        try:
            v = convertir(clave, texto, RANGOS)
        except DatoInvalido:
            continue
        if not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v) or not mn <= v <= mx:
            hallazgos.append(f"convertir {clave}={texto!r} acepto {v!r}")
        elif texto.strip() and not texto.strip().replace(".", "", 1).replace("-", "", 1).isascii():
            hallazgos.append(f"convertir {clave}={texto!r} acepto digitos no ASCII -> {v!r}")
for clave in ("motor", "luces_altas", "emergencia", "falla_frenos"):
    for texto in ("2", "-1", "true", "si", "1.0", "01", " 1", ""):
        try:
            v = convertir(clave, texto, RANGOS)
            if texto.strip() not in ("0", "1"):
                hallazgos.append(f"convertir {clave}={texto!r} acepto {v!r}")
        except DatoInvalido:
            pass

# 2. lector con basura aleatoria: nunca lanza excepcion
random.seed(7)
datos = tmp / "vehiculo.conf"
lector = Lector(datos, RANGOS, bit)
for i in range(3000):
    n = random.randint(0, 300)
    basura = bytes(random.randint(0, 255) for _ in range(n))
    if random.random() < 0.5:
        basura = "\n".join(f"{random.choice(list(CLAVES) + ['x', ''])}={random.choice(raros)}"
                           for _ in range(random.randint(0, 15))).encode()
    datos.write_bytes(basura)
    os.utime(datos, ns=(i * 1000, i * 1000))
    try:
        r = lector.leer()
        if r is not None:
            for clave, (mn, mx) in RANGOS.items():
                v = r[clave]
                if math.isnan(v) or not mn <= v <= mx:
                    hallazgos.append(f"lector entrego {clave}={v!r}")
    except Exception as e:  # noqa: BLE001
        hallazgos.append(f"lector lanzo {type(e).__name__}: {e}")
        break

# 3. modelo: entradas raras a los setters
reloj = RelojSimulado()
e = EstadoCluster(reloj)
for setter, valor in [("set_velocidad", float("nan")), ("set_velocidad", float("inf")), ("set_rpm", float("nan")),
                      ("set_temp_agua", float("nan")), ("set_presion_aceite", -0.0), ("set_rpm", 10 ** 30),
                      ("set_velocidad", True)]:
    try:
        getattr(e, setter)(valor)
        if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
            hallazgos.append(f"{setter}({valor}) aceptado")
        if valor is True:
            hallazgos.append(f"{setter}(True) aceptado")
    except (TypeError, ValueError):
        pass

# 4. odometro: archivo con formas raras
for texto in ("1e3", "62.", ".5", "６２", "٦٢", "62\x00", "999999.9999999", "62\n63", "-0", "0" * 6, " " * 10 + "62"):
    p = tmp / "odo.txt"
    p.write_text(texto, encoding="utf-8")
    try:
        km = odometro_archivo.leer_km(p)
        if not texto.strip().isascii():
            hallazgos.append(f"odometro acepto digitos no ASCII {texto!r} -> {km}")
        if not 0 <= km < 1_000_000:
            hallazgos.append(f"odometro acepto {texto!r} -> {km}")
    except odometro_archivo.OdometroInvalido:
        pass
# odometro: millones de ticks pequenos acumulan sin deriva relevante
o = Odometro(0)
for _ in range(1_000_000):
    o.avanzar(36, 100)        # 1 ms... 100 ms a 36 km/h = 0.001 km
if abs(o.km - 1000.0) > 1e-6:
    hallazgos.append(f"deriva del odometro: {o.km!r} en vez de 1000")
o2 = Odometro(999_999.0)
o2.avanzar(360, 3_600_000 * 3)   # 1080 km de golpe: varias vueltas en un solo paso
if not 0 <= o2.km < 1_000_000:
    hallazgos.append(f"odometro con salto grande fuera de rango: {o2.km}")

# 5. configuracion: rangos raros
for linea in ("velocidad = nan, 100", "velocidad = 0, inf", "velocidad = 100, 100", "velocidad = 0", "velocidad = ,",
              "rpm = 0, 9000, 1"):
    ini = tmp / "c.ini"
    ini.write_text("[rangos]\n" + linea + "\n", encoding="utf-8")
    cfg = configuracion.cargar(ini, raiz=tmp)
    for clave, (mn, mx) in cfg.rangos.items():
        if math.isnan(mn) or math.isnan(mx) or math.isinf(mx) or mn >= mx:
            hallazgos.append(f"config {linea!r} dejo {clave}=({mn}, {mx})")
bit.cerrar()
print("HALLAZGOS:", len(hallazgos))
for h in hallazgos:
    print(" -", h)
sys.exit(1 if hallazgos else 0)
