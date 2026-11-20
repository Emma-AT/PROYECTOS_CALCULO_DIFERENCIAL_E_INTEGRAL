import itertools
import math

import numpy as np
import pytest

from src import modelo as m


# --- Integrales con resultado conocido -------------------------------------
def test_trapecio_exacto_en_funcion_lineal():
    x = np.linspace(0, 3, 7)
    assert m.trapecio(2 * x + 1, x) == pytest.approx(12.0)  # integral de 2x+1 en [0,3]


def test_simpson_exacto_en_cubica_y_preciso_en_seno():
    assert m.simpson(lambda x: x**3, 0, 2, n=2) == pytest.approx(4.0)
    assert m.simpson(np.sin, 0, math.pi, n=200) == pytest.approx(2.0, abs=1e-8)


def test_simpson_rechaza_n_impar():
    with pytest.raises(ValueError):
        m.simpson(np.sin, 0, 1, n=5)


def test_integral_acumulada_balance_con_el_total():
    x = np.linspace(0, 10, 101)
    y = np.exp(-x / 3)
    acum = m.integral_acumulada(y, x)
    assert acum[0] == 0
    assert acum[-1] == pytest.approx(m.trapecio(y, x))  # el acumulado final es la suma total
    assert np.all(np.diff(acum) >= 0)


# --- Validaciones obligatorias del modelo ----------------------------------
@pytest.mark.parametrize("k,T", [(0.01, 168), (0.1, 168), (0.7, 216), (5.0, 168)])
def test_densidad_integra_uno_con_error_menor_que_1e4(k, T):
    total = m.simpson(lambda t: m.densidad_modelo(t, k, T), 0, T, n=20000)
    assert abs(total - 1) < 1e-4


def test_ip_tiende_a_un_medio_cuando_k_tiende_a_cero():
    assert abs(m.ip_modelo(1e-9, 168) - 0.5) < 1e-4
    assert abs(m.ip_modelo(1e-9, 216) - 0.5) < 1e-4


def test_ip_modelo_crece_con_k_y_se_acerca_a_uno():
    ks = [1e-6, 1e-3, 1e-2, 0.1, 1, 10, 1e3]
    ips = [m.ip_modelo(k, 168) for k in ks]
    assert all(a < b for a, b in itertools.pairwise(ips))
    assert 0.5 <= ips[0] and ips[-1] < 1


@pytest.mark.parametrize("k,T", [(0.05, 168), (0.7, 216), (2.0, 168)])
def test_simpson_coincide_con_la_formula_cerrada_del_ip(k, T):
    assert m.ip_modelo(k, T, n=4000) == pytest.approx(m.ip_modelo_cerrado(k, T), abs=1e-6)


@pytest.mark.parametrize("k,T", [(0.08, 168), (0.7, 216)])
def test_fraccion_ultimas_24h_coincide_con_la_integral_numerica(k, T):
    num = m.simpson(lambda t: m.densidad_modelo(t, k, T), T - 24, T, n=4000)
    assert m.fraccion_ultimas(k, T, 24) == pytest.approx(num, abs=1e-8)
    assert m.fraccion_ultimas(k, T, 24) == pytest.approx(math.log(1 + 24 * k) / math.log(1 + k * T))


def test_f_modelo_va_de_cero_a_uno_y_es_creciente():
    t = np.linspace(0, 168, 500)
    F = m.f_modelo(t, 0.3, 168)
    assert F[0] == pytest.approx(0, abs=1e-12) and F[-1] == pytest.approx(1)
    assert np.all(np.diff(F) >= 0)


# --- Parte empírica ---------------------------------------------------------
def test_ip_empirico_es_el_promedio_de_t_sobre_T():
    rng = np.random.default_rng(1)
    tau = rng.beta(3, 1.2, size=500)
    assert m.indice_procrastinacion(tau, n=5000) == pytest.approx(tau.mean(), abs=1e-3)


def test_ip_de_entregas_uniformes_es_un_medio():
    tau = np.linspace(0, 1, 10001)
    assert m.indice_procrastinacion(tau) == pytest.approx(0.5, abs=1e-3)


def test_f_empirica_sin_datos_falla_con_mensaje_claro():
    with pytest.raises(ValueError, match="No hay entregas"):
        m.f_empirica([])


# --- Bisección --------------------------------------------------------------
@pytest.mark.parametrize("k,T", [(0.05, 168), (0.7, 216), (0.3, 168)])
def test_estimar_k_recupera_k_exacto_desde_el_ip_del_modelo(k, T):
    assert m.estimar_k(m.ip_modelo(k, T), T) == pytest.approx(k, rel=1e-6)


@pytest.mark.parametrize("k,T", [(0.05, 168), (0.7, 216)])
def test_estimar_k_con_entregas_simuladas_error_menor_que_10_por_ciento(k, T):
    horas = m.simular_entregas(k, T, n=20000, semilla=7)
    assert horas.min() >= 0 and horas.max() <= T
    k_est = m.estimar_k(m.indice_procrastinacion(horas / T), T)
    assert abs(k_est - k) / k < 0.10


@pytest.mark.parametrize("ip", [0.5, 0.3, 1.0, 1.2])
def test_estimar_k_rechaza_ip_fuera_de_rango(ip):
    with pytest.raises(ValueError):
        m.estimar_k(ip, 168)
