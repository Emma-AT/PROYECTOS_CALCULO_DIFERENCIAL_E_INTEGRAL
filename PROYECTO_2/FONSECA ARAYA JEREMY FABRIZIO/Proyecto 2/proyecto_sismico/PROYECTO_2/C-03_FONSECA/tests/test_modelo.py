"""Pruebas de resultados conocidos, unidades, límites y regresión del proyecto."""

from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from scipy.integrate import simpson as simpson_scipy
from scipy.integrate import trapezoid

from src.escenarios import comparar_escenarios, recomendar
from src.limpieza import (
    EXCEL,
    BaseDatos,
    corregir_linea_base,
    interpolar_faltantes,
    leer_base,
    validar_esquema,
)
from src.modelo import (
    G,
    duracion_significativa,
    estimar_b,
    intensidad_arias,
    perdida_anual,
    perdida_exacta_lineal,
    probabilidad,
    tasa,
    validar_seno,
    vpn_refuerzo,
)
from src.numericos import error_relativo, integral_acumulada, simpson, trapecio


@pytest.fixture
def base() -> BaseDatos:
    """Entrega una lectura independiente del Excel asignado."""
    return leer_base(EXCEL)


def test_trapecio_lineal_no_uniforme() -> None:
    """La integral de 2x+1 entre 0 y 3 es 12, aun con paso variable."""
    x = np.array([0, 0.2, 1, 3])
    assert trapecio(x, 2 * x + 1) == pytest.approx(12)


def test_simpson_cubico() -> None:
    """Simpson integra exactamente un polinomio de grado tres."""
    x = np.linspace(0, 2, 11)
    assert simpson(x, x**3) == pytest.approx(4)


def test_acumulado_balance_y_unidades() -> None:
    """Aceleración 2 cm/s² durante 3 s produce v=6 cm/s y x=9 cm."""
    t = np.linspace(0, 3, 31)
    v = integral_acumulada(t, np.full_like(t, 2))
    x = integral_acumulada(t, v)
    assert v[-1] == pytest.approx(6)
    assert x[-1] == pytest.approx(9)
    assert v[-1] == pytest.approx(trapecio(t, np.full_like(t, 2)))


def test_doble_integral_seno_obligatoria() -> None:
    """Ambas curvas tienen error relativo máximo menor al 0,5 % exigido."""
    assert (validar_seno().error_relativo_max_pct < 0.5).all()


@pytest.mark.parametrize("x,y", [([0, 1, 2, 3], [1, 2, 3, 4]), ([0, 1, 3], [0, 1, 9])])
def test_simpson_rechaza_malla_inadecuada(x: list, y: list) -> None:
    """No se aplica la fórmula de Simpson donde sus hipótesis fallan."""
    with pytest.raises(ValueError):
        simpson(x, y)


@pytest.mark.parametrize("x,y", [([0, 0], [1, 2]), ([1, 0], [1, 2]), ([0, 1], [1, np.nan])])
def test_trapecio_rechaza_entradas_invalidas(x: list, y: list) -> None:
    """Rechaza tiempos duplicados, invertidos y ordenadas faltantes."""
    with pytest.raises(ValueError):
        trapecio(x, y)


def test_interpolacion_y_linea_base() -> None:
    """Interpola un faltante y resta el promedio antes del evento."""
    t = np.arange(5.0)
    a = np.array([2, np.nan, 2, 6, 4])
    np.testing.assert_allclose(interpolar_faltantes(t, a), [2, 2, 2, 6, 4])
    np.testing.assert_allclose(corregir_linea_base(t, a, 3), [0, 0, 0, 4, 2])


def test_no_extrapola_faltante_extremo() -> None:
    """Un hueco en el extremo necesita un supuesto que no se hace en silencio."""
    with pytest.raises(ValueError):
        interpolar_faltantes([0, 1, 2], [np.nan, 1, 2])


def test_arias_conversion_cm_a_m() -> None:
    """100 cm/s² durante 2 s equivale a IA=pi/g m/s."""
    assert intensidad_arias([0, 1, 2], [100, 100, 100]) == pytest.approx(np.pi / G)


def test_duracion_energia_constante() -> None:
    """Energía uniforme durante 10 s tiene duración 5–95 % de 9 s."""
    t = np.linspace(0, 10, 101)
    assert duracion_significativa(t, np.ones_like(t)) == pytest.approx((0.5, 9.5, 9))


def test_duracion_nula_indefinida() -> None:
    """Aceleración nula no produce una duración significativa definida."""
    with pytest.raises(ValueError):
        duracion_significativa([0, 1, 2], [0, 0, 0])


def test_tasa_y_probabilidad() -> None:
    """En M=3 la tasa es lambda3 y el horizonte nulo tiene probabilidad cero."""
    assert tasa(3, 20, 1) == pytest.approx(20)
    assert tasa(4, 20, 1) == pytest.approx(2)
    assert probabilidad(7, 20, 1, 0) == 0
    assert 0 < probabilidad(7, 20, 1, 50) < 1


def test_pae_dano_constante() -> None:
    """Con daño fijo, PAE=V*D*(lambda(5)-lambda(8)), sin ajustes numéricos."""
    m = np.linspace(5, 8, 13)
    esperado = 1000 * 0.2 * (tasa(5, 20, 1) - tasa(8, 20, 1))
    assert perdida_anual(m, np.full_like(m, 0.2), 20, 1, 1000) == pytest.approx(esperado, rel=1e-6)
    assert perdida_exacta_lineal(m, np.full_like(m, 0.2), 20, 1, 1000) == pytest.approx(esperado)


def test_vpn_descuento_cero_y_positivo() -> None:
    """El caso r=0 evita división por cero y coincide con el límite analítico."""
    assert vpn_refuerzo(100, 20, 0, 10) == pytest.approx(100)
    assert vpn_refuerzo(100, 20, 0.1, 10) == pytest.approx(-100 + 200 * (1 - np.exp(-1)))
    assert vpn_refuerzo(100, 20, 1e-12, 10) == pytest.approx(100)


def test_comparacion_scipy_solo_validacion() -> None:
    """Las bibliotecas externas se usan como referencia, no como implementación."""
    x = np.linspace(0, 3, 101)
    y = np.exp(-x) * np.cos(x)
    assert simpson(x, y) == pytest.approx(simpson_scipy(y, x=x))
    assert trapecio(x, y) == pytest.approx(trapezoid(y, x=x))


def test_lectura_no_modifica_excel(base: BaseDatos) -> None:
    """La lectura conserva los faltantes originales y las 625 observaciones."""
    antes = EXCEL.read_bytes()
    leer_base(BytesIO(antes))
    assert EXCEL.read_bytes() == antes
    assert len(base.hojas["Catalogo_sismos"]) == 625
    assert base.hojas["Catalogo_sismos"].profundidad_km.isna().sum() == 6
    assert base.hojas["Acelerograma"].aceleracion_cm_s2.isna().sum() == 3


def test_esquema_unidad_incorrecta(base: BaseDatos) -> None:
    """Impide tratar aceleración en m/s² como si fuera cm/s²."""
    d = base.hojas["Diccionario"]
    d.loc[d.columna == "aceleracion_cm_s2", "unidad"] = "m/s²"
    with pytest.raises(ValueError, match="Unidad inválida"):
        validar_esquema(base.hojas)


def test_recomendacion_y_sensibilidad(base: BaseDatos) -> None:
    """La recomendación responde al parámetro b; no está escrita como constante."""
    b = estimar_b(base.hojas["Catalogo_sismos"], base.m0)
    assert recomendar(comparar_escenarios(base, b)).escenario == "Opción A"
    assert recomendar(comparar_escenarios(base, b + 0.1)).escenario == "Sin refuerzo"


def test_no_invertir_si_todos_vpn_negativos() -> None:
    """No recomienda la alternativa menos negativa cuando existe VPN=0."""
    tabla = pd.DataFrame({"escenario": ["Sin refuerzo", "A", "B"], "vpn_colones": [0, -1, -2]})
    assert recomendar(tabla).escenario == "Sin refuerzo"


def test_error_referencia_nula() -> None:
    """Distingue cero exacto de error relativo indefinido por referencia cero."""
    assert error_relativo(0, 0) == 0
    assert np.isinf(error_relativo(1, 0))
