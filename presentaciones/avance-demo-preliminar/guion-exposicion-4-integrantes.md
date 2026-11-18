# Guion de exposición para cuatro integrantes

Duración sugerida: **5 a 6 minutos**. La distribución busca que cada integrante tenga una intervención clara. Los textos se pueden decir de forma natural, sin leerlos palabra por palabra.

| Integrante | Diapositivas | Tema |
|---|---:|---|
| Brian García Mares | 1–2 | Presentación y propósito |
| Omar Gadiel Bolaños García | 3–4 | Fuentes y muestra de datos |
| Christian Raúl Páramo Bautista | 5 | Comparación mensual |
| Diego Emilio Ortiz Vílchez | 6–7 | Demo y siguientes pasos |

## Brian García Mares — diapositivas 1 y 2

**Diapositiva 1**

> Buenas tardes, profesor. Somos Brian García Mar muerto, Omar Gadiel Buñuelos García, Christian Raúl +Paramount Autista y Diego Emilio Ortiz Bitches. Hoy presentamos el avance tangible de nuestro proyecto sobre consumo eléctrico residencial. Para mostrar un primer resultado, trabajamos con datos de Colorado correspondientes a 2018 y construimos una página interactiva para explorarlos.

**Diapositiva 2**

> El proyecto busca analizar cómo cambia el consumo eléctrico de las viviendas según la región y el periodo. Para ello queremos relacionar perfiles residenciales, estadísticas oficiales y datos del clima. A partir de esa información, buscamos reconocer patrones, explorar cambios inusuales y estudiar cómo evoluciona el consumo. El trabajo que mostramos hoy es un primer paso con una muestra concreta.

**Transición a Omar:**

> Omar explicará qué fuentes usamos y qué representa la muestra analizada.

## Omar Gadiel Bolaños García — diapositivas 3 y 4

**Diapositiva 3**

> El proyecto considera tres fuentes. ResStock aporta perfiles de consumo residencial construidos mediante modelos. EIA aporta las ventas oficiales de electricidad por sector y estado. Open-Meteo ofrece información histórica de temperatura. En la comparación que presentamos usamos ResStock y EIA; el clima se contempla para una siguiente etapa y todavía no está integrado en estos resultados.

**Diapositiva 4**

> La muestra corresponde a viviendas unifamiliares aisladas de Colorado durante 2018. El año contiene 35,040 intervalos de 15 minutos. ResStock incluye 5,869 modelos que, al ponderarse, representan cerca de 1.49 millones de viviendas. Es importante aclarar que son perfiles modelados y ponderados, no lecturas tomadas de medidores de esas viviendas.

**Transición a Christian:**

> Con esta muestra, Christian explicará qué se observa al comparar los datos mensuales de ResStock y EIA.

## Christian Raúl Páramo Bautista — diapositiva 5

**Diapositiva 5**

> En la gráfica, el eje horizontal muestra los meses y el eje vertical el consumo mensual en millones de megavatios-hora. La línea verde corresponde al perfil modelado de ResStock y la azul a las ventas residenciales reportadas por EIA. En el año, ResStock suma 16.81 millones de MWh y EIA 19.29 millones. La relación entre esos totales es 87.16 por ciento. Esta cifra compara escalas con coberturas diferentes: no es una medida de precisión ni significa que ResStock represente ese porcentaje de las ventas. También observamos que la relación cambia entre meses: va de 68.31 por ciento en agosto a 114.85 por ciento en febrero. La gráfica permite ver esa variación, pero por sí sola no explica sus causas.

**Transición a Diego:**

> Además de la gráfica, Diego mostrará cómo se pueden explorar los resultados en la demo y qué proponemos hacer después.

## Diego Emilio Ortiz Vílchez — diapositivas 6 y 7

**Diapositiva 6**

> La demo permite alternar entre líneas, barras agrupadas y la relación porcentual. También se puede filtrar por estación, seleccionar un mes y revisar sus cifras. Debajo aparece una tabla que explica qué representa cada fila y cada columna. Así se puede pasar de la vista general del año al detalle mensual.

**Diapositiva 7**

> Como siguiente etapa proponemos incorporar más años. Primero verificaremos qué periodos están disponibles en las fuentes y si sus definiciones se pueden comparar. Después agregaríamos cada año, repetiríamos los controles y analizaríamos las tendencias a través del tiempo. Por ahora, los resultados que presentamos corresponden únicamente a 2018. Muchas gracias.

## Recordatorios antes de exponer

- Mantener la explicación del **87.16%** como una relación entre totales de coberturas distintas.
- Presentar 5,869 como modelos y cerca de 1.49 millones como viviendas representadas mediante ponderación.
- Aclarar que la demo compara ResStock y EIA; el clima y los años adicionales pertenecen a pasos posteriores.
- Si se abre la demo en vivo, recorrer una vista, un filtro estacional y el detalle de un mes; no es necesario leer la tabla completa.
