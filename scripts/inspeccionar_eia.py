
from pathlib import Path
from openpyxl import load_workbook

# Ruta del archivo EIA
ruta = Path("data/raw/eia_sales_revenue.xlsx")

if not ruta.is_file():
    raise FileNotFoundError(f"No existe: {ruta}")

# Abrir Excel
wb = load_workbook(
    ruta,
    read_only=True,
    data_only=True
)

try:
    print("\n=== ARCHIVO EIA ===")

    # Mostrar las hojas disponibles
    print("\nHojas encontradas:")

    for hoja in wb.sheetnames:
        print("-", hoja)

    # Inspeccionar las primeras hojas
    for ws in wb.worksheets[:3]:

        print(f"\n=== HOJA: {ws.title} ===")
        print("Filas:", ws.max_row)
        print("Columnas:", ws.max_column)

        print("\nPrimeras 12 filas:")

        for numero, fila in enumerate(
            ws.iter_rows(
                min_row=1,
                max_row=12,
                max_col=12,
                values_only=True
            ),
            start=1
        ):
            valores = [
                str(v)[:65] if v is not None else "-"
                for v in fila
            ]

            print(numero, "|", " | ".join(valores))

finally:
    wb.close()
