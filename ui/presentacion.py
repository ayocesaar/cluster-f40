"""Capa de presentacion del cluster: traduce el EstadoCluster a lo que se
dibuja en pantalla (valor, posicion de aguja, color y estado de cada uno de
los 10 elementos, con la numeracion oficial de la especificacion).

No importa Tkinter, para que las pruebas puedan verificar lo que el usuario
veria sin abrir una ventana. ui/tablero.py solo dibuja lo que devuelve vista()."""

# Colores de estado que dibuja el tablero (la aguja y los testigos toman estos colores).
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

# Elementos adicionales (Etapa 18): se agregan a los diez aprobados, no los sustituyen.
ELEMENTOS_EXTRA = {
    12: {"nombre": "Puerta abierta", "categoria": INFORMATIVA},
    13: {"nombre": "Cinturon", "categoria": CRITICA},
    14: {"nombre": "Combustible", "categoria": LECTURA, "minimo": 0, "maximo": 100},
    15: {"nombre": "Proteccion del motor", "categoria": CRITICA},
    16: {"nombre": "Carga de bateria", "categoria": CRITICA},
}
TANQUE_L = 120.0     # capacidad del tanque del F40 (fichas tecnicas publicadas; ver docs/realismo_y_liberacion.md)
TEXTO_CAUSA = {"sobretemperatura": "SOBRETEMPERATURA", "sobrepresion_turbo": "SOBREPRESION TURBO",
               "aceite": "ACEITE", "combustible": "SIN COMBUSTIBLE", "electrica": "SISTEMA ELECTRICO"}


def _lectura(numero, valor, color):
    e = ELEMENTOS[numero]
    fraccion = (valor - e["minimo"]) / (e["maximo"] - e["minimo"])
    return {"valor": valor, "fraccion": fraccion, "color": color}


def _testigo(encendido, color):
    return {"encendido": encendido, "color": color if encendido else COLOR_APAGADO}


def vista_odometro(estado):
    """Elemento 11 (odometro): los 6 digitos que muestra el tablero."""
    return {"km": estado.odometro.valor, "texto": estado.odometro.texto}


def vista(estado):
    """Devuelve {numero: descripcion} de los 10 elementos tal como se dibujan."""
    # R07: con emergencia activa y direccional puesto, el testigo 8 tiene
    # precedencia visual: el testigo 6 no se dibuja mientras dure (decision D7).
    precedencia = estado.emergencia_tiene_precedencia
    # Prueba de testigos al dar contacto (Etapa 18): durante 2 s se encienden todos. Es solo de
    # presentacion: las reglas y la bitacora no cambian.
    prueba = getattr(estado, "prueba_testigos_activa", False)
    return {
        1: _lectura(1, estado.velocidad, COLOR_NORMAL),
        2: _lectura(2, estado.p_aceite,
                    COLOR_AMBAR if estado.color_aceite == "ambar" else COLOR_NORMAL),
        3: _lectura(3, estado.rpm, COLOR_ROJO if estado.color_rpm == "rojo" else COLOR_NORMAL),
        4: _lectura(4, estado.temp_agua, COLOR_ROJO if estado.color_temp == "rojo" else COLOR_NORMAL),
        5: _lectura(5, estado.p_turbo,
                    COLOR_AMBAR if estado.contorno_turbo == "ambar" else COLOR_NORMAL),
        6: dict(_testigo(estado.testigo_direccional_encendido and not precedencia or prueba, COLOR_VERDE),
                lado=estado.direccional),
        7: _testigo(estado.testigo_luces_altas_encendido or prueba, COLOR_AZUL),
        8: _testigo(estado.testigo_emergencia_encendido or prueba, COLOR_AMBAR),
        9: _testigo(estado.testigo_baja_presion_aceite or prueba, COLOR_ROJO),
        10: _testigo(estado.testigo_falla_frenos_encendido or prueba, COLOR_ROJO),
    }


def vista_extra(estado):
    """Elementos adicionales 12-15 y el estado de la llave, tal como se dibujan.

    Un elemento sin dato (el productor no envia su clave) queda apagado y marcado con
    sin_dato=True, para que el tablero lo muestre en gris en lugar de inventar un valor."""
    prueba = estado.prueba_testigos_activa
    puerta = estado.testigo_puerta_encendido
    combustible = estado.combustible
    causa = estado.falla_motor if estado.proteccion_motor_activa else None
    if estado.motor_activo:
        llave = "MOTOR"
    elif estado.encendido:
        llave = "CONTACTO"
    else:
        llave = "OFF"
    return {
        12: dict(_testigo(puerta or prueba, COLOR_ROJO if puerta and estado.en_movimiento else COLOR_AMBAR),
                 sin_dato=estado.puertas is None, bits=estado.puertas,
                 detalle="+".join(n for b, n in ((1, "CONDUCTOR"), (2, "PASAJERO")) if (estado.puertas or 0) & b)),
        13: dict(_testigo(estado.testigo_cinturon_encendido or prueba, COLOR_ROJO),
                 sin_dato=estado.cinturon_desabrochado is None),
        14: {"valor": combustible, "litros": None if combustible is None else combustible * TANQUE_L / 100,
             "fraccion": 0.0 if combustible is None else combustible / 100,
             "color": COLOR_AMBAR if estado.reserva_combustible else COLOR_NORMAL,
             "reserva": dict(_testigo(estado.reserva_combustible or prueba, COLOR_AMBAR)),
             "sin_dato": combustible is None},
        15: dict(_testigo(causa is not None or prueba, COLOR_ROJO), causa=causa,
                 texto=TEXTO_CAUSA.get(causa, ""), sin_dato=estado.falla_motor is None),
        16: dict(_testigo(estado.testigo_carga_encendido or prueba, COLOR_ROJO), voltaje=estado.voltaje,
                 sin_dato=estado.voltaje is None and estado.encendido),
        "llave": {"estado": llave, "prueba": prueba},
    }
