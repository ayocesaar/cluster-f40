"""Lee la caja negra del cluster (datos/caja_negra.bin) sin modificarla, y genera su evidencia.

Uso:
    python3 tools/caja_negra.py                      # cabecera y los ultimos 5 registros
    python3 tools/caja_negra.py --ultimos 100 --csv salida.csv
    python3 tools/caja_negra.py --hex 1              # el ultimo registro: bytes en hexadecimal y cada campo
    python3 tools/caja_negra.py --demo docs/evidencias/caja_negra   # 70 s simulados con sobrecalentamiento

La lectura es de solo lectura (O_RDONLY) y usa acceso directo: el registro numero k esta en el
byte 64 + (k mod capacidad) x 32, asi que no recorre el archivo para llegar a los ultimos."""

import argparse
import os
import time
import pathlib
import struct
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sistema import config as configuracion  # noqa: E402
from sistema.caja_negra import (CABECERA, CAMPOS, FIRMA, REGISTRO, CajaNegra, Registrador, _crc,  # noqa: E402
                                desempaquetar, exportar_csv)

NOMBRES = ("fecha (Q, ms)", "secuencia (I)", "velocidad (H, 0.1 km/h)", "rpm (H)", "aceite (H, 0.01 bar)",
           "agua (h, 0.1 C, con signo)", "turbo (H, 0.01 bar)", "combustible (B, %, 255 = sin dato)",
           "voltaje (B, 0.1 V, 255 = sin dato)", "testigos (H, bits)", "causa (B, 255 = sin dato)",
           "estado (B, bits)", "crc (H, CRC-16)")


def leer_cabecera(ruta):
    with open(ruta, "rb") as archivo:
        datos = archivo.read(CABECERA.size)
    firma, version, tamano, capacidad, total, creada, crc = CABECERA.unpack(datos)
    return {"firma": firma, "version": version, "tamano_registro": tamano, "capacidad": capacidad, "total": total,
            "creada_ms": creada, "crc_ok": _crc(datos[:-2]) == crc and firma == FIRMA, "bytes": datos}


def leer_crudo(ruta, cabecera, desde_el_final):
    """Bytes del registro n-esimo contando desde el final (1 = el ultimo), por acceso directo."""
    secuencia = cabecera["total"] - desde_el_final
    desplazamiento = CABECERA.size + (secuencia % cabecera["capacidad"]) * REGISTRO.size
    fd = os.open(ruta, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        os.lseek(fd, desplazamiento, os.SEEK_SET)
        return desplazamiento, os.read(fd, REGISTRO.size)
    finally:
        os.close(fd)


def ultimos(ruta, cabecera, n):
    registros, danados = [], 0
    for k in range(min(n, cabecera["total"], cabecera["capacidad"]), 0, -1):
        _, crudo = leer_crudo(ruta, cabecera, k)
        try:
            registros.append(desempaquetar(crudo))
        except ValueError:
            danados += 1
    return registros, danados


def hexadecimal(datos):
    return " ".join(f"{b:02x}" for b in datos)


def describir_registro(ruta, cabecera, n):
    desplazamiento, crudo = leer_crudo(ruta, cabecera, n)
    lineas = [f"Registro {n} desde el final: byte {desplazamiento} = 64 + ({cabecera['total'] - n} mod "
              f"{cabecera['capacidad']}) x 32", f"  hex: {hexadecimal(crudo)}"]
    for nombre, valor in zip(NOMBRES, REGISTRO.unpack(crudo)):
        lineas.append(f"  {nombre:<38} {valor}")
    try:
        lineas.append(f"  decodificado: {desempaquetar(crudo)}")
    except ValueError as error:
        lineas.append(f"  REGISTRO DANADO: {error}")
    return lineas


def demo(carpeta):
    """70 s simulados: contacto, arranque, manejo y falla del radiador hasta que la ECU corta el motor."""
    from logic.estado import EstadoCluster
    from logic.reloj import RelojSimulado
    from panel.ecu import Ecu
    from panel.fisica import Vehiculo
    from sistema.lector import CLAVES, CLAVES_EXTRA, convertir, formatear
    carpeta = pathlib.Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for viejo in carpeta.glob("*"):
        if viejo.is_file():
            viejo.unlink()
    reloj = RelojSimulado()
    estado = EstadoCluster(reloj)
    caja = CajaNegra(carpeta / "caja_negra.bin", capacidad=600)
    registrador = Registrador(caja, carpeta, reloj=lambda: reloj.ahora_ms() / 1000)
    v, ecu = Vehiculo(contacto=True, cinturon=True, temp_agua=85.0), Ecu()   # motor ya caliente
    rangos = configuracion.RANGOS_ESPECIFICACION
    for paso in range(1400):                     # 70 s en pasos de 50 ms
        if paso == 40:
            v.motor = True
        elif paso == 100:
            v.cambiar("1")
            v.acelerador = 0.6
        elif paso == 180:
            v.cambiar("2")
        elif paso == 200:
            v.fallas.radiador = True             # el radiador falla: la temperatura sube
        elif paso == 280:
            v.cambiar("3")
            v.acelerador = 0.25
        ecu.vigilar(v, 0.05)
        v.avanzar(0.05)
        if paso % 2 == 0:                        # el cuadro lee cada 100 ms
            for clave, valor in {**v.lecturas(), **v.lecturas_extra(ecu.proteccion)}.items():
                setter = (CLAVES.get(clave) or CLAVES_EXTRA[clave])[0]
                getattr(estado, setter)(convertir(clave, formatear(clave, valor), rangos))
        reloj.avanzar(50)
        estado.tick()
        registrador.muestrear(estado)
        time.sleep(0.0005)                       # como el tablero real: el hilo escritor tambien corre
    registrador.cerrar()
    ruta = carpeta / "caja_negra.bin"
    cabecera = leer_cabecera(ruta)
    registros, danados = ultimos(ruta, cabecera, cabecera["capacidad"])
    eventos = sorted(carpeta.glob("evento_*.csv"))
    lineas = ["Caja negra: demostracion de 70 s simulados (arranque, manejo y falla del radiador)",
              f"Archivo caja_negra.bin: {ruta.stat().st_size} bytes = cabecera {CABECERA.size} + "
              f"{cabecera['capacidad']} registros x {REGISTRO.size} (tamano fijo: no crece)",
              f"Registros escritos: {cabecera['total']} (el anillo conserva los ultimos {cabecera['capacidad']}); "
              f"siguiente posicion: {cabecera['total'] % cabecera['capacidad']}",
              f"Cabecera valida (firma y CRC): {'si' if cabecera['crc_ok'] else 'NO'}",
              f"Lectura completa por acceso directo: {len(registros)} registros validos, {danados} danados",
              f"Muestras descartadas por cola llena: {registrador.descartados}",
              f"Eventos exportados: {', '.join(e.name for e in eventos) or 'ninguno'}"]
    for evento in eventos:
        filas = evento.read_text(encoding="utf-8").splitlines()
        lineas.append(f"  {evento.name}: {len(filas) - 1} registros; columnas: {filas[0]}")
        lineas.append(f"  ultima fila: {filas[-1]}")
    lineas += ["", f"Cabecera en hexadecimal: {hexadecimal(cabecera['bytes'])}", ""]
    lineas += describir_registro(ruta, cabecera, 1)
    (carpeta / "reporte.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0 if cabecera["crc_ok"] and not danados and eventos else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lee la caja negra del cluster (solo lectura)")
    parser.add_argument("--archivo", default=None)
    parser.add_argument("--ultimos", type=int, default=5)
    parser.add_argument("--csv", default=None, help="exporta los ultimos N registros a CSV")
    parser.add_argument("--hex", type=int, default=None, help="muestra el registro N desde el final, byte por byte")
    parser.add_argument("--demo", default=None, help="genera la evidencia en esa carpeta")
    args = parser.parse_args(argv)
    if args.demo:
        return demo(args.demo)
    ruta = pathlib.Path(args.archivo) if args.archivo else configuracion.cargar().archivo_caja_negra
    if not ruta.is_file():
        print(f"No existe {ruta}: abre el tablero para que se cree.", file=sys.stderr)
        return 1
    try:
        cabecera = leer_cabecera(ruta)
    except struct.error:
        print("Cabecera ilegible.", file=sys.stderr)
        return 1
    print(f"{ruta.name}: firma {cabecera['firma'].decode(errors='replace')} v{cabecera['version']}, "
          f"{cabecera['capacidad']} registros de {cabecera['tamano_registro']} bytes, {cabecera['total']} escritos, "
          f"cabecera {'valida' if cabecera['crc_ok'] else 'INVALIDA'}")
    if args.hex is not None:
        print("\n".join(describir_registro(ruta, cabecera, args.hex)))
        return 0
    registros, danados = ultimos(ruta, cabecera, args.ultimos)
    for r in registros[-5:]:
        print("  " + ", ".join(f"{c}={r[c]}" for c in CAMPOS))
    if danados:
        print(f"  {danados} registros danados (CRC) omitidos")
    if args.csv:
        exportar_csv(registros, args.csv)
        print(f"CSV: {args.csv} ({len(registros)} registros)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
