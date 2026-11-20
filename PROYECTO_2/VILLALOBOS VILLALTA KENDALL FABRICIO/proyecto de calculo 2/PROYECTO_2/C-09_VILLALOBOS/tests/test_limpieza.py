"""Lectura, validación de la base y tratamiento de faltantes y atípicos."""

import numpy as np
import pandas as pd
import pytest

from src.config import RUTA_DATOS
from src.limpieza import (
    detectar_atipicos,
    imputar_voluntario,
    leer_base,
    leer_parametros,
    validar_base,
)


def test_base_tiene_todas_las_hojas_y_registros():
    hojas = leer_base(RUTA_DATOS)
    assert len(hojas["Concentraciones"]) == 780
    assert len(hojas["Pruebas_atencion"]) == 480
    assert hojas["Voluntarios"]["voluntario"].nunique() == 60


def test_error_claro_si_falta_una_columna():
    hojas = leer_base(RUTA_DATOS)
    hojas["Bebidas"] = hojas["Bebidas"].drop(columns="cafeina_mg")
    with pytest.raises(ValueError, match="cafeina_mg"):
        validar_base(hojas)


def test_parametros_con_unidades_validadas():
    tabla = leer_base(RUTA_DATOS)["Parametros"]
    p = leer_parametros(tabla)
    assert p.inicio < p.fin < p.hora_dormir
    malo = tabla.copy()
    malo.loc[malo["parametro"] == "Umbral de efecto en la atención", "unidad"] = "mg/dL"
    with pytest.raises(ValueError, match="Unidad"):
        leer_parametros(malo)


def test_detecta_un_pico_aislado_sin_falsos_positivos():
    t = np.array([0.25, 0.5, 1, 2, 4, 6, 8, 12, 24])
    c = 5 * np.exp(-0.15 * t) * (1 - np.exp(-3 * t))
    c_mal = c.copy()
    c_mal[4] *= 3
    assert not detectar_atipicos(t, c).any()
    assert np.flatnonzero(detectar_atipicos(t, c_mal)).tolist() == [4]


def test_imputacion_interior_y_final():
    t = np.array([0.5, 1, 2, 6, 8, 12, 24], dtype=float)
    c = 4 * np.exp(-0.1 * t)
    con_huecos = c.copy()
    con_huecos[2] = np.nan
    con_huecos[-1] = np.nan
    lleno = imputar_voluntario(t, con_huecos)
    assert not np.isnan(lleno).any()
    assert lleno[2] == pytest.approx(np.interp(2, [1, 6], [c[1], c[3]]))
    assert lleno[-1] == pytest.approx(c[-1], rel=1e-9)


def test_limpieza_conserva_registros_y_no_deja_faltantes(analisis):
    limpio, bitacora = analisis.conc_limpio, analisis.bitacora
    assert len(limpio) == 780
    assert limpio["concentracion_mg_L"].notna().all()
    assert set(bitacora["estado"]) <= {"faltante", "atípico"}
    tratados = (limpio["estado"] != "observado").sum()
    assert tratados == len(bitacora)
    original = pd.read_excel(RUTA_DATOS, sheet_name="Concentraciones")
    assert original["concentracion_mg_L"].isna().sum() == (bitacora["estado"] == "faltante").sum()
