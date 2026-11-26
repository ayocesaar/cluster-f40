"""Demostracion del sonido del motor en un archivo WAV, con mediciones reales del audio.

Conduce el modelo fisico del panel (con su ECU) por un guion de 22 s: contacto con la alarma del
cinturon, arranque, ralenti, acelerones en neutral, primera a fondo hasta el limitador, segunda
con el turbo, descarga al soltar, frenada y apagado. Genera el audio con panel/sonido.py y
mide propiedades del sonido con el mismo codigo que usan las pruebas.

Uso: python tools/sonido_demo.py [CARPETA]   (por defecto docs/evidencias/sonido)"""

import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from panel.ecu import Ecu  # noqa: E402
from panel.fisica import Vehiculo  # noqa: E402
from panel.sonido import (BLOQUE, FS, EstadoSonoro, SalidaWav, SintetizadorMotor, envolvente, estado_de,  # noqa: E402
                          periodo_dominante_ms, potencia)

DT = BLOQUE / FS

# (desde_s, accion)
GUION = (
    (0.0, "contacto"), (1.8, "cinturon"), (2.3, "arrancar"), (4.5, "acelerar"), (5.1, "soltar"),
    (6.0, "acelerar"), (6.6, "soltar"), (7.6, "primera"), (11.6, "segunda"), (14.6, "soltar"),
    (16.6, "frenar"), (21.1, "apagar"), (22.4, "fin"),
)


def conducir(salida):
    v, ecu, sint = Vehiculo(), Ecu(), SintetizadorMotor()
    pendientes, t, bloques = list(GUION), 0.0, 0
    while pendientes:
        while pendientes and t >= pendientes[0][0]:
            accion = pendientes.pop(0)[1]
            if accion == "contacto":
                v.contacto = True
            elif accion == "cinturon":
                v.cinturon = True
            elif accion == "arrancar" and ecu.motivo_sin_arranque(v) is None:
                v.motor = True
            elif accion == "acelerar":
                v.acelerador = 1.0
            elif accion == "soltar":
                v.acelerador = 0.0
            elif accion in ("primera", "segunda"):
                v.cambiar("1" if accion == "primera" else "2")
                v.acelerador = 1.0
            elif accion == "frenar":
                v.acelerador, v.freno = 0.0, 0.6
            elif accion == "apagar":
                v.motor, v.contacto, v.freno = False, False, 0.0
            elif accion == "fin":
                return sint, bloques, t
        if v.freno and v.velocidad < 5 and v.marcha != "N":
            v.cambiar("N")
        ecu.vigilar(v, DT)
        v.avanzar(DT)
        salida.escribir(sint.generar(estado_de(v), BLOQUE).tobytes())
        bloques += 1
        t += DT
    return sint, bloques, t


def _estable(estado, segundos, arrancado=True):
    sint = SintetizadorMotor()
    sint.motor_previo = arrancado
    datos = []
    for _ in range(int(segundos * FS / BLOQUE)):
        datos += sint.generar(estado, BLOQUE)
    return datos, sint


def mediciones():
    lineas = []
    ralenti, _ = _estable(EstadoSonoro(motor=True, rpm=1000, contacto=True), 1.5)
    periodo = periodo_dominante_ms(ralenti[FS // 2:])
    lineas.append(f"Ralenti 1000 rpm: una explosion cada {periodo:.1f} ms (esperado 60000 / 1000 / 4 = 15.0 ms: "
                  f"4 explosiones por vuelta, V8 de cuatro tiempos)")
    alto, _ = _estable(EstadoSonoro(motor=True, rpm=6000, acel=1.0, contacto=True), 1.0)
    relacion = potencia(alto[FS // 4:], 400) / potencia(alto[FS // 4:], 425)
    lineas.append(f"6000 rpm a fondo: potencia en 400 Hz (frecuencia de encendido) {relacion:.1f} veces la de 425 Hz")
    for rpm in (7000, 8200):
        datos, sint = _estable(EstadoSonoro(motor=True, rpm=rpm, acel=1.0, contacto=True), 1.0)
        env = sorted(envolvente(datos[FS // 4:], FS // 100))
        lineas.append(f"{rpm} rpm a fondo: envolvente p10/p90 = {env[len(env) // 10] / env[9 * len(env) // 10]:.3f}, "
                      f"explosiones cortadas por el limitador = {sint.cortes}")
    sin_turbo, _ = _estable(EstadoSonoro(motor=True, rpm=5000, acel=1.0, contacto=True), 1.0)
    con_turbo, _ = _estable(EstadoSonoro(motor=True, rpm=5000, acel=1.0, turbo=1.1, contacto=True), 1.0)
    frecuencia = 2200 + 2600 * 1.1 / 1.2
    lineas.append(f"Silbido del turbo ({frecuencia:.0f} Hz) con 1.1 bar: {potencia(con_turbo[FS // 4:], frecuencia) / potencia(sin_turbo[FS // 4:], frecuencia):.0f} "
                  "veces la potencia sin presion")
    campana, _ = _estable(EstadoSonoro(contacto=True, cinturon=False), 9.0, arrancado=False)
    ventanas = [potencia(campana[i:i + FS // 4], 1046) for i in range(0, len(campana) - FS // 4, FS // 4)]
    sonando = [i * 0.25 for i, p in enumerate(ventanas) if p > max(ventanas) * 0.01]
    lineas.append(f"Alarma del cinturon: suena de {sonando[0]:.2f} s a {sonando[-1] + 0.25:.2f} s "
                  "(FMVSS 208 S7.3 pide de 4 a 8 s)")
    sint = SintetizadorMotor()
    for _ in range(int(0.5 * FS / BLOQUE)):
        sint.generar(EstadoSonoro(motor=True, rpm=1000, contacto=True), BLOQUE)
    lineas.append(f"Motor de arranque: {sint.explosiones} explosiones en los primeros 0.5 s (arranca a los 0.55 s)")
    inicio = time.perf_counter()
    _estable(EstadoSonoro(motor=True, rpm=6000, acel=1.0, turbo=1.0, contacto=True), 2.0)
    costo = (time.perf_counter() - inicio) / 2.0
    lineas.append(f"Costo de sintesis: {costo * 1000:.0f} ms de CPU por segundo de audio ({costo * 100:.0f} % de un nucleo)")
    return lineas


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    carpeta = pathlib.Path(argv[0]) if argv else RAIZ / "docs" / "evidencias" / "sonido"
    wav = carpeta / "motor_demo.wav"
    salida = SalidaWav(wav)
    sint, bloques, segundos = conducir(salida)
    salida.cerrar()
    lineas = ["Sonido del motor sintetizado por codigo (panel/sonido.py): demostracion y mediciones reales",
              f"Archivo: {wav.name}, {segundos:.1f} s, {FS} Hz, 16 bits, mono, {salida.bytes} bytes de audio",
              f"Guion: {', '.join(f'{t:g} s {a}' for t, a in GUION)}",
              f"En el guion: {sint.explosiones} explosiones, {sint.cortes} cortadas por el limitador, "
              f"{sint.petardeos} petardeos al soltar", "", "Mediciones del audio generado:"]
    lineas += [f"  {linea}" for linea in mediciones()]
    lineas += ["", "Sonido aproximado: no es una grabacion del F40 ni se calibro contra uno; no usa audio de terceros."]
    (carpeta / "reporte.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
