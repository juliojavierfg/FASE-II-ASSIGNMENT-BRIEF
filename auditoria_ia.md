# Interpretación de IA y auditoría

La respuesta de ChatGPT del 13 de noviembre de 2026 se compara con los resultados calculados en Python.

## 1. Resultados calculados antes de la interpretación

- 30 pares diarios de datos simulados; igual carga IT y ambiente dentro de cada par.
- Consumo medio base: 4.617,258 kWh/día; mejorado: 4.041,709 kWh/día.
- Ahorro medio: 575,549 kWh/día; proporción agregada: 12,465 %.
- IC bilateral 95 % para la media del ahorro: [544,460; 606,638] kWh/día.
- t pareada unilateral: 37,8628; gl=29; p=1,5153e-26.
- Correlación diaria ambiente-refrigeración: r=0,6561 (30 días base).
- La mejora se introduce en el generador: refrigeración común ×0,60 y otros auxiliares −10 kW.

## 2. Prompt aplicado a estos resultados

«Con los resultados anteriores, redacta una explicación breve para un responsable
no técnico y recomienda un siguiente paso. Distingue la simulación de un resultado
real y no conviertas la correlación en causalidad.»

## 3. Respuesta de ChatGPT objeto de auditoría

«En la simulación, el escenario mejorado consume aproximadamente un 12,5 % menos
que el base, con la misma carga informática. El ahorro medio ronda 576 kWh al día.
La relación positiva entre temperatura exterior y refrigeración ayuda a identificar
condiciones de mayor demanda, pero no demuestra por sí sola causalidad.
Estos resultados favorecen estudiar la opción mejorada mediante una prueba piloto
con mediciones reales antes de decidir una implantación.»

## 4. Auditoría crítica de la respuesta

| Afirmación / omisión | Comprobación | Decisión |
|---|---|---|
| Ahorro de aproximadamente 12,5 % | 100 × (suma base − suma mejorado) / suma base = 12,465 % | Aceptar como resultado de la simulación |
| Ahorro de unos 576 kWh/día | Media de las 30 diferencias = 575,549 kWh/día | Aceptar con redondeo |
| Igual carga informática | Comparación de 720 pares horarios con `np.allclose`: verdadero | Aceptar dentro del diseño simulado |
| No atribuye causalidad a r | r=0,6561; comparten un ciclo y parámetros impuestos | Aceptar; el vínculo tampoco es evidencia externa al generador |
| Recomienda un piloto, no implantación directa | No hay datos reales, costes ni validación térmica interna | Recomendación proporcionada, condicionada a viabilidad |
| Omite el intervalo de incertidumbre | IC 95 % [544,460; 606,638] para la media | Añadir, sin presentarlo como rango de ahorro del 95 % de los días |
| No indica que la mejora está incorporada al código | El factor 0,60 y la reducción de 10 kW forman parte del generador | Añadir para evitar un razonamiento circular |
| No analiza inversión ni seguridad térmica | Dataset sin costes ni temperaturas internas | No afirmar rentabilidad ni seguridad de equipos |

Los redondeos del ahorro coinciden con los resultados de Python. La conclusión revisada incorpora el intervalo de confianza y explica cómo se introdujo la mejora en la simulación.

## 5. Conclusión revisada para el responsable

En 30 pares de días simulados, la opción mejorada reduce el consumo total un 12,5 %
con la misma carga informática y ambiente. La media del ahorro es de 576 kWh/día;
el intervalo del 95 % para esa media del modelo es aproximadamente de 544 a
607 kWh/día. La mejora estaba supuesta en el código, por lo que el resultado no
prueba que una instalación vaya a obtenerla. Conviene valorar un piloto con
contadores y mediciones térmicas internas, comparar condiciones equivalentes y
estudiar el coste antes de decidir una inversión.

## 6. Evidencia de comprobación

Los cálculos constan en `resultados.json`, `resumen_diario.csv` y el notebook.
El registro `verificaciones` confirma equivalencias numéricas entre fórmulas
independientes y SciPy. Los resultados describen el comportamiento del modelo con los supuestos de simulación utilizados.
