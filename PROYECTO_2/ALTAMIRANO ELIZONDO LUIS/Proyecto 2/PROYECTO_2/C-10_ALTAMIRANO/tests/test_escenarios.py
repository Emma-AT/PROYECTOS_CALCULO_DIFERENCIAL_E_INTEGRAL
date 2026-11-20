from pathlib import Path

import pandas as pd
import pytest

from src import escenarios as es
from src.limpieza import cargar_datos, depurar_entregas, leer_parametros

RUTA = Path(__file__).resolve().parent.parent / "datos" / "P05_C-10_ALTAMIRANO.xlsx"


def _resumen(notas, horas):
    return pd.DataFrame(
        {"grupo": list("ABCD")[: len(notas)], "nota_media": notas, "horas_docente": horas}
    )


def test_elegir_prefiere_menos_horas_si_la_diferencia_es_menor_que_el_umbral():
    r = _resumen([80.0, 79.5], [6.0, 1.0])
    assert es.elegir_estrategia(r, umbral=1.0)[0] == "B"  # 0,5 puntos < 1: gana la más barata
    assert es.elegir_estrategia(r, umbral=0.4)[0] == "A"  # 0,5 puntos > 0,4: gana la mejor nota


def test_elegir_con_empate_de_horas_gana_la_mayor_nota():
    r = _resumen([80.0, 79.8], [2.0, 2.0])
    assert es.elegir_estrategia(r, umbral=1.0)[0] == "A"


def test_umbral_de_cambio_detecta_donde_cambia_la_decision():
    r = _resumen([80.0, 74.0, 70.0], [6.0, 1.0, 0.0])
    cambios = es.umbral_de_cambio(r)
    assert cambios["umbral_puntos"].tolist() == [6.0, 10.0]
    assert cambios["pasa_a"].tolist() == ["B", "C"]


@pytest.fixture(scope="module")
def real():
    hojas = cargar_datos(RUTA)
    p = leer_parametros(hojas["Parametros"])
    dep = depurar_entregas(hojas["Entregas"], hojas["Tareas"], p["nota_max"])
    return hojas, p, dep, es.resumen_grupo(dep, hojas["Grupos"], p["ventana_h"], p["nota_max"])


@pytest.mark.skipif(not RUTA.exists(), reason="no está el Excel en datos/")
def test_resumen_real_el_modelo_reproduce_las_ultimas_24_horas(real):
    _, _, _, r = real
    assert (r["ip_modelo"] - r["ip_obs"]).abs().max() < 1e-6  # k ajustado al IP observado
    assert (
        r["ultimas_modelo"] - r["ultimas_obs"]
    ).abs().max() < 0.06  # dentro de 6 puntos porcentuales


@pytest.mark.skipif(not RUTA.exists(), reason="no está el Excel en datos/")
def test_decision_real_y_su_robustez(real):
    hojas, p, _dep, r = real
    elegida, _ = es.elegir_estrategia(r, p["umbral_nota"])
    assert elegida == "G03"
    tabla = es.sensibilidad_tratamientos(
        hojas["Entregas"],
        hojas["Tareas"],
        hojas["Grupos"],
        p["ventana_h"],
        p["nota_max"],
        p["umbral_nota"],
    )
    assert (tabla["elegida"] == "G03").all()  # no cambia con ningún tratamiento de los datos


@pytest.mark.skipif(not RUTA.exists(), reason="no está el Excel en datos/")
def test_bootstrap_es_reproducible_y_contiene_la_diferencia(real):
    _, _, dep, _ = real
    a = es.bootstrap_diferencia(dep, "G03", "G04", repeticiones=500, semilla=3)
    b = es.bootstrap_diferencia(dep, "G03", "G04", repeticiones=500, semilla=3)
    assert a == b
    dif, lo, hi = a
    assert lo < dif < hi


@pytest.mark.skipif(not RUTA.exists(), reason="no está el Excel en datos/")
def test_texto_de_recomendacion_incluye_grupo_y_cifras(real):
    _, p, _, r = real
    g, ex = es.elegir_estrategia(r, p["umbral_nota"])
    txt = es.texto_recomendacion(r, g, ex)
    assert g in txt and "78.3" in txt and "6.2" in txt
