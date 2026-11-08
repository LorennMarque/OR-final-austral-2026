"""Rutas del proyecto, carga y validación de los datos de entrada."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"

ORIGENES = ("Norte", "Centro", "Sur")
ZONAS = ("Capital", "Oeste", "Este", "Costa", "Interior")
RUTAS = (
    "N-CAP", "N-OES", "N-EST", "N-COS", "N-INT",
    "C-CAP", "C-OES", "C-EST", "C-COS", "C-INT",
    "S-CAP", "S-OES", "S-EST", "S-COS", "S-INT",
)

COLUMNAS_ORIGENES = {"origin": None, "supply": "numerica"}
COLUMNAS_ZONAS = {
    "destination": None,
    "nominal_demand": "numerica",
    "shortage_penalty": "numerica",
    "initial_inventory": "numerica",
    "storage_capacity": "numerica",
    "holding_cost": "numerica",
    "waste_cost": "numerica",
}
COLUMNAS_RUTAS = {
    "route_id": None,
    "origin": None,
    "destination": None,
    "unit_cost": "numerica",
    "capacity": "numerica",
}


class DatosInvalidos(ValueError):
    """Un archivo de entrada no cumple el diccionario de datos."""


def sha256(ruta: str | Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def validar_tabla(tabla: pd.DataFrame, nombre: str, columnas: dict, clave: str) -> pd.DataFrame:
    """Columnas obligatorias, sin faltantes, clave única y numéricas finitas y no negativas."""
    ausentes = [c for c in columnas if c not in tabla.columns]
    if ausentes:
        raise DatosInvalidos(f"{nombre}: faltan columnas {ausentes}")
    tabla = tabla[list(columnas)].copy()
    if tabla.isna().any().any():
        celdas = tabla.columns[tabla.isna().any()].tolist()
        raise DatosInvalidos(f"{nombre}: hay valores faltantes en {celdas}")
    if not tabla[clave].is_unique:
        repetidos = tabla.loc[tabla[clave].duplicated(), clave].tolist()
        raise DatosInvalidos(f"{nombre}: {clave} repetido {repetidos}")
    for columna, tipo in columnas.items():
        if tipo != "numerica":
            continue
        if not pd.api.types.is_numeric_dtype(tabla[columna]):
            raise DatosInvalidos(f"{nombre}: {columna} no es numérica")
        valores = tabla[columna].to_numpy(dtype=float)
        if not np.isfinite(valores).all():
            raise DatosInvalidos(f"{nombre}: {columna} tiene valores no finitos")
        if (valores < 0).any():
            raise DatosInvalidos(f"{nombre}: {columna} tiene valores negativos")
        tabla[columna] = valores
    return tabla


def validar_red(origins: pd.DataFrame, destinations: pd.DataFrame, routes: pd.DataFrame) -> None:
    """Integridad referencial y conjunto de rutas habilitadas del caso canónico."""
    if tuple(origins["origin"]) != ORIGENES:
        raise DatosInvalidos(f"origins.csv: se esperaban {ORIGENES} en ese orden")
    if tuple(destinations["destination"]) != ZONAS:
        raise DatosInvalidos(f"destinations.csv: se esperaban {ZONAS} en ese orden")
    if tuple(routes["route_id"]) != RUTAS:
        raise DatosInvalidos("routes.csv: el conjunto u orden de las 15 rutas no es el esperado")
    desconocidos = set(routes["origin"]) - set(origins["origin"])
    if desconocidos:
        raise DatosInvalidos(f"routes.csv: centros inexistentes {sorted(desconocidos)}")
    desconocidas = set(routes["destination"]) - set(destinations["destination"])
    if desconocidas:
        raise DatosInvalidos(f"routes.csv: zonas inexistentes {sorted(desconocidas)}")
    if routes.duplicated(["origin", "destination"]).any():
        raise DatosInvalidos("routes.csv: hay dos rutas para el mismo par centro-zona")


def cargar_datos(data_dir: str | Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Devuelve `origins`, `destinations` y `routes` validados."""
    data_dir = Path(data_dir)
    origins = validar_tabla(pd.read_csv(data_dir / "origins.csv"), "origins.csv", COLUMNAS_ORIGENES, "origin")
    destinations = validar_tabla(
        pd.read_csv(data_dir / "destinations.csv"), "destinations.csv", COLUMNAS_ZONAS, "destination"
    )
    routes = validar_tabla(pd.read_csv(data_dir / "routes.csv"), "routes.csv", COLUMNAS_RUTAS, "route_id")
    validar_red(origins, destinations, routes)
    return origins, destinations, routes
