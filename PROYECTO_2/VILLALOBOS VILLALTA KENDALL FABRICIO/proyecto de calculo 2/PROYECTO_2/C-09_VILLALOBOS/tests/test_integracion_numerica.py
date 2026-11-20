"""Reglas de integración propias contra resultados conocidos."""

import numpy as np
import pytest
from scipy.integrate import simpson as simpson_scipy
from scipy.integrate import trapezoid

from src.modelo import (
    biseccion,
    horas_efecto,
    integral_exponencial_truncada,
    simpson,
    trapecio,
    trapecio_acumulado,
)


def test_trapecio_exacto_en_rectas():
    x = np.array([0.0, 0.3, 1.0, 2.5, 4.0])
    assert trapecio(x, 3 * x + 2) == pytest.approx(3 * 16 / 2 + 2 * 4)


def test_simpson_exacto_en_parabolas_con_espaciado_irregular():
    x = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 24.0])
    y = 3 * x**2 - 2 * x + 1
    exacta = 24**3 - 24**2 + 24
    assert simpson(x, y) == pytest.approx(exacta, rel=1e-12)


def test_simpson_exacto_en_cubicas_con_espaciado_uniforme():
    x = np.linspace(0, 2, 9)
    assert simpson(x, x**3) == pytest.approx(4.0, rel=1e-12)


def test_reglas_propias_coinciden_con_scipy():
    rng = np.random.default_rng(1)
    x = np.sort(rng.uniform(0, 10, 15))
    y = np.exp(-0.3 * x) * (1 + np.sin(x))
    assert trapecio(x, y) == pytest.approx(trapezoid(y, x=x), rel=1e-12)
    assert simpson(x, y) == pytest.approx(simpson_scipy(y, x=x), rel=1e-10)


def test_acumulado_balance_con_total():
    x = np.linspace(0, 5, 21)
    y = np.sqrt(x)
    acumulado = trapecio_acumulado(x, y)
    assert acumulado[0] == 0
    assert acumulado[-1] == pytest.approx(trapecio(x, y))
    assert np.all(np.diff(acumulado) >= 0)


@pytest.mark.parametrize("k", [0.04, 0.135, 0.31])
def test_integral_impropia_exponencial(k):
    assert integral_exponencial_truncada(k, 400) == pytest.approx(1 / k, rel=1e-6)


def test_biseccion_raiz_conocida():
    assert biseccion(lambda x: x**2 - 2, 0, 2) == pytest.approx(np.sqrt(2), abs=1e-8)
    with pytest.raises(ValueError):
        biseccion(lambda x: x**2 + 1, 0, 2)


def test_horas_efecto_casos_limite():
    t = np.linspace(0, 24, 241)
    assert horas_efecto(t, np.full_like(t, 5.0), 1.5, 8, 20) == pytest.approx(12)
    assert horas_efecto(t, np.zeros_like(t), 1.5, 8, 20) == 0
    rampa = t / 10
    assert horas_efecto(t, rampa, 1.5, 8, 20) == pytest.approx(20 - 15)
