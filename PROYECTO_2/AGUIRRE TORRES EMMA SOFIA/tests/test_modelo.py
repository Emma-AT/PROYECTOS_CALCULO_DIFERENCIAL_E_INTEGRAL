"""Pruebas unitarias para los métodos numéricos y aerodinámicos de src/modelo.py.

Estas pruebas definen los casos de verificación analítica con soluciones
teóricas conocidas. Están marcadas con xfail mientras las funciones
estén pendientes de implementación en src/.
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.limpieza import densidad_aire
from src.modelo import (
    TurbinaEolica,
    densidad_weibull,
    energia,
    potencia,
    potencia_media,
    simpson_propio,
    trapecio_acumulado,
    trapecio_propio,
    verificar_limite_betz,
    weibull_momentos,
)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_densidad_aire_condiciones_estandar():
    """Verifica el cálculo de densidad del aire a nivel del mar (15 °C y 101325 Pa).

    Valor de referencia estándar ISA: rho ≈ 1.2250 kg/m^3.
    """
    temp_c = 15.0
    presion_pa = 101325.0
    rho = densidad_aire(temp_c, presion_pa)

    # R = 287.058 J/(kg*K), T = 288.15 K -> rho = 101325 / (287.058 * 288.15) ≈ 1.2250
    assert math.isclose(float(rho), 1.2250, rel_tol=1e-3)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_trapecio_propio_integral_polinomio():
    """Verifica trapecio_propio integrando f(x) = x en [0, 2].

    Integral analítica exacta: int_0^2 x dx = [x^2 / 2]_0^2 = 2.0.
    """
    x = np.linspace(0.0, 2.0, 21)
    y = x
    resultado = trapecio_propio(y, x=x)
    assert math.isclose(resultado, 2.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_trapecio_acumulado_vector():
    """Verifica que la integral acumulada preserve dimensiones y valor final."""
    x = np.linspace(0.0, 4.0, 5)
    y = np.ones_like(x)  # f(x) = 1 -> int_0^t 1 dt = t
    acum = trapecio_acumulado(y, x=x)

    assert len(acum) == len(x)
    assert math.isclose(acum[0], 0.0, abs_tol=1e-6)
    assert math.isclose(acum[-1], 4.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_simpson_propio_integral_parabola():
    """Verifica simpson_propio integrando f(x) = 3*x^2 en [0, 2].

    Integral analítica exacta: int_0^2 3*x^2 dx = [x^3]_0^2 = 8.0.
    La regla de Simpson es de orden exacto para polinomios de grado <= 3.
    """
    x = np.linspace(0.0, 2.0, 21)  # 21 puntos = 20 intervalos (par)
    y = 3.0 * (x**2)
    resultado = simpson_propio(y, x=x)
    assert math.isclose(resultado, 8.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_energia_potencia_constante():
    """Verifica que potencia constante de 100 kW durante 10 horas produzca 1000 kWh."""
    potencias = np.array([100.0] * 11)  # 11 puntos con paso de 1 hora
    resultado = energia(potencias, dt_horas=1.0)
    assert math.isclose(resultado, 1000.0, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_verificar_limite_betz_cumplimiento():
    """Comprueba que una curva con Cp <= 16/27 no genere error."""
    # Turbina ideal hipotética con Cp = 0.45 < 0.5926
    diametro = 50.0
    area = np.pi * (diametro / 2.0) ** 2
    rho_ref = 1.225
    v = np.array([5.0, 10.0, 15.0])
    p_viento_kw = 0.5 * rho_ref * area * (v**3) / 1000.0
    potencia_kw = 0.40 * p_viento_kw  # Cp = 0.40

    df_curva = pd.DataFrame({"v_ms": v, "potencia_kw": potencia_kw})
    cp_series = verificar_limite_betz(df_curva, area_rotor=area, rho_ref=rho_ref)

    assert (cp_series <= (16.0 / 27.0)).all()


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_densidad_weibull_integral_unitaria():
    """Verifica que la integral numérica de la FDP de Weibull sea cercana a 1.0."""
    k = 2.0  # Rayleigh
    c = 8.0  # m/s
    v = np.linspace(0.001, 30.0, 500)
    fdp = densidad_weibull(v, k=k, c=c)
    # Integral aproximada
    area_fdp = float(np.trapz(fdp, v))
    assert math.isclose(area_fdp, 1.0, rel_tol=0.01)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_weibull_momentos_valores_positivos():
    """Verifica que los parámetros k y c estimados sean positivos y coherentes."""
    # Muestra de vientos sintéticos con media ~8 m/s
    np.random.seed(42)
    v_muestra = np.random.rayleigh(scale=8.0, size=1000)
    k, c = weibull_momentos(v_muestra)

    assert k > 0.0
    assert c > 0.0
    assert 1.5 <= k <= 2.5


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_turbina_eolica_instanciacion():
    """Verifica la instanciación de la clase TurbinaEolica y el cálculo de área."""
    turbina = TurbinaEolica(
        modelo="Turbina Test 1000",
        potencia_nominal_kw=1000.0,
        diametro_rotor_m=60.0,
        altura_buje_m=70.0,
        v_in=3.0,
        v_rated=12.0,
        v_out=25.0,
    )
    esperado_area = np.pi * (30.0**2)
    assert math.isclose(turbina.area_rotor, esperado_area, rel_tol=1e-5)


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_potencia_interpolacion_y_correccion():
    """Verifica que la potencia calculada devuelva un arreglo no negativo."""
    curva = pd.DataFrame({
        "v_ms": [0.0, 3.0, 12.0, 25.0],
        "potencia_kw": [0.0, 0.0, 1000.0, 1000.0],
    })
    v_viento = np.array([0.0, 5.0, 12.0, 20.0])
    rho = np.array([1.20, 1.225, 1.25, 1.225])

    p_calc = potencia(v_viento, curva, rho=rho, rho_ref=1.225)
    assert len(p_calc) == len(v_viento)
    assert (p_calc >= 0.0).all()


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Pendiente de implementación por el estudiante",
    strict=False,
)
def test_potencia_media_valor_positivo():
    """Verifica que la potencia media calculada sea positiva y acotada."""
    curva = pd.DataFrame({
        "v_ms": np.linspace(0.0, 25.0, 26),
        "potencia_kw": np.clip(np.linspace(0.0, 1000.0, 26), 0.0, 800.0),
    })
    p_med = potencia_media(curva, k=2.0, c=8.0, rho_ref=1.225)
    assert p_med > 0.0

