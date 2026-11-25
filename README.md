# Centro de datos inteligente

Julio Javier Fernández Garín · Unit 4002 · Engineering Mathematics · Fases I y II · 2026–2027

En este proyecto comparo el consumo de energía y el PUE de un centro de datos simulado en dos escenarios: base y mejorado. La Fase I recoge los cálculos iniciales de potencia, energía y refrigeración. En la Fase II analizo 30 días de datos horarios. Cada día se simula en ambos escenarios con la misma carga informática y la misma temperatura exterior.

## Archivos del proyecto

| Archivo o carpeta | Contenido |
|---|---|
| [notebooks/analisis_centro_datos.ipynb](notebooks/analisis_centro_datos.ipynb) | Análisis de la Fase II con el código, las tablas, las gráficas y las conclusiones. |
| [src/analisis.py](src/analisis.py) | Generación y limpieza de datos, cálculos, gráficas y comprobaciones. |
| [datos/](datos/) | Datos horarios brutos y limpios, eventos diarios, configuración y diccionario de variables. |
| [resultados/](resultados/) | Resumen diario, estadísticos, resultados del contraste y auditoría de IA. |
| [figuras/](figuras/) | Ocho gráficas de las dos fases. |

## Ejecución

Desde la carpeta del proyecto, abre una terminal con Python 3.12 y ejecuta:

```text
python -m pip install -r requirements.txt
python src/analisis.py
```

El segundo comando vuelve a generar los datos simulados, las tablas y las figuras. Para ejecutar el notebook en Jupyter:

```text
python -m pip install notebook
python -m notebook
```

Abre el notebook y ejecuta las celdas en orden. Los CSV usan coma como separador y punto decimal.

## Resultados de la Fase II

Tras eliminar un duplicado y reconstruir dos valores de potencia total a partir de sus componentes, el análisis utiliza 1.440 registros horarios. El consumo medio pasa de **4.617,258 kWh/día** en el escenario base a **4.041,709 kWh/día** en el mejorado. El ahorro medio simulado es de **575,549 kWh/día**, equivalente al **12,465 %** del consumo total del escenario base durante el periodo. El PUE del periodo pasa de **1,593** a **1,394** y se calcula dividiendo la energía total acumulada por la energía IT acumulada.

El contraste se realiza con 30 pares diarios. El intervalo de confianza del 95 % para la media del ahorro es de **544,460 a 606,638 kWh/día**. El resultado depende de los supuestos de refrigeración y consumos auxiliares incluidos en la simulación.

## Apoyo técnico de IA

Se utilizó ChatGPT como apoyo en el código Python, la generación de datos simulados y la interpretación de algunos resultados. La [auditoría de IA](resultados/auditoria_ia.md) recoge la consulta, la respuesta y su comparación con los resultados de Python.
