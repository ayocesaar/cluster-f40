"""Bocina: reproduce el sonido del motor que envia el panel de control.

El panel corre en la maquina virtual y las bocinas estan en Windows. Este proceso corre en
Windows (o en cualquier equipo con audio), escucha SOLO en 127.0.0.1 y recibe el estado del
motor como lineas JSON; valida cada mensaje antes de usarlo y sintetiza el sonido localmente
con panel/sonido.py. La conexion llega por un tunel SSH, asi nada queda expuesto a la red.

Uso (Windows, en la carpeta del proyecto):
    python tools\\bocina.py                      # espera al panel en 127.0.0.1:5055
    python tools\\bocina.py --wav prueba.wav --duracion-s 10   # graba a un archivo en vez de sonar
Panel (desde Windows, con el tunel inverso -R):
    ssh -Y -R 5055:127.0.0.1:5055 -p 2222 USUARIO@127.0.0.1 "cd ~/cluster-f40 && ./abrir_panel.sh --sonido 127.0.0.1:5055"
"""

import argparse
import pathlib
import socket
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from panel.sonido import LARGO_MAXIMO, PUERTO, EstadoSonoro, HiloSonido, SalidaWav, abrir_salida_local, de_mensaje  # noqa: E402


def servir(salida, puerto=PUERTO, host="127.0.0.1", duracion_s=None, listo=None, silencio_s=1.0):
    """Atiende un panel a la vez. Sin mensajes durante `silencio_s` el motor se calla (estado apagado)."""
    hilo = HiloSonido(salida)
    hilo.start()
    datos = {"conexiones": 0, "mensajes": 0, "invalidos": 0, "ultimo": None}
    servidor = socket.create_server((host, puerto))
    servidor.settimeout(0.5)
    if listo is not None:
        listo(servidor.getsockname()[1])
    fin = None if duracion_s is None else time.monotonic() + duracion_s
    vigente = lambda: fin is None or time.monotonic() < fin  # noqa: E731
    try:
        while vigente():
            try:
                conexion, _ = servidor.accept()
            except socket.timeout:
                continue
            datos["conexiones"] += 1
            with conexion:
                conexion.settimeout(silencio_s)
                pendiente = b""
                while vigente():
                    try:
                        bloque = conexion.recv(4096)
                    except socket.timeout:
                        hilo.publicar(EstadoSonoro())          # el panel dejo de hablar: silencio
                        continue
                    except OSError:
                        break
                    if not bloque:
                        break
                    pendiente += bloque
                    *lineas, pendiente = pendiente.split(b"\n")
                    if len(pendiente) > LARGO_MAXIMO:            # una linea sin fin no llena la memoria
                        pendiente = b""
                        datos["invalidos"] += 1
                    for linea in lineas:
                        try:
                            estado = de_mensaje(linea)
                        except ValueError:
                            datos["invalidos"] += 1
                            continue
                        hilo.publicar(estado)
                        datos["mensajes"] += 1
                        datos["ultimo"] = estado
            hilo.publicar(EstadoSonoro())                      # panel desconectado: silencio
    finally:
        servidor.close()
        hilo.detener()
    datos["bloques"] = hilo.bloques
    datos["error"] = hilo.error
    return datos


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bocina del sonido del motor (recibe el estado del panel)")
    parser.add_argument("--puerto", type=int, default=PUERTO)
    parser.add_argument("--wav", default=None, help="grabar en un archivo WAV en lugar de las bocinas")
    parser.add_argument("--duracion-s", type=float, default=None, help="por defecto, hasta Ctrl+C")
    args = parser.parse_args(argv)
    if args.wav:
        salida, texto = SalidaWav(args.wav), f"archivo {args.wav}"
    else:
        salida, texto = abrir_salida_local()
        if salida is None:
            print(f"ERROR: no hay salida de audio: {texto}", file=sys.stderr)
            return 1
    print(f"Bocina lista en 127.0.0.1:{args.puerto} (salida: {texto}). Esperando al panel; Ctrl+C para salir.",
          flush=True)
    try:
        datos = servir(salida, args.puerto, duracion_s=args.duracion_s)
    except KeyboardInterrupt:
        print("Bocina cerrada.")
        return 0
    print(f"Bocina: {datos['conexiones']} conexiones, {datos['mensajes']} mensajes validos, "
          f"{datos['invalidos']} rechazados, {datos['bloques']} bloques de audio.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
