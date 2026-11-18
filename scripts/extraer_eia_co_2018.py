
from pathlib import Path
from decimal import Decimal
from openpyxl import load_workbook

BASE = Path(__file__).resolve().parents[1]
RUTA = BASE / "data/raw/eia_sales_revenue.xlsx"

if not RUTA.is_file():
    raise FileNotFoundError(f"No existe: {RUTA}")

wb = load_workbook(
    RUTA,
    read_only=True,
    data_only=True
)

try:
    ws = wb["Monthly-States"]

    registros = []

    # Los datos comienzan en la fila 4
    for fila in ws.iter_rows(
        min_row=4,
        values_only=True
    ):
        anio = fila[0]
        mes = fila[1]
        estado = fila[2]
        estatus = fila[3]
        ventas_mwh = fila[5]

        # Filtrar Colorado durante 2018
        if (
            anio == 2018
            and str(estado).strip().upper() == "CO"
        ):
            if (
                mes is None
                or ventas_mwh is None
            ):
                raise ValueError(
                    "Registro incompleto de EIA"
                )

            mes = int(mes)
            consumo = Decimal(str(ventas_mwh))

            if mes < 1 or mes > 12 or consumo < 0:
                raise ValueError(
                    f"Registro invalido: mes {mes}"
                )

            registros.append(
                (mes, str(estatus), consumo)
            )

    # Ordenar por mes
    registros.sort(key=lambda x: x[0])

    print("\n=== EIA COLORADO 2018 ===")
    print("Registros encontrados:", len(registros))

    print("\n=== VENTAS MENSUALES ===")

    for mes, estatus, consumo in registros:
        print(
            f"Mes {mes:02d} | "
            f"{consumo:,.2f} MWh | "
            f"Estado: {estatus}"
        )

    # Calcular total anual
    total = sum(
        (r[2] for r in registros),
        Decimal("0")
    )

    print("\n=== TOTAL ANUAL EIA ===")
    print(f"Total MWh: {total:,.2f}")
    print(
        f"Millones de MWh: "
        f"{total / Decimal('1000000'):,.4f}"
    )

    meses = [r[0] for r in registros]

    if sorted(meses) != list(range(1, 13)):
        print(
            "\nADVERTENCIA: Faltan meses "
            "o existen registros duplicados."
        )
    else:
        print("\nLos 12 meses estan completos.")

finally:
    wb.close()
