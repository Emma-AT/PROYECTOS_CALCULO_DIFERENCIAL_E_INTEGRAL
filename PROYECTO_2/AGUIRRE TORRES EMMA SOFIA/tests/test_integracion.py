"""Pruebas de integración y escenarios técnicos/económicos para C-01_AGUIRRE.

Valida la coherencia de la extrapolación de viento según Hellmann, la
producción neta anual (AEP) considerando pérdidas del parque eólico y el
cálculo del Valor Presente Neto (VPN).
"""

import math

import numpy as np
import pytest

from src.escenarios import (
    energia_anual,
    escalar_viento_altura,
    vpn,
)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_escalar_viento_altura_hellmann():
    """Verifica la extrapolación de viento de 40 m a 80 m con exponente 0.14.

    Fórmula: v_80 = 10.0 * (80.0 / 40.0)**0.14 = 10.0 * 2**0.14 ≈ 11.0189 m/s.
    """
    v_ref = 10.0
    h_ref = 40.0
    h_nueva = 80.0
    alpha = 0.14

    v_proyectada = escalar_viento_altura(v_ref, h_ref, h_nueva, alpha)
    esperado = 10.0 * (2.0**0.14)
    assert math.isclose(float(v_proyectada), esperado, rel_tol=1e-4)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_energia_anual_sin_perdidas():
    """Verifica que con pérdidas 0.0, E = P_media * 8760 h * N."""
    potencia_media_kw = 500.0  # 500 kW
    n_turbinas = 10
    perdidas_l = 0.0

    # 500 * 8760 * 10 = 43,800,000 kWh
    aep = energia_anual(potencia_media_kw, n_turbinas, perdidas_l)
    assert math.isclose(aep, 43_800_000.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_energia_anual_con_perdidas_15_porciento():
    """Verifica el cálculo de AEP con un 15% de pérdidas globales de parque."""
    potencia_media_kw = 500.0
    n_turbinas = 10
    perdidas_l = 0.15

    # 43,800,000 * (1 - 0.15) = 37,230,000 kWh
    aep = energia_anual(potencia_media_kw, n_turbinas, perdidas_l)
    assert math.isclose(aep, 37_230_000.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_vpn_proyecto_rentable():
    """Verifica el cálculo analítico del Valor Presente Neto (VPN).

    Caso de prueba simplificado:
        - Inversión inicial I_0 = 1,000,000 USD
        - Flujo anual neto CF = 200,000 USD
        - Tasa descuento r = 0.10 (10%)
        - Años N = 2 años
        VPN = -1,000,000 + 200,000/(1.1) + 200,000/(1.1^2)
            = -1,000,000 + 181,818.18 + 165,289.26 = -652,892.56 USD
    """
    inversion = 1_000_000.0
    # CF_t = delta_energia * precio - opex = 2_000_000 * 0.10 - 0 = 200_000 USD
    delta_energia_kwh = 2_000_000.0
    precio_kwh = 0.10
    delta_mantenimiento = 0.0
    tasa_descuento = 0.10
    anios = 2

    vpn_calc = vpn(
        inversion=inversion,
        delta_energia_kwh=delta_energia_kwh,
        precio_kwh=precio_kwh,
        delta_mantenimiento=delta_mantenimiento,
        tasa_descuento=tasa_descuento,
        anios=anios,
    )
    esperado = -1_000_000.0 + (200_000.0 / 1.1) + (200_000.0 / (1.1**2))
    assert math.isclose(vpn_calc, esperado, rel_tol=1e-4)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_escalar_viento_altura_vector():
    """Verifica que escalar_viento_altura procese adecuadamente vectores de numpy."""
    v_ref = np.array([5.0, 10.0, 15.0])
    v_proyectado = escalar_viento_altura(v_ref, h_ref=40.0, h_nueva=80.0, alpha=0.14)
    assert len(v_proyectado) == len(v_ref)
    assert (v_proyectado > v_ref).all()

