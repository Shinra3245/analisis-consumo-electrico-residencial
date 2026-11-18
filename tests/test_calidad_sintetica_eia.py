
import os
import sys
import unittest
from pathlib import Path

# Permitir importar el modulo del pipeline
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "jobs" / "batch"))

os.environ["PYSPARK_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from validar_eia_registros import validar_registros_eia


class TestCalidadSinteticaEIA(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.spark = (
            SparkSession.builder
            .appName("TestCalidadSinteticaEIA")
            .master("local[2]")
            .getOrCreate()
        )

        cls.spark.sparkContext.setLogLevel("ERROR")

        # Datos artificiales para probar las reglas
        registros = [
            ("2018", "1", "CO", "Final", "100.0"),
            ("2018", "2", "CO", "Final", "200.0"),
            ("2018", "2", "CO", "Final", "210.0"),
            ("2018", "3", "CO", "Final", "-50.0"),
            ("2018", "4", "CO", "Final", "abc"),
            ("2018", "5", "CO", "Preliminary", "500.0"),
            ("2018", "13", "CO", "Final", "600.0"),
            ("2018", "6", "TX", "Final", "600.0"),
            ("2018", "7", "CO", "Final", "700.0")
        ]

        columnas = [
            "anio",
            "mes",
            "estado",
            "estatus_dato",
            "ventas_residenciales_mwh"
        ]

        cls.bronze = cls.spark.createDataFrame(
            registros, columnas
        )

        cls.datos = validar_registros_eia(cls.bronze)

        cls.validos = cls.datos.filter(
            F.col("errores") == ""
        )

        cls.rechazados = cls.datos.filter(
            F.col("errores") != ""
        )

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_01_cantidad_registros(self):
        self.assertEqual(self.datos.count(), 9)

    def test_02_registros_validos(self):
        self.assertEqual(self.validos.count(), 2)

    def test_03_registros_rechazados(self):
        self.assertEqual(self.rechazados.count(), 7)

    def test_04_detectar_duplicados(self):

        duplicados = self.rechazados.filter(
            F.col("errores").contains(
                "Registro duplicado"
            )
        ).count()

        self.assertEqual(duplicados, 2)

    def test_05_detectar_ventas_invalidas(self):

        invalidos = self.rechazados.filter(
            F.col("errores").contains(
                "Ventas invalidas"
            )
        ).count()

        self.assertEqual(invalidos, 2)

    def test_06_detectar_mes_invalido(self):

        invalidos = self.rechazados.filter(
            F.col("errores").contains(
                "Mes invalido"
            )
        ).count()

        self.assertEqual(invalidos, 1)

    def test_07_detectar_estado_invalido(self):

        invalidos = self.rechazados.filter(
            F.col("errores").contains(
                "Estado invalido"
            )
        ).count()

        self.assertEqual(invalidos, 1)

    def test_08_detectar_estatus_no_final(self):

        invalidos = self.rechazados.filter(
            F.col("errores").contains(
                "Estatus no final"
            )
        ).count()

        self.assertEqual(invalidos, 1)


if __name__ == "__main__":
    unittest.main()
