"""Modelo farmacocinético, unidades y validación obligatoria."""

import numpy as np
import pytest

from src.config import TOLERANCIA_VALIDACION
from src.modelo import ModeloUnCompartimento, analizar_voluntario, simpson


@pytest.fixture
def modelo() -> ModeloUnCompartimento:
    return ModeloUnCompartimento(k=0.135, ka=3.0, v_l=41.0)


def test_concentracion_cero_antes_de_la_toma_y_lineal_en_dosis(modelo):
    t = np.array([-2.0, 0.0, 1.0, 5.0])
    c100 = modelo.concentracion(t, 100)
    assert c100[0] == 0 and c100[1] == 0
    assert np.allclose(modelo.concentracion(t, 200), 2 * c100)
    assert np.allclose(modelo.concentracion(t, 0), 0)


def test_antiderivada_analitica_contra_simpson(modelo):
    t = np.linspace(0, 24, 2401)
    numerica = simpson(t, modelo.concentracion(t, 200))
    assert float(modelo.auc_hasta(24, 200)) == pytest.approx(numerica, rel=1e-8)


def test_auc_infinito_es_d_sobre_vk_y_tiene_unidades_mg_h_L(modelo):
    t = np.linspace(0, 400, 40001)
    numerica = simpson(t, modelo.concentracion(t, 200))
    assert modelo.auc_infinito(200) == pytest.approx(200 / (41.0 * 0.135))
    assert numerica == pytest.approx(modelo.auc_infinito(200), rel=1e-6)
    assert modelo.depuracion == pytest.approx(200 / modelo.auc_infinito(200))


def test_caso_limite_ka_igual_k():
    m = ModeloUnCompartimento(k=0.5, ka=0.5, v_l=10)
    casi = ModeloUnCompartimento(k=0.5, ka=0.5 + 1e-7, v_l=10)
    t = np.linspace(0, 10, 11)
    assert np.allclose(m.concentracion(t, 100), casi.concentracion(t, 100), rtol=1e-5)


def test_pico_en_tiempo_maximo(modelo):
    tmax = modelo.tiempo_maximo()
    c = lambda x: float(modelo.concentracion(x, 100))  # noqa: E731
    assert c(tmax) > c(tmax - 0.01) and c(tmax) > c(tmax + 0.01)


def test_analizar_voluntario_recupera_parametros_de_datos_sinteticos(modelo):
    t = np.array([0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 24])
    c = modelo.concentracion(t, 200)
    r = analizar_voluntario(t, c, 200)
    assert r.k_1_h == pytest.approx(modelo.k, rel=1e-3)
    assert r.vida_media_h == pytest.approx(np.log(2) / modelo.k, rel=1e-3)
    assert r.v_l == pytest.approx(modelo.v_l, rel=0.05)
    assert r.auc_total > modelo.auc_infinito(200)
    assert r.auc_total == pytest.approx(r.auc_0_24_trapecio + r.cola_mg_h_l)


def test_validacion_obligatoria_auc_200h(analisis):
    validacion = analisis.tablas["validacion_auc"]
    assert len(validacion) == 60
    assert validacion["error_rel"].max() < TOLERANCIA_VALIDACION


def test_acumulado_observado_coincide_con_integral_exacta(analisis):
    verif = analisis.tablas["verificacion_datos"]
    assert verif["error_rel_acumulado"].mean() < 0.01
    assert verif["r2"].median() > 0.9


def test_relacion_atencion_tiene_pendiente_positiva(analisis):
    assert analisis.relacion.pendiente > 0
    assert 0 < analisis.relacion.r2 <= 1
