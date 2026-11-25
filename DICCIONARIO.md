# Diccionario y generación de datos

Todos los registros son simulados. `dia` identifica un par de condiciones experimentales
hipotéticas, no una fecha de calendario ni una secuencia antes/después real.

## Matriz horaria

Tras limpiar, hay 1.440 filas y 9 columnas: 30 pares × 24 horas × 2 escenarios.
Cada fila contiene un escenario en una hora del par de condiciones.

| Columna | Tipo / unidad | Significado |
|---|---|---|
| dia | entero 1–30 | Identificador del par diario independiente |
| hora | entero 0–23, h | Hora del ciclo diario |
| escenario | categoría | base o mejorado |
| p_it_kw | continua, kW | Potencia media IT durante una hora |
| temperatura_exterior_c | continua, °C | Temperatura exterior de esa hora |
| p_refrigeracion_kw | continua, kW | Potencia media de refrigeración |
| p_otros_kw | continua, kW | Otros auxiliares: 37 base y 27 mejorado |
| p_total_kw | continua, kW | Suma de los tres componentes de potencia |
| pue_horario | cociente sin unidad | Potencia total / potencia IT en esa hora |

Las 1.441 filas brutas contienen una copia exacta adicional. Dos valores de
`p_total_kw` se han vaciado intencionadamente para mostrar la preparación de datos.
Los componentes están presentes y permiten reconstruirlos exactamente; no se
simulan fallos de sensores ni se imputa una medición desconocida.

## Generador

Sea c(h)=cos[2π(h−15)/24]. Para cada día se sortean A~N(0,6²) kW,
B~N(0,2²) °C y dos errores U_base,U_mejorado~N(0,1,8²) kW.
Cada llamada a la normal usa desviación estándar (no varianza).

- IT = 120 + A + 6 c(h) + ε_IT, ε_IT~N(0,1,5²) kW.
- Ambiente = 24 + B + 5 c(h) + ε_T, ε_T~N(0,0,5²) °C.
- Refrigeración común C = 35 + 8 c(h) + 0,8 B + 0,08(IT−120) + ε_C.
  El factor 0,8 tiene unidades kW/°C; 0,08 es kW/kW; ε_C~N(0,0,7²) kW.
- Refrigeración base = C + U_base + ε_base.
- Refrigeración mejorada = 0,60 C + U_mejorado + ε_mejorado.
- ε_base y ε_mejorado~N(0,0,4²) kW.
- Potencia total = IT + refrigeración + otros auxiliares.

Los sorteos son independientes salvo los términos diarios y horarios compartidos
explícitamente. Dentro de cada par, la carga IT y el ambiente son idénticos.
No se truncan las normales; se comprueba que las potencias generadas son positivas.
Esta parametrización es ilustrativa, no una calibración con sensores. El factor 0,60
representa un supuesto de reducción del 40 % del componente común de refrigeración;
no representa una especificación técnica de un equipo existente.
La reducción auxiliar fija es de 10 kW. A condiciones nominales (IT=120, B=0 y errores=0)
la potencia media del escenario base es 192 kW y la del mejorado, 168 kW,
lo que conecta con los PUE de 1,60 y 1,40 de la Fase I.

## Recuentos: eventos_diarios.csv

30 filas y cuatro columnas: `dia`, `inspecciones` (20/día), `rechazos` (0–20) y
`avisos` (entero ≥0). Son eventos auxiliares de mantenimiento, sin escenario,
y no se utilizan para atribuir efectos a la refrigeración.
Se generan rechazos~Binomial(20,0,02) y avisos~Poisson(1,5), independientes.
En el análisis se estiman p y λ de los recuentos obtenidos; no se confunden con los
parámetros usados para generar la simulación.

## Agregación diaria

`e_it_kwh`, `e_total_kwh` y `e_refrigeracion_kwh` suman las potencias horarias
multiplicadas por Δt=1 h. `p_it_media_kw` es e_it_kwh/24 h.
`pue_diario` es e_total_kwh/e_it_kwh. Las medias de carga IT de ambos escenarios
coinciden por construcción; no son dos muestras independientes.

## Limitaciones

No hay estacionalidad anual, fines de semana, humedad, averías físicas, costes,
incertidumbre de sensores ni validación de una instalación. El contraste estudia
las propiedades del generador, no la eficacia real de una intervención.
La reproducibilidad exacta depende de conservar código, semilla y versiones.
