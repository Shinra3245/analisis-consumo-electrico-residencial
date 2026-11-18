
import os
import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE / "jobs" / "batch")
)

os.environ["PYSPARK_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from validar_resstock_registros import (
    validar_registros_resstock
)


class TestCalidadSinteticaResStock(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.spark = (
            SparkSession.builder
            .appName("TestCalidadSinteticaResStock")
            .master("local[2]")
            .getOrCreate()
        )

        cls.spark.sparkContext.setLogLevel("ERROR")

        # Funcion para crear registros artificiales
        def fila(
            fecha,
            estado="CO",
            tipo="Single-Family Detached",
            modelos="5869",
            viviendas="1490160.655",
            consumo="100.0"
        ):
            return (
                fecha,
                estado,
                tipo,
                modelos,
                viviendas,
                consumo,
                "resstock",
                "datos_sinteticos.csv"
            )

        registros = [
            # Registros validos
            fila("2018-01-01 00:15:00"),
            fila("2019-01-01 00:00:00"),

            # Fecha invalida
            fila("fecha-invalida"),

            # Estado incorrecto
            fila("2018-01-01 00:30:00", estado="TX"),

            # Tipo de vivienda vacio
            fila("2018-01-01 00:45:00", tipo=" "),

            # Consumo negativo
            fila("2018-01-01 01:00:00", consumo="-50"),

            # Consumo no numerico
            fila("2018-01-01 01:15:00", consumo="abc"),

            # Consumo nulo
            fila("2018-01-01 01:30:00", consumo=None),

            # Cantidad de modelos invalida
            fila("2018-01-01 01:45:00", modelos="0"),

            # Viviendas representadas invalidas
            fila("2018-01-01 02:00:00", viviendas="0"),

            # Intervalo fuera del anio 2018
            fila("2019-01-01 00:30:00")
        ]

        columnas = [
            "timestamp",
            "in.state",
            "in.geometry_building_type_recs",
            "models_used",
            "units_represented",
            "out.electricity.total.energy_consumption..kwh",
            "_source",
            "_source_file"
        ]

        cls.bronze = cls.spark.createDataFrame(
            registros,
            columnas
        )

        cls.datos = validar_registros_resstock(
            cls.bronze
        ).cache()

        cls.datos.count()

        cls.validos = cls.datos.filter(
            F.col("errores") == ""
        )

        cls.rechazados = cls.datos.filter(
            F.col("errores") != ""
        )

    @classmethod
    def tearDownClass(cls):
        cls.datos.unpersist()
        cls.spark.stop()

    def contar_error(self, texto):
        return self.rechazados.filter(
            F.col("errores").contains(texto)
        ).count()

    def test_01_cantidad_registros(self):
        self.assertEqual(self.datos.count(), 11)

    def test_02_registros_validos(self):
        self.assertEqual(self.validos.count(), 2)

    def test_03_registros_rechazados(self):
        self.assertEqual(self.rechazados.count(), 9)

    def test_04_fecha_invalida(self):
        self.assertEqual(
            self.contar_error("Fecha invalida"), 1
        )

    def test_05_estado_invalido(self):
        self.assertEqual(
            self.contar_error("Estado invalido"), 1
        )

    def test_06_tipo_vivienda_invalido(self):
        self.assertEqual(
            self.contar_error(
                "Tipo de vivienda invalido"
            ), 1
        )

    def test_07_consumos_invalidos(self):
        self.assertEqual(
            self.contar_error("Consumo invalido"), 3
        )

    def test_08_modelos_invalidos(self):
        self.assertEqual(
            self.contar_error("Modelos invalidos"), 1
        )

    def test_09_viviendas_invalidas(self):
        self.assertEqual(
            self.contar_error(
                "Viviendas representadas invalidas"
            ), 1
        )

    def test_10_anio_invalido(self):
        self.assertEqual(
            self.contar_error(
                "Anio fuera de la muestra"
            ), 1
        )

    def test_11_limite_anual(self):
        # El intervalo que termina a medianoche
        # del 1 de enero de 2019 pertenece a 2018.
        fila_limite = self.validos.filter(
            F.date_format(
                "timestamp_fin",
                "yyyy-MM-dd HH:mm:ss"
            ) == "2019-01-01 00:00:00"
        ).first()

        self.assertIsNotNone(fila_limite)
        self.assertEqual(fila_limite["anio"], 2018)
        self.assertEqual(fila_limite["mes"], 12)

        self.assertEqual(
            str(fila_limite["timestamp_inicio"]),
            "2018-12-31 23:45:00"
        )


if __name__ == "__main__":
    unittest.main()
