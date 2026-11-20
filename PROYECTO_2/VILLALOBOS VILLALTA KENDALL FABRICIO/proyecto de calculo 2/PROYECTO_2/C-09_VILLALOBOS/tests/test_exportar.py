"""Exportación de tablas: CSV en formato regional español y libro de Excel."""

import io

import pandas as pd
from openpyxl import load_workbook

from src.exportar import libro_excel, tabla_csv


def _tabla() -> pd.DataFrame:
    return pd.DataFrame({"grupo": ["rápida", "lenta"], "horas_efecto": [7.86722, 3.8]}).set_index(
        "grupo"
    )


def test_csv_usa_punto_y_coma_coma_decimal_y_conserva_el_indice():
    texto = tabla_csv(_tabla()).decode("utf-8-sig")
    assert texto.splitlines()[0] == "grupo;horas_efecto"
    assert "rápida;7,8672" in texto
    leida = pd.read_csv(io.StringIO(texto), sep=";", decimal=",")
    assert leida["horas_efecto"].tolist() == [7.8672, 3.8]


def test_excel_tiene_una_hoja_por_tabla_con_encabezado_fijo():
    contenido = libro_excel({"guia": _tabla(), "otra": _tabla().reset_index()})
    libro = load_workbook(io.BytesIO(contenido))
    assert libro.sheetnames == ["guia", "otra"]
    hoja = libro["guia"]
    assert [c.value for c in hoja[1]] == ["grupo", "horas_efecto"]
    assert hoja["B2"].value == 7.8672
    assert hoja.freeze_panes == "A2" and hoja["A1"].font.bold


def test_columnas_de_dos_niveles_se_aplanan(analisis):
    resumen = analisis.tablas["resumen_grupos"]
    primera = tabla_csv(resumen).decode("utf-8-sig").splitlines()[0]
    assert primera.startswith("grupo;vida_media_h_count;vida_media_h_median")
