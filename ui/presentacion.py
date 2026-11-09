"""Capa de presentacion del cluster: traduce el EstadoCluster a lo que se
dibuja en pantalla (valor, posicion de aguja, color y estado de cada uno de
los 10 elementos, con la numeracion oficial de la especificacion).

No importa Tkinter, para que las pruebas puedan verificar lo que el usuario
veria sin abrir una ventana. ui/tablero.py solo dibuja lo que devuelve vista()."""

# Paleta 8-bit del tablero.
COLOR_NORMAL = "#e8e8f0"
COLOR_ROJO = "#ff4d4d"
COLOR_AMBAR = "#ffb02e"
COLOR_VERDE = "#4fd06b"
COLOR_AZUL = "#4d8dff"
COLOR_APAGADO = "#262638"

LECTURA = "lectura"
INFORMATIVA = "informativa"
CRITICA = "critica"

ELEMENTOS = {
    1: {"nombre": "Velocimetro", "categoria": LECTURA, "minimo": 0, "maximo": 360},
    2: {"nombre": "Presion de aceite", "categoria": LECTURA, "minimo": 0, "maximo": 10},
    3: {"nombre": "Tacometro", "categoria": LECTURA, "minimo": 0, "maximo": 9000},
    4: {"nombre": "Temp. agua", "categoria": LECTURA, "minimo": 40, "maximo": 130},
    5: {"nombre": "Presion turbo", "categoria": LECTURA, "minimo": 0, "maximo": 2},
    6: {"nombre": "Direccionales", "categoria": INFORMATIVA},
    7: {"nombre": "Luces altas", "categoria": INFORMATIVA},
    8: {"nombre": "Intermitentes", "categoria": INFORMATIVA},
    9: {"nombre": "Baja presion aceite", "categoria": CRITICA},
    10: {"nombre": "Falla de frenos", "categoria": CRITICA},
}


def _lectura(numero, valor, color):
    e = ELEMENTOS[numero]
    fraccion = (valor - e["minimo"]) / (e["maximo"] - e["minimo"])
    return {"valor": valor, "fraccion": fraccion, "color": color}


def _testigo(encendido, color):
    return {"encendido": encendido, "color": color if encendido else COLOR_APAGADO}


def vista(estado):
    """Devuelve {numero: descripcion} de los 10 elementos tal como se dibujan."""
    # R07: con emergencia activa y direccional puesto, el testigo 8 tiene
    # precedencia visual: el testigo 6 no se dibuja mientras dure (decision D7).
    precedencia = estado.emergencia_tiene_precedencia
    return {
        1: _lectura(1, estado.velocidad, COLOR_NORMAL),
        2: _lectura(2, estado.p_aceite,
                    COLOR_AMBAR if estado.color_aceite == "ambar" else COLOR_NORMAL),
        3: _lectura(3, estado.rpm, COLOR_ROJO if estado.color_rpm == "rojo" else COLOR_NORMAL),
        4: _lectura(4, estado.temp_agua, COLOR_ROJO if estado.color_temp == "rojo" else COLOR_NORMAL),
        5: _lectura(5, estado.p_turbo,
                    COLOR_AMBAR if estado.contorno_turbo == "ambar" else COLOR_NORMAL),
        6: dict(_testigo(estado.testigo_direccional_encendido and not precedencia, COLOR_VERDE),
                lado=estado.direccional),
        7: _testigo(estado.testigo_luces_altas_encendido, COLOR_AZUL),
        8: _testigo(estado.testigo_emergencia_encendido, COLOR_AMBAR),
        9: _testigo(estado.testigo_baja_presion_aceite, COLOR_ROJO),
        10: _testigo(estado.testigo_falla_frenos_encendido, COLOR_ROJO),
    }
