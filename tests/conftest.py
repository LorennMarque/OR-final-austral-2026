import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.datos import DATA_DIR, cargar_datos  # noqa: E402
from src import markov as mk  # noqa: E402
from src import simulacion as sim  # noqa: E402
from src.transporte import resolver, techo  # noqa: E402

TOL = 1e-7


def cerca(actual, esperado, atol=TOL):
    """allclose con rtol=0 que además rechaza NaN o infinitos."""
    actual = np.asarray(actual, dtype=float)
    esperado = np.asarray(esperado, dtype=float)
    assert np.isfinite(actual).all(), "hay valores no finitos"
    assert np.isfinite(esperado).all(), "hay valores esperados no finitos"
    assert np.allclose(actual, esperado, rtol=0, atol=atol), f"{actual} != {esperado}"


@pytest.fixture(scope="session")
def datos():
    return cargar_datos(DATA_DIR)


@pytest.fixture(scope="session")
def entradas(datos):
    origins, destinations, routes = datos
    return {
        "demanda": destinations.set_index("destination")["nominal_demand"],
        "oferta": origins.set_index("origin")["supply"],
        "capacidad": routes.set_index("route_id")["capacity"],
    }


@pytest.fixture(scope="session")
def soluciones(datos, entradas):
    _, destinations, routes = datos
    d, a, u = entradas["demanda"], entradas["oferta"], entradas["capacidad"]
    u_s2 = u.copy()
    u_s2.loc["C-OES"] = 0.70 * u.loc["C-OES"]
    casos = {
        "nominal": (d, a, u),
        "S1": (techo(1.10, d), a, u),
        "S2": (d, a, u_s2),
        "S3": (d, a * 0.90, u),
        "resguardo": (techo(1.05, d), a, u),
    }
    return {
        nombre: (resolver(routes, destinations, dem, of, cap, nombre), dem, of, cap)
        for nombre, (dem, of, cap) in casos.items()
    }


@pytest.fixture(scope="session")
def observaciones():
    return mk.validar_observaciones(pd.read_csv(DATA_DIR / "markov_observations.csv"))


@pytest.fixture(scope="session")
def matriz(observaciones):
    return mk.estimar_matriz(observaciones)[1]


@pytest.fixture(scope="session")
def parametros():
    return sim.cargar_parametros(DATA_DIR / "markov_state_parameters.csv")


@pytest.fixture(scope="session")
def flujos(soluciones):
    return {
        "nominal": soluciones["nominal"][0].flujos["flujo"].round(9).to_numpy(),
        "resguardo": soluciones["resguardo"][0].flujos["flujo"].round(9).to_numpy(),
    }
