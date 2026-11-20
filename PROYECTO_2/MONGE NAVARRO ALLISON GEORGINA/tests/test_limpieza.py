"""Pruebas de la limpieza de conteos."""

import numpy as np
import pytest

from src import limpieza as lz


def test_detecta_cero_de_mas():
    """130 junto a 12 y 11 es más de 5 veces sus vecinos: es sospechoso."""
    conteos = [10, 12, 130, 11, 9]
    assert lz.detectar_cero_de_mas(conteos).tolist() == [False, False, True, False, False]


def test_no_marca_valores_normales():
    conteos = [10, 20, 40, 35, 15]
    assert not lz.detectar_cero_de_mas(conteos).any()


def test_interpola_hueco_en_medio_del_dia():
    """Hueco entre 10 y 20: la línea recta da 15."""
    assert lz.interpolar_huecos([10, np.nan, 20]).tolist() == [10, 15, 20]


def test_limpiar_dia_corrige_y_cuenta():
    dia = lz.limpiar_dia([10, 12, 130, 11, np.nan, 9])
    assert dia.atipicos == 1
    assert dia.faltantes == 1
    assert dia.conteos[2] == pytest.approx(11.5)  # entre 12 y 11
    assert dia.conteos[4] == pytest.approx(10.0)  # entre 11 y 9
    assert not np.isnan(dia.conteos).any()
