# Ficha de Modelo Acordado (FMA) — Parte I

Documento de referencia del modelo implementado en `src/transporte.py` y
`notebooks/part1_primal.ipynb`. Describe el modelo tal como está implementado; no registra
aprobaciones ni fechas de congelamiento por parte de la cátedra, que no están disponibles.

## Decisión

- **Decisor:** gerencia logística de Red Federal de Insumos Esenciales.
- **Qué controla:** el flujo semanal planificado en cada una de las 15 rutas habilitadas.
- **Horizonte:** una semana operativa típica.
- **Pregunta:** ¿qué plan cubre la demanda nominal con el menor costo total, permitiendo faltante
  sólo cuando la red no alcanza y haciéndolo visible mediante una penalización?

## Conjuntos

| Símbolo | Significado | Fuente |
|---|---|---|
| $I$ | Centros: Norte, Centro, Sur | `origins.origin` |
| $J$ | Zonas: Capital, Oeste, Este, Costa, Interior | `destinations.destination` |
| $E \subseteq I\times J$ | 15 rutas habilitadas (las 3 × 5 combinaciones) | `routes.route_id`, `origin`, `destination` |

## Parámetros

| Símbolo | Significado | Unidad | Columna |
|---|---|---|---|
| $a_i$ | Oferta máxima del centro $i$ | unidades logísticas/semana | `origins.supply` (**reconstruida**) |
| $d_j$ | Demanda nominal de la zona $j$ | unidades/semana | `destinations.nominal_demand` |
| $u_{ij}$ | Capacidad de la ruta | unidades/semana | `routes.capacity` |
| $c_{ij}$ | Costo unitario de la ruta | puntos logísticos/unidad | `routes.unit_cost` |
| $p_j$ | Penalización por unidad no atendida | puntos/unidad | `destinations.shortage_penalty` |

Los puntos logísticos resumen flete, manipulación y seguro; no son pesos ni dólares. La penalización
es un costo social explícito, no un precio de venta.

## Variables de decisión

- $x_{ij} \ge 0$: flujo planificado por la ruta $(i,j)$, unidades/semana, continuo.
- $s_j \ge 0$: demanda no atendida en la zona $j$, unidades/semana, continua.

## Modelo

$$
\begin{aligned}
\min_{x,s}\quad & \sum_{(i,j)\in E} c_{ij}x_{ij} + \sum_{j\in J} p_j s_j \\
\text{s.a.}\quad & \sum_{j:(i,j)\in E} x_{ij} \le a_i && \forall i\in I && \text{(oferta)}\\
& x_{ij} \le u_{ij} && \forall (i,j)\in E && \text{(capacidad de ruta)}\\
& \sum_{i:(i,j)\in E} x_{ij} + s_j = d_j && \forall j\in J && \text{(balance de zona)}\\
& x_{ij}\ge 0,\ s_j\ge 0 .
\end{aligned}
$$

Solver: OR-Tools 9.15, GLOP (simplex continuo). Sustituye a `scipy.optimize.linprog`; el modelo
es el mismo.

## Supuestos y exclusiones

- La unidad logística equivalente es divisible: variables continuas. Despachos en pallets enteros
  requerirían un modelo entero, fuera de alcance.
- El faltante es visible y penalizado; no hay pedidos pendientes dentro de la semana.
- La oferta no obliga a despacharse por completo.
- No hay costos fijos de apertura de rutas ni restricciones de flota.

## Escenarios y política de comparación

| Instancia | Cambio | Redondeo |
|---|---|---|
| S1 | $d_j^{S1} = \lceil 1{,}10\,d_j \rceil$ | techo, tras redondear a 8 decimales para evitar $\lceil 55{,}000000000000007\rceil = 56$ |
| S2 | $u_{C\text{-}OES}^{S2} = 0{,}70\,u_{C\text{-}OES} = 24{,}5$ | sin redondeo |
| S3 | $a_i^{S3} = 0{,}90\,a_i$ | sin redondeo |
| Resguardo | $d_j^{res} = \lceil 1{,}05\,d_j \rceil$, oferta y capacidad nominales | techo |

El resguardo es una política alternativa para la Parte II, no un escenario de control.

## Casos de prueba manuales

Un corredor Norte–Capital, costo 4, penalización 80.

| Caso | Oferta | Capacidad | Demanda | Faltante permitido | Resultado esperado |
|---|---:|---:|---:|---|---|
| Factible | 10 | 10 | 6 | sí | $x=6$, $s=0$, costo 24 |
| Infactible | 10 | 3 | 6 | no | INFEASIBLE |
| Mismo caso con faltante | 10 | 3 | 6 | sí | $x=3$, $s=3$, costo 252 |
| Borde | 6 | 6 | 6 | sí | $x=6$ llena oferta y capacidad, $s=0$, costo 24 |

Se ejecutan en el notebook y en `tests/test_transporte.py` con la misma función `resolver`.

## Verificación

- **Independiente** (`verificar`): recalcula objetivo, transporte y penalización desde los flujos
  y los datos del escenario; uso y holgura por centro; holgura por ruta; balance por zona;
  no negatividad. Tolerancia absoluta $10^{-7}$. Compara el objetivo recalculado con el del solver.
- **Certificado dual** (`certificado`): objetivo dual igual al primal, signos duales consistentes
  con la convención de OR-Tools (restricción $\le$ con dual $\le 0$ al minimizar) y holgura
  complementaria. `VerifySolution` de GLOP se informa como control adicional.
- Hay óptimos alternativos en el caso nominal; las pruebas comparan valor y factibilidad, no la
  igualdad de cada flujo.

## Resultados con los datos actuales

| Instancia | Objetivo | Faltante | Despacho |
|---|---:|---:|---:|
| Nominal | 818,0 | 0 | 211 |
| S1 | 1.168,0 | 4 (Interior) | 230 |
| S2 | 849,5 | 0 | 211 |
| S3 | 1.039,5 | 4 (Interior) | 207 |
| Resguardo | 892,0 | 0 | 224 |

## Salida puente

`outputs/part1_solution.csv` y `outputs/part1_solution_buffer.csv`: una fila por ruta en el orden
de `routes.csv`, columnas `route_id, origin, destination, planned_flow, capacity, unit_cost, policy`.
`planned_flow` se redondea a 9 decimales para eliminar ruido de punto flotante de GLOP. Las huellas
SHA-256 se guardan en `outputs/part1_manifest.json`.
