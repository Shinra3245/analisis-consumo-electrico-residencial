
import json
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

RUTA_JSON = (
    BASE / "data/exports/comparacion_co_2018.json"
)


class TestComparacionJSON(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not RUTA_JSON.is_file():
            raise FileNotFoundError(
                f"No existe el JSON: {RUTA_JSON}"
            )

        with open(RUTA_JSON, encoding="utf-8") as archivo:
            cls.datos = json.load(archivo)

        cls.meses = cls.datos["meses"]

    def test_01_estructura(self):
        """Validar campos principales del JSON."""

        self.assertEqual(self.datos["anio"], 2018)
        self.assertEqual(self.datos["estado"], "CO")
        self.assertEqual(self.datos["unidad"], "MWh")

        self.assertIn("totales", self.datos)
        self.assertIn("fuentes", self.datos)
        self.assertIn("meses", self.datos)

    def test_02_meses_completos(self):
        """Comprobar los 12 meses sin duplicados."""

        numeros = [fila["mes"] for fila in self.meses]

        self.assertEqual(len(numeros), 12)
        self.assertEqual(numeros, list(range(1, 13)))

        for fila in self.meses:
            self.assertEqual(fila["anio"], 2018)
            self.assertEqual(fila["estado"], "CO")

    def test_03_totales_anuales(self):
        """Comparar con los resultados verificados."""

        totales = self.datos["totales"]

        self.assertAlmostEqual(
            totales["resstock_mwh"],
            16809653.30,
            places=2
        )

        self.assertAlmostEqual(
            totales["eia_mwh"],
            19286952.00,
            places=2
        )

        self.assertEqual(
            totales["relacion_porcentaje"],
            87.16
        )

    def test_04_calculos_mensuales(self):
        """Verificar diferencias y porcentajes."""

        for fila in self.meses:
            resstock = fila["resstock_mwh"]
            eia = fila["eia_mwh"]

            self.assertGreaterEqual(resstock, 0)
            self.assertGreater(eia, 0)

            diferencia = resstock - eia
            porcentaje = resstock / eia * 100

            self.assertAlmostEqual(
                fila["diferencia_mwh"],
                diferencia,
                delta=0.03
            )

            self.assertAlmostEqual(
                fila["relacion_porcentaje"],
                porcentaje,
                delta=0.02
            )

    def test_05_consistencia_totales(self):
        """Comprobar que los meses suman el total anual."""

        total_resstock = sum(
            fila["resstock_mwh"] for fila in self.meses
        )

        total_eia = sum(
            fila["eia_mwh"] for fila in self.meses
        )

        self.assertAlmostEqual(
            total_resstock,
            self.datos["totales"]["resstock_mwh"],
            delta=0.10
        )

        self.assertAlmostEqual(
            total_eia,
            self.datos["totales"]["eia_mwh"],
            delta=0.10
        )


if __name__ == "__main__":
    unittest.main()
