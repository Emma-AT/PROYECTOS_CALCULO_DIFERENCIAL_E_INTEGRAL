"""Pruebas automáticas del proyecto (ejecutar con: pytest)."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.escenarios import escalar_c, precio_equilibrio, vpn
from src.limpieza import cargar_datos, densidad_aire, limpiar_viento
from src.modelo import (
    Turbina,
    densidad_weibull,
    potencia_media,
    simpson,
    trapecio,
    trapecio_acumulado,
    turbinas_desde_excel,
    weibull_momentos,
)

EXCEL = Path(__file__).resolve().parents[1] / "datos" / "P09_C-01_AGUIRRE.xlsx"


def test_trapecio_exacto_en_recta():
    x = np.linspace(0, 2, 11)
    assert trapecio(3 * x + 1, x[1] - x[0]) == pytest.approx(8.0)


def test_simpson_exacto_en_cubica():
    x = np.linspace(0, 2, 11)
    assert simpson(x**3, x[1] - x[0]) == pytest.approx(4.0)


def test_simpson_rechaza_subintervalos_impares():
    with pytest.raises(ValueError):
        simpson(np.ones(4), 1.0)


def test_acumulado_termina_en_la_integral_total():
    y = np.random.default_rng(0).random(50)
    assert trapecio_acumulado(y, 0.5)[-1] == pytest.approx(trapecio(y, 0.5))


def test_weibull_integra_uno():
    v = np.linspace(0, 60, 6001)
    area = simpson(densidad_weibull(v, 2.27, 9.86), v[1] - v[0])
    assert abs(area - 1) < 0.001


def test_turbina_ideal_coincide_con_formula_gamma():
    rho, d, cp, k, c = 1.225, 100.0, 0.45, 2.0, 8.0
    v = np.linspace(0, 45, 4501)
    area = math.pi * d**2 / 4
    p_kw = 0.5 * rho * area * cp * v**3 / 1000
    ideal = Turbina("ideal", 1, 1e12, d, 80, 0, 0, v, p_kw)
    exacta = 0.5 * rho * area * cp * c**3 * math.gamma(1 + 3 / k) / 1000
    assert potencia_media(ideal, k, c, rho, rho, n=4500) == pytest.approx(exacta, rel=1e-3)


def test_weibull_momentos_recupera_parametros():
    muestra = 9.0 * np.random.default_rng(1).weibull(2.3, 50_000)
    k, c = weibull_momentos(muestra)
    assert k == pytest.approx(2.3, rel=0.03)
    assert c == pytest.approx(9.0, rel=0.03)


def test_densidad_aire_estandar():
    assert float(densidad_aire(15.0, 101325.0, 287.05)) == pytest.approx(1.225, rel=1e-3)


def test_limpieza_quita_picos_y_faltantes():
    df = pd.DataFrame(
        {
            "fecha_hora": pd.date_range("2026-01-01", periods=6, freq="h"),
            "velocidad_m_s": [8.0, 8.5, 39.8, np.nan, 9.0, 9.2],
            "produccion_planta_MWh": [1.0] * 6,
        }
    )
    limpio = limpiar_viento(df)
    assert limpio["v_limpia_m_s"].notna().all()
    assert limpio["v_limpia_m_s"].max() < 35
    assert list(limpio["estado_viento"][2:4]) == ["pico", "faltante"]


def test_curvas_reales_cumplen_betz():
    for t in turbinas_desde_excel(cargar_datos(EXCEL)):
        assert t.cp(1.225).max() <= 16 / 27


def test_vpn_y_altura_casos_limite():
    assert vpn(100.0, 0.0, 50.0, 0.0, 0.08, 20) == pytest.approx(-100.0)
    assert vpn(0.0, 1.0, 1.0, 0.0, 0.10, 1) == pytest.approx(1 / 1.1)
    assert escalar_c(9.86, 55, 55, 0.15) == pytest.approx(9.86)


def test_precio_equilibrio_anula_el_vpn():
    ref = {"energia_GWh": 10.0, "mantenimiento_colones": 500.0}
    fila = {"energia_GWh": 30.0, "mantenimiento_colones": 300.0, "inversion_colones": 1e9}
    p_eq = precio_equilibrio(fila, ref, 0.08, 20)
    assert vpn(1e9, 20e6, p_eq, -200.0, 0.08, 20) == pytest.approx(0.0, abs=1e-3)
