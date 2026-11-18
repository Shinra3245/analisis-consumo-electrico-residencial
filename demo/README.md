# Consumo eléctrico residencial en Colorado (versión preliminar)

Visor web estático que compara el consumo de un perfil modelado de viviendas unifamiliares (ResStock, Colorado 2018) con las ventas del sector residencial (EIA-861M, Colorado 2018).

## Cómo abrirlo

No requiere internet, instalación ni dependencias externas.

- Directo: abre `demo/index.html` en el navegador.
- Con servidor local (desde la raíz del repositorio):

  ```bash
  python -m http.server 8000 --directory demo
  ```

  y visita <http://localhost:8000>.

## Qué muestra

1. **Datos:** ResStock (5,869 modelos ponderados) y EIA-861M (ventas mensuales del sector residencial).
2. **Para qué:** comparar la escala del perfil modelado con el total residencial estatal.
3. **Resultados:** 16.81M MWh (ResStock), 19.29M MWh (EIA) y una relación anual de 87.16%, con comparación mensual en gráfico (líneas, barras o relación), filtro por temporada, selección de mes y tabla. La relación mensual va de 68.31% (agosto) a 114.85% (febrero).
4. **Calidad:** 35,040 intervalos de 15 minutos, 0 faltantes y 0 negativos.

El 87.16% compara escalas entre coberturas distintas (solo viviendas unifamiliares modeladas frente a todas las residencias); no mide error ni participación real.

## Archivos

- `index.html`: estructura y contenido.
- `styles.css`: estilos (responsive, modo claro y oscuro).
- `app.js`: datos mensuales, gráficos SVG e interacciones.
