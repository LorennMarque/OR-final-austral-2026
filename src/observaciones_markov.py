"""Serie histórica semanal para estimar la cadena de Markov de la Parte II."""

from __future__ import annotations

import numpy as np
import pandas as pd

ESTADOS = ("Normal", "Pico", "Disrupcion")
N_SEMANAS = 160
SEMILLA = 20260816

# Persistencia alta: un régimen suele repetirse, como en la serie del caso.
_TRANSICION = np.array(
    [
        [0.74, 0.21, 0.05],
        [0.28, 0.62, 0.10],
        [0.50, 0.15, 0.35],
    ],
    dtype=float,
)


def observaciones_historicas(n: int = N_SEMANAS, seed: int = SEMILLA) -> pd.DataFrame:
    """Devuelve `n` semanas con columnas `period` y `state`.

    La última semana es Disrupcion, que es la condición inicial de la simulación.
    Cada estado tiene al menos una salida, así las tres filas de la matriz se pueden estimar.
    """
    if n < 4:
        raise ValueError("Hacen falta al menos 4 semanas para observar una salida de cada estado")
    rng = np.random.default_rng(seed)
    for _ in range(100):
        estados = [_siguiente(rng, None)]
        for _semana in range(n - 1):
            estados.append(_siguiente(rng, estados[-1]))
        estados[-1] = "Disrupcion"
        if _todas_las_filas_observadas(estados):
            return pd.DataFrame({"period": np.arange(n, dtype=int), "state": estados})
    raise RuntimeError("No se obtuvo una serie con salida observada desde cada estado")


def _siguiente(rng: np.random.Generator, actual: str | None) -> str:
    if actual is None:
        return "Normal"
    fila = _TRANSICION[ESTADOS.index(actual)]
    return ESTADOS[int(rng.choice(len(ESTADOS), p=fila))]


def _todas_las_filas_observadas(estados: list[str]) -> bool:
    salidas = {estado: 0 for estado in ESTADOS}
    for origen, _destino in zip(estados, estados[1:]):
        salidas[origen] += 1
    return all(salidas[estado] > 0 for estado in ESTADOS)
