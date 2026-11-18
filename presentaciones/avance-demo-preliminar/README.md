# Presentación del avance tangible

La carpeta contiene una presentación nueva sobre la demo web de consumo eléctrico residencial en Colorado. Mantiene el estilo de fondos doodle azul y tarjetas crema de la entrega anterior.

## Archivos

- `Consumo_electrico_residencial_demo.pdf`: siete páginas, armado directamente desde las imágenes PNG.
- `diapositivas/`: imágenes 16:9 independientes, una por diapositiva.
- `evidencia/demo-grafica.png`: captura tomada de la demo local actual.
- `guion.md`: contenido resumido y guía para explicar las diapositivas.
- `guion-exposicion-4-integrantes.md`: reparto de diapositivas, texto oral y transiciones para el equipo.
- `generar.py`: compositor que coloca texto y gráfica sobre las ilustraciones existentes y une los PNG en PDF.

## Regenerar

Desde la raíz del proyecto, ejecutar `python presentaciones/avance-demo-preliminar/generar.py` (requiere Pillow). El script usa los fondos de `presentaciones/arte_generado/` y conserva esta entrega separada de la presentación anterior.

La muestra comparativa corresponde a Colorado en 2018. La diapositiva final presenta la incorporación de otros años como una etapa futura condicionada a la disponibilidad y comparabilidad de los datos.
