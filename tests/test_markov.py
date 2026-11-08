import numpy as np
import pandas as pd
import pytest

from src import markov as mk
from src.datos import DATA_DIR
from src.markov import ESTADOS

from conftest import TOL, cerca

CONTEOS = [[66, 20, 3], [16, 37, 5], [6, 1, 5]]
MATRIZ = [[66 / 89, 20 / 89, 3 / 89], [16 / 58, 37 / 58, 5 / 58], [6 / 12, 1 / 12, 5 / 12]]


def test_serie_valida(observaciones):
    assert len(observaciones) == 160
    assert set(observaciones["state"]) <= set(ESTADOS)
    assert observaciones["state"].iloc[-1] == "Disrupcion"
    assert ESTADOS == ("Normal", "Pico", "Disrupcion")


def test_serie_es_la_entregada():
    entregada = DATA_DIR.parent / "docs" / "final" / "markov_observations.csv"
    if not entregada.exists():
        pytest.skip("docs/final/markov_observations.csv no está disponible")
    assert (DATA_DIR / "markov_observations.csv").read_bytes() == entregada.read_bytes()


def test_conteos(observaciones):
    conteos = mk.contar_transiciones(observaciones)
    assert conteos.to_numpy().tolist() == CONTEOS
    assert conteos.to_numpy().sum() == 159
    assert conteos.sum(axis=1).tolist() == [89, 58, 12]
    assert list(conteos.index) == list(ESTADOS) and list(conteos.columns) == list(ESTADOS)


def test_matriz(matriz):
    cerca(matriz.to_numpy(), MATRIZ)
    cerca(matriz.sum(axis=1), np.ones(3))
    assert (matriz.to_numpy() >= 0).all()
    cerca(matriz.loc["Disrupcion"], [0.5, 1 / 12, 5 / 12])


def test_estado_sin_salidas_se_rechaza():
    serie = pd.DataFrame({"period": range(4), "state": ["Normal", "Pico", "Normal", "Disrupcion"]})
    with pytest.raises(RuntimeError, match="Disrupcion"):
        mk.estimar_matriz(serie)


@pytest.mark.parametrize("dano", ["estado_desconocido", "largo", "final", "periodos", "faltante"])
def test_validar_observaciones_rechaza(dano, observaciones):
    serie = observaciones.copy()
    if dano == "estado_desconocido":
        serie.loc[3, "state"] = "Crisis"
    elif dano == "largo":
        serie = serie.iloc[1:].reset_index(drop=True)
        serie["period"] = range(len(serie))
    elif dano == "final":
        serie.loc[159, "state"] = "Normal"
    elif dano == "periodos":
        serie.loc[5, "period"] = 99
    elif dano == "faltante":
        serie.loc[7, "state"] = None
    with pytest.raises(ValueError):
        mk.validar_observaciones(serie)


def test_validar_matriz_rechaza_filas_invalidas(matriz):
    mala = matriz.copy()
    mala.iloc[0, 0] += 0.01
    with pytest.raises(ValueError):
        mk.validar_matriz(mala)
    mala = matriz.copy()
    mala.iloc[0, 0], mala.iloc[0, 1] = -0.1, mala.iloc[0, 1] + mala.iloc[0, 0] + 0.1
    with pytest.raises(ValueError):
        mk.validar_matriz(mala)
    with pytest.raises(ValueError):
        mk.validar_matriz(matriz.iloc[::-1])


def test_un_paso(matriz):
    cerca(mk.potencia(matriz, 1), matriz)
    pi1 = mk.distribucion_inicial()
    cerca(pi1, [0, 0, 1])
    cerca(mk.distribucion_semana(matriz, pi1, 1), pi1)
    cerca(mk.distribucion_semana(matriz, pi1, 2), matriz.loc["Disrupcion"])


def test_varios_pasos_chapman_kolmogorov(matriz):
    P = matriz.to_numpy()
    cerca(mk.potencia(matriz, 2), P @ P)
    cerca(mk.potencia(matriz, 5), mk.potencia(matriz, 2).to_numpy() @ mk.potencia(matriz, 3).to_numpy())
    pi1 = mk.distribucion_inicial()
    for t in (1, 2, 4, 13, 25):
        siguiente = mk.distribucion_semana(matriz, pi1, t).to_numpy() @ P
        cerca(mk.distribucion_semana(matriz, pi1, t + 1), siguiente)
        cerca(mk.distribucion_semana(matriz, pi1, t).sum(), 1.0)


def test_estacionaria(matriz):
    assert mk.es_irreducible(matriz) and mk.es_regular(matriz)
    pi = mk.estacionaria(matriz)
    cerca(pi.to_numpy() @ matriz.to_numpy(), pi)
    cerca(pi.sum(), 1.0)
    cerca(pi, [0.5522, 0.3624, 0.0855], atol=5e-4)
    cerca(mk.potencia(matriz, 200).to_numpy(), np.tile(pi.to_numpy(), (3, 1)))


def test_reducibilidad_detectada():
    estados = list(ESTADOS)
    absorbente = pd.DataFrame([[1.0, 0, 0], [0.5, 0.5, 0], [0, 0.5, 0.5]], index=estados, columns=estados)
    assert not mk.es_irreducible(absorbente)
    periodica = pd.DataFrame([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]], index=estados, columns=estados)
    assert mk.es_irreducible(periodica) and not mk.es_regular(periodica)


def test_ocupacion_esperada(matriz):
    pi1 = mk.distribucion_inicial()
    ocupacion = mk.ocupacion_esperada(matriz, pi1, 26)
    cerca(ocupacion.sum(), 26)
    cerca(mk.ocupacion_esperada(matriz, pi1, 1), pi1)
    assert ocupacion["Disrupcion"] > 26 * mk.estacionaria(matriz)["Disrupcion"]
