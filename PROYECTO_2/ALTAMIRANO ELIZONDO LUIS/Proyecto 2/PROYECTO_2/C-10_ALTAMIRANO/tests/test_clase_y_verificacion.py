from pathlib import Path

import numpy as np
import pytest

from src import modelo as m

RUTA = Path(__file__).resolve().parent.parent / "datos" / "P05_C-10_ALTAMIRANO.xlsx"


def test_error_relativo():
    assert m.error_relativo(1.01, 1.0) == pytest.approx(0.01)
    assert m.error_relativo(0.2, 0.0) == pytest.approx(0.2)  # exacto cero: error absoluto


def test_grupo_entregas_con_k_conocido_recupera_ip_k_y_ultimas_24h():
    k, T = 0.3, 168.0
    horas = m.simular_entregas(k, T, n=20000, semilla=11)
    g = m.GrupoEntregas("sim", T, horas)
    assert g.tau.min() >= 0 and g.tau.max() <= 1
    assert g.ip_observado() == pytest.approx(m.ip_modelo(k, T), abs=0.01)
    assert abs(g.k_estimado() - k) / k < 0.10
    assert g.ultimas_observada() == pytest.approx(g.ultimas_modelo(), abs=0.02)


def test_grupo_entregas_tau_es_horas_sobre_plazo():
    g = m.GrupoEntregas("g", 100.0, np.array([0.0, 50.0, 100.0]))
    assert g.tau.tolist() == [0.0, 0.5, 1.0]
    assert g.ultimas_observada(ventana=24.0) == pytest.approx(1 / 3)


@pytest.mark.skipif(not RUTA.exists(), reason="falta el Excel")
def test_cada_integral_importante_coincide_de_dos_formas():
    from src.escenarios import resumen_grupo
    from src.limpieza import cargar_datos, depurar_entregas, leer_parametros
    from src.reporte import tabla_verificacion

    hojas = cargar_datos(RUTA)
    p = leer_parametros(hojas["Parametros"])
    dep = depurar_entregas(hojas["Entregas"], hojas["Tareas"], p["nota_max"])
    res = resumen_grupo(dep, hojas["Grupos"], p["ventana_h"])
    t = tabla_verificacion(res, dep, p["ventana_h"])
    assert len(t) == 6 * 4  # seis comparaciones por grupo
    assert t["error relativo"].max() < 1e-3
