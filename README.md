# Del plan nominal a una decisión confiable bajo incertidumbre

Trabajo Práctico Integrador de Investigación Operativa — Universidad Austral, 2026.
Autor: Lorenzo Marquesini.

## Pregunta

Red Federal de Insumos Esenciales distribuye cada semana unidades logísticas desde tres centros
(Norte, Centro, Sur) hacia cinco zonas (Capital, Oeste, Este, Costa, Interior) por 15 rutas.
La pregunta central es: **¿qué plan conviene con los datos nominales y qué tan confiable sigue
siendo en futuros plausibles?**

- **Parte I — Programación lineal** (`notebooks/part1_primal.ipynb`). Modelo de transporte con
  faltante penalizado, resuelto con OR-Tools (GLOP). Verificación independiente, certificado de
  optimalidad, escenarios S1, S2 y S3, plan de resguardo (+5 % de demanda de diseño) y exportación
  de las dos políticas.
- **Parte II — Markov y Monte Carlo** (`notebooks/part2_markov_montecarlo.ipynb`). Cadena de Markov
  de regímenes (Normal, Pico, Disrupción) estimada sobre 160 semanas; probabilidades a varios pasos y
  distribución estacionaria; 1.200 trayectorias de 26 semanas (piloto de 200) con números
  aleatorios comunes; comparación emparejada de las dos políticas fijas y recomendación.

Se usa OR-Tools GLOP en lugar de `scipy.optimize.linprog`, que nombra el enunciado: es el mismo
modelo lineal continuo, resuelto con otro solver.

## Resultados de referencia

| Instancia | Objetivo (puntos/semana) | Faltante |
|---|---:|---:|
| Nominal | 828,0 | 0 |
| S1: demanda +10 % | 1.453,0 | 9 |
| S2: C-OES al 70 % | 849,5 | 0 |
| S3: oferta al 90 % | 1.305,0 | 8,5 |
| Resguardo: demanda +5 % | 907,0 | 0 |

Monte Carlo (1.200 trayectorias, diferencia emparejada resguardo − nominal, IC 95 %):

| Métrica | Nominal | Resguardo | Diferencia | IC 95 % |
|---|---:|---:|---:|---|
| Costo total por trayectoria | 99.906,2 | 82.363,5 | −17.542,7 | [−17.679,0; −17.406,3] |
| Nivel de servicio | 0,8058 | 0,8527 | +0,0469 | [0,0466; 0,0472] |

El resguardo es la mejor de las dos políticas fijas evaluadas, pero ninguna alcanza un servicio
alto (85 % en el resguardo). Los costos son **puntos de costo logístico**, no dinero.

## Estructura

```text
README.md, requirements.txt, pytest.ini, ai_log.jsonl
data/                   entradas (ver "Procedencia de los datos")
src/
  datos.py              rutas del proyecto, carga y validación de origins/destinations/routes
  transporte.py         LP: resolver, verificar, certificado, exportar/cargar políticas
  markov.py             estados, conteos, matriz, potencias, estacionaria, ocupación esperada
  simulacion.py         parámetros, futuros aleatorios, evaluación pandas y NumPy, campaña, IC
  graficos.py           estilo común de gráficos, tablas HTML e imágenes en tema claro u oscuro
notebooks/              part1_primal.ipynb, part2_markov_montecarlo.ipynb (los dos notebooks principales)
outputs/                salidas generadas por los notebooks (presentacion/: imágenes para el informe)
model_card/             part1_fma.md, part2_protocol.md, feedback.md
tests/                  pruebas automáticas (pytest)
docs/final/             enunciado, plantillas de los notebooks y serie de estados entregada
```

## Instalación

Probado con Python 3.12.3 en Linux. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` fija las versiones exactas con las que se validó el proyecto. El generador
aleatorio de NumPy no garantiza la misma secuencia entre versiones mayores, así que para reproducir
los números de referencia conviene usar esas versiones.

## Ejecución

Los notebooks se ejecutan **en orden**, porque la Parte II lee los archivos que exporta la Parte I:

1. `notebooks/part1_primal.ipynb`
2. `notebooks/part2_markov_montecarlo.ipynb`

Pueden abrirse desde `notebooks/` o desde la raíz: cada notebook busca la raíz del repositorio
(la carpeta que contiene `src/datos.py`) y usa rutas relativas a ella. Ambos completan
*Restart and Run All* sin intervención. Para ejecutarlos sin interfaz:

```bash
cd notebooks
python -c "
import nbformat
from nbclient import NotebookClient
for f in ['part1_primal.ipynb', 'part2_markov_montecarlo.ipynb']:
    nb = nbformat.read(f, as_version=4)
    NotebookClient(nb, timeout=900, kernel_name='python3').execute()
    nbformat.write(nb, f)
"
```

La Parte I tarda unos segundos; la Parte II, unos 20 segundos (incluye el análisis de sensibilidad).
Las versiones HTML (`notebooks/*.html`) se generan aparte con Quarto (`quarto render notebooks/part1_primal.ipynb`)
y deben volver a renderizarse después de ejecutar los notebooks.

El documento renderizado oculta el código (`execute: echo: false` en el encabezado de cada notebook); sólo se ven
un fragmento de `resolver` con OR-Tools GLOP en la Parte I y uno de `entorno` y `campana` en la Parte II, extraídos
del código real con `g.mostrar_fragmento`. Las celdas de infraestructura llevan `#| include: false` y se ejecutan igual.
Todo el código está en `src/` y en los notebooks.

Los PDF (`notebooks/*.pdf`) se imprimen desde el HTML, que conserva las tablas HTML; `notebooks/print.css` ajusta
tipografía y saltos de página sólo para impresión:

```bash
for nb in part1_primal part2_markov_montecarlo; do
  google-chrome --headless=new --no-pdf-header-footer --print-to-pdf=notebooks/$nb.pdf "file://$PWD/notebooks/$nb.html"
done
```

## Pruebas

```bash
python -m pytest
```

104 pruebas sobre las implementaciones reales de `src/`: casos manuales factible, infactible y de
borde; objetivos, cotas, balances y no negatividad del nominal, S1, S2, S3 y resguardo; óptimos
alternativos; rechazo de datos inválidos; integridad de los archivos puente; conteos, matriz,
potencias y estacionaria; balances semanales exactos, faltante, descarte y costos; límite
determinista; capacidad cero; números aleatorios comunes; equivalencia pandas/NumPy; tamaño del
experimento, piloto y reproducibilidad por semilla; y regresión de los resultados de referencia.
La tolerancia es `atol=1e-7`, `rtol=0`, y las comparaciones fallan si aparecen NaN.

## Salidas

| Archivo | Lo genera | Contenido |
|---|---|---|
| `outputs/part1_solution.csv` | Parte I | Política nominal: una fila por ruta con `route_id, origin, destination, planned_flow, capacity, unit_cost, policy` |
| `outputs/part1_solution_buffer.csv` | Parte I | Política de resguardo, mismo esquema |
| `outputs/part1_manifest.json` | Parte I | Objetivos y SHA-256 de entradas y políticas |
| `outputs/markov_matrix.csv` | Parte II | Matriz de transición estimada, orden Normal, Pico, Disrupcion |
| `outputs/montecarlo_summary.csv` | Parte II | Una fila por trayectoria: métricas y componentes de costo de cada política |
| `outputs/paired_comparison.csv` | Parte II | Medias, diferencia emparejada, error estándar e IC 95 % por métrica |
| `outputs/part2_manifest.json` | Parte II | Semilla, tamaños, versiones y SHA-256 de entradas, políticas y salidas |
| `outputs/presentacion/verificacion_lp_oscuro.png` | Parte I | Verificación numérica del plan nominal (objetivo, brecha primal–dual, residuos, cotas) en tema oscuro, para el apéndice |
| `outputs/presentacion/rutas_nominal_resguardo_oscuro.png` | Parte I | Rutas cuyo flujo cambia entre el plan nominal y el de resguardo, en tema oscuro, para el apéndice |
| `outputs/presentacion/distribucion_resguardo_claro.png` | Parte II | Distribución semanal del plan de resguardo por centro y zona, con totales, en tema claro, para el one pager |
| `outputs/presentacion/evidencia_decision_claro.png` | Parte II | Indicadores de la recomendación (costo determinista, costo simulado, servicio, faltante) e IC 95 %, en tema claro, para el one pager |
| `outputs/presentacion/ocupacion_teorica_simulada_oscuro.png` | Parte II | Ocupación esperada por la cadena frente a la simulada, con IC 95 %, en tema oscuro, para el apéndice |
| `outputs/presentacion/validacion_simulacion_oscuro.png` | Parte II | Indicadores de validación de la simulación (piloto, réplicas, diferencia pandas/NumPy) en tema oscuro, para el apéndice |
| `outputs/presentacion/sensibilidad_oscuro.png` | Parte II | Tabla resumen de sensibilidad en tema oscuro (fondo `#0E0E0E`) para la presentación |
| `outputs/presentacion/parametros_zonas_oscuro.png` | Parte II | Parámetros por zona de la simulación (demanda, penalización, inventario, almacenamiento y descarte) en tema oscuro, para el apéndice |

La Parte II recalcula el SHA-256 de cada política y se detiene si no coincide con el registrado
por la Parte I.

## Procedencia de los datos

| Archivo | Origen |
|---|---|
| `destinations.csv`, `routes.csv` | Material del curso (estaban en `docs/final/`). |
| `origins.csv` | Material de la cátedra: Norte 75, Centro 80, Sur 70 (225 unidades frente a 211 de demanda). Reemplaza la oferta reconstruida del 07/11/2026. |
| `markov_state_parameters.csv` | Material de la cátedra: multiplicadores y disponibilidad por estado (Normal 1,00 / 1,00 / 0,98; Pico 1,20 / 0,85 / 0,90; Disrupción 1,00 / 0,60 / 0,70). Reemplaza los parámetros sintéticos. |
| `markov_observations.csv` | Material del curso: copia sin cambios de `docs/final/markov_observations.csv`, la serie histórica que el enunciado da por entregada (160 semanas, la última en Disrupción). El notebook verifica que ambos archivos sean idénticos. |

Los costos, faltantes y resultados Monte Carlo usan estos archivos. Siguen siendo datos didácticos
del caso, no mediciones de una operación real.

## Limitaciones del modelo

- Plan semanal fijo durante 26 semanas: sin reoptimización, pronóstico ni pedidos pendientes.
- Variables continuas (unidades divisibles); despachos en pallets enteros requerirían un modelo entero.
- La penalización por faltante es un valor asignado y domina el costo simulado (≈ 81 % en la política nominal).
- Los intervalos Monte Carlo miden error de simulación condicional a la matriz estimada y a los
  parámetros por estado de la cátedra; no incluyen la incertidumbre de estimar la matriz (sólo 12
  transiciones observadas desde Disrupción).
- Sólo se comparan dos políticas; "resguardo" no es una política óptima del problema estocástico.
