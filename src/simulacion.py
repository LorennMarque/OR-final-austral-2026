"""Simulación Monte Carlo de políticas fijas bajo regímenes de Markov (Parte II).

Dos implementaciones del mismo modelo semanal:
- `operar_semana` / `operar`: versión pandas, explicativa, con una tabla por semana.
- `evaluar_plan`: versión NumPy, la que usa la campaña de 1.200 trayectorias.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from .markov import ESTADOS

TOL = 1e-7
HORIZONTE = 26
ESTADO_INICIAL = "Disrupcion"
SEMILLA_MAESTRA = 20260816
N_PILOTO = 200
N_CAMPANA = 1200
COLUMNAS_ESTADO = ["demand_multiplier", "capacity_multiplier", "route_availability"]
POLITICAS = ("nominal", "resguardo")
METRICAS = [
    ("costo", "Costo total"),
    ("servicio", "Nivel de servicio"),
    ("faltante", "Unidades faltantes"),
    ("probabilidad_faltante", "Probabilidad de algún faltante"),
    ("fraccion_semanas_faltante", "Fracción de semanas con faltante"),
    ("inventario", "Inventario medio"),
    ("descarte", "Descarte"),
]


def cargar_parametros(ruta: str | Path, estados=ESTADOS) -> pd.DataFrame:
    """Multiplicadores y disponibilidad por estado, validados y en el orden de `estados`."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. Hacen falta demand_multiplier, capacity_multiplier y "
            "route_availability para Normal, Pico y Disrupcion."
        )
    tabla = pd.read_csv(ruta)
    faltan = [c for c in ["state", *COLUMNAS_ESTADO] if c not in tabla.columns]
    if faltan:
        raise ValueError(f"markov_state_parameters.csv: faltan columnas {faltan}")
    if not tabla["state"].is_unique:
        raise ValueError("markov_state_parameters.csv: hay estados repetidos")
    if set(tabla["state"]) != set(estados):
        raise ValueError(f"markov_state_parameters.csv: se esperaban exactamente los estados {list(estados)}")
    tabla = tabla.set_index("state").loc[list(estados), COLUMNAS_ESTADO]
    if tabla.isna().any().any():
        raise ValueError("markov_state_parameters.csv: hay parámetros faltantes")
    tabla = tabla.astype(float)
    if not np.isfinite(tabla.to_numpy()).all():
        raise ValueError("markov_state_parameters.csv: hay parámetros no finitos")
    if (tabla < 0).any().any():
        raise ValueError("markov_state_parameters.csv: hay multiplicadores negativos")
    if (tabla["route_availability"] > 1).any():
        raise ValueError("markov_state_parameters.csv: route_availability fuera de [0, 1]")
    return tabla


def crear_generadores(semilla: int = SEMILLA_MAESTRA, n: int = N_CAMPANA) -> list[np.random.Generator]:
    """Un generador independiente por réplica, derivado de la semilla maestra."""
    return [np.random.default_rng(hijo) for hijo in np.random.SeedSequence(semilla).spawn(n)]


def demanda(rng, demanda_nominal, multiplicador):
    """D_j ~ Poisson(d_j * m_dem), independiente entre zonas."""
    media = np.asarray(demanda_nominal, dtype=float) * multiplicador
    return rng.poisson(media)


def disponibilidad(rng, n_rutas, probabilidad):
    """A_ij ~ Bernoulli(route_availability), independiente entre rutas."""
    return (rng.random(n_rutas) < probabilidad).astype(int)


def capacidad_efectiva(disponible, capacidad_nominal, multiplicador):
    """A_ij * u_ij * m_cap: cero si la ruta no opera."""
    operativo = np.asarray(disponible, dtype=float)
    nominal = np.asarray(capacidad_nominal, dtype=float)
    return operativo * nominal * multiplicador


def siguiente_estado(rng, matriz: pd.DataFrame, estado: str) -> str:
    nombres = list(matriz.columns)
    fila = matriz.loc[estado].to_numpy(dtype=float)
    fila = fila / fila.sum()
    return nombres[int(rng.choice(len(nombres), p=fila))]


def trayectoria_estados(rng, matriz, horizonte=HORIZONTE, inicial=ESTADO_INICIAL) -> list[str]:
    """Sólo la cadena de estados, para ilustrar una trayectoria."""
    estados = [inicial]
    for _ in range(horizonte - 1):
        estados.append(siguiente_estado(rng, matriz, estados[-1]))
    return estados


def entorno(rng, matriz, rutas, zonas, parametros, horizonte=HORIZONTE, inicial=ESTADO_INICIAL) -> dict:
    """Un futuro completo de `horizonte` semanas, generado sin conocer la política.

    Orden de sorteos en cada semana t: estado (si t > 1), demandas de las cinco zonas,
    disponibilidad de las quince rutas.
    """
    demanda_nominal = zonas["nominal_demand"].to_numpy()
    capacidad_nominal = rutas["capacity"].to_numpy()
    estado = inicial
    estados, pedidas, abiertas, topes = [], [], [], []
    for t in range(horizonte):
        if t:
            estado = siguiente_estado(rng, matriz, estado)
        fila = parametros.loc[estado]
        pedida = demanda(rng, demanda_nominal, float(fila["demand_multiplier"]))
        abierta = disponibilidad(rng, len(rutas), float(fila["route_availability"]))
        tope = capacidad_efectiva(abierta, capacidad_nominal, float(fila["capacity_multiplier"]))
        estados.append(estado)
        pedidas.append(np.asarray(pedida, dtype=float))
        abiertas.append(np.asarray(abierta, dtype=int))
        topes.append(np.asarray(tope, dtype=float))
    return {
        "estado": estados,
        "demanda": np.vstack(pedidas),
        "disponible": np.vstack(abiertas),
        "capacidad": np.vstack(topes),
    }


def flujo_de(plan: pd.DataFrame, rutas: pd.DataFrame) -> np.ndarray:
    """planned_flow alineado con el orden de routes.csv."""
    flujo = plan.set_index("route_id")["planned_flow"]
    if not flujo.index.is_unique or set(flujo.index) != set(rutas["route_id"]):
        raise RuntimeError("El plan debe tener exactamente un flujo por ruta")
    return rutas["route_id"].map(flujo).to_numpy(dtype=float)


# --- Versión pandas: una semana en una tabla legible ---------------------------------

def operar_semana(plan, rutas, zonas, pedida, capacidad, inventario, tol=TOL):
    envio = rutas[["route_id", "origin", "destination", "unit_cost"]].copy()
    envio["planificado"] = flujo_de(plan, rutas)
    envio["capacidad_efectiva"] = np.asarray(capacidad, dtype=float)
    envio["despachado"] = np.minimum(envio["planificado"], envio["capacidad_efectiva"])

    zonas_idx = zonas.set_index("destination")
    cuadro = pd.DataFrame(index=zonas_idx.index)
    cuadro["demanda"] = pd.Series(np.asarray(pedida, dtype=float), index=zonas["destination"].to_numpy())
    cuadro["inventario_inicial"] = inventario.reindex(cuadro.index).astype(float)
    cuadro["recepcion"] = envio.groupby("destination")["despachado"].sum().reindex(cuadro.index).fillna(0.0)
    cuadro["existencias"] = cuadro["inventario_inicial"] + cuadro["recepcion"]
    cuadro["atendido"] = np.minimum(cuadro["existencias"], cuadro["demanda"])
    cuadro["faltante"] = cuadro["demanda"] - cuadro["atendido"]
    cuadro["sobrante"] = cuadro["existencias"] - cuadro["atendido"]
    cuadro["inventario"] = np.minimum(cuadro["sobrante"], zonas_idx["storage_capacity"])
    cuadro["descarte"] = np.maximum(cuadro["sobrante"] - zonas_idx["storage_capacity"], 0.0)

    if cuadro.isna().any().any():
        raise RuntimeError("Apareció un valor faltante en el balance semanal")
    if (cuadro[["demanda", "recepcion", "atendido", "faltante", "inventario", "descarte"]] < -tol).any().any():
        raise RuntimeError("Apareció un valor negativo en el balance semanal")
    if (cuadro["inventario"] > zonas_idx["storage_capacity"] + tol).any():
        raise RuntimeError("El inventario supera la capacidad de almacenamiento")
    if not np.allclose(cuadro["atendido"] + cuadro["faltante"], cuadro["demanda"], rtol=0, atol=tol):
        raise RuntimeError("La demanda atendida más el faltante no cubre la demanda")
    if not np.allclose(cuadro["atendido"] + cuadro["sobrante"], cuadro["existencias"], rtol=0, atol=tol):
        raise RuntimeError("Lo atendido más el sobrante no coincide con las existencias")
    if not np.allclose(cuadro["inventario"] + cuadro["descarte"], cuadro["sobrante"], rtol=0, atol=tol):
        raise RuntimeError("Inventario más descarte no coincide con el sobrante")

    costo_transporte = float((envio["despachado"] * envio["unit_cost"]).sum())
    costo_faltante = float((cuadro["faltante"] * zonas_idx["shortage_penalty"]).sum())
    costo_almacen = float((cuadro["inventario"] * zonas_idx["holding_cost"]).sum())
    costo_descarte = float((cuadro["descarte"] * zonas_idx["waste_cost"]).sum())
    costos = pd.Series({
        "transporte": costo_transporte,
        "faltante": costo_faltante,
        "almacen": costo_almacen,
        "descarte": costo_descarte,
        "total": costo_transporte + costo_faltante + costo_almacen + costo_descarte,
    })
    return envio, cuadro, costos, cuadro["inventario"].copy()


def operar(plan, rutas, zonas, futuro) -> pd.DataFrame:
    """Recorre un futuro con la versión pandas y devuelve una fila por semana."""
    inventario = zonas.set_index("destination")["initial_inventory"].astype(float)
    filas = []
    for t, estado in enumerate(futuro["estado"]):
        _envio, cuadro, costos, inventario = operar_semana(
            plan, rutas, zonas, futuro["demanda"][t], futuro["capacidad"][t], inventario
        )
        filas.append({
            "semana": t + 1,
            "estado": estado,
            "demanda": float(cuadro["demanda"].sum()),
            "atendido": float(cuadro["atendido"].sum()),
            "faltante": float(cuadro["faltante"].sum()),
            "descarte": float(cuadro["descarte"].sum()),
            "inventario": float(inventario.sum()),
            "costo_transporte": float(costos["transporte"]),
            "costo_faltante": float(costos["faltante"]),
            "costo_almacen": float(costos["almacen"]),
            "costo_descarte": float(costos["descarte"]),
            "costo": float(costos["total"]),
        })
    return pd.DataFrame(filas)


def resumir_operacion(semanal: pd.DataFrame) -> dict:
    """Las métricas de `evaluar_plan` calculadas desde la tabla semanal de `operar`."""
    pedida = float(semanal["demanda"].sum())
    con_faltante = semanal["faltante"] > 1e-9
    return {
        "costo": float(semanal["costo"].sum()),
        "servicio": float(semanal["atendido"].sum()) / pedida if pedida > 0 else np.nan,
        "faltante": float(semanal["faltante"].sum()),
        "probabilidad_faltante": float(con_faltante.any()),
        "fraccion_semanas_faltante": float(con_faltante.mean()),
        "inventario": float(semanal["inventario"].mean()),
        "descarte": float(semanal["descarte"].sum()),
        "costo_transporte": float(semanal["costo_transporte"].sum()),
        "costo_faltante": float(semanal["costo_faltante"].sum()),
        "costo_almacen": float(semanal["costo_almacen"].sum()),
        "costo_descarte": float(semanal["costo_descarte"].sum()),
        "demanda": pedida,
        "atendido": float(semanal["atendido"].sum()),
    }


# --- Versión NumPy: la de la campaña ----------------------------------------------------

def red_logistica(rutas, zonas) -> dict:
    indice = {zona: i for i, zona in enumerate(zonas["destination"])}
    return {
        "zona": rutas["destination"].map(indice).to_numpy(),
        "costo": rutas["unit_cost"].to_numpy(dtype=float),
        "penalizacion": zonas["shortage_penalty"].to_numpy(dtype=float),
        "almacenaje": zonas["holding_cost"].to_numpy(dtype=float),
        "descarte": zonas["waste_cost"].to_numpy(dtype=float),
        "capacidad_deposito": zonas["storage_capacity"].to_numpy(dtype=float),
        "inventario_inicial": zonas["initial_inventory"].to_numpy(dtype=float),
    }


def evaluar_plan(flujo, futuro, red, registrar=False) -> dict:
    """Evalúa un plan fijo sobre un futuro. No modifica `futuro` ni `red`.

    El nivel de servicio es sum(atendido) / sum(demanda) en las 26 semanas; si la demanda
    total es cero no está definido y se devuelve NaN (la campaña lo rechaza en `chequear`).
    Con `registrar=True` agrega las matrices semana x zona y semana x ruta para auditar balances.
    """
    n_zonas = len(red["inventario_inicial"])
    inventario = red["inventario_inicial"].copy()
    costo = atendido = pedida = faltante = descarte = stock = 0.0
    c_transporte = c_faltante = c_almacen = c_descarte = 0.0
    semanas_con_faltante = 0
    traza = {k: [] for k in ("despacho", "inicial", "recepcion", "atendido", "faltante", "inventario", "descarte")}
    for t in range(len(futuro["estado"])):
        enviado = np.minimum(flujo, futuro["capacidad"][t])
        recepcion = np.zeros(n_zonas)
        np.add.at(recepcion, red["zona"], enviado)
        demanda_t = futuro["demanda"][t]
        existencias = inventario + recepcion
        cubierto = np.minimum(existencias, demanda_t)
        perdido = demanda_t - cubierto
        sobrante = existencias - cubierto
        if registrar:
            traza["inicial"].append(inventario.copy())
        inventario = np.minimum(sobrante, red["capacidad_deposito"])
        tirado = np.maximum(sobrante - red["capacidad_deposito"], 0.0)
        transporte_t = enviado @ red["costo"]
        faltante_t = perdido @ red["penalizacion"]
        almacen_t = inventario @ red["almacenaje"]
        descarte_t = tirado @ red["descarte"]
        costo += float(transporte_t + faltante_t + almacen_t + descarte_t)
        c_transporte += float(transporte_t)
        c_faltante += float(faltante_t)
        c_almacen += float(almacen_t)
        c_descarte += float(descarte_t)
        atendido += float(cubierto.sum())
        pedida += float(demanda_t.sum())
        faltante += float(perdido.sum())
        descarte += float(tirado.sum())
        stock += float(inventario.sum())
        if perdido.sum() > 1e-9:
            semanas_con_faltante += 1
        if registrar:
            for clave, valor in (("despacho", enviado), ("recepcion", recepcion), ("atendido", cubierto),
                                 ("faltante", perdido), ("inventario", inventario), ("descarte", tirado)):
                traza[clave].append(np.array(valor, dtype=float))
    horizonte = len(futuro["estado"])
    resultado = {
        "costo": costo,
        "servicio": atendido / pedida if pedida > 0 else np.nan,
        "faltante": faltante,
        "probabilidad_faltante": float(semanas_con_faltante > 0),
        "fraccion_semanas_faltante": semanas_con_faltante / horizonte,
        "inventario": stock / horizonte,
        "descarte": descarte,
        "costo_transporte": c_transporte,
        "costo_faltante": c_faltante,
        "costo_almacen": c_almacen,
        "costo_descarte": c_descarte,
        "demanda": pedida,
        "atendido": atendido,
    }
    if registrar:
        resultado["traza"] = {clave: np.vstack(valores) for clave, valores in traza.items()}
    return resultado


def campana(generadores, matriz, rutas, zonas, parametros, flujos: dict, inicio: int = 0):
    """Una trayectoria por generador, compartida por todas las políticas de `flujos`.

    `inicio` es el número de la primera réplica, para correr piloto y resto por separado
    sin cambiar qué generador corresponde a cada réplica.
    """
    red = red_logistica(rutas, zonas)
    filas, estados = [], []
    for i, rng in enumerate(generadores):
        futuro = entorno(rng, matriz, rutas, zonas, parametros)
        fila = {"replica": inicio + i, "demanda": float(futuro["demanda"].sum())}
        for politica, flujo in flujos.items():
            metricas = evaluar_plan(flujo, futuro, red)
            metricas.pop("demanda")
            fila.update({f"{clave}_{politica}": valor for clave, valor in metricas.items()})
        filas.append(fila)
        estados.append(futuro["estado"])
    return pd.DataFrame(filas), estados


def chequear(tabla: pd.DataFrame, politicas=POLITICAS, tol: float = TOL) -> None:
    """Invariantes de cada réplica. Falla si hay NaN o valores imposibles."""
    if tabla.isna().any().any():
        raise AssertionError("Hay métricas NaN en la campaña")
    assert (tabla["demanda"] > 0).all()
    for politica in politicas:
        assert tabla[f"servicio_{politica}"].between(0, 1).all()
        for clave in ("costo", "faltante", "descarte", "inventario", "costo_transporte",
                      "costo_faltante", "costo_almacen", "costo_descarte"):
            assert (tabla[f"{clave}_{politica}"] >= -tol).all(), clave
        assert tabla[f"fraccion_semanas_faltante_{politica}"].between(0, 1).all()
        assert set(tabla[f"probabilidad_faltante_{politica}"].unique()) <= {0.0, 1.0}
        componentes = sum(tabla[f"costo_{c}_{politica}"] for c in ("transporte", "faltante", "almacen", "descarte"))
        assert np.allclose(componentes, tabla[f"costo_{politica}"], rtol=0, atol=1e-6)
        assert np.allclose(tabla[f"atendido_{politica}"] + tabla[f"faltante_{politica}"], tabla["demanda"], rtol=0, atol=1e-6)


def intervalo(diferencia, nivel: float = 0.95):
    """Media, error estándar e IC t de Student con n-1 grados de libertad."""
    diferencia = np.asarray(diferencia, dtype=float)
    if not np.isfinite(diferencia).all():
        raise ValueError("Hay diferencias no finitas")
    n = len(diferencia)
    media = float(np.mean(diferencia))
    error = float(np.std(diferencia, ddof=1) / np.sqrt(n))
    critico = float(student_t.ppf(0.5 + nivel / 2, n - 1))
    return media, error, media - critico * error, media + critico * error


def comparacion_emparejada(resultados: pd.DataFrame, metricas=METRICAS) -> pd.DataFrame:
    """Diferencia resguardo - nominal por réplica, con IC del 95 %."""
    filas = []
    for clave, nombre in metricas:
        diferencia = resultados[f"{clave}_resguardo"] - resultados[f"{clave}_nominal"]
        media, error, bajo, alto = intervalo(diferencia.to_numpy())
        filas.append({
            "metrica": nombre,
            "nominal": float(resultados[f"{clave}_nominal"].mean()),
            "resguardo": float(resultados[f"{clave}_resguardo"].mean()),
            "diferencia": media,
            "error_estandar": error,
            "ic_inferior": bajo,
            "ic_superior": alto,
        })
    return pd.DataFrame(filas)


def ocupacion(estados: list[list[str]], orden=ESTADOS) -> pd.Series:
    """Semanas totales en cada estado sumando todas las trayectorias."""
    conteo = pd.Series([e for trayectoria in estados for e in trayectoria]).value_counts()
    return conteo.reindex(list(orden), fill_value=0).astype(int)
