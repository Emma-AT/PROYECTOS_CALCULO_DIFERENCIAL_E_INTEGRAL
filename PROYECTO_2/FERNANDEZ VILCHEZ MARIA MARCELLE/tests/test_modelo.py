"""Pruebas de limpieza.py y modelo.py (pytest)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import integrate

from src import limpieza, modelo

RUTA = Path(__file__).resolve().parents[1] / "datos" / "P01_C-02_FERNANDEZ.xlsx"


@pytest.fixture(scope="module")
def ancha() -> pd.DataFrame:
    return limpieza.cargar_espectro(RUTA)


@pytest.fixture(scope="module")
def params() -> dict[str, float]:
    return limpieza.leer_parametros(limpieza.leer_base(RUTA)["Parametros"])


# 1. Validación obligatoria: ∫_4^8 f² df = 448/3 con Simpson exacto
def test_simpson_f2_exacto() -> None:
    f = np.arange(4.0, 9.0)
    assert modelo.simpson(f, f**2) == pytest.approx(448 / 3, rel=1e-12)


# 2. El trapecio sobreestima la convexa f² (error conocido)
def test_trapecio_f2_error_conocido() -> None:
    f = np.arange(4.0, 9.0)
    # trapecio compuesto: 4 + 2(25+36+49) + ... calculado a mano = 150.0
    assert modelo.trapecio(f, f**2) == pytest.approx(150.0)
    assert modelo.trapecio(f, f**2) > 448 / 3


# 3. Simpson con número impar de subintervalos (usa 3/8) sigue siendo exacto en cúbicas
def test_simpson_impar_exacto_en_cubicas() -> None:
    f = np.arange(0.0, 6.0)  # 5 subintervalos
    assert modelo.simpson(f, f**3) == pytest.approx(5**4 / 4, rel=1e-12)


# 4. Coincidencia con scipy.integrate (solo para comparar)
def test_coincide_con_scipy(ancha: pd.DataFrame) -> None:
    f = ancha.columns.to_numpy(dtype=float)
    S = ancha.iloc[0].to_numpy()
    assert modelo.trapecio(f, S) == pytest.approx(integrate.trapezoid(S, f))
    assert modelo.simpson(f, S) == pytest.approx(integrate.simpson(S, x=f), rel=1e-2)


# 5. Aditividad / balance: theta + alfa + beta = potencia 4–30 Hz
def test_balance_de_bandas(ancha: pd.DataFrame, params: dict[str, float]) -> None:
    f = ancha.columns.to_numpy(dtype=float)
    for metodo in ("trapecio", "simpson"):
        p = modelo.potencias_por_epoca(ancha, params, metodo)
        completo = np.array(
            [
                modelo.potencia_banda(
                    fila, f, params["theta_inf"], params["beta_sup"], metodo
                )
                for fila in ancha.to_numpy()
            ]
        )
        suma = (p["theta"] + p["alfa"] + p["beta"]).to_numpy()
        # con trapecio la suma es exacta; con Simpson difiere levemente
        tol = 1e-9 if metodo == "trapecio" else 0.05
        assert np.allclose(suma, completo, rtol=tol)


# 6. Unidades: densidad constante 2 µV²/Hz en 10 Hz de ancho = 20 µV²
def test_unidades_densidad_constante() -> None:
    f = np.arange(1.0, 31.0)
    S = np.full_like(f, 2.0)
    assert modelo.potencia_banda(S, f, 4, 14, "simpson") == pytest.approx(20.0)
    assert modelo.potencia_banda(S, f, 4, 14, "trapecio") == pytest.approx(20.0)


# 7. AUC de un índice que separa perfectamente las clases vale 1
def test_auc_separacion_perfecta() -> None:
    indice = np.array([0.1, 0.2, 0.3, 2.0, 3.0, 4.0])
    etiqueta = np.array([0, 0, 0, 1, 1, 1])
    assert modelo.curva_roc(indice, etiqueta).auc == pytest.approx(1.0)


# 8. AUC de un índice sin información (clasificador al azar) ≈ 0,5; invertido = 0
def test_auc_casos_limite() -> None:
    etiqueta = np.array([0, 1, 0, 1])
    constante = np.array([1.0, 1.0, 1.0, 1.0])
    assert modelo.curva_roc(constante, etiqueta).auc == pytest.approx(0.5)
    invertido = np.array([4.0, 3.0, 2.0, 1.0])
    etiqueta2 = np.array([0, 0, 1, 1])
    assert modelo.curva_roc(invertido, etiqueta2).auc == pytest.approx(0.0)


# 9. La ROC es monótona y va de (0,0) a (1,1); TP+FN y FP+TN son constantes
def test_roc_forma_y_balances() -> None:
    rng = np.random.default_rng(1)
    etiqueta = rng.integers(0, 2, 60)
    indice = rng.normal(size=60) + etiqueta
    roc = modelo.curva_roc(indice, etiqueta)
    assert (roc.fpr[0], roc.tpr[0]) == (0.0, 0.0)
    assert (roc.fpr[-1], roc.tpr[-1]) == (1.0, 1.0)
    assert np.all(np.diff(roc.fpr) >= 0) and np.all(np.diff(roc.tpr) >= 0)
    assert np.all(roc.tp + roc.fn == etiqueta.sum())
    assert np.all(roc.fp + roc.tn == (etiqueta == 0).sum())


# 10. elegir_umbral respeta la sensibilidad mínima y minimiza el costo
def test_elegir_umbral_minimo_costo() -> None:
    indice = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], float)
    etiqueta = np.array([0, 0, 0, 0, 1, 0, 1, 1, 1, 1])
    roc = modelo.curva_roc(indice, etiqueta)
    r = modelo.elegir_umbral(roc, 0.9, 8.0, 1.0)
    assert r.sensibilidad >= 0.9
    # c=5 detecta los 5 somnolientos (1,0) con 1 falsa alarma (el índice 6)
    # c=7 daría sensibilidad 0,8 < 0,9, así que no es factible.
    assert r.umbral == 5.0
    assert r.fp == 1 and r.fn == 0 and r.costo == 1.0
    assert r.matriz_confusion().to_numpy().sum() == 10


# 11. Si ningún umbral cumple la sensibilidad, se avisa con un error claro
def test_umbral_imposible_lanza_error() -> None:
    roc = modelo.curva_roc(np.array([1.0, 2.0]), np.array([0, 1]))
    with pytest.raises(ValueError):
        modelo.elegir_umbral(roc, 1.5, 8.0, 1.0)


# 12. La interpolación completa todos los faltantes sin tocar los demás datos
def test_cargar_espectro_sin_faltantes(ancha: pd.DataFrame) -> None:
    assert limpieza.contar_faltantes(RUTA) > 0
    assert ancha.shape == (48, 30)
    assert not ancha.isna().any().any()
    original = limpieza.leer_base(RUTA)["Espectro_EEG"].dropna()
    ejemplo = original.iloc[100]
    valor = ancha.loc[(ejemplo["viaje"], ejemplo["epoca"]), ejemplo["frecuencia_Hz"]]
    assert valor == pytest.approx(ejemplo["potencia_uV2_Hz"])


# 13. detectar_artefactos marca un valor extremo y no marca datos normales
def test_detectar_artefactos_sintetico() -> None:
    idx = pd.MultiIndex.from_product([[1], range(1, 11)], names=["viaje", "epoca"])
    serie = pd.Series([100, 102, 98, 101, 99, 103, 97, 100, 400, 101], index=idx)
    marca = limpieza.detectar_artefactos(serie)
    assert marca.sum() == 1 and bool(marca.loc[(1, 9)])


# 14. Validación de entradas: archivo y hojas inexistentes dan mensajes claros
def test_validacion_de_entradas(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        limpieza.leer_base(tmp_path / "no_existe.xlsx")
    malo = tmp_path / "malo.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(malo, sheet_name="Otra", index=False)
    with pytest.raises(ValueError, match="Falta la hoja"):
        limpieza.leer_base(malo)


# 15. Ley de potencias: el ajuste recupera A y b y la integral coincide con la exacta
def test_ley_de_potencias_exacta() -> None:
    f = np.arange(1.0, 31.0)
    A, b = modelo.ajustar_ley_potencia(f, 30.0 * f**-1.5)
    assert (A, b) == (pytest.approx(30.0), pytest.approx(-1.5))
    # ∫_4^8 30 f^-1.5 df = 30/(-0.5) (8^-0.5 - 4^-0.5)
    esperado = 30 / (-0.5) * (8**-0.5 - 4**-0.5)
    assert modelo.integral_ley_potencia(30.0, -1.5, 4, 8) == pytest.approx(esperado)
    # caso b = -1: A ln(f2/f1)
    assert modelo.integral_ley_potencia(2.0, -1.0, 1, np.e) == pytest.approx(2.0)


# 16. Escenarios: el base cumple la sensibilidad mínima y el de chofer prioritario
#     no tiene más falsas alarmas que el base
def test_escenarios_coherentes() -> None:
    from src import escenarios

    d = escenarios.preparar_datos(RUTA)
    tabla = escenarios.comparar_escenarios(d)
    assert len(tabla) == 3
    assert tabla.loc[0, "sensibilidad"] >= d.params["sens_min"]
    assert tabla.loc[1, "falsas_alarmas"] <= tabla.loc[0, "falsas_alarmas"]
    assert tabla.loc[2, "epocas_usadas"] == 48 and tabla.loc[0, "epocas_usadas"] == 46


# 17. Balance: TP+FN = épocas somnolientas, TP+FP+FN+TN = épocas usadas
def test_balance_matriz_de_confusion() -> None:
    from src import escenarios

    d = escenarios.preparar_datos(RUTA)
    t = escenarios.comparar_escenarios(d).loc[0]
    n_somn = int(d.somnolencia[~d.artefacto].sum())
    assert t["omisiones"] + t["sensibilidad"] * n_somn == pytest.approx(n_somn)


# 18. evaluar_umbral coincide con el punto correspondiente de la curva ROC
def test_evaluar_umbral_coincide_con_roc() -> None:
    rng = np.random.default_rng(7)
    etiqueta = rng.integers(0, 2, 40)
    indice = rng.normal(size=40) + etiqueta
    roc = modelo.curva_roc(indice, etiqueta)
    k = 12
    r = modelo.evaluar_umbral(indice, etiqueta, roc.umbrales[k], 8.0, 1.0)
    assert (r.tp, r.fp, r.fn, r.tn) == (roc.tp[k], roc.fp[k], roc.fn[k], roc.tn[k])
    assert r.sensibilidad == pytest.approx(roc.tpr[k])
    assert r.costo == pytest.approx(8.0 * roc.fn[k] + roc.fp[k])
    # umbral muy alto: no hay alarmas; muy bajo: todo es alarma
    assert modelo.evaluar_umbral(indice, etiqueta, 1e9, 8, 1).tp == 0
    assert modelo.evaluar_umbral(indice, etiqueta, -1e9, 8, 1).tn == 0
