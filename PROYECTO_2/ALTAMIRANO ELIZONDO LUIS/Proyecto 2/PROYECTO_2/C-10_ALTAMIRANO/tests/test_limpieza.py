from pathlib import Path

import pandas as pd
import pytest

from src import limpieza as lp

RUTA = Path(__file__).resolve().parent.parent / "datos" / "P05_C-10_ALTAMIRANO.xlsx"


def _tareas():
    return pd.DataFrame(
        {
            "tarea": ["T1"],
            "grupo": ["G01"],
            "apertura": ["2026-03-09 23:00"],
            "cierre": ["2026-03-16 23:00"],
        }
    )


def _entregas(filas):
    return pd.DataFrame(
        filas, columns=["tarea", "grupo", "estudiante", "intento", "fecha_hora_entrega", "nota"]
    )


def test_conserva_solo_el_ultimo_intento():
    e = _entregas(
        [
            ["T1", "G01", "G01-01", 1, "2026-03-10 10:00", float("nan")],
            ["T1", "G01", "G01-01", 2, "2026-03-11 10:00", 70.0],
            ["T1", "G01", "G01-02", 1, "2026-03-12 10:00", 80.0],
        ]
    )
    dep = lp.depurar_entregas(e, _tareas())
    assert len(dep) == 2
    assert dep.loc[dep.estudiante == "G01-01", "nota"].iloc[0] == 70.0


@pytest.mark.parametrize(
    "metodo,esperado",
    [("dividir10", 51.3), ("tope", 100.0), ("descartar", None)],
)
def test_nota_mayor_que_100_se_trata_segun_el_metodo(metodo, esperado):
    e = _entregas([["T1", "G01", "G01-01", 1, "2026-03-10 10:00", 513.0]])
    nota = lp.depurar_entregas(e, _tareas(), atipicos=metodo)["nota"].iloc[0]
    if esperado is None:
        assert pd.isna(nota)
    else:
        assert nota == pytest.approx(esperado)


def test_dividir10_no_acepta_una_nota_que_sigue_fuera_de_rango():
    e = _entregas([["T1", "G01", "G01-01", 1, "2026-03-10 10:00", 1500.0]])
    assert pd.isna(lp.depurar_entregas(e, _tareas())["nota"].iloc[0])


def test_horas_tau_y_tardia():
    e = _entregas(
        [
            [
                "T1",
                "G01",
                "G01-01",
                1,
                "2026-03-13 11:00",
                90.0,
            ],  # 84 h desde la apertura: justo la mitad
            ["T1", "G01", "G01-02", 1, "2026-03-17 00:00", 60.0],  # una hora después del cierre
        ]
    )
    dep = lp.depurar_entregas(e, _tareas()).set_index("estudiante")
    assert dep.loc["G01-01", "horas"] == pytest.approx(84.0)
    assert dep.loc["G01-01", "tau"] == pytest.approx(0.5)
    assert not dep.loc["G01-01", "tardia"] and dep.loc["G01-02", "tardia"]


def test_imputar_media_rellena_faltantes_con_la_media_del_grupo_en_la_tarea():
    e = _entregas(
        [
            ["T1", "G01", "G01-01", 1, "2026-03-10 10:00", 60.0],
            ["T1", "G01", "G01-02", 1, "2026-03-10 11:00", 80.0],
            ["T1", "G01", "G01-03", 1, "2026-03-10 12:00", float("nan")],
        ]
    )
    dep = lp.depurar_entregas(e, _tareas(), faltantes="imputar_media_grupo_tarea")
    assert dep.loc[dep.estudiante == "G01-03", "nota"].iloc[0] == pytest.approx(70.0)


def test_validar_entradas_falla_si_falta_una_hoja_o_columna():
    hojas = {n: pd.DataFrame(columns=c) for n, c in lp.COLUMNAS.items()}
    assert lp.validar_entradas(hojas)
    sin_hoja = {k: v for k, v in hojas.items() if k != "Tareas"}
    with pytest.raises(ValueError, match="Tareas"):
        lp.validar_entradas(sin_hoja)
    hojas["Entregas"] = hojas["Entregas"].drop(columns=["nota"])
    with pytest.raises(ValueError, match="nota"):
        lp.validar_entradas(hojas)


@pytest.mark.skipif(not RUTA.exists(), reason="no está el Excel en datos/")
def test_conteos_con_los_datos_reales():
    hojas = lp.cargar_datos(RUTA)
    p = lp.leer_parametros(hojas["Parametros"])
    dep = lp.depurar_entregas(hojas["Entregas"], hojas["Tareas"], p["nota_max"])
    inf = lp.informe_depuracion(hojas["Entregas"], dep)
    assert inf["registros_originales"] == 1182
    assert inf["intentos_descartados"] == 15
    assert inf["notas_mayores_que_100"] == 4
    assert dep["nota"].max() <= 100
    assert inf["entregas_antes_de_apertura"] == 0
    # El plazo de G04 es de 216 h por la ampliación de 48 h; el resto es de 168 h.
    assert dep.groupby("grupo")["plazo_h"].first().to_dict() == {
        "G01": 168,
        "G02": 168,
        "G03": 168,
        "G04": 216,
    }
