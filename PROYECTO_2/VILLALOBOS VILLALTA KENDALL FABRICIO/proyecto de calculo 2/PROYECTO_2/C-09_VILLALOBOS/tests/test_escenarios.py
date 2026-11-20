"""Superposición, evaluación de planes y recomendación."""

import numpy as np
import pytest

from src.config import COBERTURA_PRUDENTE, GRUPOS
from src.escenarios import (
    PlanConsumo,
    concentracion_plan,
    evaluar_plan,
    hora_limite,
    maximo_diario,
)
from src.modelo import ModeloUnCompartimento, horas_efecto, horas_efecto_filas


@pytest.fixture
def modelo() -> ModeloUnCompartimento:
    return ModeloUnCompartimento(k=0.135, ka=3.0, v_l=41.0)


def test_superposicion_es_suma_de_tomas(modelo):
    t = np.linspace(0, 30, 301)
    plan = PlanConsumo("X", (8.0, 13.0), (95.0, 160.0))
    suma = modelo.concentracion(t - 8, 95) + modelo.concentracion(t - 13, 160)
    assert np.allclose(concentracion_plan(plan, modelo, t), suma)


def test_dias_previos_solo_aumentan_la_concentracion(modelo):
    t = np.linspace(0, 30, 301)
    plan = PlanConsumo("X", (8.0,), (95.0,))
    assert np.all(concentracion_plan(plan, modelo, t, 4) >= concentracion_plan(plan, modelo, t))


def test_balance_cafeina_total_y_auc_de_plan(modelo, analisis):
    plan = analisis.planes["D"]
    assert plan.total_mg == pytest.approx(3 * 95)
    t = np.linspace(0, 400, 40001)
    c = concentracion_plan(plan, modelo, t)
    auc = np.sum(np.diff(t) * (c[1:] + c[:-1]) / 2)
    assert auc == pytest.approx(plan.total_mg / (modelo.v_l * modelo.k), rel=1e-4)


def test_hora_limite_cumple_umbral_exacto(modelo, analisis):
    p = analisis.param
    h = hora_limite(modelo, 95, p)
    c = concentracion_plan(PlanConsumo("x", (h,), (95,)), modelo, np.array([p.hora_dormir]))[0]
    assert c == pytest.approx(p.c_sueno, rel=1e-4)


def test_maximo_diario_lleva_al_umbral_de_sueno(modelo, analisis):
    p = analisis.param.con_cambios(max_diario_mg=1e6)
    plan = analisis.planes["B"]
    m = maximo_diario(plan, modelo, p)
    escalado = PlanConsumo("s", plan.horas, tuple(d * m / plan.total_mg for d in plan.dosis_mg))
    assert evaluar_plan(escalado, modelo, p)["c_dormir"] == pytest.approx(p.c_sueno)


def test_terciles_y_recomendacion_cumple_criterio(analisis):
    assert analisis.clasificados["grupo"].value_counts().tolist() == [20, 20, 20]
    rec = analisis.tablas["guia_consumo"]
    assert rec["grupo"].tolist() == list(GRUPOS)
    assert (rec["c_dormir"] < analisis.param.c_sueno).all()
    assert (rec["cafeina_mg"] <= analisis.param.max_diario_mg).all()
    evaluacion = analisis.tablas["evaluacion_planes"]
    base = evaluacion[evaluacion["escenario"] == evaluacion["escenario"].iloc[0]]
    for _, fila in rec.iterrows():
        factibles = base[(base["grupo"] == fila["grupo"]) & base["cumple"]]
        assert fila["horas_efecto"] == pytest.approx(factibles["horas_efecto"].max(), abs=0.01)


def test_horas_efecto_dos_metodos(analisis):
    assert analisis.tablas["comparacion_horas_efecto"]["error_rel"].max() < 1e-3


def test_version_vectorizada_de_horas_efecto(modelo):
    t = np.linspace(8, 20, 121)
    curvas = np.array([modelo.concentracion(t - h, 160) for h in (7.0, 9.0, 12.0)])
    esperado = [horas_efecto(t, c, 1.5, 8, 20) for c in curvas]
    assert np.allclose(horas_efecto_filas(t, curvas, 1.5), esperado)


def test_plan_optimizado_cumple_y_mejora_al_catalogo_prudente(analisis):
    p = analisis.param
    opt = analisis.tablas["planes_optimizados"].set_index("grupo")
    prudente = analisis.tablas["guia_consumo_prudente"].set_index("grupo")
    assert (opt["c_dormir"] < p.c_sueno).all()
    assert (opt["cafeina_mg"] <= p.max_diario_mg).all()
    assert (opt["pct_personas_duermen_bien"] >= COBERTURA_PRUDENTE).all()
    for g in GRUPOS:
        assert opt.loc[g, "horas_efecto"] >= prudente.loc[g, "horas_efecto"] - 0.1
