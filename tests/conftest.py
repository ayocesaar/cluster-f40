import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from logic.reloj import RelojSimulado
from logic.estado import EstadoCluster


@pytest.fixture
def reloj():
    return RelojSimulado()


@pytest.fixture
def estado(reloj):
    return EstadoCluster(reloj)


@pytest.fixture
def estado_encendido(estado, reloj):
    estado.set_motor(True)
    estado.tick()
    return estado
