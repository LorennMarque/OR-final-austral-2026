# Clase 04 — Análisis de escenarios mediante reoptimización

**Versión v3.1 · Estudiante · Taller del martes (120 min)**

Tres ciclos: modelo humano → implementación con agente → verificación independiente → puesta en común. El agente no define el modelo. Roles: modelador, operador y auditor; rotan en cada ejercicio.

## Cronograma

- 00:00–00:06: encuadre y asignación de roles.
- 00:06–00:40: ejercicio 1 y puesta en común.
- 00:40–01:14: ejercicio 2 y puesta en común.
- 01:14–01:50: ejercicio 3 y puesta en común.
- 01:50–02:00: ticket de salida y registro.

## Contrato base del agente

Actuá exclusivamente como implementador y auditor de código Python. El modelo adjunto fue definido por el equipo y está cerrado. No podés elegir, reformular, agregar o eliminar variables, objetivo, restricciones, distribuciones, estados, transiciones, eventos, métricas ni supuestos. Si el modelo está incompleto o es incompatible, detenete y enumerá preguntas; no completes los vacíos por tu cuenta. Implementá exactamente la FMA. Conservá una correspondencia explícita entre símbolos y variables de código. Separá datos, modelo, resolución, verificación y presentación. Informá estado del solver, solución, objetivo, residuos, pruebas y advertencias numéricas. No redactes la recomendación de gestión: esa interpretación corresponde al equipo.

## C04E1 — Mapa de escenarios de capacidad

### Situación completa

DataCare administra proyectos internos para varias áreas y planifica el próximo trimestre. La directora de Entrega decide cantidades continuas de tres paquetes estandarizados. A es un paquete de automatización de reportes recurrentes, P un paquete de analítica predictiva para una decisión prioritaria y D un paquete de despliegue dedicado con integración y seguimiento. Cada paquete aporta 72, 95 y 120 puntos de impacto, respectivamente. A consume 3 unidades de ingeniería, 1 de especialistas y 2 de plataforma; P consume 2, 3 y 1; D consume 4, 2 y 3. En el escenario base hay 120 unidades de ingeniería, 80 de especialistas y 100 de plataforma. La demanda interna admite como máximo 30 paquetes A, 25 P y 20 D. Se analizan seis vectores de capacidad: (120,80,100), (130,80,100), (120,90,100), (120,80,110), (130,90,100) y (140,100,120). Cada vector describe un trimestre alternativo. Para compararlos correctamente debe resolverse nuevamente el mismo modelo y observar plan, valor, usos y holguras; sumar beneficios aislados puede fallar porque las capacidades interactúan.

### Pregunta de decisión

¿Qué combinación de paquetes A, P y D maximiza el impacto en cada vector de capacidad y cómo interactúan las ampliaciones de recursos?

### Vocabulario operativo

- **Paquete A:** Unidad equivalente de automatización de un reporte o proceso recurrente.
- **Paquete P:** Unidad equivalente de analítica predictiva para una decisión prioritaria.
- **Paquete D:** Unidad equivalente de despliegue dedicado con integración y seguimiento.
- **Vector de capacidad:** Disponibilidades, en orden, de ingeniería, especialistas y plataforma.
- **Demanda máxima:** Cantidad límite que las áreas internas pueden utilizar de cada paquete.

### Datos y significado

- 72, 95 y 120 son puntos de impacto por paquete A, P y D.
- A=(3,1,2) expresa unidades de ingeniería, especialistas y plataforma por paquete A.
- P=(2,3,1) expresa los tres consumos por paquete P.
- D=(4,2,3) expresa los tres consumos por paquete D.
- (120,80,100) es el vector base de capacidades trimestrales.
- 30, 25 y 20 son las demandas máximas de A, P y D.
- Los otros cinco vectores son escenarios alternativos, no recursos acumulables.

### Formulación a desarrollar en clase

Definir x_A,x_P,x_D>=0 como cantidades continuas de paquetes entregados en el trimestre. Maximizar 72x_A+95x_P+120x_D. Para un vector (b_1,b_2,b_3), imponer 3x_A+2x_P+4x_D<=b_1, x_A+3x_P+2x_D<=b_2 y 2x_A+x_P+3x_D<=b_3. Agregar x_A<=30, x_P<=25 y x_D<=20. Crear una única función que reciba el vector, construya sus lados derechos y devuelva variables, valor, usos y seis holguras. Resolver los seis escenarios declarados. Si un vector amplía componente a componente a otro, comprobar que el valor no disminuya. Para estudiar interacción, comparar la mejora conjunta con las mejoras individuales, pero describir el resultado solo para estos vectores y no extrapolar una regla universal fuera del mapa evaluado. Todos los controles usan las mismas unidades y tolerancia.

### Supuestos que el modelo adopta

- Los paquetes son divisibles por representar volúmenes agregados de trabajo.
- Aporte y consumo por paquete permanecen constantes dentro del trimestre.
- Las demandas máximas no cambian al ampliar capacidades.
- Cada escenario se conoce antes de decidir su plan.
- Los puntos de impacto son comparables entre los tres servicios.

### Control previo al agente

- [ ] Construir una tabla con una fila por recurso y una columna por paquete.
- [ ] Verificar que cada columna del enunciado queda en la columna correcta de la matriz.
- [ ] Identificar qué lados derechos cambian en cada escenario.
- [ ] Definir una prueba de factibilidad y otra de monotonía antes de programar.

**Trabajo de modelado solicitado.** Formule el modelo primal completo. Declare que cada escenario reemplaza un lado derecho y que toda comparación exige volver a resolver.

### Ficha de Modelo Acordado (FMA)

- **Decisor, horizonte y acción controlable:**
- **Datos, índices, fuente y unidades:**
- **Variables, significado, dominio y unidad:**
- **Objetivo y convención de signo:**
- **Restricciones con nombre e interpretación:**
- **Supuestos y exclusiones:**
- **Dos casos manuales y resultado esperado:**
- **Métricas, tolerancias y controles:**
- **Firma del modelador y del auditor:**

### Solicitud específica al agente

Actuá exclusivamente como implementador y auditor de código Python. El modelo adjunto fue definido por el equipo y está cerrado. No podés elegir, reformular, agregar o eliminar variables, objetivo, restricciones, distribuciones, estados, transiciones, eventos, métricas ni supuestos. Si el modelo está incompleto o es incompatible, detenete y enumerá preguntas; no completes los vacíos por tu cuenta. Implementá exactamente la FMA. Conservá una correspondencia explícita entre símbolos y variables de código. Separá datos, modelo, resolución, verificación y presentación. Informá estado del solver, solución, objetivo, residuos, pruebas y advertencias numéricas. No redactes la recomendación de gestión: esa interpretación corresponde al equipo.

**Tarea cerrada:** Cree una función que reciba las tres capacidades, resuelva el mismo modelo y devuelva variables, valor, usos y holguras. Construya una grilla de cambios individuales y conjuntos.

```python
# Pegue aquí el código aceptado y corregido.
# Mantenga separadas: datos, modelo, resolución, verificación y presentación.
```

### Verificación independiente

Recalcule el objetivo de cada fila y compruebe monotonía al ampliar el conjunto factible. Compare el cambio conjunto con la suma de cambios individuales.

### Puesta en común

¿Por qué dos ampliaciones pueden interactuar? ¿Qué afirmación es empírica dentro de la grilla y cuál sería una extrapolación injustificada?

Registre qué se sostuvo, qué se corrigió y qué supuesto queda abierto.

```json
{"exercise_id":"C04E1","model_version":"","prompt_hash":"","agent":"","accepted_changes":[],"rejected_changes":[],"tests":[],"team_interpretation":""}
```

## C04E2 — Comprar capacidad dentro del modelo

### Situación completa

DataCare considera comprar capacidad externa para el próximo trimestre en vez de fijar de antemano un escenario. La directora de Entrega elige simultáneamente los paquetes A de automatización, P de analítica predictiva y D de despliegue dedicado, y la capacidad adicional. Los paquetes aportan 72, 95 y 120 puntos; consumen recursos como A=(3,1,2), P=(2,3,1) y D=(4,2,3), en el orden ingeniería, especialistas y plataforma. Las capacidades propias son (120,80,100) y las demandas máximas (30,25,20). Puede adquirir e, hasta 20 unidades de ingeniería, a 12 puntos de costo por unidad, y s, hasta 15 unidades de especialistas, a 16 puntos por unidad. No se puede ampliar plataforma. En el caso base e y s son continuas porque el proveedor factura fracciones de capacidad equivalente. Los costos se expresan en la misma escala que el impacto para maximizar valor neto. El resultado debe separar valor bruto de los servicios, costo de compra y valor neto; de otro modo no sería posible explicar si una mejora proviene de producir más o de ignorar el costo de ampliar recursos.

### Pregunta de decisión

¿Qué plan de servicios y qué cantidades de ingeniería y especialistas conviene comprar para maximizar el valor neto trimestral?

### Vocabulario operativo

- **Capacidad comprada e:** Unidades adicionales y divisibles de ingeniería contratadas externamente.
- **Capacidad comprada s:** Unidades adicionales y divisibles de especialistas contratadas externamente.
- **Valor bruto:** Puntos aportados por los paquetes antes de restar compras.
- **Valor neto:** Valor bruto menos 12e y 16s.
- **Compra divisible:** Capacidad que puede contratarse en cantidades no enteras dentro de sus cotas.

### Datos y significado

- 20 unidades es el máximo comprable de ingeniería e.
- 12 puntos por unidad es el costo de e en la métrica del objetivo.
- 15 unidades es el máximo comprable de especialistas s.
- 16 puntos por unidad es el costo de s.
- e amplía solo las 120 unidades de ingeniería y s solo las 80 de especialistas.
- Las 100 unidades de plataforma no pueden ampliarse.
- 30, 25 y 20 siguen siendo máximos de demanda de A, P y D.

### Formulación a desarrollar en clase

Definir x_A,x_P,x_D,e,s>=0 como variables continuas. Maximizar 72x_A+95x_P+120x_D-12e-16s. Las capacidades ampliadas se escriben 3x_A+2x_P+4x_D<=120+e y x_A+3x_P+2x_D<=80+s; plataforma conserva 2x_A+x_P+3x_D<=100. Imponer x_A<=30, x_P<=25, x_D<=20, e<=20 y s<=15. La forma matricial puede trasladar e y s al lado izquierdo con coeficiente -1. Reportar el valor bruto 72x_A+95x_P+120x_D, el costo 12e+16s y su diferencia. Como controles, resolver el mismo modelo con e=s=0 y luego con costos artificialmente altos. Si la compra real fuese por bloques o incluyera un cargo fijo, esta formulación continua dejaría de representar el contrato y debería revisarse antes de cambiar el código. Cada restricción debe conservar un nombre que identifique el recurso correspondiente.

### Supuestos que el modelo adopta

- La capacidad externa tiene la misma productividad que la capacidad propia.
- La compra se usa dentro del mismo trimestre y no queda inventario de capacidad.
- Los costos 12 y 16 son lineales, sin cargos fijos ni descuentos.
- Ingeniería y especialistas pueden comprarse fraccionariamente.
- No existe un proveedor de capacidad adicional de plataforma.

### Control previo al agente

- [ ] Explicar por qué e y s aparecen con signo -1 en las restricciones matriciales.
- [ ] Comprobar que valor bruto, costo y neto usan la misma escala.
- [ ] Verificar manualmente que e<=20 y s<=15 están incluidos como dominios.
- [ ] Definir el caso sin compra que servirá de comparación.

**Trabajo de modelado solicitado.** Agregue variables de compra e y s al modelo primal. Incorpore su costo al objetivo y sus cotas; explique qué significa que sean continuas.

### Ficha de Modelo Acordado (FMA)

- **Decisor, horizonte y acción controlable:**
- **Datos, índices, fuente y unidades:**
- **Variables, significado, dominio y unidad:**
- **Objetivo y convención de signo:**
- **Restricciones con nombre e interpretación:**
- **Supuestos y exclusiones:**
- **Dos casos manuales y resultado esperado:**
- **Métricas, tolerancias y controles:**
- **Firma del modelador y del auditor:**

### Solicitud específica al agente

Actuá exclusivamente como implementador y auditor de código Python. El modelo adjunto fue definido por el equipo y está cerrado. No podés elegir, reformular, agregar o eliminar variables, objetivo, restricciones, distribuciones, estados, transiciones, eventos, métricas ni supuestos. Si el modelo está incompleto o es incompatible, detenete y enumerá preguntas; no completes los vacíos por tu cuenta. Implementá exactamente la FMA. Conservá una correspondencia explícita entre símbolos y variables de código. Separá datos, modelo, resolución, verificación y presentación. Informá estado del solver, solución, objetivo, residuos, pruebas y advertencias numéricas. No redactes la recomendación de gestión: esa interpretación corresponde al equipo.

**Tarea cerrada:** Implemente una única formulación ampliada con cinco variables. Devuelva plan, compra, valor bruto, costo de compra y valor neto; compárela con el escenario sin compra.

```python
# Pegue aquí el código aceptado y corregido.
# Mantenga separadas: datos, modelo, resolución, verificación y presentación.
```

### Verificación independiente

Compruebe que las restricciones usan 120+e y 80+s. Resuelva también con compras fijadas en cero y con costos muy altos.

### Puesta en común

¿Qué cambia si la capacidad solo puede comprarse en bloques? ¿Por qué el costo debe expresarse en la misma métrica que el objetivo?

Registre qué se sostuvo, qué se corrigió y qué supuesto queda abierto.

```json
{"exercise_id":"C04E2","model_version":"","prompt_hash":"","agent":"","accepted_changes":[],"rejected_changes":[],"tests":[],"team_interpretation":""}
```

## C04E3 — Plan estable frente a tres escenarios

### Situación completa

DataCare debe comprometer hoy un único plan trimestral de paquetes A, P y D antes de saber cuál será la disponibilidad final de recursos. A es automatización de reportes, P analítica predictiva y D un despliegue dedicado. Sus aportes son 72, 95 y 120 puntos; sus consumos de (ingeniería, especialistas, plataforma) son A=(3,1,2), P=(2,3,1) y D=(4,2,3). La demanda admite como máximo (30,25,20) paquetes. Las capacidades pueden resultar (120,80,100), (110,90,95) o (130,70,105). Un contrato con las áreas usuarias impide adaptar cantidades después de conocer cuál escenario ocurrió, por lo que el mismo vector de producción debe ser factible en los tres. La directora busca el plan común con mayor aporte y quiere compararlo con tres planes hipotéticos que sí se decidirían con el escenario conocido. Esos planes adaptados son una referencia informativa, no opciones operativamente disponibles. La diferencia ayuda a cuantificar el costo de comprometerse temprano, mientras la verificación central consiste en sustituir el plan único en cada vector de capacidad.

### Pregunta de decisión

¿Qué único plan de paquetes maximiza el aporte y permanece factible bajo los tres escenarios de capacidad, y cuánto aporta frente a planes hipotéticamente adaptables?

### Vocabulario operativo

- **Plan único:** Mismo vector de cantidades que se compromete antes de conocer el escenario.
- **Intersección factible:** Conjunto de planes que cumplen simultáneamente las restricciones de todos los escenarios.
- **Plan adaptado:** Referencia que se elegiría conociendo primero un escenario específico.
- **Compromiso temprano:** Decisión irreversible tomada antes de observar la capacidad disponible.

### Datos y significado

- (120,80,100), (110,90,95) y (130,70,105) son capacidades alternativas de ingeniería, especialistas y plataforma.
- 72, 95 y 120 son puntos por paquete A, P y D.
- A=(3,1,2), P=(2,3,1) y D=(4,2,3) son consumos por paquete en el mismo orden de recursos.
- 30, 25 y 20 son máximos de demanda comunes a los tres escenarios.
- Los tres valores adaptados se calculan con información perfecta y no son decisiones disponibles hoy.

### Formulación a desarrollar en clase

Definir x_A,x_P,x_D>=0 como cantidades continuas que deben mantenerse iguales en todos los escenarios. Maximizar 72x_A+95x_P+120x_D. Para cada capacidad b^k de los tres vectores, imponer por separado 3x_A+2x_P+4x_D<=b^k_1, x_A+3x_P+2x_D<=b^k_2 y 2x_A+x_P+3x_D<=b^k_3. Agregar una sola vez x_A<=30, x_P<=25 y x_D<=20. Esta formulación apila nueve restricciones de recursos y representa la intersección de regiones. Verificar el plan resultante contra cada vector. Para la comparación, resolver además tres modelos separados, cada uno con su capacidad conocida, y registrar sus valores. No reemplazar el plan único por alguno adaptado ni interpretar la diferencia como una pérdida evitable si el contrato realmente impide decidir después. Reportar por separado cada verificación de escenario.

### Supuestos que el modelo adopta

- Uno de los tres escenarios ocurrirá y no habrá otro fuera del conjunto considerado.
- Las cantidades comprometidas no pueden modificarse después de observar capacidad.
- Aportes, consumos y demandas máximas son iguales en los tres escenarios.
- No se asignan probabilidades ni se optimiza un promedio de escenarios.

### Control previo al agente

- [ ] Dibujar qué restricciones se repiten y qué variables permanecen únicas.
- [ ] Comprobar que las nueve reglas de recursos estarán presentes.
- [ ] Proponer un plan pequeño, como (0,0,0), y verificarlo en los tres vectores.
- [ ] Etiquetar los planes adaptados como referencias no implementables.

**Trabajo de modelado solicitado.** Formule un modelo primal con las restricciones de los tres escenarios apiladas. El objetivo usa los mismos aportes y no se adapta después de conocer el escenario.

### Ficha de Modelo Acordado (FMA)

- **Decisor, horizonte y acción controlable:**
- **Datos, índices, fuente y unidades:**
- **Variables, significado, dominio y unidad:**
- **Objetivo y convención de signo:**
- **Restricciones con nombre e interpretación:**
- **Supuestos y exclusiones:**
- **Dos casos manuales y resultado esperado:**
- **Métricas, tolerancias y controles:**
- **Firma del modelador y del auditor:**

### Solicitud específica al agente

Actuá exclusivamente como implementador y auditor de código Python. El modelo adjunto fue definido por el equipo y está cerrado. No podés elegir, reformular, agregar o eliminar variables, objetivo, restricciones, distribuciones, estados, transiciones, eventos, métricas ni supuestos. Si el modelo está incompleto o es incompatible, detenete y enumerá preguntas; no completes los vacíos por tu cuenta. Implementá exactamente la FMA. Conservá una correspondencia explícita entre símbolos y variables de código. Separá datos, modelo, resolución, verificación y presentación. Informá estado del solver, solución, objetivo, residuos, pruebas y advertencias numéricas. No redactes la recomendación de gestión: esa interpretación corresponde al equipo.

**Tarea cerrada:** Construya el modelo robusto por intersección de restricciones, resuélvalo y compare su valor con los tres planes que se obtendrían con información perfecta de cada escenario.

```python
# Pegue aquí el código aceptado y corregido.
# Mantenga separadas: datos, modelo, resolución, verificación y presentación.
```

### Verificación independiente

Verifique el plan contra cada vector de capacidad. No compare vectores solo por igualdad: compare factibilidad y valor.

### Puesta en común

¿Qué se sacrifica por exigir un plan único? ¿Cuándo sería realista adaptar el plan después de observar el escenario?

Registre qué se sostuvo, qué se corrigió y qué supuesto queda abierto.

```json
{"exercise_id":"C04E3","model_version":"","prompt_hash":"","agent":"","accepted_changes":[],"rejected_changes":[],"tests":[],"team_interpretation":""}
```

## Ticket de salida

1. Decisión que podemos defender.
2. Control que evitó un error.
3. Supuesto que debería validar un responsable real.
