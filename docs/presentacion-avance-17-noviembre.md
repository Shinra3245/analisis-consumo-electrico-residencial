# Contenido para la presentación del avance

**Duración sugerida:** 4–5 minutos.
**Estado:** contenido resumido listo para aplicar al estilo visual que entregue el equipo. El PowerPoint y PDF existentes son un borrador anterior; se actualizarán después de aplicar ese estilo.

La fuente editable del contenido es [`contenido-presentacion-avance.json`](contenido-presentacion-avance.json). Aquí está la versión para lectura y exposición.

## Diapositiva 1 — Qué proyecto realizamos

**En pantalla**

- Analizar patrones de consumo eléctrico residencial en Estados Unidos.
- Usar perfiles modelados, estadísticas oficiales y datos del clima.
- La propuesta V2 fue aprobada por el profesor.

**Qué se hizo y cómo decirlo**

“Comenzamos a revisar si las fuentes propuestas permiten iniciar el análisis. Para este avance trabajamos con una muestra pequeña de Colorado.”

**Conclusión**

El objetivo general sigue vigente; este avance comprueba fuentes y datos antes de construir el sistema.

**Idea visual para el diseño posterior:** mapa de Estados Unidos con Colorado resaltado y el título del proyecto.

## Diapositiva 2 — Qué información revisamos

**En pantalla**

- ResStock: consumo residencial estimado por computadora.
- EIA: ventas residenciales de electricidad por mes.
- Open-Meteo: historial estimado de temperatura para un punto de Denver.

**Qué se hizo y cómo decirlo**

“Consultamos datos públicos de 2018 para Colorado. Cada fuente describe algo distinto: una representa viviendas mediante modelos, otra informa ventas estatales y la tercera estima el clima de una ubicación.”

**Conclusión**

Las fuentes pueden aportar perspectivas complementarias, pero no son mediciones iguales ni deben mezclarse sin revisar sus diferencias.

**Idea visual para el diseño posterior:** tres tarjetas con una casa, un gráfico de ventas y un termómetro/mapa.

## Diapositiva 3 — Primera muestra de consumo

**En pantalla**

- Colorado · viviendas unifamiliares separadas · año 2018.
- 35,040 intervalos de consumo, uno cada 15 minutos.
- 5,869 modelos representan aproximadamente 1.49 millones de viviendas en el cálculo de ResStock.

**Qué se hizo y cómo decirlo**

“Descargamos un archivo agregado de unos 31 MB y revisamos sus campos, fechas y valores. El archivo resume modelos de vivienda; no son lecturas individuales de medidores.”

**Conclusión**

La muestra tiene suficiente detalle temporal para comenzar un análisis; representa una categoría modelada y no todo el consumo de Estados Unidos.

**Idea visual para el diseño posterior:** una casa con una línea anual dividida en intervalos de 15 minutos.

## Diapositiva 4 — Qué encontramos al compararla

**En pantalla**

- ResStock: 16.81 millones de MWh en la categoría seleccionada.
- EIA: 19.29 millones de MWh para todo el sector residencial de Colorado.
- Relación numérica simple: 87%.

**Qué se hizo y cómo decirlo**

“Sumamos los meses de la muestra de ResStock y los comparamos con las ventas residenciales mensuales publicadas por EIA. También generamos una gráfica para ver cómo cambian los valores durante el año.”

**Conclusión**

La diferencia entre las dos series cambia según el mes. El 87% no es una calificación de precisión: se comparó una categoría modelada con todas las viviendas residenciales reportadas por EIA.

**Idea visual para el diseño posterior:** la gráfica mensual existente, con ambas series y una nota visible sobre sus distintos alcances.

## Diapositiva 5 — Cómo comprobamos los datos

**En pantalla**

- La secuencia ResStock tiene intervalos regulares durante el año.
- No encontramos celdas vacías ni valores negativos en el total revisado.
- La consulta climática devolvió 8,760 horas para Denver, sin datos faltantes.

**Qué se hizo y cómo decirlo**

“Revisamos que las fechas avanzaran de forma constante y que los campos principales tuvieran valores. El clima corresponde a una estimación histórica para un punto, no a todo Colorado ni a una medición directa de una estación.”

**Conclusión**

La muestra permite continuar con pruebas iniciales. Aún necesitamos alinear ubicación y horario antes de relacionar consumo y clima.

**Idea visual para el diseño posterior:** tres indicadores simples de revisión y un reloj/mapa que muestre las diferencias de horario y ubicación.

## Diapositiva 6 — Qué sigue

**En pantalla**

1. Confirmar atribuciones y condiciones de uso de las fuentes.
2. Ampliar la comparación a más tipos de vivienda o lugares.
3. Construir el procesamiento y revisar la calidad de los datos.
4. Después, probar detección de cambios inusuales y estimaciones.
5. Preparar un tablero y evaluar si hace falta infraestructura de nube.

**Qué se hizo y cómo decirlo**

“Ya comprobamos una muestra y dejamos un análisis que puede repetirse. El siguiente avance será ampliar el análisis sin perder de vista qué representa cada fuente.”

**Conclusión**

Tenemos una base medible para continuar; todavía no están construidos el tablero, las anomalías ni las estimaciones finales.

**Idea visual para el diseño posterior:** una ruta por etapas desde “muestra revisada” hasta “análisis y tablero”.

## Fuentes para notas o diapositiva final

- [ResStock: unidades, intervalos y archivos agregados](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html)
- [EIA: ventas mensuales por estado y sector](https://www.eia.gov/electricity/data/eia861m/)
- [Open-Meteo: datos históricos de reanálisis](https://open-meteo.com/en/docs/historical-weather-api)
- [Resultados detallados, controles y limitaciones](resultados-muestra-inicial.md)

Las ideas visuales son descripciones de contenido, no imágenes generadas. Se aplicará el estilo que proporcione el usuario antes de producir la versión visual final.
