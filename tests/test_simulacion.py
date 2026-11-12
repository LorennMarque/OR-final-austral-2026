import copy

import numpy as np
import pandas as pd
import pytest

from src import markov as mk
from src import simulacion as sim
from src.datos import DATA_DIR

from conftest import TOL, cerca


@pytest.fixture(scope="module")
def red(datos):
    _, destinations, routes = datos
    return sim.red_logistica(routes, destinations)


@pytest.fixture(scope="module")
def futuro(datos, matriz, parametros):
    _, destinations, routes = datos
    return sim.entorno(sim.crear_generadores(sim.SEMILLA_MAESTRA, 1)[0], matriz, routes, destinations, parametros)


@pytest.fixture(scope="module")
def campana_completa(datos, matriz, parametros, flujos):
    _, destinations, routes = datos
    generadores = sim.crear_generadores(sim.SEMILLA_MAESTRA, sim.N_CAMPANA)
    piloto, e1 = sim.campana(generadores[:sim.N_PILOTO], matriz, routes, destinations, parametros, flujos, 0)
    resto, e2 = sim.campana(generadores[sim.N_PILOTO:], matriz, routes, destinations, parametros, flujos, sim.N_PILOTO)
    return pd.concat([piloto, resto], ignore_index=True), e1 + e2


def futuro_fijo(routes, destinations, horizonte=26, demanda=None, capacidad=None):
    demanda = destinations["nominal_demand"].to_numpy() if demanda is None else np.asarray(demanda, float)
    capacidad = routes["capacity"].to_numpy() if capacidad is None else np.asarray(capacidad, float)
    return {
        "estado": ["Normal"] * horizonte,
        "demanda": np.tile(demanda.astype(float), (horizonte, 1)),
        "disponible": np.ones((horizonte, len(routes)), dtype=int),
        "capacidad": np.tile(capacidad.astype(float), (horizonte, 1)),
    }


# --- Futuro aleatorio --------------------------------------------------------------------

def test_forma_del_futuro(futuro):
    assert len(futuro["estado"]) == sim.HORIZONTE == 26
    assert futuro["estado"][0] == "Disrupcion"
    assert futuro["demanda"].shape == (26, 5)
    assert futuro["disponible"].shape == (26, 15) and futuro["capacidad"].shape == (26, 15)
    assert set(futuro["estado"]) <= set(mk.ESTADOS)


def test_demandas_e_indicadores(futuro):
    assert np.isfinite(futuro["demanda"]).all() and (futuro["demanda"] >= 0).all()
    assert np.array_equal(futuro["demanda"], np.round(futuro["demanda"]))
    assert set(np.unique(futuro["disponible"])) <= {0, 1}


def test_capacidad_efectiva(futuro, datos, parametros):
    _, _, routes = datos
    multiplicador = parametros.loc[futuro["estado"], "capacity_multiplier"].to_numpy()[:, None]
    esperada = futuro["disponible"] * routes["capacity"].to_numpy()[None, :] * multiplicador
    cerca(futuro["capacidad"], esperada)


def test_bernoulli_extremos():
    rng = np.random.default_rng(1)
    assert sim.disponibilidad(rng, 1000, 1.0).all()
    assert not sim.disponibilidad(rng, 1000, 0.0).any()
    assert abs(sim.disponibilidad(rng, 200_000, 0.9).mean() - 0.9) < 0.005


def test_demanda_poisson_media():
    rng = np.random.default_rng(2)
    muestra = np.array([sim.demanda(rng, [50, 35], 1.2) for _ in range(20_000)])
    cerca(muestra.mean(axis=0), [60, 42], atol=0.3)


def test_cadena_simulada_reproduce_la_matriz(matriz):
    rng = np.random.default_rng(3)
    estados = sim.trayectoria_estados(rng, matriz, horizonte=200_000, inicial="Normal")
    frecuencias = mk.estimar_matriz(pd.DataFrame({"period": range(len(estados)), "state": estados}))[1]
    cerca(frecuencias.to_numpy(), matriz.to_numpy(), atol=0.02)


# --- Contabilidad semanal -----------------------------------------------------------------

@pytest.mark.parametrize("politica", ["nominal", "resguardo"])
def test_balances_semanales(politica, futuro, red, flujos):
    flujo = flujos[politica]
    r = sim.evaluar_plan(flujo, futuro, red, registrar=True)
    tr = r["traza"]
    for clave, matriz_t in tr.items():
        assert np.isfinite(matriz_t).all(), clave
    assert (tr["despacho"] <= flujo[None, :] + TOL).all()
    assert (tr["despacho"] <= futuro["capacidad"] + TOL).all()
    cerca(tr["despacho"], np.minimum(flujo[None, :], futuro["capacidad"]))
    recepcion = np.zeros_like(tr["recepcion"])
    for k, zona in enumerate(red["zona"]):
        recepcion[:, zona] += tr["despacho"][:, k]
    cerca(tr["recepcion"], recepcion)
    assert (tr["inventario"] >= -TOL).all()
    assert (tr["inventario"] <= red["capacidad_deposito"][None, :] + TOL).all()
    cerca(tr["inicial"][0], red["inventario_inicial"])
    cerca(tr["inicial"][1:], tr["inventario"][:-1])
    cerca(tr["inicial"] + tr["recepcion"], tr["atendido"] + tr["inventario"] + tr["descarte"])
    cerca(tr["atendido"] + tr["faltante"], futuro["demanda"])
    cerca(tr["faltante"], np.maximum(futuro["demanda"] - tr["inicial"] - tr["recepcion"], 0))
    sobrante = tr["inicial"] + tr["recepcion"] - tr["atendido"]
    cerca(tr["descarte"], np.maximum(sobrante - red["capacidad_deposito"][None, :], 0))


@pytest.mark.parametrize("politica", ["nominal", "resguardo"])
def test_componentes_del_costo(politica, futuro, red, flujos):
    r = sim.evaluar_plan(flujos[politica], futuro, red, registrar=True)
    tr = r["traza"]
    cerca(r["costo_transporte"], (tr["despacho"] @ red["costo"]).sum())
    cerca(r["costo_faltante"], (tr["faltante"] @ red["penalizacion"]).sum())
    cerca(r["costo_almacen"], (tr["inventario"] @ red["almacenaje"]).sum())
    cerca(r["costo_descarte"], (tr["descarte"] @ red["descarte"]).sum())
    cerca(r["costo"], r["costo_transporte"] + r["costo_faltante"] + r["costo_almacen"] + r["costo_descarte"])
    cerca(r["servicio"], tr["atendido"].sum() / futuro["demanda"].sum())
    cerca(r["inventario"], tr["inventario"].sum(axis=1).mean())
    cerca(r["fraccion_semanas_faltante"], (tr["faltante"].sum(axis=1) > 1e-9).mean())


def test_limite_determinista(datos, red, flujos):
    _, destinations, routes = datos
    r = sim.evaluar_plan(flujos["nominal"], futuro_fijo(routes, destinations), red, registrar=True)
    cerca([r["faltante"], r["descarte"], r["servicio"]], [0, 0, 1])
    cerca(r["traza"]["inventario"], np.tile(red["inventario_inicial"], (26, 1)))
    almacen = red["inventario_inicial"] @ red["almacenaje"]
    cerca(r["costo"], 26 * (828.0 + almacen))


def test_capacidad_cero_usa_solo_el_inventario_inicial(datos, red, flujos):
    _, destinations, routes = datos
    futuro = futuro_fijo(routes, destinations, capacidad=np.zeros(len(routes)))
    r = sim.evaluar_plan(flujos["nominal"], futuro, red, registrar=True)
    cerca(r["traza"]["atendido"][0], red["inventario_inicial"])
    cerca(r["traza"]["atendido"][1:], 0)
    cerca(r["costo_transporte"], 0)
    cerca(r["atendido"], red["inventario_inicial"].sum())


def test_inventario_tope_y_descarte(datos, red, flujos):
    _, destinations, routes = datos
    futuro = futuro_fijo(routes, destinations, demanda=np.zeros(5), horizonte=4)
    r = sim.evaluar_plan(flujos["resguardo"], futuro, red, registrar=True)
    cerca(r["traza"]["inventario"][-1], red["capacidad_deposito"])
    assert r["descarte"] > 0
    assert np.isnan(r["servicio"])


def test_chequear_rechaza_nan(campana_completa):
    tabla = campana_completa[0].head(3).copy()
    tabla.loc[0, "servicio_nominal"] = np.nan
    with pytest.raises(AssertionError):
        sim.chequear(tabla)


def test_evaluar_no_modifica_entradas(futuro, red, flujos):
    copia_futuro, copia_red = copy.deepcopy(futuro), copy.deepcopy(red)
    sim.evaluar_plan(flujos["nominal"], futuro, red)
    sim.evaluar_plan(flujos["resguardo"], futuro, red)
    for clave in ("demanda", "capacidad", "disponible"):
        assert np.array_equal(futuro[clave], copia_futuro[clave])
    assert futuro["estado"] == copia_futuro["estado"]
    assert np.array_equal(red["inventario_inicial"], copia_red["inventario_inicial"])


def test_numeros_aleatorios_comunes(futuro, red, flujos):
    solo_resguardo = sim.evaluar_plan(flujos["resguardo"], futuro, red)
    sim.evaluar_plan(flujos["nominal"], futuro, red)
    despues = sim.evaluar_plan(flujos["resguardo"], futuro, red)
    assert solo_resguardo == despues


# --- Dos implementaciones -----------------------------------------------------------------

@pytest.mark.parametrize("replica", [0, 1, 7, 199, 1199])
def test_pandas_y_numpy_coinciden(replica, datos, matriz, parametros, red, flujos):
    origins, destinations, routes = datos
    rng = sim.crear_generadores(sim.SEMILLA_MAESTRA, sim.N_CAMPANA)[replica]
    futuro = sim.entorno(rng, matriz, routes, destinations, parametros)
    for politica, flujo in flujos.items():
        plan = pd.DataFrame({"route_id": routes["route_id"], "planned_flow": flujo})
        con_pandas = sim.resumir_operacion(sim.operar(plan, routes, destinations, futuro))
        con_numpy = sim.evaluar_plan(flujo, futuro, red)
        assert set(con_pandas) <= set(con_numpy)
        for clave, valor in con_pandas.items():
            cerca(valor, con_numpy[clave])


# --- Campaña ---------------------------------------------------------------------------------

def test_tamanos_del_experimento(campana_completa):
    resultados, estados = campana_completa
    assert sim.N_CAMPANA == 1200 and sim.N_PILOTO == 200
    assert len(resultados) == 1200 and len(estados) == 1200
    assert list(resultados["replica"]) == list(range(1200))
    assert all(len(e) == 26 and e[0] == "Disrupcion" for e in estados)
    sim.chequear(resultados)


def test_piloto_y_resto_igual_a_una_corrida(datos, matriz, parametros, flujos, campana_completa):
    _, destinations, routes = datos
    junta, _ = sim.campana(sim.crear_generadores(), matriz, routes, destinations, parametros, flujos)
    pd.testing.assert_frame_equal(junta, campana_completa[0], check_exact=True)


def test_misma_semilla_mismo_resultado_otra_semilla_distinto(datos, matriz, parametros, flujos):
    _, destinations, routes = datos
    a, _ = sim.campana(sim.crear_generadores(123, 20), matriz, routes, destinations, parametros, flujos)
    b, _ = sim.campana(sim.crear_generadores(123, 20), matriz, routes, destinations, parametros, flujos)
    c, _ = sim.campana(sim.crear_generadores(124, 20), matriz, routes, destinations, parametros, flujos)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    assert not np.allclose(a["costo_nominal"], c["costo_nominal"])


def test_ocupacion_de_estados(campana_completa, matriz):
    assert sim.ocupacion([["Normal", "Pico"], ["Pico", "Pico", "Disrupcion"]]).tolist() == [1, 3, 1]
    _, estados = campana_completa
    ocupacion = sim.ocupacion(estados)
    assert ocupacion.sum() == 1200 * 26
    esperada = mk.ocupacion_esperada(matriz, mk.distribucion_inicial(), 26)
    por_trayectoria = pd.DataFrame([pd.Series(e).value_counts().reindex(mk.ESTADOS, fill_value=0) for e in estados])
    for estado in mk.ESTADOS:
        _, _, bajo, alto = sim.intervalo(por_trayectoria[estado])
        assert bajo <= esperada[estado] <= alto


def test_regresion_resultados_de_referencia(campana_completa):
    comparacion = sim.comparacion_emparejada(campana_completa[0]).set_index("metrica")
    cerca(comparacion.loc["Costo total", ["nominal", "resguardo", "diferencia"]].to_numpy(dtype=float),
          [99906.21, 82363.53, -17542.68], atol=0.01)
    cerca(comparacion.loc["Nivel de servicio", ["nominal", "resguardo", "diferencia"]].to_numpy(dtype=float),
          [0.8058, 0.8527, 0.0469], atol=5e-5)


# --- Estadística y parámetros ------------------------------------------------------------------

def test_intervalo_emparejado():
    rng = np.random.default_rng(4)
    d = rng.normal(2.0, 3.0, size=50)
    media, error, bajo, alto = sim.intervalo(d)
    from scipy.stats import t
    cerca(media, d.mean())
    cerca(error, d.std(ddof=1) / np.sqrt(50))
    cerca([bajo, alto], [d.mean() - t.ppf(0.975, 49) * error, d.mean() + t.ppf(0.975, 49) * error])
    assert sim.intervalo(np.zeros(10)) == (0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        sim.intervalo([1.0, np.nan])


def test_error_estandar_usa_las_diferencias(campana_completa):
    resultados = campana_completa[0]
    fila = sim.comparacion_emparejada(resultados).set_index("metrica").loc["Costo total"]
    dif = resultados["costo_resguardo"] - resultados["costo_nominal"]
    cerca(fila["error_estandar"], dif.std(ddof=1) / np.sqrt(len(dif)))


def test_parametros_por_estado(parametros):
    assert list(parametros.index) == ["Normal", "Pico", "Disrupcion"]
    cerca(parametros.to_numpy(), [[1.0, 1.0, 0.98], [1.2, 0.85, 0.9], [1.0, 0.6, 0.7]])


@pytest.mark.parametrize("dano", ["falta_estado", "repetido", "probabilidad", "negativo", "nan", "columna"])
def test_parametros_invalidos(tmp_path, dano):
    tabla = pd.read_csv(DATA_DIR / "markov_state_parameters.csv")
    if dano == "falta_estado":
        tabla = tabla.iloc[:2]
    elif dano == "repetido":
        tabla = pd.concat([tabla, tabla.iloc[[0]]])
    elif dano == "probabilidad":
        tabla.loc[0, "route_availability"] = 1.2
    elif dano == "negativo":
        tabla.loc[1, "demand_multiplier"] = -1
    elif dano == "nan":
        tabla.loc[2, "capacity_multiplier"] = np.nan
    elif dano == "columna":
        tabla = tabla.drop(columns="route_availability")
    ruta = tmp_path / "p.csv"
    tabla.to_csv(ruta, index=False)
    with pytest.raises(ValueError):
        sim.cargar_parametros(ruta)
