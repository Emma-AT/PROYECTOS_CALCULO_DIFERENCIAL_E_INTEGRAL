"""Pruebas con la base entregada (datos/P06_C-06_MONGE.xlsx)."""

import io

import numpy as np
import pandas as pd
import pytest

from src import datos
from src import escenarios as es
from src.limpieza import limpiar_conteos
from src.modelo import totales_diarios, trapecio


@pytest.fixture(scope="module")
def base():
    return datos.cargar_base()


@pytest.fixture(scope="module")
def limpio(base):
    return limpiar_conteos(base.conteos)


@pytest.fixture(scope="module")
def totales(base, limpio):
    return totales_diarios(limpio, base.parametros.hi, base.parametros.hf)


def test_lee_parametros_con_unidades(base):
    p = base.parametros
    assert p.hi < 7 < 16 < p.hf
    assert p.dias_campana > 0 and p.horas_turno > 0


def test_falta_una_hoja_da_error_claro():
    archivo = io.BytesIO()
    pd.DataFrame({"x": [1]}).to_excel(archivo, sheet_name="Otra", index=False)
    archivo.seek(0)
    with pytest.raises(ValueError, match="Falta la hoja"):
        datos.leer_hojas(archivo)


def test_limpieza_no_toca_el_original_y_no_deja_huecos(base, limpio):
    assert limpio["aves_limpias"].notna().all()
    assert limpio["aves_contadas"].isna().sum() == base.conteos["aves_contadas"].isna().sum()
    sin_tocar = limpio["correccion"] == ""
    assert np.allclose(
        limpio.loc[sin_tocar, "aves_limpias"], limpio.loc[sin_tocar, "aves_contadas"]
    )


def test_total_es_la_suma_de_las_especies(totales):
    assert np.allclose(totales["Total"], totales[es.ESPECIES].sum(axis=1))
    assert len(totales) == 50


def test_colas_agregan_aves(limpio, totales):
    """Las colas triangulares suman aves: el total es mayor que lo contado."""
    contado = limpio["aves_limpias"].sum()
    assert totales["Total"].sum() > contado


def test_optima_supera_a_los_demas_en_fechas(base, limpio, totales):
    esc = es.comparar_escenarios(totales, limpio, base.parametros)
    optima = esc[esc["nombre"].str.startswith("Óptima")]["frac_fechas"].iloc[0]
    assert (esc["frac_fechas"] <= optima + 1e-12).all()
    assert esc["frac_registrada"].between(0, 1).all()


def test_aves_registradas_coinciden_con_la_fraccion(base, limpio, totales):
    """Unidades: aves registradas = fracción x total de la temporada (aves)."""
    esc = es.comparar_escenarios(totales, limpio, base.parametros)
    N = trapecio(totales["Total"], totales["dia"])
    assert np.allclose(esc["aves_registradas"], esc["frac_registrada"] * N)
