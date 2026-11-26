"""Atajos de comandos del panel: lo que antes se escribia en la terminal.

Cada atajo es una lista de argumentos (sin shell, para evitar inyeccion) o una
funcion de Python que devuelve texto. El Ejecutor corre un comando a la vez en un
proceso hijo y entrega su salida linea por linea a la interfaz mediante una cola
(productor: hilo lector de la tuberia; consumidor: el hilo de Tkinter)."""

import os
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
TEMPORAL = pathlib.Path(tempfile.gettempdir())


def con_pantalla(argv):
    """Las pruebas con ventanas se corren en una pantalla virtual si existe (no saltan al escritorio)."""
    return (["xvfb-run", "-a"] + argv) if shutil.which("xvfb-run") else argv


def pid_tablero():
    """PID de un cluster en ejecucion (python ... main.py), buscado en /proc; None si no hay."""
    proc = pathlib.Path("/proc")
    if not proc.is_dir():
        return None
    for entrada in proc.iterdir():
        if not entrada.name.isdigit() or int(entrada.name) == os.getpid():
            continue
        try:
            args = (entrada / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if args and b"python" in pathlib.Path(args[0].decode(errors="replace")).name.encode() \
                and any(a.endswith(b"main.py") for a in args[1:]):
            return int(entrada.name)
    return None


def estado_tablero():
    """Hilos y memoria del cluster en ejecucion (temas 3.1 y 5.3), leidos de /proc."""
    pid = pid_tablero()
    if pid is None:
        return "El tablero no esta en ejecucion (o este sistema no tiene /proc)."
    lineas = [f"Tablero en ejecucion: PID {pid}"]
    estado = pathlib.Path(f"/proc/{pid}/status").read_text().splitlines()
    lineas += [l for l in estado if l.split(":")[0] in ("State", "Threads", "VmSize", "VmRSS",
                                                          "voluntary_ctxt_switches", "nonvoluntary_ctxt_switches")]
    hilos = sorted(p.name for p in pathlib.Path(f"/proc/{pid}/task").iterdir())
    lineas.append(f"Hilos (LWP): {', '.join(hilos)}")
    descriptores = []
    for fd in pathlib.Path(f"/proc/{pid}/fd").iterdir():
        try:
            destino = os.readlink(fd)
        except OSError:
            continue
        if any(t in destino for t in ("log", "lock", "vehiculo", "odometro")):
            descriptores.append(f"  fd {fd.name} -> {destino}")
    return "\n".join(lineas + ["Archivos abiertos:"] + descriptores)


def observar_proceso():
    """Comandos de observacion de la guia (seccion 6) sobre el tablero en ejecucion. El PID sale de
    /proc (un entero), y cada orden va como lista de argumentos: nada se concatena en un shell."""
    pid = pid_tablero()
    salida = []
    if pid is None:
        salida.append("El tablero no esta en ejecucion: ps no tiene PID que observar.")
    else:
        salida.append(f"$ ps -o pid,ppid,stat,%cpu,%mem,rss,vsz,cmd -p {pid}")
        salida.append(subprocess.run(["ps", "-o", "pid,ppid,stat,%cpu,%mem,rss,vsz,cmd", "-p", str(pid)],
                                     capture_output=True, text=True, timeout=10).stdout.rstrip())
    logs = sorted(str(p.relative_to(RAIZ)) for p in (RAIZ / "logs").glob("*.log"))
    if logs:
        for argv in (["du", "-h", *logs], ["wc", "-l", *logs]):
            salida.append("$ " + " ".join(argv))
            salida.append(subprocess.run(argv, cwd=RAIZ, capture_output=True, text=True, timeout=10).stdout.rstrip())
    else:
        salida.append("Sin bitacoras en logs/ todavia.")
    return "\n".join(salida)


# (grupo, [(etiqueta, ayuda, comando)]); comando = lista de argumentos o funcion sin argumentos.
REPORTE = TEMPORAL / "reporte_panel.txt"
ATAJOS = (
    ("Pruebas", [
        ("Todas", "pytest completo", con_pantalla([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"])),
        ("Odometro", "CP-120 a CP-137", con_pantalla([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                                      "tests/test_odometro.py"])),
        ("Robustez", "CP-138 a CP-151", con_pantalla([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                                      "tests/test_robustez.py"])),
        ("Panel", "CP-155 a CP-162", con_pantalla([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                                   "tests/test_panel.py"])),
        ("Realismo", "CP-163 a CP-183", con_pantalla([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                                      "tests/test_realismo.py", "tests/test_liberacion.py"])),
        ("Aceptacion", "CA-01 a CA-10 sobre la interfaz", con_pantalla([PY, "-m", "aceptacion.escenarios",
                                                                         "tests/datos/escenarios_aceptacion.csv"])),
    ]),
    ("Ataque QA y rendimiento", [
        ("Fuzzing", "valores raros y basura al lector", [PY, "tools/qa/fuzzing.py"]),
        ("Caos 40 s", "corrupcion, borrado y permisos", con_pantalla([PY, "tools/qa/caos.py"])),
        ("P12 15 s", "intervalo, latencia, memoria", con_pantalla([PY, "tools/ejecucion_prolongada.py", "--duracion-s",
                                                                   "15", "--salida", str(TEMPORAL / "metricas_panel.txt")])),
    ]),
    ("Sistema operativo", [
        ("Diagnostico", "tools/diagnostico.sh sobre logs/",
         ["bash", "-c", 'bash tools/diagnostico.sh logs "$1" && cat "$1"', "diagnostico", str(REPORTE)]),
        ("Hilos y memoria", "/proc del tablero en ejecucion", estado_tablero),
        ("ps du wc", "comandos de observacion de la guia, seccion 6", observar_proceso),
        ("Errores", "ultimas lineas de errores.log", ["tail", "-n", "15", "logs/errores.log"]),
    ]),
    ("Liberacion de produccion", [
        ("Banco sano", "9 pruebas de la epoca", [PY, "tools/banco_liberacion.py"]),
        ("Matriz de fallas", "cada falla debe salir RECHAZADA",
         [PY, "tools/banco_liberacion.py", "--evidencia", "--salida", str(TEMPORAL / "banco_panel.txt")]),
    ]),
)


def disponible(comando):
    """Un atajo se puede usar si su programa existe (bash y tail no existen en Windows)."""
    return callable(comando) or shutil.which(comando[0]) is not None or comando[0] == PY


class Ejecutor:
    """Corre un comando a la vez y entrega su salida por una cola (sin bloquear la interfaz)."""

    def __init__(self, cwd=RAIZ):
        self.cwd = cwd
        self.proceso = None
        self.cola = queue.Queue()

    @property
    def ocupado(self):
        return self.proceso is not None and self.proceso.poll() is None

    def iniciar(self, comando, nombre=""):
        if self.ocupado:
            return False
        self.cola.put(("inicio", f"$ {nombre or ' '.join(comando if not callable(comando) else ['(interno)'])}"))
        if callable(comando):
            try:
                texto = comando()
                for linea in texto.splitlines():
                    self.cola.put(("linea", linea))
                self.cola.put(("fin", 0))
            except Exception as error:  # noqa: BLE001 - se informa en la consola
                self.cola.put(("linea", f"{type(error).__name__}: {error}"))
                self.cola.put(("fin", 1))
            return True
        entorno = dict(os.environ, PYTHONUNBUFFERED="1")
        try:
            self.proceso = subprocess.Popen(comando, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, bufsize=1, env=entorno)
        except OSError as error:
            self.cola.put(("linea", f"No se pudo ejecutar: {error}"))
            self.cola.put(("fin", 127))
            return False
        threading.Thread(target=self._leer, args=(self.proceso,), daemon=True).start()
        return True

    def _leer(self, proceso):
        for linea in proceso.stdout:
            self.cola.put(("linea", linea.rstrip("\n")))
        self.cola.put(("fin", proceso.wait()))

    def detener(self):
        if self.ocupado:
            self.proceso.terminate()      # SIGTERM: cierre ordenado del comando
            return True
        return False

    def pendientes(self):
        mensajes = []
        while True:
            try:
                mensajes.append(self.cola.get_nowait())
            except queue.Empty:
                return mensajes
