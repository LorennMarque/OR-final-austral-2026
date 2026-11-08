"""Estimación y análisis de la cadena de Markov de regímenes (Parte II)."""

from __future__ import annotations

import numpy as np
import pandas as pd

ESTADOS = ("Normal", "Pico", "Disrupcion")
N_SEMANAS = 160
TOL = 1e-7
ESTADO_INICIAL = "Disrupcion"


def validar_observaciones(
    observaciones: pd.DataFrame,
    estados=ESTADOS,
    n_esperado: int = N_SEMANAS,
    ultimo: str = ESTADO_INICIAL,
) -> pd.DataFrame:
    if list(observaciones.columns) != ["period", "state"]:
        raise ValueError("markov_observations.csv debe tener exactamente las columnas period y state")
    if observaciones.isna().any().any():
        raise ValueError("markov_observations.csv tiene valores faltantes")
    if len(observaciones) != n_esperado:
        raise ValueError(f"Se esperaban {n_esperado} semanas y hay {len(observaciones)}")
    periodos = observaciones["period"].to_numpy()
    if not np.array_equal(periodos, np.arange(n_esperado)):
        raise ValueError("Los períodos deben ser 0, 1, ..., n-1, consecutivos y ordenados")
    desconocidos = set(observaciones["state"]) - set(estados)
    if desconocidos:
        raise ValueError(f"Estados no declarados: {sorted(desconocidos)}")
    if observaciones["state"].iloc[-1] != ultimo:
        raise ValueError(f"La última semana debe ser {ultimo}")
    return observaciones


def contar_transiciones(serie: pd.DataFrame, estados=ESTADOS) -> pd.DataFrame:
    """n_rs: veces que la semana t está en r y la t+1 en s."""
    estados = list(estados)
    codigo = {estado: k for k, estado in enumerate(estados)}
    secuencia = serie["state"].map(codigo)
    if secuencia.isna().any():
        raise ValueError("Hay estados fuera del conjunto declarado")
    secuencia = secuencia.to_numpy(dtype=int)
    conteos = np.zeros((len(estados), len(estados)), dtype=int)
    np.add.at(conteos, (secuencia[:-1], secuencia[1:]), 1)
    return pd.DataFrame(conteos, index=pd.Index(estados, name="desde"), columns=pd.Index(estados, name="hacia"))


def validar_matriz(matriz: pd.DataFrame, estados=ESTADOS, tol: float = TOL) -> pd.DataFrame:
    estados = list(estados)
    if list(matriz.index) != estados or list(matriz.columns) != estados:
        raise ValueError(f"La matriz debe usar el orden {estados} en filas y columnas")
    valores = matriz.to_numpy(dtype=float)
    if not np.isfinite(valores).all():
        raise ValueError("La matriz tiene probabilidades no finitas")
    if (valores < 0).any():
        raise ValueError("La matriz tiene probabilidades negativas")
    if np.abs(valores.sum(axis=1) - 1).max() > tol:
        raise ValueError("Alguna fila de la matriz no suma uno")
    return matriz


def estimar_matriz(serie: pd.DataFrame, estados=ESTADOS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conteos y matriz P_rs = n_rs / sum_q n_rq. Se detiene si una fila no tiene salidas."""
    conteos = contar_transiciones(serie, estados)
    salidas = conteos.sum(axis=1)
    vacias = salidas[salidas == 0].index.tolist()
    if vacias:
        raise RuntimeError(
            "Fila no estimable, sin salidas observadas: " + ", ".join(map(str, vacias))
            + ". No se completa con ceros ni se inventa una autotransición."
        )
    matriz = conteos.div(salidas, axis=0)
    return conteos, validar_matriz(matriz, estados)


def potencia(matriz: pd.DataFrame, k: int) -> pd.DataFrame:
    """P^k: probabilidad de pasar de r a s en exactamente k semanas."""
    return pd.DataFrame(
        np.linalg.matrix_power(matriz.to_numpy(dtype=float), k), index=matriz.index, columns=matriz.columns
    )


def distribucion_inicial(estados=ESTADOS, inicial: str = ESTADO_INICIAL) -> np.ndarray:
    vector = np.zeros(len(estados))
    vector[list(estados).index(inicial)] = 1.0
    return vector


def distribucion_semana(matriz: pd.DataFrame, inicial: np.ndarray, semana: int) -> pd.Series:
    """Distribución del estado en la semana t (la semana 1 es la condición inicial): pi_0 P^(t-1)."""
    if semana < 1:
        raise ValueError("La primera semana es 1")
    return pd.Series(inicial @ potencia(matriz, semana - 1).to_numpy(), index=matriz.columns)


def es_irreducible(matriz: pd.DataFrame) -> bool:
    """Todo estado alcanza a todo otro: (I + A)^(n-1) > 0 con A la matriz de adyacencia."""
    n = len(matriz)
    adyacencia = (matriz.to_numpy() > 0).astype(int)
    alcance = np.linalg.matrix_power(np.eye(n, dtype=int) + adyacencia, n - 1)
    return bool((alcance > 0).all())


def es_regular(matriz: pd.DataFrame) -> bool:
    """Existe k con P^k > 0 en todas las entradas (irreducible y aperiódica).

    Basta revisar k <= (n-1)^2 + 1 (cota de Wielandt).
    """
    n = len(matriz)
    adyacencia = (matriz.to_numpy() > 0).astype(int)
    actual = adyacencia.copy()
    for _ in range((n - 1) ** 2 + 1):
        if (actual > 0).all():
            return True
        actual = ((actual @ adyacencia) > 0).astype(int)
    return False


def estacionaria(matriz: pd.DataFrame, tol: float = TOL) -> pd.Series:
    """Resuelve pi (P - I) = 0 con sum(pi) = 1 por mínimos cuadrados y verifica el resultado."""
    P = matriz.to_numpy(dtype=float)
    n = len(P)
    sistema = np.vstack([P.T - np.eye(n), np.ones((1, n))])
    lado_derecho = np.zeros(n + 1)
    lado_derecho[-1] = 1.0
    pi, *_ = np.linalg.lstsq(sistema, lado_derecho, rcond=None)
    if np.abs(pi @ P - pi).max() > tol or abs(pi.sum() - 1) > tol or (pi < -tol).any():
        raise RuntimeError("No se obtuvo una distribución estacionaria válida")
    return pd.Series(np.clip(pi, 0.0, None), index=matriz.columns, name="estacionaria")


def ocupacion_esperada(matriz: pd.DataFrame, inicial: np.ndarray, horizonte: int) -> pd.Series:
    """Número esperado de semanas en cada estado durante las semanas 1..horizonte."""
    total = sum(distribucion_semana(matriz, inicial, t) for t in range(1, horizonte + 1))
    return total.rename("semanas_esperadas")
