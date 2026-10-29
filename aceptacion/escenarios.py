"""Pruebas de aceptacion del cluster dirigidas por datos.

Lee los escenarios de un archivo CSV, los ejecuta sobre la interfaz Tkinter
real (con reloj simulado para que ciclos y parpadeos sean deterministas) y
compara lo que queda dibujado en pantalla con lo esperado en cada paso.

Uso: python -m aceptacion.escenarios tests/datos/escenarios_aceptacion.csv
(requiere servidor grafico; en la VM: xvfb-run -a python -m aceptacion.escenarios ...)."""

import csv
import pathlib
import sys
import tkinter as tk
from dataclasses import dataclass

from logic.estado import EstadoCluster
from logic.reloj import RelojSimulado
from ui.presentacion import COLOR_AMBAR, COLOR_APAGADO, COLOR_AZUL, COLOR_NORMAL, COLOR_ROJO, COLOR_VERDE
from ui.tablero import Tablero

COLUMNAS = ("escenario", "paso", "accion", "valor", "avanzar_ms", "elemento", "esperado", "descripcion")

CONTROLES = {
    "velocidad": "set_velocidad",
    "rpm": "set_rpm",
    "presion_aceite": "set_presion_aceite",
    "temp_agua": "set_temp_agua",
    "presion_turbo": "set_presion_turbo",
    "motor": "set_motor",
    "luces_altas": "set_luces_altas",
    "emergencia": "set_emergencia",
    "falla_frenos": "set_falla_frenos",
    "direccional": "set_direccional",
}
DESLIZADORES = {"velocidad", "rpm", "presion_aceite", "temp_agua", "presion_turbo"}
INTERRUPTORES = {"motor", "luces_altas", "emergencia", "falla_frenos"}
DIRECCIONALES = ("OFF", "IZQ", "DER")

NOMBRES_COLOR = {COLOR_NORMAL: "normal", COLOR_ROJO: "rojo", COLOR_AMBAR: "ambar",
                 COLOR_VERDE: "verde", COLOR_AZUL: "azul", COLOR_APAGADO: "apagado"}
ESPERADOS_LECTURA = {"normal", "rojo", "ambar"}
ESPERADOS_TESTIGO = {"apagado", "verde", "azul", "ambar", "rojo"}


class ErrorEscenarios(Exception):
    """El archivo de escenarios no existe o tiene un formato invalido."""


@dataclass
class Paso:
    linea: int
    escenario: str
    numero: int
    accion: str
    valor: object
    avanzar_ms: float
    elemento: int
    esperado: str
    descripcion: str


@dataclass
class Resultado:
    paso: Paso
    observado: str
    aprobado: bool


def _valor(accion, texto, linea):
    if accion == "-":
        return None
    if accion in DESLIZADORES:
        try:
            return float(texto)
        except ValueError:
            raise ErrorEscenarios(f"linea {linea}: el valor {texto!r} de {accion} no es numerico") from None
    if accion in INTERRUPTORES:
        if texto not in ("0", "1"):
            raise ErrorEscenarios(f"linea {linea}: {accion} solo acepta 0 o 1, no {texto!r}")
        return texto == "1"
    if texto not in DIRECCIONALES:
        raise ErrorEscenarios(f"linea {linea}: direccional debe ser OFF, IZQ o DER, no {texto!r}")
    return texto


def _paso(fila, linea):
    fila = {c: (fila.get(c) or "").strip() for c in COLUMNAS}
    accion = fila["accion"]
    if accion != "-" and accion not in CONTROLES:
        raise ErrorEscenarios(f"linea {linea}: control desconocido {accion!r}")
    try:
        numero = int(fila["paso"])
        avanzar_ms = float(fila["avanzar_ms"])
        elemento = int(fila["elemento"])
    except ValueError:
        raise ErrorEscenarios(f"linea {linea}: paso, avanzar_ms y elemento deben ser numericos") from None
    if avanzar_ms < 0:
        raise ErrorEscenarios(f"linea {linea}: avanzar_ms negativo: {avanzar_ms:g}")
    if not 1 <= elemento <= 10:
        raise ErrorEscenarios(f"linea {linea}: elemento fuera de 1-10: {elemento}")
    esperado = fila["esperado"]
    validos = ESPERADOS_LECTURA if elemento <= 5 else ESPERADOS_TESTIGO
    if esperado not in validos and not (elemento <= 5 and esperado.startswith("valor=")):
        raise ErrorEscenarios(f"linea {linea}: esperado {esperado!r} no valido para el elemento {elemento}")
    return Paso(linea, fila["escenario"], numero, accion, _valor(accion, fila["valor"], linea),
                avanzar_ms, elemento, esperado, fila["descripcion"])


def cargar(ruta):
    """Lee el CSV y devuelve {escenario: [Paso, ...]} en el orden del archivo."""
    ruta = pathlib.Path(ruta)
    if not ruta.is_file():
        raise ErrorEscenarios(f"no existe el archivo de escenarios: {ruta}")
    escenarios = {}
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames is None:
            raise ErrorEscenarios(f"el archivo esta vacio: {ruta}")
        faltan = [c for c in COLUMNAS if c not in lector.fieldnames]
        if faltan:
            raise ErrorEscenarios(f"faltan columnas en {ruta}: {', '.join(faltan)}")
        for fila in lector:
            paso = _paso(fila, lector.line_num)
            escenarios.setdefault(paso.escenario, []).append(paso)
    if not escenarios:
        raise ErrorEscenarios(f"el archivo no tiene pasos: {ruta}")
    return escenarios


def observar(tablero, elemento, esperado):
    """Lee del canvas lo que esta dibujado para el elemento indicado."""
    it = tablero.items[elemento]
    if esperado.startswith("valor="):
        return "valor=" + tablero.canvas.itemcget(it["valor"], "text")
    color = tablero.canvas.itemcget(it["aguja" if elemento <= 5 else "forma"], "fill")
    return NOMBRES_COLOR.get(color, color)


def ejecutar(pasos):
    """Ejecuta un escenario sobre una ventana nueva, en estado seguro inicial."""
    raiz = tk.Tk()
    reloj = RelojSimulado()
    tablero = Tablero(raiz, EstadoCluster(reloj))
    resultados = []
    try:
        for paso in pasos:
            if paso.accion != "-":
                tablero.ajustar(CONTROLES[paso.accion], paso.valor)
            reloj.avanzar(paso.avanzar_ms)
            tablero.ciclo()
            observado = observar(tablero, paso.elemento, paso.esperado)
            resultados.append(Resultado(paso, observado, observado == paso.esperado))
    finally:
        tablero.detener()
        raiz.destroy()
    return resultados


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("uso: python -m aceptacion.escenarios ARCHIVO.csv", file=sys.stderr)
        return 2
    try:
        escenarios = cargar(argv[0])
    except ErrorEscenarios as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    aprobados = 0
    for nombre, pasos in escenarios.items():
        resultados = ejecutar(pasos)
        ok = all(r.aprobado for r in resultados)
        aprobados += ok
        print(f"{nombre}: {'APROBADO' if ok else 'FALLIDO'}")
        for r in resultados:
            p = r.paso
            valor = "-" if p.valor is None else p.valor
            print(f"  {'OK' if r.aprobado else 'XX'} paso {p.numero}: {p.descripcion} | "
                  f"{p.accion}={valor} +{p.avanzar_ms:g} ms | elemento {p.elemento}: "
                  f"esperado={p.esperado} observado={r.observado}")
    print(f"Resumen: {aprobados}/{len(escenarios)} escenarios aprobados")
    return 0 if aprobados == len(escenarios) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
