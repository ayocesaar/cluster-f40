"""Pruebas de aceptacion CA-01 a CA-10 (una por elemento, dirigidas por
tests/datos/escenarios_aceptacion.csv) y pruebas de manejo del archivo de
escenarios. Las de aceptacion requieren servidor grafico (en la VM: xvfb-run)."""

import pathlib

import pytest

tk = pytest.importorskip("tkinter")

from aceptacion.escenarios import CONTROLES, ErrorEscenarios, cargar, ejecutar, main

CSV = pathlib.Path(__file__).parent / "datos" / "escenarios_aceptacion.csv"
CABECERA = "escenario,paso,accion,valor,avanzar_ms,elemento,esperado,descripcion\n"


def _requiere_display():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("sin servidor grafico (DISPLAY)")


def _verificar(escenario):
    _requiere_display()
    resultados = ejecutar(cargar(CSV)[escenario])
    fallidos = [f"paso {r.paso.numero}: esperado={r.paso.esperado} observado={r.observado}"
                for r in resultados if not r.aprobado]
    assert not fallidos, "; ".join(fallidos)


def _csv(tmp_path, contenido):
    ruta = tmp_path / "escenarios.csv"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_ca01_velocimetro():
    """CA-01: velocimetro: estado seguro, ciclo de 100 ms, limite 360 km/h y regreso a 0 al apagar (R01)."""
    _verificar("CA-01")


def test_ca02_presion_aceite():
    """CA-02: medidor 2 ambar bajo 1 bar con motor activo, cruzando el umbral en ambos sentidos (R01)."""
    _verificar("CA-02")


def test_ca03_tacometro():
    """CA-03: tacometro rojo en 8000, histeresis hasta 7799 y RPM a 0 al apagar (R01, R03)."""
    _verificar("CA-03")


def test_ca04_temperatura_agua():
    """CA-04: temperatura roja sobre 110, histeresis hasta 105 y ciclo de 500 ms (R04)."""
    _verificar("CA-04")


def test_ca05_presion_turbo():
    """CA-05: contorno ambar sobre 1.5 bar e histeresis hasta 1.4 bar (R05)."""
    _verificar("CA-05")


def test_ca06_direccionales():
    """CA-06: testigo 6 verde alternando cada 500 ms con IZQ y DER, apagado con OFF (R06)."""
    _verificar("CA-06")


def test_ca07_luces_altas():
    """CA-07: testigo 7 azul fijo con motor encendido y apagado con motor apagado (R01, R07)."""
    _verificar("CA-07")


def test_ca08_emergencia_y_precedencia():
    """CA-08: testigo 8 ambar alternando cada 500 ms con precedencia visual sobre el 6 (R06, R07)."""
    _verificar("CA-08")


def test_ca09_baja_presion_aceite():
    """CA-09: testigo 9 rojo tras 1 s bajo 1 bar y apagado tras 1 s en 1.2 bar (R01, R02)."""
    _verificar("CA-09")


def test_ca10_falla_frenos():
    """CA-10: testigo 10 rojo alternando cada 300 ms aun con motor apagado (R01, R08)."""
    _verificar("CA-10")


def test_cp79_archivo_inexistente(tmp_path):
    """CP-79: un archivo de escenarios inexistente se informa con un error claro."""
    with pytest.raises(ErrorEscenarios, match="no existe"):
        cargar(tmp_path / "no_existe.csv")


@pytest.mark.parametrize("contenido, mensaje", [("", "vacio"), (CABECERA, "no tiene pasos")])
def test_cp80_archivo_vacio_o_sin_pasos(tmp_path, contenido, mensaje):
    """CP-80: un archivo vacio o solo con cabecera se rechaza."""
    with pytest.raises(ErrorEscenarios, match=mensaje):
        cargar(_csv(tmp_path, contenido))


def test_cp81_columna_faltante(tmp_path):
    """CP-81: si falta una columna obligatoria se informa cual."""
    with pytest.raises(ErrorEscenarios, match="faltan columnas.*esperado"):
        cargar(_csv(tmp_path, "escenario,paso,accion,valor,avanzar_ms,elemento,descripcion\n"))


def test_cp82_control_desconocido(tmp_path):
    """CP-82: un control que no existe se rechaza indicando la linea."""
    with pytest.raises(ErrorEscenarios, match="linea 2: control desconocido"):
        cargar(_csv(tmp_path, CABECERA + "CA-X,1,acelerador,1,0,3,normal,x\n"))


def test_cp83_valor_no_numerico(tmp_path):
    """CP-83: un valor no numerico para un deslizador se rechaza."""
    with pytest.raises(ErrorEscenarios, match="no es numerico"):
        cargar(_csv(tmp_path, CABECERA + "CA-X,1,rpm,mucho,0,3,normal,x\n"))


@pytest.mark.parametrize("fila, mensaje", [
    ("CA-X,1,-,,0,3,verde,x", "no valido para el elemento"),
    ("CA-X,1,-,,0,11,normal,x", "elemento fuera de 1-10"),
    ("CA-X,1,-,,-5,3,normal,x", "avanzar_ms negativo"),
    ("CA-X,uno,-,,0,3,normal,x", "deben ser numericos"),
    ("CA-X,1,motor,2,0,3,normal,x", "solo acepta 0 o 1"),
    ("CA-X,1,direccional,ARRIBA,0,6,apagado,x", "OFF, IZQ o DER"),
])
def test_cp84_filas_invalidas(tmp_path, fila, mensaje):
    """CP-84: filas con esperado, elemento, tiempo, numero de paso o valor invalidos se rechazan."""
    with pytest.raises(ErrorEscenarios, match=mensaje):
        cargar(_csv(tmp_path, CABECERA + fila + "\n"))


def test_cp85_archivo_real_cubre_10_escenarios_y_todos_los_controles():
    """CP-85: el CSV de aceptacion define CA-01 a CA-10 y recorre los 10 controles."""
    escenarios = cargar(CSV)
    assert list(escenarios) == [f"CA-{n:02d}" for n in range(1, 11)]
    usados = {p.accion for pasos in escenarios.values() for p in pasos}
    assert set(CONTROLES) <= usados


def test_cp87_main_sin_argumentos(capsys):
    """CP-87: el ejecutor de aceptacion sin archivo muestra el uso y devuelve 2."""
    assert main([]) == 2
    assert "uso:" in capsys.readouterr().err


def test_cp88_main_archivo_inexistente(tmp_path, capsys):
    """CP-88: el ejecutor con un archivo inexistente muestra ERROR y devuelve 2."""
    assert main([str(tmp_path / "no_existe.csv")]) == 2
    assert "ERROR: no existe" in capsys.readouterr().err


def test_cp89_main_con_archivo_real(capsys):
    """CP-89: el ejecutor con el CSV real aprueba los 10 escenarios y devuelve 0."""
    _requiere_display()
    assert main([str(CSV)]) == 0
    assert "Resumen: 10/10 escenarios aprobados" in capsys.readouterr().out


def test_cp90_main_detecta_expectativa_incorrecta(tmp_path, capsys):
    """CP-90: el oraculo detecta una diferencia: una expectativa falsa da FALLIDO y devuelve 1."""
    _requiere_display()
    ruta = _csv(tmp_path, CABECERA + "CA-Z,1,motor,1,0,3,rojo,expectativa incorrecta a proposito\n")
    assert main([str(ruta)]) == 1
    salida = capsys.readouterr().out
    assert "CA-Z: FALLIDO" in salida and "XX paso 1" in salida
