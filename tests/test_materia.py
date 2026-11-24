"""Pruebas de temas de la materia aplicados al cluster (Etapa 15).

CP-152 senales (tema 3.2), CP-153 y CP-154 el analizador de bitacoras en Bash
(tema 2.3). CP-152 fallaba antes de agregar el manejo de senales (DEF-15)."""

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "diagnostico.sh"
posix = pytest.mark.skipif(os.name != "posix" or shutil.which("bash") is None, reason="requiere Linux con bash")


def _proyecto(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "datos").mkdir()
    (tmp_path / "config" / "cluster.ini").write_text("[intervalos]\nlectura_ms = 50\n", encoding="utf-8")
    (tmp_path / "datos" / "vehiculo.conf").write_text(
        "motor=1\nvelocidad=360\nrpm=3000\npresion_aceite=5\ntemp_agua=90\npresion_turbo=0.5\n"
        "direccional=off\nluces_altas=0\nemergencia=0\nfalla_frenos=0\n", encoding="utf-8")
    return tmp_path


@posix
@pytest.mark.parametrize("senal", [signal.SIGTERM, signal.SIGINT])
def test_cp152_senal_produce_cierre_ordenado(tmp_path, senal):
    """CP-152: kill -TERM o Ctrl+C cierran el cluster en orden: guarda el kilometraje y registra el fin (DEF-15)."""
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin servidor grafico (DISPLAY)")
    proyecto = _proyecto(tmp_path)
    proceso = subprocess.Popen([sys.executable, str(RAIZ / "main.py"), "--proyecto", str(proyecto)])
    eventos = proyecto / "logs" / "eventos.log"
    limite = time.monotonic() + 15
    while time.monotonic() < limite and not (eventos.exists() and "valor_actualizado" in eventos.read_text()):
        time.sleep(0.1)
    time.sleep(1.5)                                  # unos 0.15 km a 360 km/h
    proceso.send_signal(senal)
    assert proceso.wait(timeout=15) == 0
    texto = eventos.read_text(encoding="utf-8")
    assert f"senal_recibida {signal.Signals(senal).name} cierre ordenado" in texto
    assert " fin info=" in texto and "odometro_guardado" in texto
    assert float((proyecto / "datos" / "odometro.txt").read_text()) > 0


def _logs(carpeta, errores=0, testigo10=False):
    carpeta.mkdir(parents=True)
    eventos = ["2026-11-23T10:00:00-06:00 INFO  sistema inicio modo=manual",
               "2026-11-23T10:00:01-06:00 INFO  odometro odometro_actualizado km=000063 resultado=aceptado"]
    if testigo10:
        eventos.append("2026-11-23T10:00:02-06:00 WARN  monitor_seguridad testigo_10_encendido falla_frenos=1")
    (carpeta / "eventos.log").write_text("\n".join(eventos) + "\n", encoding="utf-8")
    lineas = [f"2026-11-23T10:00:0{i % 10}-06:00 ERROR lector_datos fuera_de_rango velocidad=400 resultado=rechazado"
              for i in range(errores)]
    (carpeta / "errores.log").write_text("".join(l + "\n" for l in lineas), encoding="utf-8")
    return carpeta


def _correr(*args):
    return subprocess.run(["bash", str(SCRIPT), *map(str, args)], capture_output=True, text=True)


@posix
def test_cp153_diagnostico_valida_argumentos_y_rutas(tmp_path):
    """CP-153: el script de diagnostico valida argumentos y carpeta con codigos de salida distintos (tema 2.3)."""
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
    assert _correr().returncode == 1 and "Uso:" in _correr().stderr
    assert _correr("a", "b", "c").returncode == 1
    assert _correr(tmp_path / "no existe").returncode == 2
    (tmp_path / "vacia").mkdir()
    assert _correr(tmp_path / "vacia").returncode == 3


@posix
@pytest.mark.parametrize("errores, testigo, estado", [
    (0, False, "Estado: SIN ERRORES"),
    (3, False, "Estado: REVISION RECOMENDADA"),
    (7, True, "Estado: CRITICO + ALERTA DE SEGURIDAD"),
])
def test_cp154_diagnostico_clasifica_y_reporta(tmp_path, errores, testigo, estado):
    """CP-154: el reporte cuenta eventos, clasifica el estado y admite rutas con espacios (tema 2.3)."""
    carpeta = _logs(tmp_path / "logs con espacios", errores, testigo)
    reporte = tmp_path / "mi reporte.txt"
    resultado = _correr(carpeta, reporte)
    assert resultado.returncode == 0, resultado.stderr
    texto = reporte.read_text(encoding="utf-8")
    assert estado in texto and f"ERROR: {errores} (rechazados: {errores})" in texto
    assert "Kilometros registrados: 1" in texto
    if errores:
        assert f"{errores} fuera_de_rango" in texto
