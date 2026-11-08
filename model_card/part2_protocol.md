# Protocolo de simulación — Parte II

Protocolo implementado en `src/markov.py`, `src/simulacion.py` y
`notebooks/part2_markov_montecarlo.ipynb`. Los parámetros del experimento están fijados como
constantes en `src/simulacion.py` y el piloto no los modifica. No registra aprobaciones de la
cátedra, que no están disponibles.

## Pregunta

¿Cuál de las dos políticas fijas exportadas por la Parte I (nominal y resguardo) conviene operar
durante 26 semanas cuando el contexto cambia según una cadena de Markov, y con qué precisión se
sostiene esa comparación?

## Entradas

| Archivo | Uso | Procedencia |
|---|---|---|
| `outputs/part1_solution.csv` | política nominal | Parte I; huella SHA-256 controlada contra `part1_manifest.json` |
| `outputs/part1_solution_buffer.csv` | política de resguardo | ídem |
| `data/markov_observations.csv` | estimación de la matriz | material del curso: copia sin cambios de `docs/final/markov_observations.csv` |
| `data/markov_state_parameters.csv` | multiplicadores por estado | **supuesto sintético** |
| `data/routes.csv`, `data/destinations.csv` | red, costos, inventario y depósito | material del curso |

## Cadena de Markov

- Estados en orden fijo: Normal, Pico, Disrupcion.
- Estimación por máxima verosimilitud: $\hat P_{ij} = N_{ij} / \sum_k N_{ik}$ sobre las 159
  transiciones consecutivas de la serie de 160 semanas. Si una fila no tiene salidas, la ejecución
  se detiene.
- Conteos con los datos actuales: Normal 66/20/3, Pico 16/37/5, Disrupción 6/1/5. La fila
  Disrupción se estima con sólo 12 transiciones.
- Probabilidades a $k$ pasos: $P^k$. Distribución de la semana $t$: $\pi_t = \pi_1 P^{t-1}$ con
  $\pi_1 = (0, 0, 1)$.
- Distribución estacionaria: solución de $\pi P = \pi$, $\sum \pi = 1$ por mínimos cuadrados, con
  controles de residuo, no negatividad, irreducibilidad y regularidad.
- Ocupación esperada en el horizonte: $\sum_{t=1}^{26} \pi_t$.

## Modelo semanal

Para cada semana $t = 1,\dots,26$, zona $j$ y ruta $(i,j)$:

1. Estado $X_t$: $X_1 = $ Disrupción; para $t > 1$, $X_t \sim \hat P(X_{t-1}, \cdot)$.
2. Demanda $D_{jt} \sim \text{Poisson}(d_j \cdot m^{dem}_{X_t})$, independiente entre zonas.
3. Disponibilidad $A_{ijt} \sim \text{Bernoulli}(\rho_{X_t})$, independiente entre rutas.
4. Capacidad efectiva $U_{ijt} = A_{ijt}\, u_{ij}\, m^{cap}_{X_t}$.
5. Despacho $y_{ijt} = \min(x_{ij}, U_{ijt})$, donde $x$ es la política fija. Lo que no se despacha
   no genera costo.
6. Existencias $E_{jt} = I_{j,t-1} + \sum_i y_{ijt}$; atendido $\min(E_{jt}, D_{jt})$; venta perdida
   $L_{jt} = D_{jt} - $ atendido (sin pedidos pendientes).
7. Inventario final $I_{jt} = \min(E_{jt} - \text{atendido}, K_j)$; descarte
   $W_{jt} = \max(E_{jt} - \text{atendido} - K_j, 0)$.
8. Costo semanal $\sum c_{ij} y_{ijt} + \sum p_j L_{jt} + \sum h_j I_{jt} + \sum w_j W_{jt}$.

$I_{j0}$, $K_j$, $h_j$ y $w_j$ son `initial_inventory`, `storage_capacity`, `holding_cost` y
`waste_cost` de `destinations.csv`.

**Las políticas no se reoptimizan:** el mismo vector $x$ se aplica las 26 semanas, sin usar
información del estado ni de la demanda realizada.

## Métricas por trayectoria

| Métrica | Definición |
|---|---|
| Costo total | suma de los 26 costos semanales (puntos logísticos) |
| Nivel de servicio | $\sum \text{atendido} / \sum D$ en las 26 semanas (NaN si la demanda total es 0; la campaña lo rechaza) |
| Unidades faltantes | $\sum L$ |
| Probabilidad de algún faltante | indicador de al menos una semana con $\sum_j L_{jt} > 0$ |
| Fracción de semanas con faltante | semanas con faltante / 26 |
| Inventario medio | $\sum_t \sum_j I_{jt} / 26$ |
| Descarte | $\sum W$ |

También se guardan los cuatro componentes del costo.

## Diseño experimental

- **Horizonte:** 26 semanas, semana 1 en Disrupción.
- **Semilla maestra:** 20260816. `numpy.random.SeedSequence(20260816).spawn(1200)` da un generador
  independiente por trayectoria; la réplica $r$ usa siempre el generador $r$.
- **Números aleatorios comunes:** cada generador produce un futuro completo (estados, demandas,
  disponibilidades) y las dos políticas se evalúan sobre ese mismo futuro. Orden de sorteos por
  semana: estado (salvo $t = 1$), 5 demandas Poisson, 15 uniformes de disponibilidad.
- **Piloto:** réplicas 0 a 199. Controla que no haya valores imposibles, que la semilla reproduzca
  exactamente una réplica y que toda trayectoria empiece en Disrupción. El piloto **no** cambia
  parámetros, métricas ni políticas: si un control falla, la ejecución se detiene.
- **Campaña:** réplicas 200 a 1.199, que se suman al piloto para un total de 1.200.
- **Comparación:** diferencia emparejada resguardo − nominal por réplica; media, error estándar
  $s/\sqrt{n}$ e intervalo del 95 % con $t_{0{,}975;\,n-1}$. Para la probabilidad de algún faltante
  (todas las réplicas = 1) se informa además la cota de Clopper–Pearson.
- **Controles de implementación:** límite determinista (demanda y capacidad fijas) contra el cálculo
  a mano; equivalencia de la versión pandas (`operar`) y la NumPy (`evaluar_plan`) en las mismas
  trayectorias; balances semanales exactos; ocupación simulada contra la esperada.

## Sensibilidad (separada)

Después de la comparación principal, el notebook repite la campaña de 1.200 trayectorias (misma
semilla maestra) cambiando un supuesto por vez: disponibilidad ±0,05 en cada estado, multiplicador de
demanda en Pico 1,10 y 1,30 (referencia 1,20), y penalizaciones ×0,5 y ×1,5. La matriz y las
políticas no cambian. Dentro de cada variante las dos políticas comparten el mismo futuro; entre
variantes eso sólo se garantiza para las penalizaciones, que no alteran ningún sorteo. Cambiar la
disponibilidad o la demanda modifica los futuros realizados, así que las diferencias entre variantes
no son emparejadas. El punto de equilibrio de la penalización (factor ≈ 0,09) vale para estos dos
planes fijos, no para planes reoptimizados con otras penalizaciones.
Esas corridas no modifican los resultados de referencia ni se guardan en `outputs/`; sólo indican
qué supuestos podrían invertir la conclusión.

## Resultados con los datos actuales

| Métrica | Nominal | Resguardo | Diferencia | IC 95 % |
|---|---:|---:|---:|---|
| Costo total | 122.539,83 | 103.122,97 | −19.416,86 | [−19.539,06; −19.294,66] |
| Nivel de servicio | 0,7464 | 0,7980 | +0,0516 | [0,0514; 0,0519] |
| Unidades faltantes | 1.488,4 | 1.186,1 | −302,3 | [−304,1; −300,6] |
| Fracción de semanas con faltante | 0,944 | 0,837 | −0,106 | [−0,111; −0,102] |
| Inventario medio | 13,71 | 28,60 | +14,88 | [14,34; 15,43] |
| Descarte | 0,03 | 1,45 | +1,42 | [1,11; 1,73] |

Los intervalos miden sólo el error de simulación, condicional a la matriz estimada y a los
parámetros por estado supuestos.

## Salidas

`outputs/markov_matrix.csv`, `outputs/montecarlo_summary.csv`, `outputs/paired_comparison.csv` y
`outputs/part2_manifest.json` (semilla, tamaños, versiones y huellas SHA-256).
