"""Modelo primal de transporte con faltante penalizado (Parte I).

min  sum c_ij x_ij + sum p_j s_j
s.a. sum_j x_ij <= a_i,  x_ij <= u_ij,  sum_i x_ij + s_j = d_j,  x, s >= 0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

from .datos import sha256

TOL = 1e-7

ESTADOS_SOLVER = {
    pywraplp.Solver.OPTIMAL: "OPTIMAL",
    pywraplp.Solver.FEASIBLE: "FEASIBLE",
    pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
    pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
    pywraplp.Solver.ABNORMAL: "ABNORMAL",
    pywraplp.Solver.MODEL_INVALID: "MODEL_INVALID",
    pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
}

COLUMNAS_POLITICA = ["route_id", "origin", "destination", "planned_flow", "capacity", "unit_cost", "policy"]


class SolverError(RuntimeError):
    """GLOP no terminó en un óptimo."""

    def __init__(self, estado: str, nombre: str):
        super().__init__(f"{nombre or 'modelo'}: GLOP terminó con estado {estado}")
        self.estado = estado


@dataclass
class SolucionTransporte:
    nombre: str
    estado: str
    objetivo: float
    flujos: pd.DataFrame
    faltantes: pd.DataFrame
    solver: pywraplp.Solver


def techo(factor: float, serie: pd.Series) -> pd.Series:
    """ceil(factor * valor) por elemento.

    Se redondea a 8 decimales antes del techo porque 1.10 * 50 vale 55.000000000000007
    en punto flotante y el techo daría 56 en lugar de 55.
    """
    return pd.Series(
        {clave: float(math.ceil(round(factor * float(valor), 8))) for clave, valor in serie.items()},
        name=serie.name,
    )


def _serie_valida(serie: pd.Series, claves, nombre: str) -> pd.Series:
    claves = list(claves)
    faltan = [c for c in claves if c not in serie.index]
    if faltan:
        raise ValueError(f"{nombre}: faltan valores para {faltan}")
    valores = serie.loc[claves].astype(float)
    if not np.isfinite(valores.to_numpy()).all():
        raise ValueError(f"{nombre}: hay valores no finitos")
    if (valores < 0).any():
        raise ValueError(f"{nombre}: hay valores negativos")
    return valores


def resolver(
    routes: pd.DataFrame,
    destinations: pd.DataFrame,
    demanda: pd.Series,
    oferta: pd.Series,
    capacidad: pd.Series,
    nombre: str = "",
    permitir_faltante: bool = True,
) -> SolucionTransporte:
    """Construye y resuelve el LP con GLOP.

    `demanda` se indexa por zona, `oferta` por centro y `capacidad` por route_id.
    Con `permitir_faltante=False` las variables s_j quedan fijas en cero, lo que sirve
    para mostrar que sin faltante explícito el modelo puede ser infactible.
    """
    demanda = _serie_valida(demanda, destinations["destination"], "demanda")
    capacidad = _serie_valida(capacidad, routes["route_id"], "capacidad")
    oferta = _serie_valida(oferta, oferta.index, "oferta")
    if set(routes["origin"]) - set(oferta.index):
        raise ValueError("oferta: hay rutas que salen de un centro sin oferta declarada")
    for columna in ("unit_cost",):
        if not np.isfinite(routes[columna].to_numpy(dtype=float)).all() or (routes[columna] < 0).any():
            raise ValueError(f"routes.{columna}: hay valores no finitos o negativos")
    penalizacion = destinations.set_index("destination")["shortage_penalty"].astype(float)
    if not np.isfinite(penalizacion.to_numpy()).all() or (penalizacion < 0).any():
        raise ValueError("shortage_penalty: hay valores no finitos o negativos")

    modelo = pywraplp.Solver.CreateSolver("GLOP")
    if modelo is None:
        raise SolverError("NO_CREADO", nombre)
    x = {
        row.route_id: modelo.NumVar(0, modelo.infinity(), f"x_{row.route_id}")
        for row in routes.itertuples(index=False)
    }
    tope_faltante = modelo.infinity() if permitir_faltante else 0.0
    s = {zone: modelo.NumVar(0, tope_faltante, f"s_{zone}") for zone in destinations["destination"]}

    for origin in oferta.index:
        salidas = routes.loc[routes["origin"] == origin, "route_id"]
        modelo.Add(sum(x[rid] for rid in salidas) <= float(oferta.loc[origin]), f"oferta_{origin}")
    for row in routes.itertuples(index=False):
        modelo.Add(x[row.route_id] <= float(capacidad.loc[row.route_id]), f"capacidad_{row.route_id}")
    for zone in destinations["destination"]:
        entradas = routes.loc[routes["destination"] == zone, "route_id"]
        modelo.Add(sum(x[rid] for rid in entradas) + s[zone] == float(demanda.loc[zone]), f"demanda_{zone}")
    modelo.Minimize(
        sum(row.unit_cost * x[row.route_id] for row in routes.itertuples(index=False))
        + sum(float(penalizacion.loc[zone]) * s[zone] for zone in s)
    )

    estado = ESTADOS_SOLVER.get(modelo.Solve(), "DESCONOCIDO")
    if estado != "OPTIMAL":
        raise SolverError(estado, nombre)

    flujos = routes[["route_id", "origin", "destination", "unit_cost"]].copy()
    flujos["capacity"] = flujos["route_id"].map(capacidad).astype(float)
    flujos["flujo"] = [x[rid].solution_value() for rid in flujos["route_id"]]
    faltantes = destinations[["destination", "shortage_penalty"]].copy()
    faltantes["demanda"] = faltantes["destination"].map(demanda).astype(float)
    faltantes["faltante"] = [s[zone].solution_value() for zone in faltantes["destination"]]
    return SolucionTransporte(nombre, estado, modelo.Objective().Value(), flujos, faltantes, modelo)


def verificar(
    solucion: SolucionTransporte,
    routes: pd.DataFrame,
    destinations: pd.DataFrame,
    demanda: pd.Series,
    oferta: pd.Series,
    capacidad: pd.Series,
    tol: float = TOL,
) -> dict:
    """Recalcula objetivo, balances y cotas desde los flujos y los datos del escenario.

    Sólo usa de la solución las columnas `flujo` y `faltante`: costos, capacidades,
    ofertas y demandas salen de los datos. Falla con AssertionError si algún control no pasa.
    """
    flujo = solucion.flujos.set_index("route_id")["flujo"].astype(float)
    faltante = solucion.faltantes.set_index("destination")["faltante"].astype(float)
    assert list(flujo.index) == list(routes["route_id"]), "La solución no tiene exactamente una fila por ruta"
    assert list(faltante.index) == list(destinations["destination"]), "La solución no tiene una fila por zona"
    assert np.isfinite(flujo.to_numpy()).all() and np.isfinite(faltante.to_numpy()).all(), "Hay valores no finitos"

    r = routes.set_index("route_id")
    z = destinations.set_index("destination")
    transporte = float((flujo * r["unit_cost"]).sum())
    penalizacion = float((faltante * z["shortage_penalty"]).sum())
    objetivo = transporte + penalizacion

    uso = flujo.groupby(r["origin"]).sum()
    centros = pd.DataFrame({"oferta": oferta.astype(float), "uso": uso.reindex(oferta.index).fillna(0.0)})
    centros["holgura"] = centros["oferta"] - centros["uso"]

    rutas = pd.DataFrame({
        "flujo": flujo,
        "capacidad": capacidad.reindex(flujo.index).astype(float),
    })
    rutas["holgura"] = rutas["capacidad"] - rutas["flujo"]

    recibido = flujo.groupby(r["destination"]).sum()
    zonas = pd.DataFrame({
        "demanda": demanda.reindex(z.index).astype(float),
        "recibido": recibido.reindex(z.index).fillna(0.0),
        "faltante": faltante,
    })
    zonas["residuo"] = zonas["recibido"] + zonas["faltante"] - zonas["demanda"]

    controles = pd.DataFrame([
        ("Objetivo recalculado = objetivo del solver", abs(objetivo - solucion.objetivo)),
        ("Balance por zona |recibido + faltante - demanda|", float(zonas["residuo"].abs().max())),
        ("Exceso sobre la oferta de un centro", max(0.0, float(-centros["holgura"].min()))),
        ("Exceso sobre la capacidad de una ruta", max(0.0, float(-rutas["holgura"].min()))),
        ("Flujo negativo", max(0.0, float(-flujo.min()))),
        ("Faltante negativo", max(0.0, float(-faltante.min()))),
    ], columns=["control", "violacion_maxima"])
    controles["cumple"] = controles["violacion_maxima"] <= tol
    fallas = controles.loc[~controles["cumple"], "control"].tolist()
    assert not fallas, f"{solucion.nombre}: no cumple {fallas}"
    return {
        "objetivo": objetivo,
        "transporte": transporte,
        "penalizacion": penalizacion,
        "centros": centros,
        "rutas": rutas,
        "zonas": zonas,
        "controles": controles,
    }


def certificado(solucion: SolucionTransporte, tol: float = TOL) -> dict:
    """Certificado de optimalidad a partir de duales y costos reducidos de GLOP.

    Convención de OR-Tools para minimizar: el dual de una restricción es la derivada del
    objetivo respecto de su lado derecho. Una restricción <= activa tiene dual <= 0, una
    variable en su cota inferior tiene costo reducido >= 0 y una variable entre cotas lo
    tiene nulo. El objetivo dual es sum(dual * cota activa) + sum(costo reducido * cota activa).
    """
    solver = solucion.solver
    inf = solver.infinity()
    base = {
        solver.FREE: "libre",
        solver.AT_LOWER_BOUND: "cota inferior",
        solver.AT_UPPER_BOUND: "cota superior",
        solver.FIXED_VALUE: "fijada",
        solver.BASIC: "básica",
    }

    def cota_activa(lb, ub, multiplicador):
        if lb > -inf and ub < inf and abs(lb - ub) <= 1e-12:
            return ub
        if multiplicador > 0:
            return lb if lb > -inf else math.nan
        if multiplicador < 0:
            return ub if ub < inf else math.nan
        return 0.0

    dual_obj = 0.0
    filas_rest = []
    actividad = {}
    for variable in solver.variables():
        actividad[variable.name()] = variable.solution_value()
    for restriccion in solver.constraints():
        lb, ub, dual = restriccion.lb(), restriccion.ub(), restriccion.dual_value()
        dual_obj += dual * cota_activa(lb, ub, dual) if abs(dual) > 0 else 0.0
        nivel = sum(restriccion.GetCoefficient(v) * actividad[v.name()] for v in solver.variables())
        if abs(lb - ub) <= 1e-12:
            holgura, tipo, signo_ok = nivel - ub, "=", True
        elif ub < inf:
            holgura, tipo, signo_ok = ub - nivel, "<=", dual <= tol
        else:
            holgura, tipo, signo_ok = nivel - lb, ">=", dual >= -tol
        filas_rest.append({
            "restriccion": restriccion.name(),
            "tipo": tipo,
            "dual": dual,
            "holgura": holgura,
            "signo_dual_ok": signo_ok,
            "holgura_complementaria": abs(holgura) <= tol or abs(dual) <= tol,
            "base": base.get(restriccion.basis_status(), str(restriccion.basis_status())),
        })

    filas_var = []
    for variable in solver.variables():
        lb, ub, rc, valor = variable.lb(), variable.ub(), variable.reduced_cost(), variable.solution_value()
        dual_obj += rc * cota_activa(lb, ub, rc) if abs(rc) > 0 else 0.0
        en_inferior = abs(valor - lb) <= tol
        en_superior = ub < inf and abs(valor - ub) <= tol
        if en_inferior and en_superior:
            ok = True
        elif en_inferior:
            ok = rc >= -tol
        elif en_superior:
            ok = rc <= tol
        else:
            ok = abs(rc) <= tol
        filas_var.append({
            "variable": variable.name(),
            "valor": valor,
            "costo_reducido": rc,
            "holgura_complementaria": ok,
            "base": base.get(variable.basis_status(), str(variable.basis_status())),
        })

    variables = pd.DataFrame(filas_var)
    restricciones = pd.DataFrame(filas_rest)
    primal = solver.Objective().Value()
    resumen = {
        "objetivo_primal": primal,
        "objetivo_dual": dual_obj,
        "brecha": abs(primal - dual_obj),
        "verify_solution_glop": bool(solver.VerifySolution(tol, False)),
        "signos_duales_ok": bool(restricciones["signo_dual_ok"].all()),
        "holgura_complementaria_ok": bool(
            variables["holgura_complementaria"].all() and restricciones["holgura_complementaria"].all()
        ),
        "iteraciones": solver.iterations(),
    }
    resumen["certificado_ok"] = bool(
        resumen["brecha"] <= tol and resumen["signos_duales_ok"] and resumen["holgura_complementaria_ok"]
    )
    return {"resumen": resumen, "variables": variables, "restricciones": restricciones}


def comparar_flujos(solucion: SolucionTransporte, base: SolucionTransporte) -> pd.DataFrame:
    tabla = solucion.flujos[["route_id", "origin", "destination", "capacity", "flujo"]].merge(
        base.flujos[["route_id", "flujo"]], on="route_id", suffixes=("", "_nominal")
    )
    tabla["diferencia"] = tabla["flujo"] - tabla["flujo_nominal"]
    return tabla


def tabla_politica(solucion: SolucionTransporte, politica: str, decimales: int = 9) -> pd.DataFrame:
    """Tabla puente. GLOP devuelve ruido de punto flotante (3.999999999999998, 4e-15): se
    redondea a `decimales`, muy por debajo de la tolerancia 1e-7, para serializar siempre igual."""
    tabla = solucion.flujos.rename(columns={"flujo": "planned_flow"})
    tabla["planned_flow"] = tabla["planned_flow"].round(decimales) + 0.0
    tabla["policy"] = politica
    return tabla[COLUMNAS_POLITICA].reset_index(drop=True)


def validar_politica(
    tabla: pd.DataFrame,
    routes: pd.DataFrame,
    origins: pd.DataFrame,
    tol: float = TOL,
) -> pd.DataFrame:
    """Esquema, una fila por ruta, metadatos iguales a routes.csv y cotas nominales."""
    faltan = [c for c in COLUMNAS_POLITICA[:-1] if c not in tabla.columns]
    if faltan:
        raise ValueError(f"Política: faltan columnas {faltan}")
    if not tabla["route_id"].is_unique:
        raise ValueError("Política: route_id repetido")
    esperadas, presentes = set(routes["route_id"]), set(tabla["route_id"])
    if presentes != esperadas:
        raise ValueError(
            f"Política: faltan {sorted(esperadas - presentes)}; sobran {sorted(presentes - esperadas)}"
        )
    tabla = tabla.set_index("route_id").loc[routes["route_id"]].reset_index()
    flujo = tabla["planned_flow"].to_numpy(dtype=float)
    if not np.isfinite(flujo).all():
        raise ValueError("Política: planned_flow no finito")
    if (flujo < -tol).any():
        raise ValueError("Política: planned_flow negativo")
    for columna in ("origin", "destination"):
        if not (tabla[columna].to_numpy() == routes[columna].to_numpy()).all():
            raise ValueError(f"Política: {columna} no coincide con routes.csv")
    for columna in ("capacity", "unit_cost"):
        if not np.allclose(tabla[columna].to_numpy(dtype=float), routes[columna].to_numpy(dtype=float), rtol=0, atol=tol):
            raise ValueError(f"Política: {columna} no coincide con routes.csv")
    if (flujo > routes["capacity"].to_numpy(dtype=float) + tol).any():
        raise ValueError("Política: planned_flow supera la capacidad nominal de una ruta")
    uso = tabla.groupby("origin")["planned_flow"].sum()
    oferta = origins.set_index("origin")["supply"].astype(float)
    if (uso.reindex(oferta.index).fillna(0.0) > oferta + tol).any():
        raise ValueError("Política: el despacho planificado supera la oferta de un centro")
    return tabla


def exportar_politica(
    solucion: SolucionTransporte,
    politica: str,
    ruta: str | Path,
    routes: pd.DataFrame,
    origins: pd.DataFrame,
) -> str:
    """Valida, escribe el CSV puente y devuelve su SHA-256."""
    tabla = tabla_politica(solucion, politica)
    validar_politica(tabla, routes, origins)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ruta, index=False, lineterminator="\n")
    validar_politica(pd.read_csv(ruta), routes, origins)
    return sha256(ruta)


def cargar_politica(ruta: str | Path, routes: pd.DataFrame, origins: pd.DataFrame) -> pd.DataFrame:
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecute primero notebooks/part1_primal.ipynb")
    return validar_politica(pd.read_csv(ruta), routes, origins)
