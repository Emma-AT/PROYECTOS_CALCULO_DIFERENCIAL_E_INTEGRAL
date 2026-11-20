"""Pruebas del modelo. Se ejecutan con:  pytest

Cada prueba revisa algo cuyo resultado ya conocemos de antemano.
Si el código calcula bien, todas pasan (salen en verde).
"""

import numpy as np
import pytest
from scipy import integrate

from src import modelo as m

# Datos de la validación obligatoria: paso gaussiano con centro conocido.
CENTRO = 27.3  # días
SIGMA = 5.0  # días
T_FINO = np.round(np.arange(0, 50.0001, 0.01), 2)
N_GAUSS = 1000 * np.exp(-((T_FINO - CENTRO) ** 2) / (2 * SIGMA**2))


# --- Reglas de integración ------------------------------------------------
def test_trapecio_exacto_en_recta():
    """El trapecio es exacto en rectas: integral de 3x + 1 en [0, 2] = 8."""
    x = np.linspace(0, 2, 7)
    assert m.trapecio(3 * x + 1, x) == pytest.approx(8.0)


def test_simpson_exacto_en_cubica():
    """Simpson es exacto en polinomios de grado 3: integral de x^3 en [0, 2] = 4."""
    x = np.linspace(0, 2, 5)
    assert m.simpson(x**3, x) == pytest.approx(4.0)


def test_simpson_y_trapecio_contra_scipy_y_valor_exacto():
    """integral de sen(x) en [0, pi] = 2. Comparamos con scipy y el valor exacto."""
    x = np.linspace(0, np.pi, 102)  # 101 intervalos (impar) a propósito
    y = np.sin(x)
    assert m.simpson(y, x) == pytest.approx(2.0, rel=1e-4)
    assert m.trapecio(y, x) == pytest.approx(integrate.trapezoid(y, x=x))
    assert m.error_relativo(m.simpson(y, x), 2.0) < m.error_relativo(m.trapecio(y, x), 2.0)


def test_integral_acumulada_empieza_en_cero_y_termina_en_el_total():
    """Balance: el último valor acumulado es igual al total."""
    x = np.linspace(0, 10, 11)
    y = x**2
    c = m.integral_acumulada(y, x)
    assert c[0] == 0
    assert c[-1] == pytest.approx(m.trapecio(y, x))
    assert np.all(np.diff(c) >= 0)


def test_integrar_con_nan_da_error_claro():
    """Caso límite: si quedan huecos sin limpiar, el código avisa."""
    with pytest.raises(ValueError):
        m.trapecio([1.0, np.nan, 3.0])


# --- Total diario ---------------------------------------------------------
def test_total_diario_sin_colas_es_la_suma_de_conteos():
    """Balance: si el vuelo dura justo las horas observadas, total = suma."""
    conteos = [5, 20, 40, 60, 55, 30, 15, 8, 2]  # 9 horas: 7:00 a 16:00
    assert m.total_diario(conteos, hi=7, hf=16) == pytest.approx(sum(conteos))


def test_total_diario_con_colas_triangulares():
    """10 aves/h constantes, vuelo de 5:00 a 18:00.

    Bloques: 9 h x 10 = 90 aves. Triángulos: 2 h x 10 / 2 = 10 antes y 10
    después. Total esperado: 110 aves.
    """
    conteos = [10] * 9
    assert m.colas_triangulares(conteos, 5, 18) == pytest.approx((10.0, 10.0))
    assert m.total_diario(conteos, 5, 18) == pytest.approx(110.0)


def test_dos_formas_del_total_diario_son_cercanas():
    """El método de bloques y el de trapecio dan resultados parecidos."""
    conteos = np.array([5, 20, 40, 60, 55, 30, 15, 8, 2], dtype=float)
    a = m.total_diario(conteos, 5.5, 17.5)
    b = m.total_diario_trapecio(conteos, 5.5, 17.5)
    assert m.error_relativo(b, a) < 0.05


# --- Curva acumulada y fechas --------------------------------------------
def test_F_empieza_en_0_termina_en_1_y_no_baja():
    F = m.acumulada(N_GAUSS, T_FINO)
    assert F[0] == 0
    assert F[-1] == pytest.approx(1.0)
    assert np.all(np.diff(F) >= 0)


def test_fecha_percentil_en_recta():
    """Si F sube en línea recta de 0 a 1 en 10 días, el 50 % es el día 5."""
    t = np.arange(11, dtype=float)
    F = t / 10
    assert m.fecha_percentil(F, t, 0.5) == pytest.approx(5.0)
    assert m.fecha_percentil(F, t, 0.05) == pytest.approx(0.5)


def test_validacion_gaussiana_fecha_media_y_mediana():
    """Validación obligatoria: fecha media y del 50 % = centro (error < 0,1 días)."""
    assert abs(m.fecha_media(N_GAUSS, T_FINO) - CENTRO) < 0.1
    F = m.acumulada(N_GAUSS, T_FINO)
    assert abs(m.fecha_percentil(F, T_FINO, 0.5) - CENTRO) < 0.1
    assert m.dispersion(N_GAUSS, T_FINO) == pytest.approx(SIGMA, rel=0.01)


def test_validacion_gaussiana_ventana_simetrica():
    """Validación obligatoria: la ventana óptima queda centrada en el pico,
    y en sus extremos la tasa es la misma: n(a + L) = n(a)."""
    L = 10.0
    r = m.mejor_ventana(N_GAUSS, L, T_FINO)
    assert abs((r.inicio + r.fin) / 2 - CENTRO) < 0.1
    n_inicio = np.interp(r.inicio, T_FINO, N_GAUSS)
    n_fin = np.interp(r.fin, T_FINO, N_GAUSS)
    assert m.error_relativo(n_fin, n_inicio) < 0.01


def test_aves_en_ventana_de_toda_la_temporada_es_el_total():
    """Unidades y balance: G sobre toda la temporada = N."""
    total = m.trapecio(N_GAUSS, T_FINO)
    assert m.aves_en_ventana(N_GAUSS, 0.0, 50.0, T_FINO) == pytest.approx(total)


def test_ventana_mas_larga_que_la_temporada_da_error():
    with pytest.raises(ValueError):
        m.mejor_ventana([1, 2, 3, 2, 1], L=10)


# --- Turno ---------------------------------------------------------------
def test_mejor_turno_conocido():
    """Perfil con pico a las 9:00 y 10:00: el mejor turno de 2 h es 9:00-11:00."""
    perfil = [1, 2, 9, 9, 2, 1]
    r = m.mejor_turno(perfil, horas=2, inicio_obs=7.0)
    assert (r.hora_inicio, r.hora_fin) == (9.0, 11.0)
    assert r.aves == 18
    assert r.fraccion == pytest.approx(18 / 24)


# --- Clase propia --------------------------------------------------------
def test_curva_de_paso_resumen():
    curva = m.CurvaDePaso("prueba", T_FINO, N_GAUSS)
    resumen = curva.resumen()
    assert resumen["fecha_5"] < resumen["fecha_50"] < resumen["fecha_95"]
    assert resumen["error_relativo"] < 1e-6


def test_curva_de_paso_rechaza_negativos():
    with pytest.raises(ValueError):
        m.CurvaDePaso("mala", [0, 1, 2], [1, -5, 2])
