from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.datos import DatosInvalidos, OUTPUTS_DIR, cargar_datos
from src.transporte import (
    SolverError, cargar_politica, certificado, exportar_politica, resolver, tabla_politica, techo,
    validar_politica, verificar,
)

from conftest import TOL, cerca

OBJETIVOS = {"nominal": 828.0, "S1": 1453.0, "S2": 849.5, "S3": 1305.0, "resguardo": 907.0}


def copiar(sol):
    return replace(sol, flujos=sol.flujos.copy(), faltantes=sol.faltantes.copy())


def mini(oferta, capacidad, demanda, con_faltante=True, costo=4.0, penalizacion=80.0):
    rutas = pd.DataFrame({"route_id": ["N-CAP"], "origin": ["Norte"], "destination": ["Capital"],
                          "unit_cost": [costo], "capacity": [capacidad]})
    zonas = pd.DataFrame({"destination": ["Capital"], "shortage_penalty": [penalizacion]})
    args = (pd.Series({"Capital": demanda}), pd.Series({"Norte": oferta}), pd.Series({"N-CAP": capacidad}))
    return rutas, zonas, args, resolver(rutas, zonas, *args, permitir_faltante=con_faltante)


# --- Casos manuales ------------------------------------------------------------------

def test_caso_factible():
    rutas, zonas, args, sol = mini(10, 10, 6)
    cerca([sol.flujos["flujo"].iloc[0], sol.faltantes["faltante"].iloc[0], sol.objetivo], [6, 0, 24])
    verificar(sol, rutas, zonas, *args)


def test_caso_infactible_sin_faltante():
    with pytest.raises(SolverError) as error:
        mini(10, 3, 6, con_faltante=False)
    assert error.value.estado == "INFEASIBLE"


def test_mismo_caso_con_faltante_es_factible():
    _, _, _, sol = mini(10, 3, 6)
    cerca([sol.flujos["flujo"].iloc[0], sol.faltantes["faltante"].iloc[0], sol.objetivo], [3, 3, 252])


def test_caso_borde_llena_las_cotas():
    rutas, zonas, args, sol = mini(6, 6, 6)
    cerca([sol.flujos["flujo"].iloc[0], sol.faltantes["faltante"].iloc[0]], [6, 0])
    control = verificar(sol, rutas, zonas, *args)
    cerca([control["centros"]["holgura"].iloc[0], control["rutas"]["holgura"].iloc[0]], [0, 0])


# --- Caso real y escenarios -------------------------------------------------------------

@pytest.mark.parametrize("nombre", list(OBJETIVOS))
def test_objetivo_y_factibilidad(nombre, soluciones, datos):
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones[nombre]
    assert sol.estado == "OPTIMAL"
    cerca(sol.objetivo, OBJETIVOS[nombre])
    control = verificar(sol, routes, destinations, dem, of, cap)
    assert control["controles"]["cumple"].all()
    cerca(control["objetivo"], sol.objetivo)


@pytest.mark.parametrize("nombre", list(OBJETIVOS))
def test_restricciones_explicitas(nombre, soluciones, datos):
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones[nombre]
    flujo = sol.flujos.set_index("route_id")["flujo"]
    faltante = sol.faltantes.set_index("destination")["faltante"]
    assert np.isfinite(flujo).all() and np.isfinite(faltante).all()
    assert (flujo >= -TOL).all() and (faltante >= -TOL).all()
    assert (flujo <= cap.loc[flujo.index] + TOL).all()
    uso = flujo.groupby(routes.set_index("route_id")["origin"]).sum()
    assert (uso <= of.loc[uso.index] + TOL).all()
    recibido = flujo.groupby(routes.set_index("route_id")["destination"]).sum()
    cerca((recibido + faltante).loc[dem.index], dem)
    costo = (flujo * routes.set_index("route_id")["unit_cost"]).sum() + (
        faltante * destinations.set_index("destination")["shortage_penalty"]).sum()
    cerca(costo, OBJETIVOS[nombre])


def test_faltantes_esperados(soluciones):
    for nombre, faltante in {"nominal": 0, "S1": 9, "S2": 0, "S3": 8.5, "resguardo": 0}.items():
        cerca(soluciones[nombre][0].faltantes["faltante"].sum(), faltante)


def test_datos_modificados_de_los_escenarios(soluciones):
    assert soluciones["S1"][1].tolist() == [55, 47, 42, 51, 39]
    assert soluciones["resguardo"][1].tolist() == [53, 45, 40, 49, 37]
    cerca(soluciones["S2"][3].loc["C-OES"], 24.5)
    cerca(soluciones["S3"][2].to_numpy(), [67.5, 72.0, 63.0])


def test_techo_tolera_error_de_punto_flotante():
    serie = pd.Series({"a": 50.0, "b": 42.0, "c": 20.0, "d": 35.0})
    assert techo(1.10, serie).tolist() == [55.0, 47.0, 22.0, 39.0]
    assert 1.10 * 50 > 55
    assert techo(1.05, pd.Series({"a": 36.0})).tolist() == [38.0]


def test_certificado_nominal(soluciones):
    resumen = certificado(soluciones["nominal"][0])["resumen"]
    assert resumen["certificado_ok"] and resumen["verify_solution_glop"]
    assert resumen["brecha"] <= TOL


@pytest.mark.parametrize("nombre", list(OBJETIVOS))
def test_certificado_en_todos_los_escenarios(nombre, soluciones):
    assert certificado(soluciones[nombre][0])["resumen"]["certificado_ok"]


# --- Verificador independiente ---------------------------------------------------------

def test_verificador_detecta_cota_violada(soluciones, datos):
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones["nominal"]
    alterada = copiar(sol)
    alterada.flujos.loc[alterada.flujos["route_id"] == "C-OES", "flujo"] += 1.0
    with pytest.raises(AssertionError):
        verificar(alterada, routes, destinations, dem, of, cap)


def test_verificador_detecta_objetivo_incorrecto(soluciones, datos):
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones["nominal"]
    alterada = copiar(sol)
    alterada.objetivo += 1e-3
    with pytest.raises(AssertionError):
        verificar(alterada, routes, destinations, dem, of, cap)


def test_verificador_rechaza_nan(soluciones, datos):
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones["nominal"]
    alterada = copiar(sol)
    alterada.flujos.loc[0, "flujo"] = np.nan
    with pytest.raises(AssertionError):
        verificar(alterada, routes, destinations, dem, of, cap)


def test_optimo_alternativo_es_aceptado(soluciones, datos):
    """Hay óptimos múltiples: otro vector de flujos con el mismo costo también es válido."""
    _, destinations, routes = datos
    sol, dem, of, cap = soluciones["nominal"]
    alternativa = copiar(sol)
    f = alternativa.flujos.set_index("route_id")["flujo"]
    f["N-OES"] += 1
    f["S-OES"] -= 1
    f["S-EST"] += 1
    f["N-EST"] -= 1
    alternativa.flujos["flujo"] = f.to_numpy()
    assert not np.allclose(alternativa.flujos["flujo"], sol.flujos["flujo"])
    control = verificar(alternativa, routes, destinations, dem, of, cap)
    cerca(control["objetivo"], OBJETIVOS["nominal"])


# --- Entradas inválidas ------------------------------------------------------------------

@pytest.mark.parametrize("cambio", ["demanda_negativa", "capacidad_nan", "zona_faltante", "oferta_inf"])
def test_resolver_rechaza_entradas_invalidas(cambio, datos, entradas):
    _, destinations, routes = datos
    d, a, u = entradas["demanda"].copy(), entradas["oferta"].copy(), entradas["capacidad"].copy()
    if cambio == "demanda_negativa":
        d.iloc[0] = -1
    elif cambio == "capacidad_nan":
        u.iloc[0] = np.nan
    elif cambio == "zona_faltante":
        d = d.drop("Capital")
    elif cambio == "oferta_inf":
        a.iloc[0] = np.inf
    with pytest.raises(ValueError):
        resolver(routes, destinations, d, a, u)


def _copiar_datos(tmp_path):
    for nombre in ("origins.csv", "destinations.csv", "routes.csv"):
        (tmp_path / nombre).write_bytes((OUTPUTS_DIR.parent / "data" / nombre).read_bytes())


@pytest.mark.parametrize("archivo, cambio", [
    ("routes.csv", lambda t: t.drop(columns="capacity")),
    ("routes.csv", lambda t: t.assign(unit_cost=t["unit_cost"].where(t.index != 0, np.nan))),
    ("routes.csv", lambda t: t.assign(route_id=t["route_id"].where(t.index != 1, "N-CAP"))),
    ("routes.csv", lambda t: t.assign(origin=t["origin"].where(t.index != 0, "Oeste"))),
    ("routes.csv", lambda t: t.assign(capacity=t["capacity"].where(t.index != 0, -1.0))),
    ("routes.csv", lambda t: t.iloc[:-1]),
    ("origins.csv", lambda t: t.assign(supply=t["supply"].astype(object).where(t.index != 0, "mucho"))),
    ("origins.csv", lambda t: pd.concat([t, t.iloc[[0]]])),
    ("destinations.csv", lambda t: t.assign(nominal_demand=t["nominal_demand"].where(t.index != 0, np.inf))),
    ("destinations.csv", lambda t: t.assign(shortage_penalty=-t["shortage_penalty"])),
])
def test_cargar_datos_rechaza_archivos_invalidos(tmp_path, archivo, cambio):
    _copiar_datos(tmp_path)
    tabla = pd.read_csv(tmp_path / archivo)
    cambio(tabla).to_csv(tmp_path / archivo, index=False)
    with pytest.raises(DatosInvalidos):
        cargar_datos(tmp_path)


def test_cargar_datos_acepta_los_datos_del_proyecto(datos):
    origins, destinations, routes = datos
    assert len(origins) == 3 and len(destinations) == 5 and len(routes) == 15


# --- Archivo puente ----------------------------------------------------------------------

def test_exportar_y_cargar_politica(tmp_path, soluciones, datos):
    origins, _, routes = datos
    ruta = tmp_path / "plan.csv"
    huella = exportar_politica(soluciones["nominal"][0], "nominal", ruta, routes, origins)
    assert len(huella) == 64
    plan = cargar_politica(ruta, routes, origins)
    assert list(plan["route_id"]) == list(routes["route_id"])
    assert set(plan.columns) >= {"route_id", "origin", "destination", "planned_flow", "capacity", "unit_cost"}
    cerca((plan["planned_flow"] * plan["unit_cost"]).sum(), OBJETIVOS["nominal"])
    assert exportar_politica(soluciones["nominal"][0], "nominal", tmp_path / "otra.csv", routes, origins) == huella


@pytest.mark.parametrize("dano", ["duplicada", "faltante", "negativa", "sobre_capacidad", "metadato", "sobre_oferta", "nan"])
def test_validar_politica_rechaza_archivos_danados(dano, soluciones, datos):
    origins, _, routes = datos
    tabla = tabla_politica(soluciones["nominal"][0], "nominal")
    if dano == "duplicada":
        tabla = pd.concat([tabla, tabla.iloc[[0]]])
    elif dano == "faltante":
        tabla = tabla.iloc[1:]
    elif dano == "negativa":
        tabla.loc[1, "planned_flow"] = -1.0
    elif dano == "sobre_capacidad":
        tabla.loc[1, "planned_flow"] = tabla.loc[1, "capacity"] + 1
    elif dano == "metadato":
        tabla.loc[0, "unit_cost"] = 99.0
    elif dano == "sobre_oferta":
        tabla.loc[tabla["route_id"] == "N-OES", "planned_flow"] = 28.0
    elif dano == "nan":
        tabla.loc[0, "planned_flow"] = np.nan
    with pytest.raises(ValueError):
        validar_politica(tabla, routes, origins)


@pytest.mark.parametrize("archivo, objetivo", [("part1_solution.csv", 828.0), ("part1_solution_buffer.csv", 907.0)])
def test_archivos_puente_exportados(archivo, objetivo, datos):
    ruta = OUTPUTS_DIR / archivo
    if not ruta.exists():
        pytest.skip("Ejecute notebooks/part1_primal.ipynb para generar los archivos puente")
    origins, _, routes = datos
    plan = cargar_politica(ruta, routes, origins)
    cerca((plan["planned_flow"] * plan["unit_cost"]).sum(), objetivo)
